import time
from pathlib import Path
from textual.app import App, ComposeResult, ScreenStackError
from textual import events
from textual.widgets import (
    Static, Tree, TextArea, Input, Label, ListView, ListItem, ContentSwitcher, Button
)
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual.strip import Strip
from textual.widgets._tree import line_pad, TOGGLE_STYLE
from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from rich.console import Group
from typing import cast
import re
import calendar
from datetime import datetime

session_log = []

from openpad.themes import THEMES, THEME_DESCRIPTIONS
from openpad.system_theme import detect_system_theme
from openpad.notes import (
    get_tree, read_note, write_note, delete_note,
    create_folder, delete_folder, search_notes,
    load_meta, save_meta, seed_sample_notes, rename_note,
    get_all_folders, move_note, move_folder,
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
        Binding("escape", "cancel", "Close", priority=True),
        Binding("shift+left", "prev_month", "Prev Month", priority=True),
        Binding("shift+right", "next_month", "Next Month", priority=True),
        Binding("left", "prev_day", "Prev Day", priority=True),
        Binding("right", "next_day", "Next Day", priority=True),
        Binding("up", "prev_week", "Prev Week", priority=True),
        Binding("down", "next_week", "Next Week", priority=True),
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
        self.credentials_found = False
        self.credentials_error = None
        self._credential_check_timer = None

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
        scroll.styles.scrollbar_color = t["primary"]
        scroll.styles.scrollbar_color_hover = t["primary"]
        scroll.styles.scrollbar_color_active = t["primary"]
        scroll.styles.scrollbar_background = t["bg_panel"]
        scroll.styles.scrollbar_background_hover = t["bg_panel"]
        scroll.styles.scrollbar_background_active = t["bg_panel"]

        # Start checking for credentials periodically
        self._check_for_credentials()
        self._render_calendar()
        self._render_events()

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#cal-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_cancel()

    def _fetch_events(self):
        """Fetch events for the current month and update self.events_by_day."""
        try:
            from openpad.calendar_api import get_events_for_month
            result = get_events_for_month(self.current_year, self.current_month)
            if "error" in result:
                self.events_by_day = {}
            else:
                self.events_by_day = result
        except Exception:
            self.events_by_day = {}

    def _schedule_credential_check(self):
        """Schedule the next credential check."""
        if self._credential_check_timer:
            self._credential_check_timer.stop()
        self._credential_check_timer = self.set_timer(2.0, self._check_for_credentials)

    def _check_for_credentials(self):
        """Check for credentials periodically and fetch events when available."""
        if self._credential_check_timer:
            self._credential_check_timer.stop()
            self._credential_check_timer = None

        try:
            from openpad.calendar_api import get_events_for_month
            result = get_events_for_month(self.current_year, self.current_month)

            if "error" in result:
                self.credentials_found = False
                self.credentials_error = result["error"]
                self.events_by_day = {}
            else:
                self.credentials_found = True
                self.credentials_error = None
                self.events_by_day = result

        except Exception as e:
            self.credentials_found = False
            self.credentials_error = str(e)
            self.events_by_day = {}

        self._render_calendar()
        self._render_events()

        # Keep polling only while credentials are still missing
        if not self.credentials_found:
            self._schedule_credential_check()

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

                    cell = f" {day:2} "

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

        body = self.query_one("#cal-events-body")

        # Show different messages based on credential status
        if not self.credentials_found:
            if self.credentials_error:
                body.update(f"[dim]{self.credentials_error}[/dim]\n\n[dim]Checking for credentials...[/dim]")
            else:
                body.update("[dim]Waiting for calendar credentials...\n\nIf calendar is not configured, add credentials.json to ~/.openpad/[/dim]")
            return

        events = self.events_by_day.get(sel) or self.events_by_day.get(str(sel), [])

        if not events:
            body.update("[dim]No events for this day.[/dim]")
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
        else:
            # Wrap to previous month
            if self.current_month == 1:
                self.current_month = 12
                self.current_year -= 1
            else:
                self.current_month -= 1
            self.selected_day = calendar.monthrange(self.current_year, self.current_month)[1]
            self._fetch_events()
        self._render_calendar()
        self._render_events()

    def action_next_day(self):
        max_day = calendar.monthrange(self.current_year, self.current_month)[1]
        if self.selected_day < max_day:
            self.selected_day += 1
        else:
            # Wrap to next month
            if self.current_month == 12:
                self.current_month = 1
                self.current_year += 1
            else:
                self.current_month += 1
            self.selected_day = 1
            self._fetch_events()
        self._render_calendar()
        self._render_events()

    def action_prev_week(self):
        new_day = self.selected_day - 7
        if new_day < 1:
            if self.current_month == 1:
                self.current_month = 12
                self.current_year -= 1
            else:
                self.current_month -= 1
            max_day = calendar.monthrange(self.current_year, self.current_month)[1]
            self.selected_day = max_day + new_day
            self._fetch_events()
        else:
            self.selected_day = new_day
        self._render_calendar()
        self._render_events()

    def action_next_week(self):
        max_day = calendar.monthrange(self.current_year, self.current_month)[1]
        new_day = self.selected_day + 7
        if new_day > max_day:
            if self.current_month == 12:
                self.current_month = 1
                self.current_year += 1
            else:
                self.current_month += 1
            self.selected_day = new_day - max_day
            self._fetch_events()
        else:
            self.selected_day = new_day
        self._render_calendar()
        self._render_events()

    def on_click(self, event: events.Click) -> None:
        """Handle clicks on the calendar grid to select a day."""
        try:
            grid = self.query_one("#cal-grid")
        except Exception:
            return

        # Get click position relative to the grid widget
        region = grid.content_region
        rel_x = event.screen_x - region.x
        rel_y = event.screen_y - region.y

        if rel_x < 0 or rel_y < 0:
            return

        # Each cell is exactly 4 chars wide (" DD "), 7 columns
        col = rel_x // 4
        row = rel_y

        if col > 6:
            return

        cal = calendar.monthcalendar(self.current_year, self.current_month)
        if row >= len(cal):
            return

        day = cal[row][col]
        if day == 0:
            return

        self.selected_day = day
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
        padding: 1;
        overflow-y: auto;
        background: transparent;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_name = "opencode"
        self._static = Static("")
        self._line_map: list[int] = []  # visual line index → source line index
        self._content: str = ""
        self._highlight_line: int | None = None
        self._highlight_col: int | None = None
        self._highlight_len: int = 0
        self._highlight_timer = None

    def compose(self) -> ComposeResult:
        yield self._static

    def on_click(self, event: events.Click):
        if event.chain >= 2:
            self.app.action_toggle_edit()

    def set_content(self, content: str, theme_name: str):
        self.theme_name = theme_name
        self._content = content
        self._render_markdown(content)

    def _render_markdown(self, content: str):
        t = THEMES.get(self.theme_name, THEMES["opencode"])
        lines = content.split("\n")
        in_code = False
        code_lines = []
        code_line_source_indices = []
        code_lang = ""
        line_num = 1

        num_width = max(3, len(str(len(lines))))
        gutter_width = num_width + 2

        from rich.table import Table
        table = Table(show_header=False, show_edge=False, padding=0, expand=True, box=None)
        table.add_column("gutter", no_wrap=True, width=gutter_width)
        table.add_column("content", overflow="fold", min_width=0, ratio=1)

        SYNTAX_THEME = "monokai"

        # Track which source line index each table row came from
        row_source: list[int] = []

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("```") and not in_code:
                in_code = True
                code_lang = line[3:].strip() or "text"
                code_lines = []
                code_line_source_indices = []
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
                for ci, code_line in enumerate(code_lines):
                    num_text = Text(f"{line_num:>{num_width}}  ", style=f"dim {t['text']}")
                    source_idx = code_line_source_indices[ci]
                    is_highlight_line = (
                        self._highlight_line is not None
                        and source_idx == self._highlight_line
                        and self._highlight_col is not None
                        and self._highlight_len > 0
                    )
                    if is_highlight_line:
                        # Use Pygments lexer directly to build a Rich Text with syntax
                        # colours, then overlay the search highlight on top.
                        try:
                            from pygments.lexers import get_lexer_by_name, TextLexer
                            from pygments.token import Token
                            from pygments.styles import get_style_by_name
                            try:
                                lexer = get_lexer_by_name(lang, stripnl=False)
                            except Exception:
                                lexer = TextLexer()
                            code_text = Text(no_wrap=True)
                            for ttype, value in lexer.get_tokens(code_line):
                                # Map token type to a colour via the Syntax theme
                                syn_obj = Syntax("", lang, theme=SYNTAX_THEME)
                                style_str = t["text"]
                                try:
                                    hl_theme = syn_obj._theme  # rich internal
                                    token_style = hl_theme.get_style_for_token(ttype)
                                    parts = []
                                    if token_style.color:
                                        parts.append(f"#{token_style.color}")
                                    if token_style.bold:
                                        parts.append("bold")
                                    if token_style.italic:
                                        parts.append("italic")
                                    if parts:
                                        style_str = " ".join(parts)
                                except Exception:
                                    pass
                                code_text.append(value.rstrip("\n"), style=style_str)
                        except Exception:
                            code_text = Text(code_line, no_wrap=True)
                        # Overlay highlight
                        col = self._highlight_col
                        end = min(col + self._highlight_len, len(code_line))
                        if col < len(code_line):
                            code_text.stylize("bold reverse yellow", col, end)
                        table.add_row(num_text, code_text)
                    else:
                        syn = Syntax(
                            code_line, lang,
                            theme=SYNTAX_THEME,
                            line_numbers=False,
                            background_color=t["bg"],
                            indent_guides=False,
                            word_wrap=True,
                            padding=(0, 0),
                        )
                        table.add_row(num_text, syn)
                    row_source.append(source_idx)
                    line_num += 1
                i += 1
                continue
            elif in_code:
                code_lines.append(line)
                code_line_source_indices.append(i)
                i += 1
                continue
            else:
                prefix, styled = self._style_line(line, t, line_num, num_width, i)
                table.add_row(prefix, styled)
                row_source.append(i)
                line_num += 1
                i += 1

        self._static.update(table)

        # _line_map: row index → source line index (one entry per source line).
        # scroll_y in a ScrollableContainer with a Rich Table counts TABLE ROWS,
        # not visual cells — each table row is one source line regardless of wrap.
        # So _line_map[int(scroll_y)] gives the exact source line at that position.
        self._line_map = row_source

    def highlight_match(self, line: int, col: int, length: int):
        """Temporarily highlight a search match, then clear after 1.5s."""
        if self._highlight_timer is not None:
            self._highlight_timer.stop()
        self._highlight_line = line
        self._highlight_col = col
        self._highlight_len = length
        self.set_content(self._content, self.theme_name)
        self._highlight_timer = self.set_timer(1.5, self._clear_highlight)

    def _clear_highlight(self):
        self._highlight_line = None
        self._highlight_col = None
        self._highlight_len = 0
        self._highlight_timer = None
        self.set_content(self._content, self.theme_name)

    def _style_line(self, line: str, t: dict, line_num: int, num_width: int = 3, source_index: int = -1) -> tuple[Text, Text]:
        prefix = Text(f"{line_num:>{num_width}}  ", style=f"dim {t['text']}")

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

        # Apply temporary search highlight if this is the target line
        if (self._highlight_line is not None
                and source_index == self._highlight_line
                and self._highlight_col is not None
                and self._highlight_len > 0):
            col = self._highlight_col
            length = self._highlight_len
            # Work on the plain string to find highlight bounds within content
            plain = content.plain
            if col < len(plain):
                end = min(col + length, len(plain))
                content.stylize("bold reverse yellow", col, end)

        return prefix, content


# ─────────────────────────────────────────────
#  Move Modal
# ─────────────────────────────────────────────

_MOVE_MODAL_CANCEL = object()

class MoveModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("up", "cursor_up", "", show=False, priority=True),
        Binding("down", "cursor_down", "", show=False, priority=True),
    ]

    def __init__(self, item_label: str, theme_name: str = "opencode"):
        super().__init__()
        self._item_label = item_label
        self.theme_name = theme_name
        self._folders: list[str | None] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="move-modal"):
            yield Label("", id="move-title")
            yield Static("", id="move-separator")
            with ScrollableContainer(id="move-list-container"):
                yield ListView(id="move-list")
            yield Label("[dim]↑↓ navigate  enter select  esc cancel[/dim]", id="move-footer")

    def on_mount(self):
        t = THEMES.get(self.theme_name, THEMES["opencode"])

        modal = self.query_one("#move-modal")
        modal.styles.background = t["bg_panel"]
        modal.styles.border = ("solid", t["border_active"])

        title = self.query_one("#move-title")
        title.update(f" Move  [bold]{self._item_label}[/bold]  →")
        title.styles.color = t["primary"]

        self.query_one("#move-footer").styles.color = t["text_muted"]
        self.query_one("#move-list-container").styles.background = t["bg_panel"]
        self.query_one("#move-list-container").styles.scrollbar_color = t["primary"]
        self.query_one("#move-list-container").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#move-list-container").styles.scrollbar_color_active = t["primary"]
        self.query_one("#move-list-container").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#move-list-container").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#move-list-container").styles.scrollbar_background_active = t["bg_panel"]
        self.query_one("#move-list").styles.scrollbar_color = t["primary"]
        self.query_one("#move-list").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#move-list").styles.scrollbar_color_active = t["primary"]
        self.query_one("#move-list").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#move-list").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#move-list").styles.scrollbar_background_active = t["bg_panel"]

        self._folders = get_all_folders()
        lv = self.query_one("#move-list", ListView)
        for folder in self._folders:
            display = "[dim]/ (root)[/dim]" if folder is None else f"[dim]/[/dim] {folder}"
            lv.append(ListItem(Static(f"  {display}")))

        lv.focus()

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#move-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_cancel()

    def on_list_view_selected(self, event: ListView.Selected):
        lv = self.query_one("#move-list", ListView)
        idx = lv.index
        if idx is not None and idx < len(self._folders):
            self.dismiss(self._folders[idx])

    def action_select(self):
        lv = self.query_one("#move-list", ListView)
        if lv.index is not None and lv.index < len(self._folders):
            self.dismiss(self._folders[lv.index])

    def action_cursor_up(self):
        lv = self.query_one("#move-list", ListView)
        if lv.index is not None and lv.index > 0:
            lv.index -= 1

    def action_cursor_down(self):
        lv = self.query_one("#move-list", ListView)
        if lv.index is not None and lv.index < len(self._folders) - 1:
            lv.index += 1

    def action_cancel(self):
        self.dismiss(_MOVE_MODAL_CANCEL)


