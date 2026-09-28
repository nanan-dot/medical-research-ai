<script setup lang="ts">
import { computed, nextTick, shallowRef, useTemplateRef } from "vue";
import type { SearchQuestionHistoryEntry } from "../../composables/useSearchQuestionHistory";
const props = defineProps<{ modelValue: string; disabled: boolean; error: string | null; historyQuestions: readonly SearchQuestionHistoryEntry[] }>();
const emit = defineEmits<{ "update:modelValue": [value: string]; submit: []; selectHistory: [entry: SearchQuestionHistoryEntry] }>();
const isMenuOpen = shallowRef(false); const input = useTemplateRef<HTMLTextAreaElement>("input");
const count = computed(() => props.modelValue.length);
function selectHistory(entry: SearchQuestionHistoryEntry): void { emit("selectHistory", entry); isMenuOpen.value=false; void nextTick(()=>input.value?.focus()); }
function handleKeydown(event: KeyboardEvent): void { if ((event.ctrlKey||event.metaKey)&&event.key==="Enter"&&!props.disabled){event.preventDefault();emit("submit");} if(event.key==="Escape") isMenuOpen.value=false; }
</script>
<template>
  <section
    class="question-card"
    aria-labelledby="research-question-title"
  >
    <div class="card-head">
      <div><h2 id="research-question-title">输入研究问题 <small>必填</small></h2><p>描述你的研究问题，系统将自动识别研究意图并构建检索策略</p></div><div class="example-wrap">
        <button
          type="button"
          aria-haspopup="menu"
          :aria-expanded="isMenuOpen"
          @click="isMenuOpen=!isMenuOpen"
        >
          查看历史问题⌄
        </button><div
          v-if="isMenuOpen"
          role="menu"
          class="example-menu"
        >
          <p v-if="props.historyQuestions.length === 0" class="history-empty">暂无历史问题。成功生成策略后会保存在本设备。</p><button
            v-for="entry in props.historyQuestions"
            v-else
            :key="entry.question"
            role="menuitem"
            type="button"
            @click="selectHistory(entry)"
          >
            {{ entry.question }}
          </button>
        </div>
      </div>
    </div><label for="search-entry-question">研究问题</label><textarea
      id="search-entry-question"
      ref="input"
      :value="modelValue"
      maxlength="500"
      aria-describedby="question-help question-count"
      placeholder="例如：间质性肺疾病（ILD）患者中，抗纤维化药物的疗效与安全性如何？"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value.slice(0, 500))"
      @keydown="handleKeydown"
    /><p
      id="question-count"
      class="count"
    >
      {{ count }} / 500
    </p><p
      id="question-help"
      class="sr-only"
    >
      最多 500 个字符，可按 Control 加 Enter 生成策略。
    </p><fieldset><legend>检索模式</legend><slot /></fieldset><p
      v-if="error"
      class="error"
      role="alert"
    >
      {{ error }} <button
        type="button"
        @click="emit('submit')"
      >
        重试
      </button>
    </p><button
      class="submit"
      type="button"
      :disabled="disabled"
      @click="emit('submit')"
    >
      生成检索策略 →
    </button><p class="privacy">策略会保存在你的检索历史中，供你确认与追溯。</p>
  </section>
</template>
<style scoped>
.question-card { display: grid; gap: 16px; padding: 28px 34px 24px; border-radius: 16px; background: #fff; box-shadow: 0 12px 24px rgb(18 61 129 / .1); }
.card-head { display: flex; justify-content: space-between; gap: 16px; }
.card-head h2, .card-head p { margin: 0; }
.card-head h2 { font-size: 22px; color: #0b255b; }
.card-head small { margin-left: 8px; padding: 3px 7px; border-radius: 5px; background: #eef3ff; color: #225bf0; font-size: 12px; }
.card-head p, .privacy { margin-top: 7px; color: #61739d; font-size: 14px; }
.example-wrap { position: relative; }
.example-wrap > button { min-height: 40px; padding: 0 16px; border: 1px solid #d8e1f3; border-radius: 8px; background: #fff; color: #1553e7; font-weight: 700; }
.example-menu { position: absolute; z-index: 3; right: 0; width: 250px; margin-top: 4px; padding: 6px; border: 1px solid #d8e1f3; border-radius: 8px; background: #fff; box-shadow: 0 8px 24px #123a7c20; }
.example-menu button { width: 100%; padding: 9px; border: 0; background: transparent; text-align: left; }
.history-empty { margin: 0; padding: 9px; color: #61739d; font-size: 13px; line-height: 1.5; }
.question-card > label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
textarea { box-sizing: border-box; min-height: 128px; width: 100%; padding: 16px; border: 1.5px solid #2b64f6; border-radius: 9px; resize: vertical; color: #152d60; font: inherit; line-height: 1.5; }
textarea:focus-visible, button:focus-visible, input:focus-visible { outline: 2px solid #0b5fcc; outline-offset: 2px; }
.count { margin: -10px 0 0 auto; color: #62739d; font-size: 13px; }
fieldset { display: grid; gap: 10px; margin: 0; padding: 0; border: 0; }
legend { padding: 0; color: #173166; font-size: 16px; font-weight: 700; }
.submit { justify-self: center; min-width: 300px; min-height: 48px; margin-top: 8px; border: 0; border-radius: 7px; background: linear-gradient(100deg, #1558ed, #9228ef); color: #fff; font-size: 17px; font-weight: 700; }
.submit:disabled { opacity: .52; cursor: not-allowed; }
.privacy { margin: -8px 0 0; text-align: center; }
.error { margin: 0; color: #b42318; }
.error button { margin-left: 8px; border: 0; background: transparent; color: inherit; text-decoration: underline; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

@media (max-width: 767px) {
  .question-card { padding: 20px 16px; }
  .card-head { align-items: start; flex-direction: column; }
  .submit { min-width: 100%; margin-top: 0; }
  .privacy { margin-top: 7px; }
}
</style>
