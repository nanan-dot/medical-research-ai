<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

const route = useRoute();
const documentSpaceLabel = "\u6587\u6863\u4e0e\u77e5\u8bc6";
const documentLibraryLabel = "\u6587\u6863\u5e93";
const workspaceLabel = "\u5de5\u4f5c\u53f0";

// Only confirmed product-space ancestors receive links; unrelated breadcrumb labels remain plain text.
const breadcrumbLinkByLabel: Readonly<Record<string, string>> = {
  [documentSpaceLabel]: "/documents",
  [documentLibraryLabel]: "/documents",
};

function breadcrumbTarget(label: string): string | undefined {
  return breadcrumbLinkByLabel[label];
}

const breadcrumbs = computed<string[]>(() => {
  const base = route.meta.breadcrumb;
  if (route.path === "/analysis") {
    const label = route.query.tab === "reading"
      ? "\u5355\u7bc7\u7cbe\u8bfb"
      : route.query.tab === "evidence"
        ? "\u8bc1\u636e\u95ee\u7b54"
        : "\u7814\u7a76\u6982\u89c8";
    return ["\u8bba\u6587\u7814\u7a76", label];
  }
  return Array.isArray(base)
    ? base.map(String)
    : [String(route.meta.feature?.label ?? workspaceLabel)];
});
</script>

<template>
  <nav class="breadcrumbs" aria-label="面包屑">
    <template v-for="(item, index) in breadcrumbs" :key="`${item}-${index}`">
      <span v-if="index" class="separator" aria-hidden="true">/</span>
      <strong v-if="index === breadcrumbs.length - 1">{{ item }}</strong>
      <RouterLink
        v-else-if="breadcrumbTarget(item)"
        :to="breadcrumbTarget(item)!"
        class="breadcrumb-link"
      >
        {{ item }}
      </RouterLink>
      <span v-else>{{ item }}</span>
    </template>
  </nav>
</template>

<style scoped>
.breadcrumbs { display: flex; gap: .45rem; color: var(--text-muted); font-size: .82rem; white-space: nowrap; }
.breadcrumbs strong { color: var(--text-primary); }
/* 保持与原先纯文本面包屑一致，不能使用浏览器的紫色访问链接样式。 */
.breadcrumb-link,
.breadcrumb-link:visited { color: var(--text-muted); text-decoration: none; }
.breadcrumb-link:hover,
.breadcrumb-link:focus-visible { color: var(--color-primary); outline: none; }
.separator { color: var(--text-faint); }
</style>
