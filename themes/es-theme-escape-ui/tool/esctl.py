#!/usr/bin/env python3
"""Small helpers around EmulationStation for escape/UI: read/write its settings, restart it safely.

  esctl.py apply KEY=VALUE ...   wait for the calling port to end, stop ES, write the settings, start ES
  esctl.py get KEY               print a setting
Values: subset.<name>=<value>, ThemeSet=..., UseCustomCollectionsSystem=true|false
"""
import os
import re
import subprocess
import sys
import time
import urllib.request
from xml.sax.saxutils import escape as xml_escape

ES_SETTINGS = "/userdata/system/configs/emulationstation/es_settings.cfg"
ES_INIT = "/etc/init.d/S31emulationstation"
API = "http://127.0.0.1:1234"
LOG = "/userdata/system/configs/escape-ui/esctl.log"


def log(*a):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")
    except OSError:
        pass


def procs(pattern):
    out = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = open("/proc/%s/cmdline" % pid, "rb").read().replace(b"\0", b" ").decode(errors="ignore")
        except OSError:
            continue
        if pattern in cmd and str(os.getpid()) != pid:
            out.append(int(pid))
    return out


def env():
    return {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/userdata/system", "XDG_RUNTIME_DIR": "/var/run", "LANG": "en_US.UTF-8"}


def api_up():
    try:
        with urllib.request.urlopen(API + "/", timeout=3):
            return True
    except Exception:
        return False


def get(key):
    try:
        txt = open(ES_SETTINGS, encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r'<\w+ name="%s" value="([^"]*)"' % re.escape(key), txt)
    return m.group(1) if m else None


def set_many(pairs):
    txt = open(ES_SETTINGS, encoding="utf-8").read()
    for key, val in pairs:
        tag = "bool" if val in ("true", "false") else "string"
        line = '<%s name="%s" value="%s" />' % (tag, xml_escape(key, {'"': "&quot;"}), xml_escape(val, {'"': "&quot;"}))
        pat = re.compile(r'<\w+ name="%s" value="[^"]*"\s*/>' % re.escape(key))
        if pat.search(txt):
            txt = pat.sub(lambda m: line, txt, count=1)   # a function: a "\" in the value is not a group reference
        else:
            txt = txt.replace("</config>", "\t" + line + "\n</config>")
    tmp = ES_SETTINGS + ".escape-ui.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(txt)
    os.replace(tmp, ES_SETTINGS)
    os.sync()


def es_stop():
    subprocess.run(["emulationstation-standalone", "--stop-rebooting"], env=env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([ES_INIT, "stop"], env=env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
    for pid in procs("emulationstation-standalone") + procs("emulationstation --"):   # a boot-time loop can survive a stop
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    for _ in range(50):
        if not procs("emulationstation --"):
            break
        time.sleep(0.2)


def es_start():
    subprocess.Popen([ES_INIT, "start"], env=env(), start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(180):
        if api_up():
            return True
        time.sleep(0.5)
    return False


def apply(pairs, wait_for=None):
    """Runs detached: lets the port that called it close first, so ES has the screen back."""
    log("apply", pairs)
    for _ in range(300):
        if not wait_for or not procs(wait_for):
            break
        time.sleep(0.2)
    time.sleep(1.5)
    es_stop(); time.sleep(1)
    if pairs:
        set_many(pairs)
    ok = es_start()
    log("es back" if ok else "es did not come back")


def apply_detached(pairs, wait_for):
    args = [sys.executable, os.path.abspath(__file__), "apply", "--wait", wait_for] + ["%s=%s" % kv for kv in pairs]
    subprocess.Popen(args, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "get":
        print(get(a[1]) or "")
    elif a and a[0] == "apply":
        wait = None
        if len(a) > 2 and a[1] == "--wait":
            wait = a[2]; a = a[2:]
        apply([tuple(x.split("=", 1)) for x in a[1:] if "=" in x], wait)
    else:
        print(__doc__)
