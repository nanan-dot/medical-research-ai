"""Pure parser and URL-boundary tests for official PMC data."""

import pytest

from app.modules.library_item.official_pmc_client import (
    OfficialPmcError,
    _normalize_official_pdf_url,
    _parse_oa_service_record,
    _parse_oai_record,
)


def test_parses_official_records_only_when_pmcid_and_license_exist():
    oai_xml = """
    <OAI-PMH><GetRecord><record><metadata><article>
      <front><article-meta>
        <article-id pub-id-type="pmcid">PMC123</article-id>
        <article-id pub-id-type="pmid">456</article-id>
        <article-id pub-id-type="doi">10.1000/example</article-id>
        <permissions><license><license-p>CC BY 4.0</license-p></license></permissions>
      </article-meta></front>
    </article></metadata></record></GetRecord></OAI-PMH>
    """
    oa_xml = """
    <OA><records><record id="PMC123" license="CC BY 4.0">
      <link format="pdf" href="ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/example.pdf" />
    </record></records></OA>
    """
    parsed = _parse_oai_record(oai_xml, "PMC123", "https://official.example/oai")
    license_text, pdf_url = _parse_oa_service_record(oa_xml, "PMC123")

    assert parsed.pmid == "456"
    assert parsed.doi == "10.1000/example"
    assert parsed.license == "CC BY 4.0"
    assert license_text == "CC BY 4.0"
    assert pdf_url == "https://ftp.ncbi.nlm.nih.gov/pub/pmc/example.pdf"


def test_rejects_non_official_oa_download_url():
    with pytest.raises(OfficialPmcError):
        _normalize_official_pdf_url("https://example.test/paid.pdf")
