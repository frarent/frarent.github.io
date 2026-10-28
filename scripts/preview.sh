#!/bin/bash
# =============================================================================
# preview.sh — serve the site locally at http://127.0.0.1:4000 before publishing.
# Edits to pages, _data/*.yml and CSS reload automatically; restart after
# editing _config.yml. Stop with Ctrl+C. Nothing goes online from here.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

# 1. Use Homebrew Ruby 3.3 (macOS system Ruby is too old for GitHub Pages' Jekyll)
export PATH="/opt/homebrew/opt/ruby@3.3/bin:$PATH"

# 2. Install gems on first run (into vendor/bundle, ignored by git)
bundle config set --local path vendor/bundle >/dev/null
bundle check >/dev/null 2>&1 || bundle install

# 3. Serve and open the browser
( sleep 4 && open "http://127.0.0.1:4000/" ) &
bundle exec jekyll serve --livereload --host 127.0.0.1 --port 4000
