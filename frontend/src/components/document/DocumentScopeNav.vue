<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type {
  ResourceLibraryItem,
  ResourceSourceTree,
  ResourceStorageSummary,
  ResourceTreeNode,
} from "../../api/resourceLibrary";

interface FlatTreeNode {
  node: ResourceTreeNode;
  depth: number;
}

const props = defineProps<{
  tree: ResourceSourceTree | null;
  recentItems: readonly Readonly<ResourceLibraryItem>[];
  selectedNodeId: string | null;
  total: number | null;
  loading: boolean;
  storage?: ResourceStorageSummary | null;
}>();

const emit = defineEmits<{
  selectAll: [];
  selectNode: [node: ResourceTreeNode];
  openRecent: [item: Readonly<ResourceLibraryItem>];
  manageSources: [];
}>();

const searchInput = ref("");
const activeTreeQuery = ref("");
const expandedIds = ref(new Set<string>());
const expandedBeforeSearch = ref<Set<string> | null>(null);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

const groupLabel: Readonly<Record<string, string>> = {
  local: "本地文件",
  obsidian: "Obsidian",
  zotero: "Zotero",
};
const groupOrder = ["local", "obsidian", "zotero"];

const orderedGroups = computed(() => {
  const groups = props.tree?.groups ?? [];
  return groupOrder.map((type) => groups.find((group) => group.source_type === type) ?? {
    source_type: type,
    node_id: `group:${type}`,
    descendant_count: 0,
    health: "unavailable",
    children: [],
  });
});

const treeNodesById = computed(() => {
  const nodes = new Map<string, ResourceTreeNode>();
  const visit = (children: readonly ResourceTreeNode[]) => children.forEach((node) => {
    nodes.set(node.node_id, node);
    visit(node.children);
  });
  orderedGroups.value.forEach((group) => visit(group.children));
  return nodes;
});

function matches(node: ResourceTreeNode, query: string): boolean {
  const normalized = query.trim().toLocaleLowerCase();
  return !normalized || `${node.name} ${node.relative_path}`.toLocaleLowerCase().includes(normalized);
}

function collectSearchTree(nodes: readonly ResourceTreeNode[], query: string, ancestors: Set<string>): ResourceTreeNode[] {
  return nodes.reduce<ResourceTreeNode[]>((result, node) => {
    const children = collectSearchTree(node.children, query, ancestors);
    if (!matches(node, query) && !children.length) return result;
    if (children.length) ancestors.add(node.node_id);
    result.push({ ...node, children });
    return result;
  }, []);
}

const searchAncestors = computed(() => {
  const ancestors = new Set<string>();
  if (!activeTreeQuery.value) return ancestors;
  orderedGroups.value.forEach((group) => collectSearchTree(group.children, activeTreeQuery.value, ancestors));
  return ancestors;
});

const displayedGroups = computed(() => orderedGroups.value.map((group) => ({
  ...group,
  children: activeTreeQuery.value ? collectSearchTree(group.children, activeTreeQuery.value, new Set<string>()) : group.children,
})));

function isExpanded(node: ResourceTreeNode): boolean {
  return expandedIds.value.has(node.node_id) || searchAncestors.value.has(node.node_id);
}

const visibleNodes = computed<FlatTreeNode[]>(() => {
  const output: FlatTreeNode[] = [];
  const visit = (nodes: readonly ResourceTreeNode[], depth: number) => {
    nodes.forEach((node) => {
      output.push({ node, depth });
      if (node.children.length && isExpanded(node)) visit(node.children, depth + 1);
    });
  };
  displayedGroups.value.forEach((group) => visit(group.children, 1));
  return output;
});

const hasTreeSearchResults = computed(() => visibleNodes.value.length > 0);

function toggleNode(node: ResourceTreeNode): void {
  if (!node.children.length) return;
  const next = new Set(expandedIds.value);
  if (next.has(node.node_id)) next.delete(node.node_id);
  else next.add(node.node_id);
  expandedIds.value = next;
}

