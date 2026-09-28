import { apiRequest } from "./client";
import type { AnchorVersion, SelectionPage, SourceAnchor, SourceAnchorDescriptor } from "../types/sourceAnchors";

export interface AnchoredReadingNote { id: number; source_anchor_id: number; resolved_source_anchor_id?: number | null; content: string; quote: string; created_at: string }

export const sourceAnchorsApi = {
  notes(documentId: number): Promise<AnchoredReadingNote[]> {
    return apiRequest(`/documents/${documentId}/reading-notes`);
  },
  saveNote(documentId: number, descriptor: SourceAnchorDescriptor, content: string, key: string): Promise<AnchoredReadingNote> {
    return apiRequest(`/documents/${documentId}/reading-notes`, { method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify({ anchor_descriptor: descriptor, content }) });
  },
  async version(documentId: number, fileHash: string): Promise<AnchorVersion> {
    const [anchor, layout] = await Promise.all([
      apiRequest<{ revision: { id: number; file_hash: string; state: string } | null }>(`/documents/${documentId}/anchor-manifest`),
      apiRequest<{ segmentation: { id: number; anchor_revision_id: number; state: string } | null }>(`/documents/${documentId}/segmentation-manifest`),
    ]);
    if (!anchor.revision || !layout.segmentation || anchor.revision.file_hash !== fileHash ||
        layout.segmentation.anchor_revision_id !== anchor.revision.id ||
        !["ready", "review_required"].includes(anchor.revision.state)) {
      throw new Error("原文锚点层尚未就绪，请先完成 A0/A1 处理。");
    }
    return { expected_file_hash: fileHash, expected_anchor_revision_id: anchor.revision.id,
      expected_segmentation_revision_id: layout.segmentation.id };
  },
  page(documentId: number, page: number, version: AnchorVersion, signal?: AbortSignal): Promise<SelectionPage> {
    const query = new URLSearchParams(Object.entries(version).map(([key, value]) => [key, String(value)]));
    return apiRequest<SelectionPage>(`/documents/${documentId}/selection-pages/${page}?${query}`, { signal });
  },
  get(anchorId: number): Promise<SourceAnchor> {
    return apiRequest<SourceAnchor>(`/source-anchors/${anchorId}`);
  },
};
