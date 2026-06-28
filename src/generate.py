#!/usr/bin/env python3
"""
Generate static HTML files from Jinja2 templates + normalized data JSONs.
Outputs to dist/. Only writes files if content changed (for deploy optimization).
"""

import shutil
import tempfile
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
DIST_DIR = ROOT / "dist"
GROUPS_DIR = DIST_DIR / "grupos"

JINJA_ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    keep_trailing_newline=True,
)

# Configure for PT-BR locale
JINJA_ENV.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)


def load_data() -> dict:
    data = {}
    for filename in ["teams.json", "matches.json", "standings.json", "scorers.json", "bracket.json"]:
        with open(DATA_DIR / filename) as f:
            data[filename.replace('.json', '')] = json.load(f)
    return data


def build_meta() -> dict:
    return {
        "generator": "copa2026-static",
        "build_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "1.0",
    }


def render_index(data: dict, meta: dict) -> None:
    template = JINJA_ENV.get_template("index.html")
    html = template.render(data=data, meta=meta)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")


def render_grupos(data: dict, meta: dict) -> None:
    template = JINJA_ENV.get_template("grupos.html")
    html = template.render(data=data, meta=meta)
    GROUPS_DIR.mkdir(parents=True, exist_ok=True)
    (GROUPS_DIR / "index.html").write_text(html, encoding="utf-8")


def render_grupo_detail(data: dict, meta, group_letter: str) -> None:
    template = JINJA_ENV.get_template("grupo_detail.html")

    group_matches = [m for m in data['matches'] if m.get('group') == group_letter]
    group_standings = [s for s in data['standings'] if s.get('group') == group_letter]

    html = template.render(data=data, meta=meta, group_letter=group_letter)
    group_file = GROUPS_DIR / f"grupo_{group_letter}.html"
    group_file.write_text(html, encoding="utf-8")


def render_mata_mata(data: dict, meta: dict) -> None:
    template = JINJA_ENV.get_template("mata-mata.html")
    html = template.render(data=data, meta=meta)
    (DIST_DIR / "mata-mata.html").write_text(html, encoding="utf-8")


def render_artilheiros(data: dict, meta: dict) -> None:
    template = JINJA_ENV.get_template("artilheiros.html")
    html = template.render(data=data, meta=meta)
    (DIST_DIR / "artilheiros.html").write_text(html, encoding="utf-8")


def render_jogos(data: dict, meta: dict) -> None:
    template = JINJA_ENV.get_template("jogos.html")
    html = template.render(data=data, meta=meta)
    (DIST_DIR / "jogos.html").write_text(html, encoding="utf-8")


def copy_meta_json(data: dict, meta: dict) -> None:
    with open(DIST_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)


def copy_assets() -> None:
    """Copy CSS and JS source files to dist/assets/."""
    assets_src = ROOT / "assets"
    assets_dst = DIST_DIR / "assets"
    assets_dst.mkdir(parents=True, exist_ok=True)
    
    for src_file in assets_src.iterdir():
        if src_file.is_file():
            dst = assets_dst / src_file.name
            if not dst.exists():
                shutil.copy2(src_file, dst)
            else:
                src_mtime = src_file.stat().st_mtime
                dst_mtime = dst.stat().st_mtime
                if src_mtime > dst_mtime:
                    shutil.copy2(src_file, dst)


def main() -> int:
    data = load_data()
    meta = build_meta()

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    copy_meta_json(data, meta)

    render_index(data, meta)
    render_grupos(data, meta)

    for letter in "ABCDEFGHIJKL":
        render_grupo_detail(data, meta, letter)

    render_mata_mata(data, meta)
    render_artilheiros(data, meta)
    render_jogos(data, meta)

    copy_assets()

    file_count = len([f for f in DIST_DIR.rglob("*") if f.is_file()])
    print(f"Generated {file_count} files")
    print(f"Mata-mata: {len(data.get('bracket', []))} matches")
    print("Done.")
    return 0


if __name__ == "__main__":
    exit(main())