import type { FulltextStatus } from "../api/literatureSearch";

const messages: Record<FulltextStatus, string> = {
  metadata_only: "已加入知识库；未发现本地 PDF 或已核验的开放获取全文。",
  local_pdf_available: "已加入知识库；已关联本地全文。",
  open_access_available: "已加入知识库；可访问已核验的开放获取全文。",
  unavailable: "已加入知识库；全文目前不可用。",
};

export function libraryStatusMessage(status: FulltextStatus): string {
  return messages[status];
}
