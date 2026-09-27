// measure.js: measure stride height of each flow block (incl. collapsed margins)
const path = require('path');
function loadPlaywright() {
  try { return require('playwright'); } catch (_) {}
  const Module = require('module');
  const g = 'C:\\Users\\MahdiLpTp\\AppData\\Roaming\\npm\\node_modules';
  Module.globalPaths.push(g);
  return require(path.join(g, 'playwright'));
}
(async () => {
  const file = process.argv[2];
  if (!file) { console.error('usage: node measure.js flow.html'); process.exit(2); }
  const pw = loadPlaywright();
  const browser = await pw.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1400 } });
  await page.goto('file:///' + path.resolve(file).replace(/\\/g, '/'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  const data = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('.flowblk'));
    const out = [];
    const base = els[0] ? els[0].offsetTop : 0;
    els.forEach((el, i) => {
      const top = el.offsetTop - base;
      let stride;
      if (i + 1 < els.length) {
        stride = (els[i + 1].offsetTop - base) - top;
      } else {
        const cs = getComputedStyle(el);
        stride = el.offsetHeight + parseFloat(cs.marginBottom || 0);
      }
      out.push({ ch: el.dataset.ch, bi: el.dataset.bi, h: Math.round(stride) });
    });
    return out;
  });
  console.log(JSON.stringify(data));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
