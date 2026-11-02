#!/usr/bin/env python3
"""escape/UI's watcher for the charger (runs from boot: /userdata/system/custom.sh).

1. The charging screen: plugged in and nothing pressed for SCREEN_AFTER seconds, on ES's menus
   (no game) -> ES is paused and charge_screen.py shows the boot screen with a random figure and
   glitch bursts, until a button or unplugging; then ES carries on, and after another SCREEN_AFTER
   seconds untouched (still charging) it comes back with a new figure. ES's own
   battery icon can't do this: on the home screen it only looks at the battery when the view is shown.
   At plug-in the figure's loop is drawn ahead (two cores) so the screen runs smooth from frame one.
3. Smooth mode (theme option escape-perf, on by default): on ES's menus the CPU governor is
   "performance" so the figure videos and the screens never wait for the clock to ramp up. A game
   gets its own governor from emulatorlauncher; under 15 % without the charger the system's own
   setting comes back; turning the option off restores it too.
4. The missing accent colours: charging + no game + no button for IDLE seconds -> `gen.py
   --all-colours` at the lowest priority; a button, unplugging or a game stops it, the next run goes on.
"""
import glob
import os
import select
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
IDLE = 300                      # seconds without a button before drawing colours
SCREEN_AFTER = 15               # seconds after plugging in (untouched) before the charging screen
CHECK = 60                      # how often to look
PIDFILE = "/tmp/escape-ui-charged.pid"
BOOT_GRACE = 60                 # no charging screen in the first minute (ES is still starting)
CACHE = "/tmp/escape-charge"    # charge_screen.py --prepare draws a loop here
LOG = "/userdata/system/configs/escape-ui/gen.log"


def charging():
    for p in glob.glob("/sys/class/power_supply/*usb*/online") + glob.glob("/sys/class/power_supply/*ac*/online"):
        try:
            if open(p).read().strip() == "1":
                return True
        except OSError:
            pass
    try:
        return open(glob.glob("/sys/class/power_supply/*battery*/status")[0]).read().strip() in ("Charging", "Full")
    except (OSError, IndexError):
        return False


def playing():
    """A game or a port is running (ES starts them through emulatorlauncher or a port script)."""
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = open("/proc/%s/cmdline" % pid, "rb").read()
        except OSError:
            continue
        if b"emulatorlauncher" in cmd or b"/userdata/roms/ports/" in cmd or b"retroarch" in cmd:
            return True
    return False


_missing = {"sig": None, "at": 0.0, "val": False}


def library_sig():
    """What the drawing depends on, by modification times only (a stat per rom folder, no file scan):
    the gamelists, the rom folders, ES's settings and collections, escape/UI's config."""
    sys.path.insert(0, HERE)
    import gen
    paths = [os.path.join(gen.ES_DIR, "es_settings.cfg"), os.path.join(gen.ES_DIR, "collections"), gen.CFG]
    paths += glob.glob(os.path.join(gen.USERDATA, "roms", "*")) + glob.glob(os.path.join(gen.USERDATA, "roms", "*", "gamelist.xml"))
    sig = []
    for p in sorted(paths):
        try:
            sig.append((p, os.stat(p).st_mtime))
        except OSError:
            pass
    return tuple(sig)


def missing():
    """Are some accent colours not drawn yet? ready_accents() walks every rom folder on the card (slow
    on the exFAT FUSE mount), so the answer is kept until something it depends on changes, or 30 min."""
    sys.path.insert(0, HERE)
    import gen
    import art
    sig, now = library_sig(), time.time()
    if sig == _missing["sig"] and now - _missing["at"] < 1800:
        return _missing["val"]
    try:
        val = len(gen.ready_accents()) < len(art.PALETTE)
    except Exception:
        val = False
    _missing.update(sig=sig, at=now, val=val)
    return val


def es_pids():
    out = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                cmd = open("/proc/%s/cmdline" % pid, "rb").read().split(b"\0")
            except OSError:
                continue
            if cmd and os.path.basename(cmd[0]) == b"emulationstation":
                out.append(int(pid))
    return out


GOV = "/sys/devices/system/cpu/cpufreq/policy0/scaling_governor"


def system_governor():
    try:
        for line in open("/userdata/system/batocera.conf"):
            if line.startswith("system.cpu.governor="):
                return line.split("=", 1)[1].strip() or "schedutil"
    except OSError:
        pass
    return "schedutil"


def set_governor(name):
    try:
        if open(GOV).read().strip() != name:
            with open(GOV, "w") as f:
                f.write(name)
    except OSError:
        pass


def battery_level():
    try:
        return int(open(glob.glob("/sys/class/power_supply/*battery*/capacity")[0]).read().strip())
    except Exception:
        return 100


def perf_on():
    sys.path.insert(0, HERE)
    import gen
    return gen.es_setting("subset.escape-perf") != "off"


def screen_on():
    sys.path.insert(0, HERE)
    import gen
    return gen.es_setting("subset.escape-charge") != "off"


