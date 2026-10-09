; =============================================================================
; NanoRecall — 32-bit SSE2 Screen Differencing & Memory Microkernels (x86 FASM)
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; Standard 32-bit cdecl Calling Convention
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
; [ebp+8]=a, [ebp+12]=b, [ebp+16]=count
; Returns float in ST(0) and XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_frame_diff_f32:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 28

    mov esi, [ebp + 8]          ; a
    mov edi, [ebp + 12]         ; b
    mov ecx, [ebp + 16]         ; count

    xorps xmm0, xmm0
    xorps xmm1, xmm1
    test ecx, ecx
    jz .diff_f32_zero_32

    mov eax, 7FFFFFFFh
    mov [esp + 16], eax
    movss xmm5, [esp + 16]
    shufps xmm5, xmm5, 0

    xor eax, eax

.diff_f32_loop8_32:
    lea edx, [eax + 8]
    cmp edx, ecx
    ja .diff_f32_tail4_32

    movups xmm2, [esi + eax*4]
    movups xmm3, [edi + eax*4]
    subps  xmm2, xmm3
    andps  xmm2, xmm5
    addps  xmm0, xmm2

    movups xmm3, [esi + eax*4 + 16]
    movups xmm4, [edi + eax*4 + 16]
    subps  xmm3, xmm4
    andps  xmm3, xmm5
    addps  xmm1, xmm3

    add eax, 8
    jmp .diff_f32_loop8_32

.diff_f32_tail4_32:
    addps xmm0, xmm1

.diff_f32_loop4_32:
    lea edx, [eax + 4]
    cmp edx, ecx
    ja .diff_f32_reduce_32

    movups xmm2, [esi + eax*4]
    movups xmm3, [edi + eax*4]
    subps  xmm2, xmm3
    andps  xmm2, xmm5
    addps  xmm0, xmm2

    add eax, 4
    jmp .diff_f32_loop4_32

.diff_f32_reduce_32:
    movhlps xmm1, xmm0
    addps   xmm0, xmm1
    movaps  xmm1, xmm0
    shufps  xmm1, xmm1, 001h
    addss   xmm0, xmm1

.diff_f32_scalar_32:
    cmp eax, ecx
    jae .diff_f32_norm_32

    movss xmm2, [esi + eax*4]
    subss xmm2, [edi + eax*4]
    andps xmm2, xmm5
    addss xmm0, xmm2
    inc eax
    jmp .diff_f32_scalar_32

.diff_f32_norm_32:
    cvtsi2ss xmm1, ecx
    divss xmm0, xmm1
    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

.diff_f32_zero_32:
    xorps xmm0, xmm0
    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; float nanorecall_frame_diff_u8(const uint8_t* a, const uint8_t* b, size_t count)
; [ebp+8]=a, [ebp+12]=b, [ebp+16]=count
; Returns float in ST(0) and XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_frame_diff_u8:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 28

    mov esi, [ebp + 8]          ; a
    mov edi, [ebp + 12]         ; b
    mov ecx, [ebp + 16]         ; count

    pxor xmm0, xmm0             ; accumulator (2x 64-bit totals)
    test ecx, ecx
    jz .diff_u8_zero_32

    xor eax, eax

.diff_u8_loop16_32:
    lea edx, [eax + 16]
    cmp edx, ecx
    ja .diff_u8_reduce_32

    movdqu xmm1, [esi + eax]
    movdqu xmm2, [edi + eax]
    psadbw xmm1, xmm2           ; computes SAD into two 64-bit words
    paddq  xmm0, xmm1

    add eax, 16
    jmp .diff_u8_loop16_32

.diff_u8_reduce_32:
    ; Sum the two 64-bit quadwords in xmm0
    movhlps xmm1, xmm0
    paddq   xmm0, xmm1
    movd    edx, xmm0           ; total sum in edx

.diff_u8_scalar_32:
    cmp eax, ecx
    jae .diff_u8_calc_32

    mov esi, [ebp + 8]
    mov edi, [ebp + 12]
    movzx ebx, byte [esi + eax]
    movzx esi, byte [edi + eax]
    sub ebx, esi
    mov esi, ebx
    sar esi, 31
    xor ebx, esi
    sub ebx, esi
    add edx, ebx
    inc eax
    jmp .diff_u8_scalar_32

