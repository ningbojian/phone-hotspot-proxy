# 手机热点代理助手
<!-- profile-agent:readme:start -->
🇨🇳 [中文](README.md) · 🇺🇸 [English](README.en.md)
# 手机热点代理助手

<!-- managed:start -->
连上手机热点后双击运行，自动把 Windows 系统代理接到手机侧的代理服务上；
关闭窗口时自动关闭系统代理。

> **它解决什么问题**：手机自己能正常上网，但电脑上有些软件连不上，
> 而它们还不支持单独设置代理。手动去改 Windows 系统代理又太麻烦 ——
> 每次换网络都要改一遍 IP 和端口，用完还得改回来。
> 做成系统级代理后，所有软件自动生效，不用逐个配置。

## 特性

- **自动探测** — 遍历当前所有 IPv4 默认网关，在候选端口上探测可用代理，不用手动查 IP 和端口
- **一键切换** — 双击即自动接上；关窗或点按钮即关闭
- **不破坏原设置** — 改动前先把原始代理设置备份到 `backup.json`，随时可一键还原
- **记住可用地址** — 上次探测成功的网关记在 `config.json`，下次优先尝试
- **连通性测试** — 内置测试按钮，通不通一眼看到
- **零依赖** — 只用 Python 标准库 + tkinter，单文件，不需要 `pip install`
<!-- managed:end -->

## 环境要求

- **Windows** — 用到注册表、PowerShell 和 Wininet，不支持 macOS / Linux
- **Python 3.7+** — 依赖 `subprocess.run(capture_output=...)`，该参数 3.7 引入
- **tkinter** — Windows 官方 Python 安装包和 conda 环境都自带

## 快速开始

1. 克隆本仓库，或用 `git clone` 之外的方式下载 `proxy_gui.py`
2. 运行：
   - 双击 `run-debug.bat` —— 带控制台，方便看报错
   - 或命令行 `python proxy_gui.py`
3. 想要桌面快捷方式（无控制台窗口），双击 `重建快捷方式.bat`

### 前置条件

手机侧需要运行一个在局域网内监听的代理类 App，并开启「允许来自局域网的连接」。
电脑连上**该手机的热点**之后，本工具才能探测到它。

内置候选端口：`10809`、`10808`、`7890`、`10810`、`1087`。
要加自己的端口，改 `proxy_gui.py` 里的 `EXTRA_PORTS`。

## 工作原理

1. 用 PowerShell 的 `Get-NetRoute` 取出所有 IPv4 默认网关
   （只正则提取 IP，不解析本地化文本，绕开中文系统下的输出乱码）
2. 在每个网关上依次 TCP 探测候选端口，命中即认为是手机侧代理
3. 把原系统代理备份到 `backup.json`，再写入新的 `ProxyEnable` / `ProxyServer` / `ProxyOverride`
4. 调用 Wininet 的 `InternetSetOptionW(39/37)` 通知系统
   —— 不调这一步，注册表虽然改了但浏览器不会生效
5. 关窗时关闭系统代理；点「恢复原始设置」则读回备份还原

## 文件说明

| 文件 | 作用 | 入库 |
|---|---|---|
| `proxy_gui.py` | 主程序，单文件 | ✅ |
| `run-debug.bat` | 带控制台的启动器，方便看 traceback | ✅ |
| `重建快捷方式.bat` | 在桌面生成/修复快捷方式（用 `pythonw.exe`，无控制台窗口） | ✅ |
| `rebuild_shortcut.py` | 上面那个 bat 实际调用的脚本。用 `__file__` 定位自己，文件夹随便移 | ✅ |
| `test agent b` | B 模式的手动验证备注（内容为「测试 B模式是否生效」），不参与打包与运行 | ✅ |
| `config.json` | 上次可用的网关、可选的 `probe_url` 覆盖 | ❌ 已 gitignore |
| `backup.json` | 改动前的原始代理设置 | ❌ 已 gitignore |

> 两个 `.bat` 都按「真实安装路径 → `py` 启动器 → PATH 上的 `python`」的顺序找解释器，
> 并且会跳过 `%LOCALAPPDATA%\Microsoft\WindowsApps` 下的 Microsoft Store 占位程序
> —— 那个 `python.exe` 在非交互调用时什么都不干，直接用它会导致双击没反应。

> `test agent b` 只是一份纯文本的验证备注，程序不会读取它，删掉也不影响运行。

## 配置

`config.json` 首次运行后自动生成，两个可选字段：

```json
{
  "last_host": "192.168.1.1",
  "probe_url": "http://example.com/generate_204"
}
```

- `last_host` — 上次探测成功的网关，会被排到候选列表最前面
- `probe_url` — 连通性测试访问的地址，用来覆盖内置默认值。
  默认是 `http://www.msftconnecttest.com/connecttest.txt`（只验证代理本身活没活）。
  想测「代理能不能通到某个特定站点」，把它改成对应地址即可，不用改代码。

## 常见问题

**检测不到手机代理？**
确认电脑连的是手机热点而不是别的 WiFi，且手机上的代理 App 开了「允许局域网连接」。

**一直显示「未检测到」？**
部分手机开热点时会做客户端隔离，电脑和手机之间互相不可见。换一种热点模式或换台手机试试。

**测试通过但还是打不开网页？**
点一次「重新检测」。系统代理变更后，少数浏览器需要重启才能识别。

**改了端口没生效？**
`EXTRA_PORTS` 是列表，按顺序全部探测，不是只测第一个。

## 已知限制

- 只设置 HTTP 代理，不处理 PAC / 自动配置脚本
- **关窗时是「关闭代理」，不是「恢复原样」** —— `on_close` 里写死了 `ProxyEnable=0`。
  如果你原本就开着别的代理，请用「恢复原始设置」按钮而不是直接关窗
