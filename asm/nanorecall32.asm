; =============================================================================
; NanoRecall 32-bit Native SIMD Dynamic Link Library (PE32 DLL)
; Flat Assembler (FASM) Bare-Metal Engine (x86 SSE2)
; Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
; MIT License
; =============================================================================

format PE GUI 4.0 DLL
entry DllEntryPoint

include 'C:\proekts\FASM\INCLUDE\WIN32A.INC'

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
    mov eax, isa_str
    ret

; Include microkernels
include 'nanorecall32_kernel.inc'

section '.data' data readable
isa_str db 'SSE2 (FASM x86 32-bit, 128-bit SIMD)', 0

section '.edata' export data readable
export 'nanorecall32.dll',\
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
