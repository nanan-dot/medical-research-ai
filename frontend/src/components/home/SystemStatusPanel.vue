<script setup lang="ts">
import { onMounted, ref } from "vue";
import { healthApi } from "../../api/health";

const state = ref<"loading" | "ok" | "down">("loading");
onMounted(async () => {
  try {
    const health = await healthApi.get();
    state.value = health.status === "ok" || health.status === "healthy" ? "ok" : "down";
  } catch (cause) {
    state.value = "down";
    console.warn("系统状态读取失败", cause);
  }
});
const label = { loading: "正在连接系统状态", ok: "系统状态正常 · 本地优先", down: "后端连接异常" } as const;
</script>
<template>
  <section class="system-status" aria-label="系统状态">
    <div class="panel-head">
      <h2>系统状态</h2>
    </div>
    <p class="status-line"><span class="dot" :class="state"></span><span>{{ label[state] }}</span></p>
    <p class="detail">模型、隐私与诊断设置可在设置中心查看。</p>
  </section>
</template>
<style scoped>
.system-status{min-width:0}.panel-head{margin-bottom:.4rem}.panel-head h2{margin:0;font-size:1rem;color:var(--text-primary)}.status-line{display:flex;align-items:center;gap:.5rem;margin:.4rem 0;color:var(--text-muted);font-size:.86rem}.dot{width:.5rem;height:.5rem;border-radius:50%}.dot.loading{background:var(--color-warning)}.dot.ok{background:var(--color-success)}.dot.down{background:var(--color-danger)}.detail{margin:0;color:var(--text-faint);font-size:.78rem;line-height:1.55}
</style>
