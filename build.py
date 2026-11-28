#!/usr/bin/env python3
"""Build the Advenue digital website into static HTML (one folder per URL) in dist/.

No dependencies beyond Python 3.8+. Usage:

    python3 build.py                 # local build, noindex (preview)
    SITE_ENV=production python3 build.py

Indexing switch (the important part):
  * SITE_ENV=production  -> pages are indexable, robots.txt points to the sitemap.
  * SITE_ENV=preview     -> every page gets <meta name="robots" content="noindex, nofollow">.
  * SITE_ENV not set     -> production only when Cloudflare Pages builds the production
                            branch (CF_PAGES_BRANCH=main), preview everywhere else.
BASE_PATH lets the same site run under a sub-folder, e.g. BASE_PATH=/advenue-web for the
GitHub Pages preview. Canonical URLs always point to https://advenue.cz.
"""
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

DOMAIN = "https://advenue.cz"
SITE_NAME = "Advenue digital"
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = Path(os.environ.get("OUT_DIR") or ROOT / "dist").resolve()
PUBLISHED = "2026-11-01"  # guides: first published / last reviewed
MODIFIED = "2026-11-01"

PRODUCTION_BRANCH = os.environ.get("PRODUCTION_BRANCH", "main")
SITE_ENV = os.environ.get("SITE_ENV") or (
    "production" if os.environ.get("CF_PAGES_BRANCH") == PRODUCTION_BRANCH else "preview")
if SITE_ENV not in ("production", "preview"):
    sys.exit(f"SITE_ENV must be 'production' or 'preview', not {SITE_ENV!r}")
INDEXABLE = SITE_ENV == "production"
BASE = os.environ.get("BASE_PATH", "").rstrip("/")

OG_IMAGE = DOMAIN + "/assets/og-image.jpg"
ORG_ID = DOMAIN + "/#organizace"
LINKEDIN = "https://www.linkedin.com/company/advenue/"
FACEBOOK = "https://www.facebook.com/advenuedigi"

HOME = ("Úvod", "/")
SERVICES = ("Služby", "/nase-sluzby/")
GUIDES = ("Návody", "/navody/")

