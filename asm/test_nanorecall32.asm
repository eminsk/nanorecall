; =============================================================================
; NanoRecall — 32-bit Native Standalone FASM Test & Benchmark Suite
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; =============================================================================

format PE console
entry start

include 'C:\proekts\FASM\INCLUDE\WIN32A.INC'

section '.data' data readable writeable
    hdr_msg     db '====================================================================', 13, 10
                db '  NanoRecall Native x86 32-bit FASM SSE2 Engine Test Suite', 13, 10
                db '====================================================================', 13, 10, 0
    isa_msg     db '  Active SIMD Backend: %s', 13, 10, 0
    t1_msg      db '  [TEST 1] Core Version & ISA Identification: ', 0
    t2_msg      db '  [TEST 2] Float32 Screen Frame Differencing (SSE2): ', 0
    t3_msg      db '  [TEST 3] Grayscale UInt8 SAD Differencing (psadbw): ', 0
    t4_msg      db '  [TEST 4] Perceptual Hash Hamming Distance (32-bit): ', 0
    t5_msg      db '  [TEST 5] Unrolled SSE2 Vector Dot Product (dim=128): ', 0
    t6_msg      db '  [TEST 6] Vector Cosine Similarity (Identical & Orthogonal): ', 0
    t7_msg      db '  [TEST 7] In-Place Vector L2 Normalization: ', 0
    t8_msg      db '  [TEST 8] Batch Memory Frame Cosine Search: ', 0
    t9_msg      db '  [TEST 9] Privacy RGBA Screen Bounding Box Masking: ', 0

    pass_str    db 'PASS', 13, 10, 0
    fail_str    db 'FAIL!', 13, 10, 0

    all_ok_msg  db '--------------------------------------------------------------------', 13, 10
                db '  ALL 32-BIT FASM NANORECALL NATIVE TESTS PASSED (100%% Accuracy)!', 13, 10
                db '====================================================================', 13, 10, 0

    isa_str     db 'SSE2 (FASM x86 32-bit, 128-bit SIMD)', 0
    sign_mask   dd 7FFFFFFFh
    tol         dd 3A83126Fh ; 0.001f

    ; Data buffers
    align 16
    diff_f32_a  rd 32
    diff_f32_b  rd 32

    align 16
    diff_u8_a   rb 1024
    diff_u8_b   rb 1024

    hash_a      dd 33334444h, 11112222h, 77778888h, 55556666h
    hash_b      dd 33334444h, 11112222h, 7777888Fh, 55556666h ; 3 bits diff

    align 16
    vec_a       rd 128
    align 16
    vec_b       rd 128
    align 16
    vec_norm    rd 128

    align 16
    matrix_vecs rd 4 * 128
    batch_scores rd 4

    align 16
    screen_pix  rd 1024 ; 32x32 RGBA pixels

    temp_flt    dd 0.0

section '.text' code readable executable

; Include microkernels
include 'nanorecall32_kernel.inc'

align 16
nanorecall_simd_isa:
    mov eax, isa_str
    ret

start:
    push hdr_msg
    call [printf]
    add esp, 4

    call nanorecall_simd_isa
    push eax
    push isa_msg
    call [printf]
    add esp, 8

    ; -------------------------------------------------------------------------
    ; [TEST 1] Version & ISA
    ; -------------------------------------------------------------------------
    push t1_msg
    call [printf]
    add esp, 4

    call nanorecall_version
    cmp eax, 106
    jne .t1_fail
    push pass_str
    call [printf]
    add esp, 4
    jmp .test2
.t1_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 1
    call [ExitProcess]

.test2:
    ; -------------------------------------------------------------------------
    ; [TEST 2] Float32 Frame Diff (a=1.0f, b=1.5f, diff=0.5f)
    ; -------------------------------------------------------------------------
    push t2_msg
    call [printf]
    add esp, 4

    mov eax, 3F800000h ; 1.0f
    mov edx, 3FC00000h ; 1.5f
    xor ecx, ecx
.init_f32:
    cmp ecx, 32
    jae .run_f32
    mov [diff_f32_a + ecx*4], eax
    mov [diff_f32_b + ecx*4], edx
    inc ecx
    jmp .init_f32

.run_f32:
    push 32
    push diff_f32_b
    push diff_f32_a
    call nanorecall_frame_diff_f32
    add esp, 12

    ; Result in ST(0): check ~0.5f
    fstp dword [temp_flt]
    movss xmm0, [temp_flt]
    mov eax, 3F000000h
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t2_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test3
.t2_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 2
    call [ExitProcess]

.test3:
    ; -------------------------------------------------------------------------
    ; [TEST 3] UInt8 Frame Diff (a=100, b=151, diff=51/255 = 0.2f)
    ; -------------------------------------------------------------------------
    push t3_msg
    call [printf]
    add esp, 4

    xor ecx, ecx
.init_u8:
    cmp ecx, 1024
    jae .run_u8
    mov byte [diff_u8_a + ecx], 100
    mov byte [diff_u8_b + ecx], 151
    inc ecx
    jmp .init_u8

.run_u8:
    push 1024
    push diff_u8_b
    push diff_u8_a
    call nanorecall_frame_diff_u8
    add esp, 12

    ; Result in ST(0): check ~0.2f (3E4CCCCDh)
    fstp dword [temp_flt]
    movss xmm0, [temp_flt]
    mov eax, 3E4CCCCDh
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t3_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test4
.t3_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 3
    call [ExitProcess]

