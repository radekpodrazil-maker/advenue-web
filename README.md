# advenue-web

Web Advenue digital, který nahradí starý WordPress na **advenue.cz**. Každá stránka je samostatné
statické HTML s vlastní URL, aby Google mohl hodnotit služby a návody zvlášť. Obsah se zobrazí
i bez JavaScriptu.

- Produkce (po spuštění): https://advenue.cz, hosting Cloudflare Pages
- Testovací náhled: https://radekpodrazil-maker.github.io/advenue-web/ (vždy `noindex`)
- Kontaktní formulář posílá poptávky na webhook v Make.com, viz `src/assets/site.js`

## Struktura

| Cesta | Co tam je |
|---|---|
| `src/pages/*.html` | obsah jednotlivých stránek (jen to, co je mezi menu a patičkou) |
| `src/assets/` | `site.css`, `site.js`, úvodní obrázek `hero.jpg`, obrázek pro sdílení `og-image.jpg` |
| `src/static/` | soubory, které jdou do kořene webu beze změny: `_redirects`, `_headers`, `favicon.svg` |
| `build.py` | poskládá web do `dist/`. Obsahuje seznam stránek (URL, title, description), menu, patičku, strukturovaná data, sitemap a robots.txt |
| `check.py` | kontrola hotového buildu: title, description, canonical, jedno H1, JSON-LD, odkazy a přesměrování |
| `deploy/github-pages-preview.yml` | připravený workflow pro testovací náhled na GitHub Pages (viz níže) |

## Stránky

| URL | Obsah |
|---|---|
| `/` | úvod |
| `/nase-sluzby/` | rozcestník služeb (zachovaná URL starého webu) |
| `/sprava-reklam-v-online-prostredi/` | výkonnostní reklama, hlavní SEO stránka |
| `/e-mail-marketing/` | e-mail marketing |
| `/weby-e-shopy-vyvoj-aplikaci/` | weby, e-shopy a aplikace |
| `/o-nas/`, `/reference/`, `/cenik/`, `/caste-otazky/`, `/kontakt/`, `/ochrana-osobnich-udaju/` | ostatní stránky |
| `/navody/` | rozcestník návodů |
| `/navody/nastaveni-google-analytics-4/` | návod GA4 |
| `/navody/reklama-na-facebooku-a-instagramu/` | návod Meta Ads |
| `/navody/mereni-konverzi-google-ads/` | návod konverze Google Ads |
| `/navody/mereni-konverzi-sklik/` | návod konverze Sklik |
| `/navody/jak-napsat-e-mail-ktery-lide-otevrou/` | návod e-maily |

## Build

```
python3 build.py                       # náhled, noindex
SITE_ENV=production python3 build.py   # produkce, indexovatelné
python3 check.py dist production       # kontrola
```

Stačí Python 3.8+ bez dalších balíčků. Build soubory v `dist/` jen přepisuje, nemaže je. Po přejmenování
stránky proto stavějte do čisté složky: `OUT_DIR=/jina/slozka python3 build.py`.

## Přepínač indexace (noindex)

O všem rozhoduje proměnná prostředí `SITE_ENV`:

| Hodnota | Výsledek |
|---|---|
| `production` | stránky bez `noindex`, `robots.txt` odkazuje na `sitemap.xml` |
| `preview` | každá stránka má `<meta name="robots" content="noindex, nofollow">` |
| nenastaveno | na Cloudflare Pages produkční větev (`main`) = `production`, cokoli jiného = `preview` |

Na Cloudflare tedy produkce funguje i bez nastavení a náhledy větví mají `noindex` automaticky.
Pro jistotu nastavte i `SITE_ENV` (viz níže). Adresy `*.pages.dev` mají navíc `X-Robots-Tag: noindex`
z `_headers`, takže se do Googlu nedostanou ani produkční kopie mimo advenue.cz. Stránka 404 je vždy `noindex`.

## Nasazení na Cloudflare Pages

