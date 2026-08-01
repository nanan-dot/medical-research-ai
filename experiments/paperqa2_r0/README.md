# R0-WP05 PaperQA2 independent experiment

This experiment validates `paper-qa==2026.3.18` outside the FastAPI/business layers. It uses only local Ollama (`qwen3:4b` plus `nomic-embed-text`) and a public, text-extractable PLOS Medicine PDF. No cloud fallback is configured.

## Inputs and environment

- Public PDF: DOI `10.1371/journal.pmed.1004335`; place it at `data/paperqa2_r0/plos-medicine-carrs-followup.pdf`.
- Verified SHA-256: `b6edeac8ee9ebad3faf4672c9334241d0161305e8c626ca5cf9ea47e7d1b5c1e`.
- Package: install `requirements.lock` in an isolated Python 3.13 environment.
- Local source reference supplied for API review: `F:\AIxiangguanneirong\Codex\codex-skill-yasuobao\paper-qa-main`. It is a `main` snapshot without SCM metadata, so it is not the locked runtime artifact.

## Reproducible commands

```powershell
$env:PYTHONPATH=''
& 'C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe' experiments\paperqa2_r0\run.py --output data\paperqa2_r0\result-first.json
& 'C:\Users\ADMIN\.paperqa-codex-venv\Scripts\python.exe' experiments\paperqa2_r0\run.py --output data\paperqa2_r0\result-reused.json
```

The first run builds `data/paperqa2_r0/index/paperqa-docs.pkl`; the second loads it only when the PDF hash and PaperQA version match. Pickle is unsafe for untrusted input, so the script restricts the index to this ignored experiment data directory. Delete the local index and rebuild it if its provenance is uncertain.

The factual question asks for cumulative first microvascular and macrovascular events during 6.5 years and their group split. Verify the answer against PDF page 11 (PDF viewer numbering): 507 total, 233 in the intervention group, and 274 in usual care.

## Known issues

- PaperQA exposes chunk page ranges (for example `pages 4-5`), not always a single pinpoint page.
- Small local models may vary in wording and citation formatting; factual numbers and retrieved evidence must still be manually checked.
- The index format is version-bound and Python-pickle-based, not a portable long-term knowledge-base format.
- Scanned PDFs require OCR and are outside this work package.
- Windows environments with a global `PYTHONPATH` must clear it before invoking Python.
