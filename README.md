# claytoncamera.com

The canonical **person entity** site for Clayton Camera — technical founder, Orlando FL.

Static site, GitHub Pages from `main` root (`CNAME` → `claytoncamera.com`).
Deploy = push to `main`.

## Why this domain exists

The exact string "Clayton Camera" is an ambiguous search query: it collides with traffic and
weather cameras in the towns of Clayton (NY / NC / CA) and with unrelated photography businesses.
Measured non-personalized on 2026-07-24, **nothing of Clayton's ranked for his own name.**

Beating that is entity disambiguation, not keyword SEO. An exact-match personal domain is the
strongest available signal, so this site is the canonical home of the person entity and every
other property points at it.

## ⚠️ The entity `@id` is load-bearing

This page owns:

```
https://claytoncamera.com/#person
```

That id is referenced from **four files across four repos**:

| Repo | File |
|---|---|
| `claytoncamera/claytoncamera.com` | `index.html` (owner) |
| `claytoncamera/loopholemaxing` | `index.html` |
| `claytoncamera/loopholemaxing` | `clayton-camera/index.html` (redirect stub) |
| `claytoncamera/workwithclayton` | `index.html` |

**Never mint a second Person `@id`.** A split id turns one person into several unrelated mentions
and discards every signal pointing here. If the id ever changes, change all four in one commit.

`loopholemaxing/tests/seo-scan.sh` enforces the single-id rule **inside the loopholemaxing repo
only** — this repo and workwithclayton are not covered by it, so check them by hand.

## Maintenance

- New page → add a `<url>` entry to `sitemap.xml`.
- Keep the name / role / location strings identical to those in the brain runbook
  (`01_projects/personal-brand/NAME_SERP_RUNBOOK.md`). Consistency across citations *is* the
  entity-merging signal; varied phrasing prevents the merge.
- Claims on this page must stay falsifiable — same honesty rule as the rest of the network.
