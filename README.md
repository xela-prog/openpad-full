# OpenPad

```
  █▀▀█ █▀▀█ █▀▀▀ █▀▀▄ █▀▀█ █▀▀█ █▀▀▄
  █  █ █▀▀▀ █▀▀▀ █  █ █▀▀▀ █▀▀█ █  █
  ▀▀▀▀ ▀    ▀▀▀▀ ▀  ▀ ▀    ▀  ▀ ▀▀▀▀
```

A fast, terminal-based note-taking app designed for computer science students.  
Write, organize, and search Markdown notes — directly from your terminal.

---

## 🚀 Install

```bash
pip install openpad
```

Run:

```bash
openpad
```

---

## ✨ Features

- 📁 Folder-based note organization
- 📝 Markdown support (headers, lists, code blocks)
- 🎨 12 built-in themes (Tokyo Night, Catppuccin, Gruvbox…)
- 🔍 Full-text search across all notes
- ⚡ Auto-save while typing
- 🧠 Syntax highlighting for 20+ languages
- 📅 Google Calendar integration (optional)
- 🪶 Lightweight (Textual-based, no Electron)
- 📦 Notes stored as plain Markdown files

---

## ⌨️ Key Bindings

| Key        | Action                    |
|------------|---------------------------|
| `n`        | New note                  |
| `ctrl+n`   | New folder                |
| `e`        | Toggle edit mode          |
| `ctrl+f`   | Search                    |
| `ctrl+t`   | Change theme              |
| `ctrl+c`   | Open calendar             |
| `d`        | Delete note               |
| `escape`   | Exit edit mode            |
| `q`        | Quit                      |

---

## 📂 Data Storage

Your data is stored locally:

| Path                    | Purpose                    |
|-------------------------|----------------------------|
| `~/.openpad/notes/`     | All notes                  |
| `~/.openpad/meta.json`  | Settings (theme, etc.)     |

---

## 📅 Google Calendar (Optional)

To enable calendar:

1. Get Google API credentials
2. Place file here:

```bash
~/.openpad/credentials.json
```

If not configured, OpenPad will still work normally.

---

## 🧪 First Run

OpenPad automatically creates sample notes to help you get started.

---

## 🧠 Why OpenPad?

- No setup complexity
- Works inside your existing terminal workflow
- Faster than GUI note apps
- Your notes are just `.md` files — no lock-in

---

## 💻 Requirements

- Python 3.10+
- Terminal with true color support
- Linux / macOS / Windows (WSL or Windows Terminal)

---

## 🪟 Windows Support

Works with:

- Windows Terminal (recommended)
- WSL (Ubuntu, etc.)

---

## 🛠 Development

Clone and run locally:

```bash
git clone <your-repo-url>
cd openpad
pip install -e .
openpad
```

---

## 🐛 Troubleshooting

### Colors look wrong

```bash
echo $TERM
# should be xterm-256color
```

### Permission issues

```bash
ls -la ~/.openpad/
```

---

## 📄 License

MIT License

---

Built with https://textual.textualize.io/