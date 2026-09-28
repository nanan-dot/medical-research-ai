<script setup lang="ts">
// 素问品牌标识：打开的文献页 + 中央证据定位点。
// 图形语言取自品牌决策（打开的文献页 + 引文线 + 证据定位点），
// 不使用任何第三方文字商标；尺寸由父级控制。
withDefaults(defineProps<{ size?: number }>(), { size: 28 });
</script>

<template>
  <!-- eslint-disable vue/max-attributes-per-line -->
  <svg
    class="brand-logo"
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-label="素问品牌标识"
  >
    <rect
      x="2.5"
      y="2.5"
      width="27"
      height="27"
      rx="6"
      stroke="currentColor"
      stroke-width="1.8"
    />
    <!-- 打开的文献页（左右两页对称轮廓） -->
    <path
      d="M16 7 C 12.5 4.6, 7.5 4.8, 5 6 V 25 C 7.5 23.8, 12.5 23.6, 16 26 C 19.5 23.6, 24.5 23.8, 27 25 V 6 C 24.5 4.8, 19.5 4.6, 16 7 Z"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linejoin="round"
      fill="none"
    />
    <!-- 左页引文线 -->
    <line x1="8.5" y1="10.5" x2="13" y2="10.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="8.5" y1="14" x2="12.2" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <!-- 右页引文线 -->
    <line x1="19" y1="10.5" x2="23.5" y2="10.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="19.8" y1="14" x2="23.5" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <!-- 中央证据定位点（实心圆 + 定位针尖） -->
    <circle cx="16" cy="16" r="2.6" fill="#2563EB" />
    <path d="M16 18.6 V 23" stroke="#2563EB" stroke-width="1.6" stroke-linecap="round" />
  </svg>
  <!-- eslint-enable vue/max-attributes-per-line -->
</template>
