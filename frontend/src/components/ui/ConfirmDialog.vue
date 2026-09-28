<script setup lang="ts">
import { nextTick, onBeforeUnmount, watch } from "vue";

const props = defineProps<{ open: boolean; title: string; description: string; confirmLabel: string; pending: boolean; error: string | null; returnFocus?: HTMLElement | null }>();
const emit = defineEmits<{ cancel: []; confirm: [] }>();
let priorFocus: HTMLElement | null = null;

function close(): void { if (!props.pending) emit("cancel"); }
function onKeydown(event: KeyboardEvent): void { if (event.key === "Escape") { event.preventDefault(); close(); } }
watch(() => props.open, async (open) => { if (open) { priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null; await nextTick(); document.querySelector<HTMLElement>(".confirm-dialog__confirm")?.focus(); } else { (props.returnFocus ?? priorFocus)?.focus(); } });
onBeforeUnmount(() => { priorFocus = null; });
</script>
<template>
  <div
    v-if="open"
    class="confirm-dialog__backdrop"
    @click.self="close"
  >
    <section
      class="confirm-dialog"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="`${title}-title`"
      @keydown="onKeydown"
    >
      <h2 :id="`${title}-title`">{{ title }}</h2>
      <p>{{ description }}</p>
      <p
        v-if="error"
        class="confirm-dialog__error"
        role="alert"
      >
        {{ error }}
      </p>
      <footer>
        <button
          type="button"
          :disabled="pending"
          @click="close"
        >
          取消
        </button><button
          class="confirm-dialog__confirm"
          type="button"
          :disabled="pending"
          @click="emit('confirm')"
        >
          {{ pending ? "处理中…" : confirmLabel }}
        </button>
      </footer>
    </section>
  </div>
</template>
<style scoped>
.confirm-dialog__backdrop { position: fixed; z-index: 50; inset: 0; display: grid; place-items: center; padding: 16px; background: rgb(15 30 60 / 28%); }
.confirm-dialog { width: min(100%, 440px); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 22px; background: var(--surface); box-shadow: 0 18px 60px rgb(25 55 110 / 24%); }
.confirm-dialog h2 { margin: 0; color: var(--text-primary); font-size: 1.1rem; }.confirm-dialog p { color: var(--text-muted); line-height: 1.6; }.confirm-dialog__error { color: var(--color-danger) !important; }.confirm-dialog footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }.confirm-dialog button { min-height: 40px; border: 1px solid var(--border-strong); border-radius: 8px; padding: 0 14px; background: var(--surface); color: var(--text-primary); font-weight: 700; }.confirm-dialog__confirm { border-color: var(--color-danger) !important; background: var(--color-danger) !important; color: #fff !important; }
</style>
