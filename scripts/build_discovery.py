#!/usr/bin/env python3
"""Generate and check Yonsei STL discovery files.

The publication registry at data/publications.json is the source for
sitemap.xml, llms.txt, and publications/index.html. Paper HTML is not
rewritten. Run this script after editing the registry or a paper head:

    python scripts/build_discovery.py
    python scripts/build_discovery.py --check

To add a paper, copy an existing project folder, edit its HTML, append one
object to data/publications.json, then run this script. Do not rename a
folder after its URL has been published.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "publications.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
LLMS_PATH = ROOT / "llms.txt"
PUBLICATIONS_PATH = ROOT / "publications" / "index.html"
ROBOTS_PATH = ROOT / "robots.txt"
DRAFT_MARKERS = ("IVIFormer_draft", "MWSC_draft", "RPT-SR")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def load_registry() -> dict:
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    publications = data.get("publications")
    if not isinstance(publications, list) or not publications:
        raise SystemExit("publications.json must contain a non-empty publications list")
    paths = [item.get("path") for item in publications]
    if len(paths) != len(set(paths)):
        raise SystemExit("publications.json contains a duplicate project path")
    return data


def project_url(registry: dict, publication: dict) -> str:
    return f"{registry['base_url']}/{publication['path']}/"


def doi_url(publication: dict) -> str:
    return f"https://doi.org/{publication['doi']}"


def image_url(registry: dict, publication: dict) -> str:
    return f"{registry['base_url']}/{publication['path']}/{publication['image']}"


def publication_sort_value(publication: dict) -> str:
    """Sort full dates before a year-only date in the same year.

    A year-only value means the source did not give a month or day. Padding
    it to YYYY-00 keeps it after the dated records from that year when the
    list is newest-first, without inventing a month.
    """
    value = publication["date_published"]
    if re.fullmatch(r"\d{4}", value):
        return f"{value}-00"
    return value


def sorted_publications(registry: dict) -> list[dict]:
    return sorted(
        registry["publications"],
        key=lambda item: (publication_sort_value(item), item["title"]),
        reverse=True,
    )


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def html_escape(value: str) -> str:
    return xml_escape(value)


def periodical(publication: dict) -> dict:
    node = {
        "@type": "Periodical",
        "name": publication["journal"],
    }
    if publication.get("issn"):
        node["issn"] = publication["issn"]
    if not publication.get("volume"):
        return node
    volume = {
        "@type": "PublicationVolume",
        "volumeNumber": publication["volume"],
        "isPartOf": node,
    }
    if publication.get("issue"):
        return {
            "@type": "PublicationIssue",
            "issueNumber": publication["issue"],
            "isPartOf": volume,
        }
    return volume


def json_ld(registry: dict, publication: dict) -> dict:
    authors = []
    for author in publication["authors"]:
        person = {
            "@type": "Person",
            "name": author["name"],
            "url": author["url"],
            "affiliation": {
                "@type": "Organization",
                "name": author["affiliation"],
            },
        }
        authors.append(person)
    same_as = [doi_url(publication)]
    if publication.get("arxiv_url"):
        same_as.append(publication["arxiv_url"])
    document = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": publication["title"],
        "name": publication["title"],
        "author": authors,
        "datePublished": publication.get("online_date") or publication["date_published"],
        "description": publication["abstract"],
        "publisher": {"@type": "Organization", "name": publication["publisher"]},
        "isPartOf": periodical(publication),
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "DOI",
            "value": publication["doi"],
        },
        "sameAs": same_as,
        "url": project_url(registry, publication),
        "image": image_url(registry, publication),
        "keywords": publication["keywords"],
    }
    if publication.get("pdf_url"):
        document["encoding"] = {
            "@type": "MediaObject",
            "contentUrl": publication["pdf_url"],
            "encodingFormat": "application/pdf",
        }
    return document


def citation_meta(publication: dict) -> list[tuple[str, str]]:
    container_meta = publication.get("container_meta", "citation_journal_title")
    tags = [
        ("citation_title", publication["title"]),
        *[("citation_author", author["citation"]) for author in publication["authors"]],
        ("citation_publication_date", publication["citation_publication_date"]),
        (container_meta, publication["journal"]),
    ]
    if publication.get("volume"):
        tags.append(("citation_volume", publication["volume"]))
    if publication.get("issue"):
        tags.append(("citation_issue", publication["issue"]))
    tags.append(("citation_firstpage", publication["firstpage"]))
    if publication.get("issn"):
        tags.append(("citation_issn", publication["issn"]))
    tags.extend(
        [
            ("citation_doi", publication["doi"]),
            ("citation_abstract", publication["abstract"]),
        ]
    )
    if publication.get("pdf_url"):
        tags.append(("citation_pdf_url", publication["pdf_url"]))
    return tags


def render_seo_block(registry: dict, publication: dict) -> str:
    url = project_url(registry, publication)
    image = image_url(registry, publication)
    lines = [
        "<!-- seo:meta:start -->",
        f'<link rel="canonical" href="{html_escape(url)}">',
        '<link rel="describedby" href="https://yonsei-stl.github.io/llms.txt">',
    ]
    for name, content in citation_meta(publication):
        lines.append(f'<meta name="{name}" content="{html_escape(content)}">')
    lines.extend(
        [
            '<meta property="og:type" content="article">',
            f'<meta property="og:title" content="{html_escape(publication["title"])}">',
            f'<meta property="og:description" content="{html_escape(publication["meta_description"])}">',
            f'<meta property="og:url" content="{html_escape(url)}">',
            f'<meta property="og:image" content="{html_escape(image)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{html_escape(publication["title"])}">',
            f'<meta name="twitter:description" content="{html_escape(publication["meta_description"])}">',
            f'<meta name="twitter:image" content="{html_escape(image)}">',
            '<script type="application/ld+json">',
            json.dumps(json_ld(registry, publication), ensure_ascii=False, indent=2),
            "</script>",
            "<!-- seo:meta:end -->",
        ]
    )
    return "\n".join(lines)


def render_sitemap(registry: dict) -> str:
    urls = [f"{registry['base_url']}/publications/"]
    urls.extend(project_url(registry, item) for item in sorted_publications(registry))
    body = "\n".join(
        f"  <url>\n    <loc>{xml_escape(url)}</loc>\n  </url>" for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{SITEMAP_NS}">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def render_llms(registry: dict) -> str:
    lines = [
        "# Yonsei STL",
        "",
        f"> Research project pages from {registry['lab_name']}.",
        "",
        "This file maps published project pages for agents that request it. "
        "It does not replace the HTML pages, the sitemap, or the papers.",
        "",
        "## Publications",
        "",
        f"- [Publication index]({registry['base_url']}/publications/): "
        "Published Yonsei STL research project pages",
    ]
    for publication in sorted_publications(registry):
        lines.append(
            f"- [{publication['title']}]({project_url(registry, publication)}): "
            f"{publication['summary']}"
        )
    lines.extend(["", "## Bibliographic records", ""])
    for publication in sorted_publications(registry):
        lines.append(f"- [{publication['title']} DOI]({doi_url(publication)})")
        extras = catalog_resources(publication)
        if extras is None:
            if publication.get("arxiv_url"):
                lines.append(f"- [{publication['path']} arXiv]({publication['arxiv_url']})")
            if publication.get("code_url"):
                lines.append(f"- [{publication['path']} code]({publication['code_url']})")
            if publication.get("dataset_url"):
                lines.append(f"- [{publication['path']} dataset]({publication['dataset_url']})")
            if publication.get("pdf_url"):
                lines.append(f"- [{publication['path']} PDF]({publication['pdf_url']})")
        else:
            for item in extras:
                lines.append(
                    f"- [{publication['path']} {item['label']}]({item['url']})"
                )
    lines.append("")
    return "\n".join(lines)


def catalog_resources(publication: dict) -> list[dict] | None:
    """Extra catalog links supplied with a paper.

    Returns None when the record uses the older arXiv/code/dataset fields.
    Paper links are omitted because the catalog already renders that button.
    """
    resources = publication.get("resources")
    if not resources:
        return None
    paper_url = publication.get("paper_url")
    return [
        item
        for item in resources
        if item.get("label") != "Paper" and item.get("url") != paper_url
    ]


def render_button(href: str, label: str) -> str:
    return (
        f'<a class="button" href="{html_escape(href)}">{html_escape(label)}</a>'
    )


def render_publications_page(registry: dict) -> str:
    cards = []
    items = []
    for position, publication in enumerate(sorted_publications(registry), start=1):
        url = project_url(registry, publication)
        authors = ", ".join(html_escape(author["name"]) for author in publication["authors"])
        thumb = f"../{publication['path']}/{publication['image']}"
        buttons = [
            render_button(url, "Project page"),
            render_button(publication["paper_url"], "Paper"),
        ]
        extras = catalog_resources(publication)
        if extras is None:
            if publication.get("arxiv_url"):
                buttons.append(render_button(publication["arxiv_url"], "arXiv"))
            if publication.get("code_url"):
                buttons.append(render_button(publication["code_url"], "Code"))
            if publication.get("dataset_url"):
                buttons.append(render_button(publication["dataset_url"], "Dataset"))
        else:
            for item in extras:
                buttons.append(render_button(item["url"], item["label"]))
        cards.append(
            "\n".join(
                [
                    "<article>",
                    f'<a class="thumb-link" href="{html_escape(url)}">',
                    f'<img src="{html_escape(thumb)}" alt="{html_escape(publication["title"])} figure">',
                    "</a>",
                    "<div>",
                    f"<h2><a href=\"{html_escape(url)}\">{html_escape(publication['title'])}</a></h2>",
                    f"<p class=\"authors\">{authors}</p>",
                    f"<p class=\"venue\">{html_escape(publication['venue_label'])}</p>",
                    f"<p>{html_escape(publication['summary'])}</p>",
                    f"<p class=\"actions\">{''.join(buttons)}</p>",
                    "</div>",
                    "</article>",
                ]
            )
        )
        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": publication["title"],
                "url": url,
            }
        )
    collection = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Yonsei STL Publications",
        "url": f"{registry['base_url']}/publications/",
        "description": "Published research project pages from Seamless Trans-X Lab, Yonsei University.",
        "mainEntity": {"@type": "ItemList", "itemListElement": items},
    }
    style = """
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Google Sans", "Noto Sans", sans-serif;
      color: #222;
      background: #fff;
      line-height: 1.5;
    }
    header, main { width: min(960px, calc(100% - 2rem)); margin: 0 auto; }
    header { padding: 2.5rem 0 1rem; }
    .lab { margin: 0 0 0.5rem; color: #555; }
    h1 { margin: 0 0 0.75rem; font-size: clamp(2rem, 5vw, 3.25rem); line-height: 1.15; }
    .lede { max-width: 42rem; color: #333; }
    article {
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 1.25rem;
      padding: 1.25rem 0;
      border-top: 1px solid #e6e6e6;
    }
    article img { width: 100%; height: 120px; object-fit: contain; background: #fafafa; border-radius: 8px; }
    h2 { margin: 0 0 0.35rem; font-size: 1.25rem; line-height: 1.3; }
    h2 a { color: inherit; }
    .authors, .venue { margin: 0.15rem 0; }
    .venue { color: #555; font-weight: 700; }
    .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .button {
      display: inline-block;
      padding: 0.4rem 0.9rem;
      border-radius: 999px;
      background: #363636;
      color: #fff;
      text-decoration: none;
    }
    a:focus-visible, .button:focus-visible { outline: 3px solid #3273dc; outline-offset: 2px; }
    footer { width: min(960px, calc(100% - 2rem)); margin: 0 auto 2rem; color: #555; }
    @media (max-width: 700px) {
      article { grid-template-columns: 1fr; }
      article img { height: 180px; }
    }
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Publications | Yonsei STL</title>
  <meta name="description" content="Published research project pages from Seamless Trans-X Lab, Yonsei University.">
  <link rel="canonical" href="{registry['base_url']}/publications/">
  <link rel="describedby" href="{registry['base_url']}/llms.txt">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Publications | Yonsei STL">
  <meta property="og:description" content="Published research project pages from Seamless Trans-X Lab, Yonsei University.">
  <meta property="og:url" content="{registry['base_url']}/publications/">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Publications | Yonsei STL">
  <meta name="twitter:description" content="Published research project pages from Seamless Trans-X Lab, Yonsei University.">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Google+Sans|Noto+Sans|Castoro">
  <script type="application/ld+json">
{json.dumps(collection, ensure_ascii=False, indent=2)}
  </script>
  <style>{style}</style>
</head>
<body>
  <header>
    <p class="lab"><a href="{html_escape(registry['lab_url'])}">{html_escape(registry['lab_name'].split(',')[0])}</a>, Yonsei University</p>
    <h1>Publications</h1>
    <p class="lede">Project pages for published research from Yonsei STL. Each link below keeps the existing project URL.</p>
  </header>
  <main>
{chr(10).join(cards)}
  </main>
  <footer>
    <p><a href="{html_escape(registry['lab_url'])}">Lab website</a></p>
  </footer>
</body>
</html>
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: list[tuple[str, str, str]] = []
        self.links: list[tuple[str, str]] = []
        self.anchors: list[tuple[str, str]] = []
        self.images: list[tuple[str, str | None]] = []
        self.json_ld: list[str] = []
        self.h1_count = 0
        self.html_lang = ""
        self._capture_json = False
        self._json_parts: list[str] = []
        self._in_h1 = False
        self._anchor_href = ""
        self._anchor_parts: list[str] = []
        self._in_anchor = False
        self._author_depth = 0
        self._author_names: list[str] = []
        self._capture_abstract = False
        self._abstract_parts: list[str] = []
        self._in_abstract_p = False
        self.visible_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_lang = attr.get("lang", "")
        if tag == "meta":
            self.metas.append((attr.get("name", ""), attr.get("property", ""), attr.get("content", "")))
        if tag == "link":
            self.links.append((attr.get("rel", ""), attr.get("href", "")))
        if tag == "a":
            self._in_anchor = True
            self._anchor_href = attr.get("href", "")
            self._anchor_parts = []
        if tag == "img":
            self.images.append((attr.get("src", ""), attr.get("alt")))
        if tag == "h1":
            self.h1_count += 1
            self._in_h1 = True
        if tag == "script" and attr.get("type") == "application/ld+json":
            self._capture_json = True
            self._json_parts = []
            self._skip_depth += 1
        classes = attr.get("class", "")
        if tag == "div" and "publication-authors" in classes.split():
            self._author_depth += 1
        if self._capture_abstract and tag == "p" and not self._abstract_parts:
            self._in_abstract_p = True
        if tag in {"script", "style"} and not self._capture_json:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_anchor:
            text = normalize_space("".join(self._anchor_parts))
            self.anchors.append((self._anchor_href, text))
            if self._author_depth and text:
                self._author_names.append(text.rstrip(","))
            self._in_anchor = False
        if tag == "h1":
            self._in_h1 = False
        if tag == "div" and self._author_depth:
            self._author_depth -= 1
        if tag == "p" and self._in_abstract_p:
            self._in_abstract_p = False
            self._capture_abstract = False
        if tag == "script" and self._capture_json:
            self.json_ld.append("".join(self._json_parts))
            self._capture_json = False
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_json:
            self._json_parts.append(data)
            return
        if self._skip_depth:
            return
        if self._in_anchor:
            self._anchor_parts.append(data)
        if normalize_space(data) == "Abstract":
            self._capture_abstract = True
        if self._in_abstract_p:
            self._abstract_parts.append(data)
        if data.strip():
            self.visible_parts.append(data)

    @property
    def abstract(self) -> str:
        return normalize_space("".join(self._abstract_parts))

    @property
    def visible_text(self) -> str:
        return normalize_space("".join(self.visible_parts))


def meta_values(parser: PageParser, name: str) -> list[str]:
    return [content for meta_name, _prop, content in parser.metas if meta_name == name]


def property_values(parser: PageParser, prop: str) -> list[str]:
    return [content for _name, meta_prop, content in parser.metas if meta_prop == prop]


def find_periodical(node: dict) -> dict:
    current = node.get("isPartOf")
    while isinstance(current, dict) and current.get("@type") != "Periodical":
        current = current.get("isPartOf")
    return current if isinstance(current, dict) else {}


def find_volume(node: dict) -> str:
    current = node.get("isPartOf")
    while isinstance(current, dict):
        if current.get("@type") == "PublicationVolume":
            return str(current.get("volumeNumber", ""))
        current = current.get("isPartOf")
    return ""


def find_issue(node: dict) -> str:
    current = node.get("isPartOf", {})
    if isinstance(current, dict) and current.get("@type") == "PublicationIssue":
        return str(current.get("issueNumber", ""))
    return ""


def check_relative_assets(html: str, page_dir: Path, label: str, errors: list[str]) -> None:
    visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    suffixes = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf", ".bib", ".json"}
    sources = re.findall(r'(?:src|href)="([^"]+)"', visible)
    for srcset in re.findall(r'srcset="([^"]+)"', visible):
        for part in srcset.split(","):
            url = part.strip().split(" ", 1)[0]
            if url:
                sources.append(url)
    for src in sources:
        if src.startswith(("http://", "https://", "data:", "mailto:", "#", "//")):
            continue
        relative = src.split("?", 1)[0].split("#", 1)[0]
        path = (ROOT / relative.lstrip("/")).resolve() if relative.startswith("/") else (page_dir / relative).resolve()
        if path.suffix.lower() not in suffixes:
            continue
        if ROOT.resolve() not in path.parents and path != ROOT.resolve():
            errors.append(f"{label}: asset path escapes the repository ({src})")
        elif not path.is_file():
            errors.append(f"{label}: missing local asset {src}")


def allowed_external_urls(registry: dict, publication: dict) -> set[str]:
    allowed = {
        project_url(registry, publication),
        doi_url(publication),
        publication["paper_url"],
        registry["lab_url"],
        f"{registry['base_url']}/",
        f"{registry['base_url']}/publications/",
        f"{registry['base_url']}/llms.txt",
    }
    for author in publication["authors"]:
        allowed.add(author["url"])
    for item in publication.get("resources") or []:
        allowed.add(item["url"])
    for found in re.findall(r"https://[^\s<>\"']+", publication["abstract"]):
        allowed.add(found.rstrip(".,;:)"))
    return allowed


def part_names(node: dict) -> list[str]:
    names = []
    current = node.get("isPartOf")
    while isinstance(current, dict):
        if current.get("name"):
            names.append(str(current["name"]))
        current = current.get("isPartOf")
    return names


def check_supplied_publication(registry: dict, publication: dict, errors: list[str]) -> None:
    """Check a packaged project page without rewriting its citation markup."""
    path = ROOT / publication["path"] / "index.html"
    label = publication["path"]
    if not path.is_file():
        errors.append(f"{label}: missing index.html")
        return
    html = path.read_text(encoding="utf-8")
    if "noindex" in html.lower():
        errors.append(f"{label}: page contains noindex")
    for pdf in (ROOT / publication["path"]).rglob("*.pdf"):
        errors.append(f"{label}: publisher PDF must not be committed ({pdf.relative_to(ROOT)})")
    parser = PageParser()
    parser.feed(html)
    url = project_url(registry, publication)
    image = image_url(registry, publication)
    authors = [author["name"] for author in publication["authors"]]

    if parser.html_lang != "en":
        errors.append(f"{label}: html lang must be en")
    h1_text = [
        normalize_space(re.sub(r"<[^>]+>", "", match))
        for match in re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, flags=re.S)
    ]
    if h1_text != [publication["title"]]:
        errors.append(f"{label}: expected one h1 equal to the title, found {h1_text}")
    canonical = [href for rel, href in parser.links if rel == "canonical"]
    if canonical != [url]:
        errors.append(f"{label}: canonical is {canonical}, expected {url}")
    described = [href for rel, href in parser.links if rel == "describedby"]
    if described != [f"{registry['base_url']}/llms.txt"]:
        errors.append(f"{label}: missing describedby link to llms.txt")
    if f"{registry['base_url']}/publications/" not in html:
        errors.append(f"{label}: missing link to the publication index")

    ids = re.findall(r'\sid="([^"]+)"', html)
    if len(ids) != len(set(ids)):
        errors.append(f"{label}: duplicate element ids")
    if html.count("<details") != html.count("<summary"):
        errors.append(f"{label}: figure disclosures are not native details/summary pairs")
    for required in ('id="BibTeX"', 'id="bibtex-code"', 'href="citation.bib"', 'href="citation.json"', "data-copy-bibtex hidden"):
        if required not in html:
            errors.append(f"{label}: missing citation control {required}")

    actual_by_name: dict[str, list[str]] = {}
    for name, _prop, content in parser.metas:
        if name.startswith("citation_"):
            actual_by_name.setdefault(name, []).append(content)
    expected_meta = {
        "citation_title": [publication["title"]],
        "citation_author": authors,
        "citation_publication_date": [publication["citation_publication_date"]],
        publication.get("container_meta", "citation_journal_title"): [publication["journal"]],
        "citation_doi": [publication["doi"]],
        "citation_firstpage": [publication["firstpage"]],
    }
    if publication.get("volume"):
        expected_meta["citation_volume"] = [publication["volume"]]
    elif "citation_volume" in actual_by_name:
        errors.append(f"{label}: citation_volume is present without a registry volume")
    if publication.get("lastpage"):
        expected_meta["citation_lastpage"] = [publication["lastpage"]]
    elif "citation_lastpage" in actual_by_name:
        errors.append(f"{label}: citation_lastpage is present without a registry last page")
    if publication.get("issn"):
        expected_meta["citation_issn"] = [publication["issn"]]
    elif "citation_issn" in actual_by_name:
        errors.append(f"{label}: citation_issn is present without a registry ISSN")
    if publication.get("issue"):
        expected_meta["citation_issue"] = [publication["issue"]]
    elif "citation_issue" in actual_by_name:
        errors.append(f"{label}: citation_issue is present without a registry issue")
    for name, expected_values in expected_meta.items():
        if actual_by_name.get(name) != expected_values:
            errors.append(f"{label}: {name} is {actual_by_name.get(name)}, expected {expected_values}")
    if "citation_abstract" in actual_by_name and normalize_space(actual_by_name["citation_abstract"][0]) != normalize_space(publication["abstract"]):
        errors.append(f"{label}: citation_abstract does not match the registry abstract")
    if meta_values(parser, "description") != [publication["meta_description"]]:
        errors.append(f"{label}: meta description does not match the registry")
    for prop, expected_value in (
        ("og:title", publication["title"]),
        ("og:description", publication["meta_description"]),
        ("og:url", url),
        ("og:image", image),
        ("og:type", "article"),
    ):
        if property_values(parser, prop) != [expected_value]:
            errors.append(f"{label}: {prop} does not match the registry")

    if len(parser.json_ld) != 1:
        errors.append(f"{label}: expected one JSON-LD block, found {len(parser.json_ld)}")
    else:
        try:
            data = json.loads(parser.json_ld[0])
        except json.JSONDecodeError as exc:
            errors.append(f"{label}: JSON-LD does not parse ({exc})")
            data = None
        if isinstance(data, dict):
            if data.get("@type") != "ScholarlyArticle":
                errors.append(f"{label}: JSON-LD type is not ScholarlyArticle")
            if data.get("headline") != publication["title"] or data.get("name") != publication["title"]:
                errors.append(f"{label}: JSON-LD title does not match the registry")
            if data.get("url") != url or data.get("image") != image:
                errors.append(f"{label}: JSON-LD url or image does not match the registry")
            if normalize_space(str(data.get("abstract", ""))) != normalize_space(publication["abstract"]):
                errors.append(f"{label}: JSON-LD abstract does not match the registry")
            if normalize_space(str(data.get("description", ""))) != normalize_space(publication["meta_description"]):
                errors.append(f"{label}: JSON-LD description does not match the registry")
            if [author.get("name") for author in data.get("author", [])] != authors:
                errors.append(f"{label}: JSON-LD authors do not match the registry")
            if data.get("identifier", {}).get("value") != publication["doi"]:
                errors.append(f"{label}: JSON-LD DOI does not match the registry")
            same_as = data.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            if doi_url(publication) not in same_as:
                errors.append(f"{label}: JSON-LD sameAs is missing the DOI URL")
            if data.get("keywords") != publication["keywords"]:
                errors.append(f"{label}: JSON-LD keywords do not match the registry")
            online_date = publication.get("online_date")
            if online_date:
                if data.get("datePublished") != online_date:
                    errors.append(f"{label}: JSON-LD datePublished does not match the online date")
            elif re.fullmatch(r"\d{4}", publication["date_published"]):
                if data.get("datePublished"):
                    errors.append(f"{label}: JSON-LD has a full date the registry does not")
            elif data.get("datePublished") != publication["date_published"]:
                errors.append(f"{label}: JSON-LD datePublished does not match the registry")
            if publication["journal"] not in part_names(data):
                errors.append(f"{label}: JSON-LD container does not match the registry")
            found_volume = find_volume(data)
            if publication.get("volume"):
                if found_volume != publication["volume"]:
                    errors.append(f"{label}: JSON-LD volume does not match the registry")
            elif found_volume:
                errors.append(f"{label}: JSON-LD volume is present without a registry volume")

    if parser.abstract != normalize_space(publication["abstract"]):
        errors.append(f"{label}: visible abstract does not match the registry")
    if parser._author_names != authors:
        errors.append(f"{label}: visible authors {parser._author_names} do not match the registry")
    if publication["venue_label"] not in parser.visible_text:
        errors.append(f"{label}: venue label is not visible")
    bibtex_doi = publication["bibtex_doi"].lower()
    if f"doi = {{{bibtex_doi}}}" not in html.lower():
        errors.append(f"{label}: BibTeX is missing the bare DOI")
    if "doi = {https://doi.org/" in html.lower():
        errors.append(f"{label}: BibTeX DOI is a URL instead of a bare DOI")
    if publication["bibtex_author"] not in html:
        errors.append(f"{label}: BibTeX author string does not match the registry")
    if f"year = {{{publication['citation_publication_date']}}}" not in html:
        errors.append(f"{label}: BibTeX year does not match the citation year")
    for src, alt in parser.images:
        if not alt or not alt.strip():
            errors.append(f"{label}: image {src} is missing alt text")
    check_relative_assets(html, path.parent, label, errors)

    csl_path = path.parent / "citation.json"
    if not csl_path.is_file():
        errors.append(f"{label}: missing citation.json")
    else:
        try:
            csl = json.loads(csl_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{label}: citation.json does not parse ({exc})")
            csl = None
        if isinstance(csl, dict):
            if csl.get("title") != publication["title"] or csl.get("DOI") != publication["doi"]:
                errors.append(f"{label}: CSL-JSON title or DOI does not match the registry")
            issued = csl.get("issued", {}).get("date-parts", [[None]])[0][0]
            if str(issued) != publication["citation_publication_date"]:
                errors.append(f"{label}: CSL-JSON year does not match the citation year")
            csl_authors = [
                f"{author.get('given', '')} {author.get('family', '')}".strip()
                for author in csl.get("author", [])
            ]
            if csl_authors != authors:
                errors.append(f"{label}: CSL-JSON authors do not match the registry")
            if csl.get("container-title") != publication["journal"]:
                errors.append(f"{label}: CSL-JSON container does not match the registry")

    allowed = allowed_external_urls(registry, publication)
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith("#") or "://" not in href and not href.startswith("mailto:"):
            continue
        if href in allowed:
            continue
        if href in {"https://fonts.googleapis.com", "https://fonts.gstatic.com"} or href.startswith(
            ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")
        ):
            continue
        if href.startswith("mailto:shiho@yonsei.ac.kr"):
            continue
        errors.append(f"{label}: unexpected external URL {href}")


def check_publication(registry: dict, publication: dict, errors: list[str]) -> None:
    if publication.get("page_profile") == "supplied":
        check_supplied_publication(registry, publication, errors)
        return
    path = ROOT / publication["path"] / "index.html"
    label = publication["path"]
    if not path.is_file():
        errors.append(f"{label}: missing index.html")
        return
    html = path.read_text(encoding="utf-8")
    if "noindex" in html.lower():
        errors.append(f"{label}: page contains noindex")
    parser = PageParser()
    parser.feed(html)
    url = project_url(registry, publication)
    image = image_url(registry, publication)

    if parser.html_lang != "en":
        errors.append(f"{label}: html lang must be en")
    if parser.h1_count != 1:
        errors.append(f"{label}: expected one h1, found {parser.h1_count}")
    canonical = [href for rel, href in parser.links if rel == "canonical"]
    if canonical != [url]:
        errors.append(f"{label}: canonical is {canonical}, expected {url}")
    described = [href for rel, href in parser.links if rel == "describedby"]
    if described != [f"{registry['base_url']}/llms.txt"]:
        errors.append(f"{label}: missing describedby link to llms.txt")

    expected = citation_meta(publication)
    expected_names = [name for name, _content in expected]
    actual_by_name: dict[str, list[str]] = {}
    for name, _prop, content in parser.metas:
        if name.startswith("citation_"):
            actual_by_name.setdefault(name, []).append(content)
    if "citation_pdf_url" in actual_by_name and not publication.get("pdf_url"):
        errors.append(f"{label}: citation_pdf_url is present without a hosted PDF")
    for name, content in expected:
        found = actual_by_name.get(name, [])
        if name == "citation_author":
            continue
        if name == "citation_abstract":
            if not found or normalize_space(found[0]) != normalize_space(content):
                errors.append(f"{label}: citation_abstract does not match the registry abstract")
            continue
        if found != [content]:
            errors.append(f"{label}: {name} is {found}, expected {[content]}")
    if actual_by_name.get("citation_author") != [author["citation"] for author in publication["authors"]]:
        errors.append(f"{label}: citation_author list does not match the registry")
    missing = [name for name in expected_names if name not in actual_by_name and name != "citation_author"]
    if missing:
        errors.append(f"{label}: missing citation tags {sorted(set(missing))}")

    descriptions = meta_values(parser, "description")
    if descriptions != [publication["meta_description"]]:
        errors.append(f"{label}: meta description does not match the registry")
    for prop, expected_value in (
        ("og:title", publication["title"]),
        ("og:description", publication["meta_description"]),
        ("og:url", url),
        ("og:image", image),
        ("og:type", "article"),
    ):
        if property_values(parser, prop) != [expected_value]:
            errors.append(f"{label}: {prop} does not match the registry")
    if "teaser.png" in image and publication["path"] == "SpectraDiff":
        errors.append("SpectraDiff: social image must not be the unused 3DGS teaser")
    if publication["path"] == "SpectraDiff" and "teaser.png" in "".join(property_values(parser, "og:image")):
        errors.append("SpectraDiff: og:image points at teaser.png")

    if len(parser.json_ld) != 1:
        errors.append(f"{label}: expected one JSON-LD block, found {len(parser.json_ld)}")
    else:
        try:
            data = json.loads(parser.json_ld[0])
        except json.JSONDecodeError as exc:
            errors.append(f"{label}: JSON-LD does not parse ({exc})")
            data = None
        if isinstance(data, dict):
            if data.get("@type") != "ScholarlyArticle":
                errors.append(f"{label}: JSON-LD type is not ScholarlyArticle")
            if data.get("headline") != publication["title"] or data.get("name") != publication["title"]:
                errors.append(f"{label}: JSON-LD title does not match the registry")
            if data.get("url") != url or data.get("image") != image:
                errors.append(f"{label}: JSON-LD url or image does not match the registry")
            if normalize_space(str(data.get("description", ""))) != normalize_space(publication["abstract"]):
                errors.append(f"{label}: JSON-LD description does not match the visible abstract")
            names = [author.get("name") for author in data.get("author", [])]
            if names != [author["name"] for author in publication["authors"]]:
                errors.append(f"{label}: JSON-LD authors do not match the registry")
            identifier = data.get("identifier", {})
            if identifier.get("value") != publication["doi"]:
                errors.append(f"{label}: JSON-LD DOI does not match the registry")
            if doi_url(publication) not in data.get("sameAs", []):
                errors.append(f"{label}: JSON-LD sameAs is missing the DOI URL")
            if data.get("datePublished") != publication["date_published"]:
                errors.append(f"{label}: JSON-LD datePublished does not match the registry")
            if find_periodical(data).get("name") != publication["journal"]:
                errors.append(f"{label}: JSON-LD journal does not match the registry")
            if find_volume(data) != publication["volume"]:
                errors.append(f"{label}: JSON-LD volume does not match the registry")
            if publication.get("issue") and find_issue(data) != publication["issue"]:
                errors.append(f"{label}: JSON-LD issue does not match the registry")
            if data.get("keywords") != publication["keywords"]:
                errors.append(f"{label}: JSON-LD keywords do not match the registry")

    if parser.abstract != normalize_space(publication["abstract"]):
        errors.append(f"{label}: visible abstract does not match the registry")
    if parser._author_names != [author["name"] for author in publication["authors"]]:
        errors.append(
            f"{label}: visible authors {parser._author_names} do not match the registry"
        )
    if publication["venue_label"] not in parser.visible_text:
        errors.append(f"{label}: venue label is not visible")
    bibtex_doi = publication["bibtex_doi"].lower()
    if f"doi = {{{bibtex_doi}}}" not in html.lower():
        errors.append(f"{label}: BibTeX is missing the bare DOI")
    if "doi = {https://doi.org/" in html.lower():
        errors.append(f"{label}: BibTeX DOI is a URL instead of a bare DOI")
    if publication["bibtex_author"] not in html:
        errors.append(f"{label}: BibTeX author string does not match the registry")
    if "https://yonsei-stl.github.io/publications/" not in html:
        errors.append(f"{label}: missing link to the publication index")
    for src, alt in parser.images:
        if not alt or not alt.strip():
            errors.append(f"{label}: image {src} is missing alt text")
    check_relative_assets(html, path.parent, label, errors)
    if publication.get("pdf_url"):
        relative = publication["pdf_url"].split(f"/{publication['path']}/", 1)[-1]
        pdf_path = ROOT / publication["path"] / relative
        if not pdf_path.is_file():
            errors.append(f"{label}: pdf_url does not point at a file in the project directory")
        if not publication["pdf_url"].startswith(f"{registry['base_url']}/{publication['path']}/"):
            errors.append(f"{label}: pdf_url is outside the project directory")


def check_content_rules(errors: list[str]) -> None:
    rasmd = (ROOT / "RASMD" / "index.html").read_text(encoding="utf-8")
    pix = (ROOT / "Pix2Next" / "index.html").read_text(encoding="utf-8")
    spectra = (ROOT / "SpectraDiff" / "index.html").read_text(encoding="utf-8")
    rm = (ROOT / "RM-MLLM" / "index.html").read_text(encoding="utf-8")
    if "RAMSD" in rasmd:
        errors.append("RASMD: teaser still says RAMSD")
    for page_name, page_html in (
        ("RASMD", rasmd),
        ("Pix2Next", pix),
        ("SpectraDiff", spectra),
        ("RM-MLLM", rm),
    ):
        if "<sup></sup>" in page_html or "<sup> </sup>" in page_html:
            errors.append(f"{page_name}: empty affiliation superscript")
    if "Information Fusion Journal, Elsevier" in rasmd:
        errors.append("RASMD: journal is still listed as an affiliation")
    pix_parser = PageParser()
    pix_parser.feed(pix)
    incheol = [href for href, text in pix_parser.anchors if text == "Incheol Park"]
    if incheol != ["https://stl.yonsei.ac.kr/"]:
        errors.append(f"Pix2Next: Incheol Park link is {incheol}")
    spectra_parser = PageParser()
    spectra_parser.feed(spectra)
    visible = spectra_parser.visible_text
    for phrase in ("3DGS", "Gaussian Splatting", "stereo pairs"):
        if phrase in visible:
            errors.append(f"SpectraDiff: visible text still contains {phrase}")
    if any(text == "Supplementary" for _href, text in spectra_parser.anchors):
        errors.append("SpectraDiff: Supplementary button is still present")
    if "volume = {266}" not in spectra:
        errors.append("SpectraDiff: BibTeX is missing volume 266")
    rm_parser = PageParser()
    rm_parser.feed(rm)
    self_links = [
        href
        for href, text in rm_parser.anchors
        if href.rstrip("/") == "https://yonsei-stl.github.io/RM-MLLM"
    ]
    if self_links:
        errors.append("RM-MLLM: a button or anchor still points at the project page")
    paper_links = [href for href, text in rm_parser.anchors if text == "Paper"]
    if paper_links != ["https://doi.org/10.1016/j.rineng.2026.112317"]:
        errors.append(f"RM-MLLM: Paper link is {paper_links}")
    for label in ("Code", "Data"):
        if any(text == label for _href, text in rm_parser.anchors):
            errors.append(f"RM-MLLM: {label} button is present without a verified URL")
    if "JIN2026RASMD" in rm or "Information Fusion" in rm:
        errors.append("RM-MLLM: RASMD BibTeX residue is still present")
    for folder in ("RASMD", "SpectraDiff"):
        script = (ROOT / folder / "static" / "js" / "script.js").read_text(encoding="utf-8")
        if "if (!beforeAfterContainer)" not in script:
            errors.append(f"{folder}: slider script does not guard a missing container")
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    if 'url=https://stl.yonsei.ac.kr/' not in root:
        errors.append("Root index.html no longer redirects to the lab website")
    for draft in ("IVIFormer_draft", "MWSC_draft"):
        draft_html = (ROOT / draft / "index_old.html").read_text(encoding="utf-8")
        if 'name="robots" content="noindex"' not in draft_html:
            errors.append(f"{draft}: index_old.html is missing noindex")
    check_supplied_fidelity(errors)


def check_supplied_fidelity(errors: list[str]) -> None:
    """Keep the source-review decisions that the packaged pages were built to preserve."""
    ivi = (ROOT / "IVIFormer" / "index.html").read_text(encoding="utf-8")
    if "ICCV Workshops, 2025" not in ivi:
        errors.append("IVIFormer: venue must stay ICCV Workshops, 2025")
    if "Car, Traffic Sign, and Bus decrease" not in ivi:
        errors.append("IVIFormer: class-level detection decreases are missing")
    for value in (
        "0.5317",
        "0.5201",
        "0.2752",
        "0.2224",
        "0.1410",
        "0.1080",
        "0.2018",
        "0.3638",
        "0.2505",
        "0.2673",
    ):
        if f"<td>{value}</td>" not in ivi:
            errors.append(f"IVIFormer: missing detection value {value}")

    swir = (ROOT / "SWIR-Material-Classification" / "index.html").read_text(encoding="utf-8")
    if swir.count("<sup>†</sup>") != 5:
        errors.append("SWIR-Material-Classification: expected five equal-contribution markers")
    if swir.count('name="citation_author"') != 7:
        errors.append("SWIR-Material-Classification: expected seven authors")
    for value in ("0.58", "0.92", "0.75", "0.99", "0.73", "1.00", "0.77"):
        if f"<td>{value}</td>" not in swir:
            errors.append(f"SWIR-Material-Classification: missing per-object accuracy {value}")
    if "not used here as an aggregate accuracy" not in swir:
        errors.append("SWIR-Material-Classification: explanatory note for the abstract percentages is missing")

    rain = (ROOT / "SeeingThroughRain" / "index.html").read_text(encoding="utf-8")
    if "Measurement, 2026" not in rain or "Available online 12 November 2025" not in rain:
        errors.append("SeeingThroughRain: citation year and online date must both remain visible")
    if '"datePublished": "2025-11-12"' not in rain or 'name="citation_publication_date" content="2026"' not in rain:
        errors.append("SeeingThroughRain: JSON-LD online date and citation year are no longer distinct")
    if "29% visibility increase" not in rain or "do not directly match that headline percentage" not in rain:
        errors.append("SeeingThroughRain: visibility explanatory note is missing")
    for value in ("1479.6 m", "4869.5 m", "353.0 m", "537.7 m", "308.1 m", "454.3 m"):
        if value not in rain:
            errors.append(f"SeeingThroughRain: missing visibility estimate {value}")
    if "github.com" in rain:
        errors.append("SeeingThroughRain: a code repository link was added")

    mwsc = (ROOT / "MWSC" / "index.html").read_text(encoding="utf-8")
    lowered = mwsc.lower()
    if any(phrase in lowered for phrase in ("five vlm", "six vlm", "5 vlms", "6 vlms")):
        errors.append("MWSC: page resolves the unresolved VLM count")
    if "100m" in lowered:
        errors.append("MWSC: page reprints the unresolved fog-visibility threshold")


def check_robots(errors: list[str]) -> None:
    if not ROBOTS_PATH.is_file():
        errors.append("robots.txt is missing")
        return
    lines = []
    for raw in ROBOTS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = raw.split("#", 1)[0].strip()
        if stripped:
            lines.append(stripped)
    disallows = [line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("disallow:")]
    allows = [line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("allow:")]
    sitemaps = [line.split(":", 1)[1].strip() for line in lines if line.lower().startswith("sitemap:")]
    if allows != ["/"]:
        errors.append(f"robots.txt Allow rules are {allows}")
    if disallows != ["/IVIFormer_draft/", "/MWSC_draft/"]:
        errors.append(f"robots.txt Disallow rules are {disallows}")
    if sitemaps != ["https://yonsei-stl.github.io/sitemap.xml"]:
        errors.append(f"robots.txt Sitemap is {sitemaps}")


def check_generated(registry: dict, errors: list[str]) -> None:
    expected = {
        SITEMAP_PATH: render_sitemap(registry),
        LLMS_PATH: render_llms(registry),
        PUBLICATIONS_PATH: render_publications_page(registry),
    }
    for path, content in expected.items():
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)} is missing; run the generator")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != content:
            errors.append(f"{path.relative_to(ROOT)} does not match the registry; regenerate it")
        for marker in DRAFT_MARKERS:
            if marker in actual:
                errors.append(f"{path.relative_to(ROOT)} exposes {marker}")
    if PUBLICATIONS_PATH.is_file():
        check_relative_assets(
            PUBLICATIONS_PATH.read_text(encoding="utf-8"),
            PUBLICATIONS_PATH.parent,
            "publications",
            errors,
        )
    if SITEMAP_PATH.is_file():
        try:
            tree = ET.fromstring(SITEMAP_PATH.read_text(encoding="utf-8"))
        except ET.ParseError as exc:
            errors.append(f"sitemap.xml is not valid XML ({exc})")
            return
        locs = [node.text for node in tree.findall(f".//{{{SITEMAP_NS}}}loc")]
        expected_locs = [f"{registry['base_url']}/publications/"]
        expected_locs.extend(project_url(registry, item) for item in sorted_publications(registry))
        if locs != expected_locs:
            errors.append(f"sitemap locations are {locs}")


def generate(registry: dict) -> None:
    write_text(SITEMAP_PATH, render_sitemap(registry))
    write_text(LLMS_PATH, render_llms(registry))
    write_text(PUBLICATIONS_PATH, render_publications_page(registry))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated files or page metadata drift")
    parser.add_argument("--print-seo", action="store_true", help="print head blocks for the paper pages")
    args = parser.parse_args()
    registry = load_registry()
    if args.print_seo:
        for publication in sorted_publications(registry):
            print(f"\n\n===== {publication['path']} =====\n")
            print(render_seo_block(registry, publication))
        return 0
    if not args.check:
        generate(registry)
    errors: list[str] = []
    if args.check:
        check_generated(registry, errors)
        check_robots(errors)
        check_content_rules(errors)
        for publication in registry["publications"]:
            check_publication(registry, publication, errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.check:
        print("SEO check passed")
    else:
        print("Wrote sitemap.xml, llms.txt, and publications/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
