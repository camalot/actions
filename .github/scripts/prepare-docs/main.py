#!/usr/bin/env python3
"""Generate Jekyll documentation pages and _includes symlinks from action.yml files.

Actions without a README.md alongside their action.yml are skipped entirely.
Category folders that contain sub-folder actions are rendered via index.md.j2;
if the category folder itself has a README.md it is symlinked and included.
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


def action_parts(action_path: Path) -> tuple[str, str, str]:
    """Return (category, sub_slug, full_slug).

    helm/build-publish/action.yml -> ("helm", "build-publish", "helm-build-publish")
    version/release/action.yml    -> ("version", "release",    "version-release")
    """
    rel_parts = action_path.relative_to(REPO_ROOT).parts[:-1]
    category = rel_parts[0]
    sub_slug = "-".join(rel_parts[1:]) if len(rel_parts) > 1 else rel_parts[0]
    full_slug = "-".join(rel_parts)
    return category, sub_slug, full_slug


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


def get_category_title(cat_dir: Path) -> str:
    fm = parse_front_matter(cat_dir / "index.md")
    return fm.get("title", "")


def get_existing_page_nav_orders(cat_dir: Path) -> dict[str, int]:
    """Return {stem: nav_order} for every non-index page in cat_dir."""
    orders: dict[str, int] = {}
    for md in cat_dir.glob("*.md"):
        if md.name == "index.md":
            continue
        v = read_nav_order(md)
        if v is not None:
            orders[md.stem] = v
    return orders


def get_existing_index_nav_orders() -> dict[str, int]:
    """Return {category: nav_order} from existing category index.md files."""
    orders: dict[str, int] = {}
    for index in DOCS_DIR.glob("*/index.md"):
        v = read_nav_order(index)
        if v is not None:
            orders[index.parent.name] = v
    return orders


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

    # Partition actions: only process those with a README.md.
    by_category: dict[str, list[Path]] = defaultdict(list)
    for action_path in find_actions():
        rel = str(action_path.relative_to(REPO_ROOT))
        if not (action_path.parent / "README.md").exists():
            skipped.append((rel, "no README.md"))
            continue
        cat, _, _ = action_parts(action_path)
        by_category[cat].append(action_path)

    # Track category index nav_orders (preserved across regeneration).
    index_nav_orders = get_existing_index_nav_orders()

    for category, paths in sorted(by_category.items()):
        cat_dir = DOCS_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        index_name = display_name(category, words)

        # Category folder README symlink (e.g. helm/README.md → _includes/helm.md).
        cat_readme = REPO_ROOT / category / "README.md"
        readme_symlink = maybe_create_readme_symlink(cat_readme, f"{category}.md")

        # Preserve or assign category index nav_order.
        if category not in index_nav_orders:
            index_nav_orders[category] = next_nav_order(index_nav_orders)

        index_content = index_template.render(
            index_name=index_name,
            nav_order=index_nav_orders[category],
            parent=None,
            readme_symlink=readme_symlink,
        )
        index_path = cat_dir / "index.md"
        index_path.write_text(index_content, encoding="utf-8")
        generated.append(str(index_path.relative_to(REPO_ROOT)))

        # Snapshot existing action page nav_orders for this category.
        existing = get_existing_page_nav_orders(cat_dir)
        parent_title = get_category_title(cat_dir)

        for action_path in sorted(paths):
            _, sub_slug, full_slug = action_parts(action_path)

            with action_path.open(encoding="utf-8") as fh:
                action_data = yaml.safe_load(fh)

            action_name = action_data.get("name") or display_name(sub_slug, words)
            description = (action_data.get("description") or "").strip()

            # Action README symlink (always exists at this point — skipped otherwise).
            action_readme_symlink = maybe_create_readme_symlink(
                action_path.parent / "README.md",
                f"{full_slug}.md",
            )

            # Preserve existing nav_order; assign a new one otherwise.
            doc_path = cat_dir / f"{sub_slug}.md"
            if sub_slug in existing:
                nav_order = existing[sub_slug]
            else:
                nav_order = next_nav_order(existing)
                existing[sub_slug] = nav_order

            content = action_template.render(
                action_name=action_name,
                nav_order=nav_order,
                parent=parent_title,
                description=description,
                action_readme_symlink=action_readme_symlink,
            )
            doc_path.write_text(content, encoding="utf-8")
            generated.append(str(doc_path.relative_to(REPO_ROOT)))

    # Summary
    width = 60
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
