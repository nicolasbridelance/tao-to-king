"""Deterministic, corpus-wide planning without generation or network calls."""

from __future__ import annotations

import itertools
import json
import random
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass

from taolab.plan.axes import Catalogue, fingerprint, rejected_by


SCHEMA = """
CREATE TABLE IF NOT EXISTS axis (
    id TEXT PRIMARY KEY, definition_hash TEXT NOT NULL, definition_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS axis_value (
    axis_id TEXT NOT NULL, id TEXT NOT NULL, definition_hash TEXT NOT NULL,
    definition_json TEXT NOT NULL, PRIMARY KEY (axis_id, id)
);
CREATE TABLE IF NOT EXISTS plan (
    id TEXT PRIMARY KEY, seed INTEGER NOT NULL, prompt_version TEXT NOT NULL,
    axes_hash TEXT NOT NULL, rules_hash TEXT NOT NULL, cell_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS cell (
    id TEXT PRIMARY KEY, anchor_id TEXT NOT NULL, context_json TEXT NOT NULL,
    coordinates_json TEXT NOT NULL, prompt_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_cell (
    plan_id TEXT NOT NULL, cell_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
    PRIMARY KEY (plan_id, cell_id), UNIQUE (plan_id, ordinal)
);
"""


@dataclass(frozen=True)
class Cell:
    id: str
    anchor_id: str
    context: tuple[tuple[str, str], ...]
    coordinates: dict[str, str]


@dataclass(frozen=True)
class Plan:
    id: str
    seed: int
    prompt_version: str
    axes_hash: str
    rules_hash: str
    anchor_count: int
    cells: tuple[Cell, ...]
    rejected: dict[str, int]

    def summary(self) -> dict:
        values = {axis: Counter() for axis in self.cells[0].coordinates} if self.cells else {}
        works = Counter()
        for cell in self.cells:
            works[cell.anchor_id.split(":", 1)[0]] += 1
            for axis, value in cell.coordinates.items():
                values[axis][value] += 1
        return {
            "plan_id": self.id, "seed": self.seed, "prompt_version": self.prompt_version,
            "anchors": self.anchor_count, "cells": len(self.cells),
            "works": dict(sorted(works.items())),
            "axis_values": {axis: dict(sorted(counts.items())) for axis, counts in values.items()},
            "rejected_candidates": dict(sorted(self.rejected.items())),
        }


