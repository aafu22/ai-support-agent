import io
import zipfile

import pytest

from app.services.ingestion.extractors import detect_type, extract_txt


def _docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def test_accepts_valid_types():
    assert detect_type("a.pdf", b"%PDF-1.7 ...") == "pdf"
    assert detect_type("a.docx", _docx_bytes()) == "docx"
    assert detect_type("a.txt", b"hello") == "txt"


@pytest.mark.parametrize(
    "name,data",
    [
        ("evil.exe", b"MZ..."),
        ("fake.pdf", b"<html>not a pdf</html>"),
        ("fake.docx", b"just text"),
        ("zip.docx", b"PK\x03\x04junk"),
        ("empty.txt", b""),
        ("bin.txt", b"abc\x00\x01\x02"),
        ("noext", b"hello"),
    ],
)
def test_rejects_invalid_files(name, data):
    with pytest.raises(ValueError):
        detect_type(name, data)


def test_txt_extraction_handles_bom():
    assert extract_txt("\ufeffhello".encode("utf-8"))[0][1] == "hello"
