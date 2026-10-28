# frarent.github.io

Personal academic website of Francesco Rentocchini — <https://frarent.github.io>.
Built by GitHub Pages (Jekyll) from the `master` branch. Dark, script-free, system fonts.

## Where content lives

| What | File |
|------|------|
| Bio text | `_pages/about.md` |
| Current / previous positions, education | `_data/positions.yml` (move ended roles to `previous`, never delete) |
| Selected publications, working papers | `_data/publications.yml` (hand-curated) |
| Current work (papers in preparation) | `_data/current_work.json` — **generated** from the newest draft in each project listed in `~/.config/frarent-site/current_work_sources.json` (local, not in this repo; set `include` true/false there) |
| OpenAlex snapshot (not shown on the site; used to detect new papers for `UPDATE_REPORT.md`) | `_data/openalex.json` — **generated**, do not edit |
| CV shown on /cv/ | `files/CV_Rentocchini.pdf` — **copied** from `/Volumes/work/projects/CV/CVs/CV_green.pdf` |
| Sidebar, links, e-mail | `_config.yml` (`author`, `links`) |
| Colours and layout | `assets/css/site.css`, `_layouts/default.html` |

## Workflow

```bash
python3 scripts/update_site.py   # refresh OpenAlex data + CV, writes UPDATE_REPORT.md
scripts/preview.sh               # local preview at http://127.0.0.1:4000
scripts/publish.sh               # asks for confirmation, commits, pushes to master
```

`scripts/update_site.py --weekly` runs every Monday at 09:30 via launchd
(`~/Library/LaunchAgents/com.user.websiteupdate.plist`; log in `~/Library/Logs/website-update.log`).
It refreshes the data and sends a notification if something changed; it never commits or pushes.
launchd calls Homebrew `python3` directly because only it holds the macOS permission to read
`/Volumes/work` (a shell wrapper is refused with "Operation not permitted").

OpenAlex is queried by author ID (five profiles) plus seven works misattributed to
Francesco Vona; never by ORCID (see the script header). The API key is read from
`$OPENALEX_API_KEY` or `~/.config/mac-ai/openalex_api_key`.
