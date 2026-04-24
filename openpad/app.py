from textual.app import App, ComposeResult
from textual.widgets import (
    Static, Tree, TextArea, Input, Label, ListView, ListItem, ContentSwitcher
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from rich.syntax import Syntax
from rich.text import Text
from rich.console import Group
import re
import calendar
from datetime import datetime

def _truncate(text, max_len=13):
    return text if len(text) <= max_len else text[:max_len - 3] + "…"

session_log = []

from openpad.themes import THEMES, THEME_DESCRIPTIONS
from openpad.notes import (
    get_tree, read_note, write_note, delete_note,
    create_folder, delete_folder, search_notes,
    load_meta, save_meta, seed_sample_notes, rename_note
)

ASCII_ART = """
   █▀▀█ █▀▀█ █▀▀▀ █▀▀▄ █▀▀█ █▀▀█ █▀▀▄
   █  █ █▀▀▀ █▀▀▀ █  █ █▀▀▀ █▀▀█ █  █
   ▀▀▀▀ ▀    ▀▀▀▀ ▀  ▀ ▀    ▀  ▀ ▀▀▀▀
"""

# ─────────────────────────────────────────────
#  Calendar Modal
# ─────────────────────────────────────────────

class CalendarModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("left", "prev_month", "Prev Month"),
        Binding("right", "next_month", "Next Month"),
        Binding("up", "prev_day", "Prev Day"),
        Binding("down", "next_day", "Next Day"),
    ]

    def __init__(self, theme_name: str = "opencode"):
        super().__init__()
        self.theme_name = theme_name
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self.today_day = now.day
        self.today_month = now.month
        self.today_year = now.year
        self.selected_day = now.day
        self.events_by_day = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="cal-modal"):
            with Vertical(id="cal-left"):
                yield Static("", id="cal-header")
                yield Static("", id="cal-weekdays")
                yield Static("", id="cal-grid")
                yield Static("", id="cal-footer")
            with Vertical(id="cal-right"):
                yield Static("", id="cal-events-title")
                yield ScrollableContainer(
                    Static("", id="cal-events-body"),
                    id="cal-events-scroll"
                )

    def on_mount(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])

        modal = self.query_one("#cal-modal")
        modal.styles.background = t["bg_panel"]
        modal.styles.border = ("solid", t["border_active"])

        left = self.query_one("#cal-left")
        left.styles.background = t["bg_panel"]
        left.styles.border_right = ("solid", t["border"])
        left.styles.width = 36
        left.styles.padding = (1, 1)

        right = self.query_one("#cal-right")
        right.styles.background = t["bg"]
        right.styles.width = "1fr"
        right.styles.padding = (1, 2)

        scroll = self.query_one("#cal-events-scroll")
        scroll.styles.height = "1fr"
        scroll.styles.background = t["bg"]

        self._fetch_events()
        self._render_calendar()
        self._render_events()

    def _fetch_events(self):
        try:
            from openpad.calendar_api import get_events_for_month
            result = get_events_for_month(self.current_year, self.current_month)

            if "error" in result:
                self.events_by_day = {}
            else:
                self.events_by_day = result

        except Exception:
            self.events_by_day = {}

    def _render_calendar(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])
        month_name = datetime(self.current_year, self.current_month, 1).strftime("%B %Y")

        header = self.query_one("#cal-header")
        header.update(f"[bold {t['primary']}]{month_name:^32}[/]")

        weekdays = self.query_one("#cal-weekdays")
        weekdays.update(f"[dim] Mo  Tu  We  Th  Fr  Sa  Su[/dim]")

        from rich.text import Text as RichText
        from rich.console import Group as RichGroup

        cal = calendar.monthcalendar(self.current_year, self.current_month)
        rows = []

        for week in cal:
            row = RichText()
            for day in week:
                if day == 0:
                    row.append("    ")
                else:
                    has_events = day in self.events_by_day or str(day) in self.events_by_day
                    has_exam = has_events and any(
                        e.get("color") == "exam"
                        for e in (self.events_by_day.get(day) or self.events_by_day.get(str(day), []))
                    )
                    is_today = (
                        day == self.today_day
                        and self.current_month == self.today_month
                        and self.current_year == self.today_year
                    )
                    is_selected = day == self.selected_day

                    cell = f"[{day:2}]" if is_today else f" {day:2} "

                    if is_selected and is_today:
                        row.append(cell, style=f"bold {t['primary']}")
                    elif is_selected:
                        row.append(cell, style=f"bold {t['accent']}")
                    elif is_today:
                        row.append(cell, style=f"bold {t['primary']}")
                    elif has_exam:
                        row.append(cell, style=t["error"])
                    elif has_events:
                        row.append(cell, style=t["secondary"])
                    else:
                        row.append(cell, style=t["text"])
            rows.append(row)

        grid = self.query_one("#cal-grid")
        grid.update(RichGroup(*rows))

        footer = self.query_one("#cal-footer")
        today_str = datetime.now().strftime("%a %b %d")
        footer.update(f"\n[dim]Today: {today_str}[/dim]")

    def _render_events(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])
        sel = self.selected_day

        title_widget = self.query_one("#cal-events-title")
        try:
            day_name = datetime(self.current_year, self.current_month, sel).strftime("%A, %B %d")
        except ValueError:
            day_name = "—"
        title_widget.update(f"[bold {t['primary']}]{day_name}[/]\n")

        events = self.events_by_day.get(sel) or self.events_by_day.get(str(sel), [])
        body = self.query_one("#cal-events-body")

        if not events:
            body.update("[dim]No events for this day.\n\nIf calendar is not configured, add credentials.json to ~/.openpad/[/dim]")
            return

        lines = []
        for e in events:
            color = t["error"] if e.get("color") == "exam" else t["secondary"]
            title = e.get("title", "No title")
            time_str = e.get("time", "")
            lines.append(f"[{color}]●[/] [{t['text']}]{title}[/]")
            if time_str:
                lines.append(f"  [dim]{time_str}[/dim]")
            lines.append("")

        body.update("\n".join(lines))

    def action_prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        max_day = calendar.monthrange(self.current_year, self.current_month)[1]
        self.selected_day = min(self.selected_day, max_day)
        self._fetch_events()
        self._render_calendar()
        self._render_events()

    def action_next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        max_day = calendar.monthrange(self.current_year, self.current_month)[1]
        self.selected_day = min(self.selected_day, max_day)
        self._fetch_events()
        self._render_calendar()
        self._render_events()

    def action_prev_day(self):
        if self.selected_day > 1:
            self.selected_day -= 1
            self._render_calendar()
            self._render_events()

    def action_next_day(self):
        max_day = calendar.monthrange(self.current_year, self.current_month)[1]
        if self.selected_day < max_day:
            self.selected_day += 1
            self._render_calendar()
            self._render_events()

    def action_cancel(self):
        self.dismiss(None)


