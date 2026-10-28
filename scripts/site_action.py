#!/usr/bin/env python3
"""
site_action.py — act on a weekly update without a terminal (e.g. from a chat bot).

  status         what is waiting to be published
  add W1234567   add an OpenAlex article (id from UPDATE_REPORT.md) to Selected publications;
                 if it is listed under Working papers, it is removed from there
  publish        commit everything waiting and push it online (master branch only)
  discard        drop the waiting changes to generated files (restores the published version)

Run:  python3 scripts/site_action.py <command>
Same effect as scripts/publish.sh, but non-interactive: whoever calls it has already approved.
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# =============================================================================
# 0. Settings
# =============================================================================
SITE = Path(__file__).resolve().parent.parent
CURATED = SITE / "_data" / "publications.yml"
OPENALEX = SITE / "_data" / "openalex.json"
GENERATED = ["_data/openalex.json", "_data/cv.json", "_data/current_work.json", "files"]
GIT = shutil.which("git") or "/usr/bin/git"   # schedulers and bots often run with a minimal PATH
BRANCH = "master"                               # the branch GitHub Pages builds from


def git(*args, check=True):
    r = subprocess.run([GIT, *args], cwd=SITE, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.rstrip()


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


# =============================================================================
# 1. status
# =============================================================================
def status():
    changes = git("status", "--porcelain")
    if not changes:
        print("Nothing waiting: the website is up to date.")
        return
    print("Waiting to be published:")
    for line in changes.splitlines():
        print("  " + line[3:])


# =============================================================================
# 2. add — OpenAlex article -> Selected publications
# =============================================================================
def short_authors(names):
    """'Giacomo Roberto Lupi, Ugo Rizzo' -> 'Lupi, G. R., Rizzo, U.' (lower-case particles stay with the surname)."""
    out = []
    for name in [n.strip() for n in names.split(",") if n.strip()]:
        parts = name.split()
        i = len(parts) - 1
        while i > 1 and parts[i - 1][0].islower():     # van, de, di, von ...
            i -= 1
        given = " ".join(p[0] + "." for p in parts[:i])
        out.append(f"{' '.join(parts[i:])}, {given}".rstrip(", "))
    return ", ".join(out)


def add(work_id):
    arts = {a["id"]: a for a in json.loads(OPENALEX.read_text(encoding="utf-8"))["articles"]}
    a = arts.get(work_id)
    if a is None:
        sys.exit(f"{work_id} is not among the journal articles in {OPENALEX.name} — check the id in the report.")

    # 2a. Split the file into header, selected blocks and working-paper blocks (blocks are blank-line separated)
    txt = CURATED.read_text(encoding="utf-8")
    head, rest = re.split(r"^selected:\n", txt, maxsplit=1, flags=re.M)
    sel_txt, wp_txt = re.split(r"^working_papers:\n", rest, maxsplit=1, flags=re.M)
    if (a["doi"] and f'doi: "{a["doi"]}"' in sel_txt) or norm_title(a["title"]) in norm_title(sel_txt):
        sys.exit(f"Already in Selected publications: {a['title']}")

    # 2b. The new entry, in the same format as the hand-written ones
    fields = [("authors", short_authors(a["authors"])), ("year", a["year"]), ("title", a["title"]),
              ("journal", a["journal"]), ("volume", a.get("volume")), ("pages", a.get("pages")),
              ("doi", a.get("doi"))]
    entry = "\n".join(("  - " if i == 0 else "    ") + (f"{k}: {v}" if k == "year" else f'{k}: "{v}"')
                      for i, (k, v) in enumerate((k, v) for k, v in fields if v))

    sel = [b for b in sel_txt.strip("\n").split("\n\n") if b.strip()]
    wps = [b for b in wp_txt.strip("\n").split("\n\n") if b.strip()]

    # 2c. Insert newest-first: before the first selected entry from an earlier or the same year
    year_of = lambda b: int((re.search(r"^\s*year:\s*(\d{4})", b, re.M) or [0, 0])[1])
    pos = next((i for i, b in enumerate(sel) if year_of(b) <= a["year"]), len(sel))
    sel.insert(pos, entry)

    # 2d. A working paper with the same title has now been published: remove it
    title_of = lambda b: norm_title((re.search(r'^\s*-?\s*title:\s*"([^"]*)"', b, re.M) or ["", ""])[1])
    kept = [b for b in wps if title_of(b) != norm_title(a["title"])]
    moved = len(kept) < len(wps)

    CURATED.write_text(f"{head}selected:\n" + "\n\n".join(sel) + "\n\nworking_papers:\n" + "\n\n".join(kept) + "\n",
                       encoding="utf-8")
    print(f"Added to Selected publications: {a['title']} — {a['journal']} {a['year']}"
          + (" (removed from Working papers)" if moved else "") + ".\nNot online yet: run publish to put it online.")


# =============================================================================
# 3. publish / discard
# =============================================================================
def publish():
    if git("rev-parse", "--abbrev-ref", "HEAD") != BRANCH:
        sys.exit(f"The site repository is not on {BRANCH}: publish from a terminal with scripts/publish.sh.")
    if git("status", "--porcelain"):
        git("add", "-A")
        git("commit", "-q", "-m", f"Site update {date.today().isoformat()}")
    git("pull", "-q", "--rebase", "origin", BRANCH)          # picks up edits made on github.com
    if not git("rev-list", f"origin/{BRANCH}..HEAD"):
        print("Nothing to publish: the website is already up to date.")
        return
    git("push", "-q", "origin", BRANCH)
    print(f"Published ({git('rev-parse', '--short', 'HEAD')}). Live in about a minute.")


def discard():
    waiting = git("status", "--porcelain", "--", *GENERATED)
    if not waiting:
        print("No waiting changes to generated files.")
        return
    git("checkout", "--", *GENERATED)
    git("clean", "-fdq", "--", "files")
    print("Discarded the waiting changes to generated files (hand edits, if any, are kept).")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "status":
        status()
    elif cmd == "add" and len(sys.argv) == 3:
        add(sys.argv[2].strip().upper())
    elif cmd == "publish":
        publish()
    elif cmd == "discard":
        discard()
    else:
        sys.exit(__doc__)
