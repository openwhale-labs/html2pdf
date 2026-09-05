# html2pdf

HTML to a single continuous PDF page. ([中文说明](README.zh-CN.md))

```
html2pdf report.html
```

The PDF is one page as wide as you choose and exactly as tall as the content, so it reads the way the page scrolls in a browser. No paper-size breaks, no blank band at the bottom of every sheet, no card or table cut in half. Output is vector by default: text stays selectable and searchable, links stay clickable, and fonts are embedded.

## Why not Save as PDF

A browser's print dialog always cuts the document into sheets. For anything laid out as a web page rather than a paper document, that leaves you choosing between white space and split content. Client-side libraries that turn the page into a canvas first produce images, so the text is gone.

html2pdf drives headless Chromium through [Playwright](https://playwright.dev) and declares the page size with a CSS `@page` rule sized to the rendered content, with `prefer_css_page_size` set. Very tall pages render correctly this way; passing the size through the PDF API's width and height parameters did not in testing.

## Install

```
uv tool install html2pdf-onepage
html2pdf --install-browser
```

`pipx install html2pdf-onepage` works the same way; the package is [html2pdf-onepage on PyPI](https://pypi.org/project/html2pdf-onepage/) and the command is `html2pdf`. The second command downloads the headless Chromium build matching the installed Playwright. Run it again after upgrading html2pdf if it reports that Chromium is missing.

## Usage

```
html2pdf input.html [output.pdf]

html2pdf input.html --width 1200          # page width in CSS px (default 1000)
html2pdf input.html --hide ".lang-switch" # hide elements before rendering
html2pdf input.html --image               # full-page screenshot, for pages with
                                          # blur, backdrop-filter or soft gradients
html2pdf input.html --image --scale 3     # sharper screenshot (default 2)
html2pdf input.html --paged               # multi-page output following the
                                          # document's own @page and page-break rules
html2pdf input.html --open                # open the PDF when done
```

The output path defaults to the input name with a `.pdf` extension. Elements with the class `toolbar` are hidden automatically, which is a common name for a fixed on-screen control bar that has no place in a document. `--open` uses the platform's default PDF viewer.

Screen styles are used, not print styles, and rendering waits for web fonts to load. The document must be self-contained: inline CSS, local images, or data URIs. To export a language or theme variant of a page that switches at runtime, write a copy of the HTML with the initial state set in the markup and convert that.

`--paged` is for documents that are designed as pages, such as slide decks with an `@page { size: 1280px 720px }` rule and explicit page breaks. It renders with print media and lets Chromium paginate. The layout viewport is 1280 px wide (or `--width` if larger) and 1400 px tall, so size slides in px rather than `vw` and `vh`. [`samples/slides.html`](samples/slides.html) is a three-slide example.

### As a library

```python
from html2pdf.cli import html_to_pdf

width, height = html_to_pdf("report.html", "report.pdf", width=1000)
```

## Development

```
git clone https://github.com/openwhale-labs/html2pdf
cd html2pdf
uv tool install -e .
uv run --with pytest pytest
```

Rendering tests are skipped when Playwright's Chromium is not installed (`html2pdf --install-browser`). [`samples/sample.html`](samples/sample.html) is taller than any sheet of paper and exercises the fixed toolbar, tables, cards and a tall block; [`samples/slides.html`](samples/slides.html) covers `--paged`.

## License

MIT. Copyright (c) 2026 OpenWhale Labs.
