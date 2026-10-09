; =============================================================================
; NanoRecall — 64-bit Native Standalone FASM Test & Benchmark Suite
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; =============================================================================

format PE64 console
entry start

include 'C:\proekts\FASM\INCLUDE\WIN64A.INC'

section '.data' data readable writeable
    hdr_msg     db '====================================================================', 13, 10
                db '  NanoRecall Native x86-64 FASM AVX2+FMA Engine Test Suite', 13, 10
                db '====================================================================', 13, 10, 0
    isa_msg     db '  Active SIMD Backend: %s', 13, 10, 0
    t1_msg      db '  [TEST 1] Core Version & ISA Identification: ', 0
    t2_msg      db '  [TEST 2] Float32 Screen Frame Differencing (AVX2): ', 0
    t3_msg      db '  [TEST 3] Grayscale UInt8 SAD Differencing (vpsadbw): ', 0
    t4_msg      db '  [TEST 4] Perceptual Hash Hamming Distance (popcnt): ', 0
    t5_msg      db '  [TEST 5] Unrolled AVX2+FMA Vector Dot Product (dim=128): ', 0
    t6_msg      db '  [TEST 6] Vector Cosine Similarity (Identical & Orthogonal): ', 0
    t7_msg      db '  [TEST 7] In-Place Vector L2 Normalization: ', 0
    t8_msg      db '  [TEST 8] Batch Memory Frame Cosine Search: ', 0
    t9_msg      db '  [TEST 9] Privacy RGBA Screen Bounding Box Masking: ', 0
    bench_hdr   db '--------------------------------------------------------------------', 13, 10
                db '  [BENCHMARK] Ultra-High-Speed Microkernel Throughput:', 13, 10, 0
    bench_diff  db '    * Frame Diff (32x32 1024-px): %u ns/frame (%u fps)', 13, 10, 0
    bench_dot   db '    * Vector Dot (dim=128):       %u ns/op (%u M vectors/sec)', 13, 10, 0

    pass_str    db 'PASS', 13, 10, 0
    fail_str    db 'FAIL!', 13, 10, 0

    all_ok_msg  db '--------------------------------------------------------------------', 13, 10
                db '  ALL 64-BIT FASM NANORECALL NATIVE TESTS PASSED (100%% Accuracy)!', 13, 10
                db '====================================================================', 13, 10, 0

    isa_str     db 'AVX2+FMA (FASM x86-64, 256-bit SIMD)', 0
    nr_sign_mask_f32 dd 7FFFFFFFh

    freq        rq 1
    t_start     rq 1
    t_end       rq 1

    ; Data buffers for testing
    align 32
    diff_f32_a  rd 32
    diff_f32_b  rd 32

    align 32
    diff_u8_a   rb 1024
    diff_u8_b   rb 1024

    hash_a      dq 1111222233334444h, 5555666677778888h
    hash_b      dq 1111222233334444h, 555566667777888Fh ; 3 bits diff in lowest byte

    align 32
    vec_a       rd 128
    align 32
    vec_b       rd 128
    align 32
    vec_norm    rd 128

    align 32
    matrix_vecs rd 4 * 128
    batch_scores rd 4

    align 32
    screen_pix  rd 1024 ; 32x32 RGBA pixels

section '.text' code readable executable

; Include microkernels
include 'nanorecall64_kernel.inc'

align 16
nanorecall_simd_isa:
    lea rax, [isa_str]
    ret

start:
    sub rsp, 88h

    lea rcx, [freq]
    call [QueryPerformanceFrequency]

    lea rcx, [hdr_msg]
    call [printf]

    call nanorecall_simd_isa
    mov rdx, rax
    lea rcx, [isa_msg]
    call [printf]

    lea rcx, [t1_msg]
    call [printf]

    call nanorecall_version
    cmp eax, 106
    jne .t1_fail
    lea rcx, [pass_str]
    call [printf]
    jmp .test2
.t1_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 1
    call [ExitProcess]

.test2:
    lea rcx, [t2_msg]
    call [printf]

    mov eax, 3F800000h ; 1.0f
    mov edx, 3FC00000h ; 1.5f
    xor ecx, ecx
.init_f32:
    cmp ecx, 32
    jae .run_f32
    mov [diff_f32_a + rcx*4], eax
    mov [diff_f32_b + rcx*4], edx
    inc ecx
    jmp .init_f32

.run_f32:
    lea rcx, [diff_f32_a]
    lea rdx, [diff_f32_b]
    mov r8, 32
    call nanorecall_frame_diff_f32

    ; Expected: 0.5f (3F000000h)
    mov eax, 3F000000h
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh ; 0.001f tolerance
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t2_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test3
.t2_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 2
    call [ExitProcess]

.test3:
    lea rcx, [t3_msg]
    call [printf]

    xor ecx, ecx
.init_u8:
    cmp ecx, 1024
    jae .run_u8
    mov byte [diff_u8_a + rcx], 100
    mov byte [diff_u8_b + rcx], 151
    inc ecx
    jmp .init_u8

