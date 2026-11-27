#!/usr/bin/env python3
"""Check a finished build before it goes live.

    python3 check.py dist production     # expects indexable pages
    python3 check.py dist preview        # expects noindex everywhere
    python3 check.py dist preview /advenue-web   # build made with BASE_PATH=/advenue-web

Checks every URL in sitemap.xml: one <h1>, <title> and description length, canonical,
lang, Open Graph, valid JSON-LD, the noindex switch, that every internal link and #anchor
leads somewhere real, and that _redirects never shadows a real page or points nowhere.
Exits with an error code when something is wrong.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

DOMAIN = "https://advenue.cz"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.h1, self.meta, self.ld = set(), [], 0, {}, []
        self.lang = self.canonical = None
        self.title = ""
        self._in_title = self._in_ld = False
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("link", "script") and (a.get("href") or a.get("src")):
            self.links.append(a.get("href") or a.get("src"))
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._buf = True, ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_ld:
            self._in_ld = False
            self.ld.append(self._buf)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self._buf += data


def main():
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    mode = sys.argv[2] if len(sys.argv) > 2 else "production"
    base = (sys.argv[3] if len(sys.argv) > 3 else "").rstrip("/")
    errors = []
    err = lambda where, msg: errors.append(f"{where}: {msg}")

    locs = re.findall(r"<loc>(.*?)</loc>", (dist / "sitemap.xml").read_text(encoding="utf-8"))
    paths = [loc[len(DOMAIN):] for loc in locs]
    pages = {}
    for path in paths:
        f = dist / path.lstrip("/") / "index.html"
        if not f.exists():
            err(path, "listed in sitemap but no file")
            continue
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        pages[path] = p
    nf = Page()
    nf.feed((dist / "404.html").read_text(encoding="utf-8"))
    pages["/404.html"] = nf

    titles = {}
    for path, p in pages.items():
        robots = p.meta.get("robots", "")
        if path == "/404.html":
            if "noindex" not in robots:
                err(path, "404 page must be noindex")
        else:
            if p.h1 != 1:
                err(path, f"{p.h1} <h1> elements")
            if not p.title or len(p.title) > 60:
                err(path, f"title length {len(p.title)}: {p.title!r}")
            if p.title in titles:
                err(path, f"same title as {titles[p.title]}")
            titles[p.title] = path
            desc = p.meta.get("description", "")
            if not desc or len(desc) > 155:
                err(path, f"description length {len(desc)}")
            if p.canonical != DOMAIN + path:
                err(path, f"canonical {p.canonical}")
            if p.lang != "cs":
                err(path, f"lang={p.lang}")
            for key in ("og:title", "og:description", "og:url", "og:image"):
                if not p.meta.get(key):
                    err(path, f"missing {key}")
            if p.meta.get("og:url") != DOMAIN + path:
                err(path, "og:url differs from canonical")
            if mode == "production" and "noindex" in robots:
                err(path, "noindex in a production build")
            if mode == "preview" and "noindex" not in robots:
                err(path, "preview build without noindex")
            types = []
            for block in p.ld:
                try:
                    data = json.loads(block)
                except ValueError as e:
                    err(path, f"invalid JSON-LD: {e}")
                    continue
                types += [n["@type"] for n in data.get("@graph", [data])]
            want = {"/": "ProfessionalService", "/caste-otazky/": "FAQPage"}.get(path)
            if path.startswith("/navody/") and path != "/navody/":
                want = "Article"
            if want and want not in types:
                err(path, f"JSON-LD lacks {want}")
            if path != "/" and "BreadcrumbList" not in types:
                err(path, "JSON-LD lacks BreadcrumbList")

        # links
        for href in p.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "//")):
                continue
            if base and href.startswith("/"):
                if not href.startswith(base + "/"):
                    err(path, f"link {href} misses the base path {base}")
                    continue
                href = href[len(base):]
            target, _, frag = href.partition("#")
            if not target:  # same-page anchor
                if frag and frag not in p.ids:
                    err(path, f"anchor #{frag} has no element on this page")
                continue
            target = target.split("?")[0]
            if target.startswith("/assets/") or target in ("/favicon.svg",):
                if not (dist / target.lstrip("/")).exists():
                    err(path, f"missing asset {target}")
                continue
            if target not in pages:
                err(path, f"link to unknown page {href}")
            elif frag and frag not in pages[target].ids:
                err(path, f"link {href}: no #{frag} on that page")

    # redirects
    rules = [l.split() for l in (dist / "_redirects").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    for src, dst, code in rules:
        if code != "301":
            err("_redirects", f"{src} uses {code}, expected 301")
        if dst not in pages:
            err("_redirects", f"{src} -> {dst}: target is not a page")
        pattern = "^" + re.escape(src).replace(r"\*", ".*") + "$"
        for path in pages:
            if re.match(pattern, path):
                err("_redirects", f"{src} would hide the real page {path}")

    robots_txt = (dist / "robots.txt").read_text()
    if mode == "production" and "Sitemap: https://advenue.cz/sitemap.xml" not in robots_txt:
        err("robots.txt", "no sitemap line in production")

    print(f"Checked {len(pages)} pages and {len(rules)} redirects in {dist} ({mode}).")
    if errors:
        print("\n".join("  ✗ " + e for e in errors))
        sys.exit(1)
    print("  ✓ all checks passed")


if __name__ == "__main__":
    main()
