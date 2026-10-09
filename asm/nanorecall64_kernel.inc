; =============================================================================
; NanoRecall Bare-Metal x86-64 SIMD Microkernel Engine (AVX2 + FMA)
; High-performance desktop screen differencing, embedding & privacy masking
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; =============================================================================

; -----------------------------------------------------------------------------
; int nanorecall_version(void)
; -----------------------------------------------------------------------------
align 16
nanorecall_version:
    mov eax, 106
    ret

; -----------------------------------------------------------------------------
; float nanorecall_frame_diff_f32(const float* a, const float* b, size_t count)
; RCX = a, RDX = b, R8 = count
; Computes mean absolute difference: (1 / count) * sum(|a[i] - b[i]|)
; Returns float in XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_frame_diff_f32:
    vxorps ymm0, ymm0, ymm0
    vxorps ymm1, ymm1, ymm1
    test r8, r8
    jz .diff_f32_zero

    vbroadcastss ymm5, dword [nr_sign_mask_f32]
    xor rax, rax

.diff_f32_loop16:
    lea r10, [rax + 16]
    cmp r10, r8
    ja .diff_f32_tail8

    vmovups ymm2, [rcx + rax*4]
    vmovups ymm3, [rdx + rax*4]
    vsubps ymm2, ymm2, ymm3
    vandps ymm2, ymm2, ymm5
    vaddps ymm0, ymm0, ymm2

    vmovups ymm3, [rcx + rax*4 + 32]
    vmovups ymm4, [rdx + rax*4 + 32]
    vsubps ymm3, ymm3, ymm4
    vandps ymm3, ymm3, ymm5
    vaddps ymm1, ymm1, ymm3

    add rax, 16
    jmp .diff_f32_loop16

.diff_f32_tail8:
    vaddps ymm0, ymm0, ymm1

.diff_f32_loop8:
    lea r10, [rax + 8]
    cmp r10, r8
    ja .diff_f32_reduce

    vmovups ymm2, [rcx + rax*4]
    vmovups ymm3, [rdx + rax*4]
    vsubps ymm2, ymm2, ymm3
    vandps ymm2, ymm2, ymm5
    vaddps ymm0, ymm0, ymm2

    add rax, 8
    jmp .diff_f32_loop8

.diff_f32_reduce:
    vextractf128 xmm1, ymm0, 1
    vaddps xmm0, xmm0, xmm1
    vshufps xmm1, xmm0, xmm0, 04Eh
    vaddps xmm0, xmm0, xmm1
    vshufps xmm1, xmm0, xmm0, 001h
    vaddss xmm0, xmm0, xmm1

.diff_f32_scalar:
    cmp rax, r8
    jae .diff_f32_norm

    vmovss xmm2, [rcx + rax*4]
    vsubss xmm2, xmm2, [rdx + rax*4]
    vandps xmm2, xmm2, xmm5
    vaddss xmm0, xmm0, xmm2
    inc rax
    jmp .diff_f32_scalar

.diff_f32_norm:
    vcvtsi2ss xmm1, xmm1, r8
    vdivss xmm0, xmm0, xmm1
    vzeroupper
    ret

.diff_f32_zero:
    vxorps xmm0, xmm0, xmm0
    ret

; -----------------------------------------------------------------------------
; float nanorecall_frame_diff_u8(const uint8_t* a, const uint8_t* b, size_t count)
; RCX = a, RDX = b, R8 = count
; Computes mean absolute difference on uint8 grayscale bytes normalized to 0..1:
; (1 / (count * 255)) * sum(|a[i] - b[i]|)
; Returns float in XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_frame_diff_u8:
    vpxor ymm0, ymm0, ymm0 ; accumulator (4x 64-bit totals)
    test r8, r8
    jz .diff_u8_zero

    xor rax, rax

.diff_u8_loop32:
    lea r10, [rax + 32]
    cmp r10, r8
    ja .diff_u8_reduce

    vmovdqu ymm1, [rcx + rax]
    vmovdqu ymm2, [rdx + rax]
    vpsadbw ymm1, ymm1, ymm2 ; computes SAD of 32 bytes into 4x 64-bit words
    vpaddq ymm0, ymm0, ymm1

    add rax, 32
    jmp .diff_u8_loop32

