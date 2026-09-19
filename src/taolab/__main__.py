"""Small local corpus CLI."""

import argparse
import json
import sqlite3
from pathlib import Path

from taolab.corpus.database import build_database


def main() -> None:
    parser = argparse.ArgumentParser(prog="taolab")
    parser.add_argument("--db", type=Path, default=Path("data/corpus.sqlite"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build-corpus")
    listing = commands.add_parser("list")
    listing.add_argument("--work")
    listing.add_argument("--witness")
    listing.add_argument("--kind")
    listing.add_argument("--limit", type=int, default=20)
    listing.add_argument("--contains")
    showing = commands.add_parser("show")
    showing.add_argument("id", help="Stable text_unit identifier returned by list")
    context = commands.add_parser("context")
    context.add_argument("work")
    context.add_argument("number", type=int, help="Chapter or hexagram number")
    args = parser.parse_args()
    if args.command == "build-corpus":
        print(json.dumps(build_database(Path("corpus"), args.db), ensure_ascii=False))
        return
    if args.command == "show":
        with sqlite3.connect(args.db) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM text_unit WHERE id = ?", (args.id,)).fetchone()
        if row is None:
            parser.error(f"unknown text unit: {args.id}")
        print(json.dumps(dict(row), ensure_ascii=False, indent=2))
        return
    if args.command == "context":
        with sqlite3.connect(args.db) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """SELECT id, work, witness, language, kind, reference, title, text,
                          content_hash, source_url, source_revision
                   FROM text_unit
                   WHERE work = ? AND reference = ? AND kind IN ('chapter', 'hexagram')
                   ORDER BY CASE WHEN language = 'zh' THEN 0 ELSE 1 END, witness""",
                (args.work, str(args.number)),
            ).fetchall()
        if not rows:
            parser.error(f"no context for {args.work} {args.number}")
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
        return
    conditions = []
    values = []
    for key in ("work", "witness", "kind"):
        value = getattr(args, key)
        if value:
            conditions.append(f"{key} = ?")
            values.append(value)
    if args.contains:
        conditions.append("text LIKE ?")
        values.append(f"%{args.contains}%")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with sqlite3.connect(args.db) as db:
        for row in db.execute(
            "SELECT id, title, substr(text, 1, 160), source_url FROM text_unit" + where +
            " ORDER BY work, witness, kind, ordinal LIMIT ?", (*values, args.limit)
        ):
            print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
