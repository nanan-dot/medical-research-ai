import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import WebSocket from "ws";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const output = "D:\\AI_project\\rag_medicine\\docs\\frontend-rebuild\\screenshots\\literature-search-workspace-v2";
const profile = await mkdtemp(join(tmpdir(), "rag-medicine-buttons-"));
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const expectedStrategy = await (await fetch("http://127.0.0.1:8000/api/v1/literature-search/strategies/latest-complete")).json();
const expectedStrategyId = String(expectedStrategy.id);

async function findPage() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const targets = await (await fetch("http://127.0.0.1:9466/json")).json();
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
  "--force-device-scale-factor=1",
  `--user-data-dir=${profile}`,
  "--remote-debugging-port=9466",
  "about:blank",
], { windowsHide: true });

try {
  await mkdir(output, { recursive: true });
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
  const evaluate = async (expression) => {
    const response = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
    return response.result.value;
  };
  const waitFor = async (expression, label) => {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const value = await evaluate(expression);
      if (value) return value;
      await sleep(150);
    }
    throw new Error(`Timed out waiting for ${label}`);
  };
  const clickButton = (label) => evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find((item) => item.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);

  await command("Page.enable");
  await command("Runtime.enable");
  await command("Emulation.setDeviceMetricsOverride", { width: 1536, height: 1024, deviceScaleFactor: 1, mobile: false });
  await command("Page.navigate", { url: "http://127.0.0.1:5173/literature-search/workspace?strategy_id=25" });
  await waitFor(`new URLSearchParams(location.search).get('strategy_id') === ${JSON.stringify(expectedStrategyId)} && document.querySelectorAll('.concept-group').length >= 3`, "legacy redirect");

  const checks = {};
  checks.redirect = await evaluate("location.href");
  checks.viewAllClicked = await clickButton("查看全部");
  checks.viewAllExpanded = await waitFor("[...document.querySelectorAll('button')].some((item) => item.textContent.trim() === '收起')", "expanded terms");

  checks.versionMenu = await evaluate(`(() => {
    const summary = document.querySelector('.strategy-sticky .version-selector');
    summary?.click();
    return Boolean(document.querySelector('.sticky-version-menu')?.open);
  })()`);

  checks.addOpened = await clickButton("添加术语");
  await waitFor("Boolean(document.querySelector('#strategy-new-term'))", "add term dialog");
  await evaluate(`(() => {
    const input = document.querySelector('#strategy-new-term');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, 'button acceptance term');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('.add-dialog form').requestSubmit();
  })()`);
  checks.termAdded = await waitFor("document.body.textContent.includes('10 个检索术语')", "persisted added term");

  checks.termMenuOpened = await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    group?.querySelector('summary')?.click();
    return Boolean(group?.querySelector('details')?.open);
  })()`);
  checks.termLocked = await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    const button = [...(group?.querySelectorAll('button') ?? [])].find((item) => item.textContent.trim() === '锁定首项');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  await waitFor("document.body.textContent.includes('1 个锁定词')", "locked term persistence");
  await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    group?.querySelector('summary')?.click();
  })()`);
  checks.termUnlocked = await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    const button = [...(group?.querySelectorAll('button') ?? [])].find((item) => item.textContent.trim() === '解锁首项');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  await waitFor("document.body.textContent.includes('0 个锁定词')", "unlocked term persistence");
  await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    group?.querySelector('summary')?.click();
  })()`);
  checks.termDeleted = await evaluate(`(() => {
    const group = [...document.querySelectorAll('.concept-group')].find((item) => item.textContent.includes('自定义'));
    const button = [...(group?.querySelectorAll('button') ?? [])].find((item) => item.textContent.trim() === '删除首项');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  await waitFor("document.body.textContent.includes('9 个检索术语')", "deleted term persistence");

  checks.remapClicked = await clickButton("重新映射术语");
  checks.remapReturned = await waitFor("![...document.querySelectorAll('button')].find((item) => item.textContent.trim() === '重新映射术语')?.disabled", "term remap completion");

  checks.versionCreated = await evaluate(`(() => {
    const button = [...document.querySelectorAll('.search-center-header button')].find((item) => item.textContent.includes('策略版本'));
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  checks.versionReturned = await waitFor("document.querySelector('.search-center-header button')?.textContent.includes('v')", "version persistence");

  checks.copyClicked = await clickButton("复制检索式");
  checks.validateClicked = await clickButton("验证");
  checks.validationReturned = await waitFor("document.querySelector('.validation')?.textContent.trim() !== '修改检索式后需重新验证。'", "strategy validation");
  checks.countClicked = await clickButton("刷新数量");
  checks.countReturned = await waitFor("!document.querySelector('.count button')?.disabled", "count request completion");

  const screenshot = await command("Page.captureScreenshot", { format: "png" });
  await writeFile(`${output}/workspace-buttons-accepted-1536x1024.png`, Buffer.from(screenshot.data, "base64"));

  checks.regenerateClicked = await clickButton("重新生成");
  checks.regenerateNavigated = await waitFor("location.pathname === '/literature-search' && new URLSearchParams(location.search).has('raw_topic')", "regenerate navigation");
  await command("Page.navigate", { url: `http://127.0.0.1:5173/literature-search/workspace?strategy_id=${expectedStrategyId}` });
  await waitFor("Boolean(document.querySelector('.limit-action'))", "workspace restored after regenerate check");
  checks.limitsClicked = await clickButton("查看 / 编辑");
  await sleep(700);
  checks.limitsLocation = await evaluate("location.href");
  checks.limitsNavigated = await evaluate("location.pathname === '/literature-search' && new URLSearchParams(location.search).has('raw_topic')");
  await command("Page.navigate", { url: `http://127.0.0.1:5173/literature-search/workspace?strategy_id=${expectedStrategyId}` });
  await waitFor("Boolean(document.querySelector('.strategy-sticky .execute'))", "workspace restored before execution");
  checks.executeClicked = await clickButton("开始检索 →");
  checks.executeCompleted = await waitFor("location.pathname.startsWith('/literature-search/results/') || Boolean(document.querySelector('[role=alert]'))", "search execution outcome");

  const required = ["viewAllClicked", "viewAllExpanded", "versionMenu", "addOpened", "termAdded", "termMenuOpened", "termLocked", "termUnlocked", "termDeleted", "remapClicked", "remapReturned", "versionCreated", "versionReturned", "copyClicked", "validateClicked", "validationReturned", "countClicked", "countReturned", "regenerateClicked", "regenerateNavigated", "limitsClicked", "limitsNavigated", "executeClicked", "executeCompleted"];
  const failed = required.filter((key) => !checks[key]);
  await writeFile(`${output}/button-acceptance.json`, JSON.stringify({ checks, failed }, null, 2));
  socket.close();
  if (failed.length) throw new Error(`Button checks failed: ${failed.join(', ')}`);
  process.stdout.write(`${JSON.stringify({ checks, failed }, null, 2)}\n`);
} finally {
  browser.kill();
  await sleep(300);
  await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 }).catch(() => undefined);
}
