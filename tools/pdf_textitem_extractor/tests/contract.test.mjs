import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { canonicalJson, recordHash } from "../dist/checksum.js";
import { argumentSchema, configSchema, identity } from "../dist/contract.js";

test("canonical numbers preserve binary64 and normalize negative zero", () => {
  assert.equal(canonicalJson({ n: 1 }), '{"n":{"$f64":"3ff0000000000000"}}');
  assert.equal(recordHash({ n: -0 }), recordHash({ n: 0 }));
  assert.throws(() => canonicalJson({ n: NaN }));
  assert.throws(() => canonicalJson("\ud800"));
});

test("frontend and standalone PDF.js versions are exact and equal", async () => {
  const frontend = JSON.parse(await readFile(new URL("../../../frontend/package.json", import.meta.url)));
  const tool = JSON.parse(await readFile(new URL("../package.json", import.meta.url)));
  assert.equal(frontend.dependencies["pdfjs-dist"], identity.pdfjs_version);
  assert.equal(tool.dependencies["pdfjs-dist"], identity.pdfjs_version);
});

test("boundary rejects URL and unvalidated limits/options", () => {
  assert.equal(argumentSchema.safeParse({ "--input": "https://example.com/paper.pdf" }).success, false);
  assert.equal(configSchema.safeParse({ max_pages: 0 }).success, false);
});
