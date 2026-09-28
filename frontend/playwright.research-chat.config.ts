import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e", testMatch: "research-chat.spec.ts", workers: 1, timeout: 30_000,
  outputDir: "./test-results/research-chat",
  use: { baseURL: "http://127.0.0.1:4197", screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: [
    { command: '"F:/software/programme/Anaconda/envs/med-research-ai/python.exe" -m uvicorn tests.modules.unified_conversation.browser_app:app --host 127.0.0.1 --port 8197',
      cwd: "..", env: { PYTHONPATH: "" }, url: "http://127.0.0.1:8197/api/v1/unified-conversations/capabilities", timeout: 60_000, reuseExistingServer: false },
    { command: "npm run dev -- --host 127.0.0.1 --port 4197", env: { VITE_API_PROXY: "http://127.0.0.1:8197" },
      url: "http://127.0.0.1:4197", timeout: 30_000, reuseExistingServer: false },
  ],
});
