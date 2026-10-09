/*
 * NanoRecall Bare-Metal Hardware SIMD Acceleration Microkernels (POSIX / Linux / macOS)
 * High-throughput AVX2+FMA & SSE2 microkernels for Desktop Recall, Differencing & Embedding.
 * Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
 * MIT License
 */

#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <string.h>

#if defined(__AVX2__) && defined(__FMA__)
#include <immintrin.h>
#define HAVE_AVX2_FMA 1
#elif defined(__SSE2__)
#include <emmintrin.h>
#define HAVE_SSE2 1
#endif

#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

EXPORT int nanorecall_version(void) {
    return 106;
}

EXPORT const char* nanorecall_simd_isa(void) {
#if defined(HAVE_AVX2_FMA)
    return "Hardware AVX2+FMA SIMD (POSIX / Linux Engine)";
#elif defined(HAVE_SSE2)
    return "Hardware SSE2 SIMD (POSIX / Linux Engine)";
#else
    return "Optimized C99 Vector SIMD Engine";
#endif
}

EXPORT float nanorecall_frame_diff_f32(const float* a, const float* b, size_t count) {
    if (!a || !b || count == 0) return 0.0f;

    double sum = 0.0;
    size_t i = 0;

#if defined(HAVE_AVX2_FMA)
    __m256 vsum0 = _mm256_setzero_ps();
    __m256 vsum1 = _mm256_setzero_ps();
    __m256 sign_mask = _mm256_castsi256_ps(_mm256_set1_epi32(0x7FFFFFFF));

    for (; i + 15 < count; i += 16) {
        __m256 va0 = _mm256_loadu_ps(a + i);
        __m256 vb0 = _mm256_loadu_ps(b + i);
        __m256 diff0 = _mm256_and_ps(_mm256_sub_ps(va0, vb0), sign_mask);
        vsum0 = _mm256_add_ps(vsum0, diff0);

        __m256 va1 = _mm256_loadu_ps(a + i + 8);
        __m256 vb1 = _mm256_loadu_ps(b + i + 8);
        __m256 diff1 = _mm256_and_ps(_mm256_sub_ps(va1, vb1), sign_mask);
        vsum1 = _mm256_add_ps(vsum1, diff1);
    }
    vsum0 = _mm256_add_ps(vsum0, vsum1);

    for (; i + 7 < count; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 diff = _mm256_and_ps(_mm256_sub_ps(va, vb), sign_mask);
        vsum0 = _mm256_add_ps(vsum0, diff);
    }

    float tmp[8];
    _mm256_storeu_ps(tmp, vsum0);
    for (int k = 0; k < 8; ++k) sum += tmp[k];
#endif

    for (; i < count; ++i) {
        sum += fabsf(a[i] - b[i]);
    }

    return (float)(sum / (double)count);
}

EXPORT float nanorecall_frame_diff_u8(const uint8_t* a, const uint8_t* b, size_t count) {
    if (!a || !b || count == 0) return 0.0f;

    uint64_t total_sad = 0;
    size_t i = 0;

#if defined(HAVE_AVX2_FMA)
    __m256i vsum = _mm256_setzero_si256();
    for (; i + 31 < count; i += 32) {
        __m256i va = _mm256_loadu_si256((const __m256i*)(a + i));
        __m256i vb = _mm256_loadu_si256((const __m256i*)(b + i));
        __m256i sad = _mm256_sad_epu8(va, vb);
        vsum = _mm256_add_epi64(vsum, sad);
    }
    uint64_t tmp[4];
    _mm256_storeu_si256((__m256i*)tmp, vsum);
    total_sad += tmp[0] + tmp[1] + tmp[2] + tmp[3];
#elif defined(HAVE_SSE2)
    __m128i vsum = _mm_setzero_si128();
    for (; i + 15 < count; i += 16) {
        __m128i va = _mm_loadu_si128((const __m128i*)(a + i));
        __m128i vb = _mm_loadu_si128((const __m128i*)(b + i));
        __m128i sad = _mm_sad_epu8(va, vb);
        vsum = _mm_add_epi64(vsum, sad);
    }
    uint64_t tmp[2];
    _mm_storeu_si128((__m128i*)tmp, vsum);
    total_sad += tmp[0] + tmp[1];
#endif

    for (; i < count; ++i) {
        int diff = (int)a[i] - (int)b[i];
        total_sad += (uint64_t)(diff < 0 ? -diff : diff);
    }

    return (float)((double)total_sad / ((double)count * 255.0));
}

EXPORT uint64_t nanorecall_hamming_dist_u64(const uint64_t* a, const uint64_t* b, size_t count) {
    if (!a || !b || count == 0) return 0;
    uint64_t total = 0;
    for (size_t i = 0; i < count; ++i) {
        uint64_t diff = a[i] ^ b[i];
#if defined(__GNUC__) || defined(__clang__)
        total += (uint64_t)__builtin_popcountll(diff);
#elif defined(_MSC_VER)
        total += (uint64_t)__popcnt64(diff);
#else
        diff = diff - ((diff >> 1) & 0x5555555555555555ULL);
        diff = (diff & 0x3333333333333333ULL) + ((diff >> 2) & 0x3333333333333333ULL);
        diff = (diff + (diff >> 4)) & 0x0F0F0F0F0F0F0F0FULL;
        total += (diff * 0x0101010101010101ULL) >> 56;
#endif
    }
    return total;
}

