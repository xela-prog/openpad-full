# OpenPad

```
  █▀▀█ █▀▀█ █▀▀▀ █▀▀▄ █▀▀█ █▀▀█ █▀▀▄
  █  █ █▀▀▀ █▀▀▀ █  █ █▀▀▀ █▀▀█ █  █
  ▀▀▀▀ ▀    ▀▀▀▀ ▀  ▀ ▀    ▀  ▀ ▀▀▀▀
```

A fast, terminal-based note-taking app designed for computer science students.
Write, organize, and search Markdown notes — directly from your terminal.

---

## Features

- **Folder-based note organization** — hierarchical tree sidebar with expand/collapse
- **Tabbed editing** — open multiple notes, switch with `shift+left`/`shift+right`
- **Markdown rendering** — headings, lists, code blocks, bold, italic, inline code, blockquotes, horizontal rules
- **Syntax highlighting** — 20+ languages in code blocks (Rich Monokai theme)
- **Live search** — debounced full-text search across all notes, jump-to-position with yellow highlight
- **Move notes & folders** — reorganize with `ctrl+m`, pick a destination folder
- **Auto-save** — every keystroke writes to disk immediately
- **Auto-rename** — changing the first `# Title` renames the file on exit
- **11 built-in themes** — Tokyo Night, Catppuccin, Gruvbox, Nord, Matrix, and more
- **Google Calendar integration** — optional, view events/exams/deadlines in-app
- **Session log** — on quit, see a summary of every note created, edited, deleted, moved, or renamed
- **Lightweight** — Textual-based TUI, no Electron, runs in any terminal
- **Plain Markdown files** — no lock-in, notes are just `.md` files on disk

---

## Install

Requires **Python 3.10 or newer**.

```bash
pip install openpad                     # basic install
pip install "openpad[calendar]"         # with Google Calendar support
```

> Calendar support is optional. Without it, the app runs normally — only the calendar view will show a message asking for credentials.

### Linux (Debian / Ubuntu / Mint)

```bash
python3 --version                    # check Python version
sudo apt update
sudo apt install python3 python3-pip -y
pip install openpad                  # or: pip install "openpad[calendar]"
openpad
```

### Linux (Arch / Manjaro)

Arch protects its system Python (PEP 668). Use **pipx** — it creates an isolated environment for CLI apps:

```bash
python --version
sudo pacman -S python python-pipx
pipx install openpad                 # or: pipx install "openpad[calendar]"
openpad
```

### Linux (Fedora)

```bash
python3 --version
sudo dnf install python3 python3-pip
pip install openpad                  # or: pip install "openpad[calendar]"
openpad
```

### Windows

OpenPad works best with **Windows Terminal** (free from the Microsoft Store).
The standard Command Prompt (`cmd`) will also work but colours may look worse.

```powershell
# Install Python 3.10+ from https://python.org
# IMPORTANT: check "Add Python to PATH" during installation

python --version
pip --version
pip install openpad                  # or: pip install "openpad[calendar]"
openpad
```

> **WSL alternative:** If you use WSL (Ubuntu), follow the Ubuntu steps above instead.

### macOS

```bash
python3 --version
brew install python@3        # if missing or < 3.10
pip3 install openpad                  # or: pip install "openpad[calendar]"
openpad
```

---

## Upgrading

All your notes, settings, and credentials are stored in `~/.openpad/` — upgrading the app never touches them.

```bash
# If installed via pipx (recommended for Arch / Manjaro)
pipx upgrade openpad                 # or: pipx upgrade "openpad[calendar]"

# If installed via pip
pip install --upgrade openpad        # or: pip install --upgrade "openpad[calendar]"

# If installed from source
git pull
pip install -e .                     # or: pip install -e ".[calendar]"
```

---

## Quick Start

On first launch, OpenPad creates **sample notes** in `~/.openpad/notes/` that serve as an interactive tutorial:

| Folder | Notes |
|--------|-------|
| `Welcome/` | Getting Started |
| `Guide/` | Key Bindings, Markdown Reference, Working with Folders |
| `Features/` | Tabs & Search, Themes, Google Calendar |
| `Examples/` | Python, JavaScript, SQL |

**Basic workflow:**

1. **Navigate** — arrow keys in the sidebar to browse notes
2. **Open** — press `Enter` on a note to open it in a tab
3. **Edit** — press `e` to enter edit mode, start typing
4. **Switch tabs** — `shift+left` / `shift+right`
5. **Search** — `ctrl+f`, type a query, press `Enter` on a result
6. **Quit** — press `q` to exit (see a summary of your session)

---

## Key Bindings

### Global

