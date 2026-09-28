<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from "vue";
import type { ReaderRecord } from "../../api/paperReader";

const props = defineProps<{ open: boolean; records: readonly ReaderRecord[]; activeType: string | null }>();
const emit = defineEmits<{ close: []; locate: [record: ReaderRecord] }>();
const dialog = useTemplateRef<HTMLElement>("dialog");
const previousFocus = shallowRef<HTMLElement | null>(null);
const previousOverflow = shallowRef("");
const visibleRecords = computed(() => props.activeType ? props.records.filter((record) => record.record_type === props.activeType) : props.records);
function close() { emit("close"); }
function keydown(event: KeyboardEvent) {
  if (event.key === "Escape") { close(); return; }
  if (event.key !== "Tab" || !dialog.value) return;
  const focusable = Array.from(dialog.value.querySelectorAll<HTMLElement>("button, [href], input, textarea, select, [tabindex]:not([tabindex='-1'])")).filter((element) => !element.hasAttribute("disabled"));
  if (!focusable.length) { event.preventDefault(); dialog.value.focus(); return; }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}
watch(() => props.open, (open) => {
  if (open) { previousFocus.value = document.activeElement as HTMLElement; previousOverflow.value = document.body.style.overflow; document.body.style.overflow = "hidden"; window.setTimeout(() => dialog.value?.focus(), 0); window.addEventListener("keydown", keydown); }
  else { window.removeEventListener("keydown", keydown); document.body.style.overflow = previousOverflow.value; previousFocus.value?.focus(); }
});
onMounted(() => { if (props.open) window.addEventListener("keydown", keydown); });
onBeforeUnmount(() => { window.removeEventListener("keydown", keydown); if (props.open) document.body.style.overflow = previousOverflow.value; });
</script>
<template>
  <Teleport to="body">
    <div v-if="open" class="records-overlay" @click.self="close">
      <section ref="dialog" class="records-dialog" role="dialog" aria-modal="true" aria-labelledby="records-dialog-title" tabindex="-1">
        <header class="dialog-header"><div><p class="eyebrow">论文阅读</p><h2 id="records-dialog-title">我的记录</h2></div><button class="close-button" type="button" aria-label="关闭记录弹层" @click="close">×</button></header>
        <div class="dialog-list" role="list">
          <button v-for="record in visibleRecords" :key="record.record_id" class="record-row" type="button" @click="emit('locate', record)">
            <span class="row-icon" :class="`type-${record.record_type}`" aria-hidden="true">{{ record.record_type === "highlight" ? "★" : record.record_type === "annotation" ? "✎" : record.record_type === "question" ? "?" : "▮" }}</span>
            <span class="row-copy"><b>{{ record.record_type === "highlight" ? "高亮" : record.record_type === "annotation" ? "批注" : record.record_type === "question" ? "疑问" : "收藏" }}</b><span>{{ record.text || record.quote || "已记录原文位置" }}</span><small>{{ record.page_number ? `第 ${record.page_number} 页` : "页码待定位" }}</small></span><span class="row-arrow" aria-hidden="true">›</span>
          </button>
          <p v-if="!visibleRecords.length" class="empty">暂无此类记录</p>
        </div>
      </section>
    </div>
  </Teleport>
</template>
<style scoped>
.records-overlay{position:fixed;inset:0;z-index:40;display:grid;place-items:center;padding:24px;background:#10213a66;backdrop-filter:blur(3px)}
.records-dialog{width:min(620px,100%);max-height:min(720px,90vh);overflow:hidden;border:1px solid #dbe4f1;border-radius:16px;background:#fff;box-shadow:0 24px 70px #10213a3d}
.dialog-header{display:flex;align-items:flex-start;justify-content:space-between;padding:22px 24px 16px;border-bottom:1px solid #edf1f7}.eyebrow{margin:0 0 4px;color:#1769e8;font-size:11px;font-weight:700}.dialog-header h2{margin:0;color:#132238;font-size:22px}.close-button{width:34px;height:34px;border:1px solid #dbe4f1;border-radius:9px;background:#fff;color:#344054;font-size:24px;line-height:1}.dialog-list{display:grid;gap:8px;max-height:calc(min(720px,90vh) - 100px);overflow:auto;padding:16px 20px 22px}.record-row{display:grid;grid-template-columns:38px 1fr 20px;align-items:center;gap:12px;width:100%;padding:12px;border:1px solid #e4eaf3;border-radius:10px;background:#fff;text-align:left}.record-row:hover{border-color:#9fc2ff;background:#f8fbff}.row-icon{display:grid;width:34px;height:34px;place-items:center;border-radius:9px;font-style:normal;font-weight:800}.type-highlight{background:#fff2d8;color:#f59e0b}.type-annotation{background:#e8f0ff;color:#1769e8}.type-question{background:#f1e8ff;color:#7c3aed}.type-bookmark{background:#dcf7ef;color:#10a982}.row-copy{display:grid;gap:3px;min-width:0}.row-copy b{color:#182235;font-size:12px}.row-copy span{overflow:hidden;color:#344054;font-size:13px;text-overflow:ellipsis;white-space:nowrap}.row-copy small{color:#98a2b3;font-size:11px}.row-arrow{color:#1769e8;font-size:22px}.empty{padding:36px;text-align:center;color:#667085}
</style>