EXPORT float nanorecall_vector_dot(const float* a, const float* b, size_t dim) {
    if (!a || !b || dim == 0) return 0.0f;

    double sum = 0.0;
    size_t i = 0;

#if defined(HAVE_AVX2_FMA)
    __m256 vsum0 = _mm256_setzero_ps();
    __m256 vsum1 = _mm256_setzero_ps();

    for (; i + 15 < dim; i += 16) {
        __m256 va0 = _mm256_loadu_ps(a + i);
        __m256 vb0 = _mm256_loadu_ps(b + i);
        vsum0 = _mm256_fmadd_ps(va0, vb0, vsum0);

        __m256 va1 = _mm256_loadu_ps(a + i + 8);
        __m256 vb1 = _mm256_loadu_ps(b + i + 8);
        vsum1 = _mm256_fmadd_ps(va1, vb1, vsum1);
    }
    vsum0 = _mm256_add_ps(vsum0, vsum1);

    for (; i + 7 < dim; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        vsum0 = _mm256_fmadd_ps(va, vb, vsum0);
    }

    float tmp[8];
    _mm256_storeu_ps(tmp, vsum0);
    for (int k = 0; k < 8; ++k) sum += tmp[k];
#endif

    for (; i < dim; ++i) {
        sum += (double)a[i] * (double)b[i];
    }

    return (float)sum;
}

EXPORT float nanorecall_cosine_similarity(const float* a, const float* b, size_t dim) {
    if (!a || !b || dim == 0) return 0.0f;

    double dot = 0.0, norm_a = 0.0, norm_b = 0.0;
    size_t i = 0;

#if defined(HAVE_AVX2_FMA)
    __m256 vdot = _mm256_setzero_ps();
    __m256 vna  = _mm256_setzero_ps();
    __m256 vnb  = _mm256_setzero_ps();

    for (; i + 7 < dim; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        vdot = _mm256_fmadd_ps(va, vb, vdot);
        vna  = _mm256_fmadd_ps(va, va, vna);
        vnb  = _mm256_fmadd_ps(vb, vb, vnb);
    }

    float td[8], tna[8], tnb[8];
    _mm256_storeu_ps(td, vdot);
    _mm256_storeu_ps(tna, vna);
    _mm256_storeu_ps(tnb, vnb);
    for (int k = 0; k < 8; ++k) {
        dot += td[k];
        norm_a += tna[k];
        norm_b += tnb[k];
    }
#endif

    for (; i < dim; ++i) {
        double va = a[i];
        double vb = b[i];
        dot += va * vb;
        norm_a += va * va;
        norm_b += vb * vb;
    }

    double denom = sqrt(norm_a * norm_b);
    if (denom <= 1e-12) return 0.0f;
    return (float)(dot / denom);
}

EXPORT float nanorecall_vector_normalize(float* vec, size_t dim) {
    if (!vec || dim == 0) return 0.0f;
    float dot = nanorecall_vector_dot(vec, vec, dim);
    float norm = sqrtf(dot);
    if (norm <= 1e-12f) return 0.0f;

    float scale = 1.0f / norm;
    size_t i = 0;

#if defined(HAVE_AVX2_FMA)
    __m256 vscale = _mm256_set1_ps(scale);
    for (; i + 7 < dim; i += 8) {
        __m256 v = _mm256_loadu_ps(vec + i);
        _mm256_storeu_ps(vec + i, _mm256_mul_ps(v, vscale));
    }
#endif

    for (; i < dim; ++i) {
        vec[i] *= scale;
    }

    return norm;
}

EXPORT int nanorecall_batch_search_cosine(const float* query, const float* matrix,
                                         size_t num_vectors, size_t dim,
                                         float* scores_out) {
    if (!query || !matrix || !scores_out || num_vectors == 0 || dim == 0) return -1;
    for (size_t i = 0; i < num_vectors; ++i) {
        scores_out[i] = nanorecall_cosine_similarity(query, matrix + (i * dim), dim);
    }
    return 0;
}

EXPORT int nanorecall_mask_rect_rgba(uint32_t* pixels, int width, int height,
                                    int stride, int rx, int ry, int rw, int rh,
                                    uint32_t color) {
    if (!pixels || width <= 0 || height <= 0 || rw <= 0 || rh <= 0) return 0;
    if (rx < 0 || ry < 0 || rx >= width || ry >= height) return 0;

    if (rx + rw > width) rw = width - rx;
    if (ry + rh > height) rh = height - ry;
    if (rw <= 0 || rh <= 0) return 0;

    for (int y = 0; y < rh; ++y) {
        uint32_t* row = pixels + ((size_t)(ry + y) * (size_t)stride) + rx;
        int x = 0;
#if defined(HAVE_AVX2_FMA)
        __m256i vcolor = _mm256_set1_epi32((int)color);
        for (; x + 7 < rw; x += 8) {
            _mm256_storeu_si256((__m256i*)(row + x), vcolor);
        }
#endif
        for (; x < rw; ++x) {
            row[x] = color;
        }
    }
    return 0;
}
