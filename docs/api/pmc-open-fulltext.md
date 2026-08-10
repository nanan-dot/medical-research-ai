# PMC 官方开放全文 API

## 边界

本接口只会访问 PMC 官方 OAI-PMH 与 OA Web Service；不会抓取 PMC 普通网页、期刊网站或付费墙。PMCID 仅是待核验的输入，不是下载授权。

服务按单请求串行限流（最多 3 请求/秒），并仅对网络、限流和服务端短暂故障重试。文件下载使用流式写入 `OPEN_FULLTEXT_DIR/documents/`，先检查官方地址、大小、PDF 签名和 PDF 结构，再创建 `Document`、资产及正式收藏关联。

## `POST /api/v1/library-items/{id}/fulltext-retrievals`

```json
{ "pmcid": "PMC1234567" }
```

成功的含义很严格：

1. PMC OAI 返回的 PMCID 与输入相同，且 PMID 或 DOI 与收藏项精确匹配；
2. OAI 与 OA Web Service 都返回了许可信息；
3. OA Web Service 返回受限于 `ftp.ncbi.nlm.nih.gov/pub/pmc/` 的官方 PDF 地址；
4. 下载的文件未超过 `MAX_OPEN_FULLTEXT_PDF_BYTES`、具有 PDF 签名且能被 `pypdf` 读取。

只有上述步骤都成功，`library_items.fulltext_status` 才会成为 `local_pdf_available`。响应包含可审计的 `source_url`、许可、SHA-256、文档 ID 与时间。失败时会新增一条尝试记录，使用 `identity_mismatch`、`license_unverified`、`pdf_unavailable`、`network_error`、`rate_limited`、`content_invalid` 或 `storage_failed` 区分原因；不会创建或关联伪造的全文。

## `GET /api/v1/library-items/{id}/fulltext-retrievals`

按最新优先返回该收藏项的全部官方获取尝试，供界面展示成功、拒绝和失败的真实状态。

## 配置

- `OPEN_FULLTEXT_DIR`：受控全文根目录，默认 `./data/open_fulltext`。
- `MAX_OPEN_FULLTEXT_PDF_BYTES`：单 PDF 上限，默认 100 MiB。
- `PMC_REQUEST_TIMEOUT_SECONDS` / `PMC_DOWNLOAD_TIMEOUT_SECONDS`：官方元数据与下载超时。
- `PMC_CONTACT_EMAIL`：建议填写的联系邮箱；为空时尝试复用 `PUBMED_EMAIL`。

真实网络集成测试默认不执行；自动化测试使用本地官方响应替身，不会下载或保存任何真实论文。
