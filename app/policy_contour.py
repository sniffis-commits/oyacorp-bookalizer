#!/usr/bin/env python3
"""t7: contour-following variant of t2.

User's model (16:31 photo): the outer commentary (Kesef Mishneh) hugs the
central text block's actual contour per page and expands into the freed
space UNDER the source where the source ends early - it is not a fixed
3-region grid.

Engine reality (t6 finding): expr can reference partition properties/edges
but never the fill level of a flow, so a true contour-following bottom strip
needs measure -> regenerate:
  pass 1: render with the base t2 master, measure where the source (body
          flow, incl. its raavad float) actually ends on each page
  pass k: regenerate masters so km-bottom starts at the measured source
          bottom + 2mm on that page; pages whose source never reached them
          give the center column to km entirely
  iterate until the measured bottoms stop moving between passes.

Honesty note: the contour follows the SOURCE block (incl. raavad float),
not the km flow - the km side columns still run full height.
"""
import json, os, re, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
OUT = "out"; os.makedirs(OUT, exist_ok=True)
LOG = "/tmp/t7-build.log"
BODY_FS = 12; TOL = 0.5  # mm

def sh(cmd, log=LOG):
    with open(log, "ab") as f:
        f.write(("\n$ " + cmd + "\n").encode())
        subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, check=True)

BASE_HEAD = """@page { size: A4; margin: 0; }
@-epubx-page-template {
  @-epubx-flow km   { -epubx-flow-consume: all; }
  @-epubx-flow rest { -epubx-flow-consume: all; }
  .comm.km { -epubx-flow-into: km; -epubx-flow-linger: 99; }
  .comm.mr, .comm.oh, .comm.mkm, .comm.sv, .comm.ti {
    -epubx-flow-into: rest; -epubx-flow-linger: 99;
  }
  .comm.raavad {
    float: left; width: 33%%;
    margin: 0.5mm 0 1.5mm 3mm; padding: 1.5mm;
    border: 0.5pt solid #bbb; background: #f7f7f7;
    font-size: 9pt; line-height: 1.35;
  }
  h2.st-head { clear: both; }

%(MASTERS)s
}
"""

