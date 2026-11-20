#!/usr/bin/env python3
"""Reproduce the verified 5-page Rambam PoC PDF deterministically.

This regenerates content.ordered.html (reorder + merge) and
templates/t7-contour.gen.css from policy_contour.py with the hardcoded
measurements of the verified build, then runs vivliostyle.

NOTE: policy_contour.py's main() convergence loop is DISABLED (see
REPRODUCE.md). Do not run `python3 policy_contour.py`; run this file.
"""
import subprocess, sys

code = open("policy_contour.py").read()
g = {"__name__": "pc_mod", "__file__": __file__}
exec(compile(code, "policy_contour.py", "exec"), g)

# Step 1: preprocess content.html -> content.ordered.html
# (moves the commentary pool to the document end as ONE merged element)
g["reorder_content"]()

# Step 2: emit the page-template CSS with the verified measurements:
# contours (source bottom per page, mm), last km page = 3,
# lk_tail=None (no rest takeover on the last km page),
# km_inner_pages={1,2,3} (keep the km inner column on every contour page).
css = g["gen_css"]({1: 235.98, 2: 122.80, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0},
                   3, lk_tail=None, km_inner_pages={1, 2, 3})
open("templates/t7-contour.gen.css", "w").write(css)

# Step 3: build
r = subprocess.run(["npx", "vivliostyle", "build", "content.ordered.html", "-d",
                    "--user-style", "templates/t7-contour.gen.css",
                    "-o", "out/t7-contour.pdf",
                    "--executable-browser", "/usr/bin/google-chrome"],
                   timeout=110)
sys.exit(r.returncode)
