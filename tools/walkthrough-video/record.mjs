// Records each browser scene of the walkthrough. Usage: CODE=<access code> node record.mjs [scene-prefix]
import fs from "node:fs";
import { chromium } from "playwright-core";

const APP = "https://app.34-30-79-254.sslip.io";
const API = "https://api.34-30-79-254.sslip.io";
const CODE = process.env.CODE;
const only = process.argv[2];
const SAMPLE = "H:/My Drive/AI Projects/AivaCare/sample-labs/john-miller-liver-panel.pdf";

const CURSOR = `
window.addEventListener("DOMContentLoaded", () => {
  const c = document.createElement("div");
  c.style.cssText = "position:fixed;z-index:2147483647;width:24px;height:24px;border-radius:50%;background:rgba(15,118,110,.30);border:2px solid #0f766e;pointer-events:none;transform:translate(-50%,-50%);left:" + (window.__cx ?? -50) + "px;top:" + (window.__cy ?? -50) + "px;transition:transform .12s";
  document.body.appendChild(c);
  document.addEventListener("mousemove", (e) => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }, true);
  document.addEventListener("mousedown", () => { c.style.transform = "translate(-50%,-50%) scale(.6)"; c.style.background = "rgba(15,118,110,.6)"; }, true);
  document.addEventListener("mouseup", () => { c.style.transform = "translate(-50%,-50%) scale(1)"; c.style.background = "rgba(15,118,110,.30)"; }, true);
});`;

const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });

async function token(persona) {
  const r = await fetch(`${API}/login/${persona}?code=${encodeURIComponent(CODE)}`, { method: "POST" });
  return (await r.json()).token;
}
async function admin(path, body) {
  const r = await fetch(`${API}/admin/${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${await token("admin")}`, "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

const pause = (page, s) => page.waitForTimeout(s * 1000);
async function moveTo(page, loc, settle = 0.3) {
  await loc.scrollIntoViewIfNeeded();
  const b = await loc.boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 30 });
  await pause(page, settle);
}
async function click(page, loc) {
  await moveTo(page, loc, 0.35);
  await page.mouse.down();
  await page.waitForTimeout(90);
  await page.mouse.up();
}
async function scroll(page, px, seconds = 2) {
  const steps = Math.max(1, Math.round(seconds * 20));
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, px / steps);
    await page.waitForTimeout(50);
  }
}
async function typeIn(page, loc, text) {
  await click(page, loc);
  await loc.pressSequentially(text, { delay: 45 });
}
/** Waits until the last assistant bubble in `scope` stops changing (streaming finished). */
async function waitForAnswer(page, scope, timeout = 120000) {
  const start = Date.now();
  let last = "", stableSince = Date.now();
  while (Date.now() - start < timeout) {
    const texts = await scope.locator(".md").allInnerTexts();
    const cur = texts.at(-1) ?? "";
    if (cur !== last) { last = cur; stableSince = Date.now(); }
    else if (cur.length > 40 && Date.now() - stableSince > 3000) return;
    await page.waitForTimeout(300);
  }
  throw new Error("answer timeout");
}

async function scene(id, { persona, path, phone = false }, fn) {
  if (only && !id.startsWith(only)) return;
  const vp = phone ? { width: 390, height: 844 } : { width: 1440, height: 810 };
  const ctx = await browser.newContext({ viewport: vp, recordVideo: { dir: `clips/tmp-${id}`, size: vp } });
  await ctx.addInitScript(CURSOR);
  const page = await ctx.newPage();
  const t0 = Date.now();
  const now = () => (Date.now() - t0) / 1000;
  await page.goto(`${APP}/go?as=${persona}&next=${encodeURIComponent(path)}&code=${encodeURIComponent(CODE)}`);
  await page.waitForURL((u) => !u.pathname.startsWith("/go"), { timeout: 30000 });
  await pause(page, 2.5);
  const marks = { start: now(), fast: [] };
  const fast = async (waitFn) => { const a = now(); await waitFn(); marks.fast.push([a, now()]); };
  await page.mouse.move(vp.width * 0.55, vp.height * 0.45);
  await fn(page, fast);
  marks.end = now();
  const video = page.video();
  await ctx.close();
  fs.copyFileSync(await video.path(), `clips/${id}.webm`);
  fs.writeFileSync(`clips/${id}.json`, JSON.stringify(marks));
  console.log(id, JSON.stringify(marks));
}

if (!only) console.log("reset", JSON.stringify(await admin("reset")));
if (!only) await new Promise((r) => setTimeout(r, 45000)); // let the seeded alert reviews finish

await scene("05-home", { persona: "john", path: "/patient" }, async (page) => {
  await pause(page, 1.5);
  await moveTo(page, page.getByText("ALT (liver enzyme)").first(), 1.2);
  await scroll(page, 330, 2);
  await page.mouse.move(420, 420, { steps: 30 });
  await page.mouse.move(620, 380, { steps: 40 });
  await pause(page, 2);
  await page.mouse.move(1000, 420, { steps: 30 });
  await pause(page, 2);
  await scroll(page, 500, 2.5);
  await pause(page, 1.5);
  await scroll(page, 600, 2.5);
  await moveTo(page, page.getByText("My care plan").first(), 2.5);
});

