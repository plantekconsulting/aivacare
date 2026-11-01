import { chromium } from "playwright-core";
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const p = await b.newPage({ viewport: { width: 1440, height: 810 }, deviceScaleFactor: 1.333 });
for (const s of ["s01", "s02", "s03", "s04", "s15"]) {
  await p.goto("file:///C:/dev/video/slides.html?s=" + s);
  await p.waitForTimeout(300);
  await p.screenshot({ path: `slides/${s}.png` });
}
await b.close();
