import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from taolab.corpus.database import build_database
from taolab.plan.axes import load_catalogue, rejected_by
from taolab.plan.planner import make_plan, save_plan


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ready_db(tmp_path):
    path = tmp_path / "corpus.sqlite"
    build_database(ROOT / "corpus", path)
    with sqlite3.connect(path) as db:
        yield db


def test_compatibility_rules():
    catalogue = load_catalogue(ROOT / "axes")
    assert rejected_by(catalogue, {"translation_layer": "comparison"},
                       translation_count=1, source_characters=100) == (
                           "comparison_requires_two_translations",)
    assert rejected_by(catalogue, {"translation_layer": "one"},
                       translation_count=0, source_characters=100) == (
                           "one_requires_translation",)
    assert rejected_by(catalogue, {"length": "long"},
                       translation_count=2, source_characters=79) == (
                           "long_requires_substantial_source",)
    assert not rejected_by(catalogue, {"translation_layer": "comparison", "length": "long"},
                           translation_count=2, source_characters=80)


def test_full_corpus_plan_and_persistence(ready_db):
    catalogue = load_catalogue(ROOT / "axes")
    plan = make_plan(ready_db, catalogue)
    assert plan == make_plan(ready_db, catalogue)
    assert plan.anchor_count == 483
    assert len(plan.cells) == 600
    assert len({cell.anchor_id for cell in plan.cells}) == 483
    assert len({cell.id for cell in plan.cells}) == 600
    assert set(plan.summary()["works"]) == {
        "daodejing", "zhuangzi", "liezi", "sunzi", "neiye", "zhouyi"}
    for cell in plan.cells:
        if cell.coordinates["translation_layer"] == "comparison":
            assert len(cell.context) == 3
        elif cell.coordinates["translation_layer"] == "one":
            assert len(cell.context) == 2
        else:
            assert len(cell.context) == 1
    for counts in plan.summary()["axis_values"].values():
        assert max(counts.values()) - min(counts.values()) <= 20
    save_plan(ready_db, catalogue, plan)
    save_plan(ready_db, catalogue, plan)
    assert ready_db.execute("SELECT count(*) FROM plan").fetchone()[0] == 1
    assert ready_db.execute("SELECT count(*) FROM plan_cell").fetchone()[0] == 600
    assert ready_db.execute("SELECT count(*) FROM cell").fetchone()[0] == 600


def test_source_change_invalidates_affected_cells(ready_db):
    catalogue = load_catalogue(ROOT / "axes")
    first = make_plan(ready_db, catalogue)
    target = next(cell for cell in first.cells if cell.coordinates["translation_layer"] == "one")
    translation_id = target.context[1][0]
    ready_db.execute("UPDATE text_unit SET content_hash = ? WHERE id = ?",
                     ("changed", translation_id))
    second = make_plan(ready_db, catalogue)
    before = {cell.anchor_id: cell.id for cell in first.cells[:first.anchor_count]}
    after = {cell.anchor_id: cell.id for cell in second.cells[:second.anchor_count]}
    assert before[target.anchor_id] != after[target.anchor_id]
    assert sum(before[k] != after[k] for k in before) == Counter(
        cell.anchor_id for cell in first.cells[:first.anchor_count]
        if any(unit_id == translation_id for unit_id, _ in cell.context)
    ).total()