def master(name, enabled_expr, kbtop=None, lk_tail=None, inner_rest=False,
           rest_cols=False):
    # Inline named partitions per master: cross-partition -epubx-expr
    # references (km bottoms -> rest-area top) only resolve against partitions
    # declared in the SAME master by name; the class(...) partition form
    # silently broke those references and the side columns collapsed.
    # kbtop overrides km-bottom's top (contour following); None = base
    # geometry (body bottom + 8).
    # The bottom strip (rest-area) is fed by the dedicated mr flow: MR blocks
    # are separate single-page elements, and the element-boundary rule (next
    # element starts a fresh page when the previous ends in a page's last
    # partition of that flow) places each MR block on the next page's strip.
    # lk_tail (only on the last km page): measured bottom of the km stream's
    # center-column tail. No strip on this page (MR blocks are exhausted on
    # the source pages): all partitions run to the 14mm bottom margin, the
    # left column goes to rest (km is exhausted before it), and rest-center-lk
    # starts lk_tail+3mm below the km tail. Declaration order rest-inner-lk
    # then rest-center-lk => rest fills center first, then inner, matching
    # the reading order.
    # inner_rest (non-lk contour pages whose km-inner measured empty): the
    # left column goes to the rest flow instead of km.
    # rest_cols (base master only): full-page rest columns so the rest flow
    # always has somewhere to land (pass 1 and overflow pages).
    s = name
    kbtop_decl = ("top: %.2fmm;" % kbtop) if kbtop is not None else \
        "top: -epubx-expr(body-area-%s.margin-bottom-edge + 8);" % s
    bot_decl = ("bottom: -epubx-expr(page-height - "
                "rest-area-%s.margin-top-edge + 8);" % s) if lk_tail is None \
        else "bottom: 14mm;"
    # km-bottom must not overlap rest-center-lk (the engine skipped the
    # overlapped rest partition): shrink it to the measured km tail + 1mm.
    kmbot_decl = bot_decl if lk_tail is None else \
        "bottom: %.2fmm;" % (297.0 - (lk_tail + 1.0))
    strip_part = "" if lk_tail is not None else """
    @-epubx-partition rest-area-%(s)s {
      -epubx-flow-from: rest;
      bottom: 14mm; left: 13mm; right: 13mm; height: auto; max-height: 40mm;
      font-size: 8.5pt; line-height: 1.35;
      border-top: 0.6pt solid #bbb; padding-top: 1.5mm;
    }
""" % {"s": s}
    lk_parts = ""
    if lk_tail is not None:
        lk_parts = """
    @-epubx-partition rest-inner-lk-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; left: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
      border-left: 0.5pt solid #ddd; padding-left: 2mm;
    }
    @-epubx-partition rest-center-lk-%(s)s {
      -epubx-flow-from: rest;
      top: %(ctop).2fmm; bottom: 14mm;
      left: 48mm; right: 48mm;
      font-size: 8.5pt; line-height: 1.35;
      padding: 0 1.5mm;
    }
""" % {"s": s, "ctop": max(20.0, lk_tail + 3.0)}
    if rest_cols:
        lk_parts += """
    @-epubx-partition rest-inner-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; left: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
    }
    @-epubx-partition rest-center-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; left: 48mm; right: 48mm;
      font-size: 8.5pt; line-height: 1.35;
    }
    @-epubx-partition rest-side-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; right: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
    }
""" % {"s": s}
    inner_part = ""
    if lk_tail is None:
        inner_part = """
    @-epubx-partition km-inner-%(s)s {
      -epubx-flow-from: %(inner_flow)s;
      top: 20mm; %(bot)s
      left: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
      border-left: 0.5pt solid #ddd; padding-left: 2mm;
    }
""" % {"s": s, "inner_flow": "rest" if inner_rest else "km", "bot": bot_decl}
    return """
  @-epubx-page-master %(name)s {
    -epubx-enabled: -epubx-expr(%(enabled)s);
    @-epubx-partition head-area-%(s)s {
      content: "משנה תורה · הלכות טומאת מת · פרק י״ח";
      top: 8mm; left: 15mm; right: 15mm; height: 8mm;
      font-size: 8.5pt; color: #777; text-align: center;
      border-bottom: 0.5pt solid #ccc;
    }
    @-epubx-partition page-num-%(s)s {
      content: counter(page);
      bottom: 6mm; left: 0; right: 0; height: 8mm;
      font-size: 9pt; text-align: center; color: #888;
    }
    @-epubx-partition body-area-%(s)s {
      -epubx-flow-from: body;
      top: 20mm; bottom: 55mm; left: 48mm; right: 48mm;
    }
%(lk_parts)s
%(inner_part)s
    @-epubx-partition km-bottom-%(s)s {
      -epubx-flow-from: km;
      %(kbtop_decl)s
      %(kmbot)s
      left: 48mm; right: 48mm;
      font-size: 8.5pt; line-height: 1.35;
      border-top: 0.4pt solid #ddd; padding-top: 1.5mm;
    }
    @-epubx-partition km-side-%(s)s {
      -epubx-flow-from: km;
      top: 20mm; %(bot)s
      right: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
      border-right: 0.5pt solid #ddd; padding-right: 2mm;
    }
%(strip_part)s
  }
""" % {"name": name, "enabled": enabled_expr, "s": s,
         "kbtop_decl": kbtop_decl, "bot": bot_decl, "strip_part": strip_part,
         "lk_parts": lk_parts, "inner_part": inner_part,
         "kmbot": kmbot_decl}

# Base master: fallback for pages beyond the contour range. MUST be disabled
# on pages 1..N (via -epubx-enabled), otherwise its partitions duplicate the
# contour masters' partitions and the extra body-area steals body content.