function setTreeQuery(): void {
  const next = searchInput.value.trim();
  if (next && !activeTreeQuery.value) expandedBeforeSearch.value = new Set(expandedIds.value);
  if (!next && activeTreeQuery.value && expandedBeforeSearch.value) {
    expandedIds.value = new Set(expandedBeforeSearch.value);
    expandedBeforeSearch.value = null;
  }
  activeTreeQuery.value = next;
}

function scheduleTreeSearch(): void {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(setTreeQuery, 150);
}

function focusNode(index: number): void {
  const target = visibleNodes.value[index];
  if (!target) return;
  globalThis.document.querySelector<HTMLElement>(`[data-node-id="${CSS.escape(target.node.node_id)}"]`)?.focus();
}

function handleTreeKeydown(event: KeyboardEvent, flatNode: FlatTreeNode): void {
  const index = visibleNodes.value.findIndex(({ node }) => node.node_id === flatNode.node.node_id);
  switch (event.key) {
    case "ArrowDown":
      event.preventDefault();
      focusNode(Math.min(index + 1, visibleNodes.value.length - 1));
      break;
    case "ArrowUp":
      event.preventDefault();
      focusNode(Math.max(index - 1, 0));
      break;
    case "Home":
      event.preventDefault();
      focusNode(0);
      break;
    case "End":
      event.preventDefault();
      focusNode(visibleNodes.value.length - 1);
      break;
    case "ArrowRight":
      event.preventDefault();
      if (flatNode.node.children.length && !isExpanded(flatNode.node)) toggleNode(flatNode.node);
      else if (flatNode.node.children.length) focusNode(index + 1);
      break;
    case "ArrowLeft":
      event.preventDefault();
      if (flatNode.node.children.length && isExpanded(flatNode.node)) toggleNode(flatNode.node);
      else {
        const parentIndex = visibleNodes.value.findIndex(({ node }) => node.node_id === flatNode.node.parent_id);
        if (parentIndex >= 0) focusNode(parentIndex);
      }
      break;
    case "Enter":
    case " ":
      event.preventDefault();
      emit("selectNode", flatNode.node);
      break;
    default:
      break;
  }
}

function fileTypeLabel(item: Readonly<ResourceLibraryItem>): string {
  return item.file_type?.toUpperCase() ?? item.extension?.replace(".", "").toUpperCase() ?? "文件";
}

function bytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "暂不可用";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

