import { shallowRef, type ShallowRef } from "vue";

import type { SearchMode } from "../types/searchEntry";

const STORAGE_KEY = "rag-medicine.search-question-history.v1";
const MAX_HISTORY_ITEMS = 12;

export interface SearchQuestionHistoryEntry {
  question: string;
  mode: SearchMode;
  usedAt: string;
}

function isHistoryEntry(value: unknown): value is SearchQuestionHistoryEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as Partial<SearchQuestionHistoryEntry>;
  return typeof entry.question === "string" && typeof entry.mode === "string" && typeof entry.usedAt === "string";
}

function loadHistory(): SearchQuestionHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed.filter(isHistoryEntry).slice(0, MAX_HISTORY_ITEMS) : [];
  } catch {
    return [];
  }
}

function persistHistory(entries: readonly SearchQuestionHistoryEntry[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // 浏览器禁用本地存储时仍允许正常检索，只是不跨刷新保存历史。
  }
}

/** 管理本设备最近成功创建的检索问题，供入口页快速回填。 */
export function useSearchQuestionHistory(): {
  historyQuestions: Readonly<ShallowRef<readonly SearchQuestionHistoryEntry[]>>;
  rememberQuestion: (question: string, mode: SearchMode) => void;
} {
  const historyQuestions = shallowRef<readonly SearchQuestionHistoryEntry[]>(loadHistory());

  function rememberQuestion(question: string, mode: SearchMode): void {
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) return;
    const nextEntry: SearchQuestionHistoryEntry = {
      question: normalizedQuestion,
      mode,
      usedAt: new Date().toISOString(),
    };
    const nextHistory = [
      nextEntry,
      ...historyQuestions.value.filter((entry) => entry.question !== normalizedQuestion),
    ].slice(0, MAX_HISTORY_ITEMS);
    historyQuestions.value = nextHistory;
    persistHistory(nextHistory);
  }

  return { historyQuestions, rememberQuestion };
}
