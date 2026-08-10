<script setup lang="ts">
import { computed, shallowRef, watch } from "vue";
import { RouterLink } from "vue-router";

import {
  acquireOfficialPmcFulltext,
  type OpenFulltextAcquisition,
} from "../../api/openFulltext";
import type { LibraryItem } from "../../api/literatureSearch";

const props = defineProps<{ item: LibraryItem }>();
const emit = defineEmits<{ updated: [item: LibraryItem] }>();

const pmcid = shallowRef(props.item.pmcid ?? "");
const acquiring = shallowRef(false);
const error = shallowRef("");
const acquisition = shallowRef<OpenFulltextAcquisition | null>(null);

const normalizedPmcid = computed(() => pmcid.value.trim().toUpperCase());
const isPmcidFormatValid = computed(() => /^PMC\d+$/.test(normalizedPmcid.value));

watch(
  () => props.item.pmcid,
  (nextPmcid) => {
    if (nextPmcid) pmcid.value = nextPmcid;
  },
);

async function acquire(): Promise<void> {
  if (!isPmcidFormatValid.value || acquiring.value) return;
  acquiring.value = true;
  error.value = "";
  try {
    const result = await acquireOfficialPmcFulltext(props.item.id, normalizedPmcid.value);
    acquisition.value = result.acquisition;
    emit("updated", result.item);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "无法获取开放全文";
  } finally {
    acquiring.value = false;
  }
}
</script>

<template>
  <section class="open-access" aria-label="PMC 官方开放全文">
    <label>
      PMCID
      <input v-model="pmcid" inputmode="numeric" placeholder="例如 PMC1234567" :disabled="acquiring" />
    </label>
    <button class="button" :disabled="!isPmcidFormatValid || acquiring" @click="acquire">
      {{ acquiring ? "官方核验与下载中…" : "获取 PMC 开放全文" }}
    </button>
    <small class="notice">仅在 PMC 官方 OAI 身份、许可及官方 PDF 链接均核验通过后才入库。</small>
    <p v-if="acquisition?.status === 'succeeded'" class="success">
      已获取官方开放全文（{{ acquisition.license }}）。
      <RouterLink v-if="acquisition.document_id" :to="`/documents/${acquisition.document_id}`">打开文档</RouterLink>
    </p>
    <p v-else-if="acquisition" class="failure" role="alert">{{ acquisition.error_message ?? "未能自动获取全文" }}</p>
    <p v-if="error" class="failure" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.open-access { display: grid; gap: .32rem; max-width: 17rem; padding: .45rem; border: 1px solid var(--border); border-radius: .5rem; }
label { display: grid; gap: .18rem; font-size: .76rem; font-weight: 700; }
input { min-width: 0; border: 1px solid var(--border-strong); border-radius: .3rem; padding: .28rem .4rem; background: var(--paper); color: inherit; }
.button { justify-self: start; border: 1px solid var(--border-strong); border-radius: 99px; padding: .3rem .6rem; background: var(--paper); color: var(--color-primary); font-size: .76rem; font-weight: 750; }
.button:disabled { opacity: .55; }
.notice { color: var(--text-secondary); }
.success { color: var(--color-success); margin: 0; font-size: .78rem; }
.failure { color: var(--color-danger); margin: 0; font-size: .78rem; }
</style>
