from io import BytesIO
from zipfile import ZipFile

import pytest

from agentmesh.documents import (
    CompositeDocumentParser,
    DocumentIngestionRequest,
    ExternalDocumentParserConnector,
    ImageOCRDocumentParser,
    PlainTextDocumentParser,
    SlideDocumentParser,
    UnsupportedDocumentTypeError,
    WordDocumentParser,
)
from agentmesh.seed import PROJECT, USER, WORKSPACE


def test_plain_text_document_parser_returns_structured_document() -> None:
    request = DocumentIngestionRequest(
        file_name="project-brief.md",
        content_type="text/markdown",
        content="# 618 Brief\n\n首屏优先保证核心入口密度。".encode(),
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    result = PlainTextDocumentParser().parse(request)

    assert result.title == "618 Brief"
    assert result.text == "首屏优先保证核心入口密度。"
    assert result.source.title == "project-brief.md"
    assert result.source.source_type == "document"
    assert result.source.reference == "document://project-brief.md"
    assert result.metadata["parser"] == "plain_text"


def test_plain_text_document_parser_rejects_unsupported_binary_files() -> None:
    request = DocumentIngestionRequest(
        file_name="research.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.7",
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    with pytest.raises(UnsupportedDocumentTypeError):
        PlainTextDocumentParser().parse(request)


def test_external_document_parser_connector_is_explicit_placeholder() -> None:
    request = DocumentIngestionRequest(
        file_name="research.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.7",
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    with pytest.raises(NotImplementedError, match="External document parsing"):
        ExternalDocumentParserConnector().parse(request)


def test_word_document_parser_extracts_docx_text() -> None:
    request = DocumentIngestionRequest(
        file_name="brief.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=_ooxml_bytes({"word/document.xml": _word_xml(["项目 Brief", "首屏入口效率优先。"])}),
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    result = WordDocumentParser().parse(request)

    assert result.title == "项目 Brief"
    assert "首屏入口效率优先" in result.text
    assert result.metadata["parser"] == "word"


def test_slide_document_parser_extracts_pptx_text() -> None:
    request = DocumentIngestionRequest(
        file_name="deck.pptx",
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        content=_ooxml_bytes(
            {
                "ppt/slides/slide1.xml": _slide_xml(["第一页", "竞品信息"]),
                "ppt/slides/slide2.xml": _slide_xml(["第二页", "风险结论"]),
            }
        ),
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    result = SlideDocumentParser().parse(request)

    assert result.title == "第一页"
    assert "竞品信息" in result.text
    assert "风险结论" in result.text
    assert result.metadata["parser"] == "slide"


def test_image_ocr_parser_reports_missing_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTMESH_TESSERACT_COMMAND", "agentmesh_missing_tesseract")
    request = DocumentIngestionRequest(
        file_name="brief.png",
        content_type="image/png",
        content=b"not-a-real-image",
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        uploaded_by=USER.id,
    )

    with pytest.raises(UnsupportedDocumentTypeError, match="OCR 命令不可用"):
        ImageOCRDocumentParser().parse(request)


def test_composite_parser_advertises_document_connector_extensions() -> None:
    extensions = CompositeDocumentParser().supported_extensions

    assert {".docx", ".pptx", ".png", ".jpg", ".pdf", ".md"}.issubset(extensions)


def _ooxml_bytes(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _word_xml(values: list[str]) -> str:
    runs = "".join(f"<w:p><w:r><w:t>{value}</w:t></w:r></w:p>" for value in values)
    return f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{runs}</w:body></w:document>'


def _slide_xml(values: list[str]) -> str:
    runs = "".join(f"<a:p><a:r><a:t>{value}</a:t></a:r></a:p>" for value in values)
    return f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld>{runs}</p:cSld></p:sld>'
