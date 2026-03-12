from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import tempfile

MODULE_PATH = Path(__file__).resolve().parents[1] / 'src' / 'services' / 'document_parser.py'
SPEC = spec_from_file_location('document_parser_under_test', MODULE_PATH)
MODULE = module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
DocumentParser = MODULE.DocumentParser


def _write_temp_file(suffix: str, header: bytes, body: bytes = b'body') -> str:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(header + body)
    temp.close()
    return temp.name


def test_parse_routes_real_doc_through_conversion(monkeypatch):
    parser = DocumentParser()
    doc_path = _write_temp_file('.doc', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    converted = _write_temp_file('.pdf', b'%PDF-1.7\n')
    calls = []

    def fake_convert(path: str) -> str:
        calls.append(('convert', path))
        return converted

    def fake_parse_pdf(path: str) -> str:
        calls.append(('pdf', path))
        return 'doc text'

    monkeypatch.setattr(parser, '_convert_doc_to_pdf', fake_convert, raising=False)
    monkeypatch.setattr(parser, '_parse_pdf', fake_parse_pdf)

    try:
        assert parser.parse(doc_path) == 'doc text'
        assert calls == [('convert', doc_path), ('pdf', converted)]
    finally:
        Path(doc_path).unlink(missing_ok=True)
        Path(converted).unlink(missing_ok=True)


def test_parse_routes_pseudo_docx_by_signature(monkeypatch):
    parser = DocumentParser()
    fake_docx_path = _write_temp_file('.docx', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    converted = _write_temp_file('.pdf', b'%PDF-1.7\n')
    calls = []

    monkeypatch.setattr(parser, '_convert_doc_to_pdf', lambda path: converted, raising=False)
    monkeypatch.setattr(parser, '_parse_pdf', lambda path: 'converted pseudo docx')

    try:
        assert parser.parse(fake_docx_path) == 'converted pseudo docx'
    finally:
        Path(fake_docx_path).unlink(missing_ok=True)
        Path(converted).unlink(missing_ok=True)


def test_parse_pdf_falls_back_to_ocr_when_extractors_return_empty(monkeypatch):
    parser = DocumentParser()
    pdf_path = _write_temp_file('.pdf', b'%PDF-1.7\n')

    monkeypatch.setattr(parser, '_extract_pdf_with_pypdf2', lambda path: '')
    monkeypatch.setattr(parser, '_has_module', lambda name: False)
    monkeypatch.setattr(parser, '_extract_pdf_with_ocr', lambda path: 'OCR TEXT', raising=False)

    try:
        assert parser.parse(pdf_path) == 'OCR TEXT'
    finally:
        Path(pdf_path).unlink(missing_ok=True)


def test_parse_image_uses_ocr(monkeypatch):
    parser = DocumentParser()
    image_path = _write_temp_file('.png', b'\x89PNG\r\n\x1a\n')

    monkeypatch.setattr(parser, '_extract_image_with_ocr', lambda path: 'IMAGE OCR TEXT', raising=False)

    try:
        assert parser.parse(image_path) == 'IMAGE OCR TEXT'
    finally:
        Path(image_path).unlink(missing_ok=True)
