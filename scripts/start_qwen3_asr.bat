@echo off
echo [INFO] Starting Qwen3 ASR...
echo [INFO] Working directory: D:\Qwen3_ASR
cd /d "D:\Qwen3_ASR"

set "ROOT_DIR=D:\Qwen3_ASR\"
set "PYTHON_PATH=%ROOT_DIR%WPy64-312101\python"
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%ROOT_DIR%bin;%PATH%"
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="

set "ASR_PATH=%ROOT_DIR%models\Qwen\Qwen3-ASR-0.6B"
set "ALIGN_PATH=%ROOT_DIR%models\Qwen\Qwen3-ForcedAligner-0.6B"

echo [INFO] Launching Qwen3-ASR on port 7867 (0.0.0.0)...
"%PYTHON_PATH%\python.exe" -m qwen_asr.cli.demo ^
  --asr-checkpoint "%ASR_PATH%" ^
  --aligner-checkpoint "%ALIGN_PATH%" ^
  --backend transformers ^
  --ip 0.0.0.0 --port 7867
