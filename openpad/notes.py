import os
import json
from pathlib import Path

NOTES_DIR = Path.home() / ".openpad" / "notes"
META_FILE = Path.home() / ".openpad" / "meta.json"


def ensure_dirs():
    NOTES_DIR.mkdir(parents=True, exist_ok=True)


def load_meta() -> dict:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except Exception:
            pass
    return {"theme": "opencode"}


def save_meta(meta: dict):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(meta, indent=2))


def get_tree() -> list:
    """Return tree: [{"name": folder, "notes": [note_name, ...]}, ...]"""
    ensure_dirs()
    tree = []
    try:
        entries = sorted(os.scandir(NOTES_DIR), key=lambda e: e.name)
        for entry in entries:
            if entry.is_dir():
                notes = [f for f in Path(entry.path).glob("*.md")]
                notes_sorted = sorted(notes, key=lambda f: f.stat().st_ctime)
                tree.append({
                    "name": entry.name,
                    "notes": [f.stem for f in notes_sorted],
                    "path": entry.path
                })
        root_notes = [f for f in NOTES_DIR.glob("*.md")]
        root_notes_sorted = sorted(root_notes, key=lambda f: f.stat().st_ctime)
        if root_notes_sorted:
            tree.insert(0, {
                "name": "__root__",
                "notes": [f.stem for f in root_notes_sorted],
                "path": str(NOTES_DIR)
            })
    except Exception:
        pass
    return tree


def read_note(folder: str | None, name: str) -> str:
    if folder and folder != "__root__":
        path = NOTES_DIR / folder / f"{name}.md"
    else:
        path = NOTES_DIR / f"{name}.md"
    if path.exists():
        return path.read_text()
    return ""


def write_note(folder: str | None, name: str, content: str):
    ensure_dirs()
    if folder and folder != "__root__":
        dir_path = NOTES_DIR / folder
        dir_path.mkdir(exist_ok=True)
        path = dir_path / f"{name}.md"
    else:
        path = NOTES_DIR / f"{name}.md"
    path.write_text(content)


def rename_note(folder: str | None, old_name: str, new_name: str) -> bool:
    """Rename a note file. Returns True if successful, False otherwise."""
    ensure_dirs()
    if folder and folder != "__root__":
        dir_path = NOTES_DIR / folder
        old_path = dir_path / f"{old_name}.md"
        new_path = dir_path / f"{new_name}.md"
    else:
        old_path = NOTES_DIR / f"{old_name}.md"
        new_path = NOTES_DIR / f"{new_name}.md"
    if old_path.exists() and old_path != new_path:
        if new_path.exists():
            return False
        old_path.rename(new_path)
        return True
    return False


def delete_note(folder: str | None, name: str):
    if folder and folder != "__root__":
        path = NOTES_DIR / folder / f"{name}.md"
    else:
        path = NOTES_DIR / f"{name}.md"
    if path.exists():
        path.unlink()


def create_folder(name: str):
    ensure_dirs()
    folder_path = NOTES_DIR / name
    folder_path.mkdir(exist_ok=True)
    (folder_path / ".keep").touch()


def delete_folder(name: str):
    import shutil
    folder_path = NOTES_DIR / name
    if folder_path.exists():
        shutil.rmtree(folder_path)


def search_notes(query: str) -> list:
    """Return list of (folder, note_name, snippet) matching query."""
    query = query.lower().strip()
    results = []
    ensure_dirs()
    for f in NOTES_DIR.glob("*.md"):
        content = f.read_text()
        if query in f.stem.lower() or query in content.lower():
            snippet = _get_snippet(content, query)
            results.append(("__root__", f.stem, snippet))
    for folder in NOTES_DIR.iterdir():
        if folder.is_dir():
            for f in folder.glob("*.md"):
                content = f.read_text()
                if query in f.stem.lower() or query in content.lower():
                    snippet = _get_snippet(content, query)
                    results.append((folder.name, f.stem, snippet))
    return results


def _get_snippet(content: str, query: str) -> str:
    idx = content.lower().find(query)
    if idx == -1:
        return content[:60].replace("\n", " ")
    start = max(0, idx - 20)
    end = min(len(content), idx + 60)
    return "..." + content[start:end].replace("\n", " ") + "..."


def seed_sample_notes():
    """Create structured sample notes if none exist."""
    tree = get_tree()
    if tree:
        return

    create_folder("Courses")
    create_folder("Courses/Intro_to_Programming")
    write_note(
        "Courses/Intro_to_Programming", "Lecture 01 - Variables",
        "# Lecture 01 - Variables\n\n## Key Concepts\n- Variables store data\n"
        "- Types define what data can be stored\n\n## Example (Python)\n"
        "```python\nx = 10\nname = \"Alex\"\n```\n"
    )
    write_note(
        "Courses/Intro_to_Programming", "Lecture 02 - Control Flow",
        "# Lecture 02 - Control Flow\n\n## If Statements\n"
        "```python\nif x > 0:\n    print(\"Positive\")\n```\n\n## Loops\n"
        "```python\nfor i in range(5):\n    print(i)\n```\n"
    )
    create_folder("Courses/Data_Structures")
    write_note(
        "Courses/Data_Structures", "Arrays vs Linked Lists",
        "# Arrays vs Linked Lists\n\n| Feature | Array | Linked List |\n"
        "|--------|------|-------------|\n| Access | O(1) | O(n) |\n"
        "| Insert | O(n) | O(1) |\n\n## Example\n```java\nint[] arr = new int[10];\n```\n"
    )
    create_folder("Concepts")
    write_note(
        "Concepts", "Big-O Notation",
        "# Big-O Notation\n\nDescribes algorithm efficiency.\n\n## Common Complexities\n"
        "- O(1) → Constant\n- O(log n) → Logarithmic\n- O(n) → Linear\n- O(n^2) → Quadratic\n"
    )
    write_note(
        "Concepts", "Git Basics",
        "# Git Basics\n\n## Workflow\n```bash\ngit add .\ngit commit -m \"message\"\ngit push\n```\n\n"
        "## Rollback\n- Used to revert changes before or after commit\n"
    )
    create_folder("Snippets")
    write_note(
        "Snippets", "Python Quick Snippets",
        "# Python Snippets\n\n## List Comprehension\n```python\nsquares = [x*x for x in range(10)]\n```\n\n"
        "## File Read\n```python\nwith open('file.txt') as f:\n    data = f.read()\n```\n"
    )
    write_note(
        "Snippets", "SQL Queries",
        "# SQL Snippets\n\n```sql\nSELECT * FROM users WHERE active = 1;\n\nINSERT INTO users(name) VALUES ('Alex');\n```\n"
    )
    create_folder("Practice")
    write_note(
        "Practice", "Two Sum Problem",
        "# Two Sum\n\n## Problem\nFind two numbers that add up to a target.\n\n## Solution (Python)\n"
        "```python\ndef two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n"
        "        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n```\n"
    )
    create_folder("System")
    write_note(
        "System", "Welcome to OpenPad",
        "# Welcome to OpenPad\n\nThis is your terminal-based note system.\n\n## Key Shortcuts\n"
        "- `n` → New note\n- `ctrl+f` → Search\n- `e` → Edit mode\n\n## Tips\n"
        "- Organize notes in folders\n- Use Markdown for formatting\n- Store code snippets for quick access\n"
    )