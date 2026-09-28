import { readFile, stat, open } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { once } from "node:events";
import * as pdfjs from "pdfjs-dist/legacy/build/pdf.mjs";
import { digest } from "./checksum.js";
import { configSchema, identity, type Arguments } from "./contract.js";
import { extractPage } from "./extract-page.js";

async function fileHash(path: string): Promise<string> {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(path)) hash.update(chunk);
  return hash.digest("hex");
}

export async function extractDocument(args: Arguments): Promise<void> {
  const input = args["--input"];
  if ((await stat(args["--options-file"])).size > 65536) throw new Error("INVALID_ARGUMENT");
  const config = configSchema.parse(JSON.parse(await readFile(args["--options-file"], "utf8")));
  if ((await stat(input)).size > config.max_file_bytes) throw new Error("RESOURCE_LIMIT_EXCEEDED");
  const file = await open(input, "r");
  let bytes: Buffer;
  try {
    bytes = await file.readFile();
  } finally {
    await file.close();
  }
  if (bytes.length > config.max_file_bytes) throw new Error("RESOURCE_LIMIT_EXCEEDED");
  if (digest(bytes) !== args["--expected-sha256"]) throw new Error("FILE_HASH_MISMATCH");
  if (bytes.subarray(0, 5).toString() !== "%PDF-") throw new Error("INVALID_PDF");
  let outputBytes = 0;
  async function write(record: object): Promise<void> {
    const line = JSON.stringify(record) + "\n";
    const size = Buffer.byteLength(line);
    outputBytes += size;
    if (size > config.max_line_bytes || outputBytes > config.max_output_bytes) throw new Error("RESOURCE_LIMIT_EXCEEDED");
    if (!process.stdout.write(line)) await once(process.stdout, "drain");
  }
  const packageRoot = new URL("../node_modules/pdfjs-dist/", import.meta.url);
  const loading = pdfjs.getDocument({ data: new Uint8Array(bytes), disableFontFace: true,
    useSystemFonts: false, useWorkerFetch: false, verbosity: 0,
    cMapUrl: fileURLToPath(new URL("cmaps/", packageRoot)).replaceAll("\\", "/"), cMapPacked: true,
    standardFontDataUrl: fileURLToPath(new URL("standard_fonts/", packageRoot)).replaceAll("\\", "/"),
    wasmUrl: fileURLToPath(new URL("wasm/", packageRoot)).replaceAll("\\", "/"),
  });
  try {
    const document = await loading.promise;
    if (document.numPages > config.max_pages) throw new Error("RESOURCE_LIMIT_EXCEEDED");
    const permissions = await document.getPermissions();
    if (permissions && !permissions.includes(pdfjs.PermissionFlag.COPY)) throw new Error("ENCRYPTED_PDF");
    await write({ record_type: "header", ...identity, request_id: args["--request-id"],
      file_sha256: args["--expected-sha256"], page_count: document.numPages });
    const hashes: string[] = [];
    let count = 0;
    for (let number = 1; number <= document.numPages; number += 1) {
      const record = await extractPage(await document.getPage(number), config);
      if (!("items" in record) || !Array.isArray(record.items) || !("page_content_hash" in record) || typeof record.page_content_hash !== "string") {
        throw new Error("EXTRACTION_FAILED");
      }
      hashes.push(record.page_content_hash);
      count += record.items.length;
      await write(record);
    }
    if (await fileHash(input) !== args["--expected-sha256"]) throw new Error("FILE_HASH_MISMATCH");
    await write({ record_type: "trailer", request_id: args["--request-id"], pages_emitted: document.numPages,
      items_emitted: count, document_content_hash: digest(hashes.join("|")), completed: true });
  } finally {
    await loading.destroy();
  }
}
