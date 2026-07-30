@echo off
REM ============================================================
REM  ZenaidaVet - Lanzador de un click (Windows)
REM  - Usa el entorno que YA tenga todo instalado (venv o Python global).
REM  - Si no hay ninguno listo, crea un venv, instala e ingiere ejemplos.
REM ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title ZenaidaVet

echo(
echo   ============================================
echo      ZenaidaVet - Asistente de apoyo veterinario
echo   ============================================
echo(

REM --- Elegir como ejecutar (ZEN = comando de la CLI) -----------------
REM Se prueba cada opcion verificando que tenga los paquetes clave
REM (zenaidarag, pywebview y google-genai). Se usa la primera que sirva.
set "ZEN="

REM 1) Entorno virtual del proyecto, si esta completo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import zenaidarag, webview, google.genai" >nul 2>&1 && set "ZEN=.venv\Scripts\zenaidarag.exe"
)

REM 2) Python global "python".
if not defined ZEN (
    python -c "import zenaidarag, webview, google.genai" >nul 2>&1 && set "ZEN=python -m zenaidarag.cli"
)

REM 3) Lanzador "py -3".
if not defined ZEN (
    py -3 -c "import zenaidarag, webview, google.genai" >nul 2>&1 && set "ZEN=py -3 -m zenaidarag.cli"
)

REM --- Si nada esta listo: crear venv e instalar (primera vez) --------
if not defined ZEN (
    REM Buscar cualquier Python para construir el entorno.
    set "PYBUILD="
    where python >nul 2>&1 && set "PYBUILD=python"
    if not defined PYBUILD ( where py >nul 2>&1 && set "PYBUILD=py -3" )
    if not defined PYBUILD (
        echo [ERROR] No se encontro Python. Instalalo desde:
        echo         https://www.python.org/downloads/
        echo         Marca "Add Python to PATH" durante la instalacion.
        echo(
        pause
        exit /b 1
    )
    echo [1/3] Instalando ZenaidaVet ^(solo la primera vez, puede tardar varios minutos^)...
    if not exist ".venv\Scripts\python.exe" (
        %PYBUILD% -m venv .venv || ( echo [ERROR] No se pudo crear el entorno virtual. & pause & exit /b 1 )
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -e . || ( echo [ERROR] Fallo la instalacion. & pause & exit /b 1 )
    set "ZEN=.venv\Scripts\zenaidarag.exe"
)

REM --- Verificar la API key en .env -----------------------------------
if not exist ".env" (
    echo [aviso] No existe .env; creando uno a partir de .env.example...
    copy ".env.example" ".env" >nul
    echo(
    echo   ^>^>^> IMPORTANTE: pega tu GEMINI_API_KEY en el archivo .env ^<^<^<
    echo   Se abrira en el Bloc de notas. Guardalo y volve a ejecutar este .bat.
    echo(
    notepad ".env"
    pause
    exit /b 0
)

REM --- Ingerir documentos de ejemplo si no hay indice -----------------
if not exist "data\chroma" (
    echo [2/3] Preparando el indice con los documentos de ejemplo...
    %ZEN% ingest sample_docs || ( echo [ERROR] Fallo la ingesta inicial. & pause & exit /b 1 )
)

REM --- Abrir la app ---------------------------------------------------
echo [3/3] Abriendo ZenaidaVet...
echo(
%ZEN% app
if errorlevel 1 (
    echo(
    echo [ERROR] La app se cerro con error. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

endlocal
