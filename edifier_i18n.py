"""Translations shared by the window and the tray indicator.

A language is one JSON file `locales/<code>.json`:
  {"name": "<native language name>", "strings": {key: text}, "errors": {english CLI error text: translation}}
Missing keys fall back to English, then to the key itself (proper names such as LDAC stay as they are).
Drop a new file into the locales folder and the language appears in the menu.
"""
import glob, json, os

CONF = os.path.expanduser("~/.config/edifier-control.json")
_HERE = os.path.dirname(os.path.realpath(__file__))
# repo checkout first, then the installed copy (users can add files there without reinstalling)
LOCALE_DIRS = [os.path.join(_HERE, "locales"), os.path.expanduser("~/.local/share/edifier-control/locales")]
FALLBACK = "en"


def _read(code):
    for d in LOCALE_DIRS:
        try:
            with open(os.path.join(d, f"{code}.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return {}


def available():
    """{code: native name} for every readable locale file."""
    codes = sorted({os.path.basename(p)[:-5] for d in LOCALE_DIRS for p in glob.glob(os.path.join(d, "*.json"))})
    langs = {}
    for code in codes:
        if data := _read(code):  # skip unreadable or malformed files
            langs[code] = data.get("name", code)
    return langs


def detect():
    """Saved choice, else the system language if we have it, else English."""
    langs = available()
    try:
        with open(CONF) as f:
            saved = json.load(f)["lang"]
        if saved in langs:
            return saved
    except (OSError, ValueError, KeyError):
        pass
    sys_lang = os.environ.get("LANG", "").split("_")[0].split(".")[0].lower()
    return sys_lang if sys_lang in langs else FALLBACK


def save(code):
    try:
        os.makedirs(os.path.dirname(CONF), exist_ok=True)
        with open(CONF, "w") as f:
            json.dump({"lang": code}, f)
    except OSError:
        pass


class Translator:
    def __init__(self, code):
        self.code = code
        data = _read(code)
        self.strings = {**_read(FALLBACK).get("strings", {}), **data.get("strings", {})}
        self.errors = data.get("errors", {})

    def tr(self, key):
        return self.strings.get(key, key)

    def error(self, msg):
        """Translate a CLI error message by substring match; unknown messages stay in English."""
        return next((t for en, t in self.errors.items() if en in msg), msg)
