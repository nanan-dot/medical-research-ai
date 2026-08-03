<script setup lang="ts">
import type { WritingProject } from "../../types/research-prototype";
defineProps<{ projects: WritingProject[] }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>

<template><section class="project-grid"><article v-for="project in projects" :key="project.id" class="project"><p class="eyebrow">{{ project.type }} · MOCK</p><h2>{{ project.title }}</h2><p>版本：{{ project.version }} · 最后修改：{{ project.updatedAt }}</p><footer><span class="origin">来源：{{ project.origin }}</span><button @click="emit('open', project.id)">打开草稿</button></footer></article><article class="project new"><p class="eyebrow">LOCAL DRAFT</p><h2>新建写作项目</h2><p>仅创建本地原型草稿，不会生成论文内容。</p><button>选择类型（原型）</button></article></section></template>

<style scoped>.project-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem;margin-top:1rem}.project{display:flex;min-height:180px;flex-direction:column;padding:1rem 1.1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.project h2{margin:.4rem 0;font-size:1.16rem}.project>p:not(.eyebrow){color:var(--text-muted);line-height:1.5}.project footer{display:flex;justify-content:space-between;gap:.5rem;align-items:center;margin-top:auto}.origin{color:var(--text-muted);font-size:.8rem}.project button{border:1px solid var(--border-strong);border-radius:6px;padding:.45rem .6rem;background:var(--paper);font-weight:700}.new{border-style:dashed;background:var(--surface-muted)}@media(max-width:900px){.project-grid{grid-template-columns:1fr}}</style>
