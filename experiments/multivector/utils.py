from dataclasses import dataclass

ALLOWED_FIELDS = frozenset({"title", "abstract", "methods", "results", "conclusion", "summary", "entity"})

@dataclass(frozen=True)
class VectorPlan:
    fields: tuple[str, ...]
    dimension: int
    document_count: int
    def __post_init__(self) -> None:
        if not self.fields or len(set(self.fields)) != len(self.fields): raise ValueError("fields must be non-empty and unique")
        if any(field not in ALLOWED_FIELDS for field in self.fields): raise ValueError("unsupported vector field")
        if self.dimension <= 0 or self.document_count < 0: raise ValueError("dimension and document_count are invalid")
    def estimated_vector_count(self) -> int: return len(self.fields) * self.document_count
    def estimated_bytes(self) -> int: return self.estimated_vector_count() * self.dimension * 4

    def report(self, *, recall_at_k: float | None = None, latency_ms: int | None = None) -> dict[str, object]:
        return {"fields": self.fields, "dimension": self.dimension, "document_count": self.document_count, "estimated_vectors": self.estimated_vector_count(), "estimated_bytes": self.estimated_bytes(), "recall_at_k": recall_at_k, "latency_ms": latency_ms}
