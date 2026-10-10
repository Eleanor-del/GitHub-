# GitHub 连接一键修复工具 - 使用说明

## 这是什么

一个 Windows 图形界面工具，自动诊断 GitHub 无法访问的问题，并一键修复。
无需代理工具，无需手动查 IP、改 hosts，全程点按钮即可。

## 功能

| 功能 | 说明 |
|------|------|
| 🔍 开始诊断 | 自动检测 DNS 解析、HTTP 连接、443 端口、Hosts 配置 |
| ⚡ 一键修复 | 通过 DoH 获取真实 IP → 写入 hosts → 刷新 DNS → 验证 |
| ↩ 还原 Hosts | 移除工具添加的所有 GitHub 配置 |
| 📄 查看 Hosts | 直接打开系统 hosts 文件 |
| Git 克隆加速 | 输入仓库地址，自动生成 3 种加速克隆命令 |

## 运行方法

### 方法一：直接运行 Python 脚本（推荐）

1. 确保已安装 Python 3.7+（从 https://www.python.org/downloads/ 下载，安装时勾选 "Add Python to PATH"）
2. 右键 `github_fixer.py` → **以管理员身份运行**
   - 或者：右键开始菜单 → Windows PowerShell (管理员) → 输入：
     ```
     python github_fixer.py
     ```

> ⚠️ **必须以管理员身份运行**，否则无法修改 hosts 文件。
> 程序启动时会自动检测权限，非管理员运行时点击「一键修复」会提示提权。

### 方法二：打包成 exe（双击即用，无需 Python）

如果你想做成独立 exe 文件，在安装了 Python 的电脑上执行：

```bash
pip install pyinstaller
pyinstaller -F -w --uac-admin -n "GitHub修复工具" github_fixer.py
```

打包完成后，exe 文件在 `dist` 目录下，双击即可运行（会自动请求管理员权限）。

## 使用步骤

1. **以管理员身份启动程序**，程序会自动开始诊断
2. 查看诊断结果：
   - 绿色 = 正常
   - 红色 = 有问题
   - 橙色提示框会给出具体建议
3. 点击 **「⚡ 一键修复」**，等待 10-30 秒
4. 看到"修复完成"提示后，**刷新浏览器**访问 github.com

## 修复原理

1. 通过 **DNS over HTTPS (DoH)** 从阿里/腾讯/Cloudflare 获取 GitHub 各域名的真实 IP（绕过被污染的本地 DNS）
2. 将 IP ↔ 域名映射写入系统 hosts 文件（带标记块，可一键还原）
3. 执行 `ipconfig /flushdns` 刷新 DNS 缓存
4. 发起 HTTP 请求验证连通性

覆盖的域名：github.com、raw.githubusercontent.com、github.global.ssl.fastly.net、codeload.github.com、objects.githubusercontent.com、api.github.com 等 8 个关键域名。

## Git 克隆加速

在「Git 克隆加速」区域粘贴 GitHub 仓库地址，点击「生成命令」，会得到：
- 原始命令
- gitclone 加速
- ghproxy 加速
- mirror.ghproxy 加速
- 已克隆仓库的远程地址修改命令

任选一条复制到命令行执行即可。

## 常见问题

**Q: 修复后还是打不开？**
A: 等待 1-2 分钟让 DNS 生效，或重启浏览器。也可能是 GitHub IP 又变了，重新点一次「一键修复」。

**Q: 提示"所有 DoH 服务商均无法访问"？**
A: 说明网络对 GitHub 的阻断较深，hosts 方式可能无效。建议使用代理工具，或用「Git 克隆加速」中的镜像地址。

**Q: 会影响其他网站吗？**
A: 不会。工具只在 hosts 中添加 GitHub 相关域名，且用标记块管理，可随时一键还原。

**Q: hosts 文件在哪里？**
A: `C:\Windows\System32\drivers\etc\hosts`，点击程序中的「📄 查看 Hosts」可直接打开。

## 还原方法

如果不想用了，点击「↩ 还原 Hosts」即可移除所有配置，系统恢复原样。
