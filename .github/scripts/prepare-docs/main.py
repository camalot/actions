#!/usr/bin/env python3
"""Generate Jekyll documentation pages and _includes symlinks from action.yml files.

Actions without a README.md alongside their action.yml are skipped entirely.
Each directory level between the repo root and an action is rendered as an
index.md via index.md.j2; if that directory has a README.md it is symlinked
and included.  This produces a fully nested Just-the-Docs navigation tree,
e.g. smells/test/python/pytest → Smells > Test > Python > PyTest.
"""

import os
import re
from collections import defaultdict
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "_docs"
INCLUDES_DIR = DOCS_DIR / "_includes"
TEMPLATES_DIR = REPO_ROOT / ".github" / "templates"
WORDS_FILE = Path(__file__).resolve().parent / "words.yaml"

EXCLUDE_DIRS = {".git", ".github", "_docs", "_site", "node_modules"}


# ---------------------------------------------------------------------------
# Display-name lookup
# ---------------------------------------------------------------------------

def load_words() -> dict[str, str]:
    if not WORDS_FILE.exists():
        return {}
    with WORDS_FILE.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("words") or {}


def display_name(slug: str, words: dict[str, str]) -> str:
    """Map a folder slug to a display name via words.yaml.

    Tries the whole slug first; falls back to per-word lookup; words missing
    from the map are title-cased.
    """
    if slug in words:
        return words[slug]
    return " ".join(words.get(p, p.capitalize()) for p in slug.split("-"))


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_actions() -> list[Path]:
    actions = []
    for path in sorted(REPO_ROOT.rglob("action.yml")):
        parts = path.relative_to(REPO_ROOT).parts
        if not any(part in EXCLUDE_DIRS for part in parts):
            actions.append(path)
    return actions


# ---------------------------------------------------------------------------
# Front-matter helpers
# ---------------------------------------------------------------------------

def parse_front_matter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def read_nav_order(path: Path) -> int | None:
    if not path.exists():
        return None
    fm = parse_front_matter(path)
    v = fm.get("nav_order")
    return int(v) if v is not None else None


# ---------------------------------------------------------------------------
# nav_order calculation
# ---------------------------------------------------------------------------

def next_nav_order(existing: dict[str, int]) -> int:
    """Return the next nav_order, inserting before any sentinel at the bottom.

    A sentinel is detected when the last item's gap from its predecessor is
    significantly larger than the typical inter-item gap (>3x and >= 5).
    """
    values = sorted(existing.values())
    if not values:
        return 1
    if len(values) == 1:
        return values[0] + 1

    gaps = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    if len(gaps) >= 2:
        typical = sum(gaps[:-1]) / len(gaps[:-1])
        if gaps[-1] >= 5 and gaps[-1] > typical * 3:
            return values[-2] + 1
    elif gaps[0] >= 20:
        # Only two items; a large gap implies the higher one is a sentinel.
        return values[0] + 1

    return values[-1] + 1


# ---------------------------------------------------------------------------
# Symlink helpers
# ---------------------------------------------------------------------------

def create_symlink(link_path: Path, target: Path) -> None:
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink()
    link_path.symlink_to(target)


def maybe_create_readme_symlink(readme: Path, symlink_name: str) -> str | None:
    """Create a symlink in _includes for readme if it exists. Returns symlink filename or None."""
    if not readme.exists():
        return None
    rel_target = Path(os.path.relpath(readme, INCLUDES_DIR))
    create_symlink(INCLUDES_DIR / symlink_name, rel_target)
    return symlink_name


# ---------------------------------------------------------------------------
# Existing nav_order loading
# ---------------------------------------------------------------------------

