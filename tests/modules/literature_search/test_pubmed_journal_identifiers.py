"""AC-06—09：PubMed 期刊标识与旧快照兼容验收。"""

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.schemas import PubMedConfig
from app.modules.literature_search.journal_metric_matching import match_journal_metric
from app.modules.literature_search.schema import CitationItem


def _client() -> PubMedClient:
    return PubMedClient(PubMedConfig())


def test_efetch_parses_all_journal_identifiers() -> None:
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>Example</ArticleTitle><Journal><ISSN IssnType="Print">2049-3630</ISSN><ISSN IssnType="Electronic">2434-561X</ISSN><Title>Example Journal</Title></Journal></Article><MedlineJournalInfo><MedlineTA>Ex J</MedlineTA><ISSNLinking>2049-3630</ISSNLinking></MedlineJournalInfo></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    record = _client()._parse_efetch(xml)[0]
    assert (record.issn, record.eissn, record.issn_l, record.journal_abbreviation) == (
        "2049-3630",
        "2434-561X",
        "2049-3630",
        "Ex J",
    )


def test_efetch_missing_identifiers_keeps_article() -> None:
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>2</PMID><Article><ArticleTitle>Still parsed</ArticleTitle><Journal><Title>Example Journal</Title></Journal></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    record = _client()._parse_efetch(xml)[0]
    assert record.title == "Still parsed"
    assert (record.issn, record.eissn, record.issn_l) == (None, None, None)


def test_invalid_issn_is_null_and_cannot_match() -> None:
    xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>3</PMID><Article><ArticleTitle>Invalid</ArticleTitle><Journal><ISSN IssnType="Print">2049-3631</ISSN><Title>Different</Title></Journal></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
    record = _client()._parse_efetch(xml)[0]
    assert record.issn is None
    assert (
        match_journal_metric(
            CitationItem(pmid="3", issn=record.issn, journal="Different"), []
        ).status
        == "not_found"
    )


def test_legacy_snapshot_result_bibtex_filter_compatible() -> None:
    item = CitationItem.model_validate({"pmid": "4", "title": "Legacy", "year": 2020})
    assert item.issn is None and item.eissn is None and item.issn_l is None
