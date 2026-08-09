# 评测数据集指南

评测集采用 JSONL；每行一个人工审核题目。不得保存论文全文、API 密钥或未经授权的敏感材料。

每题必须有 `question_id`、`question_type`、`difficulty`、`review_status`、`dataset_version` 和 `split`。可回答题还必须具备 `answer` 和本系统已有的 `evidence_document_id`。`no_answer=true` 的题不得填写参考答案。

开发集和测试集应使用不同文件，测试集不得用于调参。可通过 `load_jsonl(path, split=...)` 获取已校验题目与稳定 SHA-256 哈希。