.diff_u8_reduce:
    ; Extract and sum 4x 64-bit words from ymm0
    vextracti128 xmm1, ymm0, 1
    vpaddq xmm0, xmm0, xmm1
    vmovq r10, xmm0
    vpextrq r11, xmm0, 1
    add r10, r11 ; total sum in r10

.diff_u8_scalar:
    cmp rax, r8
    jae .diff_u8_calc

    movzx r11d, byte [rcx + rax]
    movzx r9d, byte [rdx + rax]
    sub r11d, r9d
    ; absolute value
    mov r9d, r11d
    sar r9d, 31
    xor r11d, r9d
    sub r11d, r9d
    add r10, r11
    inc rax
    jmp .diff_u8_scalar

.diff_u8_calc:
    vcvtsi2ss xmm0, xmm0, r10
    vcvtsi2ss xmm1, xmm1, r8
    mov r10d, 255
    vcvtsi2ss xmm2, xmm2, r10d
    vmulss xmm1, xmm1, xmm2 ; count * 255.0
    vdivss xmm0, xmm0, xmm1
    vzeroupper
    ret

.diff_u8_zero:
    vxorps xmm0, xmm0, xmm0
    ret

; -----------------------------------------------------------------------------
; uint64_t nanorecall_hamming_dist_u64(const uint64_t* a, const uint64_t* b, size_t count)
; RCX = a, RDX = b, R8 = count
; Returns uint64_t hamming bit distance in RAX
; -----------------------------------------------------------------------------
align 16
nanorecall_hamming_dist_u64:
    xor rax, rax ; total distance
    test r8, r8
    jz .ham_done

    xor r9, r9 ; index

.ham_loop:
    cmp r9, r8
    jae .ham_done

    mov r10, [rcx + r9*8]
    xor r10, [rdx + r9*8]
    popcnt r10, r10
    add rax, r10

    inc r9
    jmp .ham_loop

.ham_done:
    ret

; -----------------------------------------------------------------------------
; float nanorecall_vector_dot(const float* a, const float* b, size_t dim)
; RCX = a, RDX = b, R8 = dim
; Returns float dot product in XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_vector_dot:
    vxorps ymm0, ymm0, ymm0
    vxorps ymm1, ymm1, ymm1
    test r8, r8
    jz .vdot_done

    xor rax, rax

.vdot_loop16:
    lea r10, [rax + 16]
    cmp r10, r8
    ja .vdot_tail8

    vmovups ymm2, [rcx + rax*4]
    vfmadd231ps ymm0, ymm2, [rdx + rax*4]

    vmovups ymm3, [rcx + rax*4 + 32]
    vfmadd231ps ymm1, ymm3, [rdx + rax*4 + 32]

    add rax, 16
    jmp .vdot_loop16

.vdot_tail8:
    vaddps ymm0, ymm0, ymm1

.vdot_loop8:
    lea r10, [rax + 8]
    cmp r10, r8
    ja .vdot_reduce

    vmovups ymm2, [rcx + rax*4]
    vfmadd231ps ymm0, ymm2, [rdx + rax*4]
    add rax, 8
    jmp .vdot_loop8

.vdot_reduce:
    vextractf128 xmm1, ymm0, 1
    vaddps xmm0, xmm0, xmm1
    vshufps xmm1, xmm0, xmm0, 04Eh
    vaddps xmm0, xmm0, xmm1
    vshufps xmm1, xmm0, xmm0, 001h
    vaddss xmm0, xmm0, xmm1

.vdot_scalar:
    cmp rax, r8
    jae .vdot_done

    vmovss xmm2, [rcx + rax*4]
    vmulss xmm2, xmm2, [rdx + rax*4]
    vaddss xmm0, xmm0, xmm2
    inc rax
    jmp .vdot_scalar

.vdot_done:
    vzeroupper
    ret

; -----------------------------------------------------------------------------
; float nanorecall_cosine_similarity(const float* a, const float* b, size_t dim)
; RCX = a, RDX = b, R8 = dim
; Returns float cosine similarity in XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_cosine_similarity:
    vxorps ymm0, ymm0, ymm0 ; dot
    vxorps ymm1, ymm1, ymm1 ; norm_a
    vxorps ymm2, ymm2, ymm2 ; norm_b
    test r8, r8
    jz .cos_zero

    xor rax, rax

