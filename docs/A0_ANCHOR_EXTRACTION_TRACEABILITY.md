# A0 实施与验收报告

日期：2026-08-31。代码仓库：D:/AI_project/rag_medicine。

## 当前结论

A0 的代码实现、本机工具配置、数据库迁移和专项验证已完成；**不能宣称全仓最终验收通过**，因为现有前端还有 3 个类型错误和 1 个 lint 错误。已向用户请求最小跨页面修复授权，尚未收到授权，未修改这些页面。

本次按 acceptance-testing 将原始设计转成验收条件，增加反例并修复实现；按 FastAPI/Python 分层拆分查询、进程、暂存、发布、任务生命周期；独立 Node 工具采用 npm、严格 TypeScript、Zod 输入校验。完整条件见 docs/A0_ACCEPTANCE_CRITERIA.md。

## 验证结果

| 范围 | 实际命令（仓库根目录，除另注） | 实际结果 |
|---|---|---|
| A0 最终专项 | python -m pytest tests/modules/document_anchor -q --junitxml=data/anchor_validation/a0-pytest-final.xml | **83 passed**，99.40 秒 |
| 完整后端回归 | python -m pytest -q --junitxml=data/anchor_validation/full-pytest-final.xml | **972 passed, 13 skipped**，645.63 秒 |
| 后端 lint | python -m ruff check app tests alembic tools/pdf_textitem_extractor/validate_corpus.py | All checks passed |
| 类型检查 | python -m mypy app/modules/document_anchor app/cli app/integrations | 47 source files，无错误 |
| Python 编译 | python -m compileall -q app/modules/document_anchor app/cli/document_anchor_worker.py | exit 0 |
| 工具构建 | npm run build（tools/pdf_textitem_extractor） | exit 0 |
| 工具 lint | npm run lint（同上） | exit 0 |
| 工具类型 | npm run typecheck（同上） | exit 0 |
| 工具测试 | npm test（同上） | 3 passed |
| 锁文件 | uv lock | Resolved 157 packages，新增 psutil 7.2.2 |
| 迁移往返 | tests/modules/document_anchor/test_migration.py | upgrade → downgrade → upgrade 通过，保留既有 sentinel 数据 |
| 本机数据库 | python -m alembic upgrade head / current | e14d8a06c923 (head) |
| 本机能力探测 | PdfTextItemExtractor().probe() | 协议 1.1 / extractor 1.1.0 / PDF.js 6.2.108 / norm-2 |
| worker 入口 | python -m app.cli.document_anchor_worker --once | exit 0，本机 A0 队列为空 |
| 跨平台及阅读器 | tools/pdf_textitem_extractor/validate_corpus.py（下述 3 份 PDF） | 45 页，Windows 重跑、Linux、阅读器对照全部一致 |
| 前端 typecheck | npm run typecheck（frontend） | **失败，3 个既有错误** |
| 前端 lint | npx eslint .（frontend） | **失败，1 error、2078 warnings** |
| 前端 build | npm run build（frontend） | **失败，同 3 个类型错误** |

后端执行均使用 F:/software/programme/Anaconda/envs/med-research-ai/python.exe，并先清空 PYTHONPATH。完整回归与随后新增/重构后的 A0 专项分别执行，计数不是相加后的单次全量结果。13 个跳过项为现有套件的条件性测试，未将跳过记作通过。保留一条现有 Starlette/httpx 弃用警告。

第一轮全量为 958 passed、13 skipped、1 failed；失败由本轮新增迁移 ID 与旧迁移重名导致，已改为唯一 ID e14d8a06c923 后重跑完整套件得到上述全绿结果。早期测试也确实暴露并修复了数字哈希、软连字符丢失、EOL、空页误判、取消状态、任务详情类型、Windows 字体路径、Symbol 字体未知度量和孤儿进程问题，没有把这些失败记作通过。

## 验收追踪

