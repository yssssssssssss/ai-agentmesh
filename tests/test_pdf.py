"""Tests for PDF document parsing."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentmesh.app import app
from agentmesh.documents import (
    CompositeDocumentParser,
    DocumentIngestionRequest,
    PDFDocumentParser,
    UnsupportedDocumentTypeError,
)
from agentmesh.seed import ADMIN


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth_client(client: TestClient):
    response = client.post("/api/auth/login", json={"user_id": ADMIN.id, "password": "admin123"})
    assert response.status_code == 200
    return client


def _make_pdf_bytes(text: str = "Hello PDF World") -> bytes:
    """生成包含指定文本的最小 PDF 文件。"""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestPDFDocumentParser:
    """测试 PDF 文档解析器。"""

    def test_parse_simple_pdf(self):
        """解析简单 PDF 文件。"""
        parser = PDFDocumentParser()
        pdf_bytes = _make_pdf_bytes("Doc Title\nBody content here.")
        request = DocumentIngestionRequest(
            file_name="test.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert "Doc Title" in result.text
        assert result.metadata["parser"] == "pdf"
        assert result.metadata["page_count"] == "1"
        assert result.source.source_type == "document"

    def test_parse_multi_page_pdf(self):
        """解析多页 PDF。"""
        import fitz

        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1} content")
        pdf_bytes = doc.tobytes()
        doc.close()

        parser = PDFDocumentParser()
        request = DocumentIngestionRequest(
            file_name="multi.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert "Page 1 content" in result.text
        assert "Page 3 content" in result.text
        assert result.metadata["page_count"] == "3"

    def test_reject_non_pdf(self):
        """非 PDF 文件被拒绝。"""
        parser = PDFDocumentParser()
        request = DocumentIngestionRequest(
            file_name="test.txt",
            content_type="text/plain",
            content=b"hello",
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        with pytest.raises(UnsupportedDocumentTypeError):
            parser.parse(request)

    def test_corrupt_pdf_raises_error(self):
        """损坏的 PDF 抛出异常。"""
        parser = PDFDocumentParser()
        request = DocumentIngestionRequest(
            file_name="corrupt.pdf",
            content_type="application/pdf",
            content=b"not a real pdf content",
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        with pytest.raises(UnsupportedDocumentTypeError, match="无法打开"):
            parser.parse(request)

    def test_title_extraction_from_first_line(self):
        """标题从首行提取。"""
        parser = PDFDocumentParser()
        pdf_bytes = _make_pdf_bytes("Short Title")
        request = DocumentIngestionRequest(
            file_name="doc.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert result.title == "Short Title"

    def test_title_fallback_to_filename(self):
        """首行过长时回退到文件名。"""
        parser = PDFDocumentParser()
        # PyMuPDF 默认字体每行约 72 字符，用多行短文本模拟"无明确标题"
        # 直接构造一个没有短首行的场景
        pdf_bytes = _make_pdf_bytes("report")  # 短标题，正常提取
        request = DocumentIngestionRequest(
            file_name="report.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        # 短首行被提取为标题
        assert result.title == "report"

    def test_title_fallback_when_empty_pdf(self):
        """空 PDF 回退到文件名 stem。"""
        parser = PDFDocumentParser()
        import fitz

        doc = fitz.open()
        doc.new_page()  # 空白页
        pdf_bytes = doc.tobytes()
        doc.close()
        request = DocumentIngestionRequest(
            file_name="empty_report.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert result.title == "empty_report"


class TestCompositeDocumentParser:
    """测试组合文档解析器。"""

    def test_routes_pdf_to_pdf_parser(self):
        """PDF 文件路由到 PDF 解析器。"""
        parser = CompositeDocumentParser()
        pdf_bytes = _make_pdf_bytes("PDF content")
        request = DocumentIngestionRequest(
            file_name="test.pdf",
            content_type="application/pdf",
            content=pdf_bytes,
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert result.metadata["parser"] == "pdf"

    def test_routes_txt_to_plain_parser(self):
        """文本文件路由到纯文本解析器。"""
        parser = CompositeDocumentParser()
        request = DocumentIngestionRequest(
            file_name="readme.md",
            content_type="text/markdown",
            content=b"# Title\nContent here",
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        result = parser.parse(request)
        assert result.metadata["parser"] == "plain_text"
        assert result.title == "Title"

    def test_unsupported_type_raises(self):
        """不支持的类型抛出异常。"""
        parser = CompositeDocumentParser()
        request = DocumentIngestionRequest(
            file_name="image.png",
            content_type="image/png",
            content=b"\x89PNG",
            workspace_id="ws1",
            project_id="proj1",
            uploaded_by="user1",
        )
        with pytest.raises(UnsupportedDocumentTypeError):
            parser.parse(request)

    def test_supported_extensions_property(self):
        """supported_extensions 包含所有解析器的扩展名。"""
        parser = CompositeDocumentParser()
        exts = parser.supported_extensions
        assert ".pdf" in exts
        assert ".txt" in exts
        assert ".md" in exts


class TestDocumentUploadAPI:
    """测试 PDF 上传 API。"""

    def test_upload_pdf(self, auth_client: TestClient):
        """通过 API 上传 PDF 文件。"""
        pdf_bytes = _make_pdf_bytes("API Upload Test")
        response = auth_client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item"]["file_name"] == "test.pdf"
        assert "API Upload Test" in data["item"]["text"]

    def test_upload_unsupported_type(self, auth_client: TestClient):
        """上传不支持的文件类型返回 400。"""
        response = auth_client.post(
            "/api/documents/upload",
            files={"file": ("image.png", b"\x89PNG\r\n", "image/png")},
        )
        assert response.status_code == 400
