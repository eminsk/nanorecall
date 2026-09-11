"""
NanoRecall — 100% Private, Zero-Cloud Desktop Memory & Screen Search Engine
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from nanorecall.capture import FrameCaptureResult, ScreenCaptureEngine
from nanorecall.memory import FastFeatureEmbedder, MemoryMatch, RecallMemory
from nanorecall.ocr import OCREngine, OCRResult, TextBlock
from nanorecall.privacy import DEFAULT_BLACKLIST_KEYWORDS, PrivacyShield

__version__ = "0.1.0"
__author__ = "eminsk (M_N_Nik@yahoo.com)"
__license__ = "MIT"

__all__ = [
    "PrivacyShield",
    "ScreenCaptureEngine",
    "FrameCaptureResult",
    "OCREngine",
    "OCRResult",
    "TextBlock",
    "RecallMemory",
    "MemoryMatch",
    "FastFeatureEmbedder",
    "DEFAULT_BLACKLIST_KEYWORDS",
    "__version__",
]
