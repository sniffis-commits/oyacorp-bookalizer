# Rambam layout PoC (Vivliostyle) — verified 5-page build

Proof of concept for a classic Rambam page layout in HTML/CSS paged media:
the central Mishneh Torah text with the Kesef Mishneh commentary hugging its
contour, Raavad floating inside the text, and the remaining commentaries
(Maaseh Rokeach, Merkevet HaMishneh, Or HaYashar, Shaarayim, Tosefot Yom Tov)
flowing into full-page commentary columns once the central text ends.

Content: Mishneh Torah, Hilkhot Tumat Met, chapter 18 (halakhot 3–5).

## Contents
- `content.html` — input: the source chapter plus commentary blocks.
- `content.ordered.html` — preprocessed input (commentary pool moved to the
  document end as one merged element; produced by `policy_contour.py`).
- `policy_contour.py` — generator: preprocessing + page-template CSS emission.
- `reproduce.py` — deterministic reproduction entry point.
- `templates/t7-contour.gen.css` — generated CSS of the verified build.
- `out/t7-contour.pdf` — the verified 5-page result.

## Environment
- Node.js with `@vivliostyle/cli` 11.5.0 (core 2.46.0):
  `npm install @vivliostyle/cli@11.5.0`
- Chrome/Chromium (the commands assume `/usr/bin/google-chrome`; adjust
  `--executable-browser` or drop it to use the bundled browser).
- `pdftotext` (poppler) — only for optional verification, not the build.

## Reproduce (two equivalent paths)

Path A — rebuild from the shipped preprocessed artifacts:
```
npx vivliostyle build content.ordered.html -d \
  --user-style templates/t7-contour.gen.css \
  -o out/t7-contour.pdf \
  --executable-browser /usr/bin/google-chrome
```
Expected: `Pages: 5`.

Path B — regenerate the preprocessed HTML + CSS, then build:
```
python3 reproduce.py
```

Note: run these from the bundle's root directory — Vivliostyle requires the
custom style file to live under the build's working directory.

## What the reproduction parameters mean
`gen_css(contours, last_km_page, lk_tail=None, km_inner_pages={1,2,3})`
- contours `{1:235.98, 2:122.80, 3..6:0}`: measured bottom (mm) of the source
  block (including the Raavad float) on each page; 0 = no source on that page.
- `last_km_page=3`: page 3 is the last page containing Kesef Mishneh text.
- `lk_tail=None`: the commentary stream does not take over the freed areas of
  the last Kesef Mishneh page (see limitations).
- `km_inner_pages={1,2,3}`: the Kesef Mishneh inner column is kept on every
  contour page.

## The disabled convergence loop
`python3 policy_contour.py` runs an automatic measure → regenerate loop. It is
currently unusable: its first pass puts commentary columns in the base page
master overlapping the other partitions, and Vivliostyle hangs. Do not run it;
`reproduce.py` hardcodes the verified measurements instead. If the loop is
revived, pass 1 needs a base master without commentary columns.

## Verified properties
- 5 pages, no content loss (every source and commentary token is present).
- Continuous reading order: page 3 bottom strip → page 4 right → center →
  left column → page 5 right → center → left column top.
- Pages 4–5 carry the remaining commentaries in dense three-column layout.

## Known limitations
- Page 2: the left (inner) column stays empty — it is reserved for Kesef
  Mishneh, which ends earlier on that page.
- Page 3: the center/left area above the bottom strip stays empty — the
  commentary stream only becomes available to the layout engine after the
  Kesef Mishneh stream's last page.
- The Maaseh Rokeach note for halakha 4 (source on page 2) appears in page
  3's bottom strip rather than directly under its source.
- Contour following is measured against the source block (incl. the Raavad
  float), not against the commentary fill level.
