; =============================================================================
; NanoRecall 64-bit Native SIMD Dynamic Link Library (PE64 DLL)
; Flat Assembler (FASM) Bare-Metal Engine (AVX2 + FMA)
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; =============================================================================

format PE64 GUI 6.0 DLL
entry DllEntryPoint

include 'C:\proekts\FASM\INCLUDE\WIN64A.INC'

section '.text' code readable executable

proc DllEntryPoint hinstDLL, fdwReason, lpvReserved
    mov eax, 1
    ret
endp

; -----------------------------------------------------------------------------
; const char* nanorecall_simd_isa(void)
; -----------------------------------------------------------------------------
align 16
nanorecall_simd_isa:
    lea rax, [isa_str]
    ret

; Include microkernels
include 'nanorecall64_kernel.inc'

section '.data' data readable writeable
isa_str db 'AVX2+FMA (FASM x86-64, 256-bit SIMD)', 0
align 32
nr_sign_mask_f32 dd 8 dup (7FFFFFFFh)

section '.edata' export data readable
export 'nanorecall64.dll',\
       nanorecall_version,              'nanorecall_version',\
       nanorecall_simd_isa,             'nanorecall_simd_isa',\
       nanorecall_frame_diff_f32,       'nanorecall_frame_diff_f32',\
       nanorecall_frame_diff_u8,        'nanorecall_frame_diff_u8',\
       nanorecall_hamming_dist_u64,     'nanorecall_hamming_dist_u64',\
       nanorecall_vector_dot,           'nanorecall_vector_dot',\
       nanorecall_cosine_similarity,    'nanorecall_cosine_similarity',\
       nanorecall_vector_normalize,     'nanorecall_vector_normalize',\
       nanorecall_batch_search_cosine,  'nanorecall_batch_search_cosine',\
       nanorecall_mask_rect_rgba,       'nanorecall_mask_rect_rgba'

section '.reloc' fixups data readable discardable
if $=$$
    dd 0,8
end if