def restcol_master(n):
    # Pages after the KM stream ends: the remaining commentary stream (rest
    # flow) expands into the whole page - three full-height columns, no strip.
    # Declaration order inner,center,side => fill order side,center,inner.
    s = "restcol-p%d" % n
    return """
  @-epubx-page-master %(name)s {
    -epubx-enabled: -epubx-expr(page-number == %(n)d);
    @-epubx-partition head-area-%(s)s {
      content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm;
      font-size: 8.5pt; color: #777; text-align: center;
      border-bottom: 0.5pt solid #ccc;
    }
    @-epubx-partition page-num-%(s)s {
      content: counter(page); bottom: 6mm; left: 0; right: 0; height: 8mm;
      font-size: 9pt; text-align: center; color: #888;
    }
    @-epubx-partition rest-inner-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; left: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
      border-left: 0.5pt solid #ddd; padding-left: 2mm;
    }
    @-epubx-partition rest-center-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; left: 48mm; right: 48mm;
      font-size: 8.5pt; line-height: 1.35;
      padding: 0 1.5mm;
    }
    @-epubx-partition rest-side-%(s)s {
      -epubx-flow-from: rest;
      top: 20mm; bottom: 14mm; right: 13mm; width: 31mm;
      font-size: 8.5pt; line-height: 1.35;
      border-right: 0.5pt solid #ddd; padding-right: 2mm;
    }
  }
""" % {"name": s, "n": n, "s": s}

def base_master(npages):
    return master("base", "page-number > %d" % npages, rest_cols=True)

def contour_master(n, contour, lk_tail=None, inner_rest=False):
    # km-bottom starts 4mm below the measured contour (source/float bottom).
    # The gap must exceed the float's bottom margin (1.5mm) with slack: an
    # overlapping partition edge makes the engine defer the float below it.
    # contour == 0: no source on this page, km takes the whole center column.
    # lk_tail: measured km-tail bottom; set only on the last km page.
    # inner_rest: this page's left column measured empty of km -> give it to
    # the rest flow.
    kbtop = 20.0 if contour == 0.0 else contour + 4.0
    return master("contour-p%d" % n, "page-number == %d" % n, kbtop,
                  lk_tail=lk_tail, inner_rest=inner_rest)

def gen_css(bottoms_by_page, last_km_page, lk_tail=None, km_inner_pages=()):
    masters = [base_master(len(bottoms_by_page))]
    for pg in sorted(bottoms_by_page):
        if pg <= last_km_page:
            masters.append(contour_master(
                pg, bottoms_by_page[pg],
                lk_tail=lk_tail if pg == last_km_page else None,
                inner_rest=pg not in km_inner_pages))
        else:
            masters.append(restcol_master(pg))
    return BASE_HEAD % {"MASTERS": "".join(masters)}

MM = 2.83465  # pt per mm
BODY_L = 48 * MM; BODY_R = (210 - 48) * MM
BODY_TOP = 20 * MM
BASE_KBTOP = 250.0  # base master km-bottom top (body bottom 242 + 8), mm

BODY_BOT_EDGE = (297 - 55) * MM  # base body-area bottom edge, pt
FLOAT_X1 = 95 * MM               # raavad float column right edge, pt

def measure(pdf, prev_contours=None):
    """Per page: contour = max(source bottom, raavad-float bottom) in mm.
    source words: bbox height > 12pt, in the body band, above the body bottom
    edge. float words: 9.5-12pt, left float column (x1 <= 95mm), above the
    edge. prev_contours gives this pass's per-page shrunken body bottom edge
    (contour+1); pass 1 uses the base edge. Pages with no source/float words
    get contour 0 (km takes the whole center column)."""
    r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                       capture_output=True, text=True, timeout=60)
    per = {}
    pages = re.split(r"<page ", r.stdout)[1:]
    for pnum, p in enumerate(pages, 1):
        words = re.findall(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">',
            p)
        edge = BODY_BOT_EDGE
        if prev_contours and prev_contours.get(pnum):
            edge = min(edge, (prev_contours[pnum] + 4.0) * MM - 1)
        s_bot = f_bot = 0.0
        for x0, y0, x1, y1 in words:
            x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
            if x0 < BODY_L - 3 or x1 > BODY_R + 3:
                continue
            if y0 < BODY_TOP - 3 or y0 >= edge - 1:
                continue
            h = y1 - y0
            if h > 12:
                s_bot = max(s_bot, y1)
            elif h > 9.5 and x1 <= FLOAT_X1 + 3:
                f_bot = max(f_bot, y1)
        # a page with no source words has no contour: km takes the center
        per[pnum] = (max(s_bot, f_bot) if s_bot > 0 else 0.0) / MM
    return per, len(pages)

