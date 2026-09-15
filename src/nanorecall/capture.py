"""
NanoRecall Screen Capture & Smart Frame Differencing Engine
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None


class FrameCaptureResult:
    def __init__(
        self,
        image: Any,
        timestamp: str,
        image_path: Optional[str] = None,
        thumb_path: Optional[str] = None,
        diff_score: float = 1.0,
        is_duplicate: bool = False,
    ):
        self.image = image
        self.timestamp = timestamp
        self.image_path = image_path
        self.thumb_path = thumb_path
        self.diff_score = diff_score
        self.is_duplicate = is_duplicate


class ScreenCaptureEngine:
    """
    High-performance desktop screenshot engine equipped with perceptual
    frame differencing to eliminate duplicate frames when screen is static.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        diff_threshold: float = 0.015,  # 1.5% pixel change required
        thumb_size: Tuple[int, int] = (320, 180),
        format: str = "WEBP",
        quality: int = 80,
    ):
        if storage_dir is None:
            self.storage_dir = Path.home() / ".nanorecall" / "frames"
        else:
            self.storage_dir = Path(storage_dir)

        self.thumbs_dir = self.storage_dir / "thumbs"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

        self.diff_threshold = diff_threshold
        self.thumb_size = thumb_size
        self.format = format.upper()
        self.quality = quality
        self._last_fingerprint: Optional[np.ndarray] = None

    def _compute_fingerprint(self, img: Any) -> np.ndarray:
        """
        Calculates a fast 32x32 grayscale perceptual signature for delta comparison.
        """
        small = img.resize((32, 32), Image.Resampling.BILINEAR).convert("L")
        return np.asarray(small, dtype=np.float32) / 255.0

    def compute_diff(self, img: Any) -> float:
        """
        Returns the normalized difference (0.0 to 1.0) compared to the previous frame.
        """
        current_fp = self._compute_fingerprint(img)
        if self._last_fingerprint is None:
            self._last_fingerprint = current_fp
            return 1.0

        diff = float(np.mean(np.abs(current_fp - self._last_fingerprint)))
        return diff

    def capture_frame(self, force_save: bool = False) -> FrameCaptureResult:
        """
        Grabs current screen, evaluates diff, and saves only if screen changed.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M%S")

        # Native desktop screenshot
        try:
            raw_img = ImageGrab.grab(all_screens=False)
        except Exception:
            # Fallback black image if display unavailable (e.g. CI runner)
            raw_img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))

        diff_score = self.compute_diff(raw_img)
        is_duplicate = diff_score < self.diff_threshold and not force_save

        if is_duplicate:
            return FrameCaptureResult(
                image=raw_img,
                timestamp=timestamp,
                diff_score=diff_score,
                is_duplicate=True,
            )

        # Update last fingerprint
        self._last_fingerprint = self._compute_fingerprint(raw_img)

        # Prepare image for saving (convert RGBA/P to RGB for universal JPEG/WEBP safety)
        if raw_img.mode != "RGB":
            save_img = raw_img.convert("RGB")
        else:
            save_img = raw_img

        # Save primary frame
        ext = "webp" if self.format == "WEBP" else "jpg"
        filename = f"{timestamp}.{ext}"
        image_path = self.storage_dir / filename

        save_fmt = "WEBP" if self.format == "WEBP" else "JPEG"
        try:
            save_img.save(image_path, format=save_fmt, quality=self.quality)
        except Exception:
            # Fallback to PNG or JPEG if WEBP codec missing
            filename = f"{timestamp}.jpg"
            image_path = self.storage_dir / filename
            save_img.save(image_path, format="JPEG", quality=self.quality)

        # Save thumbnail for fast dashboard rendering
        thumb_path = self.thumbs_dir / filename
        thumb = save_img.copy()
        thumb.thumbnail(self.thumb_size, Image.Resampling.BILINEAR)
        try:
            thumb.save(thumb_path, format=save_fmt, quality=70)
        except Exception:
            thumb.save(thumb_path, format="JPEG", quality=70)


        return FrameCaptureResult(
            image=raw_img,
            timestamp=timestamp,
            image_path=str(image_path),
            thumb_path=str(thumb_path),
            diff_score=diff_score,
            is_duplicate=False,
        )
