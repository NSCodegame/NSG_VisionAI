"""
LSTMAnomalyWorker — Phase 12, Task 12.1

Detects anomalous movement patterns in person trajectories using an LSTM Autoencoder.
Computes reconstruction error to identify outliers (loitering, running, etc.).
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from app.core.config import settings

logger = logging.getLogger(__name__)

class LSTMAutoencoder(nn.Module):
    """
    Standard LSTM Autoencoder for sequence reconstruction.
    """
    def __init__(self, input_dim: int, hidden_dim: int):
        super(LSTMAutoencoder, self).__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_dim)
        _, (hidden, _) = self.encoder(x)
        # hidden shape: (1, batch, hidden_dim)
        
        # Repeat hidden state for decoder
        seq_len = x.size(1)
        hidden_repeated = hidden.repeat(seq_len, 1, 1).transpose(0, 1)
        
        output, _ = self.decoder(hidden_repeated)
        return output

class AnomalyDetectionWorker:
    """
    Worker for identifying anomalous trajectories.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(settings.lstm_model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.seq_len = settings.lstm_sequence_length
        self.threshold = settings.lstm_anomaly_threshold
        
        # Dimensions: x, y, dx, dy (velocity)
        self.input_dim = 4
        self.hidden_dim = 64
        
        logger.info("Initializing AnomalyDetectionWorker (LSTM Autoencoder) on %s", self.device)
        self.model = LSTMAutoencoder(self.input_dim, self.hidden_dim).to(self.device)
        
        try:
            # In production, we'd load weights here
            # self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.eval()
            logger.info("Anomaly detection models initialized (using default/mock weights for development)")
        except Exception as e:
            logger.warning("Could not load LSTM weights from %s: %s", self.model_path, e)

    def _preprocess(self, points: List[Tuple[float, float]]) -> torch.Tensor:
        """
        Convert raw percentage coordinates to normalized sequence [x, y, dx, dy].
        """
        pts = np.array(points)
        # Calculate velocities
        velocities = np.diff(pts, axis=0, prepend=[pts[0]])
        
        # Combine [x, y, dx, dy]
        features = np.hstack([pts, velocities])
        
        # Ensure exact sequence length
        if len(features) > self.seq_len:
            features = features[-self.seq_len:]
        elif len(features) < self.seq_len:
            # Pad with zeros if necessary (though we usually wait for 30 points)
            padding = np.zeros((self.seq_len - len(features), self.input_dim))
            features = np.vstack([padding, features])
            
        return torch.FloatTensor(features).unsqueeze(0).to(self.device)

    def compute_anomaly_score(self, points: List[Tuple[float, float]]) -> float:
        """
        Compute anomaly score based on MSE reconstruction error.
        
        Returns:
            Float score (0.0 - 1.0)
        """
        if len(points) < 5: # Not enough data for a sequence
            return 0.0

        x = self._preprocess(points)
        
        with torch.no_grad():
            reconstructed = self.model(x)
            # Compute Mean Squared Error
            loss = nn.functional.mse_loss(reconstructed, x).item()
            
        # Scale loss to a 0.0 - 1.0 score (sigmoid-like scaling)
        # Using a simple exponential decay for normalization around the threshold
        score = 1.0 / (1.0 + np.exp(-10 * (loss - self.threshold/2)))
        return float(score)

_anomaly_worker: Optional[AnomalyDetectionWorker] = None

def get_anomaly_worker() -> AnomalyDetectionWorker:
    """Singleton instance getter."""
    global _anomaly_worker
    if _anomaly_worker is None:
        _anomaly_worker = AnomalyDetectionWorker()
    return _anomaly_worker