KM_VOCAB = None
def last_km_page(pdf):
    """Last page containing km-flow words (vocab-based; rest words that share
    km vocabulary pollute, so require a minimum count)."""
    global KM_VOCAB
    if KM_VOCAB is None:
        import html as _h
        hsrc = open("content.html").read()
        def norm(t):
            t = re.sub(r"<[^>]+>", " ", t); t = _h.unescape(t)
            return re.sub(r"\s+", " ", t).strip()
        km = set(norm(" ".join(re.findall(
            r"<aside class=\"comm km[^\"]*\"[^>]*>(.*?)</aside>", hsrc, re.S))).split())
        rest = set(norm(" ".join(re.findall(
            r"<aside class=\"comm (?:mr|oh|mkm|sv|ti)[^\"]*\"[^>]*>(.*?)</aside>",
            hsrc, re.S))).split())
        KM_VOCAB = km - rest
    import html as _h
    r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                       capture_output=True, text=True, timeout=60)
    pages = re.split(r"<page ", r.stdout)[1:]
    last = 0
    for pnum, p in enumerate(pages, 1):
        toks = [_h.unescape(w)[::-1] for w in re.findall(
            r'<word xMin="[\d.]+" yMin="[\d.]+" xMax="[\d.]+" yMax="[\d.]+">([^<]*)</word>', p)]
        if sum(1 for t in toks if t in KM_VOCAB) >= 15:
            last = pnum
    return last

def km_inner_pages(pdf):
    """Pages whose left column (x < 46mm) contains km-flow words."""
    import html as _h
    last_km_page(pdf)  # ensure KM_VOCAB is initialised
    r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                       capture_output=True, text=True, timeout=60)
    pages = re.split(r"<page ", r.stdout)[1:]
    out = set()
    for pnum, p in enumerate(pages, 1):
        for x0, x1, w in re.findall(
                r'<word xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)" yMax="[\d.]+">([^<]*)</word>',
                p):
            if float(x1) <= 46 * MM and _h.unescape(w)[::-1] in KM_VOCAB:
                out.add(pnum)
                break
    return out

def km_tail_bottom(pdf, lkp):
    """Bottom (mm) of the km stream's center-column tail on the last km page.
    km words: vocab-matched, in the center band. 0 when the tail does not
    reach the center column (rest-center-lk then starts at 20mm)."""
    import html as _h
    if not lkp:
        return 0.0
    last_km_page(pdf)  # ensure KM_VOCAB is initialised
    r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                       capture_output=True, text=True, timeout=60)
    pages = re.split(r"<page ", r.stdout)[1:]
    if lkp > len(pages):
        return 0.0
    bot = 0.0
    for x0, y0, x1, y1, w in re.findall(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
            pages[lkp - 1]):
        x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
        t = _h.unescape(w)[::-1]
        if t in KM_VOCAB and 46 * MM - 3 <= x0 and x1 <= 164 * MM + 3 \
                and 15 * MM <= y0 < 285 * MM:
            bot = max(bot, y1)
    return bot / MM

REST_RE = r"\s*<aside class=\"comm (?:mr|oh|mkm|sv|ti)[^\"]*\"[^>]*>.*?</aside>"

