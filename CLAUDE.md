# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI services management hub ("AI HUB") - a FastAPI application that provides a web dashboard to monitor and start AI services running on the local network. It displays service status (running/not running) and allows starting services via batch scripts.

## Tech Stack

- **Python**: 3.12+ (managed via `.python-version`)
- **Package Manager**: uv (modern Python package manager)
- **Web Framework**: FastAPI with uvicorn
- **Templating**: Jinja2 (templates in `templates/hub.html`)
- **Platform**: Windows (uses batch scripts for service management)

## Common Commands

### Development

```bash
# Install dependencies
uv sync

# Run the server (use Python directly if uv trampoline fails)
.venv/Scripts/python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port 9000

# Or using uv
uv run uvicorn server:app --host 0.0.0.0 --port 9000
```

### Windows Batch Shortcuts

```bash
# Start the hub server
start_control.bat
```

## Architecture

### Core Components

1. **`server.py`** - FastAPI application with endpoints:
   - `GET /` - Renders `hub.html` template with service status
   - `GET /start?name={service_name}` - Starts a service by executing its batch script
   - `GET /stop?name={service_name}` - Stops a service by killing processes on its port
   - `GET /check?name={service_name}` - Returns JSON `{"running": true/false}`
   - `GET /logs?name={service_name}&lines=100` - Returns recent log lines

2. **`services.json`** - Configuration for managed services with fields:
   - `name` - Display name for the service
   - `port` - TCP port to check for service status
   - `url` - Full URL to open when clicking "打开"
   - `start_script` - Absolute path to the Windows batch file that starts the service

3. **`templates/hub.html`** - Jinja2 template for the dashboard UI with service cards, log panel, and info modal

4. **`scripts/`** - Windows batch files (`.bat`) that start external AI services. Each script:
   - Changes to the service's working directory
   - Uses `uv run` or direct Python to launch the service
   - Example: `start_sora.bat` launches Gradio app on port 7860

5. **`logs/services/`** - Service log files (`{service_name}.log`) with stdout/stderr from batch scripts

### Service Status Detection

`is_service_running()` in `server.py:141-151` checks service status by:
1. Attempting TCP connection to `127.0.0.1:{port}`
2. If that fails, extracting hostname from service's `url` field and trying that

This supports services bound to specific IPs (e.g., `192.168.252.126`).

### Service Lifecycle

1. User visits dashboard at `/`
2. Template receives `services` list (with `running` boolean) and `running_services` list
3. If running: shows green dot + "打开" + "停止" + "详情" buttons
4. If stopped: shows red dot + "启动" + "详情" buttons
5. Clicking start executes batch script via `subprocess.Popen()` in `start_service()` with output redirected to `logs/services/{name}.log`
6. `start_service()` sets environment variables including `TORCH_HOME`, `HF_HOME`, and `XDG_CACHE_HOME` to ensure AI services use the correct user cache directories
7. JavaScript polls `/check` every 4 seconds until service starts, then reloads page

### Frontend

- **Jinja2 Template**: `templates/hub.html` renders service cards and includes JavaScript
- **Log Panel**: Fixed bottom panel showing tabs for running services, fetches from `/logs` endpoint
- **Info Modal**: "详情" buttons show service descriptions defined in the `serviceInfo` JavaScript object
- **Data Passing**: `running_services` passed via `{{ running_services | tojson }}` Jinja2 filter

## Important Notes

- **Windows-specific**: Uses Windows batch scripts and absolute Windows paths (`D:\...`)
- **Environment Variables**: `start_service()` explicitly sets `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TORCH_HOME`, `HF_HOME`, and `XDG_CACHE_HOME` to ensure services find their data and cache in the correct user directories
- **Process Management**: Services run independently; stopping uses `taskkill /PID {pid} /F /T` on LISTENING processes only
- **Security**: The `/start` endpoint executes shell commands via `subprocess.Popen(..., shell=True)`
- **No authentication**: Dashboard has no built-in authentication