.diff_u8_calc_32:
    cvtsi2ss xmm0, edx
    cvtsi2ss xmm1, ecx
    mov eax, 255
    cvtsi2ss xmm2, eax
    mulss xmm1, xmm2            ; count * 255.0
    divss xmm0, xmm1

    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

.diff_u8_zero_32:
    xorps xmm0, xmm0
    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; uint64_t nanorecall_hamming_dist_u64(const uint64_t* a, const uint64_t* b, size_t count)
; [ebp+8]=a, [ebp+12]=b, [ebp+16]=count
; Returns 64-bit distance in EDX:EAX
; -----------------------------------------------------------------------------
align 16
nanorecall_hamming_dist_u64:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx

    mov esi, [ebp + 8]          ; a
    mov edi, [ebp + 12]         ; b
    mov ecx, [ebp + 16]         ; count

    xor eax, eax                ; total_lo
    xor edx, edx                ; total_hi

    test ecx, ecx
    jz .ham_done_32

    xor ebx, ebx

.ham_loop_32:
    cmp ebx, ecx
    jae .ham_done_32

    push ecx
    mov ecx, [esi + ebx*8]
    xor ecx, [edi + ebx*8]
    popcnt ecx, ecx
    add eax, ecx
    adc edx, 0

    mov ecx, [esi + ebx*8 + 4]
    xor ecx, [edi + ebx*8 + 4]
    popcnt ecx, ecx
    add eax, ecx
    adc edx, 0
    pop ecx

    inc ebx
    jmp .ham_loop_32

.ham_done_32:
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; float nanorecall_vector_dot(const float* a, const float* b, size_t dim)
; [ebp+8]=a, [ebp+12]=b, [ebp+16]=dim
; Returns float in ST(0) and XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_vector_dot:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 28

    mov esi, [ebp + 8]          ; a
    mov edi, [ebp + 12]         ; b
    mov ecx, [ebp + 16]         ; dim

    xorps xmm0, xmm0
    xorps xmm1, xmm1
    test ecx, ecx
    jz .dot32_zero

    xor eax, eax

.dot32_loop8:
    lea edx, [eax + 8]
    cmp edx, ecx
    ja .dot32_tail4

    movups xmm2, [esi + eax*4]
    movups xmm3, [edi + eax*4]
    mulps  xmm2, xmm3
    addps  xmm0, xmm2

    movups xmm2, [esi + eax*4 + 16]
    movups xmm3, [edi + eax*4 + 16]
    mulps  xmm2, xmm3
    addps  xmm1, xmm2

    add eax, 8
    jmp .dot32_loop8

.dot32_tail4:
    addps xmm0, xmm1

.dot32_loop4:
    lea edx, [eax + 4]
    cmp edx, ecx
    ja .dot32_reduce

    movups xmm2, [esi + eax*4]
    movups xmm3, [edi + eax*4]
    mulps  xmm2, xmm3
    addps  xmm0, xmm2
    add eax, 4
    jmp .dot32_loop4

.dot32_reduce:
    movhlps xmm1, xmm0
    addps   xmm0, xmm1
    movaps  xmm1, xmm0
    shufps  xmm1, xmm1, 001h
    addss   xmm0, xmm1

.dot32_scalar:
    cmp eax, ecx
    jae .dot32_done

    movss xmm2, [esi + eax*4]
    mulss xmm2, [edi + eax*4]
    addss xmm0, xmm2
    inc eax
    jmp .dot32_scalar

.dot32_done:
    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

.dot32_zero:
    xorps xmm0, xmm0
    movss [esp], xmm0
    fld dword [esp]
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; float nanorecall_cosine_similarity(const float* a, const float* b, size_t dim)
; [ebp+8]=a, [ebp+12]=b, [ebp+16]=dim
; Returns float in ST(0) and XMM0
; -----------------------------------------------------------------------------
align 16
nanorecall_cosine_similarity:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 48

    mov esi, [ebp + 8]          ; a
    mov edi, [ebp + 12]         ; b
    mov ecx, [ebp + 16]         ; dim

    xorps xmm0, xmm0            ; dot
    xorps xmm1, xmm1            ; norm_a
    xorps xmm2, xmm2            ; norm_b
    test ecx, ecx
    jz .cos32_zero

    xor eax, eax

