// Real local acceptance runner. It never intercepts API calls or imports a fixture.
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import WebSocket from "ws";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.REAL_FLOW_URL ?? "http://127.0.0.1:5175";
const output = "D:\\AI_project\\rag_medicine\\docs\\frontend-rebuild\\screenshots\\literature-search-workspace-v2";
const question = "间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？";
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function target(port) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = pages.find((item) => item.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch {}
    await sleep(150);
  }
  throw new Error("Edge DevTools unavailable");
}

function command(socket, id, method, params = {}) {
  return new Promise((resolve, reject) => {
    const listener = (raw) => {
      const message = JSON.parse(raw);
      if (message.id !== id.value) return;
      socket.off("message", listener);
      if (message.error) {
        reject(new Error(message.error.message));
      } else {
        resolve(message.result);
      }
    };
    socket.on("message", listener);
    socket.send(JSON.stringify({ id: ++id.value, method, params }));
  });
}

async function waitFor(cdp, expression, label) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const response = await cdp("Runtime.evaluate", { expression, returnByValue: true });
    if (response.result?.value) return response.result.value;
    await sleep(150);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

const profileDir = await mkdtemp(join(tmpdir(), "rag-medicine-real-flow-"));
const browser = spawn(edge, [
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--force-device-scale-factor=1",
  `--user-data-dir=${profileDir}`,
  "--remote-debugging-port=9444",
  "about:blank",
], { windowsHide: true });

