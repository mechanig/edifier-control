#!/bin/sh
# Build dist/edifier-control_<version>_all.deb from the working tree. No root needed.
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' edifier-control)"
[ -n "$version" ] || { echo "cannot read __version__" >&2; exit 1; }
pkg=edifier-control
stage="$root/build/deb/${pkg}_${version}_all"
out="$root/dist"

rm -rf "$stage" && mkdir -p "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/share/$pkg/locales" \
    "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/share/icons/hicolor/symbolic/apps" "$stage/usr/share/doc/$pkg" "$out"

# programs (system python in the shebang, as Debian policy asks)
for f in edifier-control edifier-control-gui; do
    sed '1s|^#!.*|#!/usr/bin/python3|' "$f" > "$stage/usr/bin/$f"
    chmod 755 "$stage/usr/bin/$f"
done
install -m 644 edifier_common.py edifier_i18n.py edifier_indicator.py edifier_panel.py "$stage/usr/share/$pkg/"
install -m 644 locales/*.json "$stage/usr/share/$pkg/locales/"

# desktop entries and icons
install -m 644 local.edifier.control.desktop edifier-control-background.desktop "$stage/usr/share/applications/"
install -m 644 icons/edifier-control.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
install -m 644 icons/edifier-control-symbolic.svg "$stage/usr/share/icons/hicolor/symbolic/apps/"
python3 packaging/render_icons.py "$stage/usr/share/icons/hicolor" 48 128 256

# docs
gzip -9n -c CHANGELOG.md > "$stage/usr/share/doc/$pkg/changelog.gz"
install -m 644 README.md "$stage/usr/share/doc/$pkg/README.md"
install -m 644 packaging/copyright "$stage/usr/share/doc/$pkg/copyright"

# control data
size="$(du -sk "$stage" | cut -f1)"
sed -e "s/@VERSION@/$version/" -e "s/@SIZE@/$size/" packaging/control.in > "$stage/DEBIAN/control"
(cd "$stage" && find usr -type f -exec md5sum {} + | sort -k2) > "$stage/DEBIAN/md5sums"
find "$stage" -type d -exec chmod 755 {} +
find "$stage/usr" -type f ! -perm -u+x -exec chmod 644 {} +   # no group-writable files (the umask of the builder leaks in otherwise)

dpkg-deb --root-owner-group --build "$stage" "$out/${pkg}_${version}_all.deb" >/dev/null
echo "built $out/${pkg}_${version}_all.deb"
