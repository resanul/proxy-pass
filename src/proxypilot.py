"""ProxyPilot v1.0 — Windows proxy configuration utility.

Configures WinINET, optional WinHTTP, and user environment proxy variables.
It is not a transparent packet tunnel; applications may ignore these settings.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener
import winreg

APP_NAME = "ProxyPilot"
VERSION = "1.0.0"
STATE_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
BACKUP_FILE = STATE_DIR / "backup.json"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
TEST_URL = "https://cloudcode-pa.googleapis.com/"

def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, shell=False)

def get_registry_settings() -> dict:
    result = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride", "AutoConfigURL"):
            try:
                value, kind = winreg.QueryValueEx(key, name)
                result[name] = {"value": value, "type": kind}
            except FileNotFoundError:
                result[name] = None
    return result

def env_snapshot() -> dict:
    names = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
             "http_proxy", "https_proxy", "all_proxy", "no_proxy")
    result = {name: None for name in names}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
            for name in names:
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    result[name] = {"value": value, "type": kind}
                except FileNotFoundError:
                    pass
    except OSError:
        pass
    return result

def set_reg(name: str, value, kind: int) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        if value is None:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, name, 0, kind, value)

def set_user_env(name: str, value) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        if value is None:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)

def notify_windows() -> None:
    try:
        import ctypes
        wininet = ctypes.WinDLL("wininet", use_last_error=True)
        wininet.InternetSetOptionW(None, 39, None, 0)  # SETTINGS_CHANGED
        wininet.InternetSetOptionW(None, 37, None, 0)  # REFRESH
    except Exception:
        pass

class ProxyPilotApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"ProxyPilot v{VERSION}")
        root.geometry("760x690")
        root.minsize(700, 620)
        self.host = tk.StringVar(value="")
        self.port = tk.StringVar(value="3128")
        self.bypass = tk.StringVar(value="localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>")
        self.use_winhttp = tk.BooleanVar(value=False)
        self.use_env = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready. Enter the Squid host/IP and listener port.")
        self._ui()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def _ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="ProxyPilot", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, text=f"Windows Proxy Manager  •  Version {VERSION}").pack(anchor="w", pady=(0, 15))
        frame = ttk.LabelFrame(outer, text="Squid proxy (no authentication)", padding=12)
        frame.pack(fill="x")
        row = ttk.Frame(frame); row.pack(fill="x")
        ttk.Label(row, text="Host / IP").pack(side="left")
        ttk.Entry(row, textvariable=self.host, width=32).pack(side="left", padx=(8, 20))
        ttk.Label(row, text="Port").pack(side="left")
        ttk.Entry(row, textvariable=self.port, width=10).pack(side="left", padx=8)
        ttk.Label(frame, text="Enter a Squid listener reachable from this Windows PC.").pack(anchor="w", pady=(7, 0))
        ttk.Label(frame, text="Bypass list (semicolon-separated)").pack(anchor="w", pady=(10, 3))
        ttk.Entry(frame, textvariable=self.bypass).pack(fill="x")

        opts = ttk.LabelFrame(outer, text="Settings to configure", padding=12)
        opts.pack(fill="x", pady=10)
        ttk.Label(opts, text="Windows Internet Settings (WinINET) will always be configured.").pack(anchor="w")
        ttk.Checkbutton(opts, text="Also configure WinHTTP (may require Administrator)", variable=self.use_winhttp).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts, text="Set user-level HTTP_PROXY / HTTPS_PROXY / ALL_PROXY variables", variable=self.use_env).pack(anchor="w", pady=2)

        buttons = ttk.Frame(outer); buttons.pack(fill="x", pady=3)
        ttk.Button(buttons, text="Test Proxy", command=self.test_proxy).pack(side="left")
        ttk.Button(buttons, text="Apply", command=self.apply).pack(side="left", padx=8)
        ttk.Button(buttons, text="Restore Backup", command=self.restore).pack(side="left")
        ttk.Button(buttons, text="Reset to Direct", command=self.reset).pack(side="left", padx=8)

        diag = ttk.LabelFrame(outer, text="Diagnostics", padding=10)
        diag.pack(fill="both", expand=True, pady=(9, 5))
        ttk.Label(diag, textvariable=self.status, wraplength=680).pack(anchor="w")
        self.log = tk.Text(diag, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(7, 0))
        ttk.Label(outer, text="Note: ProxyPilot configures proxy-aware apps; it does not force every app's traffic through Squid.",
                  foreground="#9a5b00", wraplength=700).pack(anchor="w", pady=(7, 0))

    def log_line(self, message: str):
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def endpoint(self):
        host = self.host.get().strip()
        if not host:
            raise ValueError("Enter the Squid host or IP.")
        try:
            port = int(self.port.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise ValueError("Port must be an integer from 1 to 65535.")
        return host, port, f"http://{host}:{port}"

    def test_proxy(self):
        try:
            host, port, proxy = self.endpoint()
        except ValueError as exc:
            messagebox.showerror("Invalid proxy", str(exc)); return
        self.status.set("Testing Squid TCP listener, then HTTPS via proxy…")
        threading.Thread(target=self._test_worker, args=(host, port, proxy), daemon=True).start()

    def _test_worker(self, host, port, proxy):
        lines = []
        try:
            with socket.create_connection((host, port), timeout=5):
                lines.append(f"TCP listener: PASS — {host}:{port}")
        except Exception as exc:
            lines.append(f"TCP listener: FAIL — {exc}")
            self.root.after(0, lambda: self._test_done(lines))
            return
        try:
            opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
            request = Request(TEST_URL, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
            with opener.open(request, timeout=15) as response:
                lines.append(f"HTTPS: HTTP {response.status}; response received through proxy.")
        except URLError as exc:
            lines.append(f"HTTPS: FAIL — {getattr(exc, 'reason', exc)}")
            lines.append("Inspect Squid/WSA logs. HTTP 401/403/404 responses may still mean an endpoint responded.")
        except Exception as exc:
            lines.append(f"HTTPS: FAIL — {exc}")
        self.root.after(0, lambda: self._test_done(lines))

    def _test_done(self, lines):
        for line in lines:
            self.log_line(line)
        self.status.set(lines[-1] if lines else "Test complete.")

    def save_backup_once(self):
        if BACKUP_FILE.exists():
            return
        data = {"wininet": get_registry_settings(), "env": env_snapshot()}
        try:
            result = run_cmd(["netsh", "winhttp", "show", "proxy"])
            data["winhttp_show"] = {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        except Exception as exc:
            data["winhttp_show"] = {"stdout": str(exc)}
        BACKUP_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_line(f"Original settings backed up to: {BACKUP_FILE}")

    def apply(self):
        try:
            host, port, proxy = self.endpoint()
            self.save_backup_once()
            set_reg("ProxyEnable", 1, winreg.REG_DWORD)
            set_reg("ProxyServer", f"http={host}:{port};https={host}:{port}", winreg.REG_SZ)
            set_reg("ProxyOverride", self.bypass.get().strip(), winreg.REG_SZ)
            notify_windows()
            self.log_line("Applied WinINET settings.")
            if self.use_env.get():
                for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                    set_user_env(name, proxy)
                self.log_line("Updated user proxy environment variables; restart applications to inherit them.")
            if self.use_winhttp.get():
                bypass = "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*"
                result = run_cmd(["netsh", "winhttp", "set", "proxy", f"{host}:{port}", bypass])
                output = result.stdout.strip() or result.stderr.strip() or f"exit code {result.returncode}"
                self.log_line(f"WinHTTP: {output}")
                if result.returncode:
                    self.log_line("WinHTTP may require running ProxyPilot as Administrator.")
            self.status.set(f"Configured {proxy}. Restart apps to apply environment variables.")
            messagebox.showinfo("ProxyPilot", "Proxy settings applied to supported clients.\nRestart Antigravity and other applications.\nThis does not force every application's traffic through Squid.")
        except Exception as exc:
            messagebox.showerror("Apply failed", str(exc))

    def restore(self):
        if not BACKUP_FILE.exists():
            messagebox.showwarning("Backup unavailable", "No original settings backup exists yet."); return
        if not messagebox.askyesno("Restore", "Restore the original settings saved before the first Apply?"):
            return
        try:
            data = json.loads(BACKUP_FILE.read_text(encoding="utf-8"))
            for name, item in data.get("wininet", {}).items():
                set_reg(name, None if item is None else item["value"], winreg.REG_SZ if item is None else item["type"])
            for name, item in data.get("env", {}).items():
                set_user_env(name, None if item is None else item["value"])
            notify_windows()
            self.log_line("Restored WinINET and user environment values.")
            saved_output = data.get("winhttp_show", {}).get("stdout", "")
            if "Direct access (no proxy server)" in saved_output:
                result = run_cmd(["netsh", "winhttp", "reset", "proxy"])
                self.log_line("WinHTTP: " + (result.stdout.strip() or result.stderr.strip()))
            elif self.use_winhttp.get():
                self.log_line("WinHTTP's previous non-direct configuration needs manual restoration from your approved configuration.")
            self.status.set("Restore processed. Restart applications.")
        except Exception as exc:
            messagebox.showerror("Restore failed", str(exc))

    def reset(self):
        if not messagebox.askyesno("Reset to direct", "Disable WinINET proxy and remove ProxyPilot user proxy variables?"):
            return
        try:
            set_reg("ProxyEnable", 0, winreg.REG_DWORD)
            notify_windows()
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
                set_user_env(name, None)
            self.log_line("Disabled WinINET proxy and removed ProxyPilot environment variables.")
            if self.use_winhttp.get() and messagebox.askyesno("WinHTTP", "Also reset WinHTTP to direct access?"):
                result = run_cmd(["netsh", "winhttp", "reset", "proxy"])
                self.log_line("WinHTTP: " + (result.stdout.strip() or result.stderr.strip()))
            self.status.set("Reset processed. Restart applications.")
        except Exception as exc:
            messagebox.showerror("Reset failed", str(exc))

def main():
    if sys.platform != "win32":
        print("ProxyPilot is intended for Windows.")
        raise SystemExit(1)
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    ProxyPilotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
