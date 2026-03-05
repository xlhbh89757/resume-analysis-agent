from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "services" / "document_parser.py"
SPEC = spec_from_file_location("document_parser_under_test", MODULE_PATH)
MODULE = module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
DocumentParser = MODULE.DocumentParser


def test_clean_text_removes_watermark_like_noise():
    parser = DocumentParser()
    token = "5e2074214e41d9581HR-0t66EVZXy4W7UPmcWOKgnf7XNBVm3A~~"
    raw = (
        "\u59d3\u540d\uff1a\u5f20\u4e09\n"
        + token
        + "\n\u5de5\u4f5c\u7ecf\u5386\n"
        + token
        + "\n\u9879\u76ee\u7ecf\u5386\n"
    )

    cleaned = parser._clean_text(raw)

    assert token not in cleaned
    assert "\u5de5\u4f5c\u7ecf\u5386" in cleaned
    assert "\u9879\u76ee\u7ecf\u5386" in cleaned


def test_clean_text_repairs_common_mojibake_text():
    parser = DocumentParser()
    source = "\u59d3\u540d\u5f20\u4e09\u5de5\u4f5c\u7ecf\u5386"
    garbled = source.encode("utf-8").decode("gbk", errors="ignore")

    cleaned = parser._clean_text(garbled)

    assert "\u59d3\u540d\u5f20\u4e09" in cleaned
    assert "\u5de5\u4f5c\u7ecf\u5386" in cleaned


def test_is_low_quality_text_detects_noise_dominated_content():
    parser = DocumentParser()
    token = "5e2074214e41d9581HR-0t66EVZXy4W7UPmcWOKgnf7XNBVm3A~~"
    noisy = "\n".join([token, token, token, "\u9879\u76ee\u4e00", "\u9879\u76ee\u4e8c"])

    assert parser._is_low_quality_text(noisy) is True
