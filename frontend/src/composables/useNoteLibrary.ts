import { computed, shallowRef } from "vue";
import { DEFAULT_NOTE_FILTERS, noteLibraryApi, type NoteFacets, type NoteFilters, type NotePage, type NoteRead } from "../api/noteLibrary";

export function useNoteLibrary() {
  const page = shallowRef<NotePage | null>(null); const facets = shallowRef<NoteFacets | null>(null); const selected = shallowRef<NoteRead | null>(null); const loading = shallowRef(false); const error = shallowRef<string | null>(null);
  let controller: AbortController | null = null; let sequence = 0;
  const items = computed(() => page.value?.items ?? []);
  async function load(filters: NoteFilters): Promise<void> { const id = ++sequence; controller?.abort(); controller = new AbortController(); loading.value = true; error.value = null; try { const [nextPage, nextFacets] = await Promise.all([noteLibraryApi.list(filters, controller.signal), noteLibraryApi.facets(filters, controller.signal)]); if (id !== sequence) return; page.value = nextPage; facets.value = nextFacets; } catch (cause) { if (id !== sequence || (cause instanceof DOMException && cause.name === "AbortError")) return; error.value = cause instanceof Error ? cause.message : "笔记库暂时无法加载"; } finally { if (id === sequence) loading.value = false; } }
  async function select(noteId: number | null): Promise<void> { selected.value = null; if (!noteId) return; try { selected.value = await noteLibraryApi.get(noteId); } catch (cause) { error.value = cause instanceof Error ? cause.message : "笔记详情暂时无法加载"; } }
  return { page, facets, selected, items, loading, error, load, select, cancel: () => { sequence += 1; controller?.abort(); }, defaults: DEFAULT_NOTE_FILTERS };
}
