"""The top-bar icon over the real session bus: registers a StatusNotifierItem, builds the menu, reacts to clicks.

Skipped when there is no session bus or no panel (StatusNotifierWatcher) running.
"""
import os, subprocess, sys, textwrap, unittest

from gi.repository import Gio, GLib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    BUS = Gio.bus_get_sync(Gio.BusType.SESSION)
    HAS_PANEL = BUS.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "NameHasOwner",
                              GLib.Variant("(s)", ("org.kde.StatusNotifierWatcher",)), None, 0, 2000).unpack()[0]
except GLib.Error:
    BUS, HAS_PANEL = None, False

# runs the panel icon with a fake backend in its own process and prints what the backend was asked to do
CHILD = textwrap.dedent("""
    import sys
    sys.path.insert(0, %r)
    from gi.repository import GLib
    import edifier_i18n, edifier_panel
    class FakeBackend:
        def run(self, *args): print("RUN", *args, flush=True)
        def refresh(self): print("REFRESH", flush=True)
    quit_ = lambda: (print("QUIT", flush=True), loop.quit())
    panel = edifier_panel.PanelIcon(edifier_i18n.Translator("en"), FakeBackend(), "audio-headphones-symbolic",
                                    lambda: print("OPEN", flush=True), quit_)
    panel.show({"mode": "anc", "audio": "spatial", "eq": "vocal", "battery": 42})
    panel.show_codec("sbc")
    loop = GLib.MainLoop()
    GLib.timeout_add(20000, loop.quit)
    print("READY", flush=True)
    loop.run()
""") % ROOT


def call(dest, path, iface, method, args=None):
    return BUS.call_sync(dest, path, iface, method, args, None, 0, 5000)


@unittest.skipUnless(HAS_PANEL, "needs a session bus with a status notifier watcher (a desktop panel)")
class PanelOverDBus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.child = subprocess.Popen([sys.executable, "-u", "-c", CHILD], stdout=subprocess.PIPE, text=True)
        assert cls.child.stdout.readline().strip() == "READY"
        cls.name = cls.find_item()
        cls.layout = call(cls.name, "/MenuBar", "com.canonical.dbusmenu", "GetLayout", GLib.Variant("(iias)", (0, -1, []))).unpack()[1]

    @classmethod
    def tearDownClass(cls):
        cls.child.kill()
        cls.child.wait()

    @classmethod
    def find_item(cls):
        """Our own icon: the registered item whose bus connection belongs to the child process.

        Matching by Id alone would also pick up a real, already running copy of the application.
        """
        for _ in range(50):
            items = call("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher", "org.freedesktop.DBus.Properties", "Get",
                         GLib.Variant("(ss)", ("org.kde.StatusNotifierWatcher", "RegisteredStatusNotifierItems"))).unpack()[0]
            for item in items:
                name = item.split("@")[0]
                if item.endswith("@/StatusNotifierItem") and name.startswith(":"):
                    pid = call("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                               "GetConnectionUnixProcessID", GLib.Variant("(s)", (name,))).unpack()[0]
                    if pid == cls.child.pid:
                        return name
            GLib.usleep(100_000)
        raise AssertionError("indicator never registered")

    def item(self, label, node=None):
        node = node or self.layout
        if node[1].get("label") == label:
            return node
        for child in node[2]:
            if found := self.item(label, child):
                return found

    def click(self, label):
        call(self.name, "/MenuBar", "com.canonical.dbusmenu", "Event",
             GLib.Variant("(isvu)", (self.item(label)[0], "clicked", GLib.Variant("i", 0), 0)))
        return self.child.stdout.readline().strip()

    def test_menu_reflects_the_status(self):
        self.assertEqual(self.item("Edifier — Battery: 42%")[1]["enabled"], False)
        self.assertEqual(self.item("ANC High")[1]["toggle-state"], 1)
        self.assertEqual(self.item("Off")[1]["toggle-state"], 0)
        self.assertEqual(self.item("Spatial")[1]["toggle-state"], 1)
        self.assertEqual(self.item("SBC")[1]["toggle-state"], 1)
        self.assertEqual(self.item("LDAC")[1]["toggle-state"], 0)
        self.assertEqual(self.item("Vocal")[1]["enabled"], False)  # spatial sound takes over the equaliser

    def test_label_next_to_the_icon(self):
        label = call(self.name, "/StatusNotifierItem", "org.freedesktop.DBus.Properties", "Get",
                     GLib.Variant("(ss)", ("org.kde.StatusNotifierItem", "XAyatanaLabel"))).unpack()[0]
        self.assertEqual(label, "42%")

    def test_clicks_become_cli_commands(self):
        self.assertEqual(self.click("Wind"), "RUN wind")
        self.assertEqual(self.click("Game"), "RUN audio game")
        self.assertEqual(self.click("Bass"), "RUN eq bass")
        self.assertEqual(self.click("SBC-XQ"), "RUN codec sbc-xq")
        self.assertEqual(self.click("Refresh"), "REFRESH")
        self.assertEqual(self.click("Open window"), "OPEN")


if __name__ == "__main__":
    unittest.main()
