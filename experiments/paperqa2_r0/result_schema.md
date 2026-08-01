# PaperQA2 R0 result schema

The runtime JSON is a sanitized record, not a serialized `Docs` object. It stores the fixed package/model configuration, source PDF filename and SHA-256, timings, answer fields, retrieved source title/citation/page range, and evidence excerpts capped at 600 characters. It never stores embeddings, API keys, environment variables, or the complete paper text.

`capabilities` records machine-checkable observations. `manual_source_pdf_page` is a human verification pointer and is not inferred as a publication page number.

The committed `result.sample.json` is produced from a real run with machine-specific absolute paths excluded. Runtime results remain under ignored `data/paperqa2_r0/`.