# Every page: source fragment, URL, <title> (<= 60 chars), meta description (<= 155 chars),
# which main-menu item is active, breadcrumb trail and structured-data kind.
PAGES = [
    dict(src="index", path="/", kind="home", nav=None,
         title="Generování leadů a e-commerce marketing | Advenue digital",
         description="Agentura specialistů na generování leadů a e-commerce. Kampaně, e-maily "
                     "a weby, které firmám přinášejí poptávky a e-shopům objednávky. Audit zdarma."),
    dict(src="nase-sluzby", path="/nase-sluzby/", kind="page", nav="sluzby", crumbs=[HOME],
         title="Služby: kampaně, e-maily, weby a aplikace | Advenue digital",
         description="Generování leadů a výkon e-shopů: kampaně, e-maily, weby a aplikace. Každou "
                     "službu můžete využít samostatně, nejvíc přinesou dohromady."),
    dict(src="sprava-reklam-v-online-prostredi", path="/sprava-reklam-v-online-prostredi/",
         kind="service", nav="sluzby", crumbs=[HOME, SERVICES],
         service="Správa reklam a online kampaní", min_price=15000,
         title="Správa reklam a online kampaní | Advenue digital",
         description="Správa digitálních kampaní v Google Ads, Skliku, na Facebooku, Instagramu "
                     "a LinkedInu. Řídíme je podle ceny za lead a tržeb e-shopu. Od 15 000 Kč měsíčně."),
    dict(src="e-mail-marketing", path="/e-mail-marketing/", kind="service", nav="sluzby",
         crumbs=[HOME, SERVICES], service="E-mail marketing",
         title="E-mail marketing a automatizace | Advenue digital",
         description="E-mailové automatizace, které vracejí zákazníky e-shopů k nákupu a nové leady "
                     "vedou k poptávce. Newslettery, segmentace a A/B testy."),
    dict(src="weby-e-shopy-vyvoj-aplikaci", path="/weby-e-shopy-vyvoj-aplikaci/", kind="service",
         nav="sluzby", crumbs=[HOME, SERVICES], service="Weby, e-shopy a vývoj aplikací",
         title="Weby, e-shopy a vývoj aplikací na míru | Advenue digital",
         description="E-shopy, landing pages a aplikace na míru, které z návštěvníků dělají objednávky "
                     "a poptávky. Aplikace od 25 000 Kč, hotové do 14 dnů."),
    dict(src="o-nas", path="/o-nas/", kind="page", nav="o-nas", crumbs=[HOME],
         title="O nás | Advenue digital",
         description="Pražská agentura specialistů na generování leadů a e-commerce. Komunikujete "
                     "přímo se seniorním specialistou, bez account managera uprostřed."),
    dict(src="reference", path="/reference/", kind="page", nav="reference", crumbs=[HOME],
         title="Reference | Advenue digital",
         description="Výběr z našich projektů: weby a kampaně pro absl.cz, SCALL, AutoTarga, "
                     "Livesupp a další. Weby si můžete rovnou proklikat."),
    dict(src="cenik", path="/cenik/", kind="page", nav="cenik", crumbs=[HOME],
         title="Ceník služeb | Advenue digital",
         description="Správa kampaní od 15 000 Kč měsíčně, aplikace na míru od 25 000 Kč. "
                     "Přesnou cenu vám řekneme po auditu zdarma."),
    dict(src="caste-otazky", path="/caste-otazky/", kind="faq", nav=None, crumbs=[HOME],
         title="Časté otázky | Advenue digital",
         description="Kolik stojí správa kampaní, jestli je v ceně rozpočet na reklamu, co obsahuje "
                     "audit zdarma a s kým budete komunikovat."),
    dict(src="kontakt", path="/kontakt/", kind="page", nav="kontakt", crumbs=[HOME],
         title="Kontakt | Advenue digital",
         description="Napište nám, s čím potřebujete pomoct. Ozveme se a úvodní audit uděláme "
                     "zdarma. Advenue digital s.r.o., Jičínská 226/17, Praha 3."),
    dict(src="ochrana-osobnich-udaju", path="/ochrana-osobnich-udaju/", kind="page", nav=None,
         crumbs=[HOME], title="Ochrana osobních údajů | Advenue digital",
         description="Jak nakládáme s údaji, které nám svěříte přes tento web, jaké cookies "
                     "používáme a jaká máte práva."),
    dict(src="navody", path="/navody/", kind="page", nav="navody", crumbs=[HOME],
         title="Návody na marketing krok za krokem | Advenue digital",
         description="Postupy krok za krokem: Google Analytics 4, reklama na Facebooku a Instagramu, "
                     "měření konverzí v Google Ads a Skliku, e-maily."),
    dict(src="navody-nastaveni-google-analytics-4", path="/navody/nastaveni-google-analytics-4/",
         kind="article", nav="navody", crumbs=[HOME, GUIDES],
         title="Jak nastavit Google Analytics 4 | Advenue digital",
         description="Bez měření je marketing jen odhad. Postup, jak GA4 nastavit správně hned "
                     "napoprvé, včetně věcí, na které se často zapomíná."),
    dict(src="navody-reklama-na-facebooku-a-instagramu",
         path="/navody/reklama-na-facebooku-a-instagramu/", kind="article", nav="navody",
         crumbs=[HOME, GUIDES],
         title="Reklama na Facebooku a Instagramu: návod | Advenue digital",
         description="Tlačítko „Propagovat příspěvek“ většinou přinese jen lajky. Postup, jak spustit "
                     "kampaň na Facebooku a Instagramu, která přivádí zákazníky."),
    dict(src="navody-mereni-konverzi-google-ads", path="/navody/mereni-konverzi-google-ads/",
         kind="article", nav="navody", crumbs=[HOME, GUIDES],
         title="Jak měřit konverze z Google Ads | Advenue digital",
         description="Google Ads bez měření konverzí optimalizuje na kliky. S měřením na poptávky "
                     "a objednávky. Dvě cesty, jak ho nastavit."),
    dict(src="navody-mereni-konverzi-sklik", path="/navody/mereni-konverzi-sklik/",
         kind="article", nav="navody", crumbs=[HOME, GUIDES],
         title="Jak nastavit měření konverzí v Skliku | Advenue digital",
         description="Konverzní kód, retargeting a povinný parametr souhlasu. Postup, jak nastavit "
                     "konverze v Skliku, aby se kampaně daly řídit podle výsledků."),
    dict(src="navody-jak-napsat-e-mail-ktery-lide-otevrou",
         path="/navody/jak-napsat-e-mail-ktery-lide-otevrou/", kind="article", nav="navody",
         crumbs=[HOME, GUIDES],
         title="Jak napsat e-mail, který lidé otevřou | Advenue digital",
         description="Odesílatel, předmět, preheader a doručitelnost. Osm věcí, které rozhodují, "
                     "jestli e-mail skončí přečtený, nebo ve spamu."),
]

