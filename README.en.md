# Phone Hotspot Proxy Helper

🇨🇳 [中文](README.md) · 🇺🇸 [English](README.en.md)

<!-- managed:start -->
Double-click after connecting to your phone's hotspot and the tool automatically points the Windows system proxy at the proxy service running on the phone; closing the window turns the system proxy off again.

> **What it solves**: The phone itself has internet access, but some desktop apps can't connect — and they don't support setting a proxy of their own. Editing the Windows system proxy by hand is tedious: every network change means re-entering the IP and port, and undoing it afterwards. As a system-wide proxy, everything picks it up automatically with no per-app configuration.

## Features

- **Auto discovery** — walks every IPv4 default gateway and probes the candidate ports for a live proxy, so no manual IP or port lookup
- **One-click toggle** — double-click to connect; close the window or click the button to disconnect
- **Leaves your settings intact** — the original proxy settings are backed up to `backup.json` before any change, restorable in one click
- **Remembers the working address** — the gateway that last probed successfully is stored in `config.json` and tried first next time
- **Connectivity test** — a built-in test button shows at a glance whether it works
- **Zero dependencies** — Python standard library + tkinter only, single file, no `pip install`
<!-- managed:end -->

## Requirements

- **Windows** — uses the registry, PowerShell and Wininet; macOS / Linux are not supported
- **Python 3.7+** — relies on `subprocess.run(capture_output=...)`, which was added in 3.7
- **tkinter** — bundled with the official Windows Python installer and with conda

## Quick start

1. Clone this repository, or download `proxy_gui.py` some other way
2. Run it:
   - Double-click `run-debug.bat` — keeps a console open so errors are visible
   - Or run `python proxy_gui.py` from a terminal
3. Want a desktop shortcut (no console window)? Double-click `重建快捷方式.bat`

### Prerequisites

The phone needs a proxy app listening on the LAN with 'allow connections from the LAN' enabled. The PC can only discover it after connecting to **that phone's hotspot**.

Built-in candidate ports: `10809`, `10808`, `7890`, `10810`, `1087`. To add your own, edit `EXTRA_PORTS` in `proxy_gui.py`.

## How it works

1. Use PowerShell `Get-NetRoute` to collect all IPv4 default gateways
   (extract the IPs with a regex only and never parse localized text, which sidesteps garbled output on non-English systems)
2. TCP-probe the candidate ports on each gateway in turn; the first hit is treated as the phone-side proxy
3. Back up the current system proxy to `backup.json`, then write the new `ProxyEnable` / `ProxyServer` / `ProxyOverride`
4. Call Wininet's `InternetSetOptionW(39/37)` to notify the system
   — without this step the registry changes don't take effect in browsers
5. Closing the window disables the system proxy; 'restore original settings' reads the backup back

## Files

| File | Purpose | Tracked |
|---|---|---|
| `proxy_gui.py` | Main program, single file | ✅ |
| `run-debug.bat` | Launcher that keeps a console open for tracebacks | ✅ |
| `重建快捷方式.bat` | Creates/repairs the desktop shortcut (uses `pythonw.exe`, no console window) | ✅ |
| `rebuild_shortcut.py` | The script that bat actually calls. Locates itself via `__file__`, so the folder can move anywhere | ✅ |
| `test agent b` | Manual verification note for B mode (its content is '测试 B模式是否生效'), not used at build or run time | ✅ |
| `config.json` | Last working gateway, optional `probe_url` override | ❌ gitignored |
| `backup.json` | Original proxy settings from before the change | ❌ gitignored |

> Both `.bat` files look for an interpreter in the order 'real install path → `py` launcher → `python` on PATH',
> and skip the Microsoft Store stub under `%LOCALAPPDATA%\Microsoft\WindowsApps`
> — that `python.exe` does nothing when called non-interactively, so using it makes double-click appear to do nothing.

> `test agent b` is just a plain-text verification note; the program never reads it, and deleting it changes nothing.

## Configuration

`config.json` is generated on first run and has two optional fields:

```json
{
  "last_host": "192.168.1.1",
  "probe_url": "http://example.com/generate_204"
}
```

- `last_host` — the gateway that last probed successfully; it is moved to the front of the candidate list
- `probe_url` — the URL the connectivity test hits, overriding the built-in default.
  The default is `http://www.msftconnecttest.com/connecttest.txt` (it only checks that the proxy itself is alive).
  To test whether the proxy can reach a specific site, point this at that address — no code changes needed.

## FAQ

**Can't find the phone proxy?**
Make sure the PC is on the phone's hotspot and not another Wi-Fi, and that the proxy app on the phone has 'allow LAN connections' enabled.

**It always says 'not detected'?**
Some phones isolate clients on their hotspot, so the PC and the phone can't see each other. Try another hotspot mode or another phone.

**The test passes but pages still won't load?**
Click 're-detect' once. After a system proxy change, a few browsers need a restart to notice it.

**Changed the port but nothing happened?**
`EXTRA_PORTS` is a list: every entry is probed in order, not just the first one.

## Known limitations

- Sets an HTTP proxy only; PAC / auto-config scripts are not handled
- **Closing the window disables the proxy rather than restoring the previous state** — `on_close` hard-codes `ProxyEnable=0`.
  If you already had another proxy enabled, use the 'restore original settings' button instead of just closing the window
- The `HTTP_PORT` constant is currently referenced nowhere; it is a leftover definition
- IPv4 only

## License

MIT, see [LICENSE](LICENSE).