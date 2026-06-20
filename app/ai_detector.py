"""AI detection pipeline using YOLO vehicle detection with optional OpenALPR."""
import json
import logging
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Represents a detected vehicle."""

    license_plate: Optional[str]
    vehicle_type: Optional[str]
    color: Optional[str]
    make: Optional[str]
    model: Optional[str]
    confidence: float
    bbox: Tuple[int, int, int, int]
    timestamp: str


class ALPRDetector:
    """Optional OpenALPR integration via the `alpr` CLI."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.alpr_binary = shutil.which("alpr") if enabled else None
        if self.enabled and not self.alpr_binary:
            logger.info("OpenALPR CLI not found; license-plate recognition is disabled")
        elif self.alpr_binary:
            logger.info("OpenALPR CLI detected and enabled")

    def recognize(self, image: np.ndarray) -> Optional[str]:
        """Recognize the most likely license plate from an image crop."""
        if not self.alpr_binary:
            return None

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            cv2.imwrite(tmp_path, image)

            result = subprocess.run(
                [self.alpr_binary, "-j", "-n", "1", tmp_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=1.5,
            )
            if result.returncode != 0:
                return None

            payload = json.loads(result.stdout or "{}")
            results = payload.get("results", [])
            if not results:
                return None

            candidates = results[0].get("candidates", [])
            if not candidates:
                return None
            return candidates[0].get("plate")
        except Exception as e:
            logger.debug(f"ALPR recognition failed: {e}")
            return None
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass


class VehicleDetector:
    """Vehicle detector backed by Ultralytics YOLO models."""

    VEHICLE_LABELS = {"car", "truck", "bus", "motorbike", "motorcycle"}

    def __init__(self, model_path: Optional[str] = None, model_name: str = "yolo11n.pt"):
        self.model = None
        self.names: Dict[int, str] = {}
        self.model_path = model_path
        self.model_name = model_name
        self._initialize()

    def _initialize(self):
        try:
            from ultralytics import YOLO

            source = self.model_path or self.model_name
            self.model = YOLO(source)
            self.names = self.model.names
            logger.info(f"YOLO model loaded: {source}")
        except Exception as e:
            logger.error(
                f"YOLO model unavailable ({e}). Install ultralytics and provide a model to enable AI detection."
            )
            self.model = None

    def detect(self, frame: np.ndarray, confidence_threshold: float) -> List[Detection]:
        if self.model is None:
            return []

        try:
            results = self.model.predict(
                source=frame,
                verbose=False,
                conf=confidence_threshold,
                classes=None,
                device=0,
            )
        except Exception as e:
            logger.debug(f"GPU inference failed, retrying with auto device: {e}")
            results = self.model.predict(
                source=frame,
                verbose=False,
                conf=confidence_threshold,
            )

        detections: List[Detection] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                cls_idx = int(box.cls.item())
                label = str(self.names.get(cls_idx, str(cls_idx))).lower()
                if label not in self.VEHICLE_LABELS:
                    continue

                conf = float(box.conf.item())
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                detections.append(
                    Detection(
                        license_plate=None,
                        vehicle_type=label,
                        color=None,
                        make=None,
                        model=None,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        timestamp=now,
                    )
                )
        return detections


class AIDetector:
    """Background AI detection engine."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "yolo11n.pt",
        alpr_enabled: bool = True,
        inference_fps: int = 5,
        confidence_threshold: float = 0.5,
    ):
        self.vehicle_detector = VehicleDetector(model_path=model_path, model_name=model_name)
        self.alpr = ALPRDetector(enabled=alpr_enabled)
        self.inference_fps = max(1, int(inference_fps))
        self.confidence_threshold = confidence_threshold

        self.running = False
        self.thread = None

        self.inference_interval = 1.0 / self.inference_fps
        self.last_inference_time = 0.0

        self.current_frame = None
        self.current_frame_lock = threading.Lock()

        self.latest_detections: List[Detection] = []
        self.detections_lock = threading.Lock()

        self.on_detections_callback: Optional[Callable] = None

    def set_input_frame(self, frame: np.ndarray):
        """Queue a frame for inference."""
        with self.current_frame_lock:
            self.current_frame = frame.copy()

    def start(self) -> bool:
        if self.running:
            return False
        self.running = True
        self.thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.thread.start()
        logger.info("AI detector started")
        return True

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("AI detector stopped")

    def _inference_loop(self):
        while self.running:
            time_since_last = time.time() - self.last_inference_time
            if time_since_last < self.inference_interval:
                time.sleep(self.inference_interval - time_since_last)
            self.last_inference_time = time.time()

            with self.current_frame_lock:
                if self.current_frame is None:
                    continue
                frame = self.current_frame.copy()

            try:
                detections = self._run_inference(frame)
                with self.detections_lock:
                    self.latest_detections = detections
                if self.on_detections_callback and detections:
                    self.on_detections_callback(detections)
            except Exception as e:
                logger.error(f"Error in inference loop: {e}")

    def _run_inference(self, frame: np.ndarray) -> List[Detection]:
        detections = self.vehicle_detector.detect(frame, self.confidence_threshold)
        if not detections:
            return []

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            h, w = frame.shape[:2]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            if x2 <= x1 or y2 <= y1:
                continue

            vehicle_crop = frame[y1:y2, x1:x2]
            plate = self.alpr.recognize(vehicle_crop)
            if plate:
                det.license_plate = plate

        return detections

    def get_latest_detections(self) -> List[Detection]:
        with self.detections_lock:
            return self.latest_detections.copy()

    def set_detections_callback(self, callback: Callable):
        self.on_detections_callback = callback

    def get_stats(self) -> Dict:
        with self.detections_lock:
            return {
                "latest_detections": len(self.latest_detections),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
