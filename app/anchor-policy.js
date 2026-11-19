// Anchored-floating policy layer probe (bounded):
// pass 1: render with base geometry in a real browser, measure each Raavad
//         anchor passage (page, vertical offset) and each Raavad block height.
// pass 2..3: generate per-page masters (source column absorbs the space above
//         the float; Raavad block placed beside its passage), re-render,
//         re-measure; iterate until offsets converge (<=1mm) or max 3 passes.
// Output: templates/t6-anchored.gen.css + console JSON with measurements.
const puppeteer = require('puppeteer-core');
const fs = require('fs');

const BASE_CSS = fs.readFileSync('/tmp/poc/app/templates/t2-rambam.css', 'utf8')
  // strip the fixed raavad-area/body-area from the base master; we re-declare them per master below
  ;

function buildBaseCss() {
  // same geometry as templates/t2-rambam.css but as a named default master,
  // so per-anchor-page masters can override it for their page only.
  return `@page { size: A4; margin: 0; }
@-epubx-page-template {
  @-epubx-flow raavad { -epubx-flow-consume: all; }
  @-epubx-flow km     { -epubx-flow-consume: all; }
  .comm.raavad { -epubx-flow-into: raavad; -epubx-flow-linger: 99; }
  .comm.km     { -epubx-flow-into: km; -epubx-flow-linger: 99; }
  .head-area { content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm; font-size: 8.5pt; color: #777; text-align: center; border-bottom: 0.5pt solid #ccc; }
  .body-area { -epubx-flow-from: body; top: 20mm; bottom: 55mm; left: 48mm; right: 48mm; }
  .km-area { -epubx-flow-from: km; top: 20mm; bottom: 55mm; right: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-right: 0.5pt solid #ddd; padding-right: 2mm; }
  .raavad-area { -epubx-flow-from: raavad; top: 20mm; bottom: 55mm; left: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-left: 0.5pt solid #ddd; padding-left: 2mm; }
  .page-num { content: counter(page); bottom: 6mm; left: 0; right: 0; height: 8mm; font-size: 9pt; text-align: center; color: #888; }
  @-epubx-page-master class(base) {
    @-epubx-partition class(head-area) {}
    @-epubx-partition class(body-area) {}
    @-epubx-partition class(km-area) {}
    @-epubx-partition class(raavad-area) {}
    @-epubx-partition class(page-num) {}
  }
}
`;
}

function anchorMasterCss(m) {
  // m: {id, page, anchorTop, raavadHeight}
  // On the anchor page: source column spans full width above the float
  // (absorbs the otherwise-empty side column), narrows beside it;
  // the Raavad block starts beside its passage (top = anchor offset).
  const bodyTopH = Math.max(0, m.anchorTop - 20);
  const raavadH = Math.min(m.raavadHeight + 2, 297 - 25 - m.anchorTop);
  return `
  /* anchored float for ${m.id}: page ${m.page}, anchor at ${m.anchorTop.toFixed(1)}mm, block ${m.raavadHeight.toFixed(1)}mm */
  .head-area-${m.id} { content: "משנה תורה · הלכות טומאת מת · פרק י״ח"; top: 8mm; left: 15mm; right: 15mm; height: 8mm; font-size: 8.5pt; color: #777; text-align: center; border-bottom: 0.5pt solid #ccc; }
  .body-top-${m.id} { -epubx-flow-from: body; top: 20mm; left: 13mm; right: 13mm; height: ${bodyTopH.toFixed(1)}mm; }
  .body-main-${m.id} { -epubx-flow-from: body; top: ${m.anchorTop.toFixed(1)}mm; bottom: 25mm; left: 48mm; right: 48mm; }
  .km-area-${m.id} { -epubx-flow-from: km; top: 20mm; bottom: 25mm; right: 13mm; width: 31mm; font-size: 8.5pt; line-height: 1.35; border-right: 0.5pt solid #ddd; padding-right: 2mm; }
  .raavad-area-${m.id} { -epubx-flow-from: raavad; top: ${m.anchorTop.toFixed(1)}mm; left: 13mm; width: 31mm; height: ${raavadH.toFixed(1)}mm; font-size: 8.5pt; line-height: 1.35; border-left: 0.5pt solid #ddd; padding-left: 2mm; }
  .page-num-${m.id} { content: counter(page); bottom: 6mm; left: 0; right: 0; height: 8mm; font-size: 9pt; text-align: center; color: #888; }
  @-epubx-page-master class(anchored-${m.id}) {
    -epubx-enabled: -epubx-expr(page-number == ${m.page});
    @-epubx-partition class(head-area-${m.id}) {}
    @-epubx-partition class(body-top-${m.id}) {}
    @-epubx-partition class(body-main-${m.id}) {}
    @-epubx-partition class(km-area-${m.id}) {}
    @-epubx-partition class(raavad-area-${m.id}) {}
    @-epubx-partition class(page-num-${m.id}) {}
  }
`;
}