watch([() => props.selectedNodeId, treeNodesById], ([selectedNodeId, nodes]) => {
  if (!selectedNodeId) return;
  const selected = nodes.get(selectedNodeId);
  if (!selected) return;
  const ancestors = new Set(expandedIds.value);
  let parentId = selected.parent_id;
  while (parentId) {
    ancestors.add(parentId);
    parentId = nodes.get(parentId)?.parent_id ?? null;
  }
  expandedIds.value = ancestors;
}, { immediate: true });

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<template>
  <aside class="scope-nav" aria-label="资料来源上下文">
    <button class="all-resources" :class="{ active: props.selectedNodeId === null }" type="button" @click="emit('selectAll')">
      <span aria-hidden="true">▤</span><span>全部资料</span><strong v-if="props.total !== null">{{ props.total }}</strong><span v-else class="unavailable">暂不可用</span>
    </button>

    <label class="source-search" for="resource-source-search">
      <span class="sr-only">搜索资料来源或文件夹</span>
      <span aria-hidden="true">⌕</span>
      <input id="resource-source-search" v-model="searchInput" placeholder="搜索资料来源或文件夹…" @input="scheduleTreeSearch">
    </label>

    <section class="recent-section" aria-labelledby="recent-resources-heading">
      <h2 id="recent-resources-heading">最近使用</h2>
      <div v-if="props.recentItems.length" class="recent-list">
        <button v-for="item in props.recentItems.slice(0, 5)" :key="item.id" class="recent-item" type="button" :aria-label="`打开资料 ${item.display_name}`" :title="`${item.display_name} · ${item.source_name}`" @click="emit('openRecent', item)">
          <span class="file-icon" :class="`file-icon--${fileTypeLabel(item).toLowerCase()}`" aria-hidden="true">{{ fileTypeLabel(item) }}</span>
          <span>{{ item.display_name }}</span>
        </button>
      </div>
      <p v-else class="quiet-empty">打开资料后会显示在这里</p>
    </section>

    <section class="tree-section" aria-labelledby="resource-sources-heading">
      <h2 id="resource-sources-heading">资料来源</h2>
      <p v-if="props.loading && !props.tree" class="quiet-empty">正在加载资料来源…</p>
      <p v-else-if="activeTreeQuery && !hasTreeSearchResults" class="quiet-empty">没有匹配的资料来源</p>
      <div v-else class="tree" role="tree" aria-label="资料来源树">
        <section v-for="group in displayedGroups" :key="group.node_id" class="tree-group">
          <p class="tree-group-heading">
            <span>{{ groupLabel[group.source_type] ?? group.source_type }}</span>
            <strong v-if="group.descendant_count">{{ group.descendant_count }}</strong>
            <span v-if="group.health === 'unavailable'" class="unavailable">不可用</span>
          </p>
          <template v-for="flatNode in visibleNodes.filter(({ node }) => group.children.some((child) => node.node_id === child.node_id) || group.children.some((child) => child.node_id === node.parent_id || node.node_id.startsWith(`tree:${child.source_id}:`)))" :key="flatNode.node.node_id">
            <div class="tree-row" :style="{ paddingInlineStart: `${8 + flatNode.depth * 16}px` }">
              <button v-if="flatNode.node.children.length" class="tree-toggle" type="button" :aria-label="`${isExpanded(flatNode.node) ? '折叠' : '展开'} ${flatNode.node.name}`" :aria-expanded="isExpanded(flatNode.node)" @click="toggleNode(flatNode.node)"><span aria-hidden="true">›</span></button>
              <span v-else class="tree-spacer" aria-hidden="true"></span>
              <button class="tree-node" :class="{ active: flatNode.node.node_id === props.selectedNodeId }" type="button" role="treeitem" :data-node-id="flatNode.node.node_id" :aria-level="flatNode.depth + 1" :aria-selected="flatNode.node.node_id === props.selectedNodeId" :aria-expanded="flatNode.node.children.length ? isExpanded(flatNode.node) : undefined" @keydown="handleTreeKeydown($event, flatNode)" @click="emit('selectNode', flatNode.node)">
                <span class="node-name">{{ flatNode.node.name }}</span><strong>{{ flatNode.node.descendant_count }}</strong><span v-if="flatNode.node.health === 'unavailable'" class="unavailable">不可用</span>
              </button>
            </div>
          </template>
          <p v-if="!group.children.length" class="quiet-empty group-empty">{{ group.health === 'unavailable' ? '不可用' : '尚未配置' }}</p>
        </section>
      </div>
    </section>

    <div v-if="props.storage" class="storage" :class="{ warning: props.storage.status === 'exceeded' }">
      <span aria-hidden="true">▤</span><span>已使用 {{ bytes(props.storage.total_known_bytes) }}</span><span v-if="props.storage.status === 'exceeded'">空间超限</span>
    </div>
    <button class="manage-sources" type="button" @click="emit('manageSources')">管理资料来源</button>
  </aside>
</template>

