"""NanoRecall — 100% Private, Zero-Cloud Desktop Memory & Screen Search Engine.

Hardware-Accelerated bare-metal FASM SIMD (AVX2+FMA / SSE2) Engine.
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

__version__ = "0.1.6"
__author__ = "eminsk (M_N_Nik@yahoo.com)"
__license__ = "MIT"

from nanorecall.capture import FrameCaptureResult, ScreenCaptureEngine
from nanorecall.fasm import FASMHardwareEngine, default_engine, is_fasm_available, simd_backend
from nanorecall.mcp_server import NanoRecallMCPServer
from nanorecall.memory import FastFeatureEmbedder, MemoryMatch, RecallMemory
from nanorecall.ocr import OCREngine, OCRResult, TextBlock
from nanorecall.privacy import DEFAULT_BLACKLIST_KEYWORDS, PrivacyShield

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
    "FASMHardwareEngine",
    "is_fasm_available",
    "simd_backend",
    "default_engine",
    "DEFAULT_BLACKLIST_KEYWORDS",
    "NanoRecallMCPServer",
    "__version__",
]