# ─────────────────────────────────────────────
#  Theme Picker
# ─────────────────────────────────────────────

class ThemePicker(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "select", "Select"),
        Binding("up", "cursor_up", "", show=False, priority=True),
        Binding("down", "cursor_down", "", show=False, priority=True),
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

    def _refresh_arrow(self):
        lv = self.query_one("#theme-list", ListView)
        for i, item in enumerate(lv.children):
            name = self.theme_names[i]
            desc = THEME_DESCRIPTIONS.get(name, "")
            static = item.children[0]
            static.update(f"  {'▶ ' if i == lv.index else '  '}{name:<26} {desc}")

    def on_mount(self):
        t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        self.query_one("#theme-modal").styles.background = t["bg_panel"]
        self.query_one("#theme-modal").styles.border = ("solid", t["border_active"])
        self.query_one("#theme-title").styles.color = t["primary"]
        self.query_one("#theme-list-container").styles.scrollbar_color = t["primary"]
        self.query_one("#theme-list-container").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#theme-list-container").styles.scrollbar_color_active = t["primary"]
        self.query_one("#theme-list-container").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#theme-list-container").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#theme-list-container").styles.scrollbar_background_active = t["bg_panel"]
        self.query_one("#theme-list").styles.scrollbar_color = t["primary"]
        self.query_one("#theme-list").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#theme-list").styles.scrollbar_color_active = t["primary"]
        self.query_one("#theme-list").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#theme-list").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#theme-list").styles.scrollbar_background_active = t["bg_panel"]
        self.query_one("#theme-footer").update("Restart the app for the theme to fully apply")
        self.query_one("#theme-footer").styles.color = t["error"]
        lv = self.query_one("#theme-list", ListView)
        for name in self.theme_names:
            item = ListItem(Static(""), id=f"theme-{name}")
            lv.append(item)
        lv.index = self.selected_idx
        self._refresh_arrow()

    def on_list_view_highlighted(self, event: ListView.Highlighted):
        self._refresh_arrow()

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#theme-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_dismiss()

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

    def action_cursor_up(self):
        lv = self.query_one("#theme-list", ListView)
        if lv.index is not None and lv.index > 0:
            lv.index -= 1

    def action_cursor_down(self):
        lv = self.query_one("#theme-list", ListView)
        if lv.index is not None and lv.index < len(self.theme_names) - 1:
            lv.index += 1


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

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#input-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_cancel()

    def on_input_submitted(self, event: Input.Submitted):
        event.stop()
        try:
            self.dismiss(event.value.strip())
        except ScreenStackError:
            pass

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

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#confirm-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_cancel()

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
        self._current_query = ""

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
        self.query_one("#search-results-container").styles.scrollbar_color = t["primary"]
        self.query_one("#search-results-container").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#search-results-container").styles.scrollbar_color_active = t["primary"]
        self.query_one("#search-results-container").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#search-results-container").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#search-results-container").styles.scrollbar_background_active = t["bg_panel"]
        self.query_one("#search-results").styles.scrollbar_color = t["primary"]
        self.query_one("#search-results").styles.scrollbar_color_hover = t["primary"]
        self.query_one("#search-results").styles.scrollbar_color_active = t["primary"]
        self.query_one("#search-results").styles.scrollbar_background = t["bg_panel"]
        self.query_one("#search-results").styles.scrollbar_background_hover = t["bg_panel"]
        self.query_one("#search-results").styles.scrollbar_background_active = t["bg_panel"]
        self.query_one("#search-input").focus()

    def on_click(self, event: events.Click) -> None:
        modal = self.query_one("#search-modal")
        if event.widget is not modal and modal not in event.widget.ancestors:
            self.action_cancel()

    def on_input_changed(self, event: Input.Changed):
        self._search_version += 1
        version = self._search_version
        query = event.value.strip()
        self._current_query = query
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
            for folder, name, snippet, line, col in self._results[:20]:
                folder_label = f"{folder}/" if folder != "__root__" else ""
                lv.append(ListItem(
                    Static(f"  {folder_label}{name}\n  [dim]{snippet[:50]}[/dim]")
                ))

    def on_list_view_selected(self, event: ListView.Selected):
        lv = self.query_one("#search-results", ListView)
        idx = lv.index
        if idx is not None and idx < len(self._results):
            folder, name, snippet, line, col = self._results[idx]
            self.dismiss((folder, name, line, col, len(self._current_query)))

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


