// 对照现有阅读器的实际 PDF.js 包与 getTextContent() 默认参数，不复用后端提取器。
import { readFile } from "node:fs/promises";
import { getDocument } from "../../../frontend/node_modules/pdfjs-dist/legacy/build/pdf.mjs";

const loading = getDocument({ data: new Uint8Array(await readFile(process.argv[2])), verbosity: 0 });
try {
  const document = await loading.promise;
  const pages = [];
  for (let number = 1; number <= document.numPages; number++) {
    const content = await (await document.getPage(number)).getTextContent();
    pages.push(content.items.filter(item => "str" in item).map(item => ({ text: item.str, transform: item.transform })));
  }
  process.stdout.write(JSON.stringify(pages));
} finally {
  await loading.destroy();
}