.cos32_loop4:
    lea edx, [eax + 4]
    cmp edx, ecx
    ja .cos32_reduce

    movups xmm3, [esi + eax*4]
    movups xmm4, [edi + eax*4]

    movaps xmm5, xmm3
    mulps  xmm5, xmm4
    addps  xmm0, xmm5

    movaps xmm5, xmm3
    mulps  xmm5, xmm5
    addps  xmm1, xmm5

    movaps xmm5, xmm4
    mulps  xmm5, xmm5
    addps  xmm2, xmm5

    add eax, 4
    jmp .cos32_loop4

.cos32_reduce:
    ; Reduce dot (xmm0)
    movhlps xmm3, xmm0
    addps   xmm0, xmm3
    movaps  xmm3, xmm0
    shufps  xmm3, xmm3, 001h
    addss   xmm0, xmm3

    ; Reduce norm_a (xmm1)
    movhlps xmm3, xmm1
    addps   xmm1, xmm3
    movaps  xmm3, xmm1
    shufps  xmm3, xmm3, 001h
    addss   xmm1, xmm3

    ; Reduce norm_b (xmm2)
    movhlps xmm3, xmm2
    addps   xmm2, xmm3
    movaps  xmm3, xmm2
    shufps  xmm3, xmm3, 001h
    addss   xmm2, xmm3

.cos32_scalar:
    cmp eax, ecx
    jae .cos32_calc

    movss xmm3, [esi + eax*4]
    movss xmm4, [edi + eax*4]

    movaps xmm5, xmm3
    mulss  xmm5, xmm4
    addss  xmm0, xmm5

    mulss  xmm3, xmm3
    addss  xmm1, xmm3

    mulss  xmm4, xmm4
    addss  xmm2, xmm4

    inc eax
    jmp .cos32_scalar

.cos32_calc:
    mulss xmm1, xmm2
    sqrtss xmm1, xmm1
    xorps xmm3, xmm3
    ucomiss xmm1, xmm3
    jbe .cos32_zero

    divss xmm0, xmm1
    movss [esp], xmm0
    fld dword [esp]
    add esp, 48
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

.cos32_zero:
    xorps xmm0, xmm0
    movss [esp], xmm0
    fld dword [esp]
    add esp, 48
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; float nanorecall_vector_normalize(float* vec, size_t dim)
; [ebp+8]=vec, [ebp+12]=dim
; Normalizes vec in-place. Returns float original norm in ST(0) and XMM0.
; -----------------------------------------------------------------------------
align 16
nanorecall_vector_normalize:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 32

    mov esi, [ebp + 8]          ; vec
    mov ecx, [ebp + 12]         ; dim

    test ecx, ecx
    jz .norm32_zero

    ; Call nanorecall_vector_dot(vec, vec, dim)
    push ecx
    push esi
    push esi
    call nanorecall_vector_dot
    add esp, 12
    fstp st0                    ; discard ST(0), keep in XMM0

    sqrtss xmm0, xmm0           ; norm
    movss [esp + 16], xmm0      ; save original norm

    xorps xmm1, xmm1
    ucomiss xmm0, xmm1
    jbe .norm32_zero

    ; 1.0f / norm
    mov eax, 3F800000h
    mov [esp + 20], eax
    movss xmm2, [esp + 20]
    divss xmm2, xmm0            ; scale

    movaps xmm3, xmm2
    shufps xmm3, xmm3, 0

    xor eax, eax

.norm32_loop4:
    lea edx, [eax + 4]
    cmp edx, ecx
    ja .norm32_scalar

    movups xmm4, [esi + eax*4]
    mulps  xmm4, xmm3
    movups [esi + eax*4], xmm4

    add eax, 4
    jmp .norm32_loop4

.norm32_scalar:
    cmp eax, ecx
    jae .norm32_done

    movss xmm4, [esi + eax*4]
    mulss xmm4, xmm2
    movss [esi + eax*4], xmm4
    inc eax
    jmp .norm32_scalar

.norm32_done:
    movss xmm0, [esp + 16]      ; restore original norm
    movss [esp], xmm0
    fld dword [esp]
    add esp, 32
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

