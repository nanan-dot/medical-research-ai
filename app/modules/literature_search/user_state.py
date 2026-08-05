"""literature_search — 用户态（saved / read_status / tags / 自定义序号）纯逻辑。

manage-refs 融合点：已保存 / 已读 / 标签 属于用户态数据，与检索快照
（items_json）分离。快照不可写回，因此用户态独立存储，GET 结果时按 PMID
实时并入，筛选时可组合"是否已保存 / 是否已读 / 标签"条件。

本模块只包含纯函数（标签规范化、默认值），不触碰数据库；持久化在
repository.py，业务编排在 service.py。custom 排序序号使用单条记录的
custom_order_index 列（见 model.LiteratureSearchItemState），不需要全量
PMID 顺序 JSON 的序列化/反序列化。
"""

from __future__ import annotations

import json
from collections.abc import Iterable

# 标签规范：单个标签最大长度与最大数量。防止超长标签拖垮前端渲染与查询。
_MAX_TAG_LENGTH = 50
_MAX_TAG_COUNT = 20

DEFAULT_READ_STATUS = "unread"


def normalize_tags(tags: Iterable[str] | None) -> list[str]:
    """标签规范化：去空、去首尾空白、去重、限长、限数。

    设计说明：标签是用户自由输入的短文本，规范化后存入 JSON 列；比较时
    用规范化后的值，避免 "cancer" 与 " cancer " 视为两个标签。
    """
    if not tags:
        return []
    seen: list[str] = []
    for tag in tags:
        cleaned = " ".join(tag.split())[:_MAX_TAG_LENGTH]
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
        if len(seen) >= _MAX_TAG_COUNT:
            break
    return seen


def serialize_tags(tags: list[str]) -> str:
    """标签列表序列化为 JSON 字符串（存 DB Text 列）。"""
    return json.dumps(normalize_tags(tags), ensure_ascii=False)


def deserialize_tags(raw: str | None) -> list[str]:
    """从 JSON 字符串反序列化标签列表；空或非法输入返回空列表。

    设计说明：旧数据或手工编辑可能产生非法 JSON，这里兜底返回空列表，
    不抛异常导致整页结果无法加载。
    """
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(value, list):
        return []
    return normalize_tags(str(tag) for tag in value)


def default_state() -> tuple[bool, str, list[str]]:
    """返回用户态默认值：(saved=False, read_status='unread', tags=[])。"""
    return False, DEFAULT_READ_STATUS, []
