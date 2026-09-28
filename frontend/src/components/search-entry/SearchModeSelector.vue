<script setup lang="ts">import type { SearchMode } from "../../types/searchEntry";const props=defineProps<{modelValue:SearchMode}>();const emit=defineEmits<{"update:modelValue":[value:SearchMode]}>();const modes:[SearchMode,string,string][]=[["auto","自动识别","根据研究问题识别结构"],["pico","PICO","临床干预研究"],["peco","PECO","观察性研究"],["disease","疾病主题","疾病主题综述"],["mechanism","机制研究","机制与基础研究"],["custom","自定义","BACKEND_REQUIRED：自定义偏好契约未接入"]];</script><template>
  <div
    class="modes"
    role="radiogroup"
    aria-label="检索模式"
  >
    <label
      v-for="[value,label,hint] in modes"
      :key="value"
      :title="hint"
    ><input
      :checked="props.modelValue===value"
      type="radio"
      name="search-mode"
      :value="value"
      :disabled="value==='custom'"
      @change="emit('update:modelValue',value)"
    ><span>{{ label }}</span></label>
  </div>
</template><style scoped>.modes{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}.modes label{display:flex;align-items:center;justify-content:center;gap:7px;min-height:44px;border:1px solid #d9e1f0;border-radius:8px;color:#253d70;font-weight:600;cursor:pointer}.modes label:has(input:checked){border-color:#3266f6;background:#f4f7ff;color:#1e59ec}.modes label:has(input:disabled){cursor:not-allowed;opacity:.55}.modes input{accent-color:#245cf1}@media(max-width:1023px){.modes{grid-template-columns:repeat(3,1fr)}}@media(max-width:767px){.modes{grid-template-columns:repeat(2,1fr)}}</style>
