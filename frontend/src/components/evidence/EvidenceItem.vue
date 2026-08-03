<script setup lang="ts">
export type EvidenceKind = "paper" | "user_note" | "user_data" | "model_summary" | "model_inference" | "pending";
export interface EvidenceItemModel { id: number | string; title: string | null; excerpt: string | null; page: number | null; section: string | null; kind: EvidenceKind; support?: "direct" | "summary" | "inference" | "missing"; }
defineProps<{ item: EvidenceItemModel }>();
const emit = defineEmits<{ open: [item: EvidenceItemModel] }>();
const labels: Record<EvidenceKind, string> = { paper: "论文", user_note: "用户笔记", user_data: "用户数据", model_summary: "模型总结", model_inference: "模型推断", pending: "待确认" };
</script>
<template><button class="evidence" type="button" @click="emit('open', item)"><span class="kind">{{ labels[item.kind] }}</span><strong>{{ item.title || "来源未提供" }} · 第 {{ item.page ?? "未提供" }} 页</strong><span>章节：{{ item.section || "未提供" }}</span><small>{{ item.excerpt || "原文摘录未提供" }}</small></button></template>
<style scoped>.evidence{display:grid;gap:.35rem;width:100%;padding:.85rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper);color:var(--text-primary);text-align:left}.evidence:hover{border-color:var(--color-primary)}.kind{width:max-content;padding:.15rem .4rem;border-radius:99px;background:var(--color-primary-soft);color:var(--color-primary);font-size:.7rem;font-weight:800}.evidence span:not(.kind),small{color:var(--text-muted);font-size:.78rem}</style>