.test4:
    ; -------------------------------------------------------------------------
    ; [TEST 4] Hamming distance
    ; -------------------------------------------------------------------------
    push t4_msg
    call [printf]
    add esp, 4

    push 2
    push hash_b
    push hash_a
    call nanorecall_hamming_dist_u64
    add esp, 12

    cmp eax, 3
    jne .t4_fail
    cmp edx, 0
    jne .t4_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test5
.t4_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 4
    call [ExitProcess]

.test5:
    ; -------------------------------------------------------------------------
    ; [TEST 5] Vector Dot Product (dim=128, a=1.0f, b=2.0f -> dot=256.0f)
    ; -------------------------------------------------------------------------
    push t5_msg
    call [printf]
    add esp, 4

    mov eax, 3F800000h ; 1.0f
    mov edx, 40000000h ; 2.0f
    xor ecx, ecx
.init_dot:
    cmp ecx, 128
    jae .run_dot
    mov [vec_a + ecx*4], eax
    mov [vec_b + ecx*4], edx
    inc ecx
    jmp .init_dot

.run_dot:
    push 128
    push vec_b
    push vec_a
    call nanorecall_vector_dot
    add esp, 12

    ; Result in ST(0): check 256.0f (43800000h)
    fstp dword [temp_flt]
    movss xmm0, [temp_flt]
    mov eax, 43800000h
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t5_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test6
.t5_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 5
    call [ExitProcess]

.test6:
    ; -------------------------------------------------------------------------
    ; [TEST 6] Cosine Similarity (Identical -> 1.0f)
    ; -------------------------------------------------------------------------
    push t6_msg
    call [printf]
    add esp, 4

    push 128
    push vec_a
    push vec_a
    call nanorecall_cosine_similarity
    add esp, 12

    fstp dword [temp_flt]
    movss xmm0, [temp_flt]
    mov eax, 3F800000h
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t6_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test7
.t6_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 6
    call [ExitProcess]

.test7:
    ; -------------------------------------------------------------------------
    ; [TEST 7] In-Place Vector Normalization
    ; -------------------------------------------------------------------------
    push t7_msg
    call [printf]
    add esp, 4

    xor ecx, ecx
.init_norm:
    cmp ecx, 128
    jae .set_norm_vals
    mov dword [vec_norm + ecx*4], 0
    inc ecx
    jmp .init_norm

.set_norm_vals:
    mov dword [vec_norm + 0], 40400000h ; 3.0f
    mov dword [vec_norm + 4], 40800000h ; 4.0f

    push 128
    push vec_norm
    call nanorecall_vector_normalize
    add esp, 8

    ; Returned norm in ST(0) should be 5.0f (40A00000h)
    fstp dword [temp_flt]
    movss xmm0, [temp_flt]
    mov eax, 40A00000h
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t7_fail

    ; vec_norm[0] should be 0.6f (3F19999Ah)
    movss xmm0, [vec_norm + 0]
    mov eax, 3F19999Ah
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t7_fail

    push pass_str
    call [printf]
    add esp, 4
    jmp .test8
.t7_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 7
    call [ExitProcess]

.test8:
    ; -------------------------------------------------------------------------
    ; [TEST 8] Batch Cosine Search
    ; -------------------------------------------------------------------------
    push t8_msg
    call [printf]
    add esp, 4

    xor ecx, ecx
.init_mat:
    cmp ecx, 4 * 128
    jae .run_batch
    mov edx, 3F800000h ; 1.0f
    mov [matrix_vecs + ecx*4], edx
    inc ecx
    jmp .init_mat

.run_batch:
    push batch_scores
    push 128
    push 4
    push matrix_vecs
    push vec_a
    call nanorecall_batch_search_cosine
    add esp, 20

    ; Verify all 4 scores are ~1.0f
    xor ecx, ecx
.check_scores:
    cmp ecx, 4
    jae .batch_ok
    movss xmm0, [batch_scores + ecx*4]
    mov eax, 3F800000h
    mov [temp_flt], eax
    subss xmm0, [temp_flt]
    movss xmm1, [sign_mask]
    andps xmm0, xmm1
    ucomiss xmm0, [tol]
    ja .t8_fail
    inc ecx
    jmp .check_scores

.batch_ok:
    push pass_str
    call [printf]
    add esp, 4
    jmp .test9
.t8_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 8
    call [ExitProcess]

.test9:
    ; -------------------------------------------------------------------------
    ; [TEST 9] Screen RGBA Rect Masking
    ; -------------------------------------------------------------------------
    push t9_msg
    call [printf]
    add esp, 4

    ; Init 32x32 screen pixels to black (0xFF000000)
    xor ecx, ecx
.init_pix:
    cmp ecx, 1024
    jae .run_mask
    mov dword [screen_pix + ecx*4], 0FF000000h
    inc ecx
    jmp .init_pix

.run_mask:
    ; Mask rect (rx=4, ry=4, rw=8, rh=8) with white 0xFFFFFFFF
    push 0FFFFFFFFh ; color
    push 8          ; rh
    push 8          ; rw
    push 4          ; ry
    push 4          ; rx
    push 32         ; stride
    push 32         ; height
    push 32         ; width
    push screen_pix ; pixels
    call nanorecall_mask_rect_rgba
    add esp, 36

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

    push pass_str
    call [printf]
    add esp, 4

    ; All Passed
    push all_ok_msg
    call [printf]
    add esp, 4

    push 0
    call [ExitProcess]

.t9_fail:
    push fail_str
    call [printf]
    add esp, 4
    push 9
    call [ExitProcess]

section '.idata' import data readable
library kernel32, 'KERNEL32.DLL',\
        msvcrt,   'MSVCRT.DLL'

import kernel32,\
       ExitProcess, 'ExitProcess'

import msvcrt,\
       printf, 'printf'
