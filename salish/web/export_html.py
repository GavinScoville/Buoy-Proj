"""Render the Markdown report as a standalone HTML page.

Markdown viewers cannot show the PyVista scenes, so the report embeds a still
of each one and links to the interactive HTML. This exporter turns those links
into <iframe>s, so the scenes are live and spinnable in the page.

    python -m salish.web.export_html            # write artifacts/site/*.html
    python -m salish.web.export_html --serve    # ...and serve it, see below
    python -m salish.web.export_html --site _site   # self-contained folder for GitHub Pages

The images and scenes are referenced by relative path, so the page only works
from inside artifacts/site/. Browsers also differ on whether a file:// page may
frame another local file, so --serve runs a local web server over the repo and
prints the URL to open; without the 3D frames, opening the file works anywhere.

--site copies the page to <dir>/index.html along with only the files it links
to, so the published folder never picks up config or state by accident.
"""

import argparse
import re
import shutil
import webbrowser
from pathlib import Path

import markdown

from salish.paths import ARTIFACTS, PROJECT_ROOT, SITE
from salish.web.website import REPORT

IFRAME = ('<iframe src="\\1" width="100%" height="620" loading="lazy" '
          'title="Interactive 3D wave surface"></iframe>')

LINK_3D = re.compile(r"\[Open the interactive version[^]]*\]\(([^)]+)\)")

# Python-Markdown leaves the contents of a raw HTML block alone unless the tag
# says otherwise, which would print the collapsed sections' images as source.
# GitHub ignores the attribute, so it stays out of the Markdown itself.
DETAILS = re.compile(r"<details>")

STYLE = """
:root { color-scheme: light dark; }
body { margin: 0 auto; padding: 2rem 1rem 4rem; max-width: 56rem; line-height: 1.6;
       font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif; }
h1 { font-size: 2rem; } h2 { margin-top: 2.5rem; } h3 { margin-top: 2rem; }
hr { border: 0; border-top: 1px solid currentColor; opacity: .2; margin: 2.5rem 0; }
img, iframe { max-width: 100%; border-radius: 4px; }
iframe { border: 1px solid currentColor; }
details { margin: 1rem 0; padding: .5rem 0; }
summary { cursor: pointer; padding: .4rem 0; }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
{body}
</body>
</html>
"""


# Relative targets of Markdown images and links: ![alt](path) and [text](path)
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")


def _render(text, embed_3d, title):
    if embed_3d:
        text = LINK_3D.sub(IFRAME, text)
    text = DETAILS.sub('<details markdown="1">', text)
    body = markdown.markdown(text, extensions=["md_in_html", "extra", "sane_lists"])
    return PAGE.format(title=title, style=STYLE, body=body)


def export_html(report=REPORT, out=None, embed_3d=True, title="Salish Sea Surf Report"):
    """Convert the Markdown report to HTML. Returns the path written."""
    out = Path(out) if out else SITE / (report.stem + ".html")
    out.write_text(_render(report.read_text(), embed_3d, title))
    print(f"HTML report written: {out}")
    return out


def build_site(site_dir, report=REPORT, embed_3d=True, title="Salish Sea Surf Report"):
    """
    Write a self-contained copy of the report to site_dir: index.html plus
    every file under artifacts/ it links to, at the same path relative to
    artifacts/ (so ../plots/x.png becomes plots/x.png). Missing files and
    anything outside artifacts/ are left as they are. Returns index.html.
    """
    site_dir = Path(site_dir)
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)

    def copy(match):
        target = match.group(1)
        src = (report.parent / target).resolve()
        if "://" in target or not src.is_file() or not src.is_relative_to(ARTIFACTS):
            return match.group(0)
        rel = src.relative_to(ARTIFACTS)
        (site_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, site_dir / rel)
        return f"]({rel.as_posix()})"

    text = LINK_TARGET.sub(copy, report.read_text())
    index = site_dir / "index.html"
    index.write_text(_render(text, embed_3d, title))
    n = sum(1 for p in site_dir.rglob("*") if p.is_file()) - 1
    print(f"Site written: {index} (+{n} linked files)")
    return index


def serve(path, port=8765):
    """Serve the repo so the page can frame the 3D scenes, and open it."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    if not path.resolve().is_relative_to(PROJECT_ROOT):
        raise SystemExit(f"--serve needs the page inside {PROJECT_ROOT}, got {path}")
    url = f"http://localhost:{port}/{path.resolve().relative_to(PROJECT_ROOT)}"
    handler = partial(SimpleHTTPRequestHandler, directory=str(PROJECT_ROOT))
    with ThreadingHTTPServer(("", port), handler) as httpd:
        print(f"Serving {PROJECT_ROOT} at {url}\nCtrl-C to stop.")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--out", help="where to write the HTML")
    parser.add_argument("--no-3d", action="store_true",
                        help="keep the 3D scenes as links instead of embedding them")
    parser.add_argument("--serve", action="store_true",
                        help="serve the page over HTTP and open a browser")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--site", metavar="DIR",
                        help="write a self-contained site (index.html + linked files) to DIR")
    args = parser.parse_args()

    if args.site:
        build_site(args.site, embed_3d=not args.no_3d)
        return
    path = export_html(out=args.out, embed_3d=not args.no_3d)
    if args.serve:
        serve(path, args.port)


if __name__ == "__main__":
    main()