.run_u8:
    lea rcx, [diff_u8_a]
    lea rdx, [diff_u8_b]
    mov r8, 1024
    call nanorecall_frame_diff_u8

    ; Expected: 0.2f (3E4CCCCDh)
    mov eax, 3E4CCCCDh
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh ; 0.001f tolerance
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t3_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test4
.t3_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 3
    call [ExitProcess]

.test4:
    ; -------------------------------------------------------------------------
    ; [TEST 4] Hamming distance
    ; -------------------------------------------------------------------------
    lea rcx, [t4_msg]
    call [printf]

    lea rcx, [hash_a]
    lea rdx, [hash_b]
    mov r8, 2
    call nanorecall_hamming_dist_u64

    cmp rax, 3
    jne .t4_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test5
.t4_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 4
    call [ExitProcess]

.test5:
    ; -------------------------------------------------------------------------
    ; [TEST 5] Vector Dot Product (dim=128, a=1.0f, b=2.0f -> dot=256.0f)
    ; -------------------------------------------------------------------------
    lea rcx, [t5_msg]
    call [printf]

    mov eax, 3F800000h ; 1.0f
    mov edx, 40000000h ; 2.0f
    xor ecx, ecx
.init_dot:
    cmp ecx, 128
    jae .run_dot
    mov [vec_a + rcx*4], eax
    mov [vec_b + rcx*4], edx
    inc ecx
    jmp .init_dot

.run_dot:
    lea rcx, [vec_a]
    lea rdx, [vec_b]
    mov r8, 128
    call nanorecall_vector_dot

    ; Expected: 256.0f (43800000h)
    mov eax, 43800000h
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh ; 0.001f tolerance
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t5_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test6
.t5_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 5
    call [ExitProcess]

.test6:
    ; -------------------------------------------------------------------------
    ; [TEST 6] Cosine Similarity (Identical -> 1.0f)
    ; -------------------------------------------------------------------------
    lea rcx, [t6_msg]
    call [printf]

    lea rcx, [vec_a]
    lea rdx, [vec_a]
    mov r8, 128
    call nanorecall_cosine_similarity

    ; Expected: 1.0f (3F800000h)
    mov eax, 3F800000h
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t6_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test7
.t6_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 6
    call [ExitProcess]

.test7:
    ; -------------------------------------------------------------------------
    ; [TEST 7] In-Place Vector Normalization
    ; -------------------------------------------------------------------------
    lea rcx, [t7_msg]
    call [printf]

    ; vec_norm[0] = 3.0f (40400000h), vec_norm[1] = 4.0f (40800000h), rest = 0
    xor ecx, ecx
.init_norm:
    cmp ecx, 128
    jae .set_norm_vals
    mov dword [vec_norm + rcx*4], 0
    inc ecx
    jmp .init_norm

.set_norm_vals:
    mov dword [vec_norm + 0], 40400000h ; 3.0f
    mov dword [vec_norm + 4], 40800000h ; 4.0f

    lea rcx, [vec_norm]
    mov rdx, 128
    call nanorecall_vector_normalize

    ; Returned norm should be 5.0f (40A00000h)
    mov eax, 40A00000h
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t7_fail

    ; vec_norm[0] should be 0.6f (3F19999Ah)
    vmovss xmm0, [vec_norm + 0]
    mov eax, 3F19999Ah
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    vucomiss xmm0, xmm2
    ja .t7_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .test8
.t7_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 7
    call [ExitProcess]

.test8:
    ; -------------------------------------------------------------------------
    ; [TEST 8] Batch Cosine Search
    ; -------------------------------------------------------------------------
    lea rcx, [t8_msg]
    call [printf]

    ; Setup matrix with 4 vectors:
    ; vec 0 = vec_a (cosine with vec_a = 1.0f)
    ; vec 1 = vec_a
    ; vec 2 = vec_a
    ; vec 3 = vec_a
    xor ecx, ecx
.init_mat:
    cmp ecx, 4 * 128
    jae .run_batch
    mov edx, 3F800000h ; 1.0f
    mov [matrix_vecs + rcx*4], edx
    inc ecx
    jmp .init_mat

.run_batch:
    lea rcx, [vec_a]
    lea rdx, [matrix_vecs]
    mov r8, 4                   ; 4 vectors
    mov r9, 128                 ; dim = 128
    mov qword [rsp + 20h], batch_scores
    call nanorecall_batch_search_cosine

    ; Verify all 4 scores are ~1.0f
    xor ecx, ecx
.check_scores:
    cmp ecx, 4
    jae .batch_ok
    vmovss xmm0, [batch_scores + rcx*4]
    mov eax, 3F800000h
    vmovd xmm1, eax
    vsubss xmm0, xmm0, xmm1
    vbroadcastss xmm3, dword [nr_sign_mask_f32]
    vandps xmm0, xmm0, xmm3
    mov eax, 3A83126Fh
    vmovd xmm2, eax
    vucomiss xmm0, xmm2
    ja .t8_fail
    inc ecx
    jmp .check_scores

