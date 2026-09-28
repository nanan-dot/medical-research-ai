# 期刊指标后端

本能力只管理用户有权使用的本地 UTF-8 CSV，不随应用分发真实 JCR、IF 或中科院数据。论文检索快照 `items_json` 保持不可变，指标在读取结果页时从当前激活批次动态装配，且不参与论文评分或排序。

## CSV

必需列为 `journal_name,metric_year`。可选列为：

```text
issn,eissn,issn_l,impact_factor,impact_factor_year,jcr_best_quartile,jcr_year,
wos_indexes,wos_year,cas_quartile,cas_year,cas_category,is_cas_top,warning_status
```

`wos_indexes` 用逗号或分号分隔，只允许 `SCIE/SSCI/ESCI/AHCI`。文件必须为 UTF-8（允许 BOM），默认上限 32 MiB，可用 `JOURNAL_METRIC_IMPORT_MAX_BYTES` 调整。

示例（明显虚构，仅说明格式）：

```csv
journal_name,issn,metric_year,impact_factor,jcr_best_quartile,wos_indexes
Example Journal,2049-3630,2025,1.2,Q1,ESCI
```

## API

- `POST /api/v1/journal-metrics/imports/preview`：multipart 字段 `file`。
- `POST /api/v1/journal-metrics/imports/commit`：重新上传同一 `file`，同时提交 `expected_file_hash`、`provider`、`provider_version`、`edition_year`、`license_provenance`。
- `GET /api/v1/journal-metrics/imports?offset=0&limit=20`：批次列表。
- `POST /api/v1/journal-metrics/imports/{id}/activate`：事务内切换同来源同年度版本。
- `POST /api/v1/journal-metrics/imports/{id}/archive`：归档且不自动回退旧版。
- `GET /api/v1/literature-search/{result_id}/items/{pmid}/journal-metrics`：最近十年详情与精确发表年度指标。

PubMed 检索在最终执行边界强制追加滚动最近 15 个自然年的日期条件；任务保存实际发送的查询，因此重跑沿用原日期快照。
