"""The top-bar icon and its menu: the same controls as the window, driven by the same Backend."""
from edifier_common import GROUPS, TITLE
from edifier_indicator import Indicator


class PanelIcon:
    def __init__(self, translator, backend, icon_name, on_open, on_quit):
        self.backend, self.on_open, self.on_quit = backend, on_open, on_quit
        self.indicator = Indicator("edifier-control", TITLE, icon_name, on_activate=on_open)
        self.status = None
        self.rebuild(translator)

    @property
    def available(self):
        """True when a panel with a StatusNotifierWatcher is running, i.e. the icon can actually be seen."""
        return self.indicator.panel_running()

    def rebuild(self, translator):
        """(Re)build the menu, also used when the language changes."""
        self.tr, self.i18n = translator.tr, translator
        menu = self.indicator.menu
        for child in list(menu.root.get_children()):
            menu.root.child_delete(child)
        self.items, m = {}, menu
        self.info = m.info(m.root, self.tr("connecting"))
        m.separator(m.root)
        for key, cmd, title, entries in GROUPS:
            parent = m.root if key == "mode" else m.submenu(m.root, self.tr(title))  # noise modes are used most
            self.items[key] = {value: m.radio(parent, self.tr(label), lambda c=cmd, v=value: self._choose(c, v))
                               for value, label in entries}
            if key == "mode":
                m.separator(m.root)
        m.separator(m.root)
        m.action(m.root, self.tr("refresh"), self.backend.refresh)
        m.action(m.root, self.tr("open"), self.on_open)
        m.action(m.root, self.tr("quit"), self.on_quit)
        if self.status:
            self.show(self.status)

    def _choose(self, cmd, value):
        self.backend.run(*([cmd] if cmd else []), value)

    # --- updates, same names as the window so the app can treat both alike
    def show(self, st):
        self.status = st
        m = self.indicator.menu
        battery = st.get("battery")
        m.set_label(self.info, f"Edifier — {self.tr('battery')}: {battery}%" if battery is not None else "Edifier")
        self.indicator.set_label(f"{battery}%" if battery is not None else "", "100%")
        for key in ("mode", "audio", "eq"):
            if st.get(key):
                self._select(key, st[key])
        for item in self.items["eq"].values():  # spatial sound takes over the equaliser
            m.set_enabled(item, st.get("audio") != "spatial")

    def show_codec(self, codec):
        self._select("codec", codec)

    def show_error(self, text):
        # None means the CLI printed something that is not a status reply
        text = self.tr("bad_reply") if text is None else self.i18n.error(text) or self.tr("error")
        self.indicator.menu.set_label(self.info, text[:60])
        self.indicator.set_label("", "")

    def _select(self, key, value):
        for name, item in self.items[key].items():
            self.indicator.menu.check(item, name == value)
