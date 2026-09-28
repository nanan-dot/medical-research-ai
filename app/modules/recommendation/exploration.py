"""从实际检索式构造探索证据；不把召回成功等同于主题相关。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.v5_query import QueryTerm

_FIELDS = {
    "title": ("pubmed_title",), "ti": ("pubmed_title",),
    "abstract": ("pubmed_abstract_results",),
    "title/abstract": ("pubmed_title", "pubmed_abstract_results"),
    "tiab": ("pubmed_title", "pubmed_abstract_results"),
    "mesh terms": ("pubmed_mesh",), "mesh": ("pubmed_mesh",), "mh": ("pubmed_mesh",),
    "publication type": ("pubmed_publication_type",), "pt": ("pubmed_publication_type",),
    "all fields": ("pubmed_title", "pubmed_abstract_results", "pubmed_mesh", "pubmed_publication_type"),
}
_SPLIT = re.compile(r'("[^"]*"|\[[^\]]+\]|\bAND\b|\bOR\b|\bNOT\b|[()])', re.IGNORECASE)
_DATE_RANGE = re.compile(r'"?(\d{4})"?\s*\[(?:Date - Publication|dp|pdat)\]\s*:\s*"?(\d{4})"?\s*\[(?:Date - Publication|dp|pdat)\]', re.IGNORECASE)


def contains_term(text: str, term: str) -> bool:
    """词边界阻止 ILD 命中 children；仅支持明确的末尾词干通配。"""
    pattern = re.escape(term.rstrip("*")).replace(r"\ ", r"\s+")
    suffix = r"\w*" if term.endswith("*") else ""
    return bool(re.search(r"(?<!\w)" + pattern + suffix + r"(?!\w)", text, re.IGNORECASE))


@dataclass(frozen=True)
class Clause:
    operator: str
    value: str = ""
    children: tuple[Clause, ...] = ()

    def evaluate(self, item: CitationItem) -> tuple[bool, list[dict[str, object]]]:
        if self.operator == "term":
            return _match_atom(self.value, item)
        outcomes = [child.evaluate(item) for child in self.children]
        if self.operator == "NOT":
            return not outcomes[0][0], []
        passed = all(value for value, _ in outcomes) if self.operator == "AND" else any(value for value, _ in outcomes)
        return passed, [match for value, matches in outcomes if value for match in matches]


def _atom_parts(value: str) -> tuple[str, tuple[str, ...]]:
    field_match = re.search(r"\[([^\]]+)\]$", value)
    tag = field_match[1].strip().lower() if field_match else "all fields"
    if tag not in _FIELDS:
        raise ValueError(f"暂不能核验检索字段 [{tag}]，请使用题名/摘要、MeSH 或文献类型字段。")
    term = value[:field_match.start()].strip() if field_match else value.strip()
    term = term.strip('"').strip()
    if not term or term == "*" or "[" in term or ":" in term:
        raise ValueError("检索式无法安全解析，请检查英文检索式。")
    return term, _FIELDS[tag]


def _match_atom(value: str, item: CitationItem) -> tuple[bool, list[dict[str, object]]]:
    if value.startswith("__years_"):
        start, end = map(int, value.removeprefix("__years_").split("_"))
        return item.year is not None and start <= item.year <= end, []
    term, sources = _atom_parts(value)
    metadata = {
        "pubmed_title": item.title or "",
        "pubmed_abstract_results": item.abstract or "",
        "pubmed_mesh": " ".join(item.mesh_terms),
        "pubmed_publication_type": " ".join(item.publication_types),
    }
    fields = [field for field in sources if contains_term(metadata[field], term)]
    if not fields:
        return False, []
    evidence_text = metadata[fields[0]]
    hit = re.search(re.escape(term.rstrip("*")), evidence_text, re.IGNORECASE)
    start = max(0, (hit.start() if hit else 0) - 60)
    excerpt = evidence_text[start:start + 240]
    return True, [{
        "dimension": "topic", "status": "matched", "matched_terms": [term],
        "source": "exploration_query", "field": ",".join(fields),
        "reason": "executed_query_metadata_match", "version": "exploration-match-v1",
        "excerpt": excerpt,
    }]


class _Parser:
    def __init__(self, query: str) -> None:
        # 保留引号和字段标签，将未加引号的短语视作一个保守的匹配单元。
        self.tokens: list[str] = []
        atom: list[str] = []
        for part in _SPLIT.split(query):
            if not part.strip():
                continue
            if part.upper() in {"AND", "OR", "NOT", "(", ")"}:
                if atom:
                    self.tokens.append(" ".join(atom))
                    atom = []
                self.tokens.append(part.upper())
            else:
                atom.append(part.strip())
        if atom:
            self.tokens.append(" ".join(atom))
        groups: list[set[str]] = [set()]
        for token in self.tokens:
            if token == "(":
                groups.append(set())
            elif token == ")" and len(groups) > 1:
                groups.pop()
            elif token in {"AND", "OR"}:
                groups[-1].add(token)
                if len(groups[-1]) > 1:
                    raise ValueError("混用 AND 与 OR 时请用括号明确检索范围。")
        self.position = 0
        self.terms: list[QueryTerm] = []

    def peek(self) -> str:
        return self.tokens[self.position] if self.position < len(self.tokens) else ""

    def parse(self) -> Clause:
        node = self.parse_and()
        while self.peek() == "OR":
            self.position += 1
            node = Clause("OR", children=(node, self.parse_and()))
        return node

    def parse_and(self) -> Clause:
        node = self.parse_atom()
        while self.peek() in {"AND", "NOT"}:
            if self.peek() == "AND":
                self.position += 1
            node = Clause("AND", children=(node, self.parse_atom()))
        return node

    def parse_atom(self) -> Clause:
        token = self.peek()
        self.position += 1
        if token == "NOT":
            return Clause("NOT", children=(self.parse_atom(),))
        if token == "(":
            node = self.parse()
            if self.peek() != ")":
                raise ValueError("检索式括号不配对。")
            self.position += 1
            return node
        if token in {"", ")", "AND", "OR"}:
            raise ValueError("检索式缺少主题词。")
        if not token.startswith("__years_"):
            term, fields = _atom_parts(token)
            self.terms.append(QueryTerm(term, "topic", "exploration_query", ",".join(fields)))
        return Clause("term", token)


@dataclass(frozen=True)
class ExplorationPlan:
    query: str
    clause: Clause
    terms: list[QueryTerm]

    def evaluate(self, item: CitationItem) -> tuple[bool, list[dict[str, object]]]:
        eligible, matches = self.clause.evaluate(item)
        return eligible and bool(matches), matches


def build_exploration_plan(
    question: str, *, original_question: str = "", executed_query: str = ""
) -> ExplorationPlan:
    """原主题复用已执行查询；改写的查询须保留布尔和字段语义。"""
    query = executed_query if question.strip() == original_question.strip() and executed_query else question.strip()
    if not query.isascii():
        # 局部词典命中不能代表整句翻译完成，否则会静默丢弃干预或亚组约束。
        raise ValueError("修改后的主题需先确认英文检索式，请填写英文检索式或回到检索页确认术语。")
    parsed_query = _DATE_RANGE.sub(lambda match: f"__years_{match[1]}_{match[2]}", query)
    parser = _Parser(parsed_query)
    clause = parser.parse()
    if parser.peek() or not parser.terms:
        raise ValueError("检索式无法安全解析，请检查英文检索式和括号。")
    return ExplorationPlan(query, clause, parser.terms)
