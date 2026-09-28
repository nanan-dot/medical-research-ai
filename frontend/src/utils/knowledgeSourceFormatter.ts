import type { KnowledgeSourceHealth, KnowledgeSourceType } from "../api/knowledgeSources";
export const SOURCE_TYPE_LABEL: Record<KnowledgeSourceType, string> = { local_folder: "本地文件夹", obsidian_vault: "Obsidian Vault", temporary_import: "临时导入" };
export const HEALTH_LABEL: Record<KnowledgeSourceHealth, string> = { ready: "全部可用", syncing: "同步中", needs_attention: "需要处理", paused: "已暂停", unavailable: "不可访问" };
export function formatPercent(value: number | null): string { return value === null ? "—" : `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`; }
export function formatDate(value: string | null): string { return value ? new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", month: "numeric", day: "numeric" }).format(new Date(value)) : "尚未同步"; }