def _roots(db: sqlite3.Connection) -> tuple[
    list[sqlite3.Row], dict[tuple[str, str, str], list[sqlite3.Row]]
]:
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT id, work, witness, language, kind, reference, text, content_hash
           FROM text_unit WHERE parent_id IS NULL ORDER BY work, kind, ordinal, witness"""
    ).fetchall()
    anchors = [r for r in rows if r["language"] == "zh" and r["kind"] in
               {"chapter", "hexagram", "wing"}]
    translations: dict[tuple[str, str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        if row["language"] != "zh" and row["kind"] in {"chapter", "hexagram", "wing"}:
            translations[row["work"], row["kind"], row["reference"]].append(row)
    for group in translations.values():
        group.sort(key=lambda row: row["witness"])
    return anchors, translations


def make_plan(
    db: sqlite3.Connection, catalogue: Catalogue, *, size: int = 600,
    seed: int = 0, prompt_version: str = "spike-v1",
) -> Plan:
    anchors, translations = _roots(db)
    if not anchors:
        raise ValueError("no Chinese root units; run build-corpus first")
    if size < len(anchors):
        raise ValueError(f"size {size} is below {len(anchors)} Chinese root units")
    if not prompt_version:
        raise ValueError("prompt version must be nonempty")
    axes = catalogue.axes
    combinations = [dict(zip((a.id for a in axes), values)) for values in
                    itertools.product(*(tuple(v["id"] for v in a.values) for a in axes))]
    rng = random.Random(seed)
    rng.shuffle(anchors)
    marginal = {a.id: Counter() for a in axes}
    used: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    choices: dict[str, list[dict[str, str]]] = {}
    rejected: Counter[str] = Counter()
    for anchor in anchors:
        related = translations.get((anchor["work"], anchor["kind"], anchor["reference"]), [])
        valid = []
        for coords in combinations:
            reasons = rejected_by(catalogue, coords, translation_count=len(related),
                                  source_characters=len(anchor["text"].strip()))
            if reasons:
                rejected.update(reasons)
            else:
                valid.append(coords)
        if not valid:
            raise ValueError(f"no valid coordinates for {anchor['id']}")
        choices[anchor["id"]] = valid
    cells: list[Cell] = []
    for index in range(size):
        anchor = anchors[index % len(anchors)]
        anchor_id = anchor["id"]
        available = [c for c in choices[anchor_id]
                     if tuple(c[a.id] for a in axes) not in used[anchor_id]]
        if not available:
            raise ValueError(f"all coordinates exhausted for {anchor_id}")
        scores = [sum(marginal[a.id][c[a.id]] for a in axes) for c in available]
        minimum = min(scores)
        coords = rng.choice([c for c, score in zip(available, scores) if score == minimum])
        used[anchor_id].add(tuple(coords[a.id] for a in axes))
        for axis, value in coords.items():
            marginal[axis][value] += 1
        related = translations.get((anchor["work"], anchor["kind"], anchor["reference"]), [])
        layer = coords.get("translation_layer", "chinese")
        selected = related[:2] if layer == "comparison" else related[:1] if layer == "one" else []
        context = tuple((r["id"], r["content_hash"]) for r in [anchor, *selected])
        cell_id = fingerprint({
            "context": context, "coordinates": coords,
            "axes_hash": catalogue.axes_hash, "prompt_version": prompt_version,
        })
        cells.append(Cell(cell_id, anchor_id, context, coords))
    plan_id = fingerprint({
        "seed": seed, "prompt_version": prompt_version,
        "axes_hash": catalogue.axes_hash, "rules_hash": catalogue.rules_hash,
        "cells": [cell.id for cell in cells],
    })
    return Plan(plan_id, seed, prompt_version, catalogue.axes_hash,
                catalogue.rules_hash, len(anchors), tuple(cells), dict(rejected))


def _immutable(db: sqlite3.Connection, table: str, key: tuple[str, ...], definition: dict) -> None:
    digest = fingerprint(definition)
    where = " AND ".join(f"{column} = ?" for column in
                         (("id",) if table == "axis" else ("axis_id", "id")))
    existing = db.execute(f"SELECT definition_hash FROM {table} WHERE {where}", key).fetchone()
    if existing and existing[0] != digest:
        raise ValueError(f"{table} {'.'.join(key)} was redefined; introduce a new ID")
    if existing:
        return
    columns = ("id", "definition_hash", "definition_json") if table == "axis" else (
        "axis_id", "id", "definition_hash", "definition_json")
    placeholders = ", ".join("?" for _ in columns)
    db.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
               (*key, digest, json.dumps(definition, ensure_ascii=False, sort_keys=True)))


def save_plan(db: sqlite3.Connection, catalogue: Catalogue, plan: Plan) -> None:
    db.executescript(SCHEMA)
    with db:
        for axis in catalogue.axes:
            # The axis metadata may evolve as values are added. Value definitions stay immutable.
            _immutable(db, "axis", (axis.id,), {
                "id": axis.id, "type": axis.type, "description": axis.description,
            })
            for value in axis.values:
                _immutable(db, "axis_value", (axis.id, value["id"]), value)
        db.execute(
            """INSERT OR IGNORE INTO plan
               (id, seed, prompt_version, axes_hash, rules_hash, cell_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (plan.id, plan.seed, plan.prompt_version, plan.axes_hash, plan.rules_hash,
             len(plan.cells)),
        )
        for ordinal, cell in enumerate(plan.cells):
            db.execute(
                """INSERT OR IGNORE INTO cell
                   (id, anchor_id, context_json, coordinates_json, prompt_version)
                   VALUES (?, ?, ?, ?, ?)""",
                (cell.id, cell.anchor_id, json.dumps(cell.context, ensure_ascii=False),
                 json.dumps(cell.coordinates, ensure_ascii=False, sort_keys=True),
                 plan.prompt_version),
            )
            db.execute("INSERT OR IGNORE INTO plan_cell VALUES (?, ?, ?)",
                       (plan.id, cell.id, ordinal))