# ─────────────────────────────────────────────
#  Note Viewer
# ─────────────────────────────────────────────

class NoteViewer(ScrollableContainer):
    """Renders markdown with syntax-highlighted code blocks."""

    DEFAULT_CSS = """
    NoteViewer {
        width: 1fr;
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
        background: transparent;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_name = "opencode"
        self._static = Static("")

    def compose(self) -> ComposeResult:
        yield self._static

    def set_content(self, content: str, theme_name: str):
        self.theme_name = theme_name
        self._render_markdown(content)

    def _render_markdown(self, content: str):
        t = THEMES.get(self.theme_name, THEMES["opencode"])
        lines = content.split("\n")
        output_parts = []
        in_code = False
        code_lines = []
        code_lang = ""
        line_num = 1

        SYNTAX_THEME = "monokai"

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("```") and not in_code:
                in_code = True
                code_lang = line[3:].strip() or "text"
                code_lines = []
                i += 1
                continue
            elif line.startswith("```") and in_code:
                in_code = False
                lang_map = {
                    "js": "javascript", "py": "python",
                    "sh": "bash", "ts": "typescript",
                    "md": "markdown", "rb": "ruby",
                    "rs": "rust", "cs": "csharp",
                }
                lang = lang_map.get(code_lang.lower(), code_lang.lower())
                from rich.columns import Columns
                for code_line in code_lines:
                    num_text = Text(f"{line_num:>4}  ", style=f"dim {t['text']}")
                    syn = Syntax(
                        code_line, lang,
                        theme=SYNTAX_THEME,
                        line_numbers=False,
                        background_color=t["bg"],
                        indent_guides=False,
                        word_wrap=False,
                        padding=(0, 0),
                    )
                    output_parts.append(Columns([num_text, syn], padding=(0, 0)))
                    line_num += 1
                i += 1
                continue
            elif in_code:
                code_lines.append(line)
                i += 1
                continue
            else:
                output_parts.append(self._style_line(line, t, line_num))
                line_num += 1
                i += 1

        self._static.update(Group(*output_parts))

    def _style_line(self, line: str, t: dict, line_num: int) -> Text:
        prefix = Text(f"{line_num:>4}  ", style=f"dim {t['text']}")

        indent_len = len(line) - len(line.lstrip())
        indent = line[:indent_len]
        stripped = line.lstrip()

        content = Text(indent, style=t["text"])

        def inline(text: str) -> Text:
            result = Text()
            pattern = re.compile(r"(\*\*(.+?)\*\*|__(.+?)__|`([^`]+)`|\*(.+?)\*|_(.+?)_)")
            last = 0

            for m in pattern.finditer(text):
                result.append(text[last:m.start()], style=t["text"])
                full = m.group(0)

                if full.startswith("**") or full.startswith("__"):
                    inner = m.group(2) or m.group(3)
                    result.append(inner, style=f"bold {t['text']}")
                elif full.startswith("`"):
                    inner = m.group(4)
                    result.append(f"`{inner}`", style=t["syntax_str"])
                elif full.startswith("*") or full.startswith("_"):
                    inner = m.group(5) or m.group(6)
                    result.append(inner, style=f"italic {t['text']}")

                last = m.end()

            result.append(text[last:], style=t["text"])
            return result

        if stripped.startswith("# "):
            content.append(stripped[2:], style=f"bold {t['primary']}")
        elif stripped.startswith("## "):
            content.append(stripped[3:], style=f"bold {t['secondary']}")
        elif stripped.startswith("### "):
            content.append(stripped[4:], style=f"bold {t['accent']}")
        elif stripped.startswith("#### "):
            content.append(stripped[5:], style=t["accent"])
        elif stripped.startswith("> "):
            content.append(f"│ {stripped[2:]}", style=f"italic {t['text_muted']}")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            item = stripped[2:]

            if item.startswith("> "):
                content.append("• ", style=t["text"])
                content.append(f"│ {item[2:]}", style=f"italic {t['text_muted']}")
            else:
                content.append("• ", style=t["text"])
                content.append_text(inline(item))

        elif re.match(r"^\d+\. ", stripped):
            content.append_text(inline(stripped))
        elif stripped.startswith("---"):
            content.append("─" * 50, style=t["text_muted"])
        else:
            content.append_text(inline(stripped))

        result = Text()
        result.append_text(prefix)
        result.append_text(content)
        return result


# ─────────────────────────────────────────────
#  Theme Picker
# ─────────────────────────────────────────────

class ThemePicker(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, current_theme: str):
        super().__init__()
        self.active_pad_theme = current_theme
        self.theme_names = list(THEMES.keys())
        self.selected_idx = self.theme_names.index(current_theme) if current_theme in self.theme_names else 0

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-modal"):
            yield Label(" Themes", id="theme-title")
            yield Static("", id="theme-separator")
            with ScrollableContainer(id="theme-list-container"):
                yield ListView(id="theme-list")
            yield Static("", id="theme-footer")

    def on_mount(self):
        t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        self.query_one("#theme-modal").styles.background = t["bg_panel"]
        self.query_one("#theme-modal").styles.border = ("solid", t["border_active"])
        self.query_one("#theme-title").styles.color = t["primary"]
        self.query_one("#theme-footer").update("[dim]↑↓ navigate  enter select  esc close[/dim]")
        lv = self.query_one("#theme-list", ListView)
        for name in self.theme_names:
            desc = THEME_DESCRIPTIONS.get(name, "")
            item = ListItem(
                Static(f"  {'▶ ' if name == self.active_pad_theme else '  '}{name:<26} {desc}"),
                id=f"theme-{name}"
            )
            lv.append(item)
        lv.index = self.selected_idx

    def on_list_view_selected(self, event: ListView.Selected):
        name = event.item.id.replace("theme-", "")
        self.dismiss(name)

    def action_select(self):
        lv = self.query_one("#theme-list", ListView)
        if lv.index is not None:
            name = self.theme_names[lv.index]
            self.dismiss(name)

    def action_dismiss(self):
        self.dismiss(None)


# ─────────────────────────────────────────────
#  Input Modal
# ─────────────────────────────────────────────

class InputModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, prompt: str, placeholder: str = "", theme_name: str = "opencode"):
        super().__init__()
        self._prompt = prompt
        self._placeholder = placeholder
        self.theme_name = theme_name

    def compose(self) -> ComposeResult:
        with Vertical(id="input-modal"):
            yield Label(self._prompt, id="input-label")
            yield Input(placeholder=self._placeholder, id="modal-input")
            yield Label("[dim]enter confirm  esc cancel[/dim]", id="input-hint")

    def on_mount(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])

        modal = self.query_one("#input-modal")
        modal.styles.background = t["bg_panel"]
        modal.styles.border = ("solid", t["border_active"])

        self.query_one("#input-label").styles.color = t["primary"]
        self.query_one("#input-hint").styles.color = t["text_muted"]

        inp = self.query_one("#modal-input")
        inp.styles.background = t["bg"]
        inp.styles.color = t["text"]
        inp.styles.border = ("solid", t["border_active"])

        inp.focus()

    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value.strip())

    def action_cancel(self):
        self.dismiss(None)


# ─────────────────────────────────────────────
#  Confirm Modal
# ─────────────────────────────────────────────

class ConfirmModal(ModalScreen):
    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, message: str, theme_name: str = "opencode"):
        super().__init__()
        self._message = message
        self.theme_name = theme_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-modal"):
            yield Label(self._message, id="confirm-msg")
            yield Label("[dim]y confirm  n cancel[/dim]", id="confirm-hint")

    def on_mount(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])

        modal = self.query_one("#confirm-modal")
        modal.styles.background = t["bg_panel"]
        modal.styles.border = ("solid", t["border_active"])

        self.query_one("#confirm-msg").styles.color = t["primary"]
        self.query_one("#confirm-hint").styles.color = t["text_muted"]

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


# ─────────────────────────────────────────────
#  Search Modal
# ─────────────────────────────────────────────

class SearchModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, theme_name: str = "opencode"):
        super().__init__()
        self.theme_name = theme_name
        self._results = []
        self._search_version = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="search-modal"):
            yield Label(" Search Notes", id="search-title")
            yield Input(placeholder="Type to search...", id="search-input")
            with ScrollableContainer(id="search-results-container"):
                yield ListView(id="search-results")
            yield Label("[dim]enter open  esc cancel[/dim]", id="search-hint")

    def on_mount(self):
        self.query_one("#search-input").focus()

        t = THEMES.get(self.theme_name, THEMES["opencode"])

        modal = self.query_one("#search-modal")
        modal.styles.background = t["bg_panel"]
        modal.styles.border = ("solid", t["border_active"])

        self.query_one("#search-title").styles.color = t["primary"]
        self.query_one("#search-hint").styles.color = t["text_muted"]

        inp = self.query_one("#search-input")
        inp.styles.background = t["bg"]
        inp.styles.color = t["text"]
        inp.styles.border = ("solid", t["border_active"])

        self.query_one("#search-results-container").styles.background = t["bg_panel"]
        self.query_one("#search-input").focus()

    def on_input_changed(self, event: Input.Changed):
        self._search_version += 1
        version = self._search_version
        query = event.value.strip()
        self.set_timer(0.3, lambda: self._do_search(query, version))

    def _do_search(self, query: str, version: int):
        if version != self._search_version:
            return
        lv = self.query_one("#search-results", ListView)
        self._results = []
        lv._nodes._clear()
        lv.refresh()
        if query:
            self._results = search_notes(query)
            for folder, name, snippet in self._results[:20]:
                folder_label = f"{folder}/" if folder != "__root__" else ""
                lv.append(ListItem(
                    Static(f"  {folder_label}{name}\n  [dim]{snippet[:50]}[/dim]")
                ))

    def on_list_view_selected(self, event: ListView.Selected):
        lv = self.query_one("#search-results", ListView)
        idx = lv.index
        if idx is not None and idx < len(self._results):
            folder, name, _ = self._results[idx]
            self.dismiss((folder, name))

    def action_cancel(self):
        self.dismiss(None)


# ─────────────────────────────────────────────
#  Editor
# ─────────────────────────────────────────────

class OpenPadTextArea(TextArea):
    """Text editor that inserts spaces on Tab and exits edit mode when focus leaves."""

    BINDINGS = [
        Binding("tab", "insert_tab", "Insert Tab", show=False),
    ]

    def action_insert_tab(self):
        self.insert("    ")

    def on_blur(self) -> None:
        app = self.app
        if getattr(app, "edit_mode", False):
            app.call_later(app.action_view_mode)


# ─────────────────────────────────────────────
#  Main App
# ─────────────────────────────────────────────

class OpenPad(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    ModalScreen {
        align: center middle;
    }
    #header {
        height: 1;
        layout: horizontal;
        padding: 0 1;
    }
    #header-title {
        width: auto;
        content-align: left middle;
    }
    #header-right {
        width: 1fr;
        content-align: right middle;
        text-align: right;
    }
    #body {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: 24;
        border-right: solid #333333;
        overflow: hidden;
    }
    #editor-area {
        width: 1fr;
        height: 1fr;
    }
    #note-viewer {
        width: 1fr;
        height: 1fr;
    }
    #text-editor {
        width: 1fr;
        height: 1fr;
    }
    #statusbar {
        height: 1;
        layout: horizontal;
        padding: 0 1;
    }
    #status-left {
        width: 1fr;
        content-align: left middle;
    }
    #status-right {
        width: auto;
        content-align: right middle;
        text-align: right;
    }
    #theme-modal {
        width: 72;
        height: 20;
        border: solid #444444;
        padding: 1;
        align: center middle;
    }
    #theme-title {
        text-style: bold;
        padding-bottom: 1;
    }
    #theme-list-container {
        height: 14;
    }
    #theme-footer {
        padding-top: 1;
    }
    #input-modal {
        width: 50;
        height: 9;
        border: solid #444444;
        padding: 1 2;
        align: center middle;
    }
    #input-label {
        padding-bottom: 1;
        text-style: bold;
    }
    #input-hint {
        padding-top: 1;
    }
    #confirm-modal {
        width: 50;
        height: 7;
        border: solid #444444;
        padding: 1 2;
        align: center middle;
    }
    #confirm-msg {
        padding-bottom: 1;
        text-style: bold;
    }
    #search-modal {
        width: 64;
        height: 24;
        border: solid #444444;
        padding: 1 2;
        align: center middle;
    }
    #search-title {
        text-style: bold;
        padding-bottom: 1;
    }
    #search-results-container {
        height: 16;
    }
    #search-hint {
        padding-top: 1;
    }
    #cal-modal {
        width: 80;
        height: 28;
        border: solid #444444;
        align: center middle;
    }
    Tree {
        padding: 0;
        background: transparent;
    }
    Tree > .tree--cursor {
        background: #c4a882aa;
        color: #ffffff;
    }
    Tree > .tree--highlight {
        background: #c4a88255;
    }
    Tree > .tree--highlight-line {
        background: #c4a88222;
    }
    TextArea > .text-area--cursor {
        background: #c4a88299;
        color: #000000;
    }
    TextArea > .text-area--selection {
        background: #c4a88240;
    }
    TextArea > .text-area--scrollbar {
        background: transparent;
    }
    TextArea > .text-area--scrollbar-gutter {
        background: transparent;
    }
    """

    def on_text_area_changed(self, event: TextArea.Changed):
        if self.edit_mode and self.selected_note:
            ta = self.query_one("#text-editor", TextArea)
            write_note(self.selected_folder, self.selected_note, ta.text)
            note_entry = f"  ~ edited:  {self.selected_folder + '/' if self.selected_folder and self.selected_folder != '__root__' else ''}{self.selected_note}"
            if note_entry not in session_log:
                session_log.append(note_entry)

    BINDINGS = [
        Binding("n", "new_note", "New Note"),
        Binding("ctrl+n", "new_folder", "New Folder"),
        Binding("d", "delete_item", "Delete"),
        Binding("e", "toggle_edit", "Edit"),
        Binding("ctrl+f", "search", "Search"),
        Binding("ctrl+t", "open_theme_picker", "Theme"),
        Binding("ctrl+c", "open_calendar", "Calendar"),
        Binding("escape", "view_mode", "View"),
        Binding("q", "quit", "Quit"),
    ]

    edit_mode: reactive = reactive(False)
    selected_folder: str | None = None
    selected_note: str | None = None
    active_pad_theme: str = "opencode"

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Static("OpenPad", id="header-title")
            yield Static("", id="header-right")
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Tree("Notes", id="note-tree")
            with ContentSwitcher(id="editor-area", initial="note-viewer"):
                yield NoteViewer(id="note-viewer")
                yield OpenPadTextArea(id="text-editor")
        with Horizontal(id="statusbar"):
            yield Static("", id="status-left")
            yield Static("", id="status-right")

    def on_mount(self):
        seed_sample_notes()
        meta = load_meta()
        self.active_pad_theme = meta.get("theme", "opencode")
        self._apply_theme()
        self._rebuild_tree()
        ta = self.query_one("#text-editor", TextArea)
        ta.show_line_numbers = True
        ta.scroll_sensitivity_y = 0.1

    def on_unmount(self):
        # Print ASCII art in the current theme's primary color
        t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        primary = t.get("primary", "#c4a882")
        # Convert hex color to ANSI 24-bit escape sequence
        def hex_to_ansi(hex_color):
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 6:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                return f"\033[38;2;{r};{g};{b}m"
            return ""
        ansi_color = hex_to_ansi(primary)
        reset = "\033[0m"
        print(f"{ansi_color}{ASCII_ART}{reset}")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        # All additional text in theme color
        print(f"{ansi_color}  Session ended:{reset} {now}")
        if session_log:
            print(f"{ansi_color}  Summary:{reset}")
            for entry in session_log:
                print(entry)
        else:
            print(f"{ansi_color}  No changes made this session.{reset}")

    def _apply_theme(self):
        t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        self.screen.styles.background = t["bg"]

        header = self.query_one("#header")
        header.styles.background = t["bg_panel"]
        header.styles.color = t["text"]

        title = self.query_one("#header-title")
        title.styles.color = t["primary"]
        title.styles.text_style = "bold"
        title.update("OpenPad")

        right = self.query_one("#header-right")
        right.styles.color = t["text_muted"]
        right.update(f"theme: {self.active_pad_theme}")

        sidebar = self.query_one("#sidebar")
        sidebar.styles.background = t["bg_panel"]
        sidebar.styles.border_right = ("solid", t["border"])

        editor_area = self.query_one("#editor-area")
        editor_area.styles.background = t["bg"]

        statusbar = self.query_one("#statusbar")
        statusbar.styles.background = t["bg_panel"]
        statusbar.styles.color = t["text_muted"]

        tree = self.query_one("#note-tree", Tree)
        tree.styles.background = t["bg_panel"]
        tree.styles.color = t["text"]
        tree.styles.padding = (0, 1)

        viewer = self.query_one("#note-viewer", NoteViewer)
        viewer.styles.background = t["bg"]

        ta = self.query_one("#text-editor", TextArea)
        ta.styles.background = t["bg"]
        ta.styles.color = t["text"]
        ta.styles.border = ("solid", t["border_active"])
        ta.styles.scrollbar_color = t["primary"]
        ta.styles.scrollbar_background = t["bg_panel"]
        ta.styles.scrollbar_color_hover = t["accent"]

        self._update_status()

        if self.selected_note:
            self._load_note_view()

    def _update_status(self):
        t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        left = self.query_one("#status-left")
        right = self.query_one("#status-right")

        if self.selected_note:
            folder_label = f"{self.selected_folder}/" if self.selected_folder and self.selected_folder != "__root__" else ""
            note_label = f"{folder_label}{self.selected_note}"
            mode = "EDIT" if self.edit_mode else "VIEW"
            left.update(note_label)
            right.update(f"{mode}")
        else:
            left.update("No note selected")
            right.update("")

        left.styles.color = t["primary"] if self.selected_note else t["text_muted"]
        right.styles.color = t["text_muted"]

    def _rebuild_tree(self):
        tree = self.query_one("#note-tree", Tree)
        tree.clear()
        tree.root.expand()

        data = get_tree()
        for folder_data in data:
            fname = folder_data["name"]
            if fname == "__root__":
                for note in folder_data["notes"]:
                    tree.root.add_leaf(_truncate(note), data={"folder": None, "note": note})
            else:
                node = tree.root.add(_truncate(fname), data={"folder": fname, "note": None})
                for note in folder_data["notes"]:
                    node.add_leaf(_truncate(note), data={"folder": fname, "note": note})

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted):
        data = event.node.data
        if data and data.get("note"):
            self.selected_folder = data["folder"]
            self.selected_note = data["note"]
            self._edit_original_note_name = data["note"]
            self.edit_mode = False
            self._load_note_view()
            self._update_status()

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        data = event.node.data
        if data and data.get("note"):
            self.selected_folder = data["folder"]
            self.selected_note = data["note"]
            self._edit_original_note_name = data["note"]
            self.edit_mode = False
            self._load_note_view()
            self._update_status()

    def _load_note_view(self):
        content = read_note(self.selected_folder, self.selected_note)
        switcher = self.query_one("#editor-area", ContentSwitcher)

        if self.edit_mode:
            switcher.current = "text-editor"
            ta = self.query_one("#text-editor", TextArea)
            ta.load_text(content)
            ta.read_only = False
            ta.focus()
        else:
            viewer = self.query_one("#note-viewer", NoteViewer)
            viewer.set_content(content, self.active_pad_theme)
            switcher.current = "note-viewer"

    def _save_and_rename(self):
        """Save current note and rename file if first line changed."""
        if not self.selected_note:
            return
        ta = self.query_one("#text-editor", TextArea)
        content = ta.text
        old_name = getattr(self, "_edit_original_note_name", self.selected_note)

        first_line = content.split("\n")[0]
        if first_line.startswith("# "):
            new_name = first_line[2:].strip()
        else:
            new_name = old_name

        if new_name and new_name != old_name:
            if rename_note(self.selected_folder, old_name, new_name):
                self.selected_note = new_name
                session_log.append(f"  * renamed: {old_name} → {new_name}")

        write_note(self.selected_folder, self.selected_note, content)

    def action_toggle_edit(self):
        if not self.selected_note:
            return
        if self.edit_mode:
            self._save_and_rename()
            self.edit_mode = False
            self._rebuild_tree()
        else:
            self._edit_original_note_name = self.selected_note
            self.edit_mode = True
        self._load_note_view()
        self._update_status()

    def action_view_mode(self):
        if self.edit_mode:
            self._save_and_rename()
            self.edit_mode = False
            self._rebuild_tree()
            self._load_note_view()
            self._update_status()

    def action_new_note(self):
        def handle(name):
            if not name:
                return
            folder = self.selected_folder if self.selected_folder else None
            write_note(folder, name, f"# {name}\n\n")
            self._rebuild_tree()
            self.selected_note = name
            self._edit_original_note_name = name
            self.edit_mode = True
            self._load_note_view()
            self._update_status()
            folder_label = f"{folder}/" if folder and folder != "__root__" else ""
            session_log.append(f"  + created note:  {folder_label}{name}")
        self.push_screen(InputModal(" New Note", "Note name...", self.active_pad_theme), handle)

    def action_new_folder(self):
        def handle(name):
            if not name:
                return
            create_folder(name)
            self._rebuild_tree()
            session_log.append(f"  + created folder: {name}")
        self.push_screen(InputModal(" New Folder", "Folder name...", self.active_pad_theme), handle)

    def action_delete_item(self):
        if not self.selected_note:
            return
        msg = f"Delete '{self.selected_note}'? (y/n)"
        def handle(confirmed):
            if confirmed:
                folder_label = f"{self.selected_folder}/" if self.selected_folder and self.selected_folder != "__root__" else ""
                session_log.append(f"  - deleted note:  {folder_label}{self.selected_note}")
                delete_note(self.selected_folder, self.selected_note)
                self.selected_note = None
                self.selected_folder = None
                self.edit_mode = False
                self._rebuild_tree()
                switcher = self.query_one("#editor-area", ContentSwitcher)
                switcher.current = "note-viewer"
                viewer = self.query_one("#note-viewer", NoteViewer)
                viewer.set_content("", self.active_pad_theme)
                self._update_status()
        self.push_screen(ConfirmModal(msg, self.active_pad_theme), handle)

    def action_search(self):
        def handle(result):
            if result:
                folder, name = result
                self.selected_folder = folder
                self.selected_note = name
                self.edit_mode = False
                self._load_note_view()
                self._update_status()
        self.push_screen(SearchModal(self.active_pad_theme), handle)

    def action_quit(self):
        if self.edit_mode and self.selected_note:
            self._save_and_rename()
        self.exit()

    def action_open_theme_picker(self):
        def handle(theme_name):
            if theme_name:
                self.active_pad_theme = theme_name
                meta = load_meta()
                meta["theme"] = theme_name
                save_meta(meta)
                self._apply_theme()
                self._rebuild_tree()
        self.push_screen(ThemePicker(self.active_pad_theme), handle)

    def action_open_calendar(self):
        self.push_screen(CalendarModal(self.active_pad_theme))

    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if val == "/theme":
            event.stop()
            self.action_open_theme_picker()



CSS_EXTRA = """
ListView {
    background: transparent;
    border: none;
    padding: 0;
}
ListItem {
    background: transparent;
    padding: 0;
}
ListItem:hover {
    background: #ffffff10;
}
ListItem.--highlight {
    background: #ffffff18;
}
Input {
    border: solid #444444;
    background: #111111;
    color: #e0e0e0;
    padding: 0 1;
    height: 3;
}
"""


def main():
    app = OpenPad()
    app.CSS += CSS_EXTRA
    app.run()


if __name__ == "__main__":
    main()