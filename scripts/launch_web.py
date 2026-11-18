"""
一键启动 Web GUI
================
双击 `启动.bat` 就能打开浏览器用工具。

行为:
  · 端口已被占用 → 认为服务已在跑, 直接开浏览器
  · 端口空闲     → 后台拉起 pick_gui.py, 等端口就绪再开浏览器
  · 启动失败     → 打印可读原因, 不留孤儿进程

用法:
  python scripts/launch_web.py            # 默认端口 9876
  python scripts/launch_web.py --port 9999
  python scripts/launch_web.py --no-browser
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex(('127.0.0.1', port)) == 0


def main():
    ap = argparse.ArgumentParser(description='一键启动 Web GUI')
    ap.add_argument('--port', type=int, default=9876)
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--wait', type=int, default=40, help='等待端口就绪秒数')
    args = ap.parse_args()

    url = f'http://127.0.0.1:{args.port}/'

    if port_in_use(args.port):
        print(f'✅ 端口 {args.port} 已在监听, 直接打开浏览器')
        if not args.no_browser:
            webbrowser.open(url)
        return 0

    print(f'启动 Web GUI (端口 {args.port})...')
    log = PROJECT_ROOT / 'logs' / 'web_gui.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    # pythonw.exe 无控制台窗口 (Windows 自带)
    pyw = Path(sys.executable).with_name('pythonw.exe')
    exe = str(pyw) if pyw.exists() else sys.executable

    with log.open('a', encoding='utf-8') as lf:
        if exe != sys.executable:
            proc = subprocess.Popen(
                [exe, str(PROJECT_ROOT / 'scripts' / 'pick_gui.py'),
                 '--port', str(args.port)],
                cwd=str(PROJECT_ROOT), stdout=lf, stderr=lf,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        else:
            proc = subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / 'scripts' / 'pick_gui.py'),
                 '--port', str(args.port)],
                cwd=str(PROJECT_ROOT), stdout=lf, stderr=lf)

    deadline = time.time() + args.wait
    while time.time() < deadline:
        if port_in_use(args.port):
            print(f'✅ 已就绪: {url}')
            print(f'   (PID {proc.pid}, 日志 {log})')
            if not args.no_browser:
                time.sleep(0.6)
                webbrowser.open(url)
            return 0
        if proc.poll() is not None:
            print(f'❌ 启动失败, 看日志: {log}')
            try:
                print(log.read_text(encoding='utf-8', errors='replace')[-1500:])
            except Exception:
                pass
            return 1
        time.sleep(0.5)

    print(f'❌ {args.wait} 秒内没就绪, 看日志: {log}')
    return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
