"""Tests for NanoRecall FASM Bare-Metal Hardware SIMD Engine.

Validates AVX2+FMA (x86-64), SSE2 (x86 32-bit), and pure-Python fallbacks
under single-threaded, multi-threaded, and free-threaded environments.
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from __future__ import annotations

import concurrent.futures
import math
import pytest
from typing import List

from nanorecall.fasm import (
    FASMHardwareEngine,
    cosine_similarity,
    default_engine,
    frame_diff_f32,
    frame_diff_u8,
    hamming_dist_u64,
    is_fasm_available,
    mask_rect_rgba,
    simd_backend,
    vector_dot,
    vector_normalize,
)


def test_fasm_identification() -> None:
    backend = simd_backend()
    assert isinstance(backend, str)
    assert len(backend) > 0
    assert is_fasm_available() is True
    assert "SIMD" in backend or "AVX" in backend or "SSE" in backend


def test_frame_diff_f32_precision() -> None:
    a = [1.0] * 64
    b = [1.5] * 64
    diff = frame_diff_f32(a, b)
    assert abs(diff - 0.5) < 1e-5

    # Identical buffers
    assert frame_diff_f32(a, a) == 0.0

    # Arbitrary patterns
    v1 = [float(i) for i in range(128)]
    v2 = [float(i + 2) for i in range(128)]
    assert abs(frame_diff_f32(v1, v2) - 2.0) < 1e-5


def test_frame_diff_u8_precision() -> None:
    # 1024 bytes (32x32 frame)
    a = bytes([100] * 1024)
    b = bytes([151] * 1024)
    # diff = 51 / 255 = 0.2
    diff = frame_diff_u8(a, b)
    assert abs(diff - 0.2) < 1e-5

    # Bytearray interoperability
    ba_a = bytearray(a)
    ba_b = bytearray(b)
    assert abs(frame_diff_u8(ba_a, ba_b) - 0.2) < 1e-5

    # List of ints
    l_a = [100] * 1024
    l_b = [151] * 1024
    assert abs(frame_diff_u8(l_a, l_b) - 0.2) < 1e-5


def test_hamming_dist_u64() -> None:
    h1 = [0x1111222233334444, 0x5555666677778888]
    h2 = [0x1111222233334444, 0x555566667777888F]  # lowest byte differs: 8 (1000b) vs F (1111b) -> 3 bits
    assert hamming_dist_u64(h1, h2) == 3
    assert hamming_dist_u64(h1, h1) == 0


def test_vector_dot_and_cosine() -> None:
    dim = 128
    v_ones = [1.0] * dim
    v_twos = [2.0] * dim

    # Dot product
    dot = vector_dot(v_ones, v_twos)
    assert abs(dot - (dim * 2.0)) < 1e-4

    # Cosine similarity - identical
    cos_ident = cosine_similarity(v_ones, v_ones)
    assert abs(cos_ident - 1.0) < 1e-5

    # Cosine similarity - orthogonal
    v_orth1 = [1.0, 0.0] * (dim // 2)
    v_orth2 = [0.0, 1.0] * (dim // 2)
    assert abs(cosine_similarity(v_orth1, v_orth2)) < 1e-5

    # Cosine similarity - opposite
    v_neg = [-1.0] * dim
    assert abs(cosine_similarity(v_ones, v_neg) - (-1.0)) < 1e-5


def test_vector_normalize() -> None:
    dim = 128
    vec = [0.0] * dim
    vec[0] = 3.0
    vec[1] = 4.0

    orig_norm = vector_normalize(vec)
    assert abs(orig_norm - 5.0) < 1e-5
    assert abs(vec[0] - 0.6) < 1e-5
    assert abs(vec[1] - 0.8) < 1e-5

    new_norm = math.sqrt(sum(x * x for x in vec))
    assert abs(new_norm - 1.0) < 1e-5


def test_batch_search_cosine() -> None:
    dim = 64
    query = [1.0] * dim
    matrix = [
        [1.0] * dim,          # parallel (cos = 1.0)
        [-1.0] * dim,         # anti-parallel (cos = -1.0)
        [1.0, -1.0] * (dim // 2),  # orthogonal (cos = 0.0)
        [2.0] * dim,          # parallel (cos = 1.0)
    ]

    scores = default_engine.batch_search_cosine(query, matrix)
    assert len(scores) == 4
    assert abs(scores[0] - 1.0) < 1e-4
    assert abs(scores[1] - (-1.0)) < 1e-4
    assert abs(scores[2] - 0.0) < 1e-4
    assert abs(scores[3] - 1.0) < 1e-4


def test_mask_rect_rgba() -> None:
    width = 32
    height = 32
    stride = 32
    pixels = [0xFF000000] * (width * height)

    # Mask 8x8 box at (4, 4) with 0xFFFFFFFF
    mask_rect_rgba(pixels, width, height, stride, rx=4, ry=4, rw=8, rh=8, color=0xFFFFFFFF)

    # Unmasked points
    assert pixels[0] == 0xFF000000
    assert pixels[3 * stride + 4] == 0xFF000000
    assert pixels[12 * stride + 12] == 0xFF000000

    # Masked points
    assert pixels[4 * stride + 4] == 0xFFFFFFFF
    assert pixels[11 * stride + 11] == 0xFFFFFFFF


def test_multithreading_stress() -> None:
    """Stress test hardware SIMD kernels with concurrent threads."""
    def worker(worker_id: int) -> bool:
        dim = 128
        v1 = [float(worker_id % 10 + 1)] * dim
        v2 = [float((worker_id + 1) % 10 + 1)] * dim

        for _ in range(100):
            d = frame_diff_f32(v1, v2)
            c = cosine_similarity(v1, v2)
            assert c > 0.99
            dot = vector_dot(v1, v2)
            assert dot > 0.0
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(worker, i) for i in range(32)]
        for fut in concurrent.futures.as_completed(futures):
            assert fut.result() is True
