"""Application configuration using Pydantic Settings"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment-based configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="NSG VisionAI Platform", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database Settings
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="nsg_visionai", description="PostgreSQL database name")
    postgres_user: str = Field(default="nsg_admin", description="PostgreSQL user")
    postgres_password: str = Field(default="change_me_in_production", description="PostgreSQL password")

    @property
    def database_url(self) -> str:
        """Construct async database URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis Settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="change_me_in_production", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # MinIO Settings
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    minio_access_key: str = Field(default="nsg_admin", description="MinIO access key")
    minio_secret_key: str = Field(default="change_me_in_production", description="MinIO secret key")
    minio_bucket_name: str = Field(default="nsg-visionai", description="MinIO bucket name")
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")
    minio_region: str = Field(default="us-east-1", description="MinIO region")

    # JWT Settings
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    jwt_access_token_expire_hours: int = Field(default=8, description="Access token expiration (hours)")
    jwt_refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration (days)")
    jwt_private_key_path: Path = Field(
        default=Path("./keys/private_key.pem"), description="JWT private key path"
    )
    jwt_public_key_path: Path = Field(
        default=Path("./keys/public_key.pem"), description="JWT public key path"
    )

    @property
    def jwt_private_key(self) -> str:
        """Load JWT private key"""
        if self.jwt_private_key_path.exists():
            return self.jwt_private_key_path.read_text()
        return ""

    @property
    def jwt_public_key(self) -> str:
        """Load JWT public key"""
        if self.jwt_public_key_path.exists():
            return self.jwt_public_key_path.read_text()
        return ""

    # Encryption Settings
    encryption_master_key: str = Field(
        default="change_me_to_64_char_hex_string_in_production_00000000000000",
        description="Master encryption key (64 hex chars)",
    )
    video_encryption_algorithm: str = Field(default="AES-256-GCM", description="Video encryption algorithm")

    @field_validator("encryption_master_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate encryption key length"""
        if len(v) != 64:
            raise ValueError("Encryption master key must be 64 characters (32 bytes hex)")
        return v

    # ML Model Paths
    yolo_model_path: Path = Field(default=Path("./models/yolov8x.pt"), description="YOLOv8 model path")
    yolo_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="YOLO confidence threshold")
    yolo_nms_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="YOLO NMS threshold")
    yolo_input_size: int = Field(default=640, description="YOLO input size")
    yolo_batch_size: int = Field(default=4, description="YOLO batch size")

    retinaface_model_path: Path = Field(
        default=Path("./models/retinaface_resnet50.pth"), description="RetinaFace model path"
    )
    retinaface_confidence_threshold: float = Field(
        default=0.90, ge=0.0, le=1.0, description="RetinaFace confidence threshold"
    )

    arcface_model_path: Path = Field(
        default=Path("./models/arcface_resnet100.pth"), description="ArcFace model path"
    )
    arcface_embedding_size: int = Field(default=512, description="ArcFace embedding size")
    face_match_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Face match threshold")

    bytetrack_track_buffer: int = Field(default=30, description="ByteTrack track buffer")
    bytetrack_match_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="ByteTrack match threshold")
    bytetrack_reid_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="ByteTrack Re-ID threshold")

    lstm_model_path: Path = Field(default=Path("./models/lstm_anomaly.pth"), description="LSTM model path")
    lstm_sequence_length: int = Field(default=30, description="LSTM sequence length")
    lstm_anomaly_threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="LSTM anomaly threshold")

    # Video Stream Settings
    video_stream_fps_ai: int = Field(default=5, description="Frame rate for AI processing")
    video_stream_fps_display: int = Field(default=25, description="Frame rate for display")
    video_stream_buffer_size: int = Field(default=100, description="Video stream buffer size")
    video_stream_reconnect_attempts: int = Field(default=5, description="Stream reconnection attempts")
    video_stream_reconnect_delay: int = Field(default=5, description="Stream reconnection delay (seconds)")
    video_stream_connection_timeout: int = Field(default=10, description="Stream connection timeout (seconds)")

    # Alert Settings
    alert_deduplication_window: int = Field(default=30, description="Alert deduplication window (seconds)")
    alert_p1_auto_resolve: bool = Field(default=False, description="Auto-resolve P1_CRITICAL alerts")

    # Video Archival Settings
    video_segment_duration: int = Field(default=600, description="Video segment duration (seconds)")
    video_retention_days: int = Field(default=30, description="Video retention period (days)")
    video_flagged_retention_permanent: bool = Field(
        default=True, description="Permanent retention for flagged segments"
    )
    video_codec: str = Field(default="h264", description="Video codec")
    video_compression_quality: int = Field(default=23, description="Video compression quality (CRF)")

    # Security Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"], description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    rate_limit_login: int = Field(default=10, description="Login rate limit (requests per minute)")
    account_lockout_attempts: int = Field(default=5, description="Account lockout after N failed attempts")
    account_lockout_duration: int = Field(default=1800, description="Account lockout duration (seconds)")
    password_bcrypt_rounds: int = Field(default=12, description="Bcrypt rounds for password hashing")

    # GPU Settings
    cuda_visible_devices: str = Field(default="0,1", description="CUDA visible devices")
    gpu_memory_fraction: float = Field(default=0.8, ge=0.1, le=1.0, description="GPU memory fraction per worker")

    # IP Camera Settings
    ip_camera_default_port: int = Field(default=554, description="Default RTSP port for IP cameras")
    ip_camera_default_username: str = Field(default="admin", description="Default username for IP cameras")
    ip_camera_default_password: str = Field(default="", description="Default password for IP cameras")
    ip_camera_onvif_port: int = Field(default=80, description="Default ONVIF HTTP port")
    ip_camera_discovery_timeout: int = Field(default=3, description="Timeout in seconds for camera discovery ping")
    ip_camera_discovery_subnet: str = Field(
        default="192.168.1.0/24",
        description="Default subnet to scan for IP cameras (CIDR notation)",
    )
    ip_camera_stream_paths: list[str] = Field(
        default=[
            "/stream1",
            "/live",
            "/h264Preview_01_main",
            "/Streaming/Channels/101",
            "/cam/realmonitor?channel=1&subtype=0",
            "/axis-media/media.amp",
            "/video1",
            "/live/ch00_0",
        ],
        description="Common RTSP stream path patterns to probe during discovery",
    )

    def validate_on_startup(self) -> None:
        """Validate critical configuration on application startup"""
        errors = []

        # Check JWT keys exist
        if not self.jwt_private_key_path.exists():
            errors.append(f"JWT private key not found: {self.jwt_private_key_path}")
        if not self.jwt_public_key_path.exists():
            errors.append(f"JWT public key not found: {self.jwt_public_key_path}")

        # Check encryption key in production
        if self.environment == "production":
            if "change_me" in self.encryption_master_key.lower():
                errors.append("Encryption master key must be changed in production")
            if "change_me" in self.postgres_password.lower():
                errors.append("PostgreSQL password must be changed in production")
            if "change_me" in self.redis_password.lower():
                errors.append("Redis password must be changed in production")
            if "change_me" in self.minio_secret_key.lower():
                errors.append("MinIO secret key must be changed in production")

        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
