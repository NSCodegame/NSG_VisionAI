"""
Webcam Detection Router — Live laptop camera with YOLO + DeepFace

GET /api/v1/webcam/stream  — MJPEG stream with bounding boxes
GET /api/v1/webcam/snapshot — Latest annotated JPEG frame
GET /api/v1/webcam/detections — Latest detection results as JSON
POST /api/v1/webcam/start   — Start webcam capture
POST /api/v1/webcam/stop    — Stop webcam capture
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from app.api.v1.dependencies.auth import require_operator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webcam", tags=["Webcam Detection"])

# ---------------------------------------------------------------------------
# COCO class remapping — correct YOLO's visual-similarity misclassifications
#
# YOLO is trained on COCO which has no "pen", "pencil", "marker" classes.
# It maps thin elongated objects to the closest COCO class (toothbrush).
# We remap based on aspect ratio + size to give accurate labels.
# ---------------------------------------------------------------------------

# Classes YOLO gets wrong due to visual similarity
_REMAP_RULES: Dict[str, List[Dict]] = {
    # toothbrush is almost always a pen/pencil/marker in office/desk context
    "toothbrush": [
        {"min_aspect": 4.0, "max_area_frac": 0.03, "label": "pen"},
        {"min_aspect": 3.0, "max_area_frac": 0.05, "label": "pencil"},
        {"label": "pen"},   # Default — toothbrush is extremely rare in surveillance
    ],
    # YOLO cannot reliably distinguish scissors from knife — both are bladed objects.
    # In a surveillance/security context, always treat as knife (higher threat priority).
    # Real scissors in a security scenario are still a potential threat anyway.
    "scissors": [
        {"label": "knife"},  # Always remap — YOLO confuses knife/scissors constantly
    ],
    # fork sometimes detected as pen/comb
    "fork": [
        {"min_aspect": 3.5, "label": "pen"},
        {"label": "fork"},
    ],
    # spoon sometimes detected as small rounded objects
    "spoon": [
        {"min_aspect": 3.0, "label": "pen"},
        {"label": "spoon"},
    ],
}

# Classes that should NEVER be remapped (already correct)
_NO_REMAP = {
    "person", "car", "truck", "bus", "motorcycle", "bicycle",
    "knife", "gun", "pistol", "rifle", "laptop", "cell phone",
    "backpack", "handbag", "suitcase", "chair", "bottle", "cup",
    "book", "clock", "vase", "remote", "keyboard", "mouse",
    "tv", "microwave", "oven", "refrigerator", "sink", "toilet",
    "bed", "couch", "dining table", "dog", "cat", "bird",
}

def _remap_class(cls_name: str, bbox: Dict, frame_shape: tuple) -> str:
    """
    Apply post-processing remapping to correct YOLO misclassifications.

    Args:
        cls_name: Raw YOLO class name
        bbox: {"x1", "y1", "x2", "y2"} in pixels
        frame_shape: (height, width, channels)

    Returns:
        Corrected class name
    """
    if cls_name in _NO_REMAP:
        return cls_name

    rules = _REMAP_RULES.get(cls_name)
    if not rules:
        return cls_name

    h, w = frame_shape[:2]
    bw = max(bbox["x2"] - bbox["x1"], 1)
    bh = max(bbox["y2"] - bbox["y1"], 1)
    aspect = max(bw, bh) / min(bw, bh)  # Always >= 1
    area_frac = (bw * bh) / (w * h)

    for rule in rules:
        min_asp = rule.get("min_aspect", 0)
        max_asp = rule.get("max_aspect", 9999)
        max_area = rule.get("max_area_frac", 1.0)
        min_area = rule.get("min_area_frac", 0.0)

        if aspect >= min_asp and aspect <= max_asp and area_frac <= max_area and area_frac >= min_area:
            return rule["label"]

    return cls_name  # No rule matched — keep original


# ---------------------------------------------------------------------------
# Behaviour analysis helpers
# ---------------------------------------------------------------------------

_BEHAVIOUR_RULES = {
    "person":       "MONITORING",
    "pen":          "USING_PEN",
    "pencil":       "USING_PEN",
    "marker":       "USING_PEN",
    "cell phone":   "USING_PHONE",
    "laptop":       "WORKING",
    "keyboard":     "WORKING",
    "mouse":        "WORKING",
    "backpack":     "CARRYING_BAG",
    "handbag":      "CARRYING_BAG",
    "suitcase":     "CARRYING_LUGGAGE",
    "knife":        "ARMED_THREAT",
    "scissors":     "POTENTIAL_THREAT",
    "gun":          "ARMED_THREAT",
    "pistol":       "ARMED_THREAT",
    "rifle":        "ARMED_THREAT",
    "bottle":       "CARRYING_OBJECT",
    "cup":          "CARRYING_OBJECT",
    "book":         "READING",
    "chair":        "SEATED",
    "car":          "VEHICLE_PRESENT",
    "motorcycle":   "VEHICLE_PRESENT",
    "bicycle":      "VEHICLE_PRESENT",
    "truck":        "VEHICLE_PRESENT",
    "bus":          "VEHICLE_PRESENT",
}

_THREAT_CLASSES = {"knife", "gun", "pistol", "rifle"}
_POTENTIAL_THREAT_CLASSES = {"scissors"}

_COLOURS = {
    "ARMED_THREAT":      (0,   0,   255),
    "POTENTIAL_THREAT":  (0,   100, 255),
    "MONITORING":        (0,   255, 0),
    "USING_PHONE":       (255, 165, 0),
    "USING_PEN":         (180, 220, 255),
    "WORKING":           (0,   200, 255),
    "READING":           (100, 200, 255),
    "CARRYING_BAG":      (200, 200, 0),
    "CARRYING_LUGGAGE":  (200, 200, 0),
    "CARRYING_OBJECT":   (180, 180, 180),
    "SEATED":            (100, 255, 100),
    "VEHICLE_PRESENT":   (255, 0,   255),
    "FACE_DETECTED":     (0,   255, 255),
    "UNKNOWN":           (128, 128, 128),
}


def _behaviour_from_class(cls: str) -> str:
    return _BEHAVIOUR_RULES.get(cls.lower(), "UNKNOWN")


def _is_threat(cls: str) -> bool:
    return cls.lower() in _THREAT_CLASSES


def _is_potential_threat(cls: str) -> bool:
    return cls.lower() in _POTENTIAL_THREAT_CLASSES


# ---------------------------------------------------------------------------
# WebcamDetector — runs in a background thread
# ---------------------------------------------------------------------------

class WebcamDetector:
    """
    Captures frames from the laptop webcam, runs YOLO object detection
    and DeepFace face analysis, then stores the annotated frame + results.
    """

    def __init__(self) -> None:
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._face_thread: Optional[threading.Thread] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._face_lock = threading.Lock()
        self._capture_lock = threading.Lock()

        # Latest raw frame from capture thread
        self._latest_raw_frame: Optional[np.ndarray] = None

        # Latest results
        self._latest_jpeg: Optional[bytes] = None
        self._latest_detections: List[Dict[str, Any]] = []
        self._latest_faces: List[Dict[str, Any]] = []
        self._pending_face_frame: Optional[np.ndarray] = None
        self._frame_count = 0
        self._fps = 0.0
        self._started_at: Optional[str] = None

        # Lazy-load models
        self._yolo = None
        self._yolo_loaded = False
        self._device = "cpu"

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def start(self, camera_index: int = 0) -> bool:
        if self._running:
            return True

        # Try DirectShow first (Windows — lower latency), then default
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error("Cannot open webcam at index %d", camera_index)
            return False

        # Set camera properties for low latency
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # Minimal buffer = latest frame always

        self._cap = cap
        self._running = True
        self._started_at = datetime.utcnow().isoformat()

        # Thread 1: Capture — reads frames as fast as camera allows
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True, name="webcam-capture")
        self._capture_thread.start()

        # Thread 2: YOLO inference — processes latest captured frame
        self._thread = threading.Thread(target=self._loop, daemon=True, name="webcam-yolo")
        self._thread.start()

        # Thread 3: Face analysis — runs independently, never blocks YOLO
        self._face_thread = threading.Thread(target=self._face_loop, daemon=True, name="webcam-face")
        self._face_thread.start()

        logger.info("Webcam detector started (camera %d)", camera_index)
        return True

    def stop(self) -> None:
        self._running = False
        for t in [self._capture_thread, self._thread, self._face_thread]:
            if t and t.is_alive():
                t.join(timeout=2)
        if self._cap:
            self._cap.release()
            self._cap = None
        self._latest_jpeg = None
        self._latest_raw_frame = None
        self._latest_detections = []
        self._latest_faces = []
        logger.info("Webcam detector stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def get_latest_detections(self) -> Dict[str, Any]:
        with self._lock:
            dets = list(self._latest_detections)
            fc = self._frame_count
            fps = round(self._fps, 1)
        with self._face_lock:
            faces = list(self._latest_faces)
        return {
            "frame_count": fc,
            "fps": fps,
            "started_at": self._started_at,
            "detections": dets,
            "faces": faces,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _load_yolo(self):
        """Load yolov8n at imgsz=640 — best balance of speed + small object detection on CPU."""
        if self._yolo_loaded:
            return
        try:
            from ultralytics import YOLO
            import torch

            self._yolo = YOLO("yolov8n.pt")   # nano — fastest, ~40 FPS on CPU
            self._device = "cpu"
            # Enable OpenCV threading for faster pre/post processing
            cv2.setNumThreads(4)
            self._yolo_loaded = True
            logger.info("YOLO yolov8n loaded on CPU with imgsz=640 for small object detection")
        except Exception as e:
            logger.warning("YOLO not available: %s", e)
            self._yolo = None
            self._yolo_loaded = True

    def _run_yolo(self, frame: np.ndarray) -> List[Dict]:
        """
        Run YOLO at imgsz=640 for proper small object detection.
        Applies post-processing remapping to fix COCO misclassifications.
        conf=0.25 catches small/distant objects.
        """
        if self._yolo is None:
            return []
        try:
            results = self._yolo.predict(
                source=frame,
                conf=0.25,
                iou=0.45,
                imgsz=640,
                verbose=False,
                stream=False,
            )
            detections = []
            if not results:
                return detections
            for box in results[0].boxes:
                cls_idx = int(box.cls[0].item())
                raw_cls = self._yolo.names[cls_idx]
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                bbox = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

                # Apply remapping to fix misclassifications (toothbrush→pen, etc.)
                cls_name = _remap_class(raw_cls, bbox, frame.shape)

                behaviour = _behaviour_from_class(cls_name)
                detections.append({
                    "class": cls_name,
                    "raw_class": raw_cls,   # Keep original for debugging
                    "confidence": round(conf, 3),
                    "behaviour": behaviour,
                    "threat": _is_threat(cls_name),
                    "potential_threat": _is_potential_threat(cls_name),
                    "bbox": bbox,
                })
            return detections
        except Exception as e:
            logger.error("YOLO inference error: %s", e)
            return []

    def _run_face_analysis(self, frame: np.ndarray) -> List[Dict]:
        """Run DeepFace on a downscaled frame for speed."""
        try:
            from deepface import DeepFace
            # Downscale to 320px wide for faster face analysis
            h, w = frame.shape[:2]
            scale = 320 / w if w > 320 else 1.0
            small = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1.0 else frame

            results = DeepFace.analyze(
                img_path=small,
                actions=["age", "gender", "emotion"],   # skip "race" — saves ~30ms
                enforce_detection=False,
                detector_backend="opencv",              # opencv is fastest backend
                silent=True,
            )
            faces = []
            if not isinstance(results, list):
                results = [results]
            for r in results:
                region = r.get("region", {})
                # Scale bbox back to original frame size
                inv = 1.0 / scale
                dominant_emotion = r.get("dominant_emotion", "neutral")
                gender = r.get("dominant_gender", r.get("gender", "Unknown"))
                age = r.get("age", 0)
                emotion_behaviour = {
                    "angry":    "AGGRESSIVE",
                    "fear":     "FEARFUL",
                    "happy":    "CALM",
                    "sad":      "DISTRESSED",
                    "surprise": "ALERT",
                    "neutral":  "CALM",
                    "disgust":  "AGITATED",
                }.get(dominant_emotion.lower(), "UNKNOWN")
                faces.append({
                    "age": int(age),
                    "gender": gender if isinstance(gender, str) else list(gender.keys())[0],
                    "emotion": dominant_emotion,
                    "behaviour": emotion_behaviour,
                    "bbox": {
                        "x1": int(region.get("x", 0) * inv),
                        "y1": int(region.get("y", 0) * inv),
                        "x2": int((region.get("x", 0) + region.get("w", 0)) * inv),
                        "y2": int((region.get("y", 0) + region.get("h", 0)) * inv),
                    },
                })
            return faces
        except Exception as e:
            logger.debug("Face analysis skipped: %s", e)
            return []

    def _annotate_frame(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        faces: List[Dict],
    ) -> np.ndarray:
        """Draw bounding boxes and labels on the frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        for det in detections:
            bb = det["bbox"]
            colour = _COLOURS.get(det["behaviour"], _COLOURS["UNKNOWN"])
            # Use red for threats, orange for potential threats
            if det.get("threat"):
                colour = (0, 0, 255)
            elif det.get("potential_threat"):
                colour = (0, 100, 255)

            cv2.rectangle(annotated, (bb["x1"], bb["y1"]), (bb["x2"], bb["y2"]), colour, 2)

            # Show corrected label; if remapped, show original in brackets
            display_cls = det["class"].upper()
            raw_cls = det.get("raw_class", det["class"])
            if raw_cls != det["class"]:
                display_cls = f"{det['class'].upper()} [was:{raw_cls}]"

            label = f"{display_cls} {det['confidence']:.0%} | {det['behaviour']}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            ly = max(bb["y1"] - 6, lh + 4)
            cv2.rectangle(annotated, (bb["x1"], ly - lh - 4), (bb["x1"] + lw + 4, ly), colour, -1)
            cv2.putText(annotated, label, (bb["x1"] + 2, ly - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)

            if det.get("threat"):
                cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), (0, 0, 255), 4)

        for face in faces:
            bb = face["bbox"]
            colour = _COLOURS["FACE_DETECTED"]
            cv2.rectangle(annotated, (bb["x1"], bb["y1"]), (bb["x2"], bb["y2"]), colour, 2)
            label = f"Age:{face['age']} {face['gender']} | {face['emotion'].upper()} ({face['behaviour']})"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            ly = bb["y2"] + lh + 6
            if ly > h:
                ly = bb["y1"] - 4
            cv2.rectangle(annotated, (bb["x1"], ly - lh - 2), (bb["x1"] + lw + 4, ly + 2), colour, -1)
            cv2.putText(annotated, label, (bb["x1"] + 2, ly),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        cv2.putText(annotated, f"NSG VisionAI | WEBCAM | {ts}",
                    (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, f"FPS:{self._fps:.1f} | Objects:{len(detections)} | Faces:{len(faces)}",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

        return annotated

    def _capture_loop(self) -> None:
        """
        Dedicated capture thread — reads frames from camera as fast as possible.
        Stores only the LATEST frame so YOLO always gets a fresh one.
        This eliminates the camera read() blocking the inference thread.
        """
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                with self._capture_lock:
                    self._latest_raw_frame = frame
            # No sleep — read as fast as camera allows (30fps hardware limit)

    def _loop(self) -> None:
        """YOLO inference loop — reads from capture buffer, never waits for camera."""
        self._load_yolo()

        fps_counter = 0
        fps_start = time.monotonic()
        frame_idx = 0
        face_trigger = 0

        while self._running:
            # Get latest frame from capture thread (non-blocking)
            with self._capture_lock:
                frame = self._latest_raw_frame
                self._latest_raw_frame = None  # Consume it

            if frame is None:
                time.sleep(0.005)  # Wait briefly for capture thread
                continue

            frame_idx += 1
            fps_counter += 1
            face_trigger += 1

            # Update FPS every second
            elapsed = time.monotonic() - fps_start
            if elapsed >= 1.0:
                self._fps = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.monotonic()

            # YOLO every frame at full 640px resolution
            detections = self._run_yolo(frame)

            # Queue frame for face analysis every 20 frames
            if face_trigger >= 20:
                face_trigger = 0
                with self._face_lock:
                    self._pending_face_frame = frame.copy()

            # Get latest face results
            with self._face_lock:
                current_faces = list(self._latest_faces)

            # Annotate and encode
            annotated = self._annotate_frame(frame, detections, current_faces)
            ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
            if ok:
                with self._lock:
                    self._latest_jpeg = buf.tobytes()
                    self._latest_detections = detections
                    self._frame_count = frame_idx

    def _face_loop(self) -> None:
        """Face analysis loop — runs in separate thread, processes queued frames."""
        while self._running:
            frame = None
            with self._face_lock:
                if self._pending_face_frame is not None:
                    frame = self._pending_face_frame
                    self._pending_face_frame = None

            if frame is not None:
                faces = self._run_face_analysis(frame)
                with self._face_lock:
                    self._latest_faces = faces
            else:
                time.sleep(0.05)  # Wait for next queued frame


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_detector = WebcamDetector()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/start", status_code=status.HTTP_200_OK,
             summary="Start webcam detection",
             description="Start laptop webcam with YOLO + face analysis (OPERATOR+)")
async def start_webcam(
    camera_index: int = 0,
    current_user=Depends(require_operator),
):
    """Start the webcam capture and AI detection pipeline."""
    if _detector.is_running:
        return {"status": "already_running", "message": "Webcam detection is already active"}

    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, _detector.start, camera_index)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot open camera at index {camera_index}. Check that no other app is using it.",
        )
    return {"status": "started", "camera_index": camera_index}


