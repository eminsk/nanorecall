#!/usr/bin/env bash
# =============================================================================
# NanoRecall - Native SIMD Acceleration Builder for Linux & macOS
# Compiles hardware-accelerated AVX2+FMA & SSE2 microkernels
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src/nanorecall"

OS="$(uname -s)"
ARCH="$(uname -m)"

echo "====================================================================="
echo "  NanoRecall - Native Library Builder"
echo "  Detected OS:   ${OS}"
echo "  Architecture:  ${ARCH}"
echo "====================================================================="

CC=${CC:-gcc}
if ! command -v "${CC}" >/dev/null 2>&1; then
    CC="clang"
fi

if [ "${OS}" = "Darwin" ]; then
    OUT_LIB="${SRC_DIR}/libnanorecall.dylib"
    echo "Compiling for macOS using ${CC}..."
    if [ "${ARCH}" = "arm64" ]; then
        ${CC} -O3 -shared -fPIC -ffast-math "${SCRIPT_DIR}/nanorecall_kernel.c" -o "${OUT_LIB}"
    else
        ${CC} -O3 -shared -fPIC -mavx2 -mfma -ffast-math "${SCRIPT_DIR}/nanorecall_kernel.c" -o "${OUT_LIB}"
    fi
    echo "[OK] Built macOS dynamic library: ${OUT_LIB}"
elif [ "${OS}" = "Linux" ]; then
    OUT_LIB="${SRC_DIR}/libnanorecall64.so"
    echo "Compiling for Linux using ${CC}..."
    if [ "${ARCH}" = "x86_64" ]; then
        ${CC} -O3 -shared -fPIC -mavx2 -mfma -ffast-math "${SCRIPT_DIR}/nanorecall_kernel.c" -o "${OUT_LIB}" -lm
    else
        ${CC} -O3 -shared -fPIC -ffast-math "${SCRIPT_DIR}/nanorecall_kernel.c" -o "${OUT_LIB}" -lm
    fi
    cp "${OUT_LIB}" "${SCRIPT_DIR}/libnanorecall64.so" 2>/dev/null || true
    echo "[OK] Built Linux shared object: ${OUT_LIB}"
fi

echo "====================================================================="
echo "  Build Complete! NanoRecall hardware acceleration is ready."
echo "====================================================================="
