"""Pure parser, download-boundary, and integrity tests for official PMC data."""

import hashlib

import httpx
import pytest

from app.modules.library_item.official_pmc_client import (
    OfficialPmcClient,
    OfficialPmcError,
    _normalize_official_pdf_url,
    _parse_oa_service_record,
    _parse_oai_record,
    _stream_response_to_path,
)
from app.modules.library_item.open_fulltext_storage import _validate_pdf


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


@pytest.mark.parametrize(
    "url",
    [
        "ftp://ftp.ncbi.nlm.nih.gov:21/pub/pmc/file.pdf",
        "ftp://ftp.ncbi.nlm.nih.gov/private/file.pdf",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/file.pdf",
    ],
)
def test_rejects_wrong_scheme_port_or_path_from_oa_service(url):
    with pytest.raises(OfficialPmcError) as raised:
        _normalize_official_pdf_url(url)
    assert raised.value.code == "content_invalid"


def test_missing_license_is_returned_as_unverified_not_inferred():
    oai_xml = """
    <OAI-PMH><GetRecord><record><metadata><article><front><article-meta>
      <article-id pub-id-type="pmcid">PMC123</article-id>
    </article-meta></front></article></metadata></record></GetRecord></OAI-PMH>
    """

    parsed = _parse_oai_record(oai_xml, "PMC123", "https://official.example/oai")

    assert parsed.license is None


@pytest.mark.asyncio
async def test_stream_gate_rejects_oversize_and_non_pdf_content(tmp_path):
    oversize = httpx.Response(200, content=b"%PDF-" + b"x" * 10)
    with pytest.raises(OfficialPmcError, match="最大"):
        await _stream_response_to_path(oversize, tmp_path / "large.pdf", 5)
    invalid = httpx.Response(200, content=b"not a pdf")
    with pytest.raises(OfficialPmcError, match="不是 PDF"):
        await _stream_response_to_path(invalid, tmp_path / "invalid.pdf", 100)


@pytest.mark.asyncio
async def test_stream_gate_persists_exact_size_and_sha256(tmp_path):
    payload = b"%PDF-1.7\nminimal"
    destination = tmp_path / "download.pdf"

    downloaded = await _stream_response_to_path(
        httpx.Response(200, content=payload), destination, 100
    )

    assert destination.read_bytes() == payload
    assert downloaded.byte_size == len(payload)
    assert downloaded.sha256 == hashlib.sha256(payload).hexdigest()


@pytest.mark.asyncio
async def test_download_rejects_non_pdf_media_type_before_writing(tmp_path):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=b"%PDF-fake",
            request=request,
        )
    )
    client = OfficialPmcClient(httpx.AsyncClient(transport=transport))
    destination = tmp_path / "response.pdf"

    with pytest.raises(OfficialPmcError, match="媒体类型"):
        await client.download_pdf_to_path(
            "https://ftp.ncbi.nlm.nih.gov/pub/pmc/file.pdf", destination, 100
        )

    assert not destination.exists()


def test_pdf_structure_gate_rejects_header_only_payload(tmp_path):
    path = tmp_path / "header-only.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a real PDF")

    with pytest.raises(OfficialPmcError) as raised:
        _validate_pdf(path)

    assert raised.value.code == "content_invalid"