@router.post("/stop", status_code=status.HTTP_200_OK,
             summary="Stop webcam detection",
             description="Stop the webcam capture (OPERATOR+)")
async def stop_webcam(current_user=Depends(require_operator)):
    """Stop the webcam capture and release the camera."""
    if not _detector.is_running:
        return {"status": "not_running"}
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _detector.stop)
    return {"status": "stopped"}


@router.get("/status", status_code=status.HTTP_200_OK,
            summary="Webcam status",
            description="Check if webcam detection is running (OPERATOR+)")
async def webcam_status(current_user=Depends(require_operator)):
    return {
        "running": _detector.is_running,
        "frame_count": _detector._frame_count,
        "fps": round(_detector._fps, 1),
        "started_at": _detector._started_at,
    }


@router.get("/snapshot",
            summary="Latest annotated frame",
            description="Get the latest annotated JPEG frame. Accepts token as query param.")
async def get_snapshot(token: Optional[str] = None, current_user=Depends(require_operator)):
    """Return the latest annotated frame as a JPEG image."""
    if not _detector.is_running:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Webcam not running. POST /webcam/start first.")
    jpeg = _detector.get_latest_jpeg()
    if jpeg is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="No frame available yet.")
    return Response(content=jpeg, media_type="image/jpeg",
                    headers={"Cache-Control": "no-cache, no-store"})