await scene("06-assistant", { persona: "john", path: "/patient/assistant" }, async (page, fast) => {
  await pause(page, 1);
  await click(page, page.getByText("Why is my ALT high and what should I eat?").first());
  await pause(page, 2.5);
  await fast(() => waitForAnswer(page, page));
  await pause(page, 1.5);
  const chip = page.getByText(/· v\d/).first();
  await moveTo(page, chip, 3);
});

await scene("07-upload", { persona: "john", path: "/patient/upload" }, async (page, fast) => {
  await pause(page, 1);
  await moveTo(page, page.getByText("Choose a PDF or photo of your report"), 0.8);
  await page.locator('input[type="file"]').setInputFiles(SAMPLE);
  await pause(page, 1.2);
  await click(page, page.getByRole("button", { name: /Read report/ }));
  await pause(page, 1.5);
  await fast(() => page.getByText("Please check these values").waitFor({ timeout: 90000 }));
  await pause(page, 1);
  await scroll(page, 300, 2);
  await pause(page, 2);
  await click(page, page.getByRole("button", { name: /These values are correct/ }));
  await page.getByText(/Saved \d+ values/).waitFor({ timeout: 30000 });
  await pause(page, 3);
});

await scene("08-alert", { persona: "dr-patel", path: "/clinician" }, async (page, fast) => {
  await pause(page, 2.5);
  admin("inject-labs");
  const john = page.locator('a[href="/clinician/patients/john-miller"]').last();
  await john.waitFor({ timeout: 30000 });
  await pause(page, 1);
  await moveTo(page, john, 2);
  await fast(() => john.getByText("AI review ready").waitFor({ timeout: 120000 }));
  await pause(page, 3);
});

await scene("09-coordinator", { persona: "coordinator", path: "/clinician" }, async (page) => {
  await pause(page, 1.5);
  await click(page, page.locator('a[href="/clinician/patients/john-miller"]').last());
  await page.getByText("Awaiting physician approval").waitFor({ timeout: 30000 });
  await pause(page, 2);
  await scroll(page, 450, 3);
  await pause(page, 1);
  await moveTo(page, page.getByText("Awaiting physician approval"), 2);
  await click(page, page.getByRole("button", { name: "Acknowledge" }));
  await pause(page, 3);
});

await scene("10-physician", { persona: "dr-patel", path: "/clinician/patients/john-miller" }, async (page, fast) => {
  await page.getByText("COPILOT REVIEW", { exact: false }).first().waitFor({ timeout: 30000 }).catch(() => {});
  await pause(page, 1.5);
  await page.mouse.move(400, 250, { steps: 25 });
  await scroll(page, 260, 2.5);
  await pause(page, 2.5);
  await scroll(page, -260, 1.5);
  const input = page.getByPlaceholder("Ask the Copilot…");
  await typeIn(page, input, "What changed in the last 90 days?");
  await page.keyboard.press("Enter");
  await pause(page, 3);
  const panel = page.locator("div").filter({ has: input }).last();
  await fast(() => waitForAnswer(page, page.locator("body")));
  await pause(page, 1);
  await moveTo(page, page.locator(".md").last(), 3);
});

await scene("11-approve", { persona: "dr-patel", path: "/clinician/patients/john-miller" }, async (page, fast) => {
  await pause(page, 1);
  const boxes = page.locator('input[type="checkbox"]');
  await moveTo(page, page.getByText(/Proposed care-plan actions/i), 1);
  await scroll(page, 200, 1.5);
  await click(page, boxes.last());
  await pause(page, 1);
  await typeIn(page, page.getByPlaceholder("Add an action…"), "Repeat liver panel in 4 weeks");
  await click(page, page.getByRole("button", { name: /Add$/ }));
  await pause(page, 1.2);
  await click(page, page.getByRole("button", { name: /Approve & notify patient/ }));
  await fast(() => page.getByRole("button", { name: /Approve & notify patient/ }).waitFor({ state: "detached", timeout: 60000 }));
  await pause(page, 1.5);
  await moveTo(page, page.getByText("Care plan", { exact: true }).first(), 3);
});

await scene("12-followup", { persona: "john", path: "/patient/updates", phone: true }, async (page) => {
  await pause(page, 2.5);
  await page.mouse.move(200, 300, { steps: 20 });
  await pause(page, 2);
  await click(page, page.getByRole("link", { name: /Home/ }).last());
  await page.getByText("My care plan").waitFor();
  await pause(page, 0.5);
  await scroll(page, 1400, 2.5);
  await moveTo(page, page.getByText("My care plan").first(), 3);
});

await scene("13-redflag", { persona: "john", path: "/patient/assistant", phone: true }, async (page) => {
  await pause(page, 1.5);
  await typeIn(page, page.getByPlaceholder("Ask a question…"), "My eyes look yellow today");
  await page.keyboard.press("Enter");
  await page.getByText(/alerted your care team/).waitFor({ timeout: 30000 });
  await pause(page, 1);
  await moveTo(page, page.getByText(/This could be serious/).first(), 4);
});

await scene("13b-redflag-queue", { persona: "dr-patel", path: "/clinician" }, async (page) => {
  await pause(page, 0.5);
  await moveTo(page, page.getByText(/Patient-reported symptom/).first(), 4.5);
});

await scene("14-governance", { persona: "dr-patel", path: "/clinician/governance" }, async (page) => {
  await pause(page, 2);
  await page.mouse.move(500, 400, { steps: 25 });
  await scroll(page, 500, 3);
  await pause(page, 1.5);
  await scroll(page, 700, 3);
  await pause(page, 2);
});

await browser.close();
