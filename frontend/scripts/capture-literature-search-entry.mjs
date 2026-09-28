import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { setTimeout as wait } from "node:timers/promises";
import WebSocket from "ws";

const edgePath = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.ENTRY_CAPTURE_URL ?? "http://127.0.0.1:5173";
const outputDirectory = "D:\\AI_project\\rag_medicine\\docs\\frontend-rebuild\\screenshots\\literature-search-entry";
const debugPort = 9228;
const viewports = [[1536, 1024], [1440, 900], [1280, 800], [1024, 768], [768, 1024], [390, 844]];
const requiredSelectors = ["h1", ".process", ".question-card", "textarea", "[role=radiogroup]", ".submit", ".quick", ".trust"];

function send(socket, messageId, method, params = {}) {
  return new Promise((resolve, reject) => {
    const onMessage = (raw) => {
      const message = JSON.parse(raw.toString());
      if (message.id !== messageId) return;
      socket.off("message", onMessage);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    };
    socket.on("message", onMessage);
    socket.send(JSON.stringify({ id: messageId, method, params }));
  });
}

async function getDebuggerTarget() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find((target) => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch { /* Browser not ready yet. */ }
    await wait(200);
  }
  throw new Error("Edge DevTools endpoint did not become ready.");
}

async function captureViewport(width, height) {
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--force-device-scale-factor=1", "--remote-debugging-port=" + debugPort, "about:blank"], { windowsHide: true });
  try {
    const target = await getDebuggerTarget();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.once("open", resolve); socket.once("error", reject); });
    let id = 0;
    const command = (method, params) => send(socket, ++id, method, params);
    const failures = []; const consoleErrors = []; const pageErrors = [];
    socket.on("message", (raw) => { const message = JSON.parse(raw.toString()); if (message.method === "Network.loadingFailed") failures.push(message.params.errorText); if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") consoleErrors.push(message.params.args.map((item) => item.value ?? item.description).join(" ")); if (message.method === "Runtime.exceptionThrown") pageErrors.push(message.params.exceptionDetails.text); });
    await command("Page.enable"); await command("Runtime.enable"); await command("Network.enable");
    await command("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    await command("Page.navigate", { url: `${baseUrl}/literature-search` });
    for (let attempt = 0; attempt < 50; attempt += 1) {
      const check = await command("Runtime.evaluate", { expression: `(${JSON.stringify(requiredSelectors)}).every((selector) => document.querySelector(selector)) && document.fonts.status === 'loaded'`, returnByValue: true });
      if (check.result.value) break;
      if (attempt === 49) throw new Error("Required entry-page locators were not ready.");
      await wait(100);
    }
    // AppShell's route transition has finished before capture, avoiding a semi-transparent entering frame.
    await wait(250);
    await command("Runtime.evaluate", { expression: "document.documentElement.classList.add('visual-capture')" });
    const geometry = await command("Runtime.evaluate", { expression: `Object.fromEntries(${JSON.stringify(requiredSelectors)}.map((selector) => { const rect = document.querySelector(selector).getBoundingClientRect(); return [selector, { x: rect.x, y: rect.y, width: rect.width, height: rect.height }]; }))`, returnByValue: true });
    const screenshot = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(`${outputDirectory}/entry-${width}x${height}.png`, Buffer.from(screenshot.data, "base64"));
    if (width === 1536) {
      await writeFile(`${outputDirectory}/navigation-desktop-expanded.png`, Buffer.from(screenshot.data, "base64"));
      await command("Runtime.evaluate", {
        expression: `(() => {
          const toggle = document.querySelector("button[aria-controls='literature-subnav']");
          const pathname = location.pathname;
          toggle?.click();
          return pathname;
        })()`,
        returnByValue: true,
      });
      await wait(50);
      const toggleState = await command("Runtime.evaluate", {
        expression: `({
          pathname: location.pathname,
          expanded: document.querySelector("button[aria-controls='literature-subnav']")?.getAttribute("aria-expanded"),
          subnav: Boolean(document.querySelector("#literature-subnav")),
        })`,
        returnByValue: true,
      });
      if (toggleState.result.value?.pathname !== "/literature-search" || toggleState.result.value?.expanded !== "false" || toggleState.result.value?.subnav) {
        throw new Error("Literature navigation toggle changed the route or did not collapse the four-item menu.");
      }
      const collapsedNavigation = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      await writeFile(`${outputDirectory}/navigation-desktop-collapsed.png`, Buffer.from(collapsedNavigation.data, "base64"));
    }
    socket.close();
    if (failures.length || consoleErrors.length || pageErrors.length) throw new Error(JSON.stringify({ failures, consoleErrors, pageErrors }));
    return { viewport: `${width}x${height}`, geometry: geometry.result.value };
  } finally { browser.kill(); }
}

await mkdir(outputDirectory, { recursive: true });
const reports = [];
for (const [width, height] of viewports) reports.push(await captureViewport(width, height));
await writeFile(`${outputDirectory}/geometry-report.json`, JSON.stringify({ reports }, null, 2));