- `HTTP_PORT` 常量目前没有被任何代码引用，是定义残留
- 只支持 IPv4

## 许可证

MIT，见 [LICENSE](LICENSE)。
<!-- profile-agent:readme:end -->

连上手机热点后双击运行，自动把 Windows 系统代理接到手机侧的代理服务上；
关闭窗口时自动关闭系统代理。

> **它解决什么问题**：手机自己能正常上网，但电脑上有些软件连不上，
> 而它们还不支持单独设置代理。手动去改 Windows 系统代理又太麻烦 ——
> 每次换网络都要改一遍 IP 和端口，用完还得改回来。
> 做成系统级代理后，所有软件自动生效，不用逐个配置。

## 特性

- **自动探测** — 遍历当前所有 IPv4 默认网关，在候选端口上探测可用代理，不用手动查 IP 和端口
- **一键切换** — 双击即自动接上；关窗或点按钮即关闭
- **不破坏原设置** — 改动前先把原始代理设置备份到 `backup.json`，随时可一键还原
- **记住可用地址** — 上次探测成功的网关记在 `config.json`，下次优先尝试
- **连通性测试** — 内置测试按钮，通不通一眼看到
- **零依赖** — 只用 Python 标准库 + tkinter，单文件，不需要 `pip install`

## 环境要求

- **Windows** — 用到注册表、PowerShell 和 Wininet，不支持 macOS / Linux
- **Python 3.7+** — 依赖 `subprocess.run(capture_output=...)`，该参数 3.7 引入
- **tkinter** — Windows 官方 Python 安装包和 conda 环境都自带

## 快速开始

1. 克隆本仓库，或用 `git clone` 之外的方式下载 `proxy_gui.py`
2. 运行：
   - 双击 `run-debug.bat` —— 带控制台，方便看报错
   - 或命令行 `python proxy_gui.py`
3. 想要桌面快捷方式（无控制台窗口），双击 `重建快捷方式.bat`

### 前置条件

手机侧需要运行一个在局域网内监听的代理类 App，并开启「允许来自局域网的连接」。
电脑连上**该手机的热点**之后，本工具才能探测到它。

内置候选端口：`10809`、`10808`、`7890`、`10810`、`1087`。
要加自己的端口，改 `proxy_gui.py` 里的 `EXTRA_PORTS`。

## 工作原理

1. 用 PowerShell 的 `Get-NetRoute` 取出所有 IPv4 默认网关
   （只正则提取 IP，不解析本地化文本，绕开中文系统下的输出乱码）
2. 在每个网关上依次 TCP 探测候选端口，命中即认为是手机侧代理
3. 把原系统代理备份到 `backup.json`，再写入新的 `ProxyEnable` / `ProxyServer` / `ProxyOverride`
4. 调用 Wininet 的 `InternetSetOptionW(39/37)` 通知系统
   —— 不调这一步，注册表虽然改了但浏览器不会生效
5. 关窗时关闭系统代理；点「恢复原始设置」则读回备份还原

## 文件说明

| 文件 | 作用 | 入库 |
|---|---|---|
| `proxy_gui.py` | 主程序，单文件 | ✅ |
| `run-debug.bat` | 带控制台的启动器，方便看 traceback | ✅ |
| `重建快捷方式.bat` | 在桌面生成/修复快捷方式（用 `pythonw.exe`，无控制台窗口） | ✅ |
| `rebuild_shortcut.py` | 上面那个 bat 实际调用的脚本。用 `__file__` 定位自己，文件夹随便移 | ✅ |
| `config.json` | 上次可用的网关、可选的 `probe_url` 覆盖 | ❌ 已 gitignore |
| `backup.json` | 改动前的原始代理设置 | ❌ 已 gitignore |

> 两个 `.bat` 都按「真实安装路径 → `py` 启动器 → PATH 上的 `python`」的顺序找解释器，
> 并且会跳过 `%LOCALAPPDATA%\Microsoft\WindowsApps` 下的 Microsoft Store 占位程序
> —— 那个 `python.exe` 在非交互调用时什么都不干，直接用它会导致双击没反应。

## 配置

`config.json` 首次运行后自动生成，两个可选字段：

```json
{
  "last_host": "192.168.1.1",
  "probe_url": "http://example.com/generate_204"
}
```

- `last_host` — 上次探测成功的网关，会被排到候选列表最前面
- `probe_url` — 连通性测试访问的地址，用来覆盖内置默认值。
  默认是 `http://www.msftconnecttest.com/connecttest.txt`（只验证代理本身活没活）。
  想测「代理能不能通到某个特定站点」，把它改成对应地址即可，不用改代码。

## 常见问题

**检测不到手机代理？**
确认电脑连的是手机热点而不是别的 WiFi，且手机上的代理 App 开了「允许局域网连接」。

**一直显示「未检测到」？**
部分手机开热点时会做客户端隔离，电脑和手机之间互相不可见。换一种热点模式或换台手机试试。

**测试通过但还是打不开网页？**
点一次「重新检测」。系统代理变更后，少数浏览器需要重启才能识别。

**改了端口没生效？**
`EXTRA_PORTS` 是列表，按顺序全部探测，不是只测第一个。

## 已知限制

- 只设置 HTTP 代理，不处理 PAC / 自动配置脚本
- **关窗时是「关闭代理」，不是「恢复原样」** —— `on_close` 里写死了 `ProxyEnable=0`。
  如果你原本就开着别的代理，请用「恢复原始设置」按钮而不是直接关窗
- `HTTP_PORT` 常量目前没有被任何代码引用，是定义残留
- 只支持 IPv4

## 许可证

MIT，见 [LICENSE](LICENSE)。
