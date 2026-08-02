<script setup lang="ts">
import { onMounted } from "vue";

import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";
import KnowledgeSourceList from "./KnowledgeSourceList.vue";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";

const { sources, loading, error, enabledCount, load, create, setEnabled, remove } =
  useKnowledgeSources();

onMounted(load);
</script>

<template>
  <section class="manager" aria-labelledby="manager-title">
    <header class="manager-header">
      <div>
        <p class="eyebrow">AUTHORIZED SOURCES</p>
        <h2 id="manager-title">知识源管理</h2>
      </div>
      <p class="summary">{{ sources.length }} 个来源 · {{ enabledCount }} 个启用</p>
    </header>
    <KnowledgeSourceForm :disabled="loading" @submit="create" />
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <KnowledgeSourceList
      :sources="sources"
      :disabled="loading"
      @toggle="setEnabled"
      @remove="remove"
    />
  </section>
</template>

<style scoped>
.manager { display: grid; gap: 1.5rem; padding: 1.5rem; border: 1px solid rgba(22, 83, 78, 0.14); border-radius: 20px; background: rgba(250, 252, 249, 0.94); box-shadow: 0 24px 70px rgba(31, 64, 61, 0.12); }
.manager-header { display: flex; align-items: end; justify-content: space-between; gap: 1rem; }
.manager-header h2 { margin: 0.1rem 0 0; font-size: clamp(1.5rem, 4vw, 2.3rem); }
.eyebrow { margin: 0; color: #0d6f66; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.14em; }
.summary { margin: 0; color: #607276; }
.request-error { margin: 0; padding: 0.8rem; border-radius: 10px; background: #fee5de; color: #8b2c19; }
</style>
