from src.utils.project_experience_normalizer import to_text_list


def test_to_text_list_parses_json_array_string():
    value = '["负责需求分析","推进上线"]'
    assert to_text_list(value) == ["负责需求分析", "推进上线"]


def test_to_text_list_splits_multiline_text():
    value = "负责接口开发\n负责联调\n  \n推进发布"
    assert to_text_list(value) == ["负责接口开发", "负责联调", "推进发布"]


def test_to_text_list_keeps_plain_text_as_single_item():
    value = "独立负责风控模块重构并上线"
    assert to_text_list(value) == ["独立负责风控模块重构并上线"]


def test_to_text_list_returns_empty_for_none():
    assert to_text_list(None) == []

