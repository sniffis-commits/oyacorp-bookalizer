#!/usr/bin/env python3
"""Anchored-floating policy layer (bounded):
pass 1: render base geometry via vivliostyle CLI, measure Raavad anchors and
        block heights from pdftotext -bbox coordinates.
pass 2..3: generate per-page masters (source absorbs the space above the
        float; Raavad block placed beside its passage), re-render, re-measure;
        stop when anchor offsets converge (<=1mm) or after 3 passes.
Output: templates/t6-anchored.gen.css, out/t6-anchored.pdf
"""
import json, re, subprocess, sys, os

APP = "/tmp/poc/app"
MM = 25.4 / 72.0  # pt -> mm
LEFT_COL_MAX_PT = 44 / MM     # raavad column: left 13mm..44mm
CENTER_MIN_PT, CENTER_MAX_PT = 48 / MM, 162 / MM

# source-passage first words per anchored halacha (RTL reversed in pdftotext)
ANCHOR_WORD = {"h4": "רונת", "h5": "לדגמ"}

BASE_HEAD = """@page { size: A4; margin: 0; }
@-epubx-page-template {
  @-epubx-flow raavad { -epubx-flow-consume: all; }
  @-epubx-flow km     { -epubx-flow-consume: all; }
  .comm.raavad { -epubx-flow-into: raavad; -epubx-flow-linger: 99; }
  .comm.km, .comm.oh, .comm.mr, .comm.mkm, .comm.sv, .comm.ti     { -epubx-flow-into: km; -epubx-flow-linger: 99; }
  .head-area { content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm; font-size: 8.5pt; color: #777; text-align: center; border-bottom: 0.5pt solid #ccc; }
  .body-area { -epubx-flow-from: body; top: 20mm; bottom: 25mm; left: 48mm; right: 48mm; }
  .km-area { -epubx-flow-from: km; top: 20mm; bottom: 25mm; right: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-right: 0.5pt solid #ddd; padding-right: 2mm; }
  .raavad-area { -epubx-flow-from: raavad; top: 20mm; bottom: 25mm; left: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-left: 0.5pt solid #ddd; padding-left: 2mm; }
  .raavad-cont-label { content: "המשך השגות הראב\"ד"; top: 13mm; left: 13mm; width: 31mm; height: 6mm; font-size: 7.5pt; color: #888; border-bottom: 0.4pt dotted #ccc; }
  .page-num { content: counter(page); bottom: 6mm; left: 0; right: 0; height: 8mm; font-size: 9pt; text-align: center; color: #888; }
%(MASTERS)s  @-epubx-page-master base {
    @-epubx-partition class(head-area) {}
    @-epubx-partition class(body-area) {}
    @-epubx-partition class(km-area) {}
    @-epubx-partition class(raavad-cont-label) {}
    @-epubx-partition class(raavad-area) {}
    @-epubx-partition class(page-num) {}
  }
}
"""

MASTER = """
  /* anchored floats: page %(page)d, first passage at %(top).1fmm;
     raavad blocks stack beside their passages instead of page-top */
  .head-area-p%(page)d { content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm; font-size: 8.5pt; color: #777; text-align: center; border-bottom: 0.5pt solid #ccc; }
  .body-main-p%(page)d { -epubx-flow-from: body; top: 20mm; bottom: 25mm; left: 48mm; right: 48mm; }
  .km-area-p%(page)d { -epubx-flow-from: km; top: 20mm; bottom: 25mm; right: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-right: 0.5pt solid #ddd; padding-right: 2mm; }
  .raavad-area-p%(page)d { -epubx-flow-from: raavad; top: %(top).1fmm; bottom: 25mm; left: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-left: 0.5pt solid #ddd; padding-left: 2mm; }
  .page-num-p%(page)d { content: counter(page); bottom: 6mm; left: 0; right: 0; height: 8mm; font-size: 9pt; text-align: center; color: #888; }
  @-epubx-page-master anchored-p%(page)d {
    -epubx-enabled: -epubx-expr(page-number == %(page)d);
    @-epubx-partition class(head-area-p%(page)d) {}
    @-epubx-partition class(body-main-p%(page)d) {}
    @-epubx-partition class(km-area-p%(page)d) {}
    @-epubx-partition class(raavad-area-p%(page)d) {}
    @-epubx-partition class(page-num-p%(page)d) {}
  }
"""


def build_pdf(css_path, pdf_path):
    r = subprocess.run(["npx", "vivliostyle", "build", "content.html", "-d",
                        "--user-style", css_path, "-o", pdf_path,
                        "--executable-browser", "/usr/bin/google-chrome"],
                       cwd=APP, capture_output=True, text=True, timeout=110)
    if r.returncode != 0 or not os.path.exists(pdf_path):
        print(r.stdout[-2000:], r.stderr[-2000:], file=sys.stderr)
        sys.exit(1)


def measure(pdf_path):
    r = subprocess.run(["pdftotext", "-bbox", pdf_path, "-"],
                       capture_output=True, text=True, timeout=60)
    pages = re.split(r"<page ", r.stdout)[1:]
    out = {}
    for pnum, p in enumerate(pages, 1):
        words = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', p)
        center_first = {}
        left_words = []
        for x0, y0, x1, y1, w in words:
            x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
            cx = (x0 + x1) / 2
            if CENTER_MIN_PT <= cx <= CENTER_MAX_PT:
                for hid, first in ANCHOR_WORD.items():
                    if w == first and hid not in center_first:
                        center_first[hid] = y0 * MM
            elif x1 <= LEFT_COL_MAX_PT:
                left_words.append((y0 * MM, y1 * MM))
        for hid, top in center_first.items():
            e = out.setdefault(hid, {})
            if "anchor" not in e:
                e["anchor"] = {"page": pnum, "top": top}
        for hid in ANCHOR_WORD:
            e = out.get(hid, {})
            # raavad chunk: left-column words on the page where its anchor lives
            if e.get("anchor", {}).get("page") == pnum and left_words and "raavad" not in e:
                e["raavad"] = {"page": pnum,
                               "top": min(y0 for y0, _ in left_words),
                               "height": max(y1 for _, y1 in left_words) - min(y0 for y0, _ in left_words)}
    return out


def gen_css(m):
    # one conditional master per page that has anchors: source absorbs the
    # space above the first anchor; raavad blocks stack from that point.
    by_page = {}
    for hid, e in m.items():
        if e.get("anchor"):
            by_page.setdefault(e["anchor"]["page"], []).append(e["anchor"]["top"])
    masters = ""
    for page, tops in sorted(by_page.items()):
        top = max(20.0, min(tops))
        masters += MASTER % {"page": page, "top": top, "bt": top - 20}
    return BASE_HEAD % {"MASTERS": masters}


def main():
    css = os.path.join(APP, "templates/t6-anchored.gen.css")
    pdf = os.path.join(APP, "out/t6-anchored.pdf")
    prev = None
    for it in range(3):
        if it == 0:
            open(css, "w").write(gen_css({}))
        build_pdf(css, pdf)
        m = measure(pdf)
        print("iter", it, json.dumps(m, ensure_ascii=False))
        if it > 0:
            ok = all(m.get(h, {}).get("anchor") and prev.get(h, {}).get("anchor")
                     and m[h]["anchor"]["page"] == prev[h]["anchor"]["page"]
                     and abs(m[h]["anchor"]["top"] - prev[h]["anchor"]["top"]) <= 1
                     for h in ANCHOR_WORD)
            if ok:
                print("converged: true")
                break
        prev = m
        open(css, "w").write(gen_css(m))
    else:
        print("converged: false")


main()
