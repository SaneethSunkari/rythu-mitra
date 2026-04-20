"""Safe disease image inference wrapper with optional checkpoint loading."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_PATH = ROOT / "disease" / "weights" / "resnet18_diseases.pt"
DEFAULT_CLASS_NAMES = [
    "paddy_blast",
    "paddy_brown_spot",
    "paddy_blb",
    "turmeric_rhizome_rot",
    "turmeric_leaf_blotch",
    "maize_fall_army_worm",
    "maize_northern_leaf_blight",
]


@dataclass
class ImageQuality:
    usable: bool
    width: int
    height: int
    brightness_mean: float
    edge_strength: float
    reason: str | None = None


class DiseaseModel:
    """Load optional disease weights and run conservative predictions."""

    def __init__(
        self,
        *,
        weights_path: str | Path | None = None,
        class_names: list[str] | None = None,
    ) -> None:
        self.weights_path = Path(weights_path or os.getenv("DISEASE_MODEL_WEIGHTS") or DEFAULT_WEIGHTS_PATH)
        self.class_names = list(class_names or DEFAULT_CLASS_NAMES)
        self._model: Any = None
        self._model_loaded = False
        self._load_error = ""

    @property
    def available(self) -> bool:
        if self._model_loaded:
            return self._model is not None
        self._ensure_model_loaded()
        return self._model is not None

    @property
    def load_error(self) -> str:
        if not self._model_loaded:
            self._ensure_model_loaded()
        return self._load_error

    def assess_image_quality(self, image_bytes: bytes) -> ImageQuality:
        try:
            from PIL import Image
            import numpy as np
        except ImportError as exc:  # pragma: no cover - dependency guard
            return ImageQuality(False, 0, 0, 0.0, 0.0, reason=f"image_runtime_missing:{exc}")

        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            width, height = image.size
            gray = image.convert("L")
            arr = np.asarray(gray, dtype="float32")

        brightness_mean = float(arr.mean()) if arr.size else 0.0
        horizontal_edges = float(abs(arr[:, 1:] - arr[:, :-1]).mean()) if arr.shape[1] > 1 else 0.0
        vertical_edges = float(abs(arr[1:, :] - arr[:-1, :]).mean()) if arr.shape[0] > 1 else 0.0
        edge_strength = (horizontal_edges + vertical_edges) / 2.0

        if min(width, height) < 180:
            return ImageQuality(False, width, height, brightness_mean, edge_strength, reason="low_resolution")
        if brightness_mean < 18:
            return ImageQuality(False, width, height, brightness_mean, edge_strength, reason="too_dark")
        if brightness_mean > 245:
            return ImageQuality(False, width, height, brightness_mean, edge_strength, reason="too_bright")
        if edge_strength < 7.5:
            return ImageQuality(False, width, height, brightness_mean, edge_strength, reason="too_blurry")
        return ImageQuality(True, width, height, brightness_mean, edge_strength)

    def predict(self, image_bytes: bytes, *, crop_hint: str | None = None) -> dict:
        quality = self.assess_image_quality(image_bytes)
        if not quality.usable:
            return {
                "status": "poor_quality",
                "confidence": 0.0,
                "predicted_label": None,
                "crop_hint": crop_hint,
                "quality": quality.__dict__,
                "model_available": self.available,
                "model_source": None,
            }

        if not self.available:
            return {
                "status": "model_unavailable",
                "confidence": 0.0,
                "predicted_label": None,
                "crop_hint": crop_hint,
                "quality": quality.__dict__,
                "model_available": False,
                "model_source": None,
                "load_error": self.load_error,
            }

        tensor = self._preprocess_image(image_bytes)
        if tensor is None:
            return {
                "status": "model_unavailable",
                "confidence": 0.0,
                "predicted_label": None,
                "crop_hint": crop_hint,
                "quality": quality.__dict__,
                "model_available": False,
                "model_source": None,
                "load_error": self.load_error or "preprocess_failed",
            }

        import torch

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)
            score, index = torch.max(probs, dim=1)

        label = self.class_names[int(index.item())]
        confidence = float(score.item())

        if crop_hint and not label.startswith(f"{crop_hint}_"):
            confidence *= 0.55

        return {
            "status": "predicted",
            "confidence": confidence,
            "predicted_label": label,
            "crop_hint": crop_hint,
            "quality": quality.__dict__,
            "model_available": True,
            "model_source": str(self.weights_path),
        }

    def _ensure_model_loaded(self) -> None:
        if self._model_loaded:
            return

        self._model_loaded = True
        if not self.weights_path.exists():
            self._load_error = "weights_missing"
            self._model = None
            return

        try:
            import torch
            from torchvision import models, transforms
        except ImportError as exc:
            self._load_error = f"torch_runtime_missing:{exc}"
            self._model = None
            return

        checkpoint = torch.load(self.weights_path, map_location="cpu")
        if isinstance(checkpoint, dict) and "class_names" in checkpoint:
            self.class_names = list(checkpoint["class_names"])

        model = models.resnet18(weights=None)
        model.fc = torch.nn.Linear(model.fc.in_features, len(self.class_names))
        state_dict = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
        model.load_state_dict(state_dict)
        model.eval()

        self._model = model
        self._transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
        self._load_error = ""

    def _preprocess_image(self, image_bytes: bytes):
        try:
            from PIL import Image
        except ImportError:
            self._load_error = "pillow_missing"
            return None

        if not self.available:
            return None

        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            tensor = self._transform(image).unsqueeze(0)
        return tensor
