#!/usr/bin/env python3
"""Render icons/edifier-control.svg to PNG for the hicolor theme: render_icons.py OUT_DIR sizes..."""
import os, sys
import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

svg, out, sizes = os.path.join(os.path.dirname(__file__), "..", "icons", "edifier-control.svg"), sys.argv[1], sys.argv[2:]
for size in map(int, sizes):
    target = os.path.join(out, f"{size}x{size}", "apps")
    os.makedirs(target, exist_ok=True)
    GdkPixbuf.Pixbuf.new_from_file_at_size(svg, size, size).savev(os.path.join(target, "edifier-control.png"), "png", [], [])