| 条件 | 行为证据 | 状态 |
|---|---|---|
| AC01 受控 PDF 与独立工具链 | test_real_pdf、test_acceptance 的真实 PDF.js 提取；DocumentPreview 原有安全测试随全量回归通过 | PASS |
| AC02 不可用/不兼容能力 | test_api_contract、test_runner：503、安全错误、启动失败清理；startup probe | PASS |
| AC03 正常协议及索引 | test_protocol、test_acceptance；独立 reader_items.mjs 对照 | PASS |
| AC04 损坏/篡改/不完整流 | test_protocol 参数矩阵；test_runner 的 exit0/缺 trailer/超行/header 错配 | PASS |
| AC05 确定性/版本身份 | 跨 Node/Python binary64 黄金向量，所有指纹输入变动，45 页 Windows/Linux 回归 | PASS |
| AC06 NFC/UTF16/连接符 | test_hardening、test_protocol：emoji、组合字符重排、Hangul、软连字符、原始空白、synthetic 范围 | PASS |
| AC07 技术质量 | test_real_pdf：空白、栅格扫描、混合、旋转和希腊字母；quality 指标与复核门禁 | PASS |
| AC08 并发/租约 | test_acceptance 双 worker；test_lifecycle 并发提交、过期领取、续租、旧持有者 fencing | PASS |
| AC09 失败/取消/重试 | test_lifecycle：失败重新执行、自动重试上限、显式重试、运行中/排队取消；test_runner：总/空闲超时、父进程提前退出 | PASS |
| AC10 原子发布/诊断 | test_lifecycle：第二页发布失败全回滚、新版本保留旧页、强制诊断不重复/不改原内容 | PASS |
| AC11 文件版本变化 | test_lifecycle：提取中改文件拒绝发布、元数据新版本不返回旧 manifest；发布前重查路径/知识源 | PASS |
| AC12 查询作用域与限额 | test_lifecycle、test_api_contract：跨文档拒绝、停用知识源拒绝、未完成正文不可见、每批≤200 项 | PASS |
| AC13 安全/资源/进程清理 | test_real_pdf：PDF JavaScript/附件惰性、损坏/加密/资源限额；test_runner：真实子进程与孤儿后代清理 | PASS |
| AC14 迁移 | test_migration 与完整 library migration 回归；本机迁移前完整备份 | PASS |
| AC15 授权论文/跨平台 | 2 篇开放许可医学论文 + 复杂版式自制 PDF，共 45 页、7975 TextItems | PASS（限已列明样本） |
| SQLite 有界批次 | test_batch_publish：1201 项实际拆成 500 / 500 / 201，完整写入 | PASS |
| 全仓前端门禁 | 下述 4 个既有错误 | BLOCKED，待用户授权 |

验收没有覆盖所有出版商/所有 PDF，也没有把“支持上限”当作极限负载性能承诺。技术 ready 不等于医学专家审核，A1 段落/翻译/语义工作没有实现。

## 黄金 PDF 及许可

