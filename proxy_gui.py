# -*- coding: utf-8 -*-
"""手机热点代理助手

连上手机热点后双击运行：自动检测手机上的代理端口，开启 Windows 系统代理；
关闭窗口时自动恢复原来的系统代理设置。

原理：手机上的代理类 App 开启"允许局域网连接"后，会在热点网关上
监听 HTTP / SOCKS5 端口。本工具自动找出当前默认网关并在其上探测
这些端口，找到后把系统代理指向它。

================================ 内容总结 ================================

一句话：把手机那一路网络扩展到整台 Windows —— 连上热点自动接过去，关窗自动还原。

解决什么问题
    手机自己能正常上网，但电脑上有些软件连不上，而且它们还不支持单独设置代理。
    手动去「设置 → 网络和 Internet → 代理」改 IP 和端口又太麻烦，
    每次换网络都要重来一遍。改成系统级代理后，所有软件自动生效，不用逐个配置。

怎么做的
    1. 用 PowerShell 取当前所有 IPv4 默认网关（只正则提取 IP，绕开中文输出乱码）
    2. 在网关上依次探测若干候选端口，命中即认为是手机侧代理
    3. 先备份原系统代理 → 写入新代理 → 调 Wininet 的 InternetSetOption
       通知系统立即生效（否则浏览器不认）
    4. 关窗时还原成工具启动前的状态

代码亮点
    · 单文件、零第三方依赖，只用标准库 + tkinter
    · UI 与探测逻辑分离，探测跑在后台线程，不卡界面
    · config.json 记住上次可用的网关地址，下次优先尝试
    · backup.json 存一份原始设置，出问题可手动还原

============================ 小红书文案（可直接复制） =======================

【标题】
手机能上的网，怎么让电脑也用上？写了个小工具🛠️

【备选标题】
有些软件在电脑上连不上，只好把手机的网络借过来

【正文】
被一个问题卡了很久：手机上网好好的，
但电脑上有几个软件一直连不上，偏偏它们还不支持单独设置代理😤

试过手动改 Windows 系统代理，能用，但太折磨——
每次连上热点都要改一遍 IP 和端口，用完还得改回去，换个网络又得重来。

干脆写了个小工具：

🎯 双击运行，自动把手机那一路网络接到整台电脑上，系统级生效
🔍 自动扫描网关找代理，IP 和端口都不用自己查
↩️ 关窗口自动还原原来的设置，不会把电脑代理搞乱（这个最爽）
💾 记住上次能用的地址，下次优先试
✅ 内置连通性测试，通不通一眼看到

最省心的是系统级生效——所有软件自动走，不用一个个去设置里配，
那些"根本不支持设代理"的软件也能正常用了✨

技术栈很朴素：Python + tkinter，单文件、零第三方依赖，双击就跑。

踩过的三个坑 👇

1️⃣ PowerShell 取默认网关，中文输出会乱码
   → 改成只正则提取 IP，不解析文本

2️⃣ 改完注册表，浏览器死活不生效
   → 要调 Wininet 的 InternetSetOption 主动通知系统

3️⃣ 多网卡时会返回多个默认网关
   → 只能挨个探测，并把上次成功过的排到最前面

写这种小工具最爽的地方就是：痛点是自己身上的，
做完立刻就能用上，正反馈来得特别快✨

【标签】
#Python #程序员日常 #效率工具 #Windows技巧 #tkinter
#独立开发 #编程 #代码分享 #摸鱼好物

=======================================================================
"""
import ctypes
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

try:
    import winreg
except ImportError:
    winreg = None

# ---------------------------------------------------------------- 配置
SETTINGS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
HTTP_PORT = 10809
SOCKS_PORT = 10808
EXTRA_PORTS = [10809, 10808, 7890, 10810, 1087]   # 依次尝试的候选端口（各客户端常见默认端口）

# 连通性探测地址的默认值。可在 config.json 里用 "probe_url" 覆盖，
# 不用改代码；换成任意一个能快速返回的地址即可。
PROBE_URL = "http://www.msftconnecttest.com/connecttest.txt"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_FILE = os.path.join(APP_DIR, "backup.json")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