.norm32_zero:
    xorps xmm0, xmm0
    movss [esp], xmm0
    fld dword [esp]
    add esp, 32
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; int nanorecall_batch_search_cosine(const float* query, const float* matrix,
;                                    size_t num_vectors, size_t dim,
;                                    float* scores_out)
; [ebp+8]=query, [ebp+12]=matrix, [ebp+16]=num_vectors, [ebp+20]=dim, [ebp+24]=scores_out
; -----------------------------------------------------------------------------
align 16
nanorecall_batch_search_cosine:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 28

    mov esi, [ebp + 16]         ; num_vectors
    test esi, esi
    jz .batch32_done

    xor ebx, ebx                ; i = 0

.batch32_loop:
    cmp ebx, esi
    jae .batch32_done

    mov edx, [ebp + 20]         ; dim
    push edx

    ; row_ptr = matrix + i * dim * 4
    mov eax, ebx
    imul eax, edx
    shl eax, 2
    add eax, [ebp + 12]
    push eax

    push dword [ebp + 8]        ; query
    call nanorecall_cosine_similarity
    add esp, 12

    mov edx, [ebp + 24]         ; scores_out
    fstp dword [edx + ebx*4]    ; store float score

    inc ebx
    jmp .batch32_loop

.batch32_done:
    xor eax, eax
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret

; -----------------------------------------------------------------------------
; int nanorecall_mask_rect_rgba(uint32_t* pixels, int width, int height,
;                              int stride, int rx, int ry, int rw, int rh,
;                              uint32_t color)
; [ebp+8]=pixels, [ebp+12]=width, [ebp+16]=height, [ebp+20]=stride,
; [ebp+24]=rx, [ebp+28]=ry, [ebp+32]=rw, [ebp+36]=rh, [ebp+40]=color
; -----------------------------------------------------------------------------
align 16
nanorecall_mask_rect_rgba:
    push ebp
    mov ebp, esp
    push esi
    push edi
    push ebx
    sub esp, 28

    mov eax, [ebp + 32]         ; rw
    mov edx, [ebp + 36]         ; rh
    test eax, eax
    jle .mask32_exit
    test edx, edx
    jle .mask32_exit

    mov esi, [ebp + 24]         ; rx
    mov edi, [ebp + 28]         ; ry
    test esi, esi
    js .mask32_exit
    test edi, edi
    js .mask32_exit

    ; Clip rw against width
    mov ebx, esi
    add ebx, eax
    cmp ebx, [ebp + 12]
    jle .clip32_h
    mov ebx, [ebp + 12]
    sub ebx, esi
    jle .mask32_exit
    mov eax, ebx                ; clipped rw
    mov [ebp + 32], eax

.clip32_h:
    ; Clip rh against height
    mov ebx, edi
    add ebx, edx
    cmp ebx, [ebp + 16]
    jle .start32_mask
    mov ebx, [ebp + 16]
    sub ebx, edi
    jle .mask32_exit
    mov edx, ebx                ; clipped rh
    mov [ebp + 36], edx

.start32_mask:
    ; Broadcast color to 4 pixels in xmm0
    mov eax, [ebp + 40]         ; color
    mov [esp + 16], eax
    movss xmm0, [esp + 16]
    shufps xmm0, xmm0, 0

    xor ecx, ecx                ; y_offset = 0

.row32_loop:
    cmp ecx, [ebp + 36]
    jge .mask32_exit

    ; row_addr = pixels + (ry + y) * stride * 4 + rx * 4
    mov eax, [ebp + 28]         ; ry
    add eax, ecx
    imul eax, [ebp + 20]        ; * stride
    add eax, [ebp + 24]         ; + rx
    shl eax, 2
    add eax, [ebp + 8]          ; row pixel address in eax

    mov edx, [ebp + 32]         ; rw
    xor esi, esi                ; x = 0

.pix32_loop4:
    lea edi, [esi + 4]
    cmp edi, edx
    ja .pix32_scalar

    movdqu [eax + esi*4], xmm0
    add esi, 4
    jmp .pix32_loop4

.pix32_scalar:
    cmp esi, edx
    jae .row32_next

    mov edi, [ebp + 40]         ; color
    mov [eax + esi*4], edi
    inc esi
    jmp .pix32_scalar

.row32_next:
    inc ecx
    jmp .row32_loop

.mask32_exit:
    xor eax, eax
    add esp, 28
    pop ebx
    pop edi
    pop esi
    pop ebp
    ret
