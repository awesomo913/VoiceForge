"""Generate docs/assets/social-preview.png (1280x640) from docs/assets/banner.svg.

Re-uses the banner's artwork (recording-studio / forge identity) on a taller
panel and renders it with headless Chrome. One-off content tool, not part of
the app; its dependency is intentionally not in requirements.txt:

    uv pip install playwright
    python scripts/make_social_preview.py

Output: docs/assets/social-preview.png
"""
from __future__ import annotations

import os
import re

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "docs", "assets")
W, H = 1280, 640
SHIFT = 96  # vertical offset of the banner artwork inside the taller panel

# Banner lines that draw its own panel (background, bevel, corner screws).
_PANEL = re.compile(
    r'^<rect (width="1280" height="400"|x="1[02]" y="1[02]")|^<g transform="translate\([\d.]+ [\d.]+\) rotate'
)


def build_svg() -> str:
    with open(os.path.join(ASSETS, "banner.svg"), encoding="utf-8") as f:
        lines = f.read().split("\n")
    head = lines[1:lines.index("</defs>") + 1]  # defs only (first line is <svg>)
    body = [ln for ln in lines[lines.index("</defs>") + 1:-1] if not _PANEL.match(ln)]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        *head,
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect width="{W}" height="{H}" filter="url(#brush)" opacity=".3"/>',
        f'<rect width="{W}" height="{H}" fill="url(#warm)"/>',
        f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="14" fill="none" stroke="#000" stroke-opacity=".5" stroke-width="2"/>',
        f'<rect x="12" y="12" width="{W-24}" height="{H-24}" rx="12" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="1.5"/>',
    ]
    for sx, sy, rot in [(36, 36, 20), (W - 36, 36, 70), (36, H - 36, 140), (W - 36, H - 36, 100)]:
        out.append(
            f'<g transform="translate({sx} {sy}) rotate({rot})"><circle r="8" fill="#14110f" opacity=".6" cy="1.5"/>'
            '<circle r="7.5" fill="url(#knurl)"/><rect x="-5.5" y="-1.2" width="11" height="2.4" fill="#16130f"/></g>'
        )
    out.append(f'<g transform="translate(0 {SHIFT})">')
    out.extend(body)
    out.append("</g>")
    out.append(
        f'<text x="{W/2}" y="{H-62}" text-anchor="middle" font-family="system-ui,\'Segoe UI\',Arial,sans-serif" '
        'font-size="28" font-weight="800" letter-spacing="4" fill="#d6c7b3">FREE  ·  OFFLINE  ·  OPEN SOURCE</text>'
    )
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    svg = build_svg()
    out_path = os.path.join(ASSETS, "social-preview.png")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content('<body style="margin:0">' + svg + "</body>")
        page.screenshot(path=out_path)
        browser.close()
    print(f"[make_social_preview] wrote {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
