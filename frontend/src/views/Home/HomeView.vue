<script setup lang="ts">
// 素问 · 工作台首页：研究起点 + 8/4 双栏（继续研究 / 进行中的工作）+ 最近活动时间线。
// 所有任务与活动均为本地演示数据；不伪造真实检索、解析或任务进度。
import { computed } from "vue";
import ResearchStartPanel from "../../components/home/ResearchStartPanel.vue";
import ContinueResearchPanel from "../../components/home/ContinueResearchPanel.vue";
import ActiveWorkPanel from "../../components/home/ActiveWorkPanel.vue";
import RecentActivityTimeline from "../../components/home/RecentActivityTimeline.vue";

// 可替换的临时默认名：后续接入用户资料后改为真实姓名。
const researcherName = "研究者";

// 可替换的临时默认项目信息：后续接入项目上下文后改为真实项目。
// 不绑定任何具体病种或药物，保持通用科研语境。
const projectName = "示例研究项目";
const projectStage = "文献调研与证据整合";

const hour = new Date().getHours();
const greeting = hour < 6 ? "凌晨好" : hour < 12 ? "上午好" : hour < 18 ? "下午好" : "晚上好";
const greetingTitle = computed(() => `${greeting}，${researcherName}`);
</script>

<template>
  <main class="workbench">
    <header class="welcome">
      <h1 class="welcome-title">{{ greetingTitle }}</h1>
      <p class="welcome-sub">
        项目：{{ projectName }}&nbsp;&nbsp;&nbsp;当前阶段：{{ projectStage }}
      </p>
    </header>

    <ResearchStartPanel />

    <div class="columns">
      <ContinueResearchPanel class="col-main" />
      <ActiveWorkPanel class="col-side" />
    </div>

    <RecentActivityTimeline />
  </main>
</template>

<style scoped>
.workbench {
  max-width: 1180px;
  margin: 0 auto;
  padding: 1.7rem 1.8rem 2.6rem;
  display: grid;
  gap: 1.6rem;
}
.welcome {
  display: grid;
  gap: 0.3rem;
}
.welcome-title {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(1.75rem, 2.5vw, 2rem);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.welcome-sub {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.86rem;
}
.columns {
  display: grid;
  grid-template-columns: minmax(0, 8fr) minmax(0, 4fr);
  gap: 1.3rem;
  align-items: start;
}
.col-main,
.col-side {
  min-width: 0;
}
@media (max-width: 1100px) {
  .columns {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .workbench {
    padding: 1.1rem 1rem 1.8rem;
    gap: 1.2rem;
  }
  .welcome-title { font-size: 1.75rem; }
}
</style>