1. Cloudflare → **Workers & Pages → Create → Pages → Connect to Git** → vyberte repo `advenue-web`.
2. Nastavení buildu:
   - Production branch: `main`
   - Framework preset: `None`
   - Build command: `python3 build.py`
   - Build output directory: `dist`
   - Environment variables: v **Production** `SITE_ENV = production`, v **Preview** `SITE_ENV = preview`
3. **Save and Deploy**. Web poběží na `<projekt>.pages.dev`. Zkontrolujte ho tam.
4. **Custom domains → Set up a custom domain** → `advenue.cz`, potom i `www.advenue.cz`.
5. Pokud DNS domény advenue.cz ještě nespravuje Cloudflare, je potřeba převést nameservery. **Pozor na e-mail:**
   před přepnutím zkontrolujte, že Cloudflare převzal záznamy MX, SPF, DKIM a DMARC pro Google Workspace.
6. **www → advenue.cz**: Rules → Redirect Rules → šablona „Redirect from WWW to root“ (301, zachovat cestu).
7. **http → https**: SSL/TLS → Edge Certificates → **Always Use HTTPS** zapnout.
8. Po spuštění:
   - ověřte staré adresy (třeba `/voice-bot/`, `/kandidatomat/`, `/author/radek/`): musí vracet 301
   - v Google Search Console odešlete `https://advenue.cz/sitemap.xml`
   - nechte zaindexovat hlavní stránky

## Přesměrování ze starého webu

Seznam je v `src/static/_redirects` (301, každá adresa s lomítkem i bez něj). Cloudflare je provede dřív,
než hledá soubor, proto tam nesmí být adresa, která na novém webu existuje. Hlídá to `check.py`.
Admin WordPressu (`/wp-admin/`, `/wp-login.php`, `/xmlrpc.php`), soubory `/wp-content/` a demo
články šablony z roku 2016 záměrně vracejí 404.

## Úpravy obsahu

- Text stránky: upravte `src/pages/<stránka>.html`.
- Title a description: seznam `PAGES` v `build.py`. Title má max. 60 znaků, description max. 155,
  build jinak skončí chybou.
- Menu a patička: funkce `header()` a `FOOTER` v `build.py`.
- Odkazy mezi stránkami pište od kořene (`/kontakt/`). Build je při `BASE_PATH` sám upraví pro náhled.

## Testovací náhled na GitHub Pages

Náhled běží na https://radekpodrazil-maker.github.io/advenue-web/, je vždy `noindex` a pracuje pod
cestou `/advenue-web/`. GitHub Pages ho servíruje z větve **`gh-pages`** (Settings → Pages → Source:
*Deploy from a branch*, `gh-pages`, `/ (root)`). V té větvi je jen hotový build, žádné zdrojáky.

**Náhled se sám neaktualizuje.** Po změně v `main` je potřeba:

1. Sestavit náhled do čisté složky a zkontrolovat ho:
   ```
   SITE_ENV=preview BASE_PATH=/advenue-web OUT_DIR=/tmp/nahled python3 build.py
   python3 check.py /tmp/nahled preview /advenue-web
   ```
2. Do složky přidat prázdný soubor `.nojekyll`, aby GitHub soubory neupravoval přes Jekyll.
3. Obsah složky nahrát jako nový commit do větve `gh-pages`, která nahradí předchozí obsah.

Stačí Claudovi napsat „aktualizuj náhled“.

Druhá možnost je workflow `deploy/github-pages-preview.yml`, který náhled sestaví sám po každém pushi
do `main`. Je potřeba ho přesunout do `.github/workflows/` (na GitHubu přes *Add file → Create new file*)
a v Settings → Pages přepnout Source na **GitHub Actions**. Claude ho sám nahrát nemůže, jeho přístup
ke GitHubu nemá oprávnění `workflow`. Po přechodu na Cloudflare Pages náhled na GitHubu není potřeba,
Cloudflare vytváří náhledy větví sám.
