@echo off
REM Build a C++ bot on Windows.
REM   Usage (from the participant_kit folder):
REM       tools\build_cpp.bat templates\cpp\my_bot.cpp
REM
REM Uses g++ (MinGW-w64 / MSYS2) if available, otherwise MSVC (cl.exe) from a
REM "x64 Native Tools Command Prompt for Visual Studio".

if "%~1"=="" (
    echo Usage: tools\build_cpp.bat ^<source.cpp^> [output_name_without_exe]
    exit /b 1
)

set SOURCE=%~1
set OUTPUT=%~2
if "%OUTPUT%"=="" set OUTPUT=%~dpn1
set KIT_DIR=%~dp0..
if exist "%KIT_DIR%\w64devkit\bin" set PATH=%KIT_DIR%\w64devkit\bin;%PATH%

where g++ >nul 2>nul
if %ERRORLEVEL%==0 (
    echo Compiling %SOURCE% with g++ ...
    g++ -std=c++17 -O2 -Wall -Wextra -I "%KIT_DIR%\third_party" "%SOURCE%" -o "%OUTPUT%.exe"
    goto :done
)

where cl >nul 2>nul
if %ERRORLEVEL%==0 (
    echo Compiling %SOURCE% with MSVC ...
    cl /nologo /std:c++17 /O2 /EHsc /I "%KIT_DIR%\third_party" "%SOURCE%" /Fe:"%OUTPUT%.exe"
    goto :done
)

echo No C++ compiler found. Install MSYS2 g++ or Visual Studio Build Tools (see docs\03_how_to_run.md).
exit /b 1

:done
echo Done. Run it with:  %OUTPUT%.exe
