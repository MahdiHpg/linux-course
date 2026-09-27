// checkfit.js: find .page elements whose content exceeds their fixed height
const path = require('path');
function loadPlaywright() {
  try { return require('playwright'); } catch (_) {}
  const Module = require('module');
  const g = 'C:\\Users\\MahdiLpTp\\AppData\\Roaming\\npm\\node_modules';
  Module.globalPaths.push(g);
  return require(path.join(g, 'playwright'));
}
(async () => {
  const pw = loadPlaywright();
  const browser = await pw.chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1400 } });
  const target = path.resolve(process.argv[2] || 'book.html');
  await page.goto('file:///' + target.split(path.sep).join('/'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(250);
  const bad = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.page').forEach(el => {
      if (el.scrollHeight > el.clientHeight + 1) {
        out.push({ id: el.id, sh: el.scrollHeight, ch: el.clientHeight });
      }
    });
    return out;
  });
  console.log(JSON.stringify(bad, null, 1));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