def loop_ready():
    """A loop to show: drawn ahead by gen.py for the colour in use, or prepared into CACHE. Without one
    the screen would draw the figure live, which takes the whole CPU (and the Wi-Fi with it)."""
    import json
    sys.path.insert(0, HERE)
    import gen
    root = os.path.join(gen.GEN, gen.current_accent(), "charge")
    try:
        if any(os.path.exists(os.path.join(root, f, "meta.json")) for f in os.listdir(root)):
            return True
    except OSError:
        pass
    try:
        return os.path.exists(os.path.join(CACHE, "meta.json")) and bool(json.load(open(os.path.join(CACHE, "meta.json"))))
    except Exception:
        return False


def prepare():
    """Draw a loop into CACHE in the background (two cores, low priority); nothing when gen.py's are there."""
    return subprocess.Popen([sys.executable, os.path.join(HERE, "charge_screen.py"), "--prepare"], start_new_session=True,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def charging_screen():
    """Pause ES, show the charging screen until a button or unplugging, carry on with ES."""
    pids = es_pids()
    if not pids:
        return
    for p in pids:
        os.kill(p, signal.SIGSTOP)
    try:   # ES's last frame, for the charging screen's way back (its figure glitches in)
        time.sleep(0.1)
        with open("/tmp/escape-es.ppm", "wb") as shot:
            subprocess.run(["fbdump"], stdout=shot, stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        try:
            os.remove("/tmp/escape-es.ppm")
        except OSError:
            pass
    try:   # a SIGTERM here ends run() with SystemExit: it kills the screen and the finally lets ES go on
        with open("/tmp/escape-charge-screen.log", "w") as err:
            subprocess.run([sys.executable, os.path.join(HERE, "charge_screen.py")], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=err, timeout=12 * 3600)
    except Exception:
        pass
    finally:
        for p in pids:
            try:
                os.kill(p, signal.SIGCONT)
            except OSError:
                pass


def stop(job):
    try:
        os.killpg(job.pid, signal.SIGTERM)
        job.wait(10)
    except Exception:
        try:
            os.killpg(job.pid, signal.SIGKILL)
        except Exception:
            pass


def main():
    try:   # one at a time
        old = int(open(PIDFILE).read())
        os.kill(old, 0)
        return
    except (OSError, ValueError):
        pass
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    # stopped while ES is paused (swap.sh restarting us, shutdown): leave through the finally blocks so
    # ES is never left frozen behind a charging screen that is gone
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    fds = []
    for p in glob.glob("/dev/input/event*"):
        try:
            fds.append(os.open(p, os.O_RDONLY | os.O_NONBLOCK))
        except OSError:
            pass
    for p in es_pids():   # in case an earlier run died with ES paused
        try:
            os.kill(p, signal.SIGCONT)
        except OSError:
            pass
    started = time.time()
    last_input, last_check, job, prep, prep_at = time.time(), 0.0, None, None, 0.0
    was_plugged, plugged_at = False, time.time()   # already on the charger at boot counts as plugging in
    last_gov, perf_set = 0.0, False
    while True:
        ready = select.select(fds, [], [], 1)[0] if fds else (time.sleep(1) or [])
        if ready:
            for fd in ready:
                try:
                    os.read(fd, 4096)
                except OSError:
                    pass
            last_input = time.time()
            if job:
                stop(job); job = None
        if job and job.poll() is not None:
            job = None
        now = time.time()
        plugged = charging()
        if plugged and not was_plugged:
            plugged_at = now
            if screen_on() and not loop_ready() and not (prep and prep.poll() is None):   # draw the loop while the 15 s run
                prep, prep_at = prepare(), now
        elif plugged and now - prep_at >= 120:   # every 2 min on the charger: did the last try leave a loop?
            prep_at = now
            if not (prep and prep.poll() is None) and screen_on() and not playing() and not loop_ready():
                prep = prepare()
        was_plugged = plugged
        if (plugged and now - started >= BOOT_GRACE and now - max(plugged_at, last_input) >= SCREEN_AFTER
                and es_pids() and not playing() and screen_on() and not (prep and prep.poll() is None) and loop_ready()):
            charging_screen()
            last_input = time.time()   # back on the menus: another SCREEN_AFTER untouched brings it back
            prep, prep_at = prepare(), time.time()   # next figure (returns at once when gen.py's loops are there)
        if now - last_gov >= 2:   # smooth mode, checked every 2 s (a game sets its own governor)
            last_gov = now
            if not playing():
                want_perf = perf_on() and (plugged or battery_level() > 15) and es_pids()
                if want_perf:
                    set_governor("performance"); perf_set = True
                elif perf_set:
                    set_governor(system_governor()); perf_set = False
        if job and (not charging() or playing()):
            stop(job); job = None
        if not job and now - last_check >= CHECK:
            last_check = now
            if charging() and now - last_input >= IDLE and not playing() and missing():
                with open(LOG, "a") as log:   # the child keeps its own copy of the handle
                    log.write(time.strftime("[escape-ui] %H:%M charging and idle: drawing the other colours\n")); log.flush()
                    job = subprocess.Popen(["nice", "-n", "19", sys.executable, os.path.join(HERE, "gen.py"), "--all-colours", "--jobs=2"],
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                _missing["sig"] = None   # look again once this run is over


if __name__ == "__main__":
    main()
