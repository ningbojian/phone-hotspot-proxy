# -*- coding: utf-8 -*-
"""重建桌面快捷方式。

移动本文件夹后运行一次即可 —— 快捷方式记录的是绝对路径，
移动后原快捷方式会指向旧位置而失效。

本脚本通过 __file__ 定位自己所在目录，所以放到哪里都能用。
"""
import base64
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "proxy_gui.py")
LNK = os.path.join(os.path.expanduser("~"), "Desktop", "手机热点代理.lnk")


def find_pythonw():
    """优先找当前解释器同目录的 pythonw.exe，退回常见的 anaconda 路径。"""
    here = os.path.dirname(os.path.abspath(sys.executable))
    cand = os.path.join(here, "pythonw.exe")
    if os.path.exists(cand):
        return cand
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    for p in (os.path.join(home, "anaconda3", "pythonw.exe"),
              os.path.join(home, "miniconda3", "pythonw.exe"),
              os.path.join(local, "Programs", "Python", "Python313", "pythonw.exe"),
              os.path.join(local, "Programs", "Python", "Python312", "pythonw.exe"),
              r"C:\Python313\pythonw.exe"):
        if os.path.exists(p):
            return p
    return None


def main():
    if not os.path.exists(SCRIPT):
        print("找不到 proxy_gui.py，请确认本脚本和它在同一文件夹内")
        return 1

    pythonw = find_pythonw()
    if not pythonw:
        print("找不到 pythonw.exe")
        return 1

    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "$s = $ws.CreateShortcut('%s'); "
        "$s.TargetPath = '%s'; "
        "$s.Arguments = '\"%s\"'; "
        "$s.WorkingDirectory = '%s'; "
        "$s.Description = '连上手机热点后双击，自动开启/恢复系统代理'; "
        "$s.IconLocation = '%%SystemRoot%%\\System32\\shell32.dll,13'; "
        "$s.Save()"
    ) % (LNK, pythonw, SCRIPT, HERE)

    enc = base64.b64encode(ps.encode("utf-16-le")).decode("ascii")
    r = subprocess.run(["powershell", "-NoProfile", "-EncodedCommand", enc],
                       capture_output=True, timeout=60)

    if os.path.exists(LNK) and r.returncode == 0:
        print("快捷方式已重建:")
        print("  位置: %s" % LNK)
        print("  指向: %s" % SCRIPT)
        return 0
    print("重建失败，退出码 %d" % r.returncode)
    return 1


if __name__ == "__main__":
    sys.exit(main())
