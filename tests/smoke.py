#!/usr/bin/env python3
"""Hardware check: runs every command against the real headphones, then restores their previous state.

Needs the headphones on and connected. Usage: python3 tests/smoke.py
"""
import json, os, subprocess, sys

CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edifier-control")
failed = []


def run(*args):
    p = subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, timeout=90)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def check(label, args, expect=None):
    code, out, err = run(*args)
    ok = code == 0 and (expect is None or expect in out)
    print(f"{'ok  ' if ok else 'FAIL'} {label:<22} {out or err}"[:110])
    if not ok:
        failed.append(label)
    return out


def status():
    code, out, err = run("status")
    if code:
        sys.exit(f"cannot read status: {err}")
    return json.loads(out)


before = status()
print("before:", {k: before.get(k) for k in ("mode", "ambient_level", "audio", "eq")})
for mode in ("anc", "anc-medium", "wind", "ambient", "normal"):
    check(f"noise {mode}", [mode], f"mode: {mode}")
    if status().get("mode") != mode:
        failed.append(f"noise {mode} readback")
for level in range(-3, 4):
    check(f"ambient-level {level}", ["ambient-level", str(level)])
    if status().get("ambient_level") != level:
        failed.append(f"level {level} readback")
check("cycle", ["cycle"])
for audio in ("game", "spatial", "music"):
    check(f"audio {audio}", ["audio", audio], f"audio: {audio}")
for eq in ("vocal", "bass", "treble", "edifier", "dynamic"):
    check(f"eq {eq}", ["eq", eq], f"eq: {eq}")
check("codec read", ["codec"], "codec:")
check("battery", ["battery"], "%")

# restore
if before.get("mode") == "ambient" and before.get("ambient_level") is not None:
    run("ambient-level", str(before["ambient_level"]))
elif before.get("mode"):
    run(before["mode"])
for key in ("audio", "eq"):
    if before.get(key):
        run(key, before[key])
after = status()
restored = all(after.get(k) == before.get(k) for k in ("mode", "audio", "eq"))
print("restored previous state:", restored)
print("FAILED:" if failed else "all passed", ", ".join(failed))
sys.exit(1 if failed or not restored else 0)
