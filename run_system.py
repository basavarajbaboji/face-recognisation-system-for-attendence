import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("==================================================================")
    print("  [>] STARTING SMART CAMPUS CROWD ATTENDANCE SYSTEM")
    print("==================================================================")

    # 1. Start FastAPI Backend Process
    print("\n[1/2] Launching FastAPI Backend on http://localhost:8000...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR))

    # Wait 2 seconds for backend to bind port
    time.sleep(2)

    # 2. Start Vite Frontend Dev Server
    print("\n[2/2] Launching React Vite Command Center on http://localhost:5173...")
    frontend_dir = ROOT_DIR / "frontend"
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev", "--", "--host"], cwd=str(frontend_dir))

    time.sleep(2)
    print("\n==================================================================")
    print("  [*] SYSTEM RUNNING SUCCESSFULLY!")
    print("  ----------------------------------------------------------------")
    print("  [+] Web Command Center:   http://localhost:5173")
    print("  [+] API Documentation:   http://localhost:8000/docs")
    print("  [+] Live Video Stream:    http://localhost:8000/api/camera/stream")
    print("==================================================================")
    print("Press Ctrl+C in this terminal to stop both servers.\n")

    try:
        # Open browser automatically
        webbrowser.open("http://localhost:5173")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
