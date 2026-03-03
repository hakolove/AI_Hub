from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess, socket, json, os, datetime
from urllib.parse import urlparse

app = FastAPI(docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(__file__)
CONFIG = os.path.join(BASE_DIR, "services.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs", "services")
os.makedirs(LOGS_DIR, exist_ok=True)

# 初始化模板
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def start_service(script_path, service_name):
    """启动服务并将输出保存到日志文件"""
    log_file = os.path.join(LOGS_DIR, f"{service_name}.log")

    # 写入启动标记
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"[{timestamp}] AI HUB: Starting {service_name}\n")
        f.write(f"[{timestamp}] AI HUB: Script: {script_path}\n")
        f.write(f"{'='*50}\n")
        f.flush()

    # 设置环境变量，确保 UTF-8 编码，并保留 Windows 用户目录相关变量
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # 确保用户目录环境变量正确传递（使用绝对路径）
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        env["USERPROFILE"] = userprofile
        env["HOME"] = userprofile
        env["APPDATA"] = os.path.join(userprofile, "AppData", "Roaming")
        env["LOCALAPPDATA"] = os.path.join(userprofile, "AppData", "Local")
        env["HOMEDRIVE"] = userprofile[:2] if len(userprofile) >= 2 else "C:"
        env["HOMEPATH"] = userprofile[2:] if len(userprofile) >= 2 else "\\Users\\dell"
        # Set PyTorch/HuggingFace cache directories to user profile
        env["TORCH_HOME"] = os.path.join(userprofile, ".cache", "torch")
        env["HF_HOME"] = os.path.join(userprofile, ".cache", "huggingface")
        env["XDG_CACHE_HOME"] = os.path.join(userprofile, ".cache")

    # 写入环境变量诊断信息
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] AI HUB: Environment:\n")
        f.write(f"[{timestamp}]   USERPROFILE={env.get('USERPROFILE', 'NOT SET')}\n")
        f.write(f"[{timestamp}]   APPDATA={env.get('APPDATA', 'NOT SET')}\n")
        f.write(f"[{timestamp}]   LOCALAPPDATA={env.get('LOCALAPPDATA', 'NOT SET')}\n")
        f.write(f"[{timestamp}]   HOME={env.get('HOME', 'NOT SET')}\n")
        f.write(f"[{timestamp}]   TORCH_HOME={env.get('TORCH_HOME', 'NOT SET')}\n")
        f.write(f"[{timestamp}]   HF_HOME={env.get('HF_HOME', 'NOT SET')}\n")
        f.flush()

    # 启动进程，输出重定向到文件（使用行缓冲）
    log_file_handle = open(log_file, "a", encoding="utf-8", buffering=1)
    subprocess.Popen(
        script_path,
        shell=True,
        env=env,
        stdout=log_file_handle,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        bufsize=1  # 行缓冲
    )


def stop_service(port):
    """停止占用指定端口的服务"""
    try:
        # 使用 netstat 查找占用端口的 PID（只找 LISTENING 状态的）
        result = subprocess.run(
            f"netstat -ano | findstr :{port} | findstr LISTENING",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout:
            return False, "未找到占用该端口的进程"

        # 解析输出获取 PID（排除 PID 0）
        lines = result.stdout.strip().split('\n')
        pids = set()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit() and pid != "0":
                    pids.add(pid)

        if not pids:
            return False, "未找到有效的进程 ID"

        # 终止所有相关进程（包括子进程）
        killed = []
        failed = []
        for pid in pids:
            try:
                # 使用 /T 参数终止进程及其所有子进程
                result = subprocess.run(
                    f"taskkill /PID {pid} /F /T",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    killed.append(pid)
                else:
                    failed.append(pid)
            except Exception as e:
                failed.append(f"{pid}({str(e)})")

        if killed:
            msg = f"已停止进程 (PID: {', '.join(killed)})"
            if failed:
                msg += f"，未能停止: {', '.join(failed)}"
            return True, msg
        return False, f"未能终止进程: {', '.join(failed) if failed else '未知错误'}"
    except Exception as e:
        return False, f"停止服务失败: {str(e)}"


def port_open(port, host="127.0.0.1"):
    """检查指定 host 和端口是否可连接"""
    s = socket.socket()
    try:
        s.connect((host, port))
        return True
    except:
        return False
    finally:
        s.close()


def is_service_running(s):
    """检查服务是否运行，先尝试本地连接，再尝试配置的URL"""
    port = s["port"]
    # 先尝试本地连接
    if port_open(port):
        return True
    # 本地失败，尝试从URL解析的host
    url_host = urlparse(s["url"]).hostname
    if url_host and url_host not in ("127.0.0.1", "localhost"):
        return port_open(port, url_host)
    return False


def load_services():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)["services"]


@app.get("/", response_class=HTMLResponse)
def hub(request: Request):
    services = []
    running_services = []

    for s in load_services():
        running = is_service_running(s)
        services.append({
            "name": s["name"],
            "port": s["port"],
            "url": s["url"],
            "running": running
        })
        if running:
            running_services.append(s["name"])

    return templates.TemplateResponse("hub.html", {
        "request": request,
        "services": services,
        "running_services": running_services
    })


@app.get("/logs")
def view_logs(name: str, lines: int = 100):
    """查看服务日志的最后N行"""
    log_file = os.path.join(LOGS_DIR, f"{name}.log")

    if not os.path.exists(log_file):
        return {"logs": "暂无日志", "exists": False}

    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"logs": "".join(last_lines), "exists": True}
    except Exception as e:
        return {"logs": f"读取日志失败: {str(e)}", "exists": False}


@app.get("/check")
def check_service(name: str):
    """检查服务是否已启动"""
    for s in load_services():
        if s["name"] == name:
            running = is_service_running(s)
            return {"running": running}
    return {"running": False, "error": "not found"}


@app.get("/start")
def start(name: str):
    for s in load_services():
        if s["name"] == name:
            if is_service_running(s):
                return {"status": "already_running"}
            start_service(s["start_script"], name)
            return {"status": "starting"}
    return {"status": "not_found"}


@app.get("/stop")
def stop(name: str):
    print(f"[STOP] Received stop request for: {name}")
    for s in load_services():
        if s["name"] == name:
            print(f"[STOP] Found service config: {s}")
            running = is_service_running(s)
            print(f"[STOP] Service running check: {running}")
            if not running:
                return {"msg": "not running"}
            success, message = stop_service(s["port"])
            print(f"[STOP] Stop result: success={success}, message={message}")
            return {"msg": message, "success": success}
    print(f"[STOP] Service not found: {name}")
    return {"msg": "not found"}
