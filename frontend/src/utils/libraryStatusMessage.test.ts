import { expect, test } from "vitest";

import { libraryStatusMessage } from "./libraryStatusMessage";

test("uses Chinese, status-based confirmation messages for saved literature", () => {
  expect(libraryStatusMessage("metadata_only")).toBe("已加入知识库；未发现本地 PDF 或已核验的开放获取全文。");
  expect(libraryStatusMessage("local_pdf_available")).toBe("已加入知识库；已关联本地全文。");
  expect(libraryStatusMessage("open_access_available")).toBe("已加入知识库；可访问已核验的开放获取全文。");
  expect(libraryStatusMessage("unavailable")).toBe("已加入知识库；全文目前不可用。");
});
