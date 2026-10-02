@echo off
setlocal

REM ========================================
REM Сборка ll sdk программы в exe через NASM
REM ========================================

REM Устанавливаем PATH для NASM и GCC
set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"

REM Шаг 1: Компиляция loGlang -> NASM x64
echo [1/3] Compiling ll sdk code...
cd /d "C:\Users\Asus\Desktop\logsdk\loGsdk nasm"
py log2masm.py
if errorlevel 1 (
    echo Error: Python compilation failed
    pause
    exit /b 1
)

REM Шаг 2: Ассемблирование NASM -> OBJ
echo [2/3] Assembling with NASM...
cd /d "C:\Users\Asus\Desktop\ll sdk"
nasm -f win64 main.asm -o main.obj
if errorlevel 1 (
    echo Error: NASM assembly failed
    pause
    exit /b 1
)

REM Шаг 3: Линковка OBJ -> EXE
echo [3/3] Linking with GCC...
gcc main.obj -o main.exe -lkernel32
if errorlevel 1 (
    echo Error: GCC linking failed
    pause
    exit /b 1
)

echo.
echo Build successful!
echo Running program:
main.exe
echo.
pause