class NoteTree(Tree):
    """Tree with 1-space indentation per depth level."""

    def _render_line(self, y: int, x1: int, x2: int, base_style: Style) -> Strip:
        tree_lines = self._tree_lines
        width = self.size.width

        if y >= len(tree_lines):
            return Strip.blank(width, base_style)

        line = tree_lines[y]

        is_hover = self.hover_line >= 0 and any(node._hover for node in line.path)

        cache_key = (
            y,
            is_hover,
            width,
            self._updates,
            self._pseudo_class_state,
            tuple(node._updates for node in line.path),
        )
        if cache_key in self._line_cache:
            strip = self._line_cache[cache_key]
        else:
            base_hidden = self.get_component_styles("tree--guides").color.a == 0
            hover_hidden = self.get_component_styles("tree--guides-hover").color.a == 0
            selected_hidden = (
                self.get_component_styles("tree--guides-selected").color.a == 0
            )

            base_guide_style = self.get_component_rich_style(
                "tree--guides", partial=True
            )
            guide_hover_style = base_guide_style + self.get_component_rich_style(
                "tree--guides-hover", partial=True
            )
            guide_selected_style = base_guide_style + self.get_component_rich_style(
                "tree--guides-selected", partial=True
            )

            hover = line.path[0]._hover
            selected = line.path[0]._selected and self.has_focus

            def get_guides(style: Style, hidden: bool) -> tuple[str, str, str, str]:
                if self.show_guides and not hidden:
                    lines = self.LINES["default"]
                    if style.bold:
                        lines = self.LINES["bold"]
                    elif style.underline2:
                        lines = self.LINES["double"]
                else:
                    lines = (" ", " ", " ", " ")

                guide_depth = max(0, self.guide_depth - 2)
                guide_lines = tuple(
                    characters[0] + characters[-1] * guide_depth
                    for characters in lines
                )
                return cast("tuple[str, str, str, str]", guide_lines)

            if is_hover:
                line_style = self.get_component_rich_style("tree--highlight-line")
            else:
                line_style = base_style

            line_style += Style(meta={"line": y})

            guides = Text(style=line_style)
            guides_append = guides.append

            guide_style = base_guide_style

            hidden = True
            for i, node in enumerate(line.path[1:]):
                hidden = base_hidden
                if hover:
                    hidden = hover_hidden
                if selected:
                    hidden = selected_hidden

                if i == 0:
                    hidden = True

                space, vertical, _, _ = get_guides(guide_style, hidden)
                guide = space if node.is_last else vertical
                if node != line.path[-1]:
                    guides_append(guide, style=guide_style)
                hover = hover or node._hover
                selected = (selected or node._selected) and self.has_focus

            if len(line.path) > 1:
                space_char, vertical_char, terminator, cross = get_guides(guide_style, hidden)
                if line.last:
                    guides.append(terminator, style=guide_style)
                else:
                    guides.append(vertical_char, style=guide_style)

            label_style = self.get_component_rich_style("tree--label", partial=True)
            if self.hover_line == y:
                label_style += self.get_component_rich_style(
                    "tree--highlight", partial=True
                )
            if self.cursor_line == y:
                label_style += self.get_component_rich_style(
                    "tree--cursor", partial=False
                )

            label = self.render_label(line.path[-1], line_style, label_style).copy()
            label.stylize(Style(meta={"node": line.node._id}))
            guides.append(label)

            segments = list(guides.render(self.app.console))
            pad_width = max(self.virtual_size.width, width)
            segments = line_pad(segments, 0, pad_width - guides.cell_len, line_style)
            strip = self._line_cache[cache_key] = Strip(segments)

        strip = strip.crop(x1, x2)
        return strip

    def render_label(self, node, base_style, style):
        node_label = node._label.copy()
        node_label.stylize(style)

        if node._allow_expand:
            icon = self.ICON_NODE_EXPANDED if node.is_expanded else self.ICON_NODE
            prefix = (icon, base_style + TOGGLE_STYLE)
        else:
            pad = " " * Text(self.ICON_NODE, no_wrap=True).cell_len
            prefix = (pad, base_style)

        text = Text.assemble(prefix, node_label)
        return text