.cos_loop8:
    lea r10, [rax + 8]
    cmp r10, r8
    ja .cos_reduce

    vmovups ymm3, [rcx + rax*4]
    vmovups ymm4, [rdx + rax*4]

    vfmadd231ps ymm0, ymm3, ymm4
    vfmadd231ps ymm1, ymm3, ymm3
    vfmadd231ps ymm2, ymm4, ymm4

    add rax, 8
    jmp .cos_loop8

.cos_reduce:
    ; Reduce dot (ymm0 -> xmm0)
    vextractf128 xmm3, ymm0, 1
    vaddps xmm0, xmm0, xmm3
    vshufps xmm3, xmm0, xmm0, 04Eh
    vaddps xmm0, xmm0, xmm3
    vshufps xmm3, xmm0, xmm0, 001h
    vaddss xmm0, xmm0, xmm3

    ; Reduce norm_a (ymm1 -> xmm1)
    vextractf128 xmm3, ymm1, 1
    vaddps xmm1, xmm1, xmm3
    vshufps xmm3, xmm1, xmm1, 04Eh
    vaddps xmm1, xmm1, xmm3
    vshufps xmm3, xmm1, xmm1, 001h
    vaddss xmm1, xmm1, xmm3

    ; Reduce norm_b (ymm2 -> xmm2)
    vextractf128 xmm3, ymm2, 1
    vaddps xmm2, xmm2, xmm3
    vshufps xmm3, xmm2, xmm2, 04Eh
    vaddps xmm2, xmm2, xmm3
    vshufps xmm3, xmm2, xmm2, 001h
    vaddss xmm2, xmm2, xmm3

.cos_scalar:
    cmp rax, r8
    jae .cos_calc

    vmovss xmm3, [rcx + rax*4]
    vmovss xmm4, [rdx + rax*4]
    vfmadd231ss xmm0, xmm3, xmm4
    vfmadd231ss xmm1, xmm3, xmm3
    vfmadd231ss xmm2, xmm4, xmm4
    inc rax
    jmp .cos_scalar

.cos_calc:
    vmulss xmm1, xmm1, xmm2
    vsqrtss xmm1, xmm1, xmm1
    vxorps xmm3, xmm3, xmm3
    vucomiss xmm1, xmm3
    jbe .cos_zero

    vdivss xmm0, xmm0, xmm1
    vzeroupper
    ret

.cos_zero:
    vxorps xmm0, xmm0, xmm0
    vzeroupper
    ret

; -----------------------------------------------------------------------------
; float nanorecall_vector_normalize(float* vec, size_t dim)
; RCX = vec, RDX = dim
; Normalizes vec in-place. Returns float original norm in XMM0.
; -----------------------------------------------------------------------------
align 16
nanorecall_vector_normalize:
    test rdx, rdx
    jz .norm_zero

    ; 1. Calculate L2 norm: dot(vec, vec)
    sub rsp, 28h
    mov r8, rdx
    mov rdx, rcx
    call nanorecall_vector_dot
    vsqrtss xmm0, xmm0, xmm0     ; norm in xmm0
    vmovaps xmm5, xmm0           ; preserve original norm
    add rsp, 28h

    vxorps xmm1, xmm1, xmm1
    vucomiss xmm0, xmm1
    jbe .norm_zero

    ; Invert norm for fast multiplication: 1.0 / norm
    mov eax, 3F800000h           ; 1.0f
    vmovd xmm2, eax
    vdivss xmm2, xmm2, xmm0      ; scale = 1.0 / norm

    vbroadcastss ymm3, xmm2
    xor rax, rax

.norm_loop8:
    lea r10, [rax + 8]
    cmp r10, r8
    ja .norm_scalar

    vmovups ymm4, [rcx + rax*4]
    vmulps ymm4, ymm4, ymm3
    vmovups [rcx + rax*4], ymm4

    add rax, 8
    jmp .norm_loop8

.norm_scalar:
    cmp rax, r8
    jae .norm_done

    vmovss xmm4, [rcx + rax*4]
    vmulss xmm4, xmm4, xmm2
    vmovss [rcx + rax*4], xmm4
    inc rax
    jmp .norm_scalar

.norm_done:
    vmovaps xmm0, xmm5           ; return original norm
    vzeroupper
    ret

.norm_zero:
    vxorps xmm0, xmm0, xmm0
    ret