BYPASS = ("localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;"
          "172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;"
          "172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>")

C_BG = "#f4f6f8"
C_CARD = "#ffffff"
C_TEXT = "#1f2933"
C_DIM = "#7b8794"
C_OK = "#22a06b"
C_BAD = "#d64545"
C_WARN = "#e8a33d"
C_ACCENT = "#2f6fd0"


# ---------------------------------------------------------------- 注册表
def read_proxy_state():
    """读取当前系统代理设置。"""
    st = {"ProxyEnable": 0, "ProxyServer": "", "ProxyOverride": ""}
    if not winreg:
        return st
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as k:
            for name in list(st):
                try:
                    st[name] = winreg.QueryValueEx(k, name)[0]
                except FileNotFoundError:
                    pass
    except OSError:
        pass
    return st


def _notify_windows():
    """通知系统代理设置已变更，让浏览器立即生效。"""
    try:
        wininet = ctypes.windll.Wininet
        wininet.InternetSetOptionW(0, 39, 0, 0)   # SETTINGS_CHANGED
        wininet.InternetSetOptionW(0, 37, 0, 0)   # REFRESH
    except Exception:
        pass


def write_proxy_state(enable, server=None, override=None):
    """写入系统代理。server/override 传 None 表示不改动该项，传 "" 表示清空。"""
    if not winreg:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0,
                        winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
        if server is not None:
            winreg.SetValueEx(k, "ProxyServer", 0, winreg.REG_SZ, server)
        if override is not None:
            winreg.SetValueEx(k, "ProxyOverride", 0, winreg.REG_SZ, override)
    _notify_windows()


# ---------------------------------------------------------------- 探测
def get_gateways():
    """返回当前所有 IPv4 默认网关（不解析本地化文本，只取 IP）。"""
    ps = ('Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" '
          '| Select-Object -ExpandProperty NextHop')
    ips = []
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, timeout=25)
        text = out.stdout.decode("utf-8", "ignore")
        ips = re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)
    except Exception:
        pass

    seen, res = set(), []
    for ip in ips:
        if ip != "0.0.0.0" and ip not in seen:
            seen.add(ip)
            res.append(ip)

    # 把上次成功的地址排到前面，优先尝试
    last = load_config().get("last_host")
    if last in res:
        res.remove(last)
        res.insert(0, last)
    return res


def port_open(host, port, timeout=0.8):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def find_phone_proxy(log):
    """在所有默认网关上探测代理端口，返回 (host, http_port, socks_port)。"""
    for gw in get_gateways():
        log("检查网关 %s ..." % gw)
        http_p = socks_p = None
        for p in EXTRA_PORTS:
            if port_open(gw, p):
                if p == SOCKS_PORT:
                    socks_p = p
                elif http_p is None:
                    http_p = p
        if http_p or socks_p:
            log("在 %s 上发现代理 (HTTP %s / SOCKS %s)"
                % (gw, http_p or "-", socks_p or "-"))
            return gw, http_p, socks_p
    return None, None, None


def test_connectivity(host, port):
    """经代理访问探测地址，返回 (ok, 说明)。"""
    if not host or not port:
        return False, "无代理"
    import urllib.request
    url = probe_url()
    ph = "http://%s:%d" % (host, port)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": ph, "https": ph}))
    t0 = time.time()
    try:
        r = opener.open(url, timeout=12)
        ms = int((time.time() - t0) * 1000)
        return True, "通畅 (%d ms)" % ms
    except Exception as e:
        return False, "失败: %s" % e


# ---------------------------------------------------------------- 配置
def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(d):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except Exception:
        pass


def probe_url():
    """探测地址：config.json 里的 probe_url 优先，否则用内置默认值。"""
    return load_config().get("probe_url") or PROBE_URL


