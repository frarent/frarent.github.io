#!/usr/bin/env python3
"""
update_site.py — refresh the website's generated content. Never commits or pushes.

  1. Publications: query OpenAlex by author ID (not ORCID), check identity,
     keep journal articles, merge duplicates, write _data/openalex.json.
  2. CV: copy the latest compiled CV into the site (recompiling into a temp
     folder first if the .tex is newer than the .pdf).
  3. Current work: title and authors from the newest draft in each selected
     project folder, written to _data/current_work.json.
  4. Report: write UPDATE_REPORT.md listing what changed and what needs a
     human decision (new articles, working papers that look published, new drafts).

All personal settings (author IDs, CV location, project folders) are read from a
local JSON config outside the repository: ~/.config/site-update/config.json, or the
path in $SITE_UPDATE_CONFIG. See scripts/config.example.json for its structure.

Run:  python3 scripts/update_site.py            (from anywhere; --weekly adds a desktop notification)
Then: scripts/preview.sh  →  check  →  scripts/publish.sh
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# =============================================================================
# 0. Settings — edit here
# =============================================================================
SITE = Path(__file__).resolve().parent.parent
OUT_JSON = SITE / "_data" / "openalex.json"
CURATED = SITE / "_data" / "publications.yml"
REPORT = SITE / "UPDATE_REPORT.md"

CONFIG_FILE = Path(os.environ.get("SITE_UPDATE_CONFIG",
                                  Path.home() / ".config" / "site-update" / "config.json")).expanduser()
CFG = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}

# Surname that must appear on a work or draft for it to count as yours (identity check).
SURNAME = CFG.get("author_surname", "")

# OpenAlex: query by author profile ID (more reliable than ORCID when profiles are split or mixed up).
OA = CFG.get("openalex", {})
OWN_AUTHOR_IDS = OA.get("author_ids", [])
EXTRA_WORK_IDS = OA.get("extra_work_ids", [])        # your works filed under someone else's profile
EXCLUDE_WORK_IDS = set(OA.get("exclude_work_ids", []))
JOURNAL_FIXES = OA.get("journal_fixes", {})          # wrong journal names in OpenAlex -> correct name
MIN_WORKS = OA.get("min_works", 1)                   # fewer works than this = broken query, not a shrunken record

# Work types that count as journal articles.
ARTICLE_TYPES = {"article", "review", "editorial", "letter"}

# CV: the PDF shown on the CV page is copied from here (the CV source folder is never modified).
CV_CFG = CFG.get("cv", {})
CV_DIR = Path(CV_CFG["source_dir"]).expanduser() if CV_CFG.get("source_dir") else None
CV_NAME = CV_CFG.get("name", "CV")
CV_TARGET = SITE / CV_CFG.get("target", "files/CV.pdf")
CV_META = SITE / "_data" / "cv.json"

# Current work: which project folders feed it.
CW = CFG.get("current_work", {})
CW_JSON = SITE / "_data" / "current_work.json"
NOT_PAPER_PROJECTS = set(CW.get("skip_projects", []))   # folders that never hold a paper draft


# =============================================================================
# 1. OpenAlex helpers
# =============================================================================
def api_key():
    """Key from $OPENALEX_API_KEY, else from the file named in the config (schedulers often skip the shell profile)."""
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if not key and OA.get("api_key_file"):
        f = Path(OA["api_key_file"]).expanduser()
        if f.exists():
            key = f.read_text().strip()
    return key


def fetch_all(filter_str):
    """Return every work matching an OpenAlex filter, following cursor pagination."""
    results, cursor = [], "*"
    while cursor:
        params = {"filter": filter_str, "per-page": "200", "cursor": cursor}
        key = api_key()
        if key:
            params["api_key"] = key
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params, safe=":|")
        with urllib.request.urlopen(url, timeout=60) as r:
            page = json.load(r)
        results += page["results"]
        cursor = page["meta"].get("next_cursor") if page["results"] else None
    return results


def short_id(openalex_url):
    return (openalex_url or "").rsplit("/", 1)[-1]


def bare_doi(doi):
    return doi.lower().replace("https://doi.org/", "") if doi else None


def norm_title(t):
    """Lower-case, letters and digits only: used to match versions of the same paper."""
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def is_mine(work, extra):
    """Identity check: the configured surname must appear on the work."""
    for a in work.get("authorships", []):
        name = (a.get("author") or {}).get("display_name") or ""
        raw = a.get("raw_author_name") or ""
        if extra:
            # Works filed under another profile: check the raw name printed on the paper.
            if SURNAME.lower() in raw.lower():
                return True
        elif short_id((a.get("author") or {}).get("id")) in OWN_AUTHOR_IDS and SURNAME.lower() in name.lower():
            return True
    return False


def h_index(cites):
    cites = sorted(cites, reverse=True)
    return sum(1 for i, c in enumerate(cites, start=1) if c >= i)


# =============================================================================
# 2. Build the publication data
# =============================================================================
def build_publications():
    own = fetch_all("author.id:" + "|".join(OWN_AUTHOR_IDS))
    extra = fetch_all("openalex:" + "|".join(EXTRA_WORK_IDS)) if EXTRA_WORK_IDS else []

    # 2a. Identity check; drop anything that fails and report it.
    works, rejected = {}, []
    for w, is_extra in [(w, False) for w in own] + [(w, True) for w in extra]:
        if is_mine(w, is_extra):
            works[short_id(w["id"])] = w
        else:
            rejected.append(w.get("title"))
    if len(works) < MIN_WORKS:   # guard: an empty or tiny result means the query broke, not that the record shrank
        sys.exit(f"STOP: only {len(works)} works passed the identity check — not overwriting {OUT_JSON.name}")

    # 2b. Totals over every work (all versions), as in the corrected CLAUDE.md metrics.
    all_cites = [w["cited_by_count"] for w in works.values()]

    # 2c. Journal articles only, one entry per paper.
    articles = {}
    for wid, w in works.items():
        src = (w.get("primary_location") or {}).get("source") or {}
        if wid in EXCLUDE_WORK_IDS or w.get("type") not in ARTICLE_TYPES or src.get("type") != "journal":
            continue
        b = w.get("biblio") or {}
        fp, lp = b.get("first_page"), b.get("last_page")
        pages = fp if (fp and (not lp or lp == fp)) else (f"{fp}–{lp}" if fp else None)
        vol = b.get("volume")
        if vol and b.get("issue"):
            vol = f"{vol}({b['issue']})"
        rec = {
            "id": wid,
            "title": (w.get("title") or "").strip(),
            "authors": ", ".join((a.get("raw_author_name") or a["author"]["display_name"]).strip()
                                 for a in w["authorships"]),
            "year": w.get("publication_year"),
            "journal": JOURNAL_FIXES.get(src.get("display_name"), src.get("display_name")),
            "volume": vol,
            "pages": pages,
            "doi": bare_doi(w.get("doi")),
            "citations": w["cited_by_count"],
        }
        key = rec["doi"] or norm_title(rec["title"])
        tkey = norm_title(rec["title"])
        # merge with an existing entry that has the same DOI or the same title
        dup = next((k for k, r in articles.items() if k == key or norm_title(r["title"]) == tkey), None)
        if dup is None or rec["citations"] > articles[dup]["citations"]:
            if dup is not None:
                del articles[dup]
            articles[key] = rec

    arts = sorted(articles.values(), key=lambda r: (-(r["year"] or 0), r["title"].lower()))

    # 2d. Citation lookup by DOI for the curated "selected" list.
    by_doi = {}
    for w in works.values():
        d = bare_doi(w.get("doi"))
        if d:
            by_doi[d] = max(by_doi.get(d, 0), w["cited_by_count"])

    data = {
        "updated": date.today().isoformat(),
        "source": "OpenAlex",
        "metrics": {"works": len(works), "n_articles": len(arts),
                    "citations": sum(all_cites), "h_index": h_index(all_cites)},
        "citations_by_doi": by_doi,
        "articles": arts,
    }
    return data, rejected


# =============================================================================
# 3. CV sync
# =============================================================================
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def sync_cv():
    if CV_DIR is None:
        return "No CV source configured — CV not updated."
    tex, pdf = CV_DIR / f"{CV_NAME}.tex", CV_DIR / f"{CV_NAME}.pdf"
    if not tex.exists() and not pdf.exists():
        return "CV source folder not reachable — CV not updated."
    source, note = pdf, ""
    # 120 s tolerance: a .tex saved together with its PDF is not an "edit since the last compile",
    # and recompiling would stamp an unchanged CV with today's date (the CV prints \today).
    if tex.exists() and (not pdf.exists() or tex.stat().st_mtime > pdf.stat().st_mtime + 120):
        # .tex edited since the last compile: compile into a temp folder, never into the CV project.
        tmp = Path(tempfile.mkdtemp(prefix="cvbuild_"))
        for _ in range(2):
            # fallback for schedulers whose PATH lacks the TeX binaries (default MacTeX location)
            pdflatex = shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"
            subprocess.run([pdflatex, "-interaction=nonstopmode", f"-output-directory={tmp}", tex.name],
                           cwd=CV_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        built = tmp / f"{CV_NAME}.pdf"
        if built.exists():
            source, note = built, " (recompiled from the newer .tex)"
        else:
            note = " — WARNING: .tex is newer than .pdf but recompiling failed; used the existing PDF"
    unchanged = sha(source) == sha(CV_TARGET)
    if unchanged and CV_META.exists():
        return "CV unchanged."
    if not unchanged:
        CV_TARGET.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, CV_TARGET)
    # Record the CV's own date for the CV page (file dates are lost when GitHub Pages checks out the repo).
    cv_date = date.fromtimestamp(source.stat().st_mtime).isoformat()
    CV_META.write_text(json.dumps({"date": cv_date}, indent=1) + "\n")
    return f"CV {'date recorded' if unchanged else 'updated'} from {source.name} (dated {cv_date}){note}."


# =============================================================================
# 3b. Current work — titles and authors read from drafts in the project repositories
# =============================================================================
def braced(s, start):
    """Text inside the {...} group that opens at or after `start` (handles nested braces)."""
    i = s.find("{", start)
    if i < 0:
        return "", start
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j], j + 1
    return s[i + 1:], len(s)


def strip_cmd(s, cmd):
    """Remove every \\cmd{...} including its (nested) argument, e.g. \\thanks{...}."""
    while (k := s.find("\\" + cmd)) >= 0:
        _, end = braced(s, k)
        s = s[:k] + s[end:]
    return s


ACCENTS = {"\\'e": "é", "\\'a": "á", "\\'i": "í", "\\'o": "ó", "\\`a": "à", "\\`e": "è", "\\`o": "ò",
           '\\"o': "ö", '\\"u': "ü", "\\c{c}": "ç", "\\c c": "ç", "\\~n": "ñ"}


def clean_tex(s):
    """LaTeX fragment -> plain text."""
    for k, v in ACCENTS.items():
        s = s.replace(k, v)
        if len(k) == 3:                                   # also the braced form, e.g. \'{e}
            s = s.replace(f"{k[:2]}{{{k[2]}}}", v)
    s = s.replace("\\&", "&").replace("~", " ")
    s = re.sub(r"\\\\(\[[^\]]*\])?", " ", s)                        # line breaks \\ and \\[2pt]
    s = re.sub(r"\\(textbf|textit|emph|textsc|mbox)\s*\{", "{", s)  # keep the argument
    s = re.sub(r"\\(bf|it|large|Large|LARGE|huge|small|normalsize|centering|vspace\{[^}]*\})\b", "", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", "", s)                # any other command
    s = re.sub(r"[{}$]", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,;")


def parse_tex_draft(txt):
    """(title, [authors]) from a LaTeX draft; authors from \\author[..]{..} blocks or 'A \\and B'."""
    k = re.search(r"\\title\s*(\[[^\]]*\])?\s*\{", txt)
    title = clean_tex(braced(txt, k.start())[0]) if k else ""
    authors, pos = [], 0
    while (m := re.compile(r"\\author\s*(\[[^\]]*\])?\s*\{").search(txt, pos)):
        body, pos = braced(txt, m.start())
        body = strip_cmd(body, "thanks")
        authors += [clean_tex(a) for a in re.split(r"\\and\b|,(?![^{]*\})", body) if clean_tex(a)]
    return title, authors


def parse_md_draft(txt):
    """(title, [authors]) from a Markdown draft: '# ' headings = title, '### ' headings = authors."""
    head = txt.split("```", 1)[0]
    sym = "∗†‡§¶*"
    title = " ".join(l[2:].strip().strip(sym) for l in head.splitlines() if l.startswith("# "))
    authors = [l[4:].strip().strip(sym) for l in head.splitlines() if l.startswith("### ")]
    return re.sub(r":\s+", ": ", title).strip(), authors


def newest_draft(proj_dir, patterns, require_fr=True):
    """Newest file matching the globs that has a title (and names SURNAME, unless require_fr=False)."""
    cands = []
    for pat in patterns:
        for p in proj_dir.glob(pat):
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if require_fr and SURNAME not in txt:
                continue
            title, authors = parse_md_draft(txt) if p.suffix == ".md" else parse_tex_draft(txt)
            if title:
                cands.append(((date.fromtimestamp(p.stat().st_mtime), p.name), p, title, authors))
    return max(cands, key=lambda c: c[0])[1:] if cands else None


def unlisted_drafts(root, listed):
    """Project folders not in the config that contain a LaTeX draft naming SURNAME (for the report)."""
    found = []
    for proj in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        if proj.name in listed or proj.name in NOT_PAPER_PROJECTS:
            continue
        for p in list(proj.glob("writing/*.tex")) + list(proj.glob("writing/*/*.tex")):
            txt = p.read_text(encoding="utf-8", errors="ignore")[:30000]
            if "\\begin{document}" in txt and "\\title" in txt and SURNAME in txt:
                found.append(f"{proj.name}/{p.relative_to(proj)}")
                break
    return found


def build_current_work():
    if not CW.get("projects_root"):
        return None, ["No current_work settings in the config — Current work not updated"]
    cfg = CW
    root = Path(cfg["projects_root"]).expanduser()
    if not root.is_dir():
        return None, ["projects folder not reachable — Current work not updated"]
    papers, notes = [], []
    for e in cfg["projects"]:
        if not e.get("include"):
            continue
        add = e.get("authors_add", [])            # co-authors the drafts do not list yet
        hit = newest_draft(root / e["project"], e.get("drafts", []), require_fr=not add)
        if not hit and not (e.get("title") and e.get("authors")):
            notes.append(f"{e['project']}: no draft found for {e.get('drafts')} — kept off the page")
            continue
        path, title, authors = hit or (None, "", [])
        authors = [cfg.get("name_fixes", {}).get(a, a) for a in authors]
        for a in add:
            if a in authors:
                continue
            surnames = [n.split()[-1] for n in authors]
            if authors and surnames == sorted(surnames):   # alphabetical list: keep it alphabetical
                authors.insert(sum(s < a.split()[-1] for s in surnames), a)
            else:
                authors.append(a)
        papers.append({"project": e["project"],
                       "title": e.get("title") or title,
                       "authors": e.get("authors") or ", ".join(authors),
                       "status": e.get("status", "in preparation"),
                       "draft": str(path.relative_to(root)) if path else "manual entry"})
    new = unlisted_drafts(root, {e["project"] for e in cfg["projects"]})
    notes += [f"NEW draft not yet classified: {d} — add it to scripts/current_work_sources.json" for d in new]
    return {"updated": date.today().isoformat(), "papers": papers}, notes


# =============================================================================
# 4. Report and main
# =============================================================================
def curated_titles_and_dois():
    """Read titles/DOIs from publications.yml with a regex (no PyYAML needed)."""
    txt = CURATED.read_text(encoding="utf-8")
    dois = {d.lower() for d in re.findall(r'^\s*doi:\s*"([^"]+)"', txt, re.M) if d}
    wps = txt.split("working_papers:", 1)[-1]
    wp_titles = re.findall(r'^\s*title:\s*"([^"]+)"', wps, re.M)
    return dois, wp_titles


def main():
    old = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {"articles": [], "metrics": {}}
    data, rejected = build_publications()
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cv_msg = sync_cv()
    old_cw = json.loads(CW_JSON.read_text()) if CW_JSON.exists() else {"papers": []}
    cw, cw_notes = build_current_work()
    if cw is not None:
        public = {"updated": cw["updated"],
                  "papers": [{k: p[k] for k in ("title", "authors", "status")} for p in cw["papers"]]}
        CW_JSON.write_text(json.dumps(public, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    old_ids = {a["id"] for a in old["articles"]}
    new_arts = [a for a in data["articles"] if a["id"] not in old_ids] if old_ids else []
    sel_dois, wp_titles = curated_titles_and_dois()
    wp_titles += [p["title"] for p in (cw or {}).get("papers", [])]   # a draft that got published is flagged too
    art_titles = {norm_title(a["title"]): a for a in data["articles"]}
    published_wps = [(t, art_titles[norm_title(t)]) for t in wp_titles if norm_title(t) in art_titles]
    recent_unselected = [a for a in data["articles"]
                         if (a["year"] or 0) >= date.today().year - 1 and (a["doi"] or "") not in sel_dois]

    m, om = data["metrics"], old.get("metrics", {})
    lines = [f"# Website update report — {data['updated']}", "",
             f"- OpenAlex: {m['works']} works, {m['n_articles']} journal articles, "
             f"{m['citations']} citations (was {om.get('citations', 'n/a')}), h-index {m['h_index']}.",
             f"- {cv_msg}", ""]
    if new_arts:
        lines += ["## New journal articles since the last update", ""]
        lines += [f"- {a['year']} — {a['title']} — *{a['journal']}* (doi {a['doi']})" for a in new_arts] + [""]
    if published_wps:
        lines += ["## Working papers that now look published (move them to `selected` or delete)", ""]
        lines += [f"- {t} → *{a['journal']}* {a['year']}" for t, a in published_wps] + [""]
    if recent_unselected:
        lines += ["## Recent articles not in the selected list (add to `_data/publications.yml` if relevant)", ""]
        lines += [f"- {a['year']} — {a['title']} — *{a['journal']}*" for a in recent_unselected] + [""]
    if cw is not None:
        old_t = {(p["title"], p["authors"]) for p in old_cw["papers"]}
        lines += ["## Current work (from project drafts)", ""]
        lines += [f"- {'**changed** ' if (p['title'], p['authors']) not in old_t else ''}{p['title']} — "
                  f"{p['authors']} (`{p['draft']}`)" for p in cw["papers"]] + [""]
    if cw_notes:
        lines += [f"- {n}" for n in cw_notes] + [""]
    if rejected:
        lines += ["## Works dropped by the identity check", ""] + [f"- {t}" for t in rejected] + [""]
    lines += ["Next: `scripts/preview.sh` to check locally, then `scripts/publish.sh` to put it online."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def notify_if_changed():
    """--weekly: desktop notification (macOS) when the working copy changed. Never commits."""
    changed = subprocess.run(["git", "status", "--porcelain", "--", "_data/openalex.json", "_data/cv.json",
                              "_data/current_work.json", str(CV_TARGET.relative_to(SITE))],
                             cwd=SITE, capture_output=True, text=True).stdout.strip()
    if changed and shutil.which("osascript"):          # macOS only; elsewhere read UPDATE_REPORT.md
        rep = REPORT.read_text(encoding="utf-8")
        msg = ("New publication(s) found on OpenAlex" if "## New journal articles" in rep else
               "New paper draft found" if "NEW draft" in rep else "Website data refreshed")
        subprocess.run(["osascript", "-e", f'display notification "{msg} — see UPDATE_REPORT.md, then run preview.sh" '
                                           f'with title "{SITE.name}"'])


if __name__ == "__main__":
    if not CFG:
        sys.exit(f"No config found at {CONFIG_FILE} — copy scripts/config.example.json there and fill it in.")
    print(f"== {date.today()} website update")
    main()
    if "--weekly" in sys.argv:
        notify_if_changed()
