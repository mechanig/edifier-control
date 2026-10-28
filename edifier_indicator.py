"""Top-bar indicator without GTK: a StatusNotifierItem on the session bus plus a dbusmenu menu.

This is the protocol GNOME's AppIndicator extension, KDE Plasma and most other panels show icons with,
so the window (GTK 4) and the indicator can live in one process.
"""
import gi
gi.require_version("Dbusmenu", "0.4")
from gi.repository import Dbusmenu, Gio, GLib

ITEM_PATH, MENU_PATH = "/StatusNotifierItem", "/MenuBar"
WATCHER = "org.kde.StatusNotifierWatcher"

# type signature and default of every property the panels read
_PROPS = {
    "Category": ("s", "Hardware"), "Id": ("s", ""), "Title": ("s", ""), "Status": ("s", "Active"),
    "WindowId": ("i", 0), "IconName": ("s", ""), "IconThemePath": ("s", ""), "ItemIsMenu": ("b", False),
    "Menu": ("o", MENU_PATH), "OverlayIconName": ("s", ""), "AttentionIconName": ("s", ""),
    "AttentionMovieName": ("s", ""), "IconPixmap": ("a(iiay)", []), "OverlayIconPixmap": ("a(iiay)", []),
    "AttentionIconPixmap": ("a(iiay)", []), "XAyatanaLabel": ("s", ""), "XAyatanaLabelGuide": ("s", ""),
    "XAyatanaOrderingIndex": ("u", 0),
}
_XML = f"""<node><interface name="org.kde.StatusNotifierItem">
{''.join(f'<property name="{n}" type="{t}" access="read"/>' for n, (t, _) in _PROPS.items())}
<method name="ContextMenu"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
<method name="Activate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
<method name="SecondaryActivate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
<method name="Scroll"><arg name="delta" type="i" direction="in"/><arg name="orientation" type="s" direction="in"/></method>
<signal name="NewTitle"/><signal name="NewIcon"/><signal name="NewStatus"><arg name="status" type="s"/></signal>
<signal name="XAyatanaNewLabel"><arg name="label" type="s"/><arg name="guide" type="s"/></signal>
</interface></node>"""


class Menu:
    """A dbusmenu tree. Items are plain Dbusmenu items; this class only builds and updates them."""

    def __init__(self):
        self.root = Dbusmenu.Menuitem.new()
        self.server = Dbusmenu.Server.new(MENU_PATH)
        self.server.set_root(self.root)

    @staticmethod
    def _item(parent, label, enabled=True):
        item = Dbusmenu.Menuitem.new()
        item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, label)
        item.property_set_bool(Dbusmenu.MENUITEM_PROP_ENABLED, enabled)
        parent.child_append(item)
        return item

    def action(self, parent, label, callback):
        item = self._item(parent, label)
        item.connect("item-activated", lambda _item, _timestamp: callback())
        return item

    def radio(self, parent, label, callback, checked=False):
        item = self._item(parent, label)
        item.property_set(Dbusmenu.MENUITEM_PROP_TOGGLE_TYPE, Dbusmenu.MENUITEM_TOGGLE_RADIO)
        self.check(item, checked)
        item.connect("item-activated", lambda _item, _timestamp: callback())
        return item

    def submenu(self, parent, label):
        return self._item(parent, label)  # an item with children is shown as a submenu

    def info(self, parent, label):
        return self._item(parent, label, enabled=False)

    def separator(self, parent):
        item = Dbusmenu.Menuitem.new()
        item.property_set(Dbusmenu.MENUITEM_PROP_TYPE, Dbusmenu.CLIENT_TYPES_SEPARATOR)
        parent.child_append(item)

    @staticmethod
    def check(item, checked):
        item.property_set_int(Dbusmenu.MENUITEM_PROP_TOGGLE_STATE,
                              Dbusmenu.MENUITEM_TOGGLE_STATE_CHECKED if checked else Dbusmenu.MENUITEM_TOGGLE_STATE_UNCHECKED)

    @staticmethod
    def set_label(item, label):
        item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, label)

    @staticmethod
    def set_enabled(item, enabled):
        item.property_set_bool(Dbusmenu.MENUITEM_PROP_ENABLED, enabled)


class Indicator:
    def __init__(self, ident, title, icon_name, on_activate=None):
        self._values = {name: default for name, (_, default) in _PROPS.items()}
        self._values.update(Id=ident, Title=title, IconName=icon_name)
        self._on_activate = on_activate
        self.menu = Menu()
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)
        info = Gio.DBusNodeInfo.new_for_xml(_XML).interfaces[0]
        self._object_id = self.bus.register_object(ITEM_PATH, info, self._on_method, self._on_property, None)
        # (re)register whenever a panel with a StatusNotifierWatcher is, or becomes, available
        self._watch = Gio.bus_watch_name_on_connection(self.bus, WATCHER, Gio.BusNameWatcherFlags.NONE,
                                                       lambda *_: self._register(), None)

    def panel_running(self):
        """Is anything (the GNOME extension, Plasma, ...) listening for status notifier items?"""
        return self.bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                                  "NameHasOwner", GLib.Variant("(s)", (WATCHER,)), None,
                                  Gio.DBusCallFlags.NONE, -1, None).unpack()[0]

    def _register(self):
        self.bus.call(WATCHER, "/StatusNotifierWatcher", WATCHER, "RegisterStatusNotifierItem",
                      GLib.Variant("(s)", (ITEM_PATH,)), None, Gio.DBusCallFlags.NONE, -1, None, None)

    def _on_property(self, _conn, _sender, _path, _iface, name):
        signature, _ = _PROPS[name]
        return GLib.Variant(signature, self._values[name])

    def _on_method(self, _conn, _sender, _path, _iface, method, _params, invocation):
        if method == "Activate" and self._on_activate:
            self._on_activate()
        invocation.return_value(None)

    def _emit(self, signal, params=None):
        self.bus.emit_signal(None, ITEM_PATH, "org.kde.StatusNotifierItem", signal, params)

    def set_label(self, label, guide=""):
        self._values.update(XAyatanaLabel=label, XAyatanaLabelGuide=guide)
        self._emit("XAyatanaNewLabel", GLib.Variant("(ss)", (label, guide)))

    def set_icon(self, name):
        self._values["IconName"] = name
        self._emit("NewIcon")

    def set_title(self, title):
        self._values["Title"] = title
        self._emit("NewTitle")
