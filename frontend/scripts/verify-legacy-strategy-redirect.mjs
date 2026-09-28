import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import WebSocket from "ws";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const profile = await mkdtemp(join(tmpdir(), "rag-medicine-legacy-redirect-"));
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function findPage() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const targets = await (await fetch("http://127.0.0.1:9455/json")).json();
      const page = targets.find((target) => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch {}
    await sleep(100);
  }
  throw new Error("Edge DevTools unavailable");
}

const browser = spawn(edge, [
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  `--user-data-dir=${profile}`,
  "--remote-debugging-port=9455",
  "about:blank",
], { windowsHide: true });

try {
  const page = await findPage();
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.once("open", resolve);
    socket.once("error", reject);
  });
  let commandId = 0;
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++commandId;
    const listener = (raw) => {
      const message = JSON.parse(raw);
      if (message.id !== id) return;
      socket.off("message", listener);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    };
    socket.on("message", listener);
    socket.send(JSON.stringify({ id, method, params }));
  });

  await command("Page.enable");
  await command("Runtime.enable");
  await command("Page.navigate", {
    url: "http://127.0.0.1:5173/literature-search/workspace?strategy_id=25",
  });

  let state;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const result = await command("Runtime.evaluate", {
      expression: `(() => ({
        strategyId: new URLSearchParams(location.search).get('strategy_id'),
        question: document.querySelector('.strategy-basis .question p')?.textContent?.trim() ?? '',
        termGroups: document.querySelectorAll('.concept-group').length,
        meshTerms: document.querySelectorAll('.mesh-list > li').length,
        executeButtons: [...document.querySelectorAll('button')].filter((button) => button.textContent.includes('开始检索')).length,
      }))()`,
      returnByValue: true,
    });
    state = result.result.value;
    if (state.strategyId === "23" && state.termGroups >= 3 && state.meshTerms >= 3) break;
    await sleep(150);
  }
  socket.close();
  if (state.strategyId !== "23" || state.termGroups < 3 || state.meshTerms < 3 || state.executeButtons !== 1) {
    throw new Error(`Legacy strategy redirect failed: ${JSON.stringify(state)}`);
  }
  process.stdout.write(`${JSON.stringify(state, null, 2)}\n`);
} finally {
  browser.kill();
  await sleep(300);
  await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 }).catch(() => undefined);
}
