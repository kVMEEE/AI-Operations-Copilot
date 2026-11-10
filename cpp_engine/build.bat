@echo off
cd /d "%~dp0"
echo ========================================================
echo Building AI Operations Copilot C++ Core Engine
echo ========================================================

if not exist "..\app\lib" mkdir "..\app\lib"
if not exist "build" mkdir "build"

echo Compiling C++ shared library with g++ (C++17, -O3)...
g++ -std=c++17 -O3 -shared -fPIC -Iinclude src\log_analyzer.cpp src\metrics_analyzer.cpp src\correlator.cpp src\c_api.cpp -o ..\app\lib\aiops_core.dll -static-libgcc -static-libstdc++

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Compiled C++ core library successfully to ..\app\lib\aiops_core.dll
    copy /Y ..\app\lib\aiops_core.dll build\aiops_core.dll >nul
) else (
    echo [ERROR] Compilation failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
