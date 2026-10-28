"""Unit tests that need no headphones: protocol framing, argument parsing, translations."""
import importlib.machinery, importlib.util, json, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import edifier_common, edifier_i18n  # noqa: E402


def load_cli():
    loader = importlib.machinery.SourceFileLoader("edifier_control", os.path.join(ROOT, "edifier-control"))
    spec = importlib.util.spec_from_loader("edifier_control", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


cli = load_cli()


def reply(cmd, payload=b""):
    data = bytes([0xBB, 0xEC, cmd, 0x00, len(payload)]) + payload
    return data + bytes([sum(data) & 0xFF])


class Protocol(unittest.TestCase):
    def test_packet_layout_and_checksum(self):
        self.assertEqual(cli.packet(0xC1, bytes([0xB5, 0xA4])).hex(), "aaecc10002b5a4b2")
        self.assertEqual(cli.packet(0xCC).hex(), "aaeccc000062")  # empty payload: a read request

    def test_parse_roundtrip(self):
        self.assertEqual(list(cli.parse(reply(0xCC, b"\xb5\xa0"))), [(0xCC, b"\xb5\xa0")])

    def test_parse_skips_garbage_and_bad_checksum(self):
        bad = bytearray(reply(0xD0, b"\xe8"))
        bad[-1] ^= 0xFF
        stream = b"\x00\x01" + bytes(bad) + reply(0xC6, b"\xa4\xa5\xa0")
        self.assertEqual(list(cli.parse(stream)), [(0xC6, b"\xa4\xa5\xa0")])

    def test_parse_waits_for_partial_packet(self):
        self.assertEqual(list(cli.parse(reply(0xCC, b"\xb5\xa0")[:-2])), [])

    def test_ambient_levels_are_a_bijection(self):
        self.assertEqual(sorted(cli.AMBIENT_OFFSET), list(range(-3, 4)))
        self.assertEqual(len(set(cli.AMBIENT_OFFSET.values())), 7)
        for level, offset in cli.AMBIENT_OFFSET.items():
            self.assertEqual(cli.LEVEL_BY_OFFSET[offset], level)

    def test_codes_are_unique_per_table(self):
        for table in (cli.MODES, cli.AUDIO, cli.EQ):
            self.assertEqual(len(set(table.values())), len(table))


class Release(unittest.TestCase):
    def test_changelog_matches_the_cli_version(self):
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
            headings = [line for line in f if line.startswith("## [") and "Unreleased" not in line]
        self.assertTrue(headings[0].startswith(f"## [{cli.__version__}]"), headings[0])

    def test_version_flag(self):
        self.assertEqual(cli.parse_command(["--version"]), ("version", None))


class Packaging(unittest.TestCase):
    def read(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read()

    def test_desktop_file_is_named_after_the_application_id(self):
        # GNOME matches a window to its launcher (and so to its icon) by this name
        import re
        app_id = re.search(r'application_id="([^"]+)"', self.read("edifier-control-gui")).group(1)
        self.assertTrue(os.path.exists(os.path.join(ROOT, f"{app_id}.desktop")), app_id)

    def test_launchers_use_the_shipped_icon(self):
        for name in ("local.edifier.control.desktop", "edifier-control-background.desktop"):
            self.assertIn("Icon=edifier-control\n", self.read(name))
        for icon in ("edifier-control.svg", "edifier-control-symbolic.svg"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, "icons", icon)), icon)

    def test_launchers_run_installed_commands(self):
        self.assertIn("Exec=edifier-control-gui\n", self.read("local.edifier.control.desktop"))
        self.assertIn("Exec=edifier-control-gui --background\n", self.read("edifier-control-background.desktop"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "edifier-control-gui")))

    def test_every_module_is_installed_and_packaged(self):
        modules = [f for f in os.listdir(ROOT) if f.startswith("edifier_") and f.endswith(".py")]
        self.assertGreaterEqual(len(modules), 4)
        for name in ("install.sh", "packaging/build-deb.sh"):
            for module in modules:
                self.assertIn(module, self.read(name), f"{module} missing from {name}")


