#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 连接一键修复工具
功能：自动诊断 DNS/连接问题 → 通过 DoH 获取真实 IP → 写入 hosts → 刷新 DNS 缓存
适用：Windows，无代理环境
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import socket
import subprocess
import os
import sys
import re
import json
import urllib.request
import urllib.error
import platform
from datetime import datetime

# ============================================================
# 配置区
# ============================================================

# 需要修复的 GitHub 相关域名
GITHUB_DOMAINS = [
    "github.com",
    "raw.githubusercontent.com",
    "github.global.ssl.fastly.net",
    "codeload.github.com",
    "objects.githubusercontent.com",
    "api.github.com",
    "user-images.githubusercontent.com",
    "avatars.githubusercontent.com",
]

# DoH（DNS over HTTPS）服务商列表，按优先级排列，国内可用
DOH_PROVIDERS = [
    {
        "name": "阿里 DoH",
        "url": "https://dns.alidns.com/resolve?name={domain}&type=A",
        "parse": lambda d: [r["data"] for r in d.get("Answer", []) if r.get("type") == 1],
    },
    {
        "name": "腾讯 DoH",
        "url": "https://doh.pub/dns-query?name={domain}&type=A",
        "headers": {"Accept": "application/dns-json"},
        "parse": lambda d: [r["data"] for r in d.get("Answer", []) if r.get("type") == 1],
    },
    {
        "name": "Cloudflare",
        "url": "https://cloudflare-dns.com/dns-query?name={domain}&type=A",
        "headers": {"Accept": "application/dns-json"},
        "parse": lambda d: [r["data"] for r in d.get("Answer", []) if r.get("type") == 1],
    },
]

# 常见 git 镜像前缀
GIT_MIRRORS = [
    "https://gitclone.com/github.com/",
    "https://ghproxy.com/https://github.com/",
    "https://mirror.ghproxy.com/https://github.com/",
]

# hosts 文件路径（Windows）
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
# hosts 中标记块的起止标识
HOSTS_MARKER_BEGIN = "# === GitHub Fixer Begin ==="
HOSTS_MARKER_END = "# === GitHub Fixer End ==="


# ============================================================
# 工具函数
# ============================================================

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0


def run_as_admin():
    """以管理员权限重新启动自身"""
    if platform.system() == "Windows":
        import ctypes
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def get_hosts_path():
    """获取 hosts 文件路径，兼容不同系统"""
    system = platform.system()
    if system == "Windows":
        return HOSTS_PATH
    elif system == "Darwin" or system == "Linux":
        return "/etc/hosts"
    return HOSTS_PATH


def flush_dns():
    """刷新 DNS 缓存"""
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=10)
            return True, "DNS 缓存已刷新"
        elif system == "Darwin":
            subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, timeout=10)
            subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, timeout=10)
            return True, "DNS 缓存已刷新"
        elif system == "Linux":
            # 尝试多种 DNS 服务
            for cmd in [
                ["sudo", "systemctl", "restart", "nscd"],
                ["sudo", "systemctl", "restart", "systemd-resolved"],
            ]:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=10)
                except Exception:
                    pass
            return True, "DNS 缓存已刷新"
    except Exception as e:
        return False, f"DNS 刷新失败: {e}"
    return False, "不支持的操作系统"


def doh_resolve(domain, timeout=8):
    """
    通过 DoH 获取域名的真实 IP
    返回 (ip_list, provider_name)
    """
    for provider in DOH_PROVIDERS:
        try:
            url = provider["url"].format(domain=domain)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            if "headers" in provider:
                for k, v in provider["headers"].items():
                    req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ips = provider["parse"](data)
            if ips:
                return ips, provider["name"]
        except Exception:
            continue
    return [], None


def dns_resolve_system(domain):
    """使用系统 DNS 解析域名"""
    try:
        ips = socket.getaddrinfo(domain, 443, socket.AF_INET)
        return list(set(ip[4][0] for ip in ips))
    except Exception:
        return []


def check_http(url, timeout=8):
    """检测 HTTP 连接是否可达"""
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code  # 403/404 也算连通
    except Exception:
        return None