NOT_FOUND = dict(src="404", path="/404.html", kind="404", nav=None,
                 title="Stránka nenalezena | Advenue digital",
                 description="Tuhle stránku jsme nenašli.")

NAV = [("sluzby", "Služby", "/nase-sluzby/"), ("o-nas", "O nás", "/o-nas/"),
       ("reference", "Reference", "/reference/"), ("cenik", "Ceník služeb", "/cenik/"),
       ("navody", "Návody", "/navody/"), ("kontakt", "Kontakt", "/kontakt/")]

ARROW = ('<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" stroke-linecap="round" '
         'stroke-linejoin="round"/></svg>')


def esc(text):
    return html.escape(text, quote=True)


def plain(fragment):
    """Visible text of an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def asset_versions():
    out = {}
    for name in ("site.css", "site.js"):
        digest = hashlib.sha1((SRC / "assets" / name).read_bytes()).hexdigest()[:10]
        out[name] = f"/assets/{name}?v={digest}"
    return out


def header(nav_key):
    links = "\n".join(
        f'      <a href="{url}"' + (' aria-current="page"' if key == nav_key else "") + f">{label}</a>"
        for key, label, url in NAV)
    return f"""<header class="topbar" id="topbar">
<div class="wrap wrap--wide">
  <nav class="nav" aria-label="Hlavní navigace">
    <a class="brand" href="/" aria-label="Advenue digital, úvod">
      <span>Advenue<small>digital</small></span>
    </a>
    <button class="menu-btn" id="menu-btn" type="button" aria-expanded="false" aria-controls="nav-links" aria-label="Otevřít menu"><span></span><span></span><span></span></button>
    <div class="nav-links" id="nav-links">
{links}
      <a class="btn btn--primary" href="/kontakt/">Chci audit zdarma</a>
    </div>
  </nav>
</div>
</header>"""


FOOTER = """<footer>
  <div class="wrap foot-grid">
    <div>
      <a class="brand" href="/"><span>Advenue<small>digital</small></span></a>
      <p>Výkonnostní marketing, e-mail marketing, weby a aplikace.</p>
    </div>
    <div>
      <span class="label">Služby</span>
      <a href="/sprava-reklam-v-online-prostredi/">Výkonnostní marketing</a>
      <a href="/e-mail-marketing/">E-mail marketing</a>
      <a href="/weby-e-shopy-vyvoj-aplikaci/">Weby a aplikace</a>
    </div>
    <div>
      <span class="label">Agentura</span>
      <a href="/o-nas/">O nás</a>
      <a href="/reference/">Reference</a>
      <a href="/cenik/">Ceník služeb</a>
      <a href="/caste-otazky/">Časté otázky</a>
      <a href="/navody/">Návody</a>
      <a href="/kontakt/">Kontakt</a>
      <a href="https://www.linkedin.com/company/advenue/" target="_blank" rel="noopener">LinkedIn</a>
      <a href="https://www.facebook.com/advenuedigi" target="_blank" rel="noopener">Facebook</a>
    </div>
    <div>
      <span class="label">Kontakt</span>
      <address>Advenue digital s.r.o.<br>Jičínská 226/17, 130 00 Praha 3<br>IČO: 14173921</address>
      <a href="/kontakt/">info@advenue.cz</a>
      <a href="/kontakt/">+420 603 765 797</a>
    </div>
  </div>
  <div class="wrap foot">
    <span>© 2026 Advenue digital s.r.o.</span>
    <span class="foot-links"><a href="/ochrana-osobnich-udaju/">Ochrana osobních údajů</a><a href="https://advenue.cz">advenue.cz</a></span>
  </div>
