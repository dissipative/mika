#!/usr/bin/env python3
"""Build Mika's care guide into _site/ (standard library only, Python 3.11+).

    python3 build.py              build + run all checks
    python3 build.py --serve      build, then serve at http://localhost:8000/mika/
    python3 build.py --serve 9000 --prefix /other-repo/

Output:
    _site/index.html        English content; redirects to the saved or browser language
    _site/<code>/index.html one page per language (en, es, val, ru)
    _site/assets/...        stylesheet, script, icon, photos

All URLs are relative, so the site works at a domain root and under a
GitHub Pages repository subpath (https://<user>.github.io/<repo>/).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content" / "guide.toml"
TEMPLATE = ROOT / "src" / "template.html"
OUT = ROOT / "_site"

STATIC = {  # source -> destination inside _site
    ROOT / "src" / "styles.css": "assets/styles.css",
    ROOT / "src" / "site.js": "assets/site.js",
    ROOT / "src" / "favicon.svg": "assets/favicon.svg",
}
IMAGES = ROOT / "assets" / "img"

# Keys that are not part of the "main guide" word count.
NOT_COUNTED = ("meta.", "ui.", "hero.alt", "walks.photo_alt", "water.photo_alt", "home.photo_alt")
# Keys inside collapsed <details>: secondary text, reported apart from the visible guide.
COLLAPSED = ("walks.more", "health.status")
# Target: roughly 250–400 visible words. Spanish and Valencian run ~8 % longer
# than English for the same meaning, so flag only clear overruns.
WORD_RANGE = (250, 440)

# Public page: refuse content that looks like private details or placeholders.
FORBIDDEN = [
    (re.compile(r"\b(TODO|TBD|FIXME|XXX|ADD [A-Z ]+ HERE)\b"), "placeholder text"),  # case-sensitive: "todo" is Spanish
    (re.compile(r"\b(placeholder|lorem ipsum)\b", re.I), "placeholder text"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "an e-mail address"),
    (re.compile(r"(?<![\d:])\+?\d[\d ().-]{7,}\d(?![\d:])"), "a phone-like number"),
    (re.compile(r"https?://", re.I), "a URL"),
]


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------
def load_content() -> tuple[dict, list[dict], dict[str, dict[str, str]]]:
    data = tomllib.loads(CONTENT.read_text(encoding="utf-8"))
    site = data.pop("site", {})
    languages = data.pop("languages", None)
    if not languages:
        raise BuildError("guide.toml: no [[languages]] defined")
    codes = [lang["code"] for lang in languages]

    strings: dict[str, dict[str, str]] = {}

    def walk(node: dict, path: str) -> None:
        for key, value in node.items():
            full = f"{path}.{key}" if path else key
            if isinstance(value, dict) and set(value) & set(codes):
                strings[full] = value
            elif isinstance(value, dict):
                walk(value, full)
            else:
                raise BuildError(f"guide.toml: '{full}' is not a table of translations")

    walk(data, "")

    errors = []
    for key, tr in strings.items():
        missing = [c for c in codes if not str(tr.get(c, "")).strip()]
        extra = [c for c in tr if c not in codes]
        if missing:
            errors.append(f"{key}: missing or empty for {', '.join(missing)}")
        if extra:
            errors.append(f"{key}: unknown language key(s) {', '.join(extra)}")
        for code, text in tr.items():
            if text.count("**") % 2:
                errors.append(f"{key} [{code}]: unbalanced ** bold markers")
            for pattern, what in FORBIDDEN:
                if pattern.search(text):
                    errors.append(f"{key} [{code}]: looks like {what} — public page, remove it")
    if errors:
        raise BuildError("content errors:\n  " + "\n  ".join(errors))
    url = site.get("url", "").strip()
    if url and not re.match(r"^https://[^\s]+/$", url):
        raise BuildError("guide.toml: [site] url must start with https:// and end with /")
    site["url"] = url
    return site, languages, strings


TYPO = [
    (re.compile(r" (°C)"), "\u00a0\\1"),            # 15 °C never splits
    (re.compile(r"~ "), "~\u00a0"),                  # ~ 9:00
    (re.compile(r" (—|–) "), "\u00a0\\1 "),          # no dash at the start of a line
    (re.compile(r"(\d) (h|hours|horas|hores|часа|часов)\b"), "\\1\u00a0\\2"),
    (re.compile(r"\b(on|off|Dog)-(lead|sitting)\b"), "\\1\u2011\\2"),  # keep "on-lead" on one line
]


def typography(text: str) -> str:
    for pattern, repl in TYPO:
        text = pattern.sub(repl, text)
    return text


def to_html(text: str) -> str:
    out = html.escape(typography(text), quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)


def to_attr(text: str) -> str:
    return html.escape(typography(text.replace("**", "")), quote=True)


def word_count(strings: dict[str, dict[str, str]], code: str, collapsed: bool = False) -> int:
    """Words of guide text: visible text by default, or only the collapsed text."""
    total = 0
    for key, tr in strings.items():
        if key.startswith(NOT_COUNTED) or (key in COLLAPSED) != collapsed:
            continue
        # A word = a token with at least one letter ("9:00–10:00" is not prose).
        tokens = re.findall(r"[^\W_]+(?:[-'’·][^\W_]+)*", tr[code].replace("**", ""))
        total += sum(1 for t in tokens if re.search(r"[^\W\d_]", t))
    return total


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
PLACEHOLDER = re.compile(r'(="|\s)?\{\{\s*([@\w.]+)\s*\}\}')


def root_redirect_script(languages: list[dict]) -> str:
    table = json.dumps([{"code": l["code"], "match": l.get("match", [])} for l in languages],
                       ensure_ascii=False, separators=(",", ":"))
    default = languages[0]["code"]
    return (
        "<script>(function(){var L=" + table + ",d=" + json.dumps(default) + ",c=null;"
        "try{c=localStorage.getItem('mika-lang')}catch(e){}"
        "if(!L.some(function(l){return l.code===c})){c=d;"
        "var n=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||''];"
        "outer:for(var i=0;i<n.length;i++){var p=String(n[i]).toLowerCase().split('-')[0];"
        "for(var j=0;j<L.length;j++){if(L[j].match.indexOf(p)>-1){c=L[j].code;break outer}}}}"
        "if(c!==d){location.replace(c+'/'+location.hash)}})();</script>"
    )


def render(template: str, site: dict, languages: list[dict], strings: dict, lang: dict, base: str,
           is_root: bool) -> str:
    code = lang["code"]

    switcher = ["    <ul>"]
    for other in languages:
        current = ' aria-current="page"' if other["code"] == code else ""
        switcher.append(
            f'      <li><a href="{base}{other["code"]}/" hreflang="{other["html"]}" lang="{other["html"]}"'
            f' data-lang-link="{other["code"]}"{current}>{html.escape(other["label"])}</a></li>'
        )
    switcher.append("    </ul>")

    alternates = [f'<link rel="canonical" href="{base}{code}/">']
    alternates += [f'<link rel="alternate" hreflang="{l["html"]}" href="{base}{l["code"]}/">' for l in languages]
    alternates.append(f'<link rel="alternate" hreflang="x-default" href="{base or "./"}">')

    special = {
        "html_lang": lang["html"],
        "og_locale": lang.get("og", ""),
        "base": base,
        # Link previews (messengers) need absolute URLs; fall back to relative.
        "og_image": (site["url"] or base) + "assets/img/og.jpg",
        "og_url": (site["url"] + ("" if is_root else code + "/")) if site["url"] else ("./" if is_root else ""),
        "switcher": "\n".join(switcher),
        "alternates": "\n".join(alternates),
        "head_script": root_redirect_script(languages) if is_root else "",
    }

    def substitute(match: re.Match) -> str:
        prefix, name = match.group(1) or "", match.group(2)
        if name.startswith("@"):
            key = name[1:]
            if key not in special:
                raise BuildError(f"template: unknown special placeholder {{{{{name}}}}}")
            return prefix + special[key]
        if name not in strings:
            raise BuildError(f"template: no content for {{{{{name}}}}} in guide.toml")
        text = strings[name][code]
        return prefix + (to_attr(text) if prefix == '="' else to_html(text))

    return PLACEHOLDER.sub(substitute, template)


# --------------------------------------------------------------------------
# Checks on the generated HTML
# --------------------------------------------------------------------------
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "use",
        "path", "circle", "ellipse", "rect"}


class PageChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.ids: list[str] = []
        self.refs: list[tuple[str, str]] = []  # (attr, value)
        self.errors: list[str] = []
        self.lang = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "img" and a.get("alt") is None:
            self.errors.append(f"line {self.getpos()[0]}: <img> without alt")
        for attr in ("href", "src"):
            if a.get(attr):
                self.refs.append((attr, a[attr]))
        for attr in ("srcset", "imagesrcset"):
            if a.get(attr):
                for part in a[attr].split(","):
                    self.refs.append((attr, part.strip().split(" ")[0]))
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1][0] != tag:
            opened = self.stack[-1] if self.stack else ("nothing", 0)
            self.errors.append(f"line {self.getpos()[0]}: </{tag}> closes <{opened[0]}> from line {opened[1]}")
            return
        self.stack.pop()


def check_page(path: Path, site: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(site)
    errors = []
    if PLACEHOLDER.search(text):
        errors.append(f"{rel}: unrendered placeholder")
    checker = PageChecker()
    checker.feed(text)
    checker.close()
    errors += [f"{rel}: {e}" for e in checker.errors]
    if checker.stack:
        errors.append(f"{rel}: unclosed tags {checker.stack}")
    dupes = {i for i in checker.ids if checker.ids.count(i) > 1}
    if dupes:
        errors.append(f"{rel}: duplicate ids {sorted(dupes)}")
    for attr, ref in checker.refs:
        parts = urlsplit(ref)
        if parts.scheme or ref.startswith("//"):
            errors.append(f"{rel}: external {attr} '{ref}' — keep the site self-contained")
            continue
        if ref.startswith("/"):
            errors.append(f"{rel}: root-absolute {attr} '{ref}' breaks under a repository subpath")
            continue
        if parts.fragment and not parts.path:
            if parts.fragment not in checker.ids:
                errors.append(f"{rel}: link to missing #{parts.fragment}")
            continue
        target = (path.parent / unquote(parts.path)).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file() or site.resolve() not in target.parents:
            errors.append(f"{rel}: {attr} '{ref}' does not resolve inside _site")
    return errors


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def check_css(path: Path) -> list[str]:
    """Catch unbalanced braces: one stray '{' silently nests every later rule (print styles included)."""
    css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
    css = re.sub(r'"(?:\\.|[^"\\])*"', '""', css)
    depth, errors = 0, []
    for number, line in enumerate(css.splitlines(), 1):
        if line.startswith("@") and depth:
            errors.append(f"{path.name} line {number}: top-level at-rule opened inside another block")
        depth += line.count("{") - line.count("}")
        if depth < 0:
            errors.append(f"{path.name} line {number}: unexpected '}}'")
            depth = 0
    if depth:
        errors.append(f"{path.name}: {depth} unclosed '{{'")
    return errors


def build() -> None:
    css_errors = check_css(ROOT / "src" / "styles.css")
    if css_errors:
        raise BuildError("stylesheet errors:\n  " + "\n  ".join(css_errors))
    site, languages, strings = load_content()
    template = TEMPLATE.read_text(encoding="utf-8")

    unused = sorted(k for k in strings if "{{" + k + "}}" not in template.replace(" ", ""))
    if unused:
        print(f"warning: content keys not used by the template: {', '.join(unused)}")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for src, dest in STATIC.items():
        shutil.copy2(src, OUT / dest)
    shutil.copytree(IMAGES, OUT / "assets" / "img")
    (OUT / ".nojekyll").write_text("")

    pages = [(OUT / "index.html", languages[0], "", True)]
    pages += [(OUT / l["code"] / "index.html", l, "../", False) for l in languages]
    for path, lang, base, is_root in pages:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(template, site, languages, strings, lang, base, is_root), encoding="utf-8")

    errors = []
    for path, *_ in pages:
        errors += check_page(path, OUT)
    if errors:
        raise BuildError("output errors:\n  " + "\n  ".join(errors))

    print(f"built {len(pages)} pages into {OUT.relative_to(ROOT)}/")
    lo, hi = WORD_RANGE
    for lang in languages:
        n = word_count(strings, lang["code"])
        extra = word_count(strings, lang["code"], collapsed=True)
        flag = "" if lo <= n <= hi else f"  <-- outside the roughly {lo}–{hi} target"
        print(f"  {lang['code']:<4} {lang['label']:<9} {n:>4} visible words + {extra} in accordions{flag}")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"  total size {size / 1024:.0f} KiB (all image sizes included)")


def serve(port: int, prefix: str) -> None:
    import functools
    import http.server

    prefix = "/" + prefix.strip("/") + "/" if prefix.strip("/") else "/"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if prefix != "/" and path.split("?")[0].rstrip("/") == prefix.rstrip("/"):
                path = prefix  # /mika -> /mika/
            if not path.startswith(prefix):
                return str(OUT / "__not_found__")
            return super().translate_path("/" + path[len(prefix):])

        def send_head(self):
            if prefix != "/" and self.path.split("?")[0] == prefix.rstrip("/"):
                self.send_response(301)
                self.send_header("Location", prefix)
                self.end_headers()
                return None
            return super().send_head()

    handler = functools.partial(Handler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving http://localhost:{port}{prefix}  (Ctrl+C to stop)")
        httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", nargs="?", const=8000, type=int, metavar="PORT",
                        help="serve _site after building (default port 8000)")
    parser.add_argument("--prefix", default="/mika/", help="URL subpath to simulate when serving (default /mika/)")
    args = parser.parse_args()
    try:
        build()
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    if args.serve:
        try:
            serve(args.serve, args.prefix)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
