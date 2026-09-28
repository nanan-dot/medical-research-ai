# A0 PDF.js TextItem 提取器

独立运行、独立安装；PDF.js 精确版本 6.2.108。协议 1.1、提取器 1.1.0、规范化 textitem-norm-2。

## 安装与验证

在本目录执行：

```powershell
npm ci
npm run build
npm run typecheck
npm run lint
npm test
node dist/cli.js --version-json
```

后端配置 JSON 参数数组，路径包含空格也不会经过 shell：

```dotenv
PDF_TEXTITEM_EXTRACTOR_COMMAND='["node", "D:/AI_project/rag_medicine/tools/pdf_textitem_extractor/dist/cli.js"]'
PDF_TEXTITEM_EXTRACTOR_TIMEOUT_SECONDS=120
PDF_TEXTITEM_EXTRACTOR_IDLE_TIMEOUT_SECONDS=30
PDF_TEXTITEM_EXTRACTOR_MAX_FILE_BYTES=104857600
PDF_TEXTITEM_EXTRACTOR_MAX_PAGES=500
PDF_TEXTITEM_EXTRACTOR_MAX_ITEMS_PER_PAGE=50000
PDF_TEXTITEM_EXTRACTOR_MAX_LINE_BYTES=16777216
PDF_TEXTITEM_EXTRACTOR_MAX_OUTPUT_BYTES=134217728
```

从仓库根目录启动 worker：

```powershell
$env:PYTHONPATH=''
& 'F:/software/programme/Anaconda/envs/med-research-ai/python.exe' -m app.cli.document_anchor_worker
```

`--once` 处理至多一个任务，用于运维检查。任务不会在 HTTP 请求中解析 PDF；运行服务时须同时运行 worker。

## 协议与身份

- stdout 只输出 header/page/trailer NDJSON；stderr 只输出安全错误码。
- header 立即校验工具链、请求 ID 和文件 SHA256。
- page 哈希包含原始 TextItem、全部声明的有限几何、受限 styles 和栅格证据字段；哈希字段自身不参与计算。
- canonical projection 对所有 JSON 数字编码成 `{"$f64":"IEEE754大端16位十六进制"}`，把负零归一为正零；对象键按 UTF-16 顺序排序，数组顺序保留。仅在受限协议 schema 上使用，不是通用 JSON 签名格式。
- trailer 包含按页序组合的文档哈希；没有完整 trailer 或 exit 非零都不能发布。
- `disable_normalization=false` 与当前浏览器阅读器默认一致；`include_marked_content=true` 保留 source_array_index，非 TextItem 对象过滤后才生成连续 item_index。
- 系统字体关闭；标准字体、CMap 和 WASM 来自本工具的锁版依赖。PDF.js 6 不再接受旧的 isEvalSupported 参数；工具不读取/执行 PDF JavaScript、动作或附件，不使用外部 URL。
- PDF.js 对部分字体用 NaN 表示缺失的可选 ascent/descent：协议将其标为 null，并报告 UNKNOWN_FONT_METRICS；TextItem 几何 NaN/Infinity 仍拒绝。

## 规范化与质量

保留原始 TextItem 字符串。派生文本只做 NFC、移除明确控制字符并保留质量计数；空白、软连字符及医学符号保留，不跨项合断词。页连接依据前项 EOL、已有空白、方向和基线间距，新增字符明确标为 synthetic。

所有页范围和 raw_start/raw_end 都使用 UTF-16 code unit；item 的 char_map 把规范化范围映射回原始 TextItem。NFC 多对一/重排的源范围是保守包含范围，不声称每个 UTF-16 单元都独立对应一个字符。

质量是技术诊断：覆盖率为 AABB 面积估计，不是像素级并集；极端重叠达到比较预算后会明确记录 lower_bound 并要求复核。扫描判定须同时存在栅格绘图和无可选择文字。`ready` 不等于医学审核。

## 进程、事务和重试

Python 逐行校验并写入受控临时文件，单页正文有硬上限。成功/失败/取消均关闭暂存与 options；Windows 使用 kill-on-close Job Object，POSIX 使用独立进程组。

提取期间不持有数据库写事务。每秒续租/检查取消；发布前使用 Task 条件更新核验租约，随后原子写入页面与 500 项一批的 TextItem、最终指纹、Revision 状态和 Task 成功。SQLite 部分唯一索引保证每文档一个当前版本。失败回滚全部页项；诊断重跑只比较既有不可变指纹。

瞬时失败最多自动尝试 3 次，退避 1、2 秒；永久文件/加密/资源错误不自动重试。统一任务 API 支持取消与显式重试，显式重试重新获得有限预算。

## 查询接口

- `POST /api/v1/documents/{document_id}/anchor-revisions`：body 为 expected_file_hash、force_new_toolchain_run；复用完成版本 200、排队 202、冲突 409、能力不可用 503。
- `GET /api/v1/documents/{document_id}/anchor-manifest`
- `GET /api/v1/document-anchor-revisions/{revision_id}`
- `GET /api/v1/document-anchor-revisions/{revision_id}/pages/{page_number}/quality`
- 同时提供显式 document_id 作用域的 quality 路由。
- `GET /api/v1/document-anchor-capability`
- 内部 `DocumentAnchorService.text_items(document_id, revision_id, page_number, start, limit)`：每批 1–200 项，只读已完成版本，没有整篇正文 HTTP 导出接口。

授权沿用本地单用户应用的知识源控制：路径须位于启用知识源内，查询校验 Document/Revision 归属。此项不是新增的多租户认证系统。

## 黄金 PDF 回归

从仓库根运行 `pytest tests/modules/document_anchor`。测试包括真实生成 PDF、前端阅读器包独立对照、进程树清理、协议破坏、租约/重试/取消、事务回滚和迁移往返。开发依赖另需 Pillow、psutil（用于自制栅格夹具及确认子进程确实退出）。

`validate_corpus.py` 可对本地授权 PDF 进行重复运行和阅读器对照；可选 `--linux-node`、`--linux-cli` 用于 Windows+WSL 三方比较。第三方 PDF 保存在 gitignore 的 data/anchor_validation，不随源码提交；来源和许可见 docs/A0_ANCHOR_EXTRACTION_TRACEABILITY.md。