def check_port(host, port, timeout=5):
    """检测端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def read_hosts():
    """读取 hosts 文件内容"""
    path = get_hosts_path()
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def write_hosts(content):
    """写入 hosts 文件"""
    path = get_hosts_path()
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return True
    except PermissionError:
        return False
    except Exception as e:
        print(f"写入 hosts 失败: {e}")
        return False


def remove_github_hosts_block(content):
    """移除 hosts 中由本工具添加的标记块"""
    pattern = re.escape(HOSTS_MARKER_BEGIN) + r".*?" + re.escape(HOSTS_MARKER_END) + r"\n?"
    return re.sub(pattern, "", content, flags=re.DOTALL)


def build_hosts_block(ip_map):
    """构建 GitHub hosts 标记块"""
    lines = [HOSTS_MARKER_BEGIN, f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    for domain, ip in ip_map.items():
        lines.append(f"{ip:<20} {domain}")
    lines.append(HOSTS_MARKER_END)
    return "\n".join(lines) + "\n"


# ============================================================
# GUI 主程序
# ============================================================

class GitHubFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub 连接一键修复工具 v1.0")
        self.root.geometry("780x620")
        self.root.resizable(True, True)
        self.root.configure(bg="#f5f5f5")

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 780) // 2
        y = (self.root.winfo_screenheight() - 620) // 2
        self.root.geometry(f"780x620+{x}+{y}")

        self._build_ui()
        self._check_admin()

    def _build_ui(self):
        # 顶部标题栏
        title_frame = tk.Frame(self.root, bg="#24292e", height=56)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame, text="🔧 GitHub 连接一键修复工具",
            font=("Microsoft YaHei", 16, "bold"),
            bg="#24292e", fg="white"
        ).pack(side="left", padx=20, pady=12)

        self.admin_label = tk.Label(
            title_frame, text="", font=("Microsoft YaHei", 9),
            bg="#24292e", fg="#ffd33d"
        )
        self.admin_label.pack(side="right", padx=20)

        # 主内容区
        main = tk.Frame(self.root, bg="#f5f5f5")
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # ---- 诊断状态区 ----
        diag_frame = tk.LabelFrame(
            main, text=" 连接诊断 ", font=("Microsoft YaHei", 10, "bold"),
            bg="#f5f5f5", fg="#24292e", padx=12, pady=10
        )
        diag_frame.pack(fill="x")

        # 状态网格
        self.status_vars = {}
        status_items = [
            ("dns", "DNS 解析", "检测中..."),
            ("http", "HTTP 连接", "检测中..."),
            ("port443", "443 端口", "检测中..."),
            ("hosts", "Hosts 配置", "未检测"),
        ]
        for i, (key, label, default) in enumerate(status_items):
            tk.Label(
                diag_frame, text=f"{label}：", font=("Microsoft YaHei", 9),
                bg="#f5f5f5", anchor="e"
            ).grid(row=i, column=0, sticky="e", padx=(0, 8), pady=3)

            var = tk.StringVar(value=default)
            self.status_vars[key] = var
            tk.Label(
                diag_frame, textvariable=var, font=("Microsoft YaHei", 9, "bold"),
                bg="#f5f5f5", anchor="w"
            ).grid(row=i, column=1, sticky="w", pady=3)

        # 建议文本
        self.advice_var = tk.StringVar(value="点击「开始诊断」检测当前网络状况")
        tk.Label(
            diag_frame, textvariable=self.advice_var, font=("Microsoft YaHei", 9),
            bg="#fff5e6", fg="#d15704", wraplength=680, justify="left",
            padx=10, pady=6
        ).grid(row=0, column=2, rowspan=4, sticky="nsew", padx=(16, 0))
        diag_frame.grid_columnconfigure(2, weight=1)

        # ---- 按钮区 ----
        btn_frame = tk.Frame(main, bg="#f5f5f5")
        btn_frame.pack(fill="x", pady=12)

        self.btn_diagnose = tk.Button(
            btn_frame, text="🔍 开始诊断", font=("Microsoft YaHei", 10, "bold"),
            bg="#0366d6", fg="white", relief="flat", padx=20, pady=8,
            cursor="hand2", command=self._on_diagnose
        )
        self.btn_diagnose.pack(side="left", padx=(0, 8))

        self.btn_fix = tk.Button(
            btn_frame, text="⚡ 一键修复", font=("Microsoft YaHei", 10, "bold"),
            bg="#28a745", fg="white", relief="flat", padx=20, pady=8,
            cursor="hand2", command=self._on_fix
        )
        self.btn_fix.pack(side="left", padx=(0, 8))

        self.btn_restore = tk.Button(
            btn_frame, text="↩ 还原 Hosts", font=("Microsoft YaHei", 10),
            bg="#6a737d", fg="white", relief="flat", padx=16, pady=8,
            cursor="hand2", command=self._on_restore
        )
        self.btn_restore.pack(side="left", padx=(0, 8))

        self.btn_open_hosts = tk.Button(
            btn_frame, text="📄 查看 Hosts", font=("Microsoft YaHei", 10),
            bg="#6a737d", fg="white", relief="flat", padx=16, pady=8,
            cursor="hand2", command=self._on_open_hosts
        )
        self.btn_open_hosts.pack(side="left")

        # ---- 镜像加速区 ----
        mirror_frame = tk.LabelFrame(
            main, text=" Git 克隆加速 ", font=("Microsoft YaHei", 10, "bold"),
            bg="#f5f5f5", fg="#24292e", padx=12, pady=10
        )
        mirror_frame.pack(fill="x", pady=(0, 12))

        input_row = tk.Frame(mirror_frame, bg="#f5f5f5")
        input_row.pack(fill="x")
        tk.Label(input_row, text="仓库地址：", font=("Microsoft YaHei", 9), bg="#f5f5f5").pack(side="left")
        self.mirror_entry = tk.Entry(input_row, font=("Consolas", 9))
        self.mirror_entry.pack(side="left", fill="x", expand=True, padx=(4, 8), ipady=4)
        self.mirror_entry.insert(0, "https://github.com/用户名/仓库名.git")
        tk.Button(
            input_row, text="生成命令", font=("Microsoft YaHei", 9),
            bg="#0366d6", fg="white", relief="flat", padx=12, pady=4,
            cursor="hand2", command=self._on_gen_mirror
        ).pack(side="left")

        self.mirror_result = scrolledtext.ScrolledText(
            mirror_frame, height=5, font=("Consolas", 9),
            bg="#fafbfc", relief="solid", borderwidth=1
        )
        self.mirror_result.pack(fill="x", pady=(8, 0))
        self.mirror_result.insert("1.0", "在上方输入 GitHub 仓库地址，点击「生成命令」获取加速克隆命令")
        self.mirror_result.config(state="disabled")

        # ---- 日志区 ----
        log_frame = tk.LabelFrame(
            main, text=" 运行日志 ", font=("Microsoft YaHei", 10, "bold"),
            bg="#f5f5f5", fg="#24292e", padx=12, pady=8
        )
        log_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, font=("Consolas", 9), bg="#0d1117", fg="#c9d1d9",
            relief="flat", insertbackground="white"
        )
        self.log_text.pack(fill="both", expand=True)

        # 底部状态栏
        self.status_bar = tk.Label(
            self.root, text="就绪", font=("Microsoft YaHei", 8),
            bg="#e1e4e8", fg="#586069", anchor="w", padx=12
        )
        self.status_bar.pack(fill="x", side="bottom")

    def _check_admin(self):
        if is_admin():
            self.admin_label.config(text="✓ 管理员权限", fg="#3fb950")
        else:
            self.admin_label.config(text="⚠ 非管理员（修复需管理员权限）", fg="#f85149")

    def _log(self, msg, level="info"):
        """输出日志"""
        colors = {
            "info": "#c9d1d9",
            "success": "#3fb950",
            "warn": "#d29922",
            "error": "#f85149",
            "header": "#58a6ff",
        }
        color = colors.get(level, "#c9d1d9")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] ", "time")
        self.log_text.insert("end", msg + "\n", level)
        self.log_text.see("end")
        self.log_text.tag_config("time", foreground="#6e7681")
        self.log_text.tag_config(level, foreground=color)
        self.root.update_idletasks()

    def _set_status(self, key, text, color="#586069"):
        if key in self.status_vars:
            self.status_vars[key].set(text)

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.btn_diagnose.config(state=state)
        self.btn_fix.config(state=state)
        self.btn_restore.config(state=state)

    def _set_status_bar(self, text):
        self.status_bar.config(text=text)

    # ----------------------------------------------------------
    # 诊断功能
    # ----------------------------------------------------------
    def _on_diagnose(self):
        self._set_buttons_enabled(False)
        threading.Thread(target=self._do_diagnose, daemon=True).start()

    def _do_diagnose(self):
        self._log("=" * 50, "header")
        self._log("开始诊断 GitHub 连接状况...", "header")
        self._set_status_bar("正在诊断...")

        issues = []

        # 1. DNS 解析检测
        self._log("检测系统 DNS 解析 github.com ...")
        sys_ips = dns_resolve_system("github.com")
        if sys_ips:
            self._set_status("dns", f"正常 → {sys_ips[0]}", "#3fb950")
            self._log(f"系统 DNS 解析结果: {', '.join(sys_ips)}", "success")
        else:
            self._set_status("dns", "失败（DNS 污染）", "#f85149")
            self._log("系统 DNS 解析失败，疑似 DNS 污染", "error")
            issues.append("DNS 解析失败")

        # 2. DoH 对比检测
        self._log("通过 DoH 获取 github.com 真实 IP ...")
        real_ips, provider = doh_resolve("github.com")
        if real_ips:
            self._log(f"DoH ({provider}) 解析结果: {', '.join(real_ips)}", "success")
            if sys_ips and real_ips[0] not in sys_ips:
                self._log("⚠ 系统 DNS 与 DoH 结果不一致，确认存在 DNS 污染", "warn")
                issues.append("DNS 污染")
        else:
            self._log("DoH 解析也失败，可能网络完全阻断", "error")
            issues.append("网络完全阻断")

        # 3. HTTP 连接检测
        self._log("检测 HTTP 连接 https://github.com ...")
        status = check_http("https://github.com", timeout=8)
        if status:
            self._set_status("http", f"正常（HTTP {status}）", "#3fb950")
            self._log(f"HTTP 连接成功，状态码: {status}", "success")
        else:
            self._set_status("http", "超时/不可达", "#f85149")
            self._log("HTTP 连接超时", "error")
            issues.append("HTTP 连接超时")

        # 4. 443 端口检测
        self._log("检测 443 端口连通性 ...")
        target = sys_ips[0] if sys_ips else "github.com"
        port_ok = check_port(target, 443, timeout=5)
        if port_ok:
            self._set_status("port443", "开放", "#3fb950")
            self._log(f"443 端口 ({target}) 可达", "success")
        else:
            self._set_status("port443", "超时", "#f85149")
            self._log(f"443 端口 ({target}) 连接超时", "error")
            issues.append("443 端口阻断")

        # 5. Hosts 配置检测
        self._log("检测 hosts 文件中是否已有 GitHub 配置 ...")
        hosts_content = read_hosts()
        has_block = HOSTS_MARKER_BEGIN in hosts_content
        if has_block:
            self._set_status("hosts", "已配置（本工具）", "#3fb950")
            self._log("hosts 中已存在本工具添加的 GitHub 配置", "success")
        elif "github.com" in hosts_content:
            self._set_status("hosts", "已有手动配置", "#d29922")
            self._log("hosts 中存在 GitHub 相关配置（非本工具管理）", "warn")
        else:
            self._set_status("hosts", "未配置", "#d29922")
            self._log("hosts 中无 GitHub 配置", "warn")

        # 诊断结论
        self._log("-" * 50, "header")
        if not issues:
            self._log("✓ 诊断完成：网络连接正常，无需修复", "success")
            self.advice_var.set("网络状况良好，GitHub 应可正常访问。若仍有问题可尝试刷新页面或清除浏览器缓存。")
        else:
            self._log(f"诊断完成，发现 {len(issues)} 个问题: {', '.join(issues)}", "warn")
            advice = "建议点击「一键修复」自动写入真实 IP 到 hosts 文件。"
            if "网络完全阻断" in issues:
                advice = "网络可能被完全阻断，hosts 修复可能无效，建议使用代理或镜像站。"
            self.advice_var.set(advice)

        self._log("=" * 50, "header")
        self._set_status_bar("诊断完成")
        self._set_buttons_enabled(True)

    # ----------------------------------------------------------
    # 一键修复功能
    # ----------------------------------------------------------
    def _on_fix(self):
        if not is_admin():
            result = messagebox.askyesno(
                "需要管理员权限",
                "修改 hosts 文件需要管理员权限。\n\n是否以管理员身份重新启动程序？"
            )
            if result:
                run_as_admin()
                self.root.after(500, self.root.destroy)
            return

        self._set_buttons_enabled(False)
        threading.Thread(target=self._do_fix, daemon=True).start()

    def _do_fix(self):
        self._log("=" * 50, "header")
        self._log("开始一键修复 GitHub 连接...", "header")
        self._set_status_bar("正在修复...")

        ip_map = {}
        success_count = 0
        fail_domains = []

        # 1. 通过 DoH 获取所有域名的真实 IP
        self._log("步骤 1/4：通过 DoH 获取各域名真实 IP ...")
        for domain in GITHUB_DOMAINS:
            self._log(f"  解析 {domain} ...", "info")
            ips, provider = doh_resolve(domain)
            if ips:
                ip_map[domain] = ips[0]
                success_count += 1
                self._log(f"    ✓ {ips[0]}（via {provider}）", "success")
            else:
                fail_domains.append(domain)
                self._log(f"    ✗ 解析失败", "error")

        if not ip_map:
            self._log("所有域名解析均失败，无法继续修复", "error")
            self.advice_var.set("所有 DoH 服务商均无法访问，网络可能被完全阻断。建议使用代理工具或稍后重试。")
            self._set_status_bar("修复失败")
            self._set_buttons_enabled(True)
            return

        self._log(f"成功解析 {success_count}/{len(GITHUB_DOMAINS)} 个域名", "success")
        if fail_domains:
            self._log(f"以下域名解析失败（不影响主要功能）: {', '.join(fail_domains)}", "warn")

        # 2. 读取并更新 hosts
        self._log("步骤 2/4：更新 hosts 文件 ...")
        hosts_content = read_hosts()
        # 移除旧的标记块
        hosts_content = remove_github_hosts_block(hosts_content)
        # 确保末尾有空行
        if hosts_content and not hosts_content.endswith("\n"):
            hosts_content += "\n"
        # 添加新块
        new_block = build_hosts_block(ip_map)
        hosts_content += new_block

        if write_hosts(hosts_content):
            self._log("✓ hosts 文件写入成功", "success")
            self._set_status("hosts", "已配置（本工具）", "#3fb950")
        else:
            self._log("✗ hosts 文件写入失败（权限不足）", "error")
            self.advice_var.set("写入 hosts 失败，请以管理员身份运行本程序。")
            self._set_status_bar("修复失败")
            self._set_buttons_enabled(True)
            return

        # 3. 刷新 DNS 缓存
        self._log("步骤 3/4：刷新 DNS 缓存 ...")
        ok, msg = flush_dns()
        if ok:
            self._log(f"✓ {msg}", "success")
        else:
            self._log(f"⚠ {msg}", "warn")

        # 4. 验证修复效果
        self._log("步骤 4/4：验证修复效果 ...")
        # 清除 socket 缓存
        socket.setdefaulttimeout(5)
        verify_status = check_http("https://github.com", timeout=10)
        if verify_status:
            self._log(f"✓ 验证成功！GitHub HTTP 状态码: {verify_status}", "success")
            self._set_status("http", f"正常（HTTP {verify_status}）", "#3fb950")
            self.advice_var.set("修复完成！GitHub 现在应该可以正常访问了。请刷新浏览器页面。")
        else:
            self._log("⚠ 验证时 HTTP 仍超时，可能需要等待 DNS 生效或浏览器缓存未刷新", "warn")
            self.advice_var.set("Hosts 已更新，但验证时连接仍超时。请等待 1-2 分钟让 DNS 生效，或重启浏览器后再试。")

        self._log("=" * 50, "header")
        self._log("修复流程结束", "header")
        self._set_status_bar("修复完成")
        self._set_buttons_enabled(True)

        # 弹出提示
        self.root.after(0, lambda: messagebox.showinfo(
            "修复完成",
            f"已成功写入 {success_count} 条域名解析到 hosts 文件。\n\n"
            f"请刷新浏览器页面访问 GitHub。\n"
            f"如仍无法访问，请等待 1-2 分钟让 DNS 生效。"
        ))

    # ----------------------------------------------------------
    # 还原 Hosts
    # ----------------------------------------------------------
    def _on_restore(self):
        if not is_admin():
            result = messagebox.askyesno(
                "需要管理员权限",
                "修改 hosts 文件需要管理员权限。\n\n是否以管理员身份重新启动程序？"
            )
            if result:
                run_as_admin()
                self.root.after(500, self.root.destroy)
            return

        hosts_content = read_hosts()
        if HOSTS_MARKER_BEGIN not in hosts_content:
            messagebox.showinfo("提示", "hosts 文件中没有本工具添加的配置，无需还原。")
            return

        result = messagebox.askyesno(
            "确认还原",
            "将从 hosts 文件中移除本工具添加的所有 GitHub 配置。\n\n确认继续？"
        )
        if not result:
            return

        new_content = remove_github_hosts_block(hosts_content)
        if write_hosts(new_content):
            flush_dns()
            self._log("已移除 hosts 中的 GitHub 配置并刷新 DNS", "success")
            self._set_status("hosts", "未配置", "#d29922")
            messagebox.showinfo("还原成功", "已移除 GitHub 相关 hosts 配置。")
        else:
            messagebox.showerror("还原失败", "写入 hosts 文件失败，请检查权限。")

    # ----------------------------------------------------------
    # 查看 Hosts
    # ----------------------------------------------------------
    def _on_open_hosts(self):
        path = get_hosts_path()
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开 hosts 文件: {e}")

    # ----------------------------------------------------------
    # 镜像加速
    # ----------------------------------------------------------
    def _on_gen_mirror(self):
        url = self.mirror_entry.get().strip()
        if not url or "github.com" not in url:
            messagebox.showwarning("提示", "请输入有效的 GitHub 仓库地址")
            return

        # 提取 用户名/仓库名 部分
        match = re.search(r"github\.com[/:](.+?)(?:\.git)?$", url)
        if not match:
            messagebox.showwarning("提示", "无法解析仓库地址，请检查格式")
            return

        repo_path = match.group(1)
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]

        commands = []
        commands.append(f"# 原始命令")
        commands.append(f"git clone {url}")
        commands.append("")
        commands.append(f"# 加速方案 1（gitclone）")
        commands.append(f"git clone https://gitclone.com/github.com/{repo_path}.git")
        commands.append("")
        commands.append(f"# 加速方案 2（ghproxy）")
        commands.append(f"git clone https://ghproxy.com/https://github.com/{repo_path}.git")
        commands.append("")
        commands.append(f"# 加速方案 3（mirror.ghproxy）")
        commands.append(f"git clone https://mirror.ghproxy.com/https://github.com/{repo_path}.git")
        commands.append("")
        commands.append(f"# 如果已克隆但拉取慢，可设置远程地址：")
        commands.append(f"git remote set-url origin https://gitclone.com/github.com/{repo_path}.git")

        self.mirror_result.config(state="normal")
        self.mirror_result.delete("1.0", "end")
        self.mirror_result.insert("1.0", "\n".join(commands))
        self.mirror_result.config(state="disabled")
        self._log(f"已生成仓库 {repo_path} 的加速克隆命令", "info")


# ============================================================
# 入口
# ============================================================

def main():
    root = tk.Tk()
    try:
        # 设置 DPI 感知（Windows）
        if platform.system() == "Windows":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = GitHubFixerApp(root)

    # 启动时自动诊断一次
    root.after(500, app._on_diagnose)

    root.mainloop()


if __name__ == "__main__":
    main()
