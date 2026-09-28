# Search strategy workspace acceptance traceability

| AC | Evidence | Status |
| --- | --- | --- |
| 01 | `SearchEntryView.test.ts`; strategy draft API test | 部分通过：受控浏览器链路待补测 |
| 02 | `test_strategy_draft_persists_and_rejects_stale_revision` | 通过 |
| 03 | `useStrategyAutosave.test.ts` | 通过 |
| 04 | `useStrategyAutosave.test.ts` | 部分通过：网络失败重试待补测 |
| 05 | autosave 409 test；draft API test | 通过 |
| 06 | draft API test | 部分通过：研究问题专项待补测 |
| 07 | term mutation API tests | 部分通过：Query UI stale 待补测 |
| 08 | `test_patch_fingerprint_retains_existing_term_identity` | 部分通过：飞行中响应待补测 |
| 09 | `test_strategy_terms_can_unlock_and_delete`; `StrategyTermsPanel.test.ts` | 通过 |
| 10 | `test_strategy_terms_preserve_locks_and_versions_are_immutable` | 通过 |
| 11 | structured `StrategyTermRead` contract | 待 warning 专项测试 |
| 12 | MeSH verified API test | 通过 |
| 13 | MeSH unavailable/not_found API tests | 通过 |
| 14 | MeSH partial failure API test | 部分通过：工作台隔离状态待补测 |
| 15 | query validation and invalid field tag API tests | 通过 |
| 16 | draft patch API test | 部分通过：前端 stale 待补测 |
| 17 | PubMed Count API test | 通过 |
| 18 | Count PubMed failure API test | 通过 |
| 19 | Count stale fingerprint API test | 部分通过：飞行中响应待补测 |
| 20 | `StrategyVersionPanel.test.ts`; separate strategy model | 通过 |
| 21 | strategy version API test | 通过 |
| 22 | strategy version idempotency test | 通过 |
| 23 | strategy comparison API/component tests | 通过 |
| 24 | `StrategyVersionPanel.vue` conditional compare action | 待专项测试 |
| 25 | execute blocking query API test | 通过 |
| 26 | execute service reuse API test | 部分通过：浏览器跳转待补测 |
| 27 | `LiteratureSearchView.test.ts::prevents_duplicate_strategy_execution_while_the_first_request_is_active` | 通过（前端）；后端并发待补测 |
| 28 | `StrategyStepper.test.ts`; workspace component tests | 功能部分通过；视觉复刻已由用户取消，不在本轮范围 |
| 29 | Stepper select test | 部分通过：scroll observer 待补测；视觉滚动编排已由用户取消 |
| 30 | component semantic button tests | 部分通过：Dialog/focus 待补测 |
| 31 | 六视口功能截图：`docs/frontend-rebuild/screenshots/literature-search-entry/` | 基础无横向溢出待确认；视觉复刻/几何门禁已由用户取消 |
| 32 | route/component tests | 待受控后端浏览器验收 |

Status labels are intentionally conservative. This table becomes green only after the referenced test has been run successfully.
