import pandas as pd
import pytest

from app.utils import csv_utils


def test_validate_csv_format_parser_error(monkeypatch):
    def boom(*args, **kwargs):
        raise pd.errors.ParserError("boom")

    monkeypatch.setattr(csv_utils.pd, "read_csv", boom)
    with pytest.raises(ValueError):
        csv_utils.validate_csv_format("bad.csv")


def test_import_annotations_from_csv_thread_column(tmp_path):
    file_path = tmp_path / "ann_thread_column.csv"
    file_path.write_text("turn_id,thread_column\nT1,TH1\n", encoding="utf-8")
    annotations = csv_utils.import_annotations_from_csv(str(file_path))
    assert annotations == [{"turn_id": "T1", "thread_id": "TH1"}]


def test_import_annotations_from_csv_missing_columns(tmp_path):
    missing_thread = tmp_path / "ann_missing_thread.csv"
    missing_thread.write_text("turn_id,foo\nT1,X\n", encoding="utf-8")
    with pytest.raises(Exception):
        csv_utils.import_annotations_from_csv(str(missing_thread))

    missing_turn = tmp_path / "ann_missing_turn.csv"
    missing_turn.write_text("thread_id\nX\n", encoding="utf-8")
    with pytest.raises(Exception):
        csv_utils.import_annotations_from_csv(str(missing_turn))


def test_validate_annotations_csv_format_errors(tmp_path, monkeypatch):
    missing_turn = tmp_path / "ann_missing_turn.csv"
    missing_turn.write_text("thread_id\nX\n", encoding="utf-8")
    with pytest.raises(ValueError):
        csv_utils.validate_annotations_csv_format(str(missing_turn))

    empty = tmp_path / "ann_empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        csv_utils.validate_annotations_csv_format(str(empty))

    def boom(*args, **kwargs):
        raise pd.errors.ParserError("boom")

    monkeypatch.setattr(csv_utils.pd, "read_csv", boom)
    with pytest.raises(ValueError):
        csv_utils.validate_annotations_csv_format("bad.csv")
