# frarent.github.io

Personal academic website, served by GitHub Pages at <https://frarent.github.io>.
Built with Jekyll from the `master` branch: a single layout, one stylesheet, a dark theme,
system fonts and no JavaScript.

## Where content lives

| What | File |
|------|------|
| Bio text | `_pages/about.md` |
| Current and previous positions, education | `_data/positions.yml` (move ended roles to `previous` rather than deleting them) |
| Selected publications, working papers | `_data/publications.yml` (edited by hand) |
| Current work (papers in preparation) | `_data/current_work.json` (generated) |
| Bibliographic snapshot used to flag new papers | `_data/openalex.json` (generated) |
| CV shown on `/cv/` | `files/CV_Rentocchini.pdf`, with its date in `_data/cv.json` (generated) |
| Site title, sidebar, profile links, e-mail | `_config.yml` (`author`, `links`) |
| Navigation | `_data/navigation.yml` |
| Colours and layout | `assets/css/site.css`, `_layouts/default.html` |

Files marked *generated* are written by `scripts/update_site.py`; edit their sources, not the files.

## Workflow

```bash
python3 scripts/update_site.py   # refresh generated data and the CV; writes UPDATE_REPORT.md (not committed)
scripts/preview.sh               # local preview at http://127.0.0.1:4000
scripts/publish.sh               # shows the changes, asks for confirmation, commits and pushes
```

`update_site.py` does three things:

1. **Publications check.** Queries the [OpenAlex](https://openalex.org/) API by author ID and reports
   new journal articles, and working papers that appear to have been published.
2. **CV sync.** Copies the latest compiled CV into `files/`.
3. **Current work.** Reads the title and authors of the newest paper draft in each selected project
   folder.

The settings for steps 2 and 3 (where the CV and the project folders live, and which projects to
include) are local, machine-specific configuration and are not part of this repository. The script
can be scheduled (cron, launchd or similar). It only updates the working copy and never commits or
pushes, so every change is previewed before it goes online.

## Requirements

- Ruby 3.x with Bundler, for the local preview (`bundle install` installs the GitHub Pages gem set)
- Python 3, standard library only, for `update_site.py`
- Optional: an OpenAlex API key in the `OPENALEX_API_KEY` environment variable
