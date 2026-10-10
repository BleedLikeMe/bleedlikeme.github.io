#!/bin/sh
# Build rainbow.html from rainbow.tex. Needs Pandoc >= 3 (citeproc + figures);
# set PANDOC=/path/to/pandoc if the system one is older. Run from this directory.
set -e
PANDOC=${PANDOC:-pandoc}
TMP=$(mktemp --suffix=.tex)
trap 'rm -f "$TMP"' EXIT
# Pandoc can't read tabularx, and doesn't expand \dg/\sh inside $...$.
python3 - rainbow.tex > "$TMP" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
s = re.sub(r'\\begin\{tabularx\}\{\\linewidth\}\{(.*)\}',
           lambda m: '\\begin{tabular}{' + m.group(1).replace(' L@', ' l@') + '}', s)
s = s.replace('\\end{tabularx}', '\\end{tabular}')
s = re.sub(r'(?<!\\)\$[^$]+\$',
           lambda m: m.group(0).replace('\\dg', '^\\circ').replace('\\sh', '\\sharp'), s)
sys.stdout.write(s)
PY
for f in fig_scan fig_sources; do pdftocairo -svg $f.pdf $f.svg; done
"$PANDOC" "$TMP" -s --mathjax --citeproc --bibliography=refs.bib --number-sections \
  --lua-filter=html_filter.lua --css=rainbow.css \
  -M title="Can We Sing a Rainbow?" \
  -M subtitle="On the Absence of Radio Rainbows and the Sonification of the Optical One" \
  -M author="Derek Reid" -M date="October 2026" -M lang=en-GB -M link-citations=true \
  -o rainbow.html
echo "wrote rainbow.html"
