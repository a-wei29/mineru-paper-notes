# Implementation Roadmap

## V1

Goal:

- consume existing MinerU `md + json`
- generate a Chinese Obsidian draft

Required pieces:

1. `normalize_mineru.py`
2. `build_note_draft.py`
3. `pipeline.py`
4. two note templates

## V2

Goal:

- accept direct PDF input
- invoke `mineru-open-api` automatically

Add:

- PDF mode in `pipeline.py`
- temp output management
- MinerU mode selection

## V3

Goal:

- localize figures automatically

Add:

- download or copy selected visuals
- readable renaming
- Obsidian attachment embeds

## V4

Goal:

- batch processing

Add:

- folder input
- repeated note generation
- collision-safe note naming
