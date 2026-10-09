"""NanoRecall FASM Hardware Assembly Acceleration Backend.

Direct bare-metal AVX2+FMA (x86-64) and SSE2 (x86 32-bit) SIMD acceleration
for screen differencing, perceptual hashing, privacy masking, and episodic memory search.
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from __future__ import annotations

import ctypes
import math
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, Union

try:
    import numpy as np
except (ImportError, ModuleNotFoundError):
    np = None

_FASM_LIB: Optional[ctypes.CDLL] = None
_FASM_ISA: str = "Pure Python (Hardware FASM Engine Unavailable)"


def _bind_fasm_library(lib: ctypes.CDLL) -> ctypes.CDLL:
    """Bind CTypes signatures to the loaded FASM shared library."""
    if hasattr(lib, "nanorecall_version"):
        lib.nanorecall_version.argtypes = []
        lib.nanorecall_version.restype = ctypes.c_int

    if hasattr(lib, "nanorecall_simd_isa"):
        lib.nanorecall_simd_isa.argtypes = []
        lib.nanorecall_simd_isa.restype = ctypes.c_char_p

    if hasattr(lib, "nanorecall_frame_diff_f32"):
        lib.nanorecall_frame_diff_f32.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
        ]
        lib.nanorecall_frame_diff_f32.restype = ctypes.c_float

    if hasattr(lib, "nanorecall_frame_diff_u8"):
        lib.nanorecall_frame_diff_u8.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
        ]
        lib.nanorecall_frame_diff_u8.restype = ctypes.c_float

    if hasattr(lib, "nanorecall_hamming_dist_u64"):
        lib.nanorecall_hamming_dist_u64.argtypes = [
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.c_size_t,
        ]
        lib.nanorecall_hamming_dist_u64.restype = ctypes.c_uint64

    if hasattr(lib, "nanorecall_vector_dot"):
        lib.nanorecall_vector_dot.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
        ]
        lib.nanorecall_vector_dot.restype = ctypes.c_float

    if hasattr(lib, "nanorecall_cosine_similarity"):
        lib.nanorecall_cosine_similarity.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
        ]
        lib.nanorecall_cosine_similarity.restype = ctypes.c_float

    if hasattr(lib, "nanorecall_vector_normalize"):
        lib.nanorecall_vector_normalize.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
        ]
        lib.nanorecall_vector_normalize.restype = ctypes.c_float

    if hasattr(lib, "nanorecall_batch_search_cosine"):
        lib.nanorecall_batch_search_cosine.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_float),
        ]
        lib.nanorecall_batch_search_cosine.restype = ctypes.c_int

    if hasattr(lib, "nanorecall_mask_rect_rgba"):
        lib.nanorecall_mask_rect_rgba.argtypes = [
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        lib.nanorecall_mask_rect_rgba.restype = ctypes.c_int

    return lib


def _find_and_load_fasm_lib() -> Optional[ctypes.CDLL]:
    """Locates and loads the native hardware SIMD/FASM library (Windows/Linux/macOS)."""
    global _FASM_ISA

    env_path = os.environ.get("NANORECALL_SIMD_LIB") or os.environ.get("NANORECALL_FASM_LIB")
    if env_path and Path(env_path).exists():
        try:
            lib = ctypes.CDLL(env_path)
            bound = _bind_fasm_library(lib)
            if hasattr(bound, "nanorecall_simd_isa"):
                _FASM_ISA = bound.nanorecall_simd_isa().decode("utf-8", errors="replace")
            return bound
        except Exception:
            pass

    is_64bit = sys.maxsize > 2**32
    if sys.platform.startswith("win"):
        target_names = ["nanorecall64.dll"] if is_64bit else ["nanorecall32.dll"]
    elif sys.platform.startswith("darwin"):
        target_names = ["libnanorecall.dylib", "libnanorecall64.dylib"]
    else:
        # Linux / POSIX
        target_names = (
            ["libnanorecall64.so", "nanorecall64.so", "libnanorecall.so"]
            if is_64bit
            else ["libnanorecall32.so", "nanorecall32.so", "libnanorecall.so"]
        )

    pkg_dir = Path(__file__).resolve().parent
    search_dirs = [
        pkg_dir,
        pkg_dir.parent,
        pkg_dir.parent / "asm",
        pkg_dir.parent.parent / "asm",
        Path(r"C:\proekts\nanorecall\asm"),
        Path(r"C:\proekts\nanorecall\src\nanorecall"),
        Path("/usr/local/lib"),
        Path("/tmp"),
        Path.cwd(),
    ]

    for d in search_dirs:
        for name in target_names:
            cand = d / name
            if cand.exists():
                try:
                    lib = ctypes.CDLL(str(cand))
                    bound_lib = _bind_fasm_library(lib)
                    if hasattr(bound_lib, "nanorecall_simd_isa"):
                        _FASM_ISA = bound_lib.nanorecall_simd_isa().decode("utf-8", errors="replace")
                    return bound_lib
                except Exception:
                    continue

    # On-demand compilation on Linux/macOS if gcc/clang and kernel source are available
    if not sys.platform.startswith("win"):
        try:
            import shutil
            import subprocess

            cc = shutil.which("gcc") or shutil.which("clang")
            if cc:
                c_candidates = [
                    pkg_dir / "nanorecall_kernel.c",
                    pkg_dir.parent / "asm" / "nanorecall_kernel.c",
                    pkg_dir.parent.parent / "asm" / "nanorecall_kernel.c",
                    Path(r"/content/nanorecall/asm/nanorecall_kernel.c"),
                ]
                src_c = next((c for c in c_candidates if c.exists()), None)
                if src_c:
                    out_so = Path("/tmp") / target_names[0]
                    cmd = [cc, "-O3", "-shared", "-fPIC", "-mavx2", "-mfma", "-ffast-math", str(src_c), "-o", str(out_so), "-lm"]
                    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0 and out_so.exists():
                        lib = ctypes.CDLL(str(out_so))
                        bound_lib = _bind_fasm_library(lib)
                        if hasattr(bound_lib, "nanorecall_simd_isa"):
                            _FASM_ISA = bound_lib.nanorecall_simd_isa().decode("utf-8", errors="replace")
                        return bound_lib
        except Exception:
            pass

    return None


def get_fasm_library() -> Optional[ctypes.CDLL]:
    """Return the cached FASM shared library instance, or None if unavailable."""
    global _FASM_LIB
    if _FASM_LIB is None:
        _FASM_LIB = _find_and_load_fasm_lib()
    return _FASM_LIB


def is_fasm_available() -> bool:
    """Return True if hardware FASM microkernel engine is available and loaded."""
    return get_fasm_library() is not None


def simd_backend() -> str:
    """Return the active hardware acceleration backend string."""
    get_fasm_library()
    return _FASM_ISA


class FASMHardwareEngine:
    """High-level hardware-accelerated screen differencing, embedding and privacy engine."""

    def __init__(self) -> None:
        self.lib = get_fasm_library()

    @property
    def is_hardware_accelerated(self) -> bool:
        return self.lib is not None

    @property
    def isa(self) -> str:
        return simd_backend()

    def frame_diff_f32(self, a: Sequence[float], b: Sequence[float]) -> float:
        """Compute mean absolute difference between two float sequences."""
        count = min(len(a), len(b))
        if count == 0:
            return 0.0

        if self.lib is not None and hasattr(self.lib, "nanorecall_frame_diff_f32"):
            if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                a_arr = np.ascontiguousarray(a[:count], dtype=np.float32)
                b_arr = np.ascontiguousarray(b[:count], dtype=np.float32)
                pa = a_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                pb = b_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            else:
                c_arr_type = ctypes.c_float * count
                pa = c_arr_type(*(float(x) for x in a[:count]))
                pb = c_arr_type(*(float(x) for x in b[:count]))
            return float(self.lib.nanorecall_frame_diff_f32(pa, pb, count))

        # Pure-Python fallback
        if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            return float(np.mean(np.abs(a[:count] - b[:count])))
        return sum(abs(x - y) for x, y in zip(a[:count], b[:count])) / count

    def frame_diff_u8(self, a: Union[bytes, bytearray, Sequence[int]], b: Union[bytes, bytearray, Sequence[int]]) -> float:
        """Compute mean absolute difference on grayscale bytes normalized to [0, 1]."""
        count = min(len(a), len(b))
        if count == 0:
            return 0.0

        if self.lib is not None and hasattr(self.lib, "nanorecall_frame_diff_u8"):
            if isinstance(a, (bytes, bytearray)) and isinstance(b, (bytes, bytearray)):
                pa = (ctypes.c_uint8 * count).from_buffer_copy(a[:count])
                pb = (ctypes.c_uint8 * count).from_buffer_copy(b[:count])
            elif np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                a_arr = np.ascontiguousarray(a[:count], dtype=np.uint8)
                b_arr = np.ascontiguousarray(b[:count], dtype=np.uint8)
                pa = a_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
                pb = b_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
            else:
                c_arr_type = ctypes.c_uint8 * count
                pa = c_arr_type(*(int(x) for x in a[:count]))
                pb = c_arr_type(*(int(x) for x in b[:count]))
            return float(self.lib.nanorecall_frame_diff_u8(pa, pb, count))

        # Pure-Python fallback
        total = sum(abs(int(x) - int(y)) for x, y in zip(a[:count], b[:count]))
        return float(total / (count * 255.0))

    def hamming_dist_u64(self, a: Sequence[int], b: Sequence[int]) -> int:
        """Compute bitwise Hamming distance across two 64-bit integer sequences."""
        count = min(len(a), len(b))
        if count == 0:
            return 0

        if self.lib is not None and hasattr(self.lib, "nanorecall_hamming_dist_u64"):
            c_arr_type = ctypes.c_uint64 * count
            pa = c_arr_type(*(int(x) for x in a[:count]))
            pb = c_arr_type(*(int(x) for x in b[:count]))
            return int(self.lib.nanorecall_hamming_dist_u64(pa, pb, count))

        # Pure-Python fallback
        return sum(bin(int(x) ^ int(y)).count("1") for x, y in zip(a[:count], b[:count]))

    def vector_dot(self, a: Sequence[float], b: Sequence[float]) -> float:
        """Vector dot product between two float vectors."""
        dim = min(len(a), len(b))
        if dim == 0:
            return 0.0

        if self.lib is not None and hasattr(self.lib, "nanorecall_vector_dot"):
            if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                a_arr = np.ascontiguousarray(a[:dim], dtype=np.float32)
                b_arr = np.ascontiguousarray(b[:dim], dtype=np.float32)
                pa = a_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                pb = b_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            else:
                c_arr_type = ctypes.c_float * dim
                pa = c_arr_type(*(float(x) for x in a[:dim]))
                pb = c_arr_type(*(float(x) for x in b[:dim]))
            return float(self.lib.nanorecall_vector_dot(pa, pb, dim))

        # Pure-Python fallback
        if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
            return float(np.dot(a[:dim], b[:dim]))
        return float(sum(float(x) * float(y) for x, y in zip(a[:dim], b[:dim])))

    def cosine_similarity(self, a: Sequence[float], b: Sequence[float]) -> float:
        """Cosine similarity between two float vectors."""
        dim = min(len(a), len(b))
        if dim == 0:
            return 0.0

        if self.lib is not None and hasattr(self.lib, "nanorecall_cosine_similarity"):
            if np is not None and isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                a_arr = np.ascontiguousarray(a[:dim], dtype=np.float32)
                b_arr = np.ascontiguousarray(b[:dim], dtype=np.float32)
                pa = a_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                pb = b_arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            else:
                c_arr_type = ctypes.c_float * dim
                pa = c_arr_type(*(float(x) for x in a[:dim]))
                pb = c_arr_type(*(float(x) for x in b[:dim]))
            return float(self.lib.nanorecall_cosine_similarity(pa, pb, dim))

        # Pure-Python fallback
        dot = sum(float(x) * float(y) for x, y in zip(a[:dim], b[:dim]))
        norm_a = math.sqrt(sum(float(x) * float(x) for x in a[:dim]))
        norm_b = math.sqrt(sum(float(y) * float(y) for y in b[:dim]))
        denom = norm_a * norm_b
        if denom <= 1e-12:
            return 0.0
        return float(dot / denom)

    def vector_normalize(self, vec: Any) -> float:
        """In-place L2 normalization of float vector, returning original norm."""
        dim = len(vec)
        if dim == 0:
            return 0.0

        if self.lib is not None and hasattr(self.lib, "nanorecall_vector_normalize"):
            if np is not None and isinstance(vec, np.ndarray):
                if not vec.flags.c_contiguous or vec.dtype != np.float32:
                    vec = np.ascontiguousarray(vec, dtype=np.float32)
                pv = vec.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                norm = float(self.lib.nanorecall_vector_normalize(pv, dim))
                return norm
            elif isinstance(vec, list):
                c_arr_type = ctypes.c_float * dim
                pv = c_arr_type(*(float(x) for x in vec))
                norm = float(self.lib.nanorecall_vector_normalize(pv, dim))
                for i in range(dim):
                    vec[i] = pv[i]
                return norm

        # Pure-Python fallback
        norm = math.sqrt(sum(float(x) * float(x) for x in vec))
        if norm > 1e-12:
            inv = 1.0 / norm
            for i in range(dim):
                vec[i] = float(vec[i]) * inv
        return norm

    def batch_search_cosine(self, query: Sequence[float], matrix: Sequence[Sequence[float]]) -> List[float]:
        """Compute cosine similarities of query against an array of matrix vectors."""
        num_vecs = len(matrix)
        if num_vecs == 0:
            return []
        dim = len(query)

        if self.lib is not None and hasattr(self.lib, "nanorecall_batch_search_cosine"):
            # Flatten matrix
            flat_mat = (ctypes.c_float * (num_vecs * dim))()
            for r, row in enumerate(matrix):
                for c, val in enumerate(row[:dim]):
                    flat_mat[r * dim + c] = float(val)

            c_q = (ctypes.c_float * dim)(*(float(x) for x in query[:dim]))
            scores = (ctypes.c_float * num_vecs)()

            self.lib.nanorecall_batch_search_cosine(c_q, flat_mat, num_vecs, dim, scores)
            return [float(scores[i]) for i in range(num_vecs)]

        # Pure-Python fallback
        return [self.cosine_similarity(query, row) for row in matrix]

    def mask_rect_rgba(
        self,
        pixels: Any,
        width: int,
        height: int,
        stride: int,
        rx: int,
        ry: int,
        rw: int,
        rh: int,
        color: int = 0xFF000000,
    ) -> int:
        """Fill RGBA rectangle bounding box with privacy color (e.g. solid black or blur)."""
        if width <= 0 or height <= 0 or rw <= 0 or rh <= 0:
            return 0

        if self.lib is not None and hasattr(self.lib, "nanorecall_mask_rect_rgba"):
            if np is not None and isinstance(pixels, np.ndarray):
                if not pixels.flags.c_contiguous or pixels.dtype != np.uint32:
                    pixels = np.ascontiguousarray(pixels, dtype=np.uint32)
                ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
                return int(self.lib.nanorecall_mask_rect_rgba(ptr, width, height, stride, rx, ry, rw, rh, color))
            elif isinstance(pixels, (list, bytearray)):
                c_arr_type = ctypes.c_uint32 * (height * stride)
                c_buf = c_arr_type(*(int(p) for p in pixels[: height * stride]))
                res = int(self.lib.nanorecall_mask_rect_rgba(c_buf, width, height, stride, rx, ry, rw, rh, color))
                for i in range(len(pixels)):
                    pixels[i] = c_buf[i]
                return res

        # Pure-Python fallback
        for y in range(max(0, ry), min(height, ry + rh)):
            row_start = y * stride
            for x in range(max(0, rx), min(width, rx + rw)):
                idx = row_start + x
                if idx < len(pixels):
                    pixels[idx] = color
        return 0


# Default global instance
default_engine = FASMHardwareEngine()


def frame_diff_f32(a: Sequence[float], b: Sequence[float]) -> float:
    return default_engine.frame_diff_f32(a, b)


def frame_diff_u8(a: Union[bytes, bytearray, Sequence[int]], b: Union[bytes, bytearray, Sequence[int]]) -> float:
    return default_engine.frame_diff_u8(a, b)


def hamming_dist_u64(a: Sequence[int], b: Sequence[int]) -> int:
    return default_engine.hamming_dist_u64(a, b)


def vector_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return default_engine.vector_dot(a, b)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return default_engine.cosine_similarity(a, b)


def vector_normalize(vec: Any) -> float:
    return default_engine.vector_normalize(vec)


def mask_rect_rgba(pixels: Any, width: int, height: int, stride: int, rx: int, ry: int, rw: int, rh: int, color: int = 0xFF000000) -> int:
    return default_engine.mask_rect_rgba(pixels, width, height, stride, rx, ry, rw, rh, color)
