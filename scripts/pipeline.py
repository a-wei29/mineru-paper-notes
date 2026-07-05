#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

def run_subcommand(script: Path, args: list[str]) -> None:
    subprocess.run(
        ["python", str(script), *args],
        check=True,
    )


def find_output_files(workdir: Path) -> tuple[Path, Path | None]:
    markdown_files = sorted(
        workdir.rglob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    json_files = sorted(
        [path for path in workdir.rglob("*.json") if path.name != "paper_bundle.json"],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not markdown_files:
        raise RuntimeError("MinerU did not produce a markdown file.")
    return markdown_files[0], json_files[0] if json_files else None


def has_mineru_token(mineru: str) -> bool:
    if os.environ.get("MINERU_TOKEN"):
        return True
    result = subprocess.run(
        [mineru, "auth", "--show"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}".lower()
    return "no token configured" not in output


def run_mineru(
    pdf_path: Path,
    workdir: Path,
    mineru_mode: str,
    language: str,
    ocr: bool,
) -> tuple[Path, Path | None, str]:
    mineru = shutil.which("mineru-open-api")
    if not mineru:
        raise RuntimeError("mineru-open-api is not available in PATH.")

    selected_mode = mineru_mode
    if mineru_mode == "auto":
        selected_mode = "extract" if has_mineru_token(mineru) else "flash"

    if selected_mode == "extract":
        command = [
            mineru,
            "extract",
            str(pdf_path),
            "-f",
            "md,json",
            "-o",
            str(workdir),
            "--language",
            language,
        ]
        if ocr:
            command.append("--ocr")
        subprocess.run(command, check=True)
        markdown_path, json_path = find_output_files(workdir)
        return markdown_path, json_path, "extract"

    command = [
        mineru,
        "flash-extract",
        str(pdf_path),
        "-o",
        str(workdir),
        "--language",
        language,
        "--table",
        "--formula",
    ]
    if ocr:
        command.append("--ocr")
    subprocess.run(command, check=True)
    markdown_path, _ = find_output_files(workdir)
    return markdown_path, None, "flash-extract"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--parsed-markdown", type=Path)
    parser.add_argument("--parsed-json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--template", choices=["auto", "general", "security"], default="auto")
    parser.add_argument("--mineru-mode", choices=["auto", "extract", "flash"], default="auto")
    parser.add_argument("--language", default="en")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--attachments-dir", default="attachments")
    parser.add_argument("--figure-mode", choices=["none", "auto", "rich"], default="auto")
    parser.add_argument("--keep-bundle", action="store_true")
    parser.add_argument("--keep-parsed", action="store_true")
    args = parser.parse_args()

    if not args.pdf and not args.parsed_markdown:
        raise SystemExit("Provide either --pdf or --parsed-markdown.")

    skill_dir = Path(__file__).resolve().parents[1]
    normalize_script = skill_dir / "scripts" / "normalize_mineru.py"
    draft_script = skill_dir / "scripts" / "build_note_draft.py"

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_root = Path(tmpdir)
        markdown_path = args.parsed_markdown
        json_path = args.parsed_json
        mineru_used = ""

        if args.pdf:
            markdown_path, json_path, mineru_used = run_mineru(
                args.pdf,
                temp_root,
                args.mineru_mode,
                args.language,
                args.ocr,
            )

        bundle_path = temp_root / "paper_bundle.json"
        run_subcommand(
            normalize_script,
            [
                "--markdown",
                str(markdown_path),
                "--output",
                str(bundle_path),
                *(["--json", str(json_path)] if json_path else []),
            ],
        )

        run_subcommand(
            draft_script,
            [
                "--bundle",
                str(bundle_path),
                "--output",
                str(args.output),
                "--template",
                args.template,
                "--attachments-dir",
                args.attachments_dir,
                "--figure-mode",
                args.figure_mode,
                *(["--vault-root", str(args.vault_root)] if args.vault_root else []),
            ],
        )

        if args.keep_parsed and args.pdf:
            if markdown_path is not None:
                args.output.with_suffix(".mineru.md").write_text(
                    markdown_path.read_text(encoding="utf-8", errors="ignore"),
                    encoding="utf-8",
                )
            if json_path is not None and json_path.exists():
                args.output.with_suffix(".mineru.json").write_text(
                    json_path.read_text(encoding="utf-8", errors="ignore"),
                    encoding="utf-8",
                )

        if args.keep_bundle:
            saved_bundle = args.output.with_suffix(".bundle.json")
            saved_bundle.write_text(bundle_path.read_text(encoding="utf-8"), encoding="utf-8")

        if mineru_used:
            print(f"MinerU mode used: {mineru_used}")


if __name__ == "__main__":
    main()