| Key | Action |
|-----|--------|
| `n` | Create new note (or `name/` for a folder) |
| `d` | Delete selected note / highlighted folder |
| `e` | Toggle edit mode |
| `ctrl+f` | Open search |
| `ctrl+m` | Move note or folder |
| `ctrl+t` | Open theme picker |
| `ctrl+c` | Open calendar |
| `escape` | Exit edit mode / close modal |
| `t` | Focus the note tree |
| `q` | Quit (shows session summary) |
| `shift+left` | Previous tab |
| `shift+right` | Next tab |
| `space` then `e` | Toggle sidebar visibility |

### Calendar Modal (`ctrl+c`)

| Key | Action |
|-----|--------|
| `shift+left` | Previous month |
| `shift+right` | Next month |
| `left` | Previous day |
| `right` | Next day |
| `up` | Previous week (7 days) |
| `down` | Next week (7 days) |
| `escape` | Close calendar |
| Click a day | Select that day |

### Move Modal (`ctrl+m`)

| Key | Action |
|-----|--------|
| `up` / `down` | Navigate folder list |
| `enter` | Confirm move to selected folder |
| `escape` | Cancel |

### Theme Picker (`ctrl+t`)

| Key | Action |
|-----|--------|
| `up` / `down` | Browse themes |
| `enter` | Select theme |
| `escape` | Close without changing |

### Confirm Modal (deletions)

| Key | Action |
|-----|--------|
| `y` | Confirm |
| `n` | Cancel |
| `escape` | Cancel |

### Text Editor

| Key | Action |
|-----|--------|
| `tab` | Insert 4 spaces |

---

## Features in Depth

### Note Tree & Sidebar

The sidebar shows all notes organized in folders. Each note has an icon (``).

**Navigation:**
- **Arrow keys** — move highlight, preview note content (no tab created)
- **Enter** — select a note, opening it in a new tab
- Click on a folder name to highlight it for delete/move operations

The sidebar auto-resizes its width (max 45 characters). Press `space` then `e` to toggle it.

### Tab System

Each opened note appears as a tab at the top. Key behaviors:
- **Tab bar** appears when 2+ tabs are open
- **Scrolling** — left/right arrow buttons appear when tabs overflow
- **Persistence** — each tab remembers scroll position (view) and cursor position (edit)
- **Close** — click the `✕` button on any tab
- **Active tab** — highlighted in bold white

### Editor (View / Edit Modes)

Notes have two modes:

| Mode | What you see | What you can do |
|------|-------------|-----------------|
| **View** | Rendered Markdown | Navigate, scroll, double-click to edit |
| **Edit** | Raw Markdown (TextArea) | Type, auto-save, auto-rename |

- **Toggle:** press `e`
- **Auto-save:** every keystroke saves to disk immediately
- **Auto-rename:** if the first `# Heading` changes, the file is renamed on exit
- **Exit edit mode:** `escape`, or click outside the editor

### Markdown Rendering

| Syntax | Appearance |
|--------|-----------|
| `# Heading 1` | Bold, primary color |
| `## Heading 2` | Bold, secondary color |
| `### Heading 3` | Bold, accent color |
| `#### Heading 4` | Accent color |
| `**bold**` / `__bold__` | Bold text |
| `*italic*` / `_italic_` | Italic text |
| `` `code` `` | Inline code in syntax string color |
| `- list` / `* list` | Bulleted list |
| `1. numbered` | Numbered list |
| `> quote` | Blockquote with `│` prefix |
| `---` | Horizontal rule |
| `` ```lang ``` `` | Syntax-highlighted code block |

**Code block language aliases:** `js`, `py`, `sh`, `ts`, `md`, `rb`, `rs`, `cs` and more.

### Search

- Press `ctrl+f` to open the search modal
- Typing triggers a **300ms debounced** search
- Searches both filenames and file content (case-insensitive)
- Shows up to **20 results** with folder path, filename, and 50-character snippet
- Press `Enter` on a result to open the note and **jump to the match position**
- The matched text is highlighted in **bold reverse yellow** for 1.5 seconds

### Move Notes & Folders

1. Highlight a note in the tree (or a folder by clicking its name)
2. Press `ctrl+m`
3. Navigate the folder list with `up`/`down`
4. Press `enter` to move — or `escape` to cancel

The root `/` option moves items out of any subfolder.

### Theme System

11 themes, each defining 18 color slots:

| Theme | Vibe |
|-------|------|
| `opencode` | Warm amber default |
| `tokyonight` | Deep blue/purple nights |
| `everforest` | Warm green forest tones |
| `ayu` | Orange & teal on deep dark |
| `catppuccin` | Soft pastel dark |
| `catppuccin-macchiato` | Darker catppuccin variant |
| `gruvbox` | Retro warm brown & yellow |
| `kanagawa` | Japanese ink-inspired blues |
| `nord` | Arctic cold blue-grey |
| `matrix` | Hacker green on black |
| `one-dark` | Atom One Dark |

Press `ctrl+t` to open the theme picker. **Restart the app for the theme to fully apply** — some residual colours from the previous theme may persist until restart.

### Calendar

