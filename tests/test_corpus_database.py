import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from taolab.corpus.database import build_database


class CorpusDatabaseTest(unittest.TestCase):
    def test_rebuild_is_idempotent_and_preserves_source_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus = root / "corpus"
            corpus.mkdir()
            (corpus / "sample.json").write_text(json.dumps({
                "work": "zhuangzi", "witness": "received", "language": "zh",
                "chapters": [{"chapter": 3, "title": "養生主", "text": "甲\n\n乙",
                              "paragraphs": ["甲", "乙"],
                              "source_url": "https://example.org/?oldid=12",
                              "source_revision": 12}],
            }, ensure_ascii=False), encoding="utf-8")
            database = root / "corpus.sqlite"
            self.assertEqual(build_database(corpus, database), {"zhuangzi": 1})
            self.assertEqual(build_database(corpus, database), {"zhuangzi": 1})
            with sqlite3.connect(database) as db:
                rows = db.execute("SELECT id, parent_id, text, content_hash, source_revision "
                                  "FROM text_unit ORDER BY id").fetchall()
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0][2], "甲\n\n乙")
            self.assertEqual(rows[0][3], hashlib.sha256("甲\n\n乙".encode()).hexdigest())
            self.assertEqual(rows[0][4], 12)
            self.assertEqual({row[1] for row in rows[1:]}, {rows[0][0]})


if __name__ == "__main__":
    unittest.main()