; -----------------------------------------------------------------------------
; int nanorecall_batch_search_cosine(const float* query, const float* matrix,
;                                    size_t num_vectors, size_t dim,
;                                    float* scores_out)
; RCX = query, RDX = matrix, R8 = num_vectors, R9 = dim, [rsp+28h] = scores_out
; -----------------------------------------------------------------------------
align 16
nanorecall_batch_search_cosine:
    push rbp
    mov rbp, rsp
    push rbx
    push rsi
    push rdi
    push r12
    push r13
    push r14
    push r15
    sub rsp, 40                  ; 7*8=56 + 40 = 96 (multiple of 16, aligns stack)

    test r8, r8
    jz .batch_done
    test r9, r9
    jz .batch_done

    mov r12, rcx                 ; query
    mov r13, rdx                 ; matrix
    mov r14, r8                  ; num_vectors
    mov r15, r9                  ; dim
    mov rbx, [rbp + 30h]         ; scores_out ([rsp+28h] prior to push rbp)

    xor rsi, rsi                 ; index = 0

.batch_loop:
    cmp rsi, r14
    jae .batch_done

    mov rcx, r12
    mov rax, rsi
    imul rax, r15
    lea rdx, [r13 + rax*4]
    mov r8, r15

    call nanorecall_cosine_similarity
    vmovss [rbx + rsi*4], xmm0

    inc rsi
    jmp .batch_loop

.batch_done:
    vzeroupper
    xor eax, eax
    add rsp, 40
    pop r15
    pop r14
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbx
    pop rbp
    ret

; -----------------------------------------------------------------------------
; int nanorecall_mask_rect_rgba(uint32_t* pixels, int width, int height,
;                              int stride, int rx, int ry, int rw, int rh,
;                              uint32_t color)
; RCX = pixels, EDX = width, R8D = height, R9D = stride
; Stack args:
; [rsp+28h] = rx, [rsp+30h] = ry, [rsp+38h] = rw, [rsp+40h] = rh, [rsp+48h] = color
; -----------------------------------------------------------------------------
align 16
nanorecall_mask_rect_rgba:
    push rbp
    mov rbp, rsp
    push rbx
    push rsi
    push rdi
    push r12
    push r13

    ; RCX = pixels, EDX = width, R8D = height, R9D = stride
    ; [rbp + 30h] = rx, [rbp + 38h] = ry, [rbp + 40h] = rw, [rbp + 48h] = rh, [rbp + 50h] = color

    mov r10d, dword [rbp + 30h] ; rx
    mov r11d, dword [rbp + 38h] ; ry
    mov eax,  dword [rbp + 40h] ; rw
    mov esi,  dword [rbp + 48h] ; rh
    mov r13d, dword [rbp + 50h] ; color

    test eax, eax
    jle .mask_exit
    test esi, esi
    jle .mask_exit
    test r10d, r10d
    js .mask_exit
    test r11d, r11d
    js .mask_exit

    ; Clip rw if rx + rw > width
    mov ebx, r10d
    add ebx, eax
    cmp ebx, edx
    jle .clip_h
    sub edx, r10d
    jle .mask_exit
    mov eax, edx ; eax = clipped rw

.clip_h:
    ; Clip rh if ry + rh > height
    mov ebx, r11d
    add ebx, esi
    cmp ebx, r8d
    jle .start_mask
    sub r8d, r11d
    jle .mask_exit
    mov esi, r8d ; esi = clipped rh

.start_mask:
    vmovd xmm0, r13d
    vpbroadcastd ymm0, xmm0     ; 8 pixels of color

    xor r12d, r12d              ; y_offset = 0

.row_loop:
    cmp r12d, esi
    jge .mask_exit

    lea ebx, [r11d + r12d]      ; current y = ry + y_offset
    movsxd rbx, ebx
    imul rbx, r9                ; y * stride
    movsxd rdi, r10d
    add rbx, rdi                ; + rx
    lea rbx, [rcx + rbx*4]      ; row pixel address

    xor edi, edi                ; x = 0

.pix_loop8:
    lea edx, [edi + 8]
    cmp edx, eax
    ja .pix_scalar

    vmovdqu [rbx + rdi*4], ymm0
    add edi, 8
    jmp .pix_loop8

.pix_scalar:
    cmp edi, eax
    jae .row_next

    mov dword [rbx + rdi*4], r13d
    inc edi
    jmp .pix_scalar

.row_next:
    inc r12d
    jmp .row_loop

.mask_exit:
    vzeroupper
    xor eax, eax
    pop r13
    pop r12
    pop rdi
    pop rsi
    pop rbx
    pop rbp
    ret