function buildCss(measurements) {
  const tmplOpen = BASE_CSS.indexOf('@-epubx-page-template {');
  const head = buildBaseCss();
  const insertAt = head.lastIndexOf('}');
  const masters = measurements.map(anchorMasterCss).join('\n');
  return head.slice(0, insertAt) + masters + '\n}\n';
}

(async () => {
  const browser = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome', headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 850 });
  await page.goto('http://127.0.0.1:8901/render.html', { waitUntil: 'networkidle2', timeout: 60000 });
  await page.waitForFunction(() => typeof window.__loadCss === 'function', { timeout: 30000 });

  const measure = async () => {
    const count = await page.evaluate(() => document.querySelectorAll('[data-vivliostyle-page-container]').length);
    const out = {};
    for (let i = 0; i < count; i++) {
      await page.evaluate((idx) => {
        try { window.__viewer.navigateToPage({ pageIndex: idx }); }
        catch (e) { window.__viewer.navigateToPage(idx); }
      }, i);
      await new Promise(r => setTimeout(r, 450));
      const part = await page.evaluate((idx) => {
        const pages = [...document.querySelectorAll('[data-vivliostyle-page-container]')];
        const p = pages[idx];
        if (!p) return null;
        const pr = p.getBoundingClientRect();
        if (!pr.width) return null;
        const mmPerPx = 210 / pr.width;
        const res = {};
        for (const id of ['h4', 'h5']) {
          const a = p.querySelector('#' + id);
          const r = p.querySelector('aside.comm.raavad[data-for="' + id + '"]');
          if (a && !res[id]) res[id] = {};
          if (a) res[id].anchor = { page: idx + 1, top: (a.getBoundingClientRect().top - pr.top) * mmPerPx };
          if (r) {
            if (!res[id]) res[id] = {};
            const rr = r.getBoundingClientRect();
            res[id].raavad = { page: idx + 1, top: (rr.top - pr.top) * mmPerPx, height: rr.height * mmPerPx };
          }
        }
        return res;
      }, i);
      if (part) for (const id of Object.keys(part)) { out[id] = Object.assign(out[id] || {}, part[id]); }
    }
    return { totalPages: count, out };
  };

  let measurements = null;
  let converged = false;
  for (let iter = 0; iter < 3 && !converged; iter++) {
    const css = iter === 0 ? buildBaseCss()
      : buildCss(measurements.filter(m => m && m.anchor && m.raavad)
          .map(m => ({ id: m.id, page: m.anchor.page, anchorTop: m.anchor.top, raavadHeight: m.raavad.height })));
    await page.evaluate(async (cssText) => {
      await window.__loadCss(cssText);
    }, css);
    await page.waitForFunction(() => window.__ready === true, { timeout: 60000 });
    const res = await measure();
    const prev = measurements;
    measurements = ['h4', 'h5'].map(id => { const e = res.out[id] || {}; return { id, anchor: e.anchor || null, raavad: e.raavad || null }; });
    console.log('iter', iter, 'totalPages', res.totalPages, JSON.stringify(measurements));
    if (iter === 0) { converged = false; continue; }
    converged = measurements.every((m, i) => {
      const p = prev[i];
      return m.anchor && p.anchor && m.anchor.page === p.anchor.page && Math.abs(m.anchor.top - p.anchor.top) <= 1;
    });
  }
  const finalCss = buildCss(measurements.filter(m => m && m.anchor && m.raavad)
    .map(m => ({ id: m.id, page: m.anchor.page, anchorTop: m.anchor.top, raavadHeight: m.raavad.height })));
  fs.writeFileSync('/tmp/poc/app/templates/t6-anchored.gen.css', finalCss);
  console.log('converged:', converged);
  console.log('FINAL', JSON.stringify(measurements));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
