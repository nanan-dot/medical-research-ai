<script setup lang="ts">
import { useRouter } from "vue-router";
import WritingProjectList from "../../components/writing/WritingProjectList.vue";
import { writingProjects } from "../../mocks/research-prototype";
const router = useRouter();
</script>

<template><main class="page"><header class="page-header"><div><p class="eyebrow">WRITING PROJECTS · MOCK</p><h1>写作项目</h1><p>写作草稿与材料来源分开呈现；未接入的引用、原文证据和 AI 使用记录不会被伪造成已完成。</p></div><button class="primary">+ 新建项目（原型）</button></header><div class="notice"><strong>本地原型边界</strong><span>项目内容只保存在当前前端状态；不调用后端，也不生成学术文本。</span></div><WritingProjectList :projects="writingProjects" @open="router.push(`/writing/${$event}`)"/></main></template>

<style scoped>.page{padding:2rem 1.4rem;max-width:1400px}.page-header{display:flex;justify-content:space-between;gap:1rem;align-items:start}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.page-header h1{margin:.25rem 0;font-size:2.3rem}.page-header p:last-child{max-width:720px;color:var(--text-muted);line-height:1.6}.primary{border:0;border-radius:7px;padding:.6rem .8rem;background:var(--color-primary);color:#fff;font-weight:800}.notice{display:flex;gap:.8rem;margin-top:1rem;padding:.7rem .85rem;border-radius:6px;background:var(--color-warning-soft);color:var(--color-warning)}@media(max-width:720px){.page-header{display:block}.page-header .primary{margin-top:.8rem}.notice{display:block}.notice span{display:block;margin-top:.25rem}}</style>
