"""Pieces shared by the window and the tray indicator: the control table and the CLI backend."""
import json, os, queue, shutil, subprocess, sys, threading
from gi.repository import GLib

APP_NAME = "Edifier Control"
MODEL = "W820NB Plus (2025)"
TITLE = f"{APP_NAME} — {MODEL}"

# (status key, CLI command word, title text key, [(value, label text key)])
# Labels that are not keys in locales/*.json (EDIFIER, LDAC, ...) are proper names and are shown as they are.
GROUPS = [
    ("mode", "", "noise", [("normal", "off"), ("anc", "anc_high"), ("anc-medium", "anc_medium"),
                           ("wind", "wind"), ("ambient", "ambient")]),
    ("audio", "audio", "audio", [("game", "game"), ("music", "music"), ("spatial", "spatial")]),
    ("eq", "eq", "eq", [("edifier", "EDIFIER"), ("dynamic", "Dynamic"), ("vocal", "Vocal"),
                        ("bass", "Bass"), ("treble", "Treble"), ("custom", "Custom")]),
    ("codec", "codec", "codec", [("ldac", "LDAC"), ("sbc-xq", "SBC-XQ"), ("sbc", "SBC")]),
]


def find_tool(name):
    """A program of this install: on PATH, next to this file (checkout), or in the prefix's bin (<prefix>/share/<app>/../../bin)."""
    here = os.path.dirname(os.path.realpath(__file__))
    for candidate in (shutil.which(name), os.path.join(here, name), os.path.join(here, "..", "..", "bin", name)):
        if candidate and os.path.exists(candidate):
            return candidate
    return name


def error_text(stderr):
    """Last non-empty line of the CLI's stderr, so a traceback never ends up in a window."""
    lines = [x for x in stderr.splitlines() if x.strip()]
    return (lines[-1] if lines else "").replace("edifier-control: ", "")


class Backend:
    """Runs `edifier-control` calls one at a time on a worker thread and reports back on the GLib main loop.

    Callbacks (all on the main loop): on_status(dict), on_codec(name), on_error(text or None for a garbled
    reply), on_busy(number of pending calls).
    """

    def __init__(self, on_status, on_codec, on_error, on_busy=lambda n: None):
        self._on_status, self._on_codec, self._on_error, self._on_busy = on_status, on_codec, on_error, on_busy
        self._jobs = queue.Queue()  # BLE has one link, so calls must not overlap
        self._waiting = set()       # requests queued but not started; identical ones are coalesced
        self._lock = threading.Lock()
        self.busy = 0
        self._cli = find_tool("edifier-control")
        threading.Thread(target=self._worker, daemon=True).start()

    def run(self, *args):
        key = tuple(args)
        with self._lock:
            if key in self._waiting:
                return
            self._waiting.add(key)
        self.busy += 1
        self._on_busy(self.busy)
        self._jobs.put(key)

    def refresh(self):
        self.run("status")
        self.run("codec")

    def close(self):
        self._jobs.put(None)

    def _worker(self):
        while (key := self._jobs.get()) is not None:
            with self._lock:
                self._waiting.discard(key)
            try:
                p = subprocess.run([sys.executable, self._cli, *key], capture_output=True, text=True, timeout=60)
                result = (p.returncode == 0, p.stdout.strip(), p.stderr)
            except Exception as e:
                result = (False, "", str(e))
            GLib.idle_add(self._finish, key, *result)

    def _finish(self, key, ok, out, err):
        self.busy -= 1
        self._on_busy(self.busy)
        if not ok:
            self._on_error(error_text(err))
        elif key[0] == "codec":
            self._on_codec(out.replace("codec:", "").strip())
        elif key[0] == "status":
            try:
                self._on_status(json.loads(out))
            except ValueError:
                self._on_error(None)
        else:
            self.run("status")  # show what the headphones actually report
        return False  # one-shot idle callback
