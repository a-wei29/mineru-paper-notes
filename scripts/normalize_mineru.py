#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SECURITY_KEYWORDS = {
    "jailbreak",
    "prompt injection",
    "prompt leakage",
    "leakage",
    "backdoor",
    "poisoning",
    "alignment",
    "safety",
    "agent security",
    "privacy",
    "defense",
}

INSTITUTION_KEYWORDS = {
    "university",
    "institute",
    "college",
    "laboratory",
    "lab",
    "academy",
    "technology",
    "school",
    "department",
    "science",
    "china",
    "usa",
    "hong kong",
    "pittsburgh",
    "beijing",
    "carnegie mellon",
    "meta ai",
}

INSTITUTION_STARTERS = (
    "Hong",
    "Carnegie",
    "Institute",
    "Chinese",
    "University",
    "College",
    "School",
    "Department",
    "Laboratory",
    "Lab",
    "Academy",
    "Meta",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def load_json(path: Path | None) -> Any:
    if path is None or not path.exists():
        return {}
    return json.loads(read_text(path))


def iter_json_blocks(json_data: Any) -> list[dict[str, Any]]:
    if isinstance(json_data, list):
        return [item for item in json_data if isinstance(item, dict)]
    if isinstance(json_data, dict):
        blocks: list[dict[str, Any]] = []
        for page in json_data.get("pdf_info", []):
            for block in page.get("preproc_blocks", []):
                if isinstance(block, dict):
                    blocks.append(block)
        return blocks
    return []


def clean_text(text: str) -> str:
    text = text.replace("\u00d7", "x")
    text = re.sub(r"<sup>.*?</sup>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("鈥?", "-")
    text = text.replace("鈥檚", "'s")
    text = text.replace("鈭?", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def looks_like_author_name(text: str) -> bool:
    cleaned = sanitize_author_name(text)
    if not cleaned or "@" in cleaned:
        return False
    lower = cleaned.lower()
    if any(marker in lower for marker in ("ccs concepts", "reference format", "new york")):
        return False
    if any(keyword in lower for keyword in INSTITUTION_KEYWORDS):
        return False
    if any(char in cleaned for char in ":[]()"):
        return False
    if re.search(r"\d", cleaned):
        return False
    if len(cleaned) > 80:
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]+", cleaned)
    if len(tokens) < 2 or len(tokens) > 5:
        return False
    capitalized = sum(1 for token in tokens if token[:1].isupper())
    return capitalized >= max(2, len(tokens) - 1)


def sanitize_author_name(text: str) -> str:
    cleaned = clean_text(text)
    cleaned = re.sub(r"[^A-Za-z'\-\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_leading_name(text: str) -> list[str]:
    cleaned = clean_text(text)
    lower = cleaned.lower()
    if "@" in cleaned:
        match = re.match(
            r"^([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,2})\s+(?=(" + "|".join(INSTITUTION_STARTERS) + r")\b)",
            cleaned,
        )
        if match:
            candidate = sanitize_author_name(match.group(1))
            return [candidate] if looks_like_author_name(candidate) else []
    cut_positions = [lower.find(keyword) for keyword in INSTITUTION_KEYWORDS if keyword in lower]
    cut_positions = [position for position in cut_positions if position > 0]
    if not cut_positions:
        return []
    prefix = sanitize_author_name(cleaned[: min(cut_positions)].strip(" ,;-"))
    return [prefix] if looks_like_author_name(prefix) else []


def split_possible_names(text: str) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    leading = extract_leading_name(cleaned)
    if leading:
        return leading
    sanitized = sanitize_author_name(cleaned)
    if looks_like_author_name(sanitized):
        return [sanitized]
    parts = re.split(r"\s{2,}|,\s*", cleaned)
    results = []
    for part in parts:
        part = sanitize_author_name(part)
        if looks_like_author_name(part):
            results.append(part)
    return results


def extract_title(md_text: str, json_data: Any, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", md_text, re.M)
    if match:
        return clean_text(match.group(1))

    for block in iter_json_blocks(json_data):
        if block.get("type") == "title":
            lines = block.get("lines", [])
            for line in lines:
                spans = line.get("spans", [])
                parts = [span.get("content", "") for span in spans]
                title = clean_text("".join(parts))
                if title:
                    return title
        if block.get("type") == "text" and block.get("text_level") == 1:
            title = clean_text(block.get("text", ""))
            if title:
                return title
    return fallback


def extract_authors(md_text: str) -> list[str]:
    lines = [clean_text(line) for line in md_text.splitlines()]
    title_seen = False
    candidates: list[str] = []
    for line in lines:
        if not title_seen and line.startswith("# "):
            title_seen = True
            continue
        if not title_seen:
            continue
        if not line:
            continue
        line_key = line.lower().lstrip("# ").strip()
        if line_key.startswith("abstract"):
            break
        candidates.extend(split_possible_names(line))
        if len(candidates) >= 12:
            break

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped[:20]


def extract_authors_from_json(json_data: Any) -> list[str]:
    candidates: list[str] = []
    seen_title = False
    for block in iter_json_blocks(json_data):
        block_type = block.get("type")
        text = clean_text(block.get("text", ""))
        if not text and "lines" in block:
            text_parts: list[str] = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text_parts.append(span.get("content", ""))
            text = clean_text(" ".join(text_parts))
        if not text:
            continue
        is_title = block_type == "title" or (block_type == "text" and block.get("text_level") == 1)
        if is_title:
            if seen_title:
                if text.lower().startswith("abstract"):
                    return candidates[:20]
            else:
                seen_title = True
            continue
        if not seen_title:
            continue
        if text.lower().startswith("abstract"):
            return candidates[:20]
        for candidate in split_possible_names(text):
            if candidate not in candidates:
                candidates.append(candidate)
        if len(candidates) >= 12:
            return candidates[:20]
    return candidates[:20]


def extract_abstract(md_text: str) -> str:
    match = re.search(
        r"##\s+Abstract\s*(.*?)(?:\n##\s+1|\n#\s+1|\n##\s+[A-Z]|\n#\s+[A-Z])",
        md_text,
        re.S | re.I,
    )
    if not match:
        match = re.search(
            r"\bAbstract\b\s*(.*?)(?:\n## |\n# |\n1\s+Introduction)",
            md_text,
            re.S | re.I,
        )
    if not match:
        return ""
    return clean_text(re.sub(r"\s+", " ", match.group(1)))


def extract_year(md_text: str, json_path: Path | None) -> str:
    early = md_text[:8000]
    patterns = [
        r"ACM Reference Format:.*?\b((?:19|20)\d{2})\b",
        r"arXiv:[^\n]*?\b((?:19|20)\d{2})\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+((?:19|20)\d{2})\b",
        r"\b((?:19|20)\d{2})\s*(?:International Conference|Conference|Workshop|Transactions|Journal)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, early, re.I)
        if match:
            return match.group(1)
    if json_path is not None:
        match = re.search(r"__(20\d{2})", json_path.name)
        if match:
            return match.group(1)
    match = re.search(r"\b(20\d{2})\b", Path(json_path.name if json_path else "").stem)
    if match:
        return match.group(0)
    return ""


def extract_urls(md_text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)>]+", md_text)
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def extract_code_url(md_text: str, urls: list[str]) -> str:
    lines = md_text.splitlines()
    scored: list[tuple[int, str]] = []
    for url in urls:
        lower = url.lower()
        if "github.com" not in lower and "gitlab.com" not in lower:
            continue
        score = 0
        if re.search(r"github\.com/[^/\s]+/[^/\s]+", lower):
            score += 4
        elif re.search(r"github\.com/[^/\s]+/?$", lower):
            score -= 3
        if any(keyword in lower for keyword in ("code", "repo", "source")):
            score += 2
        for line in lines:
            if url in line:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ("open-source", "open source", "code", "github", "repo")):
                    score += 3
                if "reference" in line_lower:
                    score -= 1
                break
        scored.append((score, url))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return ""


def extract_sections(md_text: str) -> list[dict[str, Any]]:
    sections = []
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            sections.append({"level": 3, "title": clean_text(stripped[4:])})
        elif stripped.startswith("## "):
            title = clean_text(stripped[3:])
            sections.append({"level": 2, "title": title})
            if title.lower() == "references":
                break
        elif stripped.startswith("# "):
            sections.append({"level": 1, "title": clean_text(stripped[2:])})
    return sections[:80]


def extract_markdown_visuals(md_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    lines = md_text.splitlines()
    for index, line in enumerate(lines):
        image_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if image_match:
            path = image_match.group(1).strip()
            caption = ""
            if index + 1 < len(lines):
                next_line = clean_text(lines[index + 1])
                if next_line.lower().startswith("figure "):
                    caption = next_line
            figures.append(
                {
                    "label": f"Figure {len(figures) + 1}",
                    "caption": caption,
                    "path": path,
                    "source_type": "markdown",
                }
            )
        if "<table>" in line:
            caption = ""
            if index + 1 < len(lines):
                next_line = clean_text(lines[index + 1])
                if next_line.lower().startswith("table "):
                    caption = next_line
            tables.append(
                {
                    "label": f"Table {len(tables) + 1}",
                    "caption": caption,
                    "html": line.strip(),
                    "path": "",
                    "source_type": "markdown",
                }
            )
    return figures, tables


def extract_json_visuals(json_data: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    blocks = iter_json_blocks(json_data)
    if isinstance(json_data, list):
        for block in blocks:
            block_type = block.get("type")
            if block_type in {"image", "chart"}:
                captions = block.get("image_caption", []) or block.get("chart_caption", [])
                figures.append(
                    {
                        "label": f"Figure {len(figures) + 1}",
                        "caption": clean_text(" ".join(captions)),
                        "path": block.get("img_path", ""),
                        "source_type": "json",
                    }
                )
            if block_type == "table":
                captions = block.get("table_caption", [])
                tables.append(
                    {
                        "label": f"Table {len(tables) + 1}",
                        "caption": clean_text(" ".join(captions)),
                        "html": block.get("table_body", ""),
                        "path": block.get("img_path", ""),
                        "source_type": "json",
                    }
                )
        return figures, tables

    for block in blocks:
        block_type = block.get("type")
        if block_type == "table":
            path = ""
            html = ""
            caption_parts: list[str] = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("type") == "table":
                        path = span.get("image_path", path)
                        html = span.get("html", html)
            caption_parts.extend(block.get("table_caption", []))
            tables.append(
                {
                    "label": f"Table {len(tables) + 1}",
                    "caption": clean_text(" ".join(caption_parts)),
                    "html": html,
                    "path": path,
                    "source_type": "json",
                }
            )
    return figures, tables


def dedupe_visuals(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item.get("path", ""), item.get("caption", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def detect_template_hint(title: str, abstract: str, sections: list[dict[str, Any]]) -> str:
    haystack = " ".join([title, abstract] + [item["title"] for item in sections]).lower()
    for keyword in SECURITY_KEYWORDS:
        if keyword in haystack:
            return "security"
    return "general"


def build_bundle(markdown_path: Path, json_path: Path | None) -> dict[str, Any]:
    md_text = read_text(markdown_path)
    json_data = load_json(json_path)
    title = extract_title(md_text, json_data, markdown_path.stem)
    authors = extract_authors(md_text)
    if not authors:
        authors = extract_authors_from_json(json_data)
    abstract = extract_abstract(md_text)
    urls = extract_urls(md_text)
    sections = extract_sections(md_text)
    md_figures, md_tables = extract_markdown_visuals(md_text)
    json_figures, json_tables = extract_json_visuals(json_data)
    figures = dedupe_visuals(md_figures + json_figures)
    tables = dedupe_visuals(md_tables + json_tables)

    bundle = {
        "source": {
            "parser": "mineru",
            "markdown_path": str(markdown_path),
            "json_path": str(json_path) if json_path else "",
        },
        "metadata": {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": extract_year(md_text, json_path),
            "venue": "",
            "urls": urls,
            "code_url": extract_code_url(md_text, urls),
            "template_hint": detect_template_hint(title, abstract, sections),
        },
        "sections": sections,
        "figures": figures,
        "tables": tables,
        "raw": {
            "markdown_excerpt": clean_text(md_text[:4000]),
        },
    }
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    bundle = build_bundle(args.markdown, args.json)
    args.output.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
