# ADR-001: Fix the R0 PaperQA2 experiment version

- Status: Accepted
- Date: 2026-08-02

## Decision

Use `paper-qa==2026.3.18` in an isolated Python 3.13 environment for R0-WP05. Use local Ollama `qwen3:4b` for generation and `nomic-embed-text` for embeddings. Disable online document-detail lookup and do not configure any cloud fallback.

The user-provided `paper-qa-main` source snapshot is retained as an API reference. It lacks `.git` SCM metadata and therefore cannot establish an immutable release identity; it is not used as the version lock.

## Consequences

This keeps PaperQA's large and rapidly changing dependency graph outside the application environment, makes the successful distribution explicit, and preserves a reproducible experiment. Its local pickle index is trusted, version-specific experimental state and must not be accepted from another source or promoted directly into business infrastructure.
