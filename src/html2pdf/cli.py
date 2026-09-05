"""html2pdf: HTML to a single continuous PDF page.

A browser's Save as PDF always cuts the document into paper-sized sheets, so
you either get blank space at the bottom of every page or content split across
two. This tool renders the whole document as one PDF page whose height equals
the content height, so it reads like a web page that scrolls.

The default output is vector with selectable text. Pages that lean on effects
Chromium's PDF backend cannot draw (blur, soft radial gradients,
backdrop-filter) can be exported as a full-page screenshot with --image.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

INSTALL_HINT = "run: html2pdf --install-browser"


def _hide_css(hide: str | None) -> str:
    css = ".toolbar{display:none!important}"
    if hide:
        css += f"\n{hide}{{display:none!important}}"
    return css


# Forced page breaks belong to paged output; in single-page mode they would
# push content onto a second page.
NO_BREAKS_CSS = (
    "*{break-before:auto!important;break-after:auto!important;"
    "break-inside:auto!important;page-break-before:auto!important;"
    "page-break-after:auto!important;page-break-inside:auto!important}"
)

# Content height: the lowest edge of any element plus the body's bottom margin.
# documentElement.scrollHeight is not used because it never reports less than
# the viewport height, which would pad short documents.
CONTENT_HEIGHT_JS = """() => {
  let bottom = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const style = getComputedStyle(el);
    if (style.position === 'fixed' || style.display === 'none') continue;
    const rect = el.getBoundingClientRect();
    if (rect.height === 0) continue;
    bottom = Math.max(bottom, rect.bottom + window.scrollY);
  }
  const body = document.body.getBoundingClientRect();
  bottom = Math.max(bottom, body.bottom + window.scrollY
    + parseFloat(getComputedStyle(document.body).marginBottom));
  return Math.ceil(bottom);
}"""


def _prepare(page, hide: str | None) -> int:
    """Apply screen styles, hide chrome, wait for fonts; return content height."""
    page.emulate_media(media="screen")
    page.add_style_tag(content=_hide_css(hide) + NO_BREAKS_CSS)
    page.evaluate("async()=>{await document.fonts.ready;}")
    return page.evaluate(CONTENT_HEIGHT_JS)


def _page_count(pdf: str) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pathlib.Path(pdf).read_bytes()))


def render_vector(page, out: str, width: int, height: int) -> None:
    # The page size comes from a CSS @page rule with prefer_css_page_size; in
    # testing, page.pdf(width=, height=) misplaced content on very tall pages.
    page.add_style_tag(content=f"@page{{size:{width}px {height}px;margin:0}}")
    page.pdf(path=out, print_background=True, prefer_css_page_size=True)
    pages = _page_count(out)
    if pages != 1:
        raise RuntimeError(
            f"content did not fit on one page ({pages} pages rendered); "
            "try --paged for documents designed as pages"
        )


def render_image(page, out: str, width: int, height: int, scale: float) -> None:
    import img2pdf

    with tempfile.TemporaryDirectory(prefix="html2pdf-") as tmp:
        shot = os.path.join(tmp, "page.png")
        # Clip to the measured content; a full-page capture is never shorter
        # than the viewport.
        page.screenshot(
            path=shot,
            full_page=True,
            clip={"x": 0, "y": 0, "width": width, "height": height},
        )
        # Chromium captures width*scale pixels; raising the DPI by the same
        # factor keeps the physical page size and packs in the extra pixels.
        dpi = round(96 * scale)
        layout = img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))
        with open(out, "wb") as f:
            f.write(img2pdf.convert(shot, layout_fun=layout))


def open_file(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif shutil.which("xdg-open"):
        subprocess.run(["xdg-open", path], check=False)
    else:
        print(f"html2pdf: no opener found for {path}", file=sys.stderr)


def render_paged(page, out: str, hide: str | None) -> int:
    """Honour the document's own @page size and page-break rules (print media)."""
    page.emulate_media(media="print")
    page.add_style_tag(content=_hide_css(hide))
    page.evaluate("async()=>{await document.fonts.ready;}")
    page.pdf(path=out, print_background=True, prefer_css_page_size=True)
    return _page_count(out)


def html_to_pdf(
    html_path: str,
    out_path: str,
    width: int = 1000,
    image: bool = False,
    scale: float = 2.0,
    hide: str | None = None,
    paged: bool = False,
) -> tuple[int, int]:
    """Render ``html_path`` to ``out_path``.

    Returns (width, height) in CSS pixels for the single-page modes, or
    (page_count, 0) for ``paged``.
    """
    uri = pathlib.Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": max(width, 1280) if paged else width, "height": 1400},
            device_scale_factor=scale,
        )
        page.goto(uri, wait_until="load")
        if paged:
            n = render_paged(page, out_path, hide)
            browser.close()
            return n, 0
        height = _prepare(page, hide)
        if image:
            render_image(page, out_path, width, height, scale)
        else:
            render_vector(page, out_path, width, height)
        browser.close()
    return width, height


def install_browser() -> int:
    """Download the headless Chromium build matching the installed Playwright."""
    return subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium-headless-shell"],
        check=False,
    ).returncode


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="html2pdf",
        description="HTML to a single continuous PDF page.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", nargs="?", help="HTML file")
    ap.add_argument("output", nargs="?", help="PDF path (default: input with .pdf)")
    ap.add_argument(
        "--install-browser",
        action="store_true",
        help="download the headless Chromium build (one-time setup), then exit",
    )
    ap.add_argument(
        "--width", type=int, default=1000, help="page width in CSS px (default: 1000)"
    )
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument(
        "--image",
        action="store_true",
        help="full-page screenshot instead of vector output (text not selectable)",
    )
    ap.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="device pixel ratio: sharpness of --image output and of raster "
        "images inside vector output (default: 2)",
    )
    ap.add_argument(
        "--hide",
        metavar="SELECTOR",
        help="CSS selector to hide before rendering, e.g. '.lang-switch, .to-top'",
    )
    modes.add_argument(
        "--paged",
        action="store_true",
        help="multi-page output following the document's own @page size and "
        "page-break rules (slides, landscape decks); laid out in a 1280px-wide "
        "viewport, or --width if larger",
    )
    ap.add_argument("--open", action="store_true", help="open the PDF when done")
    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.install_browser:
        return install_browser()
    if args.input is None:
        parser.error("the following arguments are required: input")
    src = pathlib.Path(args.input)
    if not src.is_file():
        print(f"html2pdf: file not found: {src}", file=sys.stderr)
        return 1
    out = args.output or str(src.with_suffix(".pdf"))
    try:
        w, h = html_to_pdf(
            str(src), out, args.width, args.image, args.scale, args.hide, args.paged
        )
    except PlaywrightError as exc:
        if "Executable doesn't exist" in str(exc):
            print(
                f"html2pdf: Chromium is not installed; {INSTALL_HINT}", file=sys.stderr
            )
            return 1
        raise
    except RuntimeError as exc:
        print(f"html2pdf: {exc}", file=sys.stderr)
        return 1
    if args.paged:
        print(f"wrote {out} ({w} pages, document @page rules, vector)")
    else:
        mode = f"image at {args.scale:g}x" if args.image else "vector, selectable text"
        print(f"wrote {out} ({w}x{h}px single page, {mode})")
    if args.open:
        open_file(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
