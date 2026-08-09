"""UTF-8 Markdown parsing with YAML front matter and heading hierarchy."""

import re
from pathlib import Path

import yaml

from app.modules.document.parsers.base import (
    DocumentEncodingError,
    InvalidDocumentMetadataError,
    validate_extracted_size,
    validate_file_size,
)
from app.modules.document.parsers.schemas import ParsedDocument, ParsedSection

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class MarkdownParser:
    def parse(self, path: Path) -> ParsedDocument:
        validate_file_size(path)
        try:
            content = path.read_text(encoding="utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise DocumentEncodingError("Markdown must use UTF-8 encoding") from exc
        validate_extracted_size(content)
        metadata, body = self._front_matter(content)
        sections: list[ParsedSection] = []
        current_heading: tuple[str, int] | None = None
        current_lines: list[str] = []
        for line in body.splitlines():
            match = HEADING_PATTERN.match(line)
            if match:
                if current_heading is not None:
                    sections.append(
                        ParsedSection(
                            heading=current_heading[0],
                            level=current_heading[1],
                            text="\n".join(current_lines).strip(),
                        )
                    )
                current_heading = (match.group(2).strip(), len(match.group(1)))
                current_lines = []
            elif current_heading is not None:
                current_lines.append(line)
        if current_heading is not None:
            sections.append(
                ParsedSection(
                    heading=current_heading[0],
                    level=current_heading[1],
                    text="\n".join(current_lines).strip(),
                )
            )
        title_value = metadata.get("title")
        title = str(title_value).strip() if title_value is not None else None
        if not title:
            title = next(
                (section.heading for section in sections if section.level == 1),
                path.stem,
            )
        return ParsedDocument(
            source_path=str(path),
            title=title[:500],
            text=body.strip(),
            sections=sections,
            yaml_metadata=metadata,
        )

    @staticmethod
    def _front_matter(content: str) -> tuple[dict[str, object], str]:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, content
        try:
            closing = next(
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            )
        except StopIteration as exc:
            raise InvalidDocumentMetadataError(
                "YAML front matter is not closed"
            ) from exc
        try:
            value = yaml.safe_load("\n".join(lines[1:closing])) or {}
        except yaml.YAMLError as exc:
            raise InvalidDocumentMetadataError("YAML front matter is invalid") from exc
        if not isinstance(value, dict):
            raise InvalidDocumentMetadataError("YAML front matter must be a mapping")
        return {str(key): item for key, item in value.items()}, "\n".join(
            lines[closing + 1 :]
        )
