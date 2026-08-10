"""可选的本地 Tesseract OCR 引擎适配器。"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import settings


class OcrEngineUnavailableError(RuntimeError):
    """本机尚未配置 OCR 所需运行时。"""


class OcrPageProcessingError(RuntimeError):
    """单页 OCR 处理失败。"""


@dataclass(frozen=True)
class OcrEngineInfo:
    name: str
    version: str


@dataclass(frozen=True)
class OcrPageResult:
    text: str
    confidence: float | None = None


class TesseractOcrEngine:
    """使用 PDFium 栅格化和 Tesseract CLI 识别，避免依赖不受控云服务。"""

    def probe(self) -> OcrEngineInfo:
        command = self._command_path()
        if importlib.util.find_spec("pypdfium2") is None:
            raise OcrEngineUnavailableError("未安装可选依赖 pypdfium2")
        try:
            result = subprocess.run(
                [command, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise OcrEngineUnavailableError("本机 Tesseract 引擎不可用") from exc
        first_line = result.stdout.splitlines()[0].strip() if result.stdout else "unknown"
        return OcrEngineInfo(name="tesseract", version=first_line[:128])

    def page_count(self, pdf_path: Path) -> int:
        pdfium = self._pdfium_module()
        try:
            document = pdfium.PdfDocument(str(pdf_path))
            return len(document)
        except Exception as exc:
            raise OcrPageProcessingError("无法读取 PDF 页数") from exc

    def extract_page(self, pdf_path: Path, page_number: int, language: str) -> OcrPageResult:
        pdfium = self._pdfium_module()
        try:
            document = pdfium.PdfDocument(str(pdf_path))
            page = document[page_number - 1]
            bitmap = page.render(scale=settings.OCR_RENDER_SCALE)
            image = bitmap.to_pil()
            image_buffer = BytesIO()
            image.save(image_buffer, format="PNG")
            result = subprocess.run(
                [self._command_path(), "stdin", "stdout", "-l", language],
                input=image_buffer.getvalue(),
                check=True,
                capture_output=True,
                timeout=120,
            )
            return OcrPageResult(text=result.stdout.decode("utf-8", errors="replace").strip())
        except OcrEngineUnavailableError:
            raise
        except (OSError, subprocess.SubprocessError, IndexError, ValueError) as exc:
            raise OcrPageProcessingError(f"第 {page_number} 页 OCR 失败") from exc

    @staticmethod
    def _pdfium_module():
        try:
            import pypdfium2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise OcrEngineUnavailableError("未安装可选依赖 pypdfium2") from exc
        return pypdfium2

    @staticmethod
    def _command_path() -> str:
        configured = settings.TESSERACT_COMMAND.strip()
        command = configured or shutil.which("tesseract")
        if command is None:
            raise OcrEngineUnavailableError("未在 PATH 中找到 tesseract")
        return command
