#!/usr/bin/env bash
# tests/seo-scan.sh — guards the entity wiring this domain OWNS.
#
# WHY THIS EXISTS
# ---------------
# The exact string "Clayton Camera" collides with traffic/weather cams in
# three towns named Clayton. Ranking for it needs an *entity*, not keywords:
# one stable Person @id, defined here exactly once and referenced identically
# from loopholemaxing.com, workwithclayton.com, orbitroute.ai and knockfiber.com.
#
# This repo is the DEFINITION site. A second Person @id — or a second page
# whose <h1> is the name — splits one person into several weakly-evidenced
# strangers and throws away every signal pointing here. None of that errors
# at runtime, so it rots silently. These assertions make rot a CI failure.
#
# Static-only: no network, no browser. Safe to run anywhere.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAILED=0
fail() { echo "  ❌ $1"; FAILED=1; }
ok()   { echo "  ✅ $1"; }

PERSON_ID="https://claytoncamera.com/#person"
DOMAIN="https://claytoncamera.com"

# Every public page in the site, as sitemap paths. Add new pages here AND
# to sitemap.xml — the two are cross-checked in both directions below.
PAGES=(
  "/"
  "/writing/"
  "/writing/dry-run-caught-25-fake-reply-threads/"
  "/writing/entity-seo-when-your-name-is-a-thing/"
)

# ── 1. CNAME, robots.txt and the verification file ──────────────────────
echo "-- domain plumbing --"
[ -f CNAME ] && grep -q "^claytoncamera.com" CNAME \
  && ok "CNAME points at claytoncamera.com" \
  || fail "CNAME missing or wrong — GitHub Pages will drop the custom domain"

if [ ! -f robots.txt ]; then
  fail "robots.txt missing"
elif ! grep -q "^Sitemap: ${DOMAIN}/sitemap.xml" robots.txt; then
  fail "robots.txt does not advertise ${DOMAIN}/sitemap.xml"
else
  ok "robots.txt advertises the sitemap"
fi

[ -f sitemap.xml ] && ok "sitemap.xml exists" \
  || fail "sitemap.xml missing — robots.txt points at a 404"

# One verification token per Google account, shared by all three properties.
# Deleting it un-verifies the property in Search Console and silently cuts
# off indexing data.
ls google*.html >/dev/null 2>&1 \
  && ok "Search Console verification file present" \
  || fail "google*.html verification file is GONE — this un-verifies Search Console"

# ── 2. sitemap ↔ filesystem agreement, both directions ──────────────────
echo "-- sitemap coverage --"
for p in "${PAGES[@]}"; do
  grep -q "<loc>${DOMAIN}${p}</loc>" sitemap.xml 2>/dev/null \
    && ok "sitemap lists ${p}" \
    || fail "sitemap is MISSING ${p}"

  f=".${p}index.html"
  [ -f "$f" ] && ok "page exists on disk: ${p}" \
    || fail "sitemap lists ${p} but ${f} does not exist"
done

# Any index.html on disk that is not a declared page is an undeclared
# surface — either add it to PAGES + sitemap.xml, or it should not be here.
while IFS= read -r f; do
  path="/${f#./}"; path="${path%index.html}"
  declared=0
  for p in "${PAGES[@]}"; do [ "$p" = "$path" ] && declared=1; done
  [ "$declared" = 1 ] || fail "undeclared page on disk: ${path} (add to PAGES + sitemap.xml)"
done < <(find . -name index.html -not -path "./.git/*")

# ── 3. exactly ONE Person definition, tree-wide ─────────────────────────
# References ("author": {"@id": ...}) are expected everywhere; a second
# *definition* is the failure. This must PARSE the JSON-LD rather than grep
# it — /writing/ quotes schema properties inside <code> blocks as examples,
# and a text search cannot tell prose about an entity from an entity.
echo "-- one entity, one id --"
python3 - <<'PY' || FAILED=1
import json, re, sys, pathlib

PERSON_ID = "https://claytoncamera.com/#person"
# A node is a DEFINITION (not a reference) if it carries identity payload
# beyond the pointer itself.
DEFINING = {"disambiguatingDescription", "givenName", "familyName", "image",
            "knowsAbout", "address", "sameAs", "description"}

defs, refs, strays, bad = [], 0, set(), 0

