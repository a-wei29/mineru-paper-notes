# Input / Output Contract

## Accepted Inputs

The new workflow should treat MinerU as the primary parser.

Accepted forms:

1. `paper.pdf`
2. `paper.md`
3. `paper.md + paper.json`

## Intermediate Bundle

All downstream logic should depend on a stable intermediate file:

- `paper_bundle.json`

Recommended top-level fields:

```json
{
  "source": {},
  "metadata": {},
  "sections": [],
  "figures": [],
  "tables": [],
  "raw": {}
}
```

### `source`

- original input path
- markdown path
- json path
- parser name

### `metadata`

- title
- authors
- abstract
- year
- venue
- urls
- code_url
- template_hint

### `sections`

Each section should contain:

- `level`
- `title`

### `figures`

Each figure candidate should contain:

- `label`
- `caption`
- `path`
- `source_type`

### `tables`

Each table candidate should contain:

- `label`
- `caption`
- `html`
- `path`
- `source_type`

## Output Note

The final note should be a single markdown file that is directly usable in Obsidian.

Minimum output properties:

- Chinese prose
- YAML frontmatter
- note title
- high-value sections filled
- unknown fields marked as `not stated` or `needs verification`

## Attachment Policy

The skill should prefer:

- local Obsidian attachments when available

When only remote MinerU URLs exist:

- keep the URL in the bundle
- do not pretend localization has already been completed
- mark the note section accordingly
