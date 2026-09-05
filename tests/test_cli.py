"""Smoke tests. Rendering tests need Playwright's Chromium; they are skipped when
it is not installed (``html2pdf --install-browser``). Any other launch failure
is reported as an error rather than a skip.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from html2pdf import cli

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
SAMPLE = SAMPLES / "sample.html"
SLIDES = SAMPLES / "slides.html"


@pytest.fixture(scope="session")
def chromium():
    from playwright.sync_api import Error, sync_playwright

    try:
        with sync_playwright() as p:
            p.chromium.launch().close()
    except Error as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium not installed")
        raise


def _page_count(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def _media_box_height_px(pdf: Path) -> float:
    box = re.search(rb"/MediaBox\s*\[([^\]]+)\]", pdf.read_bytes()).group(1)
    return float(box.split()[3]) * 96 / 72


def test_missing_input(tmp_path, capsys):
    assert cli.main([str(tmp_path / "nope.html")]) == 1
    assert "file not found" in capsys.readouterr().err


def test_hide_css():
    assert ".toolbar" in cli._hide_css(None)
    assert ".lang-btn{display:none!important}" in cli._hide_css(".lang-btn")


def test_vector_single_page(chromium, tmp_path):
    out = tmp_path / "vector.pdf"
    assert cli.main([str(SAMPLE), str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert _page_count(out) == 1


def test_image_single_page(chromium, tmp_path):
    out = tmp_path / "image.pdf"
    assert cli.main([str(SAMPLE), str(out), "--image", "--scale", "1"]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert _page_count(out) == 1


def test_short_document_is_not_padded_to_viewport(chromium, tmp_path):
    src = tmp_path / "short.html"
    src.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}'
        "</style></head><body><div style='height:200px'>short</div></body></html>"
    )
    out = tmp_path / "short.pdf"
    assert cli.main([str(src), str(out)]) == 0
    assert _page_count(out) == 1
    assert abs(_media_box_height_px(out) - 200) < 2
    image = tmp_path / "short-image.pdf"
    assert cli.main([str(src), str(image), "--image"]) == 0
    assert abs(_media_box_height_px(image) - 200) < 2


def test_forced_breaks_do_not_drop_content_in_single_page_mode(chromium, tmp_path):
    out = tmp_path / "slides-single.pdf"
    assert cli.main([str(SLIDES), str(out)]) == 0
    assert _page_count(out) == 1
    assert abs(_media_box_height_px(out) - 3 * 720) < 2


def test_image_and_paged_are_exclusive():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["a.html", "--image", "--paged"])


def test_paged_follows_document_page_rules(chromium, tmp_path):
    out = tmp_path / "slides.pdf"
    assert cli.main([str(SLIDES), str(out), "--paged"]) == 0
    assert _page_count(out) == 3
