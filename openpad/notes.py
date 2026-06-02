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
    """Return nested tree: each folder has name, folder (rel path), notes, children."""
    ensure_dirs()

    def _scan(dir_path):
        notes = []
        children = []
        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: e.name)
            for entry in entries:
                if entry.is_dir():
                    sub_notes, sub_children = _scan(Path(entry.path))
                    rel = str(Path(entry.path).relative_to(NOTES_DIR))
                    children.append({
                        "name": entry.name,
                        "folder": rel,
                        "notes": sub_notes,
                        "children": sub_children,
                    })
                elif entry.name.endswith(".md"):
                    notes.append(Path(entry.name).stem)
        except Exception:
            pass
        notes.sort(key=lambda n: Path(dir_path, f"{n}.md").stat().st_ctime)
        return notes, children

    root_notes, top_children = _scan(NOTES_DIR)
    tree = []
    if root_notes:
        tree.append({
            "name": "__root__",
            "folder": None,
            "notes": root_notes,
            "children": [],
        })
    tree.extend(top_children)
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
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / ".keep").touch()


def delete_folder(name: str):
    import shutil
    folder_path = NOTES_DIR / name
    if folder_path.exists():
        shutil.rmtree(folder_path)


def get_all_folders() -> list[str | None]:
    """Return list of all folder paths (None = root), sorted."""
    ensure_dirs()
    folders: list[str | None] = [None]  # None = root
    for entry in sorted(NOTES_DIR.rglob("*")):
        if entry.is_dir():
            rel = str(entry.relative_to(NOTES_DIR))
            folders.append(rel)
    return folders


def move_note(old_folder: str | None, name: str, new_folder: str | None) -> bool:
    """Move a note to a different folder. Returns True on success."""
    ensure_dirs()
    if old_folder and old_folder != "__root__":
        src = NOTES_DIR / old_folder / f"{name}.md"
    else:
        src = NOTES_DIR / f"{name}.md"

    if new_folder and new_folder != "__root__":
        dest_dir = NOTES_DIR / new_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{name}.md"
    else:
        dest = NOTES_DIR / f"{name}.md"

    if not src.exists() or src == dest:
        return False
    if dest.exists():
        return False
    src.rename(dest)
    return True


def move_folder(folder: str, new_parent: str | None) -> tuple[bool, str]:
    """Move a folder under new_parent. Returns (success, new_folder_path)."""
    import shutil
    ensure_dirs()
    src = NOTES_DIR / folder
    folder_name = Path(folder).name

    if new_parent and new_parent != "__root__":
        dest = NOTES_DIR / new_parent / folder_name
    else:
        dest = NOTES_DIR / folder_name

    if not src.exists():
        return False, ""
    if src == dest:
        return False, ""
    # Prevent moving a folder into itself or a descendant
    try:
        dest.relative_to(src)
        return False, ""  # dest is inside src
    except ValueError:
        pass
    if dest.exists():
        return False, ""
    shutil.move(str(src), str(dest))
    new_rel = str(dest.relative_to(NOTES_DIR))
    return True, new_rel


def search_notes(query: str) -> list:
    """Return list of (folder, note_name, snippet, line, col) matching query."""
    query = query.lower().strip()
    results = []
    ensure_dirs()
    for f in NOTES_DIR.rglob("*.md"):
        rel = f.relative_to(NOTES_DIR)
        folder = str(rel.parent) if str(rel.parent) != "." else "__root__"
        content = f.read_text()
        if query in f.stem.lower():
            # Match in filename - return beginning of file
            snippet = content[:60].replace("\n", " ")
            if len(content) > 60:
                snippet += "..."
            results.append((folder, f.stem, snippet, 0, 0))
        elif query in content.lower():
            # Match in content
            snippet, line, col = _get_snippet_with_position(content, query)
            results.append((folder, f.stem, snippet, line, col))
    return results


