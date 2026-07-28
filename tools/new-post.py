#!/usr/bin/env python3
"""Publish a markdown post to claytoncamera.com/writing/ — and update everything
that has to move with it.

WHY THIS EXISTS
---------------
Adding a post by hand means four separate edits (the post file, sitemap.xml, the
/writing/ hub list, the homepage cards) plus the PAGES array in
tests/seo-scan.sh. Miss one and the guard goes red — or worse, it stays green
while the post is an orphan nobody can crawl. This does all five from one
markdown file, so the invariants hold by construction.

USAGE
    python3 tools/new-post.py path/to/post.md --slug my-post-slug \
        --eyebrow "Technical SEO" --date 2026-07-28 --read-time "8 min read"

The markdown needs:
    # Title on the first line
    A first paragraph, which becomes the lede and the meta description.

Supported markdown: #/##/### headings, paragraphs, ordered/unordered lists,
fenced code blocks, > blockquotes, GFM tables, `inline code`, **bold**, *italic*,
[links](url), and a callout syntax:

    :::callout Label
    Body text.
    :::

Run tests/seo-scan.sh afterwards — it is the check that this did the right thing.
"""

import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://claytoncamera.com"
PERSON_ID = f"{BASE}/#person"


# --------------------------------------------------------------------------
# A small, deliberate markdown subset. Not a general parser — it only needs to
# handle what these posts actually use, and it must never emit broken HTML,
# because the guard parses the JSON-LD but not the body.
# --------------------------------------------------------------------------
def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def md_to_html(md: str) -> tuple[str, str, str]:
    """Return (title, lede_text, body_html)."""
    lines = md.replace("\r\n", "\n").split("\n")
    if not lines or not lines[0].startswith("# "):
        sys.exit("first line must be '# Title'")
    title = lines[0][2:].strip()

    out: list[str] = []
    lede = ""
    i = 1
    para: list[str] = []
    first_para_done = False

    def flush_para():
        nonlocal para, lede, first_para_done
        if not para:
            return
        text = " ".join(para).strip()
        para = []
        if not text:
            return
        if not first_para_done:
            first_para_done = True
            lede = re.sub(r"[*`\[\]]|\(https?://[^)]+\)", "", text).strip()
            out.append(f'      <p class="lede">{inline(text)}</p>')
        else:
            out.append(f"      <p>{inline(text)}</p>")

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para()
            lang = stripped[3:].strip()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            body = html.escape("\n".join(code))
            out.append(f"<pre><code>{body}</code></pre>" if not lang else f"<pre><code>{body}</code></pre>")
            continue

        if stripped.startswith(":::callout"):
            flush_para()
            label = stripped[len(":::callout"):].strip() or "Note"
            i += 1
            buf: list[str] = []
            while i < len(lines) and lines[i].strip() != ":::":
                buf.append(lines[i].strip())
                i += 1
            i += 1
            paras = [p for p in " ".join(buf).split("\n\n") if p.strip()]
            inner = "".join(f"<p>{inline(p)}</p>" for p in (paras or [" ".join(buf)]))
            out.append(
                '      <div class="callout">\n'
                f'        <span class="callout-label">{html.escape(label)}</span>\n'
                f"        {inner}\n"
                "      </div>"
            )
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush_para()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in header)
            trs = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            out.append(f"      <table>\n        <thead><tr>{th}</tr></thead>\n        <tbody>{trs}</tbody>\n      </table>")
            continue

        if stripped.startswith("> "):
            flush_para()
            quote = [stripped[2:]]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote.append(lines[i].strip()[2:])
                i += 1
            out.append(f"      <blockquote>{inline(' '.join(quote))}</blockquote>")
            continue

        m = re.match(r"^(#{2,3})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f"      <h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            flush_para()
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            items = []
            pat = r"^\d+\.\s+" if ordered else r"^[-*]\s+"
            while i < len(lines) and re.match(pat, lines[i].strip()):
                items.append(re.sub(pat, "", lines[i].strip()))
                i += 1
            tag = "ol" if ordered else "ul"
            lis = "".join(f"\n        <li>{inline(x)}</li>" for x in items)
            out.append(f"      <{tag}>{lis}\n      </{tag}>")
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return title, lede, "\n\n".join(out)


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>{title_esc} — Clayton Camera</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{url}">

  <meta property="og:type" content="article">
  <meta property="og:title" content="{title_esc}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{url}">
  <meta property="og:site_name" content="Clayton Camera">
  <meta property="og:image" content="{base}/assets/clayton-camera.jpg">
  <meta property="article:author" content="Clayton Camera">
  <meta property="article:published_time" content="{date}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{title_esc}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{base}/assets/clayton-camera.jpg">
  <meta name="theme-color" content="#08080d">

  <!-- author + publisher REFERENCE the canonical Person @id owned by the
       homepage. Never redefine it here — see the note in /index.html. -->
  <script type="application/ld+json">
{jsonld}
  </script>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/article.css">
</head>
<body>
  <div class="bg-grid"></div>

  <header class="top-header">
    <div class="wrap">
      <a class="logo" href="/">Clayton Camera</a>
      <nav><ul class="nav-links">
        <li><a href="/writing/">Writing</a></li>
        <li class="hide-sm"><a href="https://loopholemaxing.com/#creations">Creations</a></li>
        <li><a class="nav-cta" href="https://workwithclayton.com/">Work With Clayton</a></li>
      </ul></nav>
    </div>
  </header>

  <main class="wrap">
    <p class="crumbs"><a href="/">Home</a> → <a href="/writing/">Writing</a> → {crumb}</p>

    <article>
      <p class="eyebrow">{eyebrow}</p>
      <h1>{title_esc}</h1>
      <p class="byline">By <a href="/" rel="author">Clayton Camera</a> · {date_human} · {read_time}</p>

{body}

      <div class="author-card">
        <img src="/assets/clayton-camera.jpg" width="60" height="60" alt="Clayton Camera, technical founder and software engineer in Orlando, Florida">
        <div>
          <h3><a href="/" rel="author">Clayton Camera</a></h3>
          <p>Technical founder and software engineer in Orlando, Florida. Builds AI systems, autonomous agents, and full-stack software — including <a href="https://www.orbitroute.ai">OrbitRoute</a> and <a href="https://www.knockfiber.com/">KnockFiber</a>. Client work at <a href="https://workwithclayton.com/">workwithclayton.com</a>.</p>
        </div>
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <p><a href="/">Clayton Camera</a> · <a href="/writing/">Writing</a> · <a href="https://workwithclayton.com/">Work with Clayton</a> · <a href="https://www.linkedin.com/in/claytoncamera" rel="me">LinkedIn</a> · <a href="https://github.com/claytoncamera" rel="me">GitHub</a></p>
    <p class="footer-tagline">Orlando, Florida · Building live systems, not slide decks</p>
  </footer>
</body>
</html>
"""

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--eyebrow", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--read-time", default="6 min read")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--crumb", default="", help="short breadcrumb label; defaults to the title")
    args = ap.parse_args()

    md = pathlib.Path(args.markdown).read_text(encoding="utf-8")
    title, lede, body = md_to_html(md)
    slug = args.slug.strip("/")
    url = f"{BASE}/writing/{slug}/"
    crumb = args.crumb or title
    desc = html.escape(lede[:300], quote=True)
    y, m, d = args.date.split("-")
    date_human = f"{int(d)} {MONTHS[int(m) - 1]} {y}"

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": f"{url}#article",
                "headline": title,
                "description": lede[:300],
                "url": url,
                "mainEntityOfPage": url,
                "datePublished": args.date,
                "dateModified": args.date,
                "inLanguage": "en-US",
                "image": f"{BASE}/assets/clayton-camera.jpg",
                "author": {"@id": PERSON_ID},
                "publisher": {"@id": PERSON_ID},
                "isPartOf": {"@id": f"{BASE}/writing/#blog"},
                **({"keywords": args.keywords} if args.keywords else {}),
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Clayton Camera", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "Writing", "item": f"{BASE}/writing/"},
                    {"@type": "ListItem", "position": 3, "name": crumb},
                ],
            },
        ],
    }

    page = TEMPLATE.format(
        title_esc=html.escape(title, quote=True), desc=desc, url=url, base=BASE,
        date=args.date, date_human=date_human, read_time=args.read_time,
        eyebrow=html.escape(args.eyebrow), crumb=html.escape(crumb), body=body,
        jsonld=json.dumps(graph, indent=2, ensure_ascii=False),
    )

    out = ROOT / "writing" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")

    _add_to_sitemap(url, args.date)
    _add_to_hub(slug, title, lede, args.eyebrow, date_human, args.date)
    _add_to_homepage(slug, title, lede, args.eyebrow, args.date)
    _add_to_guard(f"/writing/{slug}/")
    print("\nNow run: bash tests/seo-scan.sh")


def _add_to_sitemap(url: str, date: str):
    p = ROOT / "sitemap.xml"
    s = p.read_text(encoding="utf-8")
    if f"<loc>{url}</loc>" in s:
        print("sitemap: already listed"); return
    entry = (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{date}</lastmod>\n"
             f"    <changefreq>yearly</changefreq>\n    <priority>0.7</priority>\n  </url>\n")
    p.write_text(s.replace("</urlset>", entry + "</urlset>"), encoding="utf-8")
    print("sitemap: added")


def _add_to_hub(slug, title, lede, eyebrow, date_human, date):
    p = ROOT / "writing" / "index.html"
    s = p.read_text(encoding="utf-8")
    href = f"/writing/{slug}/"
    if href in s:
        print("hub: already linked"); return
    card = (f'        <li>\n'
            f'          <p class="meta">{date_human} · {html.escape(eyebrow)}</p>\n'
            f'          <h2><a href="{href}">{html.escape(title)}</a></h2>\n'
            f'          <p>{inline(lede[:260])}</p>\n'
            f'        </li>\n')
    s = s.replace('      <ul class="post-list">\n', '      <ul class="post-list">\n' + card, 1)
    # keep the Blog node's blogPost list in sync
    node = (f'          {{\n'
            f'            "@type": "BlogPosting",\n'
            f'            "@id": "{BASE}/writing/{slug}/#article",\n'
            f'            "headline": {json.dumps(title, ensure_ascii=False)},\n'
            f'            "url": "{BASE}/writing/{slug}/",\n'
            f'            "datePublished": "{date}",\n'
            f'            "author": {{ "@id": "{PERSON_ID}" }}\n'
            f'          }},\n')
    s = s.replace('        "blogPost": [\n', '        "blogPost": [\n' + node, 1)
    p.write_text(s, encoding="utf-8")
    print("hub: added (card + blogPost node)")


def _add_to_homepage(slug, title, lede, eyebrow, date):
    p = ROOT / "index.html"
    s = p.read_text(encoding="utf-8")
    href = f"/writing/{slug}/"
    if href in s:
        print("homepage: already linked"); return
    y, m, d = date.split("-")
    short = f"{int(d)} {MONTHS[int(m)-1][:3]} {y}"
    card = (f'        <div class="venture">\n'
            f'          <div class="meta">{short} · {html.escape(eyebrow)}</div>\n'
            f'          <h3><a href="{href}">{html.escape(title)}</a></h3>\n'
            f'          <p>{inline(lede[:200])}</p>\n'
            f'        </div>\n')
    anchor = '    <section class="block" id="writing">'
    idx = s.find(anchor)
    if idx == -1:
        print("homepage: writing section not found — add the card by hand"); return
    grid = s.find('<div class="ventures">', idx)
    insert = s.find("\n", grid) + 1
    s = s[:insert] + card + s[insert:]
    p.write_text(s, encoding="utf-8")
    print("homepage: added")


def _add_to_guard(path: str):
    p = ROOT / "tests" / "seo-scan.sh"
    s = p.read_text(encoding="utf-8")
    if f'"{path}"' in s:
        print("guard: already declared"); return
    s = s.replace('  "/writing/"\n', f'  "/writing/"\n  "{path}"\n', 1)
    p.write_text(s, encoding="utf-8")
    print("guard: PAGES updated")


if __name__ == "__main__":
    main()
