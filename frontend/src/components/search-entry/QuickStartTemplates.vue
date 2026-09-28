<script setup lang="ts">import type { SearchTemplate } from "../../types/searchEntry";defineProps<{templates:SearchTemplate[]}>();const emit=defineEmits<{select:[template:SearchTemplate]}>();</script><template>
  <section
    class="quick"
    aria-labelledby="quick-title"
  >
    <div><h2 id="quick-title">ϟ 快速开始</h2><p>选择常见研究类型，快速构建检索策略</p></div><div class="template-grid">
      <button
        v-for="template in templates"
        :key="template.id"
        type="button"
        @click="emit('select',template)"
      >
        <strong>{{ template.title }}</strong><span>{{ template.description }}</span><small>例：{{ template.question }} →</small>
      </button>
    </div>
  </section>
</template><style scoped>.quick{display:grid;gap:14px}.quick>div:first-child{display:flex;align-items:center;gap:28px}.quick h2,.quick p{margin:0}.quick h2{color:#153166;font-size:18px}.quick p{color:#7181a4;font-size:13px}.template-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.template-grid button{display:grid;gap:10px;min-height:140px;padding:20px;border:0;border-radius:12px;background:#fff;box-shadow:0 5px 16px rgb(18 61 129 / .07);color:#142f65;text-align:left}.template-grid strong{font-size:16px}.template-grid span,.template-grid small{color:#63759e;font-size:13px;line-height:1.6}.template-grid small{margin-top:auto}@media(max-width:1023px){.template-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:767px){.quick>div:first-child{align-items:start;flex-direction:column;gap:4px}.template-grid{grid-template-columns:1fr}.template-grid button{min-height:104px}}</style>