</footer>"""

NOT_FOUND_BODY = f"""  <div class="wrap">
    <header class="page-head">
      <p class="label">Chyba 404</p>
      <h1>Tuhle stránku jsme nenašli</h1>
      <p class="lead">Adresa se mohla změnit, nebo v ní je překlep. Zkuste začít od úvodu, nebo nám rovnou napište.</p>
      <nav class="jump" aria-label="Kam dál">
        <a class="s-ads" href="/sprava-reklam-v-online-prostredi/">Výkonnostní marketing</a>
        <a class="s-mail" href="/e-mail-marketing/">E-mail marketing</a>
        <a class="s-web" href="/weby-e-shopy-vyvoj-aplikaci/">Weby a aplikace</a>
        <a class="s-web" href="/navody/">Návody</a>
      </nav>
    </header>
    <div class="cta-band">
      <h2>Hledáte, jak získat víc poptávek? Začněte auditem zdarma.</h2>
      <a class="btn btn--primary" href="/kontakt/">Chci audit zdarma
        {ARROW}
      </a>
    </div>
    <p><a class="more" href="/">← Zpět na úvod</a></p>
  </div>
"""


def organization():
    return {
        "@type": "ProfessionalService",
        "@id": ORG_ID,
        "name": "Advenue digital s.r.o.",
        "alternateName": SITE_NAME,
        "description": "Agentura specialistů na generování leadů a e-commerce: výkonnostní kampaně, "
                       "e-mail marketing, weby a aplikace.",
        "url": DOMAIN + "/",
        "image": OG_IMAGE,
        "email": "info@advenue.cz",
        "telephone": "+420603765797",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "Jičínská 226/17",
            "addressLocality": "Praha 3 – Žižkov",
            "postalCode": "130 00",
            "addressCountry": "CZ",
        },
        "identifier": {"@type": "PropertyValue", "propertyID": "IČO", "value": "14173921"},
        "areaServed": {"@type": "Country", "name": "Česká republika"},
        "sameAs": [LINKEDIN, FACEBOOK],
    }


def breadcrumbs(page, h1):
    trail = page.get("crumbs", []) + [(h1, page["path"])]
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": DOMAIN + path}
            for i, (name, path) in enumerate(trail, 1)
        ],
    }


def structured_data(page, body, h1):
    url = DOMAIN + page["path"]
    publisher = {"@type": "Organization", "@id": ORG_ID, "name": "Advenue digital s.r.o.",
                 "url": DOMAIN + "/"}
    kind = page["kind"]
    if kind == "404":
        return None
    if kind == "home":
        graph = [organization(), {
            "@type": "WebSite", "@id": DOMAIN + "/#web", "url": DOMAIN + "/", "name": SITE_NAME,
            "inLanguage": "cs", "publisher": {"@id": ORG_ID}}]
    else:
        graph = [breadcrumbs(page, h1)]
    if kind == "service":
        service = {"@type": "Service", "name": page["service"], "serviceType": page["service"],
                   "url": url, "description": page["description"], "provider": publisher,
                   "areaServed": {"@type": "Country", "name": "Česká republika"}}
        if page.get("min_price"):
            service["offers"] = {"@type": "Offer", "priceSpecification": {
                "@type": "PriceSpecification", "minPrice": page["min_price"], "priceCurrency": "CZK"}}
        graph.append(service)
    if kind == "faq":
        questions = re.findall(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", body, re.S)
        if not questions:
            sys.exit("FAQ page has no <summary>/<p> pairs")
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": plain(q),
             "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in questions]})
    if kind == "article":
        graph.append({"@type": "Article", "headline": h1, "description": page["description"],
                      "image": OG_IMAGE, "datePublished": PUBLISHED, "dateModified": MODIFIED,
                      "inLanguage": "cs", "mainEntityOfPage": url,
                      "author": {"@type": "Organization", "name": SITE_NAME, "url": DOMAIN + "/"},
                      "publisher": publisher})
    data = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")


def render(page, assets):
    body = NOT_FOUND_BODY if page["kind"] == "404" else (
        SRC / "pages" / f"{page['src']}.html").read_text(encoding="utf-8")
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if len(h1s) != 1:
        sys.exit(f"{page['src']}: expected exactly one <h1>, found {len(h1s)}")
    h1 = plain(h1s[0])
    canonical = DOMAIN + page["path"]
    robots = ('<meta name="robots" content="noindex, nofollow">\n'
              if not INDEXABLE or page["kind"] == "404" else "")
    canonical_tag = "" if page["kind"] == "404" else f'<link rel="canonical" href="{canonical}">\n'
    og_type = "article" if page["kind"] == "article" else "website"
    preload = ('<link rel="preload" as="image" href="/assets/hero.jpg" fetchpriority="high">\n'
               if page["kind"] == "home" else "")
    ld = structured_data(page, body, h1)
    ld_tag = f'<script type="application/ld+json">\n{ld}\n</script>\n' if ld else ""
    out = f"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title>
<meta name="description" content="{esc(page['description'])}">
{robots}{canonical_tag}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="cs_CZ">
<meta property="og:title" content="{esc(page['title'])}">
<meta property="og:description" content="{esc(page['description'])}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Advenue digital – marketing, který se dá spočítat">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;500;700&family=Roboto:wght@400;500&family=Roboto+Mono:wght@500&display=swap">
<link rel="stylesheet" href="{assets['site.css']}">
{preload}{ld_tag}</head>
<body>
{header(page['nav'])}

<main>
{body.rstrip()}
</main>

{FOOTER}

<script src="{assets['site.js']}" defer></script>
</body>
</html>
"""
    if BASE:  # serve from a sub-folder: prefix every root-relative link and asset
        out = re.sub(r'((?:href|src)=")/(?!/)', rf"\1{BASE}/", out)
    return out


