"""FAQ database, search, popularity and page output tests."""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

import crypto_pr_faq as cf
from crypto_pr_faq.__main__ import main

ROOT = Path(__file__).resolve().parent.parent


def test_generated_files_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "tools/generate.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_database_shape():
    entries = cf.FAQ
    assert [e["id"] for e in entries] == [f"FAQ-{i:02d}" for i in range(1, 51)]
    for e in entries:
        assert set(e) == {"id", "category", "question", "answer", "popularity", "keywords", "searches"}
        assert isinstance(e["popularity"], int) and 0 <= e["popularity"] <= 100
        assert e["question"].endswith("?") and e["answer"]
        assert e["keywords"] and e["searches"]
        assert all(s == s.lower() for s in e["searches"])
    assert len(cf.categories()) == 6
    questions = [e["question"] for e in entries]
    assert len(set(questions)) == len(questions)
    phrases = [s for e in entries for s in e["searches"]]
    assert len(set(phrases)) == len(phrases), "search phrases must be unique"


def test_config():
    c = cf.CONFIG
    assert c["brand"] == "BHMarketer.ai"
    assert c["repository"] == "https://github.com/bhmarketer-ai/BHMarketer-Crypto-Press-Release-FAQ-Generator"
    assert c["service_page"].endswith(c["seo"]["url_path"])
    assert c["seo"]["primary_keyword"] == c["seo"]["h1"]
    assert len(c["seo"]["keywords"]) == 8


def test_search_phrases_find_their_entry():
    for e in cf.FAQ:
        for s in e["searches"]:
            assert cf.ask(s)[0]["id"] == e["id"], f"{s!r} did not return {e['id']}"


@pytest.mark.parametrize("query, expected", [
    ("how much does it cost", "FAQ-36"),
    ("which outlets", "FAQ-11"),
    ("will it appear on google", "FAQ-28"),
    ("is publication guaranteed", "FAQ-44"),
    ("what is the tat", "FAQ-40"),
    ("how long does it take", "FAQ-40"),
    ("can you write it for me", "FAQ-20"),
    ("coindesk", "FAQ-14"),
    ("presale", "FAQ-26"),
    ("do you include backlinks", "FAQ-16"),
    ("how do i buy", "FAQ-39"),
    ("is there a minimum", "FAQ-37"),
    ("can i choose outlets", "FAQ-12"),
    ("ai overviews", "FAQ-31"),
    ("negative results", "FAQ-32"),
    ("how long should it be", "FAQ-22"),
    ("do you work worldwide", "FAQ-08"),
    ("why choose you", "FAQ-48"),
    ("bundle", "FAQ-41"),
    ("how does it work", "FAQ-03"),
    ("can i buy it", "FAQ-02"),
    ("buy crypto press release", "FAQ-02"),
    ("what do i need to give you", "FAQ-38"),
    ("will it raise token price", "FAQ-47"),
])
def test_ask(query, expected):
    assert cf.ask(query)[0]["id"] == expected


def test_ask_no_match_and_limit():
    assert cf.ask("xyzzy") == []
    assert cf.ask("") == []
    assert len(cf.ask("outlets", limit=2)) == 2


def test_get_and_categories():
    assert cf.get("7")["id"] == "FAQ-07"
    assert cf.get("faq-50")["id"] == "FAQ-50"
    assert cf.get("99") is None
    assert len(cf.by_category("Outlets, Networks")) == 9


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.text, self.scripts, self._tag = [], {}, [], None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self._tag = tag

    def handle_data(self, data):
        if self._tag == "script":
            self.scripts.append(data)
        elif self._tag in ("h2", "h3", "p") and data.strip():
            self.text.setdefault(self._tag, []).append(data)

    def handle_endtag(self, tag):
        self._tag = None


