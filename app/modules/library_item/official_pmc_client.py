"""Official PMC OAI and OA Web Service client with conservative legal gates."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OAI_ENDPOINT = "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/"
_OA_SERVICE_ENDPOINT = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
_OFFICIAL_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
_MIN_REQUEST_INTERVAL_SECONDS = 1 / 3
_MAX_ATTEMPTS = 3
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


class OfficialPmcError(Exception):
    """Expected official-service failure that can be exposed as a precise state."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class VerifiedPmcFulltext:
    pmcid: str
    pmid: str | None
    doi: str | None
    license: str
    oai_record_url: str
    pdf_url: str


@dataclass(frozen=True)
class DownloadedPmcPdf:
    byte_size: int
    sha256: str


class OfficialPmcGateway(Protocol):
    async def fetch_verified_fulltext(self, pmcid: str) -> VerifiedPmcFulltext: ...

    async def download_pdf_to_path(
        self,
        pdf_url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> DownloadedPmcPdf: ...

    async def aclose(self) -> None: ...


class OfficialPmcRateLimiter:
    """Serialise PMC requests across endpoint instances to respect the public limit."""

    def __init__(self, minimum_interval_seconds: float = _MIN_REQUEST_INTERVAL_SECONDS) -> None:
        self._minimum_interval_seconds = minimum_interval_seconds
        self._lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def wait(self) -> None:
        async with self._lock:
            delay = self._next_request_at - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_request_at = time.monotonic() + self._minimum_interval_seconds


_rate_limiter = OfficialPmcRateLimiter()


class OfficialPmcClient:
    """Only download a PDF after official metadata confirms reusable PMC OA status."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        contact = settings.PMC_CONTACT_EMAIL or settings.PUBMED_EMAIL
        contact_suffix = f" ({contact})" if contact else ""
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            headers={
                "User-Agent": f"rag-medicine-open-fulltext/1.0{contact_suffix}",
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=False,
        )

    async def fetch_verified_fulltext(self, pmcid: str) -> VerifiedPmcFulltext:
        record_url = _oai_record_url(pmcid)
        oai_xml = await self._get_text(
            _OAI_ENDPOINT,
            {
                "verb": "GetRecord",
                "metadataPrefix": "pmc",
                "identifier": f"oai:pubmedcentral.nih.gov:{pmcid[3:]}",
            },
        )
        oai_record = _parse_oai_record(oai_xml, pmcid, record_url)
        oa_xml = await self._get_text(_OA_SERVICE_ENDPOINT, {"id": pmcid})
        oa_license, pdf_url = _parse_oa_service_record(oa_xml, pmcid)
        if not oai_record.license or not oa_license:
            raise OfficialPmcError(
                "license_unverified",
                "PMC 官方响应未同时提供可复用许可，未自动下载全文",
            )
        if not pdf_url:
            raise OfficialPmcError(
                "pdf_unavailable",
                "PMC 官方开放获取服务未提供可下载的 PDF 链接",
            )
        return VerifiedPmcFulltext(
            pmcid=pmcid,
            pmid=oai_record.pmid,
            doi=oai_record.doi,
            license=oa_license,
            oai_record_url=record_url,
            pdf_url=pdf_url,
        )

    async def download_pdf_to_path(
        self,
        pdf_url: str,
        destination: Path,
        maximum_bytes: int,
    ) -> DownloadedPmcPdf:
        _validate_official_pdf_url(pdf_url)
        last_error: OfficialPmcError | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            await _rate_limiter.wait()
            try:
                async with self._http.stream(
                    "GET",
                    pdf_url,
                    timeout=httpx.Timeout(settings.PMC_DOWNLOAD_TIMEOUT_SECONDS),
                ) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        last_error = OfficialPmcError(
                            "rate_limited" if response.status_code == 429 else "network_error",
                            f"PMC 官方 PDF 服务返回 HTTP {response.status_code}",
                        )
                    elif response.status_code != 200:
                        raise OfficialPmcError(
                            "network_error",
                            f"PMC 官方 PDF 服务返回 HTTP {response.status_code}",
                        )
                    else:
                        media_type = response.headers.get("Content-Type", "").lower()
                        if media_type and not media_type.startswith(
                            ("application/pdf", "application/octet-stream")
                        ):
                            raise OfficialPmcError(
                                "content_invalid", "PMC 官方链接未返回 PDF 媒体类型"
                            )
                        return await _stream_response_to_path(
                            response, destination, maximum_bytes
                        )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.warning("PMC PDF download failed attempt=%s: %s", attempt, exc)
                last_error = OfficialPmcError("network_error", "PMC 官方 PDF 下载服务暂不可用")

            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(2 ** (attempt - 1))
        assert last_error is not None
        raise last_error

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    async def _get_text(self, url: str, params: dict[str, str]) -> str:
        last_error: OfficialPmcError | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            await _rate_limiter.wait()
            try:
                response = await self._http.get(
                    url,
                    params=params,
                    timeout=httpx.Timeout(settings.PMC_REQUEST_TIMEOUT_SECONDS),
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                logger.warning("PMC request failed attempt=%s: %s", attempt, exc)
                last_error = OfficialPmcError("network_error", "PMC 官方验证服务暂不可用")
            else:
                if response.status_code == 200 and response.text.strip():
                    return response.text
                code = "rate_limited" if response.status_code == 429 else "network_error"
                last_error = OfficialPmcError(
                    code, f"PMC 官方验证服务返回 HTTP {response.status_code}"
                )
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(2 ** (attempt - 1))
        assert last_error is not None
        raise last_error


@dataclass(frozen=True)
class _OaiRecord:
    pmid: str | None
    doi: str | None
    license: str | None


def _oai_record_url(pmcid: str) -> str:
    return (
        f"{_OAI_ENDPOINT}?verb=GetRecord&metadataPrefix=pmc&"
        f"identifier=oai%3Apubmedcentral.nih.gov%3A{pmcid[3:]}"
    )


def _parse_oai_record(xml_text: str, requested_pmcid: str, record_url: str) -> _OaiRecord:
    root = _parse_xml(xml_text, "OAI")
    errors = [element.get("code", "unknown") for element in _iter_local(root, "error")]
    if errors:
        raise OfficialPmcError("license_unverified", f"PMC OAI 未返回可用记录：{errors[0]}")
    article_ids = _iter_local(root, "article-id")
    identifiers = {
        (element.get("pub-id-type") or "").lower(): _normal_text(element)
        for element in article_ids
    }
    actual_pmcid = (identifiers.get("pmcid") or "").upper()
    if actual_pmcid != requested_pmcid:
        raise OfficialPmcError("identity_mismatch", "PMC OAI 返回的 PMCID 与请求不一致")
    license_text = _first_nonempty_text(root, {"license", "license-p", "license_ref"})
    return _OaiRecord(
        pmid=identifiers.get("pmid"),
        doi=identifiers.get("doi"),
        license=license_text,
    )


def _parse_oa_service_record(xml_text: str, pmcid: str) -> tuple[str | None, str | None]:
    root = _parse_xml(xml_text, "OA Web Service")
    records = [
        element
        for element in _iter_local(root, "record")
        if (element.get("id") or "").upper() == pmcid
    ]
    if not records:
        raise OfficialPmcError(
            "pdf_unavailable", "PMC 官方开放获取服务未返回该 PMCID 的可下载记录"
        )
    record = records[0]
    license_text = (record.get("license") or "").strip() or None
    pdf_url: str | None = None
    for link in _iter_local(record, "link"):
        if (link.get("format") or "").lower() != "pdf":
            continue
        href = (link.get("href") or "").strip()
        if not href:
            continue
        try:
            pdf_url = _normalize_official_pdf_url(href)
        except OfficialPmcError:
            continue
        break
    return license_text, pdf_url


def _parse_xml(xml_text: str, service_name: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise OfficialPmcError(
            "network_error", f"{service_name} 返回了无法解析的 XML"
        ) from exc


def _iter_local(root: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == name]


def _normal_text(element: ElementTree.Element | None) -> str | None:
    if element is None:
        return None
    text = " ".join("".join(element.itertext()).split())
    return text or None


def _first_nonempty_text(root: ElementTree.Element, names: set[str]) -> str | None:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] in names:
            text = _normal_text(element)
            if text:
                return text
    return None


def _normalize_official_pdf_url(href: str) -> str:
    parsed = urlparse(href)
    if parsed.scheme != "ftp" or parsed.hostname != _OFFICIAL_FTP_HOST:
        raise OfficialPmcError("content_invalid", "PMC OA 服务给出的 PDF 链接不是官方 FTP 地址")
    if parsed.port is not None or not parsed.path.startswith("/pub/pmc/"):
        raise OfficialPmcError("content_invalid", "PMC OA 服务给出的 PDF 链接路径不合法")
    return f"https://{_OFFICIAL_FTP_HOST}{parsed.path}"


def _validate_official_pdf_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != _OFFICIAL_FTP_HOST
        or parsed.port is not None
        or not parsed.path.startswith("/pub/pmc/")
    ):
        raise OfficialPmcError("content_invalid", "拒绝非 PMC 官方受控 PDF 下载地址")


async def _stream_response_to_path(
    response: httpx.Response, destination: Path, maximum_bytes: int
) -> DownloadedPmcPdf:
    digest = hashlib.sha256()
    byte_size = 0
    leading_bytes = b""
    with destination.open("xb") as output:
        async for chunk in response.aiter_bytes(_DOWNLOAD_CHUNK_BYTES):
            byte_size += len(chunk)
            if byte_size > maximum_bytes:
                raise OfficialPmcError("content_invalid", "PMC PDF 超过允许的最大文件大小")
            if len(leading_bytes) < 5:
                leading_bytes += chunk[: 5 - len(leading_bytes)]
            digest.update(chunk)
            output.write(chunk)
    if not leading_bytes.startswith(b"%PDF-"):
        raise OfficialPmcError("content_invalid", "PMC 官方链接返回的内容不是 PDF")
    return DownloadedPmcPdf(byte_size=byte_size, sha256=digest.hexdigest())
