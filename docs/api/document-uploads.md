# 单 PDF 上传 API

## `POST /api/v1/document-uploads`

以 `multipart/form-data` 提交唯一的 `file` 字段。只接受 MIME 类型为
`application/pdf`（兼容 `application/x-pdf`）且扩展名为 `.pdf` 的文件。

- 默认大小上限为 50 MiB，可通过 `MAX_UPLOAD_PDF_BYTES` 配置；超过上限返回 `413`。
- 服务端流式计算 SHA-256，在临时目录完成签名和 PDF 结构校验后，才移动到
  `UPLOAD_DIR/documents/`；数据库仅保存该根目录内的相对路径。
- 上传完成后创建 `documents` 和 `document_assets` 的一对一记录，解析状态为
  `pending`。本阶段不自动解析；响应中的 `parse_trigger_url` 是已有解析触发接口。

请求示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/document-uploads \
  -F "file=@./paper.pdf;type=application/pdf"
```

成功时返回 `201 Created`，包含 `document`、资产元数据和：

```json
{
  "auto_parse_started": false,
  "parse_trigger_url": "/api/v1/documents/123/parse"
}
```

常见错误码：

- `invalid_pdf_upload`：文件数量、文件名、扩展名、MIME 或 PDF 结构不合法。
- `pdf_upload_too_large`：文件超过当前配置的大小上限。
- `pdf_upload_storage_failed`：受控存储写入失败。
