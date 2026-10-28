# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added
- MIT license (`LICENSE`); the Debian `copyright` file now states it.

## [0.0.2] - 2026-10-28

First release. Developed and tested on the Edifier W820NB Plus (2025) on Ubuntu with GNOME.

### Added
- `edifier-control` command: noise mode (off, ANC high, ANC medium, wind, ambient), ambient level -3..+3, sound mode
  (game, music, spatial), equaliser presets, A2DP codec (LDAC, SBC-XQ, SBC), and status with battery, firmware and MAC;
  `--version`. Settings are verified by reading the value back, and commands run one at a time.
- `edifier-control-gui`: one program with a GTK4/libadwaita window (battery bar, one-line errors) and a top-bar icon
  that shows the battery level and has the same controls in its menu. Closing the window hides it to the icon (or
  quits when no panel is showing icons); "Open window" in the icon menu or starting the program again brings it
  back, "Quit" in the icon menu ends it. Window and icon share one queue of commands to the headphones.
- `edifier-control-gui --background` starts only the icon; `edifier-control-background.desktop` is the launcher for it
  (`./install.sh --autostart` puts it into the autostart folder).
- The icon speaks the StatusNotifierItem protocol itself and builds its menu with libdbusmenu-glib, so it needs
  neither GTK 3 nor AppIndicator libraries.
- Application name "Edifier Control — W820NB Plus (2025)", a colour application icon and a monochrome panel icon;
  the window launcher is named `local.edifier.control.desktop`, after the application id, so GNOME shows the icon
  on the window and in the dock.
- Ukrainian and English interface; a language is a single JSON file in `locales/`, picked from the language menu.
- Debian package built by `packaging/build-deb.sh`, and `install.sh` for a user install without root.
- Unit tests, tests of the icon over a real session bus, a check that every button is a command the CLI accepts,
  and a hardware smoke test (`tests/`).
- Screenshots of the window and the icon menu in the README.

### Known limitations
- Custom equaliser bands and the LDAC bit rate on the headphones are not supported: the protocol is not known.
- Only the Edifier W820NB Plus (2025) is supported; other Edifier models use other protocols and are untested.
- The icon was checked on GNOME (Ubuntu's AppIndicator extension); KDE and other panels should show it but are untested.
  Codec switching needs PipeWire.