def test_faq_html_structure_matches_brief():
    page = _Collector()
    page.feed(cf.page_html())
    assert page.tags.count("h2") == 1
    assert page.tags.count("h3") == 50
    assert page.text["h3"] == [e["question"] for e in cf.FAQ]
    assert page.text["p"] == [e["answer"] for e in cf.FAQ]
    data = json.loads(page.scripts[0])
    assert data["@type"] == "FAQPage"
    assert [q["name"] for q in data["mainEntity"]] == page.text["h3"]
    assert [q["acceptedAnswer"]["text"] for q in data["mainEntity"]] == page.text["p"]


def test_schema_faq_matches_database():
    schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
    page = next(n for n in schema["@graph"] if n["@type"] == "FAQPage")
    assert page["mainEntity"] == cf.to_jsonld_data(cf.FAQ)["mainEntity"]


def test_faq_text_numbered_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for e in cf.FAQ:
        assert f"**{cf.number(e)}. {e['question']}**\n\n{e['answer']}" in readme
        assert e["answer"] in readme


def test_no_em_or_en_dashes_in_content():
    files = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "llms.txt", ROOT / "docs/index.md", ROOT / "docs/faq.md",
             ROOT / "output/faq-section.html", *(ROOT / "crypto_pr_faq").glob("*.json"),
             ROOT / "dataset/crypto_press_release_faqs.csv", ROOT / "schema.json", ROOT / ".zenodo.json"]
    for f in files:
        assert not re.search("[\u2013\u2014]", f.read_text(encoding="utf-8")), f.name


def test_no_invented_numbers_for_tat_or_price():
    for e in cf.FAQ:
        assert not re.search(r"\$\s?\d|\d+\s*(business\s+)?(days?|hours?|weeks?)\b", e["answer"], re.I), e["id"]


def test_cli(capsys):
    assert main(["ask", "how", "much", "does", "it", "cost"]) == 0
    out = capsys.readouterr().out
    assert "Q: How much does it cost to buy a crypto press release from BHMarketer.ai?" in out
    assert main(["show", "11", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "FAQ-11"
    assert main(["html"]) == 0
    assert capsys.readouterr().out == cf.page_html()
    assert main(["top", "3"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].strip().startswith("FAQ-36")
    assert main(["ask", "xyzzy"]) == 0
    assert "No matching question" in capsys.readouterr().out
    assert main(["show", "99"]) == 1


def test_popular():
    top = cf.popular(10)
    assert len(top) == 10
    assert [e["popularity"] for e in top] == sorted((e["popularity"] for e in top), reverse=True)
    assert top[0]["popularity"] == max(e["popularity"] for e in cf.FAQ)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for i, e in enumerate(top, 1):
        assert f"| {i} | {cf.number(e)} | {e['question']} |" in readme


def test_page_html_has_no_popularity():
    assert "Popularity" not in cf.page_html() and "popularity" not in cf.page_html()


@pytest.mark.parametrize("fmt", ["text", "markdown", "json", "jsonld", "html"])
def test_render_formats(fmt):
    out = cf.render(cf.FAQ, fmt)
    assert cf.FAQ[0]["question"] in out and cf.FAQ[-1]["question"] in out


def test_no_scoring_content():
    for f in [ROOT / "README.md", ROOT / "llms.txt", ROOT / "docs/index.md", ROOT / "schema.json", ROOT / ".zenodo.json"]:
        text = f.read_text(encoding="utf-8").lower()
        assert "benchmark cases" not in text and "lifetime" not in text and "permanent placement" not in text, f.name


def test_readme_has_no_popularity_percent():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "%" not in readme and "Popularity:" not in readme


def test_main_keywords():
    c = cf.CONFIG
    assert c["seo"]["primary_keyword"] == "Buy Crypto Press Release"
    text = " ".join(e["question"] + " " + e["answer"] for e in cf.FAQ)
    assert text.count("BHMarketer.ai") >= 30
    assert sum("buy" in e["question"].lower() for e in cf.FAQ) >= 15
