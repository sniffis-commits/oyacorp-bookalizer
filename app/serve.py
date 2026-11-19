#!/usr/bin/env python3
"""PoC demo server: static files + /gen.css endpoint that builds the
geometry-playground userStyle from query parameters.
Run: python3 serve.py [port]  ->  http://127.0.0.1:8901/index.html
"""
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote

CSS_TMPL = """@page { size: A4; margin: 0; }
@-epubx-page-template {
  @-epubx-flow km     { -epubx-flow-consume: all; }
  @-epubx-flow rest   { -epubx-flow-consume: all; }
  .comm.raavad { float: left; width: 33%%; margin: 0.5mm 0 1.5mm 3mm; padding: 1.5mm; background: #f5f5f5; }
  h2.st-head { clear: both; }
  .comm.km { -epubx-flow-into: km; -epubx-flow-linger: 99; }
  .comm.mr, .comm.oh, .comm.mkm, .comm.sv, .comm.ti { -epubx-flow-into: rest; -epubx-flow-linger: 99; }
  .head-area { content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm; font-size: 8.5pt; color: #777; text-align: center; border-bottom: 0.5pt solid #ccc; }
  .body-area { -epubx-flow-from: body; top: 20mm; bottom: 60mm; left: %(side)smm; right: %(side)smm; font-size: %(fs)spt; }
  .km-area { -epubx-flow-from: km; top: 20mm; bottom: 60mm; right: 13mm; width: %(commW)smm; font-size: %(commFs)spt; line-height: 1.35; border-right: 0.5pt solid #ddd; padding-right: 2mm; }
  .km-bottom { -epubx-flow-from: km; top: 241mm; bottom: 46mm; left: %(side)smm; right: %(side)smm; font-size: %(commFs)spt; line-height: 1.35; border-top: 0.4pt solid #ddd; padding-top: 1.5mm; }
  .km-inner { -epubx-flow-from: km; top: 20mm; bottom: 60mm; left: 13mm; width: %(commW)smm; font-size: %(commFs)spt; line-height: 1.35; border-left: 0.5pt solid #ddd; padding-left: 2mm; }
  .rest-area { -epubx-flow-from: rest; bottom: 14mm; left: 13mm; right: 13mm; height: 28mm; font-size: %(commFs)spt; line-height: 1.35; border-top: 0.6pt solid #bbb; padding-top: 1.5mm; }
  .page-num { content: counter(page); bottom: 4mm; left: 0; right: 0; height: 8mm; font-size: 9pt; text-align: center; color: #888; }
  /* named shared styles: each role renders with the style assigned to it;
     one style definition drives every role it is assigned to */
  .st-src p { font-family: %(srcF)s !important; font-size: %(srcS)spt !important; }
  h2.st-head { font-family: %(headF)s !important; font-size: %(headS)spt !important; }
  .st-comm { font-family: %(commF)s !important; font-size: %(commS)spt !important; }
  .st-label { font-family: %(labelF)s !important; font-size: %(labelS)spt !important; }
  @-epubx-page-master {
    @-epubx-partition class(head-area) {}
    @-epubx-partition class(body-area) {}
    @-epubx-partition class(km-inner) {}
    @-epubx-partition class(km-bottom) {}
    @-epubx-partition class(km-area) {}
    @-epubx-partition class(rest-area) {}
    @-epubx-partition class(page-num) {}
  }
}
"""


FONT_FACE = """@font-face { font-family: 'Noto Serif Hebrew'; src: url('/fonts/NotoSerifHebrew.woff2') format('woff2'); font-weight: 100 900; font-display: swap; }
@font-face { font-family: 'Rubik'; src: url('/fonts/Rubik.woff2') format('woff2'); font-weight: 100 900; font-display: swap; }
"""

# bundled webfonts always render; system fonts depend on the user's machine
FONTS = {
    "david": '"David", "David Libre", serif',
    "frank": '"Frank Ruehl", "Frank-Ruehl", serif',
    "narkisim": '"Narkisim", "David", serif',
    "arial": 'Arial, "Noto Sans Hebrew", sans-serif',
    "noto": '"Noto Serif Hebrew", "David", serif',
    "rubik": '"Rubik", "Noto Sans Hebrew", sans-serif',
}


def font(q, key, default):
    return FONTS.get(q.get(key, [default])[0], FONTS[default])


def size(q, key, default, lo=7, hi=22):
    return min(hi, max(lo, float(q.get(key, [str(default)])[0])))


def build_css(q):
    srcW = min(130, max(70, float(q.get("srcW", ["114"])[0])))
    commW = min(50, max(20, float(q.get("commW", ["31"])[0])))
    side = (210 - srcW) / 2
    # three editable named styles a/b/c, each font+size; roles pick a style
    styles = {}
    for k in "abc":
        styles[k] = (font(q, k + "F", "david"), size(q, k + "S", {"a": 13, "b": 12, "c": 9.5}[k], lo=6, hi=22))
    amap = q.get("map", ["bacc"])[0]
    amap = (amap + "cccc")[:4]
    role = lambda i: styles.get(amap[i], styles["c"])
    srcF, srcS = role(0)
    headF, headS = role(1)
    commF, commS = role(2)
    labelF, labelS = role(3)
    return FONT_FACE + CSS_TMPL % {
        "side": side, "fs": srcS, "commW": commW, "commFs": commS,
        "srcF": srcF, "srcS": srcS, "headF": headF, "headS": headS,
        "commF": commF, "commS": commS, "labelF": labelF, "labelS": labelS,
    }


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        raw = unquote(urlparse(self.path).path)
        parts = [p for p in raw.split("/") if p and p != ".."]
        if "gen" in parts:
            i = parts.index("gen")
            seg = parts[i + 1:]
            if len(seg) == 10 and seg[9] == "style.css":
                q = {"srcW": [seg[0]], "commW": [seg[1]],
                     "aF": [seg[2]], "aS": [seg[3]],
                     "bF": [seg[4]], "bS": [seg[5]],
                     "cF": [seg[6]], "cS": [seg[7]],
                     "map": [seg[8]]}
                try:
                    body = build_css(q).encode("utf-8")
                except (ValueError, KeyError):
                    self.send_error(400)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
        super().do_GET()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8901
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
