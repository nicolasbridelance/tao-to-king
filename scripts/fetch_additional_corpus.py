"""Fetch public-domain source texts with exact Wikisource revision provenance.

Run from the repository root: python scripts/fetch_additional_corpus.py
The generated JSON is committed; the network is needed only for missing works.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
ZH_API = "https://zh.wikisource.org/w/api.php"
FR_API = "https://fr.wikisource.org/w/api.php"
ZHUANGZI = (
    "逍遙遊 齊物論 養生主 人間世 德充符 大宗師 應帝王 駢拇 馬蹄 胠篋 在宥 天地 "
    "天道 天運 刻意 繕性 秋水 至樂 達生 山木 田子方 知北遊 庚桑楚 徐無鬼 則陽 "
    "外物 寓言 讓王 盜跖 說劍 漁父 列禦寇 天下"
).split()
LIEZI = "天瑞 黃帝 周穆王 仲尼 湯問 力命 楊朱 說符".split()


def session() -> requests.Session:
    client = requests.Session()
    client.headers["User-Agent"] = "taolab-corpus/0.1 (public-domain text research)"
    retry = Retry(total=4, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
    client.mount("https://", HTTPAdapter(max_retries=retry))
    return client


def page(api: str, title: str) -> dict:
    cache_dir = ROOT / "data/wikisource_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{api}|{title}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.exists():
        parsed = json.loads(cache_file.read_text(encoding="utf-8"))
        redirect = re.search(
            r"^#(?:重定向|REDIRECT)\s*\[\[([^\]|]+)", parsed["wikitext"]["*"], re.I
        )
        return page(api, redirect.group(1)) if redirect else parsed
    time.sleep(1.5)
    response = session().get(
        api,
        params={"action": "parse", "page": title, "prop": "text|wikitext|revid", "format": "json"},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise ValueError(f"{title}: {data['error']}")
    parsed = data["parse"]
    cache_file.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    redirect = re.search(
        r"^#(?:重定向|REDIRECT)\s*\[\[([^\]|]+)", parsed["wikitext"]["*"], re.I
    )
    return page(api, redirect.group(1)) if redirect else parsed


def clean(tag: Tag) -> str:
    clone = BeautifulSoup(str(tag), "html.parser")
    for element in clone.select("sup.reference, .mw-editsection, .ws-noexport, .noprint"):
        element.decompose()
    return re.sub(r"\s+", " ", clone.get_text("", strip=False)).strip()


def provenance(api: str, title: str, parsed: dict) -> dict:
    host = "zh" if api == ZH_API else "fr"
    title = parsed.get("title", title)
    revision = parsed.get("revid")
    if revision is None:
        raise ValueError(f"{title}: missing revision")
    return {
        "source_title": title,
        "source_url": (
            f"https://{host}.wikisource.org/wiki/"
            f"{quote(title.replace(' ', '_'), safe='/')}?oldid={revision}"
        ),
        "source_revision": revision,
    }


def paragraphs(parsed: dict, *, french: bool = False) -> list[str]:
    soup = BeautifulSoup(parsed["text"]["*"], "html.parser")
    container = soup.select_one(".prp-pages-output" if french else ".mw-parser-output")
    if container is None:
        raise ValueError("missing content container")
    if french:
        heading = container.find(["h2", "h3", "h4"])
        if heading is None:
            raise ValueError("missing French chapter heading")
        nodes = heading.find_next_siblings("p")
    else:
        nodes = container.find_all("p", recursive=False)
    result = [clean(node) for node in nodes]
    return [value for value in result if value]


def chinese_chapter(work: str, number: int, name: str) -> dict:
    title = f"{work}/{name}" if work == "莊子" else f"列子/{name}篇"
    parsed = page(ZH_API, title)
    parts = paragraphs(parsed)
    if not parts:
        raise ValueError(f"empty chapter: {title}")
    return {
        "chapter": number, "title": name, "paragraphs": parts,
        "text": "\n\n".join(parts), **provenance(ZH_API, title, parsed),
    }


def sunzi() -> list[dict]:
    title = "孫子兵法"
    parsed = page(ZH_API, title)
    soup = BeautifulSoup(parsed["text"]["*"], "html.parser")
    container = soup.select_one(".mw-parser-output")
    chapters: list[dict] = []
    for node in container.find_all(recursive=False):
        classes = node.get("class", [])
        if "mw-heading2" in classes:
            if len(chapters) == 13:
                break
            chapters.append({"chapter": len(chapters) + 1, "title": clean(node), "paragraphs": []})
        elif node.name == "p" and chapters:
            value = clean(node)
            if value:
                chapters[-1]["paragraphs"].append(value)
    if len(chapters) != 13 or any(not item["paragraphs"] for item in chapters):
        raise ValueError("Sunzi should have 13 nonempty chapters")
    for item in chapters:
        item["text"] = "\n\n".join(item["paragraphs"])
        item.update(provenance(ZH_API, title, parsed))
    return chapters


def neiye() -> list[dict]:
    title = "管子/第49篇內業"
    parsed = page(ZH_API, title)
    parts = paragraphs(parsed)
    if len(parts) < 5:
        raise ValueError("Neiye extraction is unexpectedly short")
    return [{
        "chapter": 49, "title": "內業", "paragraphs": parts,
        "text": "\n\n".join(parts), **provenance(ZH_API, title, parsed),
    }]


WINGS = {"彖", "大象", "小象", "文言", "繫辭上", "繫辭下", "說卦", "序卦", "雜卦"}


def index_links(api: str, title: str) -> list[str]:
    response = session().get(
        api, params={"action": "parse", "page": title, "prop": "links", "format": "json"},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise ValueError(data["error"])
    return [item["*"] for item in data["parse"]["links"]]


def zhouyi_page(title: str) -> tuple[str, dict]:
    parsed = page(ZH_API, title)
    soup = BeautifulSoup(parsed["text"]["*"], "html.parser")
    container = soup.select_one(".mw-parser-output")
    if container is None:
        raise ValueError(f"{title}: no content")
    name = title.split("/", 1)[1]
    if name in WINGS:
        parts = []
        for node in container.find_all(recursive=False):
            if node.name in {"p", "ul", "ol", "dl"}:
                value = clean(node)
                if value:
                    parts.append(value)
        if not parts:
            raise ValueError(f"empty wing: {title}")
        return "wing", {
            "title": name, "text": "\n\n".join(parts), **provenance(ZH_API, title, parsed),
        }
    raw = parsed["wikitext"]["*"]
    match = re.search(r"第([一二三四五六七八九十]+)卦", raw)
    if match is None:
        raise ValueError(f"{title}: no numbered hexagram heading")
    digits = {char: number for number, char in enumerate("一二三四五六七八九", 1)}
    label = match.group(1)
    if "十" in label:
        tens, ones = label.split("十", 1)
        number = (digits[tens] if tens else 1) * 10 + (digits[ones] if ones else 0)
    else:
        number = digits[label]
    lists = container.find_all("ul", recursive=False)
    if not lists:
        raise ValueError(f"{title}: no hexagram text")
    primary = clean(lists[0]).removeprefix("易經：").strip()
    if len(primary) < 20:
        raise ValueError(f"{title}: primary text too short")
    line_marks = list(re.finditer(
        r"(初[九六]|[九六][二三四五]|上[九六]|用[九六])\s*[:：,，]", primary
    ))
    if len(line_marks) < 6:
        raise ValueError(f"{title}: fewer than six line statements")
    judgement = primary[:line_marks[0].start()].strip()
    lines = []
    for position, mark in enumerate(line_marks):
        end = line_marks[position + 1].start() if position + 1 < len(line_marks) else len(primary)
        lines.append({
            "line": position + 1, "label": mark.group(1),
            "text": primary[mark.start():end].strip(),
        })
    commentaries = [clean(item) for item in lists[1:]]
    return "hexagram", {
        "hexagram": number,
        "title": name,
        "text": primary,
        "judgement": judgement,
        "lines": lines,
        "commentary_text": "\n\n".join(filter(None, commentaries)),
        **provenance(ZH_API, title, parsed),
    }


def wieger_chapter(_work: str, number: int, title: str) -> dict:
    parsed = page(FR_API, title)
    parts = paragraphs(parsed, french=True)
    if not parts:
        raise ValueError(f"empty Wieger chapter: {title}")
    return {
        "chapter": number, "title": title.rsplit("/", 1)[-1],
        "paragraphs": parts, "text": "\n\n".join(parts),
        **provenance(FR_API, title, parsed),
    }


def fetch_many(tasks: list[tuple], function) -> list:
    # Wikimedia asks API clients to avoid request bursts. Keep imports serial.
    return [function(*task) for task in tasks]


def write(
    relative: str, work: str, witness: str, language: str, chapters: list[dict],
    *, edition: str | None = None, extra: dict | None = None,
) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "work": work,
        "witness": witness,
        "language": language,
        "edition": edition,
        "source": "Wikisource",
        "retrieved": date.today().isoformat(),
        "chapters": chapters,
    }
    if extra:
        data.update(extra)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{relative}: {len(chapters)} units")


def main() -> None:
    if not (ROOT / "corpus/chinese/zhuangzi.json").exists():
        zhuangzi = fetch_many(
            [("莊子", i, name) for i, name in enumerate(ZHUANGZI, 1)], chinese_chapter
        )
        write("corpus/chinese/zhuangzi.json", "zhuangzi", "received", "zh", zhuangzi)
    if not (ROOT / "corpus/chinese/liezi.json").exists():
        liezi = fetch_many(
            [("列子", i, name) for i, name in enumerate(LIEZI, 1)], chinese_chapter
        )
        write("corpus/chinese/liezi.json", "liezi", "received", "zh", liezi)
    if not (ROOT / "corpus/chinese/sunzi.json").exists():
        write("corpus/chinese/sunzi.json", "sunzi", "received", "zh", sunzi())
    if not (ROOT / "corpus/chinese/neiye.json").exists():
        write("corpus/chinese/neiye.json", "neiye", "guanzi_49", "zh", neiye())

    if not (ROOT / "corpus/chinese/zhouyi.json").exists():
        links = index_links(ZH_API, "周易")
        yi_titles = [title for title in links if title.startswith("周易/")]
        results = fetch_many([(title,) for title in yi_titles], zhouyi_page)
        hexagrams = sorted(
            (item for kind, item in results if kind == "hexagram"),
            key=lambda item: item["hexagram"],
        )
        wings = sorted(
            (item for kind, item in results if kind == "wing"),
            key=lambda item: item["title"],
        )
        if len(hexagrams) != 64 or len({item["hexagram"] for item in hexagrams}) != 64:
            raise ValueError(f"expected 64 unique hexagrams, found {len(hexagrams)}")
        if len(wings) != len(WINGS):
            raise ValueError(f"expected {len(WINGS)} wing pages, found {len(wings)}")
        write(
            "corpus/chinese/zhouyi.json", "zhouyi", "wikisource_received", "zh",
            hexagrams, extra={"wings": wings},
        )

    for work, prefix, expected in [
        ("zhuangzi", "Les pères du système taoïste/Tchoang-tzeu", 33),
        ("liezi", "Les pères du système taoïste/Lie-tzeu", 8),
    ]:
        if (ROOT / f"corpus/translations/wieger_1913_{work}.json").exists():
            continue
        titles = index_links(FR_API, prefix)
        titles = [title for title in titles if title.startswith(prefix + "/")]
        tasks = []
        for title in titles:
            match = re.match(r"(?:Chapitre )?(\d+)\.", title.rsplit("/", 1)[-1])
            if match:
                tasks.append((work, int(match.group(1)), title))
        if len(tasks) != expected or len({task[1] for task in tasks}) != expected:
            raise ValueError(
                f"{work}: expected {expected} unique translation chapters, found {len(tasks)}"
            )
        chapters = sorted(fetch_many(tasks, wieger_chapter), key=lambda item: item["chapter"])
        write(
            f"corpus/translations/wieger_1913_{work}.json", work, "wieger_1913", "fr",
            chapters, edition="Les pères du système taoïste (1913)",
        )


if __name__ == "__main__":
    main()
