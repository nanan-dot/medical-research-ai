<template>
  <nav
    class="utility-links"
    aria-label="检索工具"
  >
    <RouterLink to="/literature-search/history">打开历史策略</RouterLink>
  </nav>
</template>

<style scoped>
.utility-links {
  position: absolute;
  z-index: 2;
  top: 30px;
  right: 42px;
}

.utility-links a {
  color: #164394;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
}

.utility-links a::before { content: "▣"; margin-right: 8px; }

@media (max-width: 767px) {
  .utility-links { top: 12px; right: 16px; }
}
</style>
