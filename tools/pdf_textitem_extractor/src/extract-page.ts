import type { PDFPageProxy } from "pdfjs-dist/types/src/display/api.js";
import { OPS } from "pdfjs-dist/legacy/build/pdf.mjs";
import { recordHash } from "./checksum.js";
import { textItemSchema, styleSchema, type Config } from "./contract.js";

export async function extractPage(page: PDFPageProxy, config: Config): Promise<object> {
  // 与现有阅读器 getTextContent() 的规范化默认值一致；过滤标记对象后 item 顺序保持一致。
  const content = await page.getTextContent({ includeMarkedContent: true, disableNormalization: false });
  const items = [];
  for (const [sourceIndex, item] of content.items.entries()) {
    if (!("str" in item)) continue;
    if (items.length >= config.max_items_per_page || item.str.length > config.max_item_characters) {
      throw new Error("RESOURCE_LIMIT_EXCEEDED");
    }
    items.push(textItemSchema.parse({ item_index: items.length, source_array_index: sourceIndex,
      text: item.str, direction: item.dir, transform: item.transform, width: item.width,
      height: item.height, font_name: item.fontName || null, has_eol: item.hasEOL }));
  }
  if (Object.keys(content.styles).length > 4096) throw new Error("RESOURCE_LIMIT_EXCEEDED");
  const styles = Object.fromEntries(Object.entries(content.styles).map(([key, value]) => {
    if (key.length > 256 || !key.isWellFormed()) throw new Error("INVALID_ARGUMENT");
    // PDF.js 对 Symbol 等无度量字体用 NaN 表示“未知”；协议使用显式 null，几何 NaN 仍拒绝。
    return [key, styleSchema.parse({ font_family: value.fontFamily,
      ascent: Number.isNaN(value.ascent) ? null : value.ascent ?? null,
      descent: Number.isNaN(value.descent) ? null : value.descent ?? null, vertical: value.vertical ?? false })];
  }));
  // 只读取绘图操作以区分空白与栅格扫描；不执行 PDF 动作、脚本或附件。
  const operators = await page.getOperatorList();
  const imageOps = new Set([OPS.paintImageXObject, OPS.paintInlineImageXObject, OPS.paintImageMaskXObject]);
  const viewport = page.getViewport({ scale: 1 });
  const record = { record_type: "page", page_number: page.pageNumber, width: viewport.width,
    height: viewport.height, rotation: viewport.rotation, view_box: page.view, items, styles,
    has_raster_image: operators.fnArray.some(op => imageOps.has(op)) };
  page.cleanup();
  return { ...record, page_content_hash: recordHash(record) };
}