def load_existing_nav_orders() -> tuple[
    dict[tuple, int],
    defaultdict[tuple, dict[str, int]],
]:
    """Scan the existing _docs tree and return preserved nav_order values.

    Returns:
        index_nav_orders  – {dir_parts_tuple: nav_order} for every index.md
        page_nav_orders   – {parent_dir_tuple: {slug: nav_order}} for every
                            non-index page
    """
    index_nav_orders: dict[tuple, int] = {}
    page_nav_orders: defaultdict[tuple, dict[str, int]] = defaultdict(dict)

    for index_md in sorted(DOCS_DIR.rglob("index.md")):
        try:
            rel_parts = index_md.parent.relative_to(DOCS_DIR).parts
        except ValueError:
            continue
        v = read_nav_order(index_md)
        if v is not None:
            index_nav_orders[rel_parts] = v

    for md in sorted(DOCS_DIR.rglob("*.md")):
        if md.name == "index.md":
            continue
        try:
            parent_parts = md.parent.relative_to(DOCS_DIR).parts
        except ValueError:
            continue
        v = read_nav_order(md)
        if v is not None:
            page_nav_orders[parent_parts][md.stem] = v

    return index_nav_orders, page_nav_orders


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    INCLUDES_DIR.mkdir(parents=True, exist_ok=True)

    words = load_words()

    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    action_template = jinja_env.get_template("action-doc.md.j2")
    index_template = jinja_env.get_template("index.md.j2")

    generated: list[str] = []
    skipped: list[tuple[str, str]] = []

    # -----------------------------------------------------------------------
    # Step 1 – collect valid actions (README.md must exist beside action.yml)
    # -----------------------------------------------------------------------
    valid_actions: list[Path] = []
    for action_path in find_actions():
        rel = str(action_path.relative_to(REPO_ROOT))
        if not (action_path.parent / "README.md").exists():
            skipped.append((rel, "no README.md"))
            continue
        valid_actions.append(action_path)

    # -----------------------------------------------------------------------
    # Step 2 – collect every unique ancestor directory that needs an index.md
    #
    # For smells/test/python/pytest/action.yml the ancestors are:
    #   ('smells',), ('smells','test'), ('smells','test','python')
    # -----------------------------------------------------------------------
    dirs_needing_index: set[tuple] = set()
    for action_path in valid_actions:
        parts = action_path.relative_to(REPO_ROOT).parts[:-1]
        for depth in range(1, len(parts)):
            dirs_needing_index.add(parts[:depth])

    # -----------------------------------------------------------------------
    # Step 3 – load existing nav_orders so we can preserve them
    # -----------------------------------------------------------------------
    index_nav_orders, page_nav_orders = load_existing_nav_orders()

    # -----------------------------------------------------------------------
    # Step 4 – generate index pages (shallowest first so parent titles are
    # known when processing children)
    # -----------------------------------------------------------------------
    index_titles: dict[tuple, str] = {}  # dir_tuple → rendered title

    for dir_tuple in sorted(dirs_needing_index, key=len):
        slug = dir_tuple[-1]
        folder_name = display_name(slug, words)
        depth = len(dir_tuple)
        src_dir = REPO_ROOT / Path(*dir_tuple)
        docs_dir_path = DOCS_DIR / Path(*dir_tuple)
        docs_dir_path.mkdir(parents=True, exist_ok=True)

        parent_title = index_titles.get(dir_tuple[:-1]) if depth > 1 else None
        grand_parent_title = index_titles.get(dir_tuple[:-2]) if depth > 2 else None

        readme_symlink = maybe_create_readme_symlink(
            src_dir / "README.md",
            f"{'-'.join(dir_tuple)}.md",
        )

        # Preserve existing nav_order or assign the next available one.
        if dir_tuple not in index_nav_orders:
            parent_key = dir_tuple[:-1]
            sibling_indices = {
                k[-1]: v
                for k, v in index_nav_orders.items()
                if len(k) == depth and k[:-1] == parent_key
            }
            sibling_pages = dict(page_nav_orders.get(parent_key, {}))
            index_nav_orders[dir_tuple] = next_nav_order(
                {**sibling_indices, **sibling_pages}
            )

        index_titles[dir_tuple] = folder_name

        index_path = docs_dir_path / "index.md"
        content = index_template.render(
            index_name=folder_name,
            nav_order=index_nav_orders[dir_tuple],
            parent=parent_title,
            grand_parent=grand_parent_title,
            readme_symlink=readme_symlink,
        )
        index_path.write_text(content, encoding="utf-8")
        generated.append(str(index_path.relative_to(REPO_ROOT)))

    # -----------------------------------------------------------------------
    # Step 5 – generate action doc pages
    # -----------------------------------------------------------------------
    for action_path in sorted(valid_actions):
        parts = action_path.relative_to(REPO_ROOT).parts[:-1]
        leaf_slug = parts[-1]
        parent_parts = parts[:-1]
        depth = len(parts)

        docs_parent_dir = DOCS_DIR / Path(*parent_parts)
        docs_parent_dir.mkdir(parents=True, exist_ok=True)

        with action_path.open(encoding="utf-8") as fh:
            action_data = yaml.safe_load(fh)

        action_name = action_data.get("name") or display_name(leaf_slug, words)
        description = (action_data.get("description") or "").strip()

        full_slug = "-".join(parts)
        action_readme_symlink = maybe_create_readme_symlink(
            action_path.parent / "README.md",
            f"{full_slug}.md",
        )

        parent_title = index_titles.get(parent_parts)
        grand_parent_title = (
            index_titles.get(parent_parts[:-1]) if len(parent_parts) > 1 else None
        )

        # Preserve existing nav_order or assign the next available one.
        if leaf_slug not in page_nav_orders[parent_parts]:
            sibling_indices = {
                k[-1]: v
                for k, v in index_nav_orders.items()
                if len(k) == depth and k[:-1] == parent_parts
            }
            sibling_pages = dict(page_nav_orders.get(parent_parts, {}))
            page_nav_orders[parent_parts][leaf_slug] = next_nav_order(
                {**sibling_indices, **sibling_pages}
            )

        nav_order = page_nav_orders[parent_parts][leaf_slug]

        doc_path = docs_parent_dir / f"{leaf_slug}.md"
        content = action_template.render(
            action_name=action_name,
            nav_order=nav_order,
            parent=parent_title,
            grand_parent=grand_parent_title,
            description=description,
            action_readme_symlink=action_readme_symlink,
        )
        doc_path.write_text(content, encoding="utf-8")
        generated.append(str(doc_path.relative_to(REPO_ROOT)))

    # Summary
    print("# Documentation Generation Summary")
    print('\n---\n')

    print(f"\n## Generated ({len(generated)}):")
    for path in generated:
        print(f"  + `{path}`")

    if skipped:
        print(f"\n## Skipped ({len(skipped)}):")
        for path, reason in skipped:
            print(f"  - `{path}`  [{reason}]")

    print(f"\n---\n**Total: {len(generated)} generated, {len(skipped)} skipped**")


if __name__ == "__main__":
    main()