try {
  await mkdir(output, { recursive: true });
  const page = await target(9444);
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.once("open", resolve); socket.once("error", reject); });
  const id = { value: 0 };
  const cdp = (method, params) => command(socket, id, method, params);
  const errors = [];
  socket.on("message", (raw) => {
    const message = JSON.parse(raw);
    if (message.method === "Runtime.exceptionThrown") errors.push(message.params.exceptionDetails.text);
    if (message.method === "Log.entryAdded" && message.params.entry.level === "error") errors.push(message.params.entry.text);
  });

  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Log.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1536, height: 1024, deviceScaleFactor: 1, mobile: false });
  await cdp("Page.navigate", { url: `${baseUrl}/literature-search` });
  await waitFor(cdp, "Boolean(document.querySelector('textarea') && document.querySelector('.submit'))", "entry controls");
  await cdp("Runtime.evaluate", {
    expression: `(() => { const input = document.querySelector('textarea'); input.value = ${JSON.stringify(question)}; input.dispatchEvent(new Event('input', { bubbles: true })); })()`,
  });
  await waitFor(cdp, "!document.querySelector('.submit').disabled", "enabled entry submission");
  await cdp("Runtime.evaluate", { expression: "document.querySelector('.submit').click()" });
  const workspaceUrl = await waitFor(cdp, "location.pathname === '/literature-search/workspace' && new URLSearchParams(location.search).get('strategy_id')", "strategy workspace navigation");
  await waitFor(cdp, "Boolean(document.querySelector('.terms-mesh-section') && document.querySelector('.strategy-query') && document.querySelector('.strategy-sticky'))", "persisted workspace content");
  await cdp("Runtime.evaluate", { expression: "document.fonts.ready" });
  const firstState = await cdp("Runtime.evaluate", {
    expression: `(() => ({
      url: location.href,
      journey: document.querySelector('[aria-current="step"]')?.parentElement?.innerText ?? '',
      terms: document.querySelectorAll('.concept-group').length,
      mesh: document.querySelectorAll('.mesh-list > li').length,
      query: document.querySelector('.strategy-query textarea')?.value ?? '',
      researchQuestion: document.querySelector('.strategy-basis .question p')?.textContent?.trim() ?? '',
      pico: [...document.querySelectorAll('.strategy-basis .intent-grid article p')].map((element) => element.textContent?.trim() ?? ''),
      sidebar: (() => { const sidebar = document.querySelector('.sidebar'); const rect = sidebar?.getBoundingClientRect(); return { present: Boolean(sidebar), width: rect?.width ?? 0, visible: Boolean(rect && rect.width >= 220 && rect.left === 0) }; })(),
      executeButtons: [...document.querySelectorAll('button')].filter((button) => button.textContent.includes('开始检索')).map((button) => ({ className: button.className, disabled: button.disabled })),
      headerHasExecute: document.querySelector('.search-center-header')?.textContent.includes('开始检索') ?? false,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))()`,
    returnByValue: true,
  });
  const firstShot = await cdp("Page.captureScreenshot", { format: "png" });
  await writeFile(`${output}/workspace-real-flow-1536x1024.png`, Buffer.from(firstShot.data, "base64"));

  await cdp("Emulation.setDeviceMetricsOverride", { width: 2560, height: 1259, deviceScaleFactor: 1, mobile: false });
  await cdp("Runtime.evaluate", { expression: "window.scrollTo(0, 0)" });
  await sleep(150);
  const wideShot = await cdp("Page.captureScreenshot", { format: "png" });
  await writeFile(`${output}/workspace-real-flow-2560x1259.png`, Buffer.from(wideShot.data, "base64"));

  await cdp("Emulation.setDeviceMetricsOverride", { width: 1536, height: 1024, deviceScaleFactor: 1, mobile: false });

  await cdp("Page.reload", { ignoreCache: true });
  await waitFor(cdp, "Boolean(document.querySelector('.terms-mesh-section') && document.querySelector('.strategy-query'))", "workspace refresh persistence");
  const refreshState = await cdp("Runtime.evaluate", {
    expression: `(() => ({
      url: location.href,
      terms: document.querySelectorAll('.concept-group').length,
      mesh: document.querySelectorAll('.mesh-list > li').length,
      query: document.querySelector('.strategy-query textarea')?.value ?? '',
      researchQuestion: document.querySelector('.strategy-basis .question p')?.textContent?.trim() ?? '',
      sidebar: (() => { const sidebar = document.querySelector('.sidebar'); const rect = sidebar?.getBoundingClientRect(); return { present: Boolean(sidebar), width: rect?.width ?? 0, visible: Boolean(rect && rect.width >= 220 && rect.left === 0) }; })(),
      executeButtons: [...document.querySelectorAll('button')].filter((button) => button.textContent.includes('开始检索')).length,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))()`,
    returnByValue: true,
  });
  const refreshedShot = await cdp("Page.captureScreenshot", { format: "png" });
  await writeFile(`${output}/workspace-real-flow-refresh-1536x1024.png`, Buffer.from(refreshedShot.data, "base64"));
  socket.close();

  const report = { visualTestOnly: false, question, workspaceStrategyId: workspaceUrl, first: firstState.result.value, refreshed: refreshState.result.value, errors };
  await writeFile(`${output}/real-flow-acceptance.json`, JSON.stringify(report, null, 2));
  if (firstState.result.value.terms < 3 || !firstState.result.value.query || firstState.result.value.researchQuestion !== question || firstState.result.value.pico.filter(Boolean).length < 3 || !firstState.result.value.sidebar.visible || firstState.result.value.executeButtons.length !== 1 || firstState.result.value.headerHasExecute) {
    throw new Error(`Unexpected real workspace state: ${JSON.stringify(firstState.result.value)}`);
  }
  if (refreshState.result.value.terms < 3 || !refreshState.result.value.query || refreshState.result.value.researchQuestion !== question || !refreshState.result.value.sidebar.visible || refreshState.result.value.executeButtons !== 1) {
    throw new Error(`Workspace did not persist after refresh: ${JSON.stringify(refreshState.result.value)}`);
  }
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} finally {
  browser.kill();
  // Edge releases Crashpad files asynchronously on Windows. Cleanup must not
  // turn an otherwise successful acceptance run into a false failure.
  await sleep(500);
  await rm(profileDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 250 }).catch(() => undefined);
}
