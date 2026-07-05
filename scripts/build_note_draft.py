#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import shutil
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

PIPELINE_KEYWORDS = ("overview", "pipeline", "framework", "architecture", "workflow", "method")
RESULT_KEYWORDS = ("result", "results", "performance", "benchmark", "comparison", "attack")
SUPPORT_KEYWORDS = ("ablation", "analysis", "case", "failure", "impact")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def load_bundle(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def choose_template(bundle: dict[str, Any], forced: str) -> str:
    if forced in {"general", "security"}:
        return forced
    hint = bundle.get("metadata", {}).get("template_hint", "")
    if hint in {"general", "security"}:
        return hint
    haystack = " ".join(
        [
            bundle.get("metadata", {}).get("title", ""),
            bundle.get("metadata", {}).get("abstract", ""),
        ]
    ).lower()
    for keyword in SECURITY_KEYWORDS:
        if keyword in haystack:
            return "security"
    return "general"


def yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "\n" + "\n".join(f'  - "{item}"' for item in items)


def clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text or "not stated"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "paper"


def summarize_problem(bundle: dict[str, Any]) -> str:
    abstract = bundle.get("metadata", {}).get("abstract", "")
    if abstract:
        return clean_sentence(abstract[:220])
    return "需要根据正文进一步确认论文要解决的具体问题。"


def summarize_method(bundle: dict[str, Any]) -> str:
    sections = bundle.get("sections", [])
    titles = [item["title"] for item in sections if item.get("level") <= 2][:6]
    if titles:
        return "论文主要围绕以下结构展开：" + " / ".join(titles)
    return "需要根据方法部分进一步提炼。"


def summarize_conclusion(bundle: dict[str, Any]) -> str:
    tables = bundle.get("tables", [])
    if tables:
        return "论文提供了定量结果表，说明作者重点通过实验对比支撑核心结论。"
    if bundle.get("figures"):
        return "论文包含方法或结果图，说明作者提供了可视化证据支撑核心结论。"
    return "需要结合实验部分进一步确认结论强度。"


def bullet_list(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def build_contributions(bundle: dict[str, Any]) -> str:
    candidates = []
    if bundle.get("sections"):
        candidates.append("论文结构完整，适合先抓方法与实验主线。")
    if bundle.get("tables"):
        candidates.append("包含结果表，便于快速定位最重要的量化证据。")
    if bundle.get("figures"):
        candidates.append("包含图示材料，有助于快速理解方法流程或实验现象。")
    return bullet_list(candidates[:3], "需要根据正文进一步归纳作者明确宣称的贡献。")


def build_section_outline(bundle: dict[str, Any]) -> str:
    items = [f"L{section['level']} {section['title']}" for section in bundle.get("sections", [])[:10]]
    return bullet_list(items, "需要补充章节结构。")


def resolve_visual_path(bundle: dict[str, Any], raw_path: str) -> Path | None:
    if not raw_path:
        return None
    if re.match(r"^https?://", raw_path, re.I):
        return None
    source_md = bundle.get("source", {}).get("markdown_path", "")
    source_dir = Path(source_md).parent if source_md else Path.cwd()
    candidate = Path(raw_path)
    if candidate.exists():
        return candidate
    joined = source_dir / raw_path
    if joined.exists():
        return joined
    return None


def score_visual(item: dict[str, Any]) -> int:
    caption = clean_sentence(item.get("caption", "")).lower()
    label = item.get("label", "").lower()
    score = 0
    if "figure" in label:
        score += 2
    if "table" in label:
        score += 2
    if any(keyword in caption for keyword in PIPELINE_KEYWORDS):
        score += 8
    if any(keyword in caption for keyword in RESULT_KEYWORDS):
        score += 7
    if any(keyword in caption for keyword in SUPPORT_KEYWORDS):
        score += 4
    if caption == "not stated":
        score -= 3
    return score


def choose_visual_candidates(bundle: dict[str, Any], figure_mode: str) -> list[dict[str, Any]]:
    if figure_mode == "none":
        return []
    candidates = []
    for item in bundle.get("figures", []):
        candidates.append({"kind": "figure", **item, "score": score_visual(item)})
    for item in bundle.get("tables", []):
        candidates.append({"kind": "table", **item, "score": score_visual(item)})
    candidates.sort(key=lambda item: item["score"], reverse=True)

    if figure_mode == "rich":
        pipeline = next(
            (
                item
                for item in candidates
                if any(keyword in clean_sentence(item.get("caption", "")).lower() for keyword in PIPELINE_KEYWORDS)
            ),
            None,
        )
        result = next(
            (
                item
                for item in candidates
                if any(keyword in clean_sentence(item.get("caption", "")).lower() for keyword in RESULT_KEYWORDS)
            ),
            None,
        )
        support = next(
            (
                item
                for item in candidates
                if any(keyword in clean_sentence(item.get("caption", "")).lower() for keyword in SUPPORT_KEYWORDS)
            ),
            None,
        )
        rich_selected = []
        for item in (pipeline, result, support):
            if item is not None and item not in rich_selected:
                rich_selected.append(item)
        for item in candidates:
            if item not in rich_selected:
                rich_selected.append(item)
            if len(rich_selected) >= 3:
                break
        candidates = rich_selected

    limit = 3 if figure_mode == "rich" else 2
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        raw_path = item.get("path", "")
        key = raw_path or f"{item.get('kind')}::{item.get('caption', '')}"
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def localize_visuals(
    bundle: dict[str, Any],
    output_path: Path,
    vault_root: Path | None,
    attachments_dir: str,
    figure_mode: str,
) -> list[dict[str, str]]:
    if vault_root is None or figure_mode == "none":
        return []

    paper_slug = slugify(bundle.get("metadata", {}).get("title", output_path.stem))
    target_dir = vault_root / attachments_dir / paper_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    localized: list[dict[str, str]] = []
    for index, item in enumerate(choose_visual_candidates(bundle, figure_mode), start=1):
        resolved = resolve_visual_path(bundle, item.get("path", ""))
        if resolved is None:
            continue
        suffix = resolved.suffix or ".png"
        caption_slug = slugify(clean_sentence(item.get("caption", "")))[:40] or f"{item.get('kind', 'visual')}-{index}"
        filename = f"{item.get('kind', 'visual')}-{index}-{caption_slug}{suffix}"
        destination = target_dir / filename
        shutil.copy2(resolved, destination)
        embed_path = f"{attachments_dir}/{paper_slug}/{filename}".replace("\\", "/")
        localized.append(
            {
                "label": item.get("label", item.get("kind", "visual").title()),
                "caption": clean_sentence(item.get("caption", "caption not stated")),
                "embed": f"![[{embed_path}]]",
                "kind": item.get("kind", "visual"),
            }
        )
    return localized


def build_visual_notes(bundle: dict[str, Any], localized_visuals: list[dict[str, str]]) -> str:
    if localized_visuals:
        notes = []
        for item in localized_visuals:
            notes.append(f"- {item['label']}: {item['caption']}")
            notes.append(item["embed"])
        return "\n".join(notes)

    notes = []
    for figure in bundle.get("figures", [])[:3]:
        notes.append(f"- {figure.get('label', 'Figure')}: {clean_sentence(figure.get('caption', 'caption not stated'))}")
    for table in bundle.get("tables", [])[:3]:
        notes.append(f"- {table.get('label', 'Table')}: {clean_sentence(table.get('caption', 'caption not stated'))}")
    return "\n".join(notes) if notes else "- 暂未抽取到高价值图表，或仍需后续本地化。"


def pick_primary_url(urls: list[str], code_url: str) -> str:
    for url in urls:
        lower = url.lower()
        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        if url == code_url:
            continue
        return url
    return code_url


def detect_security_target(bundle: dict[str, Any]) -> str:
    title = bundle.get("metadata", {}).get("title", "").lower()
    if "agent" in title:
        return "agent / tool-use system"
    if "prompt" in title:
        return "prompt-level vulnerability"
    if "backdoor" in title:
        return "backdoor behavior"
    return "LLM system or safety setting"


def render_template(template: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def build_replacements(
    bundle: dict[str, Any],
    output_path: Path,
    template_kind: str,
    localized_visuals: list[dict[str, str]],
) -> dict[str, str]:
    metadata = bundle.get("metadata", {})
    urls = metadata.get("urls", [])
    code_url = metadata.get("code_url", "")
    first_url = pick_primary_url(urls, code_url)
    title = metadata.get("title", output_path.stem)
    authors = metadata.get("authors", [])

    replacements = {
        "paper_title": title,
        "authors_yaml": yaml_list(authors),
        "year": metadata.get("year", ""),
        "venue": metadata.get("venue", ""),
        "url": first_url,
        "pdf": bundle.get("source", {}).get("markdown_path", ""),
        "code": code_url,
        "problem": summarize_problem(bundle),
        "method": summarize_method(bundle),
        "conclusion": summarize_conclusion(bundle),
        "contributions": build_contributions(bundle),
        "worth_reading": "需要结合贡献与实验强度进一步判断。",
        "worth_reproducing_judgment": "中，需看代码、数据和实验细节是否充分。",
        "problem_definition": bullet_list(
            [
                "输入输出与任务边界需要结合正文进一步确认。",
                "可以先从摘要和章节标题抓住问题设定。",
            ],
            "需要补充问题定义。",
        ),
        "method_intuition": bullet_list(
            [
                summarize_method(bundle),
                "建议优先查看方法总览图和方法章节标题。",
            ],
            "需要补充方法直觉。",
        ),
        "method_structure": build_section_outline(bundle),
        "experiment_setup": bullet_list(
            [
                "优先从实验章节和表格 caption 提取 benchmark、baseline、指标。",
                "如果后续需要复现，应重点补齐模型、数据、超参数。",
            ],
            "需要补充实验设置。",
        ),
        "key_results": bullet_list(
            [
                summarize_conclusion(bundle),
                "建议对照表格 caption 再确认最强结果是否真的对应主 claim。",
            ],
            "需要补充关键结果。",
        ),
        "evidence_judgment": bullet_list(
            [
                "当前为基于 MinerU 结构抽取的初步判断。",
                "最终证据强度仍应结合正文细读和 baseline 公平性检查。",
            ],
            "需要补充证据判断。",
        ),
        "visual_notes": build_visual_notes(bundle, localized_visuals),
        "strengths": bullet_list(
            [
                "MinerU 保留了章节、表格和部分图像线索，便于快速建立论文全貌。",
                "当前结构适合继续做中文精修与研究价值判断。",
            ],
            "需要补充优点。",
        ),
        "limitations": bullet_list(
            [
                "当前草稿仍偏结构化抽取，不等于高质量研究总结。",
                "venue、year、代码链接等字段可能仍需人工核验。",
            ],
            "需要补充局限。",
        ),
        "reproduction_clues": bullet_list(
            [
                "优先检查是否公开代码、数据、prompt、训练或推理设置。",
                "重点看实验章节和附录中的实现细节。",
            ],
            "需要补充复现线索。",
        ),
        "transferable_insights": bullet_list(
            [
                "先识别论文的问题设定、实验套路和可迁移评测方式。",
                "如果这篇论文价值高，建议再做一轮精读版笔记。",
            ],
            "需要补充可迁移收获。",
        ),
        "research_ideas": bullet_list(
            [
                "思考作者的关键假设在哪些 setting 下会失效。",
                "思考是否能把该方法迁移到你的 LLM 安全研究问题中。",
            ],
            "需要补充研究灵感。",
        ),
        "security_target": detect_security_target(bundle),
        "threat_model": "需要根据正文进一步确认攻击者能力、目标和访问方式。",
        "threat_model_detail": bullet_list(
            [
                "攻击者能力：needs verification",
                "攻击目标：needs verification",
                "黑盒/白盒/灰盒：needs verification",
            ],
            "需要补充威胁模型。",
        ),
    }

    if template_kind != "security":
        replacements.pop("security_target", None)
        replacements.pop("threat_model", None)
        replacements.pop("threat_model_detail", None)

    return replacements


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--template", choices=["auto", "general", "security"], default="auto")
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--attachments-dir", default="attachments")
    parser.add_argument("--figure-mode", choices=["none", "auto", "rich"], default="auto")
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    bundle = load_bundle(args.bundle)
    template_kind = choose_template(bundle, args.template)
    template_name = "llm-security-template.md" if template_kind == "security" else "general-ai-template.md"
    template = read_text(args.skill_dir / "assets" / template_name)
    localized_visuals = localize_visuals(
        bundle,
        args.output,
        args.vault_root,
        args.attachments_dir,
        args.figure_mode,
    )
    replacements = build_replacements(bundle, args.output, template_kind, localized_visuals)
    note = render_template(template, replacements)
    args.output.write_text(note, encoding="utf-8")


if __name__ == "__main__":
    main()
