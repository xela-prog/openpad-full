# OpenPad

```
  █▀▀█ █▀▀█ █▀▀▀ █▀▀▄ █▀▀█ █▀▀█ █▀▀▄
  █  █ █▀▀▀ █▀▀▀ █  █ █▀▀▀ █▀▀█ █  █
  ▀▀▀▀ ▀    ▀▀▀▀ ▀  ▀ ▀    ▀  ▀ ▀▀▀▀
```

A terminal-based note-taking application designed for computer science students. Write and organize your programming notes, lecture materials, and code snippets in Markdown - all from the comfort of your terminal.

---

**Current Version: 1.2 (2026-04-19)**

---

## Features

- **Folder Organization** - Organize notes into folders for different subjects (Databases, Linux, Java, etc.)
- **Notes Sorted by Creation Date** - Notes inside folders are now sorted by their creation date for easier chronological navigation
- **Markdown Support** - Write notes in Markdown with headers, lists, code blocks, and more
- **Syntax Highlighting** - Code blocks in your notes support syntax highlighting for 20+ languages
- **12 Built-in Themes** - Choose from popular themes like Tokyo Night, Catppuccin, Gruvbox, Nord, and more
- **Full-Text Search** - Instantly search across all your notes by title or content
- **Auto-Save** - Your changes are saved automatically as you type
- **Google Calendar Integration** - View your calendar and click on any date to see events for that day
- **Lightweight** - Built with Python and Textual, runs in any terminal with true color support
- **Secure Publishing** - `.gitignore` is preconfigured to exclude credentials and Python cache files

## Requirements

- **Python 3.10 or higher** - Required for the modern type annotations used in the code
- **Terminal with true color support** - Most modern terminals (iTerm2, Windows Terminal, Alacritty, GNOME Terminal) support this
- **Operating System** - Linux, macOS, or Windows (via WSL or Windows Terminal)

To check your Python version:
```bash
python3 --version
```

---

## Windows Users

OpenPad works great on Windows! You have two main options:

### 1. Windows Terminal (Native)

- Install [Windows Terminal](https://aka.ms/terminal) from the Microsoft Store (recommended)
- Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/)
- Open Windows Terminal and run the installation steps as shown above
- Run the app with `python main.py`

### 2. WSL (Windows Subsystem for Linux)