def write(rel, text):
    target = DIST / rel.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def main():
    # Files are overwritten, never deleted: after renaming a page, build into a fresh
    # folder (OUT_DIR=...) so no stale copy of the old URL is left behind.
    shutil.copytree(SRC / "assets", DIST / "assets", dirs_exist_ok=True)
    shutil.copytree(SRC / "static", DIST, dirs_exist_ok=True)
    assets = asset_versions()
    for page in PAGES:
        if len(page["title"]) > 60:
            sys.exit(f"{page['path']}: title is {len(page['title'])} chars (max 60)")
        if len(page["description"]) > 155:
            sys.exit(f"{page['path']}: description is {len(page['description'])} chars (max 155)")
        write(page["path"] + "index.html", render(page, assets))
    write("/404.html", render(NOT_FOUND, assets))

    urls = "\n".join(f"  <url><loc>{DOMAIN}{p['path']}</loc></url>" for p in PAGES)
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n")
    if INDEXABLE:
        robots = f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n"
    else:  # preview: crawlers may fetch pages, but every page carries noindex
        robots = "# Preview build: pages carry noindex. No sitemap on purpose.\nUser-agent: *\nAllow: /\n"
    write("/robots.txt", robots)
    print(f"Built {len(PAGES)} pages + 404 into dist/  |  SITE_ENV={SITE_ENV}  |  "
          f"{'INDEXABLE (production)' if INDEXABLE else 'NOINDEX (preview)'}"
          + (f"  |  BASE_PATH={BASE}" if BASE else ""))


if __name__ == "__main__":
    main()
