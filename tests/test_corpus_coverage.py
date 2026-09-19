import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CorpusCoverageTest(unittest.TestCase):
    def test_additional_works_are_complete_and_traceable(self):
        expected = {
            "zhuangzi": 33,
            "liezi": 8,
            "sunzi": 13,
            "neiye": 1,
            "zhouyi": 64,
        }
        for work, count in expected.items():
            with self.subTest(work=work):
                data = json.loads((ROOT / f"corpus/chinese/{work}.json").read_text())
                chapters = data["chapters"]
                self.assertEqual(len(chapters), count)
                ids = {ch.get("hexagram", ch.get("chapter")) for ch in chapters}
                self.assertEqual(len(ids), count)
                if work != "neiye":
                    self.assertEqual(ids, set(range(1, count + 1)))
                self.assertTrue(all(ch["text"].strip() for ch in chapters))
                self.assertTrue(all("?oldid=" in ch["source_url"] for ch in chapters))
                self.assertTrue(all(isinstance(ch["source_revision"], int) for ch in chapters))
        yi = json.loads((ROOT / "corpus/chinese/zhouyi.json").read_text())
        self.assertEqual(len(yi["wings"]), 9)  # 繫辭 is split into two pages.
        self.assertTrue(all(len(ch["lines"]) >= 6 for ch in yi["chapters"]))
        self.assertTrue(all(ch["judgement"] in ch["text"] for ch in yi["chapters"]))

    def test_wieger_translation_has_its_own_witness(self):
        for work, count in (("zhuangzi", 33), ("liezi", 8)):
            with self.subTest(work=work):
                path = ROOT / f"corpus/translations/wieger_1913_{work}.json"
                data = json.loads(path.read_text())
                self.assertEqual(data["witness"], "wieger_1913")
                self.assertEqual(data["language"], "fr")
                self.assertEqual(len(data["chapters"]), count)
                self.assertEqual(
                    {ch["chapter"] for ch in data["chapters"]}, set(range(1, count + 1))
                )
                self.assertTrue(all("?oldid=" in ch["source_url"] for ch in data["chapters"]))


if __name__ == "__main__":
    unittest.main()