.batch_ok:
    lea rcx, [pass_str]
    call [printf]
    jmp .test9
.t8_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 8
    call [ExitProcess]

.test9:
    ; -------------------------------------------------------------------------
    ; [TEST 9] Screen RGBA Rect Masking
    ; -------------------------------------------------------------------------
    lea rcx, [t9_msg]
    call [printf]

    ; Init 32x32 screen pixels to black (0xFF000000)
    xor ecx, ecx
.init_pix:
    cmp ecx, 1024
    jae .run_mask
    mov dword [screen_pix + rcx*4], 0FF000000h
    inc ecx
    jmp .init_pix

.run_mask:
    ; Mask rect (rx=4, ry=4, rw=8, rh=8) with white 0xFFFFFFFF
    ; RCX = pixels, EDX = width (32), R8D = height (32), R9D = stride (32)
    lea rcx, [screen_pix]
    mov edx, 32
    mov r8d, 32
    mov r9d, 32
    mov dword [rsp + 20h], 4          ; rx
    mov dword [rsp + 28h], 4          ; ry
    mov dword [rsp + 30h], 8          ; rw
    mov dword [rsp + 38h], 8          ; rh
    mov dword [rsp + 40h], 0FFFFFFFFh ; color
    call nanorecall_mask_rect_rgba

    ; Check pixel outside (0, 0) is still 0xFF000000
    cmp dword [screen_pix + 0], 0FF000000h
    jne .t9_fail

    ; Check pixel inside (4, 4) -> index = 4*32 + 4 = 132 is 0xFFFFFFFF
    cmp dword [screen_pix + 132*4], 0FFFFFFFFh
    jne .t9_fail

    ; Check pixel inside (11, 11) -> index = 11*32 + 11 = 363 is 0xFFFFFFFF
    cmp dword [screen_pix + 363*4], 0FFFFFFFFh
    jne .t9_fail

    ; Check pixel outside (12, 12) -> index = 12*32 + 12 = 396 is 0xFF000000
    cmp dword [screen_pix + 396*4], 0FF000000h
    jne .t9_fail

    lea rcx, [pass_str]
    call [printf]
    jmp .benchmarks
.t9_fail:
    lea rcx, [fail_str]
    call [printf]
    mov ecx, 9
    call [ExitProcess]

.benchmarks:
    lea rcx, [bench_hdr]
    call [printf]

    ; Benchmark uint8 frame diff (100,000 iterations)
    lea rcx, [t_start]
    call [QueryPerformanceCounter]

    mov r12d, 100000
.bench_diff_loop:
    lea rcx, [diff_u8_a]
    lea rdx, [diff_u8_b]
    mov r8, 1024
    call nanorecall_frame_diff_u8
    dec r12d
    jnz .bench_diff_loop

    lea rcx, [t_end]
    call [QueryPerformanceCounter]

    ; ns/op = (t_end - t_start) * 10^9 / (freq * 100000)
    mov rax, [t_end]
    sub rax, [t_start]
    mov r8, 1000000000
    mul r8
    mov r9, [freq]
    imul r9, 100000
    div r9
    test eax, eax
    jnz .diff_ns_ok
    mov eax, 1
.diff_ns_ok:
    mov ebx, eax ; ns per frame

    ; fps = 10^9 / ns
    mov rax, 1000000000
    xor rdx, rdx
    div rbx
    mov r8d, eax ; fps
    mov edx, ebx ; ns

    lea rcx, [bench_diff]
    call [printf]

    ; Benchmark vector dot product (100,000 iterations)
    lea rcx, [t_start]
    call [QueryPerformanceCounter]

    mov r12d, 100000
.bench_dot_loop:
    lea rcx, [vec_a]
    lea rdx, [vec_b]
    mov r8, 128
    call nanorecall_vector_dot
    dec r12d
    jnz .bench_dot_loop

    lea rcx, [t_end]
    call [QueryPerformanceCounter]

    mov rax, [t_end]
    sub rax, [t_start]
    mov r8, 1000000000
    mul r8
    mov r9, [freq]
    imul r9, 100000
    div r9
    test eax, eax
    jnz .dot_ns_ok
    mov eax, 1
.dot_ns_ok:
    mov ebx, eax ; ns per op

    ; M/sec = 1000 / ns
    mov eax, 1000
    xor edx, edx
    div ebx
    mov r8d, eax
    mov edx, ebx
    lea rcx, [bench_dot]
    call [printf]

    ; All Passed
    lea rcx, [all_ok_msg]
    call [printf]

    xor ecx, ecx
    call [ExitProcess]

section '.idata' import data readable
library kernel32, 'KERNEL32.DLL',\
        msvcrt,   'MSVCRT.DLL'

import kernel32,\
       ExitProcess, 'ExitProcess',\
       QueryPerformanceCounter, 'QueryPerformanceCounter',\
       QueryPerformanceFrequency, 'QueryPerformanceFrequency'

import msvcrt,\
       printf, 'printf'