def reorder_content():
    # Engine finding (spec 3.5): eligibility is gated by document position vs
    # the max unconsumed offset across primary flows. Interleaved rest blocks
    # made km fragments skip pages. Fix: keep the first two rest blocks (the
    # in-place MR and the short OH) in place so source pages get their bottom
    # strip (user's model "המעשה רוקח מתחת"); move the remaining commentary
    # pool to the end of the document as ONE merged element - the observed
    # element-boundary rule (next element starts a fresh page when the
    # previous ends in a page's last rest partition) otherwise leaves the
    # restcol pages' inner columns 60-90% blank.
    # NOTE: a variant giving MR blocks their own flow (to pin each MR under
    # its source page) mis-placed the second MR block onto overflow pages;
    # reverted.
    # Engine finding 2: when a rest-flow element ends in the LAST partition
    # of a page, the next element starts on a fresh page instead of filling
    # the remaining space in that partition (observed: sv/ti tails left the
    # inner columns of the restcol pages 60-90% blank). Fix: merge the moved
    # pool into ONE aside element so no element boundary can force a page
    # break; the block headers stay inline.
    hsrc = open("content.html").read()
    blocks = re.findall(REST_RE, hsrc, re.S)
    keep, others = blocks[:2], blocks[2:]
    pos = hsrc.find(keep[1])
    head_part, tail_part = hsrc[:pos + len(keep[1])], hsrc[pos + len(keep[1]):]
    for b in others:
        tail_part = tail_part.replace(b, "", 1)
    inners = []
    for b in others:
        m = re.match(r"\s*<aside[^>]*>(.*)</aside>\s*$", b, re.S)
        inners.append(m.group(1).strip())
    merged = ('<aside class="comm mkm st-comm">' + "\n\n".join(inners) +
              "</aside>")
    i = tail_part.rfind("</body>")
    open("content.ordered.html", "w").write(
        head_part + tail_part[:i] + "\n" + merged + "\n" + tail_part[i:])

def build(css, tag):
    open("templates/t7-contour.gen.css", "w").write(css)
    reorder_content()
    pdf = "/tmp/t7-%s.pdf" % tag
    r = subprocess.run(["npx", "vivliostyle", "build", "content.ordered.html", "-d",
                        "--user-style", "templates/t7-contour.gen.css",
                        "-o", pdf,
                        "--executable-browser", "/usr/bin/google-chrome"],
                       capture_output=True, text=True, timeout=110)
    if r.returncode != 0 or not os.path.exists(pdf):
        print(r.stdout[-1500:], r.stderr[-1500:], file=sys.stderr)
        sys.exit(1)
    return pdf

def bottoms_close(a, b):
    if set(a) != set(b):
        return False
    return all(abs(a[k] - b[k]) <= TOL for k in a)

def main():
    # pass 1: base master only, enabled everywhere
    css = BASE_HEAD.replace("%%", "%").replace("%(MASTERS)s", base_master(0))
    pdf = build(css, "pass1")
    cur, npages = measure(pdf)
    print("pass1 contours:", json.dumps(cur), flush=True)
    src_pages = [p for p in range(1, npages + 1) if cur.get(p, 0.0) > 0]

    lkp = last_km_page(pdf)
    tail = km_tail_bottom(pdf, lkp)
    kip = km_inner_pages(pdf)
    print("pass1 last km page:", lkp, "km tail bottom:", round(tail, 2),
          "km inner pages:", sorted(kip), flush=True)
    k = 1
    for k in range(2, 7):
        css = gen_css({p: cur.get(p, 0.0) for p in range(1, npages + 1)}, lkp,
                      lk_tail=tail, km_inner_pages=kip)
        pdf = build(css, f"pass{k}")
        nxt, npages2 = measure(pdf, prev_contours=cur)
        # pages that never had source keep contour 0 permanently
        nxt = {p: (nxt.get(p, 0.0) if p in src_pages else 0.0)
               for p in range(1, npages2 + 1)}
        lkp2 = last_km_page(pdf)
        tail2 = km_tail_bottom(pdf, lkp2)
        kip2 = km_inner_pages(pdf)
        print(f"pass{k} contours:", json.dumps(nxt), "last km page:", lkp2,
              "km tail bottom:", round(tail2, 2), "km inner pages:",
              sorted(kip2), flush=True)
        if npages2 == npages and lkp2 == lkp and abs(tail2 - tail) <= TOL \
                and kip2 == kip and bottoms_close(cur, nxt):
            print(f"converged after pass {k}", flush=True)
            break
        cur, npages, lkp, tail, kip = nxt, npages2, lkp2, tail2, kip2
    else:
        print("NOT converged after max passes", flush=True)

    sh(f"cp /tmp/t7-pass{k}.pdf out/t7-contour.pdf")
    sh("ls -la out/t7-contour.pdf templates/t7-contour.gen.css")
    print("PDF pages:", subprocess.run(["pdfinfo", "out/t7-contour.pdf"],
          capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])

if __name__ == "__main__":
    main()
