# MinerU Paper Notes

[中文](#中文说明) | [English](#english)

---

## 中文说明

### 1. 这是什么

`mineru-paper-notes` 是一个面向 Codex 的 skill，用来把 AI 论文的 PDF 或 MinerU 解析结果转换成适合 Obsidian 使用的中文论文笔记。

它的目标不是只做“文本抽取”，而是尽量直接产出一份接近最终可读版的笔记，帮助你快速完成这几件事：

- 在 5 到 10 分钟内抓住论文的核心问题、方法和结论
- 快速判断这篇论文值不值得精读
- 为方法复现整理出可操作的线索
- 沉淀可迁移到后续研究中的灵感

这个 skill 当前优先适配：

- 一般 AI 论文
- LLM / AI 安全论文
- 需要保留关键图表的论文阅读场景

### 2. 它能做什么

- 接受 `PDF`、`MinerU markdown`、`MinerU markdown + json` 三种输入
- 自动调用 `mineru-open-api` 解析 PDF（如果本地已安装且可用）
- 统一整理 MinerU 输出，生成稳定的中间文件 `paper_bundle.json`
- 在通用 AI 模板和 LLM 安全模板之间自动选择
- 生成中文 Obsidian 笔记
- 选择性保留高价值图表，并在可能时转成 Obsidian 本地附件嵌入

### 3. 工作流

这个 skill 的标准流程如下：

1. 判断输入是 `PDF`、`md`，还是 `md + json`
2. 如果输入是 PDF，就先调用 MinerU
3. 把 MinerU 输出规范化成统一的 `bundle`
4. 自动选择模板
5. 生成中文草稿
6. 在需要时继续精修成更接近最终版的论文笔记

### 4. 目录结构

```text
mineru-paper-notes/
├── SKILL.md
├── README.md
├── assets/
│   ├── general-ai-template.md
│   └── llm-security-template.md
├── references/
│   ├── implementation-roadmap.md
│   └── input-output-contract.md
└── scripts/
    ├── normalize_mineru.py
    ├── build_note_draft.py
    └── pipeline.py
```

### 5. 输入模式

支持三种输入：

1. 单个 PDF 文件
2. 单个 MinerU 生成的 markdown 文件
3. 一组 MinerU 生成的 `markdown + json`

推荐优先级：

- 如果你只有论文 PDF：直接走 PDF 模式
- 如果你已经用 MinerU 跑过：直接用 `md + json`
- 如果只有 markdown：也能生成，但结构化信息和图表支持通常会弱一些

### 6. 输出内容

默认会产出一份 Obsidian 可直接使用的 Markdown 笔记，通常包含：

- YAML frontmatter
- 中文论文标题和结构化元信息
- 一句话定位
- 问题定义 / 威胁模型 / 方法结构
- 关键实验与证据
- 是否值得复现的判断
- 可迁移研究灵感
- 关键图表嵌入（如果可用）

在保留中间产物时，还可能额外生成：

- `*.mineru.md`
- `*.mineru.json`
- `*.bundle.json`

### 7. 依赖要求

建议环境：

- Python 3.8+
- 已安装 `mineru-open-api`
- 本地可以直接调用 `mineru-open-api` 或 `mineru-open-api.exe`

如果要让 PDF 模式正常工作，至少需要满足：

```powershell
mineru-open-api version
```

能正常返回版本号。

### 8. 快速开始

#### 8.1 直接从 PDF 生成笔记

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\paper-note.md"
```

#### 8.2 从 MinerU 的 markdown + json 生成笔记

```powershell
python scripts/pipeline.py --parsed-markdown "C:\path\paper.md" --parsed-json "C:\path\paper.json" --output "D:\path\paper-note.md"
```

#### 8.3 只做标准化

```powershell
python scripts/normalize_mineru.py --markdown "C:\path\paper.md" --json "C:\path\paper.json" --output "D:\path\paper_bundle.json"
```

#### 8.4 从 bundle 生成草稿

```powershell
python scripts/build_note_draft.py --bundle "D:\path\paper_bundle.json" --output "D:\path\paper-note.md"
```

### 9. `pipeline.py` 常用参数

```text
--pdf PDF
--parsed-markdown PARSED_MARKDOWN
--parsed-json PARSED_JSON
--output OUTPUT
--template {auto,general,security}
--mineru-mode {auto,extract,flash}
--language LANGUAGE
--ocr
--vault-root VAULT_ROOT
--attachments-dir ATTACHMENTS_DIR
--figure-mode {none,auto,rich}
--keep-bundle
--keep-parsed
```

重点说明：

- `--template`
  - `auto`：自动判断模板
  - `general`：强制使用通用 AI 模板
  - `security`：强制使用安全方向模板

- `--mineru-mode`
  - `auto`：优先 `extract`，不满足条件时退回 `flash`
  - `extract`：尽量获取 `md + json`
  - `flash`：更轻量，但图表与结构信息更弱

- `--figure-mode`
  - `none`：不保留图表
  - `auto`：自动保留少量高价值图表
  - `rich`：更积极地保留和本地化图表

- `--keep-bundle`
  - 保留中间 `bundle.json`，便于调试与二次加工

- `--keep-parsed`
  - 保留 MinerU 的原始解析结果

### 10. 模板选择逻辑

当前内置两个模板：

- `assets/general-ai-template.md`
- `assets/llm-security-template.md`

自动选择规则大致是：

- 如果论文主题明显涉及 `LLM safety`、`jailbreak`、`prompt injection`、`data leakage`、`backdoor`、`poisoning`、`privacy`、`agent security` 等，优先走安全模板
- 否则走通用 AI 模板

如果自动判断不合适，可以手动指定：

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\note.md" --template security
```

### 11. 图表策略

这个 skill 默认不会把所有图都塞进笔记，而是优先保留最有价值的 1 到 3 个视觉材料，例如：

- 方法总览图
- 最关键的结果表
- 一个补充理解的重要图

当图像能被本地化时，会尽量生成 Obsidian 可直接嵌入的附件路径。

如果 MinerU 只返回远程链接或弱结构占位符：

- `bundle` 中仍会保留相关信息
- 但最终笔记会明确说明图表本地化可能还未完成

### 12. 在 Codex 里怎么用

如果这个 skill 已经放在 Codex 的 skill 目录中，可以直接这样说：

```text
使用 $mineru-paper-notes 分析这篇论文：D:\path\paper.pdf
```

或者：

```text
用 $mineru-paper-notes 把这个 MinerU 输出整理成 Obsidian 中文笔记：
C:\path\paper.md
C:\path\paper.json
输出到 D:\path\note.md
```

也可以在请求里明确你的偏好，例如：

- 输出中文最终版，不要英文大段摘抄
- 保留关键图表
- 偏复现导向
- 用安全方向模板

### 13. 适合的使用场景

- 你想快速过一篇 AI / LLM 论文
- 你已经有 MinerU 输出，想自动填进论文笔记模板
- 你希望沉淀可读性更强的中文 Obsidian 笔记
- 你需要保留少量关键图表辅助理解
- 你后续可能要做论文复现或研究灵感抽取

### 14. 已知限制

- 如果只有 markdown、没有 json，结构化信息抽取通常会更弱
- `flash` 模式比 `extract` 模式更容易丢失图表和版面信息
- 作者、年份、venue、代码链接等元数据仍可能需要人工核验
- 这是“高质量初稿/近最终版”生成器，不等于完全无须人工判断
- 对非 AI 论文、数学符号极多的论文、版式异常复杂的 PDF，效果可能下降

### 15. 建议的最佳实践

- 高价值论文优先使用 `extract` 模式，而不是 `flash`
- 对重要论文启用 `--keep-bundle` 与 `--keep-parsed`
- 先产出快速理解版，再在此基础上做复现版精读笔记
- 对安全方向论文，手动确认威胁模型、攻击能力、实验公平性这几项
- 对图表很多的论文，优先保留“方法图 + 主结果表 + 一张补充图”

### 16. 面向开发者的说明

这个 skill 面向的是“让 Codex 执行论文笔记生成流程”，因此：

- `SKILL.md` 是给 Codex 读的机器导向说明
- `README.md` 是给人读的使用说明
- `references/` 中存放流程约束与实现路线
- `scripts/` 中存放可复用的确定性脚本

如果你后续想扩展它，常见方向包括：

- 批量处理多个 PDF
- 更强的作者 / venue / year 元数据抽取
- 更可靠的图表定位与附件命名
- 复现导向模板
- 面向 LLM 安全、Agent 安全、多模态安全的细分模板

---

## English

### 1. What This Is

`mineru-paper-notes` is a Codex skill for turning AI paper PDFs or MinerU parsing outputs into Chinese Obsidian-ready reading notes.

It is designed to do more than raw extraction. The goal is to produce a near-final reading note that helps you:

- understand a paper's main idea quickly
- decide whether it is worth a deeper read
- capture reproduction clues
- preserve transferable research insights

It is currently best suited for:

- general AI papers
- LLM / AI security papers
- paper reading workflows where a few key figures or tables should be preserved

### 2. What It Does

- Accepts `PDF`, `MinerU markdown`, or `MinerU markdown + json`
- Calls `mineru-open-api` automatically when PDF input is used and MinerU is available
- Normalizes MinerU output into a stable intermediate `paper_bundle.json`
- Chooses between a general AI template and an LLM security template
- Generates a Chinese Obsidian note
- Selectively keeps high-value visuals and localizes them as Obsidian attachments when possible

### 3. Workflow

The standard workflow is:

1. Detect whether the input is a `PDF`, `md`, or `md + json`
2. Run MinerU first if the input is a PDF
3. Normalize MinerU output into a stable bundle
4. Select the note template
5. Generate a Chinese draft
6. Refine it into a more polished final note when needed

### 4. Directory Layout

```text
mineru-paper-notes/
├── SKILL.md
├── README.md
├── assets/
│   ├── general-ai-template.md
│   └── llm-security-template.md
├── references/
│   ├── implementation-roadmap.md
│   └── input-output-contract.md
└── scripts/
    ├── normalize_mineru.py
    ├── build_note_draft.py
    └── pipeline.py
```

### 5. Input Modes

Supported inputs:

1. A single PDF
2. A single MinerU markdown file
3. A MinerU `markdown + json` pair

Recommended usage:

- If you only have the paper PDF, use PDF mode
- If MinerU output already exists, use `md + json`
- If only markdown is available, the skill can still work, but structure and figure support will usually be weaker

### 6. Output

The default output is one Obsidian-ready Markdown note, usually including:

- YAML frontmatter
- Chinese title and structured metadata
- one-sentence positioning
- problem definition / threat model / method structure
- key experiments and evidence
- reproduction value judgment
- transferable research ideas
- selected figure or table embeds when available

If intermediate artifacts are preserved, the pipeline may also generate:

- `*.mineru.md`
- `*.mineru.json`
- `*.bundle.json`

### 7. Requirements

Recommended environment:

- Python 3.8+
- `mineru-open-api` installed
- MinerU callable from the command line

For PDF mode, this command should work:

```powershell
mineru-open-api version
```

### 8. Quick Start

#### 8.1 Generate a note directly from a PDF

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\paper-note.md"
```

#### 8.2 Generate a note from MinerU markdown + json

```powershell
python scripts/pipeline.py --parsed-markdown "C:\path\paper.md" --parsed-json "C:\path\paper.json" --output "D:\path\paper-note.md"
```

#### 8.3 Normalize MinerU output only

```powershell
python scripts/normalize_mineru.py --markdown "C:\path\paper.md" --json "C:\path\paper.json" --output "D:\path\paper_bundle.json"
```

#### 8.4 Build a draft note from a bundle

```powershell
python scripts/build_note_draft.py --bundle "D:\path\paper_bundle.json" --output "D:\path\paper-note.md"
```

### 9. Common `pipeline.py` Options

```text
--pdf PDF
--parsed-markdown PARSED_MARKDOWN
--parsed-json PARSED_JSON
--output OUTPUT
--template {auto,general,security}
--mineru-mode {auto,extract,flash}
--language LANGUAGE
--ocr
--vault-root VAULT_ROOT
--attachments-dir ATTACHMENTS_DIR
--figure-mode {none,auto,rich}
--keep-bundle
--keep-parsed
```

Highlights:

- `--template`
  - `auto`: choose automatically
  - `general`: force the general AI template
  - `security`: force the security template

- `--mineru-mode`
  - `auto`: prefer `extract`, fall back to `flash`
  - `extract`: aim for `md + json`
  - `flash`: lighter but weaker for figures and structure

- `--figure-mode`
  - `none`: keep no visuals
  - `auto`: keep a small number of high-value visuals
  - `rich`: preserve and localize visuals more aggressively

- `--keep-bundle`
  - preserve the intermediate `bundle.json`

- `--keep-parsed`
  - preserve raw MinerU parsing output

### 10. Template Selection

The skill ships with two templates:

- `assets/general-ai-template.md`
- `assets/llm-security-template.md`

The rough auto-selection rule is:

- choose the security template for topics such as `LLM safety`, `jailbreak`, `prompt injection`, `data leakage`, `backdoor`, `poisoning`, `privacy`, or `agent security`
- otherwise choose the general AI template

You can always override it manually:

```powershell
python scripts/pipeline.py --pdf "C:\path\paper.pdf" --output "D:\path\note.md" --template security
```

### 11. Figure Policy

The skill does not try to dump every image into the final note. By default, it prioritizes one to three high-value visuals such as:

- a method overview figure
- the strongest result table
- one supporting figure for intuition

When localization is possible, it will generate Obsidian-friendly local attachment embeds.

If MinerU only returns remote URLs or weak placeholders:

- the bundle still keeps the evidence
- the note should make it clear that localization may still be incomplete

### 12. How to Use It in Codex

If the skill is installed in Codex's skill directory, you can invoke it like this:

```text
Use $mineru-paper-notes to analyze this paper: D:\path\paper.pdf
```

Or:

```text
Use $mineru-paper-notes to convert this MinerU output into an Obsidian Chinese note:
C:\path\paper.md
C:\path\paper.json
Output to D:\path\note.md
```

You can also specify preferences in the request, such as:

- output a polished Chinese final note
- avoid large English excerpts
- keep key figures
- optimize for reproduction clues
- force the security template

### 13. Good Use Cases

- You want to triage an AI / LLM paper quickly
- You already have MinerU output and want it mapped into a note template
- You want readable Chinese Obsidian notes instead of raw extraction
- You need a few high-value figures preserved
- You may later reproduce the method or mine research ideas from the paper

### 14. Known Limitations

- Markdown-only input is weaker than `md + json`
- `flash` mode is weaker than `extract` mode for structure and visuals
- metadata such as authors, year, venue, and code links may still need manual verification
- this is a high-quality draft / near-final note generator, not a substitute for human judgment
- performance can degrade on non-AI papers, formula-heavy papers, or unusually complex layouts

### 15. Recommended Best Practices

- Prefer `extract` over `flash` for high-value papers
- Use `--keep-bundle` and `--keep-parsed` for important papers
- First generate a fast-understanding note, then refine into a reproduction-oriented note if needed
- For security papers, manually verify the threat model, attacker capability, and experiment fairness
- For papers with many visuals, prioritize "method figure + main result table + one supporting figure"

### 16. Notes for Developers

This skill is built to let Codex execute a paper-note generation workflow, so:

- `SKILL.md` is the machine-facing instruction file
- `README.md` is the human-facing usage guide
- `references/` stores workflow constraints and implementation notes
- `scripts/` stores reusable deterministic utilities

Common future extensions include:

- batch processing for multiple PDFs
- stronger metadata extraction for authors / venue / year
- more reliable figure localization and naming
- reproduction-oriented note templates
- specialized templates for LLM security, agent security, or multimodal safety
