// SVG -> PNG with Playwright's Chromium.
// Usage: node render.mjs <jobs.json> <svg dir> <out dir>
// Each SVG is shown in an <img> on a local page; the render waits for the image
// to decode and fails the whole run if any image does not load.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [jobsPath, svgDir, outDir] = process.argv.slice(2);
if (!jobsPath || !svgDir || !outDir) {
  console.error('usage: node render.mjs <jobs.json> <svg dir> <out dir>');
  process.exit(2);
}
const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
const page = path.join(outDir, '_render.html');
const launch = {};
if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
const browser = await chromium.launch(launch);
let failed = 0;
try {
  for (const j of jobs) {
    const src = path.resolve(svgDir, j.src);
    if (!fs.existsSync(src)) { console.error(`missing source ${j.src}`); failed++; continue; }
    const out = path.resolve(outDir, j.out);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(page, `<html><body style="margin:0;background:transparent"><img src="file://${src}" style="display:block;width:${j.width}px;height:${j.height}px"></body></html>`);
    const p = await browser.newPage({ viewport: { width: j.width, height: j.height } });
    await p.goto('file://' + page);
    const ok = await p.waitForFunction(() => document.images[0].complete, null, { timeout: 15000 })
      .then(() => p.evaluate(() => document.images[0].naturalWidth > 0)).catch(() => false);
    if (!ok) { console.error(`failed to decode ${j.src}`); failed++; await p.close(); continue; }
    await p.screenshot({ path: out, omitBackground: !!j.transparent });
    await p.close();
  }
} finally {
  await browser.close();
  fs.rmSync(page, { force: true });
}
if (failed) { console.error(`${failed} render(s) failed`); process.exit(1); }
console.log(`rendered ${jobs.length}`);