<style scoped>
.scope-nav { display:flex; min-width:0; min-height:100%; flex-direction:column; gap:12px; padding:12px 10px; background:var(--surface); }.all-resources,.recent-item,.tree-node,.manage-sources { font:inherit; cursor:pointer; }.all-resources { display:flex; align-items:center; gap:8px; min-height:40px; padding:8px 10px; border:0; border-left:2px solid transparent; border-radius:4px; background:transparent; color:var(--text-primary); font-size:14px; font-weight:650; text-align:left; }.all-resources strong { margin-left:auto; font-size:12px; font-variant-numeric:tabular-nums; }.all-resources.active,.tree-node.active { border-left-color:var(--color-primary); background:var(--color-primary-soft); color:var(--color-primary); }.source-search { display:flex; align-items:center; gap:8px; height:36px; padding:0 9px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--elevated, #fbfcfe); color:var(--text-faint); }.source-search:focus-within { border-color:var(--color-primary); box-shadow:0 0 0 2px var(--color-primary-soft); }.source-search input { width:100%; min-width:0; border:0; outline:0; background:transparent; color:var(--text-primary); font:inherit; font-size:13px; }.recent-section,.tree-section { min-width:0; }.recent-section h2,.tree-section h2 { margin:0 0 6px; color:var(--text-muted); font-size:12px; font-weight:750; }.recent-list { display:grid; gap:2px; }.recent-item { display:flex; align-items:center; gap:7px; min-width:0; min-height:30px; padding:4px 6px; border:0; border-radius:4px; background:transparent; color:var(--text-muted); font-size:12px; text-align:left; }.recent-item:hover,.recent-item:focus-visible { background:var(--color-primary-soft); color:var(--text-primary); outline:2px solid var(--color-primary); outline-offset:1px; }.recent-item > span:last-child { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.file-icon { display:grid; width:20px; height:22px; flex:0 0 auto; place-items:center; border-radius:3px; background:var(--color-primary-soft); color:var(--color-primary); font-size:8px; font-weight:800; }.file-icon--pdf { background:var(--color-danger-soft); color:var(--color-danger); }.file-icon--docx { background:var(--color-primary-soft); color:var(--color-primary); }.file-icon--pptx { background:var(--color-warning-soft); color:var(--color-warning); }.tree { display:grid; gap:8px; }.tree-group { min-width:0; }.tree-group-heading { display:flex; align-items:center; gap:6px; margin:0; padding:4px 6px; color:var(--text-muted); font-size:12px; font-weight:700; }.tree-group-heading strong { margin-left:auto; font-size:11px; font-variant-numeric:tabular-nums; }.tree-row { display:flex; min-width:0; align-items:center; }.tree-toggle,.tree-spacer { display:grid; width:24px; height:32px; flex:0 0 24px; place-items:center; border:0; background:transparent; color:var(--text-muted); }.tree-toggle { cursor:pointer; }.tree-toggle span { transition:transform 120ms ease; }.tree-toggle[aria-expanded="true"] span { transform:rotate(90deg); }.tree-toggle:focus-visible,.tree-node:focus-visible,.manage-sources:focus-visible,.all-resources:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }.tree-node { display:flex; min-width:0; flex:1; align-items:center; gap:6px; min-height:32px; padding:5px 8px; border:0; border-left:2px solid transparent; border-radius:4px; background:transparent; color:var(--text-primary); font-size:13px; text-align:left; }.tree-node:hover { background:var(--surface-muted); }.node-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.tree-node strong { margin-left:auto; color:var(--text-muted); font-size:11px; font-variant-numeric:tabular-nums; }.unavailable { color:var(--text-faint); font-size:11px; font-weight:650; white-space:nowrap; }.quiet-empty { margin:0; color:var(--text-faint); font-size:12px; line-height:1.45; }.group-empty { padding:2px 6px 2px 30px; }.storage { display:flex; align-items:center; gap:6px; margin-top:auto; padding:10px 6px; border-top:1px solid var(--border-subtle); color:var(--text-muted); font-size:12px; }.storage.warning { color:var(--color-warning); }.manage-sources { min-height:36px; border:0; border-top:1px solid var(--border-subtle); background:transparent; color:var(--color-primary); font-size:13px; font-weight:700; text-align:left; }.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0, 0, 0, 0); white-space:nowrap; }@media (max-width:1023px) { .scope-nav { min-height:auto; }.storage { margin-top:0; }}@media (prefers-reduced-motion:reduce) { .tree-toggle span { transition:none; }}
</style>
