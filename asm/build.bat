@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo   NanoRecall - Building Native FASM 32-bit and 64-bit Engines
echo =====================================================================

cd /d "%~dp0"

set FASM=
if exist "C:\proekts\FASM\FASM.EXE" set FASM=C:\proekts\FASM\FASM.EXE
if not defined FASM if exist "C:\asm\hdd\FASM.EXE" set FASM=C:\asm\hdd\FASM.EXE
if not defined FASM (
    where fasm.exe >nul 2>&1
    if !ERRORLEVEL! equ 0 set FASM=fasm.exe
)
if not defined FASM (
    echo [ERROR] FASM.EXE not found in C:\proekts\FASM, C:\asm\hdd, or PATH
    exit /b 1
)

echo Using Flat Assembler: %FASM%
echo.

echo [1/4] Assembling nanorecall64.dll (x86-64 AVX2+FMA PE64 DLL) ...
"%FASM%" nanorecall64.asm nanorecall64.dll
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Assembly failed for nanorecall64.asm
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Assembling test_nanorecall64.exe (x86-64 Standalone Test Suite) ...
"%FASM%" test_nanorecall64.asm test_nanorecall64.exe
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Assembly failed for test_nanorecall64.asm
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Assembling nanorecall32.dll (x86 32-bit SSE2 PE32 DLL) ...
"%FASM%" nanorecall32.asm nanorecall32.dll
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Assembly failed for nanorecall32.asm
    exit /b %ERRORLEVEL%
)

echo.
echo [4/4] Assembling test_nanorecall32.exe (x86 32-bit Standalone Test Suite) ...
"%FASM%" test_nanorecall32.asm test_nanorecall32.exe
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Assembly failed for test_nanorecall32.asm
    exit /b %ERRORLEVEL%
)

echo.
echo =====================================================================
echo   All 4 Targets Built Successfully!
echo =====================================================================
echo.
echo --- Executing 64-bit Native Test Suite ---
test_nanorecall64.exe
if %ERRORLEVEL% neq 0 (
    echo [ERROR] test_nanorecall64.exe failed with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo --- Executing 32-bit Native Test Suite (WoW64) ---
test_nanorecall32.exe
if %ERRORLEVEL% neq 0 (
    echo [ERROR] test_nanorecall32.exe failed with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo [Sync] Copying DLLs to src/nanorecall package directory...
if exist "..\src\nanorecall" (
    copy /y nanorecall64.dll "..\src\nanorecall\nanorecall64.dll" >nul
    copy /y nanorecall32.dll "..\src\nanorecall\nanorecall32.dll" >nul
    echo [OK] DLLs copied to src\nanorecall\
)

echo.
echo [SUCCESS] Both 32-bit and 64-bit FASM Test Suites Passed Cleanly!