| 文件 | 来源/许可 | 页数 | TextItems | 文档内容哈希 |
|---|---|---:|---:|---|
| plos-1004416.pdf | Ciccone 等，PLOS Medicine；CC BY；[出版方 PDF](https://journals.plos.org/plosmedicine/article/file?id=10.1371%2Fjournal.pmed.1004416&type=printable) | 24 | 2542 | 1373b167875efae4b71affaaeb957c4ff38d1046ca3130bc02f95930afad387d |
| bmc-03383-2.pdf | Day 等，BMC Medicine；开放许可原文；[PMC 文章](https://pmc.ncbi.nlm.nih.gov/articles/PMC11015654/)、[Europe PMC PDF](https://europepmc.org/articles/PMC11015654?pdf=render) | 17 | 5390 | bdc68fd229f5753e0a1e113fd81eedd4186bf33235e4279941e83ba72b1dd70c |
| complex.pdf | 本任务自制，双栏/希腊字母/空白/扫描/旋转页，测试代码可再生成 | 4 | 43 | 93890aa707eb7295e07a56191d94ba251da0a6ce58c0503cc617bd41d0ce2f05 |

SHA256 原文件身份、逐页哈希、质量标记和完整对照结果存于 data/anchor_validation/corpus-report.json。原 PDF 未改写，保存在被 gitignore 排除的本地 data/anchor_validation；源码不包含第三方论文全文。

Windows 与 Ubuntu/WSL 使用 Node 24.18.0、同版 PDF.js 和工具安装包。Linux Node 压缩包 SHA256 为 55aa7153f9d88f28d765fcdad5ae6945b5c0f98a36881703817e4c450fa76742，已与 nodejs.org 的 SHASUMS256.txt 核对。三份文件全部通过两次 Windows 提取、原前端 PDF.js 独立读取及 Linux 提取对照；耗时包括重复和跨平台调用，不是生产 SLA。

## 实际文件清单

新增/完成：

- app/modules/document_anchor/：__init__.py、contract.py、extractor_runner.py、fingerprint.py、input_validation.py、model.py、normalization.py、page_builder.py、publisher.py、queries.py、quality.py、repository.py、router.py、schema.py、service.py、staging.py、task_lifecycle.py、toolchain.py、windows_job.py、worker.py。
- app/cli/document_anchor_worker.py。
- alembic/versions/a0a1b2c3d4e5_add_document_anchor_revisions.py、e14d8a06c923_anchor_mapping_quality.py。
- tools/pdf_textitem_extractor/：package.json、package-lock.json、tsconfig.json、eslint.config.mjs、README.md、src/cli.ts、contract.ts、checksum.ts、extract-document.ts、extract-page.ts、兼容入口 cli.mjs、tests/contract.test.mjs、validate_corpus.py。
- tests/modules/document_anchor/：支持夹具、协议、规范化、真实 PDF、API、任务生命周期、并发、迁移、批量写入和进程清理测试。
- docs/A0_ACCEPTANCE_CRITERIA.md 与本报告。

集成修改（保留这些文件原有的用户改动）：

- app/api/v1/__init__.py：注册 A0 路由。
- app/core/models.py：注册三张 A0 表。
- app/core/config.py、.env.example：提取配置及安全限额。
- app/main.py：启动能力探测，不使其他能力因 A0 不可用而无法启动。
- app/modules/task/service.py：仅对 A0 task_type 分派取消/重试领域同步。
- tests/test_database.py：三张新表的 schema 断言。
- pyproject.toml、uv.lock：开发测试所需 Pillow、psutil。
- frontend/package.json、frontend/package-lock.json：仅将 PDF.js 从范围改为精确 6.2.108，没有改页面。
- 两个旧迁移 a0c1d2e3f4g5_add_history_execution_changes.py、g0b1c2d3e4f5_allow_exploratory_recommendations.py：仅整理 import 空行以通过仓库 lint，不改变迁移逻辑。
- 本机 .env：增加独立构建工具的 JSON 命令数组；未读取/改写其他密钥配置。

## 数据库与运行

三张表：document_anchor_revisions、document_source_pages、document_source_text_items。

旧 A0 schema 已部署，因此映射、字体样式、质量指标、bbox 和当前版本唯一约束通过**追加迁移**引入，未静默重写已应用迁移。数据库当前 head：e14d8a06c923。

迁移前备份：D:/AI_project/rag_medicine/data/anchor_validation/app-before-e14d8a06c923.db，SQLite integrity_check=ok。迁移前本机没有 A0 Revision/Task，未改动任何既有文档正文。没有删除用户文档。

本机 .env 已配置构建后的独立工具；API 服务加载新代码后可提供能力。需要执行队列时，在后端之外运行：

```powershell
Set-Location D:/AI_project/rag_medicine
$env:PYTHONPATH=''
& 'F:/software/programme/Anaconda/envs/med-research-ai/python.exe' -m app.cli.document_anchor_worker
```

本轮仅实测 --once，没有安装后台常驻服务、计划任务或重启其他进程。安装、调用、协议、退出码及查询约束见 tools/pdf_textitem_extractor/README.md。

Windows 清理使用 [Microsoft Job Objects 的 kill-on-close 语义](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)，并有父进程先退出的真实反例验证；不能用单独 process.kill() 冒充进程树清理。

## 尚未获授权的全仓阻断

- frontend/src/views/LiteratureSearch/StrategyReadySection.vue:13：混用 ?? 和 && 缺少括号。
- frontend/src/views/LiteratureSearch/StrategyTermsMeshSection.vue:88：string 不能赋给限定类别联合类型。
- frontend/src/views/LiteratureSearch/StrategyTermsMeshSection.vue:170：tag 不是合法 IconName。
- frontend/src/components/PaperResults/PaperResults.vue:15：no-unused-expressions。

这些页面在本轮开始前已处于用户的未提交改动中。本次没有修改它们。仓库 AGENTS.md 要求跨页面改动事先授权，因此全仓门禁不能被标记为完成，下一步只需用户确认是否允许最小修复上述四处。

## 范围与未实测

- 已验证 Windows 和 Ubuntu/WSL 的上述 45 页，不代表 macOS、全部 Linux 发行版或全部医学期刊排版均经过验证。
- 500 页、50000 items/page、输出/文件限额是拒绝策略；未完成这些组合上限下的长时间压力与吞吐 SLA 验证。
- 队列无限常驻、服务重启、实际多用户权限平台不属于本次实测；当前授权沿用本地单用户知识源模型。
- bbox/覆盖率是明确标注的几何估计；重叠比较达到预算会记录 lower_bound 并要求复核。
- Symbol 等字体的缺失度量保存为 null 并报告 UNKNOWN_FONT_METRICS，不虚构字体数值。