# ─────────────────────────────────────────────
#  Main App
# ─────────────────────────────────────────────

class OpenPad(App):
    CSS = """
    Screen {
        layout: vertical;
        height: 100%;
        padding: 0;
        margin: 0;
        border: none;
    }
    ModalScreen {
        align: center middle;
    }
    #body {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: auto;
        max-width: 45;
        overflow: hidden;
        background: #0d0d0d;
    }
    #note-tree {
        scrollbar-size-vertical: 0;
        scrollbar-size-horizontal: 0;
    }
    #sidebar > * {
        background: transparent;
    }
    #editor-area {
        width: 1fr;
        height: 1fr;
    }
    #tab-bar {
        width: 1fr;
        height: auto;
        dock: top;
        overflow-x: hidden;
        overflow-y: hidden;
    }
    #tab-bar Button.scroll-arrow {
        min-width: 0;
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 1;
        border: none;
        background: transparent;
        color: #888;
    }
    #tab-bar Button.scroll-arrow:hover,
    #tab-bar Button.scroll-arrow:focus {
        background: transparent;
        border: none;
        color: #888;
    }
    #tab-bar Button {
        min-width: 0;
        width: auto;
        height: auto;
        margin: 0 1 0 0;
        padding: 0 2;
        border: none;
        background: transparent;
    }
    #tab-bar Button.tab {
        color: #888;
    }
    #tab-bar Button.tab.active {
        color: #fff;
        text-style: bold;
    }
    #tab-bar Button.tab-close {
        color: #888;
        padding: 0;
        min-width: 1;
    }
    #tab-bar Static.tab-sep {
        color: #444;
        margin: 0 1;
        min-width: 1;
        width: auto;
    }
    #editor-content {
        width: 1fr;
        height: 1fr;
    }
    #note-viewer {
        width: 1fr;
        height: 1fr;
        scrollbar-size-horizontal: 0;
    }
    #text-editor {
        width: 1fr;
        height: 1fr;
    }
    #statusbar {
        height: 1;
        layout: horizontal;
    }
    #status-content {
        width: 1fr;
    }
    #theme-modal {
        width: 72;
        height: 23;
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
        text-align: center;
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
    #move-modal {
        width: 52;
        height: 22;
        border: solid #444444;
        padding: 1 2;
        align: center middle;
    }
    #move-title {
        text-style: bold;
        padding-bottom: 1;
    }
    #move-list-container {
        height: 14;
    }
    #move-footer {
        padding-top: 1;
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
    TextArea {
        scrollbar-size-horizontal: 0;
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
        self._update_status()

    BINDINGS = [
        Binding("n", "new_item", "New"),
        Binding("d", "delete_item", "Delete"),
        Binding("ctrl+f", "search", "Search"),
        Binding("ctrl+m", "move_item", "Move"),
        Binding("ctrl+t", "open_theme_picker", "Theme"),
        Binding("ctrl+c", "open_calendar", "Calendar"),
        Binding("escape", "view_mode", "View"),
        Binding("shift+left", "prev_tab", "Prev Tab", show=False),
        Binding("shift+right", "next_tab", "Next Tab", show=False),
        Binding("t", "focus_tree", "Tree"),
        Binding("q", "quit", "Quit"),
    ]

    edit_mode: reactive = reactive(False)
    selected_folder: str | None = None
    selected_note: str | None = None
    active_pad_theme: str = "opencode"
    _highlighted_folder: str | None = None
    _chord_target: str | None = None

    _open_tabs: list[tuple[str, str | None]] = []
    _active_tab_index: int = -1
    _tab_scroll: dict[tuple[str, str | None], int] = {}
    _tab_cursor: dict[tuple[str, str | None], tuple[int, int]] = {}
    _tab_target_line: dict[tuple[str, str | None], int] = {}
    _tab_id_counter: int = 0
    _last_tab_switch: float = 0.0

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "space":
            self._chord_target = "e"
            self.set_timer(0.5, self._chord_timeout)
        elif event.key == "escape" and not self.edit_mode:
            self._chord_target = "i"
            self.set_timer(0.5, self._chord_timeout)
        await super()._on_key(event)
        event.prevent_default()

    def _chord_timeout(self) -> None:
        self._chord_target = None

    def key_e(self, event: events.Key) -> None:
        if self._chord_target == "e":
            self._chord_target = None
            self.action_toggle_sidebar()

    def key_i(self, event: events.Key) -> None:
        if self._chord_target == "i":
            self._chord_target = None
            self.action_toggle_edit()

    def action_toggle_sidebar(self):
        try:
            sidebar = self.query_one("#sidebar")
            sidebar.display = not sidebar.display
        except Exception:
            pass

    def action_focus_tree(self):
        self.query_one("#note-tree", NoteTree).focus()

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield NoteTree("Notes", id="note-tree")
            with Vertical(id="editor-area"):
                yield Horizontal(id="tab-bar")
                with ContentSwitcher(id="editor-content", initial="note-viewer"):
                    yield NoteViewer(id="note-viewer")
                    yield OpenPadTextArea(id="text-editor")
        with Horizontal(id="statusbar"):
            yield Static(id="status-content")

    def on_mount(self):
        seed_sample_notes()
        meta = load_meta()
        self.active_pad_theme = meta.get("theme", "opencode")
        self._apply_theme()
        self._rebuild_tree()
        self.selected_note = None
        self.selected_folder = None
        self._load_note_view()
        self.call_after_refresh(self._update_status)
        ta = self.query_one("#text-editor", TextArea)
        ta.show_line_numbers = True
        ta.scroll_sensitivity_y = 0.1
        self.set_interval(60, self._update_status)

    def on_unmount(self):
        # Print ASCII art in the current theme's primary color
        t = getattr(self, "_resolved_theme", THEMES.get(self.active_pad_theme, THEMES["opencode"]))
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
        if self.active_pad_theme == "system":
            t = detect_system_theme()
            THEMES["system"] = t
        else:
            t = THEMES.get(self.active_pad_theme, THEMES["opencode"])
        self._resolved_theme = t
        self.screen.styles.background = t["bg"]

        sidebar = self.query_one("#sidebar")
        sidebar.styles.background = t["bg"]
        sidebar.styles.border_right = ("solid", t["border"])
        sidebar.styles.margin = 0

        editor_area = self.query_one("#editor-area")
        editor_area.styles.background = t["bg"]
        editor_area.styles.margin = 0

        self.screen.styles.border = ("none", t["bg"])

        editor_content = self.query_one("#editor-content")
        editor_content.styles.background = t["bg"]

        tab_bar = self.query_one("#tab-bar")
        tab_bar.styles.background = t["bg_element"]

        statusbar = self.query_one("#statusbar")
        statusbar.styles.color = t["text_muted"]

        tree = self.query_one("#note-tree", NoteTree)
        tree.styles.background = t["bg"]
        tree.styles.color = t["text"]
        tree.styles.padding = (0, 1)
        tree.show_guides = True
        tree.guide_depth = 2
        tree.ICON_NODE = " "
        tree.ICON_NODE_EXPANDED = " "

        viewer = self.query_one("#note-viewer", NoteViewer)
        viewer.styles.background = t["bg"]
        viewer.styles.scrollbar_color = t["primary"]
        viewer.styles.scrollbar_color_hover = t["primary"]
        viewer.styles.scrollbar_color_active = t["primary"]
        viewer.styles.scrollbar_background = t["bg_panel"]
        viewer.styles.scrollbar_background_hover = t["bg_panel"]
        viewer.styles.scrollbar_background_active = t["bg_panel"]

        ta = self.query_one("#text-editor", TextArea)
        ta.styles.background = t["bg"]
        ta.styles.color = t["text"]
        ta.styles.border = ("solid", t["border_active"])
        ta.styles.scrollbar_color = t["primary"]
        ta.styles.scrollbar_color_hover = t["primary"]
        ta.styles.scrollbar_color_active = t["primary"]
        ta.styles.scrollbar_background = t["bg_panel"]
        ta.styles.scrollbar_background_hover = t["bg_panel"]
        ta.styles.scrollbar_background_active = t["bg_panel"]

        for container_id in (
            "#cal-events-scroll", "#search-results-container",
            "#theme-list-container", "#move-list-container",
            "#theme-list", "#search-results", "#move-list"
        ):
            try:
                w = self.query_one(container_id)
                w.styles.scrollbar_color = t["primary"]
                w.styles.scrollbar_color_hover = t["primary"]
                w.styles.scrollbar_color_active = t["primary"]
                w.styles.scrollbar_background = t["bg_panel"]
                w.styles.scrollbar_background_hover = t["bg_panel"]
                w.styles.scrollbar_background_active = t["bg_panel"]
            except Exception:
                pass

        self._update_status()

        if self.selected_note:
            self._load_note_view()

    def _update_status(self):
        t = getattr(self, "_resolved_theme", THEMES.get(self.active_pad_theme, THEMES["opencode"]))
        sb = self.query_one("#status-content")

        mode = "EDIT" if self.edit_mode else "VIEW"
        now = datetime.now().strftime("%H:%M")

        if self.selected_note:
            folder_label = f"{self.selected_folder}/" if self.selected_folder and self.selected_folder != "__root__" else ""
            filepath = f"{folder_label}{self.selected_note}"
            fp_color = t["text"]
            if self.edit_mode:
                ta = self.query_one("#text-editor", TextArea)
                line_count = len(ta.text.splitlines())
            else:
                content = read_note(self.selected_folder, self.selected_note)
                line_count = len(content.splitlines()) if content else 0
            lc_text = f" {line_count} lines "
            lc_color = t["text"]
        else:
            filepath = "no/file/has/been/selected/yet"
            fp_color = t["text_muted"]
            line_count = 0
            lc_text = " [empty] "
            lc_color = t["text_muted"]

        left = Text.assemble(
            (f" {mode} ", Style(bgcolor=t["primary"], color=t["bg"])),
            ("\ue0b0", Style(bgcolor=t["bg_element"], color=t["primary"])),
            (f" {filepath} ", Style(bgcolor=t["bg_element"], color=fp_color)),
            ("\ue0b0", Style(bgcolor=t["bg_panel"], color=t["bg_element"])),
        )

        right = Text.assemble(
            ("\ue0b2", Style(bgcolor=t["bg_panel"], color=t["bg_element"])),
            (lc_text, Style(bgcolor=t["bg_element"], color=lc_color)),
            ("\ue0b2", Style(bgcolor=t["bg_element"], color=t["accent"])),
            (f" {now} ", Style(bgcolor=t["accent"], color=t["text"])),
        )

        content_width = left.cell_len + right.cell_len
        pad = max(0, sb.size.width - content_width)
        gap = Text(" " * pad, Style(bgcolor=t["bg_panel"]))
        sb.update(Text.assemble(left, gap, right))

    def _add_folder_node(self, parent, folder_data):
        node = parent.add(
            Text.assemble(" ", folder_data["name"]),
            data={"folder": folder_data["folder"], "note": None}
        )
        for child in folder_data.get("children", []):
            self._add_folder_node(node, child)
        for note in folder_data.get("notes", []):
            label = self._note_label(note, folder_data["folder"])
            node.add_leaf(
                label,
                data={"folder": folder_data["folder"], "note": note}
            )

    def _save_expanded_folders(self, node):
        result = set()
        if node.data and node.data.get("folder") and node.is_expanded:
            result.add(node.data["folder"])
        for child in node.children:
            result.update(self._save_expanded_folders(child))
        return result

    def _restore_expanded_folders(self, node, expanded):
        if node.data and node.data.get("folder") and node.data["folder"] in expanded:
            node.expand()
        for child in node.children:
            self._restore_expanded_folders(child, expanded)

    def _rebuild_tree(self):
        tree = self.query_one("#note-tree", NoteTree)
        expanded = self._save_expanded_folders(tree.root)
        tree.clear()
        tree.root.expand()

        data = get_tree()
        for item in data:
            if item["name"] == "__root__":
                for note in item["notes"]:
                    label = self._note_label(note, None)
                    tree.root.add_leaf(label, data={"folder": None, "note": note})
            else:
                self._add_folder_node(tree.root, item)

        self._restore_expanded_folders(tree.root, expanded)

        max_w = 0
        def walk(node, depth):
            nonlocal max_w
            label = node.label
            label_w = getattr(label, "cell_len", len(label))
            total = depth + 3 + label_w
            if total > max_w:
                max_w = total
            for child in node.children:
                walk(child, depth + 1)
        walk(tree.root, 0)
        sidebar = self.query_one("#sidebar")
        sidebar.styles.width = max(16, min(max_w + 5, 45))

    def _note_label(self, stem, folder):
        return Text.assemble(" ", stem)

    def _open_note_in_tab(self, note, folder, line=None, col=None, match_len=0):
        key = (note, folder)
        if key in self._open_tabs:
            self._active_tab_index = self._open_tabs.index(key)
            self._switch_to_tab(self._active_tab_index)
            self.call_after_refresh(self._scroll_to_active_tab)
            # If we have a specific position to jump to, do it after switching
            if line is not None and col is not None:
                self.call_after_refresh(lambda l=line, c=col, m=match_len: self._jump_to_match(l, c, m))
            return
        old_key = self._open_tabs[self._active_tab_index] if 0 <= self._active_tab_index < len(self._open_tabs) else None
        self._open_tabs.append(key)
        if old_key:
            self._save_tab_state()
        self._active_tab_index = len(self._open_tabs) - 1
        self.selected_note = note
        self.selected_folder = folder
        self._edit_original_note_name = note
        self.edit_mode = False
        self._update_status()
        self._rebuild_tabs()
        self.call_after_refresh(self._load_note_view)
        self.call_after_refresh(self._scroll_to_active_tab)
        # If we have a specific position to jump to, do it after loading
        if line is not None and col is not None:
            self.call_after_refresh(lambda l=line, c=col, m=match_len: self._jump_to_match(l, c, m))

    def _switch_to_tab(self, index):
        if index < 0 or index >= len(self._open_tabs):
            return
        old_key = self._open_tabs[self._active_tab_index] if self._active_tab_index >= 0 else None
        if old_key:
            self._save_tab_state()

        self._active_tab_index = index
        note, folder = self._open_tabs[index]
        self.selected_note = note
        self.selected_folder = folder
        self._edit_original_note_name = note
        self.edit_mode = False
        self._load_note_view()
        self._update_status()
        self._refresh_active_tab()

    def _scroll_to_active_tab(self):
        if len(self._open_tabs) < 2:
            return
        tab_bar = self.query_one("#tab-bar")
        active_tab = tab_bar.query("Button.tab.active")
        if not active_tab:
            return
        btn = active_tab.first()
        bar_width = tab_bar.region.width
        scroll_x = tab_bar.scroll_x
        btn_left = btn.region.x
        btn_right = btn.region.x + btn.region.width
        if btn_left >= scroll_x and btn_right <= scroll_x + bar_width:
            return
        target = max(0, btn_left - 4)
        tab_bar.scroll_to(x=target, force=True, animate=False)
        self.call_after_refresh(self._update_tab_arrows)

    def action_prev_tab(self):
        if len(self._open_tabs) < 2:
            return
        now = time.time()
        if now - self._last_tab_switch < 0.15:
            return
        self._last_tab_switch = now
        idx = (self._active_tab_index - 1) % len(self._open_tabs)
        self._switch_to_tab(idx)
        self.call_after_refresh(self._scroll_to_active_tab)

    def action_next_tab(self):
        if len(self._open_tabs) < 2:
            return
        now = time.time()
        if now - self._last_tab_switch < 0.15:
            return
        self._last_tab_switch = now
        idx = (self._active_tab_index + 1) % len(self._open_tabs)
        self._switch_to_tab(idx)
        self.call_after_refresh(self._scroll_to_active_tab)

    def _refresh_active_tab(self):
        if len(self._open_tabs) < 2:
            return
        for child in self.query("#tab-bar Button.tab, #tab-bar Button.tab.active"):
            idx = getattr(child, "data_index", -1)
            if idx < 0:
                continue
            child.set_class(idx == self._active_tab_index, "active")

    def _close_tab(self, index):
        if index < 0 or index >= len(self._open_tabs):
            return
        key = self._open_tabs[index]
        self._tab_scroll.pop(key, None)
        self._tab_cursor.pop(key, None)
        self._open_tabs.pop(index)
        if not self._open_tabs:
            self._active_tab_index = -1
            self.selected_note = None
            self.selected_folder = None
            self.edit_mode = False
            self._load_note_view()
            self._update_status()
            self._rebuild_tabs()
            return
        if index <= self._active_tab_index:
            self._active_tab_index = max(0, self._active_tab_index - 1)
        else:
            self._active_tab_index = min(self._active_tab_index, len(self._open_tabs) - 1)
        self._rebuild_tabs()
        self._switch_to_tab(self._active_tab_index)

    def _update_tab_arrows(self):
        if len(self._open_tabs) < 2:
            return
        tab_bar = self.query_one("#tab-bar")
        arrows = tab_bar.query("Button.scroll-arrow")
        for a in arrows:
            if a.id and a.id.startswith("tsl"):
                a.display = tab_bar.scroll_x > 0
            elif a.id and a.id.startswith("tsr"):
                a.display = tab_bar.scroll_x < tab_bar.max_scroll_x

    def on_resize(self):
        self.call_after_refresh(self._update_status)
        if len(self._open_tabs) >= 2:
            self.call_after_refresh(self._update_tab_arrows)

    def _scroll_tabs_left(self):
        if len(self._open_tabs) < 2:
            return
        tab_bar = self.query_one("#tab-bar")
        first_tab = tab_bar.query("Button.tab").first()
        step = first_tab.outer_size.width
        new_x = max(0, tab_bar.scroll_x - step)
        tab_bar.scroll_to(x=tab_bar.scroll_x - step, force=True, animate=False)
        for a in tab_bar.query("Button.scroll-arrow"):
            if a.id and a.id.startswith("tsl"):
                a.display = new_x > 0
            elif a.id and a.id.startswith("tsr"):
                a.display = new_x < tab_bar.max_scroll_x
        self.call_after_refresh(self._update_tab_arrows)

    def _scroll_tabs_right(self):
        if len(self._open_tabs) < 2:
            return
        tab_bar = self.query_one("#tab-bar")
        first_tab = tab_bar.query("Button.tab").first()
        step = first_tab.outer_size.width
        new_x = min(tab_bar.scroll_x + step, tab_bar.max_scroll_x)
        tab_bar.scroll_to(x=tab_bar.scroll_x + step, force=True, animate=False)
        for a in tab_bar.query("Button.scroll-arrow"):
            if a.id and a.id.startswith("tsl"):
                a.display = new_x > 0
            elif a.id and a.id.startswith("tsr"):
                a.display = new_x < tab_bar.max_scroll_x
        self.call_after_refresh(self._update_tab_arrows)

    def _rebuild_tabs(self):
        tab_bar = self.query_one("#tab-bar")
        old_children = list(tab_bar.query("*"))
        tab_bar.display = len(self._open_tabs) >= 2
        if not tab_bar.display:
            for c in old_children:
                c.remove()
            return
        left_arrow = Button("⮜", id=f"tsl-{self._tab_id_counter}", classes="scroll-arrow")
        self._tab_id_counter += 1
        left_arrow.styles.dock = "left"
        tab_bar.mount(left_arrow)
        for i, (note, folder) in enumerate(self._open_tabs):
            is_active = i == self._active_tab_index
            cls = "tab active" if is_active else "tab"
            uid = self._tab_id_counter
            self._tab_id_counter += 1
            tab = Button(note, id=f"tn-{uid}", classes=cls)
            tab.data_index = i
            tab_bar.mount(tab)
            uid = self._tab_id_counter
            self._tab_id_counter += 1
            close = Button("", id=f"tc-{uid}", classes="tab-close")
            close.data_index = i
            tab_bar.mount(close)
            if i < len(self._open_tabs) - 1:
                sep = Static("│", classes="tab-sep")
                tab_bar.mount(sep)
        right_arrow = Button("⮞", id=f"tsr-{self._tab_id_counter}", classes="scroll-arrow")
        self._tab_id_counter += 1
        right_arrow.styles.dock = "right"
        tab_bar.mount(right_arrow)
        for c in old_children:
            c.remove()
        self.call_after_refresh(self._update_tab_arrows)

    def on_button_pressed(self, event: Button.Pressed):
        button = event.button
        if button.id and button.id.startswith("tsl"):
            self._scroll_tabs_left()
            return
        if button.id and button.id.startswith("tsr"):
            self._scroll_tabs_right()
            return
        idx = getattr(button, "data_index", -1)
        if idx < 0 or idx >= len(self._open_tabs):
            return
        if button.has_class("tab-close"):
            self._close_tab(idx)
        elif button.has_class("tab"):
            self._switch_to_tab(idx)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted):
        data = event.node.data
        if data:
            self._highlighted_folder = data.get("folder")
            if data.get("note"):
                self.selected_folder = data["folder"]
                self.selected_note = data["note"]
                self._edit_original_note_name = data["note"]
                self.edit_mode = False
                self._load_note_view()
                self.query_one("#note-tree", NoteTree).focus()
                self._update_status()
            else:
                self.selected_folder = None
                self.selected_note = None
        else:
            self._highlighted_folder = None
            self.selected_folder = None
            self.selected_note = None

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        data = event.node.data
        if data and data.get("note"):
            self._open_note_in_tab(data["note"], data["folder"])

    def _load_note_view(self):
        switcher = self.query_one("#editor-content", ContentSwitcher)

        if self.edit_mode:
            content = read_note(self.selected_folder, self.selected_note)
            switcher.current = "text-editor"
            ta = self.query_one("#text-editor", TextArea)
            ta.load_text(content)
            ta.read_only = False
            key = (self.selected_note, self.selected_folder)
            if key in self._tab_cursor:
                # edit→edit tab switch: restore exact saved cursor
                ta.cursor_location = self._tab_cursor[key]
            elif key in self._tab_target_line:
                # view→edit: jump to the bottom-visible source line, col 0
                lines = content.splitlines()
                target = min(self._tab_target_line[key], max(0, len(lines) - 1))
                ta.cursor_location = (target, 0)
                # Scroll so the target line is at the top of the editor
                ta._recompute_cursor_offset()
                ta.scroll_to(y=max(0, ta._cursor_offset.y), animate=False)
            ta.focus()
        elif self.selected_note:
            content = read_note(self.selected_folder, self.selected_note)
            viewer = self.query_one("#note-viewer", NoteViewer)
            viewer.set_content(content, self.active_pad_theme)
            switcher.current = "note-viewer"
            key = (self.selected_note, self.selected_folder)
            if key in self._tab_scroll:
                viewer.scroll_y = self._tab_scroll[key]
            viewer.focus()

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
                old_key = (old_name, self.selected_folder)
                new_key = (new_name, self.selected_folder)
                if old_key in self._open_tabs:
                    idx = self._open_tabs.index(old_key)
                    self._open_tabs[idx] = new_key
                    if old_key in self._tab_scroll:
                        self._tab_scroll[new_key] = self._tab_scroll.pop(old_key)
                    if old_key in self._tab_cursor:
                        self._tab_cursor[new_key] = self._tab_cursor.pop(old_key)
                self.selected_note = new_name
                session_log.append(f"  * renamed: {old_name} → {new_name}")
                self._rebuild_tree()
                self._rebuild_tabs()
                self.call_after_refresh(self._scroll_to_active_tab)

        write_note(self.selected_folder, self.selected_note, content)

    def _save_tab_state(self):
        key = (self.selected_note, self.selected_folder)
        if key not in self._open_tabs:
            return
        if self.edit_mode:
            ta = self.query_one("#text-editor", TextArea)
            self._tab_cursor[key] = ta.cursor_location
            # Clear stale target line — it will be recomputed fresh from
            # scroll_y next time the user is in view mode and switches to edit
            self._tab_target_line.pop(key, None)
        else:
            viewer = self.query_one("#note-viewer", NoteViewer)
            self._tab_scroll[key] = viewer.scroll_y
            # Use the TOP-visible source line (scroll_y = first visible row).
            # Do NOT use size.height — it may be unreliable at this point.
            # Opening at the top-visible line gives exact WYSIWYG: the line
            # you see at the top in view is the first line in edit.
            if viewer._line_map:
                top_row = min(int(viewer.scroll_y), len(viewer._line_map) - 1)
                self._tab_target_line[key] = viewer._line_map[top_row]
            # Clear stale cursor so view→edit always uses the fresh target
            self._tab_cursor.pop(key, None)

    def _jump_to_match(self, line: int, col: int, match_len: int = 0):
        """Jump to a specific line/col and temporarily highlight the match."""
        if self.edit_mode:
            # Jump in editor
            ta = self.query_one("#text-editor", TextArea)
            ta.cursor_location = (line, col)
            ta.focus()
        else:
            # Jump in viewer
            try:
                viewer = self.query_one("#note-viewer", NoteViewer)
            except Exception:
                return
            if viewer._line_map and line < len(viewer._line_map):
                viewer.scroll_to(y=line, animate=False)
            viewer.highlight_match(line, col, match_len)

    def action_toggle_edit(self):
        if not self.selected_note:
            return
        self._save_tab_state()
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
            self._save_tab_state()
            self._save_and_rename()
            self.edit_mode = False
            self._rebuild_tree()
            self._load_note_view()
            self._update_status()

    def action_new_item(self):
        def handle(name):
            if not name:
                return
            parent = self._highlighted_folder
            if name.endswith("/"):
                folder_name = name.rstrip("/")
                full_path = f"{parent}/{folder_name}" if parent else folder_name
                create_folder(full_path)
                self._rebuild_tree()
                session_log.append(f"  + created folder: {full_path}")
            else:
                folder = parent
                write_note(folder, name, f"# {name}\n\n")
                self._rebuild_tree()
                self._open_note_in_tab(name, folder)
                self.edit_mode = True
                self._load_note_view()
                self._update_status()
                folder_label = f"{folder}/" if folder else ""
                session_log.append(f"  + created note:  {folder_label}{name}")
        self.push_screen(InputModal(" New Note/Folder (add / for folder)", "Name...", self.active_pad_theme), handle)

    def action_delete_item(self):
        if self.selected_note:
            msg = f"Delete '{self.selected_note}'? (y/n)"
            def handle(confirmed):
                if confirmed:
                    folder_label = f"{self.selected_folder}/" if self.selected_folder else ""
                    session_log.append(f"  - deleted note:  {folder_label}{self.selected_note}")
                    delete_note(self.selected_folder, self.selected_note)
                    key = (self.selected_note, self.selected_folder)
                    if key in self._open_tabs:
                        idx = self._open_tabs.index(key)
                        self._close_tab(idx)
                    self.selected_note = None
                    self.selected_folder = None
                    self._highlighted_folder = None
                    self.edit_mode = False
                    self._rebuild_tree()
                    if not self._open_tabs:
                        switcher = self.query_one("#editor-content", ContentSwitcher)
                        switcher.current = "note-viewer"
                        viewer = self.query_one("#note-viewer", NoteViewer)
                        viewer.set_content("", self.active_pad_theme)
                    self._update_status()
            self.push_screen(ConfirmModal(msg, self.active_pad_theme), handle)
        elif self._highlighted_folder:
            folder_name = self._highlighted_folder
            msg = f"Delete folder '{folder_name}' and all contents? (y/n)"
            def handle(confirmed):
                if confirmed:
                    session_log.append(f"  - deleted folder: {folder_name}")
                    delete_folder(folder_name)
                    for i in range(len(self._open_tabs) - 1, -1, -1):
                        note, folder = self._open_tabs[i]
                        if folder == folder_name:
                            key = (note, folder)
                            self._tab_scroll.pop(key, None)
                            self._tab_cursor.pop(key, None)
                            self._open_tabs.pop(i)
                    if not self._open_tabs:
                        self._active_tab_index = -1
                        self.selected_note = None
                        self.selected_folder = None
                        self.edit_mode = False
                        self._rebuild_tree()
                        switcher = self.query_one("#editor-content", ContentSwitcher)
                        switcher.current = "note-viewer"
                        viewer = self.query_one("#note-viewer", NoteViewer)
                        viewer.set_content("", self.active_pad_theme)
                    else:
                        self._active_tab_index = max(0, self._active_tab_index - 1) if self._active_tab_index >= 0 else 0
                        self._rebuild_tree()
                        self._switch_to_tab(self._active_tab_index)
                    self._update_status()
            self.push_screen(ConfirmModal(msg, self.active_pad_theme), handle)

    def action_search(self):
        def handle(result):
            if result:
                folder, name, line, col, match_len = result
                self._open_note_in_tab(name, folder, line, col, match_len)
        self.push_screen(SearchModal(self.active_pad_theme), handle)

    def action_move_item(self):
        # Determine what we're moving: selected note or highlighted folder
        if self.selected_note:
            note = self.selected_note
            folder = self.selected_folder
            label = f"{folder + '/' if folder and folder != '__root__' else ''}{note}"

            def handle(dest_folder, _note=note, _folder=folder):
                if dest_folder is _MOVE_MODAL_CANCEL:
                    return
                # dest_folder is None = root, or a folder path string
                # Normalize source folder (treat __root__ and None the same)
                src_norm = _folder if _folder and _folder != "__root__" else None
                # Don't move to same location
                if dest_folder == src_norm:
                    return
                ok = move_note(_folder, _note, dest_folder)
                if ok:
                    folder_label = f"{_folder + '/' if _folder and _folder != '__root__' else ''}"
                    session_log.append(f"  → moved note: {folder_label}{_note} → {dest_folder or '/'}")
                    # Close tab if open, then reopen in new location
                    key = (_note, _folder)
                    if key in self._open_tabs:
                        idx = self._open_tabs.index(key)
                        self._close_tab(idx)
                    self.selected_note = None
                    self.selected_folder = None
                    self._rebuild_tree()
                    self._open_note_in_tab(_note, dest_folder)
                    self._update_status()

            self.push_screen(MoveModal(label, self.active_pad_theme), handle)

        elif self._highlighted_folder:
            folder = self._highlighted_folder
            label = folder

            def handle(dest_folder, _folder=folder):
                if dest_folder is _MOVE_MODAL_CANCEL:
                    return
                src_parent = str((_folder.rsplit("/", 1)[0]) if "/" in _folder else "")
                dest_norm = dest_folder or ""
                if dest_norm == src_parent:
                    return
                ok, new_path = move_folder(_folder, dest_folder)
                if ok:
                    session_log.append(f"  → moved folder: {_folder} → {dest_folder or '/'}")
                    # Close any tabs that were inside this folder
                    for i in range(len(self._open_tabs) - 1, -1, -1):
                        note, tab_folder = self._open_tabs[i]
                        if tab_folder and (tab_folder == _folder or tab_folder.startswith(_folder + "/")):
                            key = (note, tab_folder)
                            self._tab_scroll.pop(key, None)
                            self._tab_cursor.pop(key, None)
                            self._open_tabs.pop(i)
                    if not self._open_tabs:
                        self._active_tab_index = -1
                        self.selected_note = None
                        self.selected_folder = None
                        self.edit_mode = False
                        switcher = self.query_one("#editor-content", ContentSwitcher)
                        switcher.current = "note-viewer"
                        viewer = self.query_one("#note-viewer", NoteViewer)
                        viewer.set_content("", self.active_pad_theme)
                    self._highlighted_folder = None
                    self._rebuild_tree()
                    self._rebuild_tabs()
                    self._update_status()

            self.push_screen(MoveModal(label, self.active_pad_theme), handle)

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
    background: #ffffff30;
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
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "--version":
        from importlib.metadata import version as _version
        print(f"openpad {_version('openpad')}")
        return

    notes_dir = Path.home() / ".openpad" / "notes"
    if not notes_dir.exists() or not any(notes_dir.iterdir()):
        print("")
        print("  ╭──────────────────────────────────────╮")
        print("  │                                      │")
        print("  │   Thank you for installing OpenPad!  │")
        print("  │                                      │")
        print("  │  A minimal, terminal-based note app  │")
        print("  │  designed for developers & students. │")
        print("  │                                      │")
        print("  │  Fast. Lightweight. Your notes, your │")
        print("  │  way — plain .md files, no lock-in.  │")
        print("  │                                      │")
        print("  │  I hope you enjoy using it as much   │")
        print("  │  as I enjoyed building it.           │")
        print("  │                                      │")
        print("  │       — Pierre-Alexandre             │")
        print("  │                                      │")
        print("  ╰──────────────────────────────────────╯")
        print("")

    app = OpenPad()
    app.CSS += CSS_EXTRA
    app.run()


if __name__ == "__main__":
    main()
