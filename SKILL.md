---
name: mineru-paper-notes
description: Generate Chinese Obsidian paper notes from PDF papers through a MinerU-first workflow. Use when Codex needs to parse an AI/LLM paper from PDF, consume MinerU markdown plus json outputs, extract figures/tables selectively, choose between a general AI template and an LLM security template, and produce a near-final Chinese reading note for fast understanding, replication clues, and research ideas.
---

# MinerU Paper Notes

Build Obsidian-ready Chinese paper notes with a MinerU-first pipeline.

Default goal:

- input is a PDF or a MinerU parsed result
- output is one Chinese markdown note
- keep only high-value visuals
- preserve enough structure for later reproduction

## Workflow

1. Inspect whether the input is a PDF, a MinerU markdown file, or a `md + json` pair.
2. If the input is a PDF and `mineru-open-api` is available, run MinerU first.
3. Normalize MinerU output into one stable intermediate bundle.
4. Choose the note template.
5. Generate a deterministic Chinese draft.
6. Refine the draft into a polished final note unless the user explicitly asks for a draft only.

## Input Modes

Supported inputs:

- a single PDF
- a MinerU markdown file
- a MinerU `markdown + json` pair

Read [references/input-output-contract.md](references/input-output-contract.md) before implementation work.

## Scripts

### 1. Normalize MinerU output

Use:

```powershell
python scripts/normalize_mineru.py --markdown "C:\path\paper.md" --json "C:\path\paper.json" --output "D:\path\paper_bundle.json"
```

This script:

- extracts title, authors, abstract, urls, section headings
- collects figure and table candidates
- builds a stable `paper_bundle.json`

### 2. Generate a draft note

Use:

```powershell
python scripts/build_note_draft.py --bundle "D:\path\paper_bundle.json" --output "D:\path\note.md"
```

This script:

- chooses a template with simple heuristics unless overridden
- fills frontmatter and high-confidence sections
- produces a Chinese draft note

### 3. Run the end-to-end pipeline

Use:

```powershell
python scripts/pipeline.py --parsed-markdown "C:\path\paper.md" --parsed-json "C:\path\paper.json" --output "D:\path\note.md"
```

Or, when MinerU CLI is available:

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\note.md"
```

Useful options:

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\note.md" --mineru-mode auto --keep-bundle --keep-parsed
```

Mode rules:

- `auto`: use `extract` when a MinerU token is configured, otherwise fall back to `flash-extract`
- `extract`: force `extract` and expect `md + json`
- `flash`: force `flash-extract` and accept markdown-only output

## Template Choice

Use one of:

- [assets/general-ai-template.md](assets/general-ai-template.md)
- [assets/llm-security-template.md](assets/llm-security-template.md)

Default rule:

- choose security for LLM safety, jailbreak, prompt injection, leakage, backdoor, poisoning, privacy, or agent security papers
- otherwise choose the general template

## Figure Policy

Default figure policy:

- keep at most 1 to 3 visuals
- prioritize method overview, strongest result table, and one supporting figure
- prefer local Obsidian attachments when available
- if only remote MinerU image URLs are available, keep them as evidence in the bundle and mention that localization is still needed
- if the run used `flash-extract`, expect weaker figure support because MinerU only returns markdown placeholders in that mode

## Quality Bar

The final note should help the user:

- understand the paper in 5 to 10 minutes
- decide whether the paper deserves deeper reading
- quickly judge reproduction value
- extract transferable ideas for later research

Do not:

- paste large English blocks into the final note
- hallucinate venue, code link, or metrics
- dump every figure into the note

## References

- [references/input-output-contract.md](references/input-output-contract.md)
- [references/implementation-roadmap.md](references/implementation-roadmap.md)