- Install [WSL](https://docs.microsoft.com/en-us/windows/wsl/install) and a Linux distribution (e.g., Ubuntu)
- Open your WSL terminal
- Follow the Linux installation steps above
- Run the app with `python3 main.py`

**Tips:**
- For best appearance, use Windows Terminal or a modern terminal emulator with true color support
- If you see color or layout issues, try resizing your terminal or using a different font
- If you have both `python` and `python3` installed, use the one that matches your Python 3.10+ installation

---

## Installation

1. **Clone or download this repository**
   ```bash
   git clone <your-repo-url>
   cd openpad-full
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run OpenPad**
   ```bash
   python main.py
   ```

## Key Bindings

| Key                    | Action                        |
|------------------------|-------------------------------|
| `←/→/↑/↓`              | Navigate calendar and notes   |
| Mouse click (calendar) | Select a date in the calendar |
| `n`                    | Create a new note             |
| `ctrl+n`               | Create a new folder           |
| `e`                    | Toggle edit mode (edit/view)  |
## Security & Publishing

Your `.gitignore` is set up to exclude sensitive files:

- `credentials.json` (API keys)
- `__pycache__/`, `*.pyc` (Python cache)
- `.env`, `.vscode/`, `.DS_Store`, `Thumbs.db`

This ensures you can safely publish your repository without exposing secrets or unnecessary files.

## Calendar Integration

OpenPad integrates with Google Calendar. You can:

- Open the calendar modal (`ctrl+c` or via menu)
- Click any date to view events for that day
- Use arrow keys to navigate months and days

Your Google API credentials are stored in `credentials.json` (excluded from git).
| `d`      | Delete the selected note             |
| `ctrl+f` | Search all notes                     |
| `ctrl+t` | Open theme picker                    |
| `escape` | Exit edit mode (switch to view mode) |
| `q`      | Quit OpenPad                         |

## Getting Started

### Creating Your First Note

1. Press `n` to create a new note
2. Enter a name for your note (e.g., "Python Basics")
3. The note opens in edit mode - start typing!

### Writing Markdown Notes

OpenPad supports standard Markdown syntax. Here are some examples:

```markdown
# Heading 1
## Heading 2

- Bullet point 1
- Bullet point 2

1. Numbered item 1
2. Numbered item 2

**Bold text** and *italic text*

Inline code: `print("Hello World")`

Code block with syntax highlighting:
```python
def greet(name):
    return f"Hello, {name}!"

print(greet("Student"))
```
```

### Organizing Notes into Folders

1. Press `ctrl+n` to create a new folder
2. Enter a folder name (e.g., "DataStructures", "Algorithms", "WebDev")
3. Select the folder in the sidebar, then press `n` to create a note inside it

### Searching Notes

1. Press `ctrl+f` to open the search modal
2. Type your search query
3. Results show matching notes with content snippets
4. Press `enter` to open a selected note

### Changing Themes

1. Press `ctrl+t` to open the theme picker
2. Use `up/down` arrow keys to navigate
3. Press `enter` to select a theme
4. Press `escape` to cancel

Your theme preference is saved automatically and persists between sessions.

## Data Storage

Your notes and settings are stored in your home directory:

| File/Directory         | Description                                      |
|------------------------|--------------------------------------------------|
| `~/.openpad/notes/`    | Your notes (Markdown files organized in folders) |
| `~/.openpad/meta.json` | User preferences (selected theme)                |

### Sample Notes

On first run, OpenPad creates sample notes to help you get started:
- **Database/** - Lesson I, Lesson II, Lesson III
- **Linux/** - Commands
- **Java/** - Lesson I through IV

Feel free to delete or modify these!

## Available Themes

| Theme                | Description                   |
|----------------------|-------------------------------|
| opencode             | OpenCode's default dark theme |
| tokyonight           | Deep blue/purple nights       |
| everforest           | Warm green forest tones       |
| ayu                  | Orange & teal on deep dark    |
| catppuccin           | Soft pastel dark              |
| catppuccin-macchiato | Darker catppuccin variant     |
| gruvbox              | Retro warm brown & yellow     |
| kanagawa             | Japanese ink-inspired blues   |
| nord                 | Arctic cold blue-grey         |
| matrix               | Hacker green on black         |
| one-dark             | Atom One Dark                 |

## For Computer Science Students

OpenPad is designed with CS students in mind:

- **Lecture Notes** - Create folders for each course (e.g., "CS101", "DataStructures", "OperatingSystems")
- **Code References** - Store code snippets with syntax highlighting
- **Quick Access** - Search lets you find that one command or concept instantly
- **Markdown** - Practice writing documentation in Markdown - a skill you'll use professionally
- **Lightweight** - No electron bloat, runs in tmux/screen if needed
- **Portable** - Your notes are just Markdown files - open them in any editor

### Example Use Cases

- **Database Class**: Store SQL queries, schema designs, and normalization notes
- **Linux Administration**: Keep a cheat sheet of common commands
- **Programming Languages**: Document syntax, common patterns, and gotchas
- **Algorithms**: Write pseudocode and analyze time complexity

## Troubleshooting

### Terminal Colors Look Wrong

Ensure your terminal supports true color (24-bit). Most modern terminals do by default. If colors look washed out or incorrect:

```bash
# Check if your terminal reports true color support
echo $TERM
# Should show: xterm-256color or similar
```

### Permission Errors

If you encounter permission errors when saving notes:
```bash
ls -la ~/.openpad/
# Check that the directory is owned by your user
```

### Python Version Error

If you see a syntax error, check your Python version:
```bash
python3 --version
# Must be 3.10 or higher
```

To upgrade Python on Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3.11
```

## License

MIT License - Feel free to use, modify, and distribute as needed.

---

Built with [Textual](https://textual.textualize.io/) - a TUI framework for Python.