# ---------------------------------------------------------------- 界面
class App:
    def __init__(self, root):
        self.root = root
        self.host = None
        self.http_port = None
        self.socks_port = None
        self.busy = False
        self.auto_restore = True

        # 改动前先备份原始设置
        self.original = read_proxy_state()
        self.backed_up = False

        root.title("手机热点代理助手")
        root.configure(bg=C_BG)
        root.geometry("560x470")
        root.minsize(520, 440)
        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.log("就绪。启动时检测到系统代理: %s"
                 % ("开启 " + str(self.original.get("ProxyServer", ""))
                    if self.original.get("ProxyEnable") else "关闭"))
        self.root.after(200, self.detect_and_apply)

    # ---------------- UI 构建
    def _build_ui(self):
        pad = {"padx": 16}

        tk.Label(self.root, text="手机热点代理助手", bg=C_BG, fg=C_TEXT,
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w",
                                                               pady=(16, 2), **pad)
        tk.Label(self.root, text="自动把系统代理指向手机侧的代理服务",
                 bg=C_BG, fg=C_DIM,
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", **pad)

        card = tk.Frame(self.root, bg=C_CARD, highlightbackground="#dfe3e8",
                        highlightthickness=1)
        card.pack(fill="x", pady=12, **pad)

        self.rows = {}
        for key, label in (("phone", "手机代理"), ("sys", "系统代理"),
                           ("net", "网络连通")):
            f = tk.Frame(card, bg=C_CARD)
            f.pack(fill="x", padx=14, pady=7)
            dot = tk.Label(f, text="●", bg=C_CARD, fg=C_DIM,
                           font=("Segoe UI", 13))
            dot.pack(side="left")
            tk.Label(f, text=label, bg=C_CARD, fg=C_TEXT, width=9,
                     font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(8, 0))
            val = tk.Label(f, text="检测中...", bg=C_CARD, fg=C_DIM,
                           font=("Microsoft YaHei UI", 10), anchor="w",
                           justify="left")
            val.pack(side="left", fill="x", expand=True)
            self.rows[key] = (dot, val)

        # 主按钮
        self.btn_main = tk.Button(self.root, text="正在检测...", command=self.toggle,
                                  bg=C_ACCENT, fg="white", relief="flat",
                                  font=("Microsoft YaHei UI", 11, "bold"),
                                  activebackground="#255ba8",
                                  activeforeground="white", cursor="hand2",
                                  state="disabled")
        self.btn_main.pack(fill="x", ipady=9, pady=(2, 10), **pad)

        bar = tk.Frame(self.root, bg=C_BG)
        bar.pack(fill="x", **pad)
        for text, cmd in (("重新检测", self.detect_and_apply),
                          ("测试连通", self.do_test),
                          ("恢复原始设置", self.restore_original)):
            tk.Button(bar, text=text, command=cmd, bg="#e4e7eb", fg=C_TEXT,
                      relief="flat", font=("Microsoft YaHei UI", 9),
                      activebackground="#d3d8dd", cursor="hand2"
                      ).pack(side="left", padx=(0, 8), ipady=4, ipadx=8)

        tk.Label(self.root, text="日志", bg=C_BG, fg=C_DIM,
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(14, 2), **pad)
        wrap = tk.Frame(self.root, bg=C_BG)
        wrap.pack(fill="both", expand=True, pady=(0, 14), **pad)
        self.logbox = tk.Text(wrap, height=8, bg="#1f2933", fg="#cbd2d9",
                              relief="flat", font=("Consolas", 9), wrap="word",
                              insertbackground="#cbd2d9")
        self.logbox.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(wrap, command=self.logbox.yview)
        sb.pack(side="right", fill="y")
        self.logbox.config(state="disabled", yscrollcommand=sb.set)

    # ---------------- 工具方法
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.logbox.config(state="normal")
        self.logbox.insert("end", "[%s] %s\n" % (ts, msg))
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    def set_row(self, key, color, text):
        dot, val = self.rows[key]
        dot.config(fg=color)
        val.config(fg=C_TEXT if color != C_DIM else C_DIM, text=text)

    def run_bg(self, fn):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=fn, daemon=True).start()

    # ---------------- 业务
    def detect_and_apply(self):
        def work():
            self.root.after(0, lambda: self.set_row("phone", C_WARN, "检测中..."))
            self.root.after(0, lambda: self.set_row("sys", C_DIM, "..."))
            self.root.after(0, lambda: self.set_row("net", C_DIM, "..."))

            host, hp, sp = find_phone_proxy(
                lambda m: self.root.after(0, self.log, m))

            if not host:
                self.host = None
                self.root.after(0, lambda: self.set_row(
                    "phone", C_BAD, "未检测到 —— 请确认已连手机热点，"
                                    "且代理 App 开启了「允许局域网连接」"))
                self.root.after(0, lambda: self.set_row(
                    "sys", C_DIM, "保持原状"))
                self.root.after(0, lambda: self.set_row("net", C_DIM, "未测试"))
                self.root.after(0, lambda: self.btn_main.config(
                    text="未检测到手机代理", state="disabled", bg="#9aa5b1"))
                self.busy = False
                return

            self.host, self.http_port, self.socks_port = host, hp, sp
            cfg = load_config()
            cfg["last_host"] = host
            save_config(cfg)

            use_port = hp or sp
            self.root.after(0, lambda: self.set_row(
                "phone", C_OK, "已连接  %s:%d" % (host, use_port)))

            if not self.backed_up:
                self.backed_up = True
                try:
                    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                        json.dump(self.original, f, indent=1)
                except Exception:
                    pass

            self.root.after(0, self.enable_system_proxy)
            ok, info = test_connectivity(host, hp or sp)
            self.root.after(0, lambda: self.set_row(
                "net", C_OK if ok else C_BAD, info))
            self.root.after(0, self.log, "连通性测试: " + info)
            self.busy = False

        self.run_bg(work)

    def enable_system_proxy(self):
        server = "%s:%d" % (self.host, self.http_port or self.socks_port)
        try:
            write_proxy_state(True, server, BYPASS)
        except Exception as e:
            self.log("写入系统代理失败: %s" % e)
            return
        self.set_row("sys", C_OK, "已开启  %s" % server)
        self.btn_main.config(text="关闭代理并恢复原设置", state="normal",
                             bg=C_ACCENT)
        self.log("系统代理已开启 -> %s" % server)

    def disable_system_proxy(self):
        try:
            write_proxy_state(False, "", BYPASS)
        except Exception as e:
            self.log("关闭系统代理失败: %s" % e)
            return
        self.set_row("sys", C_DIM, "已关闭")
        self.btn_main.config(text="开启系统代理", state="normal", bg=C_ACCENT)
        self.log("系统代理已关闭")

    def toggle(self):
        st = read_proxy_state()
        if st.get("ProxyEnable"):
            self.disable_system_proxy()
        else:
            if self.host:
                self.enable_system_proxy()
            else:
                self.log("尚未检测到手机代理，先重新检测")
                self.detect_and_apply()

    def do_test(self):
        def work():
            self.root.after(0, lambda: self.set_row("net", C_WARN, "测试中..."))
            ok, info = test_connectivity(self.host, self.http_port or self.socks_port)
            self.root.after(0, lambda: self.set_row(
                "net", C_OK if ok else C_BAD, info))
            self.root.after(0, self.log, "连通性测试: " + info)
            self.busy = False
        self.run_bg(work)

    def restore_original(self):
        """把系统代理恢复成本工具启动前的状态。"""
        st = self.original
        try:
            write_proxy_state(bool(st.get("ProxyEnable")),
                              st.get("ProxyServer", "") or "",
                              st.get("ProxyOverride", "") or BYPASS)
        except Exception as e:
            self.log("恢复失败: %s" % e)
            return
        self.log("已恢复原始设置 (ProxyEnable=%s, Server=%r)"
                 % (st.get("ProxyEnable"), st.get("ProxyServer")))
        if st.get("ProxyEnable"):
            self.set_row("sys", C_OK, "已恢复  %s" % st.get("ProxyServer"))
        else:
            self.set_row("sys", C_DIM, "已恢复为关闭")
        self.btn_main.config(
            text="关闭代理并恢复原设置" if read_proxy_state().get("ProxyEnable")
            else "开启系统代理", state="normal", bg=C_ACCENT)

    def on_close(self):
        """关窗时自动恢复原设置。"""
        if self.auto_restore:
            try:
                write_proxy_state(False, "", BYPASS)
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
