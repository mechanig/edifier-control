#!/bin/sh
# Install for the current user only (no root): commands, window with its top-bar icon, translations, icons and launchers.
# For a system-wide install build the .deb instead: packaging/build-deb.sh
# Pass --autostart to also start the top-bar icon at every login.
set -e
dir="$(dirname "$0")"
data="$HOME/.local/share/edifier-control"
icons="$HOME/.local/share/icons/hicolor"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$icons/scalable/apps" "$icons/symbolic/apps" "$data/locales"
install -m 755 "$dir/edifier-control" "$dir/edifier-control-gui" "$HOME/.local/bin/"
install -m 644 "$dir/edifier_common.py" "$dir/edifier_i18n.py" "$dir/edifier_indicator.py" "$dir/edifier_panel.py" "$data/"
install -m 644 "$dir"/locales/*.json "$data/locales/"   # extra files already in there are left alone
install -m 644 "$dir/icons/edifier-control.svg" "$icons/scalable/apps/"
install -m 644 "$dir/icons/edifier-control-symbolic.svg" "$icons/symbolic/apps/"
install -m 644 "$dir/local.edifier.control.desktop" "$dir/edifier-control-background.desktop" "$HOME/.local/share/applications/"
# files of earlier layouts: the indicator used to be a separate program
rm -f "$HOME/.local/bin/edifier-control-tray" "$HOME/.local/share/applications/edifier-control-tray.desktop" \
      "$HOME/.local/share/applications/edifier-control-gui.desktop" "$HOME/.config/autostart/edifier-control-tray.desktop"
if [ "$1" = "--autostart" ]; then
    mkdir -p "$HOME/.config/autostart"
    install -m 644 "$dir/edifier-control-background.desktop" "$HOME/.config/autostart/"
    echo "the top-bar icon will start at login"
fi
echo "installed: edifier-control, edifier-control-gui (translations in $data/locales)"