class Controls(unittest.TestCase):
    """The window and the panel menu are built from one table; every entry must be a command the CLI accepts."""

    def test_every_control_is_a_valid_cli_command(self):
        for key, cmd, _title, items in edifier_common.GROUPS:
            for value, _label in items:
                args = ([cmd] if cmd else []) + [value]
                with self.subTest(args=args):
                    cli.parse_command(args)

    def test_status_keys_cover_what_the_cli_reports(self):
        self.assertEqual({g[0] for g in edifier_common.GROUPS}, {"mode", "audio", "eq", "codec"})


class Arguments(unittest.TestCase):
    def parse(self, *args):
        return cli.parse_command(list(args))

    def test_valid(self):
        self.assertEqual(self.parse("anc"), ("anc", None))
        self.assertEqual(self.parse("transparency"), ("ambient", None))  # alias
        self.assertEqual(self.parse("ambient-level", "-3"), ("ambient-level", -3))
        self.assertEqual(self.parse("eq", "vocal"), ("eq", "vocal"))
        self.assertEqual(self.parse("codec"), ("codec", None))
        self.assertEqual(self.parse("codec", "ldac"), ("codec", "ldac"))
        self.assertEqual(self.parse(), ("help", None))

    def test_invalid_exits_before_any_bluetooth(self):
        for args in (["bogus"], ["ambient-level"], ["ambient-level", "x"], ["ambient-level", "4"],
                     ["audio"], ["audio", "nope"], ["eq", "nope"], ["codec", "mp3"]):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.parse(*args)


class Translations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._dirs = edifier_i18n.LOCALE_DIRS
        edifier_i18n.LOCALE_DIRS = [self.tmp] + self._dirs

    def tearDown(self):
        edifier_i18n.LOCALE_DIRS = self._dirs

    def write(self, name, data):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False))

    def test_every_locale_covers_the_english_keys(self):
        en = set(edifier_i18n._read("en")["strings"])
        for code in edifier_i18n.available():
            if code in ("xx", "de"):
                continue
            with self.subTest(code=code):
                self.assertEqual(en - set(edifier_i18n._read(code)["strings"]), set())

    def test_every_ui_label_has_a_key_or_is_a_proper_name(self):
        keys = set(edifier_i18n._read("en")["strings"])
        for _, _, title, items in edifier_common.GROUPS:
            self.assertIn(title, keys)
            for _, label in items:
                self.assertTrue(label in keys or label.replace("-", "").isalnum(), label)

    def test_new_language_by_dropping_a_file(self):
        self.write("xx.json", {"name": "Test", "strings": {"battery": "Akku"}, "errors": {"BLE connect failed": "X"}})
        self.assertIn("xx", edifier_i18n.available())
        t = edifier_i18n.Translator("xx")
        self.assertEqual(t.tr("battery"), "Akku")
        self.assertEqual(t.tr("wind"), "Wind")      # falls back to English
        self.assertEqual(t.tr("LDAC"), "LDAC")      # proper names pass through
        self.assertEqual(t.error("edifier-control: BLE connect failed: y"), "X")
        self.assertEqual(t.error("unknown"), "unknown")

    def test_broken_file_is_ignored(self):
        self.write("zz.json", "{not json")
        self.assertNotIn("zz", edifier_i18n.available())


class ErrorText(unittest.TestCase):
    def test_traceback_collapses_to_last_line(self):
        err = "Traceback (most recent call last):\n  File x\nKeyError: 'a'\n"
        self.assertEqual(edifier_common.error_text(err), "KeyError: 'a'")
        self.assertEqual(edifier_common.error_text("edifier-control: boom\n"), "boom")
        self.assertEqual(edifier_common.error_text(""), "")


if __name__ == "__main__":
    unittest.main()
