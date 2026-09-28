<script setup lang="ts">
import BaseIcon from "../ui/BaseIcon.vue";

defineEmits<{ add: [] }>();
</script>

<template>
  <header
    class="header"
    data-testid="knowledge-base-header"
  >
    <div class="copy">
      <p class="breadcrumb">研究资源 <span>/</span> 知识库</p>
      <h1>知识库</h1>
      <p class="description">统一管理科研资料来源，让文档持续转化为可检索、可问答、可追溯的知识资产。</p>
    </div>
    <div
      class="art"
      aria-hidden="true"
    >
      <span class="art-dot dot-one" /><span class="art-dot dot-two" /><BaseIcon name="folder" /><BaseIcon
        class="document"
        name="document"
      />
    </div>
    <button
      type="button"
      @click="$emit('add')"
    >
      <BaseIcon name="plus" /> 添加知识来源 <BaseIcon
        class="chevron"
        name="chevron-down"
      />
    </button>
  </header>
</template>

<style scoped>
.header { display:grid; grid-template-columns:minmax(0,1fr) 128px auto; align-items:center; gap:18px; margin:0 0 14px; }
.breadcrumb { margin:0 0 8px; color:#71809d; font-size:12px; font-weight:700; }.breadcrumb span { padding:0 6px; color:#b1bdcf; }
.header h1 { margin:0; color:#102249; font-size:28px; line-height:1.16; letter-spacing:-.035em; }.description { max-width:620px; margin:6px 0 0; color:#657696; font-size:13px; line-height:1.55; }
.header > button { display:flex; align-items:center; justify-content:center; gap:7px; min-height:38px; padding:0 14px; border:0; border-radius:7px; background:#125cff; color:#fff; font-size:13px; font-weight:750; white-space:nowrap; }.header > button .icon { font-size:16px; }.header > button .chevron { font-size:13px; }
.art { position:relative; display:grid; height:74px; place-items:center; color:#296cff; }.art > .icon:first-of-type { width:58px; height:58px; padding:14px; border:1px solid #cdddff; border-radius:15px; background:#f4f7ff; transform:rotate(-4deg); }.art .document { position:absolute; right:15px; bottom:4px; width:27px; height:27px; padding:6px; border-radius:8px; background:#fff; box-shadow:0 5px 14px #1c5eff24; }.art-dot { position:absolute; width:6px; height:6px; border-radius:50%; background:#81a8ff; }.dot-one { top:11px; left:26px; }.dot-two { right:18px; top:21px; background:#ffb648; }
@media (max-width:1023px) { .header { grid-template-columns:1fr auto; }.art { display:none; } } @media (max-width:767px) { .header { display:flex; flex-direction:column; align-items:stretch; gap:12px; }.header h1 { font-size:25px; }.header > button { min-height:42px; } }
</style>