def _get_snippet_with_position(content: str, query: str) -> tuple[str, int, int]:
    """Get snippet with line and column position of first match."""
    content_lower = content.lower()
    query_lower = query.lower()
    idx = content_lower.find(query_lower)
    
    if idx == -1:
        return content[:60].replace("\n", " "), 0, 0
    
    # Calculate line and column (0-indexed)
    line_count = content[:idx].count('\n')
    line_start = content.rfind('\n', 0, idx) + 1
    col = idx - line_start
    
    # Get snippet around the match
    start = max(0, idx - 20)
    end = min(len(content), idx + len(query) + 20)
    snippet = content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    
    return snippet, line_count, col


def seed_sample_notes():
    """Create sample notes that introduce OpenPad's features."""
    tree = get_tree()
    if tree:
        return

    create_folder("Welcome")
    write_note(
        "Welcome", "Getting Started",
        "# Welcome to OpenPad\n\n"
        "OpenPad is a **terminal-based** note-taking app for developers.\n"
        "Your notes are plain `.md` files stored locally — no lock-in, no cloud requirement.\n\n"
        "## First Steps\n"
        "- Press `n` to create a new note (or `name/` to create a folder)\n"
        "- Press `e` to toggle edit mode and start typing\n"
        "- Press `ctrl+f` to search across all your notes\n"
        "- Press `q` to quit\n\n"
        "## Tips\n"
        "The sample notes in this folder tree demonstrate every feature.\n"
        "Open a few in tabs, try the search, switch themes — explore!\n"
    )

    create_folder("Guide")
    write_note(
        "Guide", "Key Bindings",
        "# Key Bindings\n\n"
        "| Key | Action |\n"
        "|-----|--------|\n"
        "| `n` | New note (or `name/` for folder) |\n"
        "| `e` | Toggle edit mode |\n"
        "| `ctrl+f` | Search notes |\n"
        "| `ctrl+m` | Move note or folder |\n"
        "| `ctrl+t` | Change theme |\n"
        "| `ctrl+c` | Open calendar |\n"
        "| `d` | Delete note or folder |\n"
        "| `shift+left` | Previous tab |\n"
        "| `shift+right` | Next tab |\n"
        "| `space` then `e` | Toggle sidebar |\n"
        "| `escape` | Exit edit mode |\n"
        "| `q` | Quit |\n\n"
        "## Editing\n"
        "- **Double-click** a note in view mode to jump into edit mode\n"
        "- `Tab` inserts 4 spaces\n"
        "- Auto-saves as you type\n"
        "- Rename a note by changing the `# Title` line and pressing `e`\n"
    )
    write_note(
        "Guide", "Markdown Reference",
        "# Markdown Reference\n\n"
        "OpenPad renders Markdown with style.\n\n"
        "## Text Formatting\n"
        "- **Bold** — wrap with `**`\n"
        "- *Italic* — wrap with `*`\n"
        "- `Inline code` — wrap with backticks\n\n"
        "## Lists\n"
        "- Unordered lists start with `-` or `*`\n"
        "  - Nested items use indentation\n"
        "1. Numbered lists use `1.`\n"
        "2. Second item\n\n"
        "## Blockquotes\n"
        "> Prefix with `>` for blockquotes\n"
        "> They can span multiple lines\n\n"
        "## Code Blocks\n"
        "Wrap code in triple backticks with a language name:\n\n"
        "```python\n"
        "def greet(name):\n"
        "    return f\"Hello, {name}!\"\n"
        "```\n\n"
        "## Horizontal Rules\n"
        "Three dashes `---` create a divider.\n"
    )
    write_note(
        "Guide", "Working with Folders",
        "# Working with Folders\n\n"
        "Stay organized with a folder tree.\n\n"
        "## Creating\n"
        "- Press `n` and type `FolderName/` (ends with `/`) to create a folder\n"
        "- Nest folders with `Parent/Child`\n\n"
        "## Moving\n"
        "- Press `ctrl+m` on a selected note or highlighted folder\n"
        "- Pick the destination folder from the list\n"
        "- Notes inside a moved folder go with it\n\n"
        "## Deleting\n"
        "- Press `d` on a note to delete it\n"
        "- Press `d` on a highlighted folder to delete everything inside it\n\n"
        "Folders with git changes show `●` (modified) or `?` (untracked) in the sidebar.\n"
    )

    create_folder("Features")
    write_note(
        "Features", "Tabs & Search",
        "# Tabs & Search\n\n"
        "## Tabbed Editing\n"
        "Open multiple notes at once:\n"
        "- **Click** a note in the tree to open it in a tab\n"
        "- Use `shift+left` / `shift+right` to switch tabs\n"
        "- Each tab remembers its scroll position and cursor\n"
        "- Click the `×` on a tab to close it\n"
        "- The tab bar scrolls when you have many tabs open\n\n"
        "## Full-Text Search\n"
        "- Press `ctrl+f` to open search\n"
        "- Type a query — results appear after 300ms\n"
        "- Matches are found in both *filenames* and *content*\n"
        "- Press `enter` on a result to jump directly to the match\n"
        "- The match is **highlighted in yellow** for 1.5 seconds\n"
    )
    write_note(
        "Features", "Themes",
        "# Themes\n\n"
        "OpenPad ships with 11 hand-crafted themes.\n\n"
        "- **opencode** — warm amber on dark\n"
        "- **tokyonight** — deep blue/purple nights\n"
        "- **everforest** — warm green forest tones\n"
        "- **ayu** — orange & teal on deep dark\n"
        "- **catppuccin** — soft pastel dark\n"
        "- **catppuccin-macchiato** — darker variant\n"
        "- **gruvbox** — retro warm brown & yellow\n"
        "- **kanagawa** — Japanese ink-inspired blues\n"
        "- **nord** — arctic cold blue-grey\n"
        "- **matrix** — hacker green on black\n"
        "- **one-dark** — Atom One Dark\n\n"
        "Press `ctrl+t` to open the theme picker and preview them all.\n"
        "Your selection is saved to `~/.openpad/meta.json`.\n"
    )
    write_note(
        "Features", "Google Calendar",
        "# Google Calendar\n\n"
        "OpenPad can display your Google Calendar events.\n\n"
        "## Setup\n"
        "1. Go to the [Google Cloud Console](https://console.cloud.google.com)\n"
        "2. Create a project and enable the **Google Calendar API**\n"
        "3. Create OAuth 2.0 credentials (Desktop app type)\n"
        "4. Download `credentials.json` and place it at:\n\n"
        "   `~/.openpad/credentials.json`\n\n"
        "## Usage\n"
        "- Press `ctrl+c` to open the calendar\n"
        "- Navigate with `shift+left`/`shift+right` (month), `left`/`right` (day), `up`/`down` (week)\n"
        "- Click a day to select it\n"
        "- Exams and deadlines are highlighted in **red**\n\n"
        "If you skip this setup, OpenPad works normally — no errors.\n"
    )

    create_folder("Examples")
    write_note(
        "Examples", "Python",
        "# Python\n\n"
        "```python\n"
        "def fibonacci(n):\n"
        "    a, b = 0, 1\n"
        "    for _ in range(n):\n"
        "        yield a\n"
        "        a, b = b, a + b\n\n"
        "list comprehension: [x*x for x in range(10)]\n"
        "lambda: sorted(items, key=lambda x: x.price)\n"
        "f-strings: f\"Hello, {name}!\"\n"
        "```\n"
    )
    write_note(
        "Examples", "JavaScript",
        "# JavaScript\n\n"
        "```js\n"
        "function debounce(fn, delay) {\n"
        "    let timer;\n"
        "    return (...args) => {\n"
        "        clearTimeout(timer);\n"
        "        timer = setTimeout(() => fn(...args), delay);\n"
        "    };\n"
        "}\n\n"
        "const squares = [1, 2, 3].map(n => n * n);\n"
        "const { name, age } = person;\n"
        "```\n"
    )
    write_note(
        "Examples", "SQL",
        "# SQL\n\n"
        "```sql\n"
        "SELECT\n"
        "    u.name,\n"
        "    COUNT(o.id) AS order_count\n"
        "FROM users u\n"
        "LEFT JOIN orders o ON o.user_id = u.id\n"
        "WHERE u.active = 1\n"
        "GROUP BY u.id\n"
        "HAVING order_count > 5\n"
        "ORDER BY order_count DESC;\n"
        "```\n"
    )