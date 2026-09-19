"""Rebuild a searchable SQLite corpus from the versioned JSON source files."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS text_unit (
    id TEXT PRIMARY KEY,
    work TEXT NOT NULL,
    witness TEXT NOT NULL,
    language TEXT NOT NULL,
    kind TEXT NOT NULL,
    reference TEXT NOT NULL,
    parent_id TEXT REFERENCES text_unit(id),
    ordinal INTEGER NOT NULL,
    title TEXT,
    text TEXT NOT NULL CHECK (length(text) > 0),
    content_hash TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_revision INTEGER
);
CREATE INDEX IF NOT EXISTS text_unit_work_ref ON text_unit(work, witness, reference);
CREATE INDEX IF NOT EXISTS text_unit_parent ON text_unit(parent_id);
"""


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _insert(
    db: sqlite3.Connection,
    *,
    identity: str,
    work: str,
    witness: str,
    language: str,
    kind: str,
    reference: str,
    ordinal: int,
    content: str,
    source_url: str,
    source_revision: int | None,
    title: str | None = None,
    parent_id: str | None = None,
) -> None:
    if not content.strip():
        raise ValueError(f"empty passage: {identity}")
    db.execute(
        """INSERT INTO text_unit
        (id, work, witness, language, kind, reference, parent_id, ordinal, title,
         text, content_hash, source_url, source_revision)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (identity, work, witness, language, kind, reference, parent_id, ordinal,
         title, content, _digest(content), source_url, source_revision),
    )


def build_database(corpus_dir: Path, database_path: Path) -> dict[str, int]:
    """Recreate the corpus table atomically; never read personal app data."""
    files = sorted(corpus_dir.rglob("*.json"))
    if not files:
        raise ValueError(f"no corpus JSON found in {corpus_dir}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(database_path)
    try:
        db.executescript(SCHEMA)
        with db:
            db.execute("DELETE FROM text_unit")
            for path in files:
                data = json.loads(path.read_text(encoding="utf-8"))
                work = data.get("work", "daodejing")
                witness = data["witness"]
                language = data["language"]
                for chapter in data["chapters"]:
                    number = chapter.get("hexagram", chapter.get("chapter"))
                    if not isinstance(number, int):
                        raise ValueError(f"{path}: missing chapter or hexagram number")
                    kind = "hexagram" if work == "zhouyi" else "chapter"
                    reference = str(number)
                    identity = f"{work}:{witness}:{kind}:{number}"
                    url = chapter.get("source_url", data.get("source_url"))
                    if not url:
                        raise ValueError(f"{path}: missing source URL for {number}")
                    revision = chapter.get("source_revision")
                    _insert(db, identity=identity, work=work, witness=witness,
                            language=language, kind=kind, reference=reference,
                            ordinal=number, title=chapter.get("title"),
                            content=chapter["text"], source_url=url,
                            source_revision=revision)
                    for index, paragraph in enumerate(chapter.get("paragraphs", []), 1):
                        _insert(db, identity=f"{identity}:paragraph:{index}", work=work,
                                witness=witness, language=language, kind="paragraph",
                                reference=f"{number}.{index}", ordinal=index,
                                content=paragraph, source_url=url, source_revision=revision,
                                parent_id=identity)
                    judgement = chapter.get("judgement")
                    if judgement:
                        _insert(db, identity=f"{identity}:judgement", work=work,
                                witness=witness, language=language, kind="judgement",
                                reference=f"{number}.judgement", ordinal=0,
                                content=judgement, source_url=url, source_revision=revision,
                                parent_id=identity)
                    for line in chapter.get("lines", []):
                        position = line["line"]
                        _insert(db, identity=f"{identity}:line:{position}", work=work,
                                witness=witness, language=language, kind="line",
                                reference=f"{number}.{position}", ordinal=position,
                                title=line["label"], content=line["text"],
                                source_url=url, source_revision=revision, parent_id=identity)
                    commentary = chapter.get("commentary_text")
                    if commentary:
                        _insert(db, identity=f"{identity}:commentary", work=work,
                                witness=witness, language=language, kind="commentary",
                                reference=f"{number}.commentary", ordinal=1,
                                content=commentary, source_url=url,
                                source_revision=revision, parent_id=identity)
                for index, wing in enumerate(data.get("wings", []), 1):
                    _insert(db, identity=f"{work}:{witness}:wing:{wing['title']}",
                            work=work, witness=witness, language=language, kind="wing",
                            reference=wing["title"], ordinal=index, title=wing["title"],
                            content=wing["text"], source_url=wing["source_url"],
                            source_revision=wing.get("source_revision"))
        rows = db.execute(
            "SELECT work, count(*) FROM text_unit WHERE parent_id IS NULL GROUP BY work"
        ).fetchall()
        return dict(rows)
    finally:
        db.close()
