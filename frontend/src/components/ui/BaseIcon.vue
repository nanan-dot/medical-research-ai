<script setup lang="ts">
type IconName = "alert" | "chevron-down" | "close" | "document" | "filter" | "folder" | "info" | "lock" | "more" | "plus" | "search" | "star" | "sync";

defineProps<{ name: IconName; filled?: boolean }>();
</script>

<template>
  <svg
    aria-hidden="true"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <path
      v-if="name === 'folder'"
      d="M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v8A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5z"
    />
    <path
      v-else-if="name === 'document'"
      d="M6 3h8l4 4v14H6zM14 3v5h5M9 13h6M9 17h6"
    />
    <path
      v-else-if="name === 'search'"
      d="m20 20-4.4-4.4M10.8 17a6.2 6.2 0 1 1 0-12.4 6.2 6.2 0 0 1 0 12.4"
    />
    <path
      v-else-if="name === 'filter'"
      d="M4 5h16M7 12h10M10 19h4"
    />
    <path
      v-else-if="name === 'sync'"
      d="M20 7v5h-5M4 17v-5h5M6.2 9A7 7 0 0 1 18 7M17.8 15A7 7 0 0 1 6 17"
    />
    <path
      v-else-if="name === 'more'"
      d="M5 12h.01M12 12h.01M19 12h.01"
      stroke-width="3"
    />
    <path
      v-else-if="name === 'plus'"
      d="M12 5v14M5 12h14"
    />
    <path
      v-else-if="name === 'close'"
      d="m6 6 12 12M18 6 6 18"
    />
    <path
      v-else-if="name === 'chevron-down'"
      d="m7 10 5 5 5-5"
    />
    <path
      v-else-if="name === 'alert'"
      d="M12 4 3.7 19h16.6zM12 9v4M12 16h.01"
    />
    <path
      v-else-if="name === 'lock'"
      d="M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5z"
    />
    <path
      v-else-if="name === 'info'"
      d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 10v6M12 7.2h.01"
    />
    <path
      v-else-if="name === 'star'"
      :fill="filled ? 'currentColor' : 'none'"
      d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"
    />
  </svg>
</template>

<style scoped>
.icon { display: block; width: 1em; height: 1em; }
</style>