Press `ctrl+c` to open the calendar modal. Navigate months, weeks, and individual days using the arrow keys (see key bindings above).

If Google Calendar is configured, events appear overlaid on the calendar grid:
- **Exams, tests, deadlines** — shown in red
- **Other events** — shown in secondary colour
- **All-day events** — marked as "All day"
- **Timed events** — shown with `HH:MM → HH:MM` format

If not configured, the calendar still works for planning — it just won't show events.

### Status Bar

The bottom of the screen shows:
```
 VIEW ▸ Guide/Key Bindings ▸ 42 lines ▸ 14:32
```

- **Mode badge** — `VIEW` or `EDIT` (coloured with theme primary)
- **File path** — current note's folder and name
- **Line count** — number of lines in the current note
- **Time** — 24-hour, updates every 60 seconds

### Session Log & Exit Summary

When you press `q` to quit, OpenPad prints a session summary showing every change:

```
  ~ edited:   Guide/Key Bindings
  + created note:   Welcome/Getting Started
  + created folder:  Examples
  - deleted note:   Old Note/Todo
  * renamed:    Draft → Final
  → moved note:  Notes/File → Guide
```

This gives you a complete record of what you did during the session.

---

## Google Calendar Setup

This is **optional** — OpenPad works perfectly without it. When configured, the calendar view shows your events, with exams and deadlines highlighted in red.

> **Prerequisite:** You need the calendar extras installed: `pip install "openpad[calendar]"` (or `pip install -e ".[calendar]"` if building from source).

### Step 1: Enable the Google Calendar API

1. Go to the [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for **"Google Calendar API"** and click **Enable**

### Step 2: Create OAuth 2.0 credentials

1. In the Cloud Console, go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - Choose **External** user type
   - Fill in the app name and your email address
   - Under **Scopes**, add `.../auth/calendar.readonly` (or skip — it will be requested at runtime)
   - Under **Test users**, add your email address
   - Save and continue
4. For **Application type**, select **Desktop app**
5. Give it a name (e.g. "OpenPad Calendar")
6. Click **Create**
7. Click the **Download JSON** button

### Step 3: Place credentials.json

Create the directory and move the downloaded file:

```bash
mkdir -p ~/.openpad
mv ~/Downloads/client_secret_*.json ~/.openpad/credentials.json
```

The file should contain a JSON object with an `"installed"` key (not `"web"`). It will look like this:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "YOUR_PROJECT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

### Step 4: Authenticate (one-time)

You have two options:

**Option A** — Authenticate from within OpenPad:
1. Launch OpenPad: `openpad`
2. Press `ctrl+c` to open the calendar
3. A browser tab will open asking you to log into Google and grant read-only calendar access
4. After authorizing, `~/.openpad/token.pickle` is created automatically

**Option B** — Run the standalone auth script:
```bash
python auth_calendar.py
```

### Step 5: Verify

After setup, you should have these files:

```
~/.openpad/credentials.json    # OAuth client secret (yours to keep safe)
~/.openpad/token.pickle        # OAuth token (auto-generated)
```

Open the calendar (`ctrl+c`) — your events should appear with exams and deadlines in red.

> **What the scope allows:** Read-only access (`calendar.readonly`). OpenPad can view your events but cannot create, modify, or delete anything on your calendar.

> **If you skip this setup:** OpenPad works normally with no errors. The calendar simply shows a message asking you to configure credentials.

---

## Data Storage

| Path | Contents |
|------|----------|
| `~/.openpad/notes/` | All notes as `.md` files, organized in folders |
| `~/.openpad/meta.json` | Settings (`{"theme": "theme_name"}`) |
| `~/.openpad/credentials.json` | Google Calendar OAuth credentials (optional) |
| `~/.openpad/token.pickle` | Google Calendar OAuth token (auto-generated) |

---

## Build from Source

```bash
git clone <repo-url>
cd openpad
pip install -e .                     # basic install
pip install -e ".[calendar]"         # with Google Calendar support
openpad
```

---

## Troubleshooting

### Colors look wrong

```bash
echo $TERM
# should show xterm-256color or similar
```

If your terminal doesn't support true colour, some theme colours may not display correctly.

### "pip: command not found"

**Linux:** use `python3 -m pip` instead of `pip`:
```bash
python3 -m pip install openpad
```

**Windows:** make sure you checked **Add Python to PATH** during Python installation, or use:
```powershell
python -m pip install openpad
```

### Google Calendar doesn't open

- Verify `~/.openpad/credentials.json` exists and has the `"installed"` key
- Delete `~/.openpad/token.pickle` and re-authenticate if the token expired
- Check that the Google Calendar API is enabled in your Cloud Console project

### Permission issues

```bash
ls -la ~/.openpad/
```

Ensure your user owns the directory and files.

---

## License

MIT License

---

Built with [Textual](https://textual.textualize.io/)