@router.get("/detections",
            summary="Latest detection results",
            description="Get latest YOLO + face analysis results as JSON (OPERATOR+)")
async def get_detections(current_user=Depends(require_operator)):
    """Return the latest detection results as JSON."""
    if not _detector.is_running:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Webcam not running. POST /webcam/start first.")
    return _detector.get_latest_detections()


@router.get("/stream",
            summary="MJPEG live stream",
            description="Live annotated MJPEG stream from webcam. Accepts token as query param for browser <img> use.")
async def stream_webcam(token: Optional[str] = None):
    """
    Stream annotated webcam frames as multipart/x-mixed-replace MJPEG.
    Accepts JWT token as query param so browser <img> tags can load it.
    """
    # Validate token from query param (since img tags can't send headers)
    if token:
        try:
            from app.core.security import decode_token, verify_token_type
            payload = decode_token(token)
            if not verify_token_type(payload, "access"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not _detector.is_running:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Webcam not running. POST /webcam/start first.")

    async def frame_generator():
        last_sent: Optional[bytes] = None
        while _detector.is_running:
            jpeg = _detector.get_latest_jpeg()
            # Only send if we have a new frame
            if jpeg and jpeg is not last_sent:
                last_sent = jpeg
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            await asyncio.sleep(0.02)  # 50fps push rate — browser renders as fast as frames arrive

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store"},
    )
