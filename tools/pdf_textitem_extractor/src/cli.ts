import { argumentSchema, identity } from "./contract.js";
import { extractDocument } from "./extract-document.js";

const codes: Record<string, number> = { INVALID_ARGUMENT: 2, FILE_HASH_MISMATCH: 3, INVALID_PDF: 4,
  ENCRYPTED_PDF: 5, RESOURCE_LIMIT_EXCEEDED: 6, EXTRACTION_FAILED: 7, CONTRACT_WRITE_FAILED: 8 };

async function main(argv: string[]): Promise<void> {
  if (argv.length === 1 && argv[0] === "--version-json") {
    process.stdout.write(JSON.stringify(identity) + "\n");
    return;
  }
  if (argv[0] !== "extract" || argv.length !== 9) throw new Error("INVALID_ARGUMENT");
  const entries: Record<string, string> = {};
  for (let index = 1; index < argv.length; index += 2) {
    const key = argv[index], value = argv[index + 1];
    if (!key || !value || key in entries) throw new Error("INVALID_ARGUMENT");
    entries[key] = value;
  }
  await extractDocument(argumentSchema.parse(entries));
}

// 网络永不用于文档资源；PDF.js 字体/cmap/wasm 均来自锁版安装包。
globalThis.fetch = () => Promise.reject(new Error("EXTRACTION_FAILED"));
process.stdout.on("error", () => { process.exitCode = 8; });
main(process.argv.slice(2)).catch((error: unknown) => {
  let code = "EXTRACTION_FAILED";
  if (error instanceof Error) {
    if (error.message in codes) code = error.message;
    else if (error.name === "PasswordException") code = "ENCRYPTED_PDF";
    else if (error.name === "InvalidPDFException") code = "INVALID_PDF";
    else if (error.name === "ZodError") code = "INVALID_ARGUMENT";
  }
  process.stderr.write(JSON.stringify({ code }) + "\n");
  process.exitCode = codes[code] ?? 7;
});
