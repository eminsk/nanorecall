"""
Unit Tests for NanoRecall OCR Engine
"""

import pytest
from PIL import Image
from nanorecall.ocr import OCREngine, OCRResult, TextBlock


def test_ocr_engine_initialization():
    engine = OCREngine(preferred_engine="fallback")
    assert engine._backend == "fallback"

    # Extraction on blank image
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    res = engine.extract_text(img)
    assert isinstance(res, OCRResult)
    assert isinstance(res.blocks, list)


def test_text_block_dataclass():
    block = TextBlock(text="Hello NanoRecall", x=10, y=20, width=100, height=30)
    assert block.text == "Hello NanoRecall"
    assert block.x == 10
    assert block.y == 20
    assert block.width == 100
    assert block.height == 30
