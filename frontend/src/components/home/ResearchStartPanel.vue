<script setup lang="ts">
// 研究起点：工作台唯一的输入入口 + 四个快捷动作。
// 提交后调用真实后端 parse-query 创建文献检索任务；快捷动作跳转到对应功能页。
import { ref } from "vue";
import { useRouter } from "vue-router";
import { literatureSearchApi } from "../../api/literatureSearch";

const router = useRouter();
const query = ref("");
const message = ref("");
const isSubmitting = ref(false);

interface QuickAction {
  label: string;
  icon: string;
  path: string;
}

const quickActions: QuickAction[] = [
  { label: "检索文献", icon: "⌕", path: "/literature-search" },
  { label: "分析论文", icon: "◈", path: "/analysis" },
  { label: "比较研究", icon: "≋", path: "/comparisons" },
  { label: "证据问答", icon: "◌", path: "/analysis?tab=evidence" },
];

async function submitQuery(): Promise<void> {
  const text = query.value.trim();
  if (!text) {
    message.value = "请先输入临床问题或研究主题。";
    return;
  }
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  message.value = "";
  try {
    // 真实后端调用：解析检索意图（不创建任务——创建任务需要完整检索式，
    // 由文献检索页的四步流程（解析→扩展→构建→创建）完成）。
    await literatureSearchApi.parseQuery(text);
    // 跳转到文献检索页继续完整流程
    await router.push({ path: "/literature-search", query: { raw_topic: text } });
  } catch (cause) {
    message.value = cause instanceof Error ? cause.message : "无法解析检索意图";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section class="research-start" aria-label="研究起点">
    <h2 class="panel-title">研究起点</h2>
    <form class="start-form" role="search" @submit.prevent="submitQuery">
      <span class="start-icon" aria-hidden="true">✎</span>
      <input
        v-model="query"
        aria-label="输入临床问题、研究主题或想完成的任务"
        placeholder="输入临床问题、研究主题或想完成的任务"
        maxlength="200"
        :disabled="isSubmitting"
      />
      <button class="send" type="submit" aria-label="提交研究起点" :disabled="isSubmitting">➤</button>
    </form>
    <nav class="quick" aria-label="快捷动作">
      <RouterLink
        v-for="action in quickActions"
        :key="action.label"
        :to="action.path"
        class="quick-btn"
      >
        <span class="quick-icon" aria-hidden="true">{{ action.icon }}</span>
        <span>{{ action.label }}</span>
      </RouterLink>
    </nav>
    <p v-if="message" class="toast" role="status">{{ message }}</p>
  </section>
</template>

<style scoped>
.research-start {
  display: grid;
  gap: 0.8rem;
}
.panel-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.start-form {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 56px;
  padding: 0 0.9rem;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  box-shadow: var(--shadow-card);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.start-form:hover,
.start-form:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.start-icon {
  color: var(--text-faint);
  font-size: 1.05rem;
}
.start-form input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  color: var(--text-primary);
  font-size: 0.92rem;
  background: transparent;
}
.start-form input::placeholder {
  color: var(--text-faint);
}
.send {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 9px;
  background: var(--color-primary);
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background-color 0.15s;
}
.send:hover,
.send:focus-visible {
  background: #1d4ed8;
  outline: 2px solid rgba(37, 99, 235, 0.35);
  outline-offset: 2px;
}
.send:active {
  background: #1e40af;
}
.send:disabled {
  opacity: 0.6;
  cursor: default;
}
.quick {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.6rem;
}
.quick-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-height: 36px;
  padding: 0 0.7rem;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 0.83rem;
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s, background-color 0.15s;
}
.quick-btn:hover,
.quick-btn:focus-visible {
  border-color: var(--color-primary);
  color: var(--color-primary);
  outline: none;
}
.quick-btn:active {
  background: var(--nav-active-bg);
}
.quick-icon {
  color: var(--color-primary);
  font-size: 0.95rem;
}
.toast {
  margin: 0;
  padding: 0.5rem 0.8rem;
  border-radius: 8px;
  background: var(--surface-muted);
  color: var(--text-muted);
  font-size: 0.78rem;
}
@media (max-width: 720px) {
  .quick {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