def walk(node, where):
    global refs
    if isinstance(node, list):
        for n in node:
            walk(n, where)
    elif isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        nid = node.get("@id", "")
        if "Person" in types or (nid.endswith("#person") and "@type" not in node):
            if nid.endswith("#person") and nid != PERSON_ID:
                strays.add(f"{where}: {nid}")
            if DEFINING & set(node):
                defs.append(where)
            else:
                refs += 1
        for v in node.values():
            walk(v, where)

for f in sorted(pathlib.Path('.').rglob('*.html')):
    if '.git' in f.parts:
        continue
    html = f.read_text(encoding='utf-8', errors='replace')
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            walk(json.loads(block), str(f))
        except Exception:
            pass  # section 5 reports parse failures

if len(defs) == 1 and defs[0] == "index.html":
    print(f"  ✅ exactly one Person definition, on the homepage ({refs} references)")
elif len(defs) != 1:
    print(f"  ❌ expected 1 Person definition, found {len(defs)}: {defs} — the entity is split")
    bad = 1
else:
    print(f"  ❌ the Person is defined in {defs[0]}, not index.html")
    bad = 1

if strays:
    print(f"  ❌ non-canonical Person @id: {sorted(strays)}")
    bad = 1
else:
    print(f"  ✅ every #person reference uses {PERSON_ID}")
sys.exit(bad)
PY

# ── 4. the homepage IS the name ─────────────────────────────────────────
echo "-- entity page shape --"
grep -q "<title>Clayton Camera" index.html \
  && ok "title starts with the name" || fail "homepage <title> must start with 'Clayton Camera'"
grep -q "<h1>Clayton Camera</h1>" index.html \
  && ok "h1 is exactly the name" || fail "homepage <h1> must be exactly 'Clayton Camera'"
grep -q "<link rel=\"canonical\" href=\"${DOMAIN}/\">" index.html \
  && ok "homepage self-canonicalises" || fail "homepage canonical is missing or wrong"
grep -q '"@type": "FAQPage"' index.html \
  && ok "FAQPage present" || fail "FAQPage block missing — it answers the literal name query"

# Only ONE page may claim the bare name as its h1. Two pages competing for
# the same query is the duplicate canonicalisation exists to prevent.
h1s=$(grep -rl "<h1>Clayton Camera</h1>" --include="*.html" . | grep -v "^./.git" | wc -l | tr -d ' ')
[ "$h1s" = "1" ] && ok "only one page claims the bare name as h1" \
  || fail "${h1s} pages use '<h1>Clayton Camera</h1>' — they compete with each other"

# ── 5. every page canonicalises to itself and parses ────────────────────
echo "-- per-page canonical + JSON-LD --"
for p in "${PAGES[@]}"; do
  f=".${p}index.html"
  [ -f "$f" ] || continue
  grep -q "<link rel=\"canonical\" href=\"${DOMAIN}${p}\">" "$f" \
    && ok "canonical ok: ${p}" || fail "canonical missing/wrong on ${p}"
done

python3 - <<'PY' || FAILED=1
import json, re, sys, pathlib
bad = 0
for f in sorted(pathlib.Path('.').rglob('*.html')):
    if '.git' in f.parts:
        continue
    html = f.read_text(encoding='utf-8', errors='replace')
    for i, block in enumerate(re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S)):
        try:
            json.loads(block)
        except Exception as e:
            print(f"  ❌ JSON-LD block {i} in {f} does not parse: {e}")
            bad = 1
print("  ✅ all JSON-LD blocks parse" if not bad else "")
sys.exit(bad)
PY

# ── 6. no orphans ───────────────────────────────────────────────────────
# A post reachable only from the sitemap is a post with no internal links.
echo "-- internal linking --"
grep -q 'href="/writing/"' index.html \
  && ok "homepage links the writing hub" || fail "homepage does not link /writing/"
for p in "${PAGES[@]}"; do
  case "$p" in /|/writing/) continue;; esac
  grep -q "href=\"${p}\"" writing/index.html \
    && ok "writing hub links ${p}" || fail "${p} is an orphan — not linked from /writing/"
done

echo
if [ "$FAILED" = "0" ]; then
  echo "ALL CHECKS PASSED"
else
  echo "SEO SCAN FAILED"
fi
exit "$FAILED"
