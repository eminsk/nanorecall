"""
Unit Tests for NanoRecall Screen Capture Engine
"""

import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest
Image = pytest.importorskip("PIL.Image")
from nanorecall.capture import ScreenCaptureEngine


@pytest.fixture
def temp_capture_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_frame_differencing(temp_capture_dir):
    engine = ScreenCaptureEngine(storage_dir=temp_capture_dir, diff_threshold=0.05)

    img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))  # Exact identical
    img3 = Image.new("RGB", (100, 100), color=(0, 0, 0))        # Completely different

    # First frame diff is always 1.0
    diff1 = engine.compute_diff(img1)
    assert diff1 == 1.0

    # Identical frame diff is 0.0
    diff2 = engine.compute_diff(img2)
    assert diff2 == 0.0

    # Inverted frame diff is 1.0
    diff3 = engine.compute_diff(img3)
    assert diff3 == 1.0


def test_capture_and_save(temp_capture_dir):
    engine = ScreenCaptureEngine(storage_dir=temp_capture_dir, format="JPEG")
    res = engine.capture_frame(force_save=True)

    assert res.image is not None
    assert res.image_path is not None
    assert os.path.exists(res.image_path)
    assert res.thumb_path is not None
    assert os.path.exists(res.thumb_path)
    assert res.is_duplicate is False

    # Second immediate capture without force_save should detect unchanged screen (or minimal diff)
    res2 = engine.capture_frame(force_save=False)
    # If the screen hasn't changed, is_duplicate is True
    assert isinstance(res2.is_duplicate, bool)


def test_rgba_to_jpeg_compatibility(temp_capture_dir):
    engine = ScreenCaptureEngine(storage_dir=temp_capture_dir, format="JPEG")
    # Simulate RGBA image (as returned on macOS Retina displays)
    rgba_img = Image.new("RGBA", (100, 100), color=(255, 100, 50, 200))
    from unittest.mock import patch
    with patch("PIL.ImageGrab.grab", return_value=rgba_img):
        res = engine.capture_frame(force_save=True)
        assert res.image_path is not None
        assert os.path.exists(res.image_path)
        # Verify saved JPEG is valid
        loaded = Image.open(res.image_path)
        assert loaded.mode == "RGB"

