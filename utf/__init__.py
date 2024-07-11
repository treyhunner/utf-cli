from html.entities import codepoint2name
import importlib.resources
import unicodedata
import sqlite3

from darkdetect import isDark as is_dark, listener as dark_toggle_listener
import pyperclip
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Static

from .generate_db import make_database, db_path


__version__ = "0.3.1"

if not db_path.exists():
    make_database()
db = sqlite3.connect(db_path)


def find_character(query):
    where = "keyword LIKE ?"
    variables = [f"%{query}%"]
    if len(query) == 1 or any(ord(c) > 127 for c in query):
        where += " OR symbols.glyph LIKE ?"
        variables += variables
    cursor = db.execute(f"""
        SELECT DISTINCT symbols.name, symbols.glyph
        FROM keywords
        INNER JOIN symbols ON keywords.glyph = symbols.glyph
        WHERE {where}
        ORDER BY -symbols.priority
        LIMIT 100
    """, variables)
    copied_before = set(get_character_cache())
    results = [
        (name, glpyh)
        for name, glpyh in cursor.fetchall()
    ]
    return sorted(results, key=lambda r: r not in copied_before)


def increment_copy_count(name, glyph):
    db.execute("""
        INSERT INTO copied (glyph, copies, last_copied)
        VALUES (
            ?,
            1,
            datetime('now')
        )
        ON CONFLICT(glyph) DO UPDATE SET
            copies = copies + 1,
            last_copied = datetime('now')
    """, (glyph,))
    db.commit()


def get_character_cache():
    cursor = db.execute("""
        SELECT symbols.name, copied.glyph
        FROM copied
        INNER JOIN symbols
        ON symbols.glyph = copied.glyph
        ORDER BY -copies, -last_copied
    """)
    return [
        (name, glyph)
        for name, glyph in cursor.fetchall()
    ]


class SmartScroll(VerticalScroll, can_focus=False):
    def watch_show_vertical_scrollbar(self):
        self.can_focus = self.show_vertical_scrollbar


class Result(Widget):

    __slots__ = ("name", "character")

    BINDINGS = [
        ("c", "copy_code", "Copy code point"),
        ("enter", "copy_character", "Copy character"),
        ("h", "copy_html_entity", "Copy HTML entity"),
        ("n", "copy_name", "Copy name"),
    ]

    def __init__(self, name, character):
        name = name.title()
        self.name = name
        self.character = character
        super().__init__()

    def get_html_entity(self):
        codes = [ord(c) for c in self.character]
        return "".join(
            f"&{codepoint2name.get(c, f'#{c}')};"
            for c in codes
        )

    def compose(self):
        yield Static(self.name, classes="name")
        code = ""
        entity = ""
        if len(self.character) == 1:
            c = ord(self.character)
            code = f"{c:X}"
            code = code.zfill(8 if len(code) > 4 else 4)
            entity = self.get_html_entity()
        yield Static(code)
        yield Static(self.character)
        yield Static(entity)

    @property
    def can_focus(self):
        return True

    def action_copy_code(self):
        code = self.character.encode("unicode_escape").decode()
        pyperclip.copy(code)
        self.notify(f"[green]Copied[/green] {code}")
        increment_copy_count(self.name, self.character)

    def action_copy_character(self):
        pyperclip.copy(self.character)
        self.notify(f"[green]Copied[/green] {self.character}")
        increment_copy_count(self.name, self.character)

    def action_copy_html_entity(self):
        html_entity = self.get_html_entity()
        pyperclip.copy(html_entity)
        self.notify(f"[green]Copied[/green] {html_entity}")
        increment_copy_count(self.name, self.character)

    def action_copy_name(self):
        pyperclip.copy(self.name)
        self.notify(f"[green]Copied[/green] {self.name!r}")
        increment_copy_count(self.name, self.character)

    def on_click(self, event):
        self.action_copy_character()


class SearchBox(Input):

    BINDINGS = [
        Binding("enter", "first_result", "Select first result", priority=True),
    ]

    class Done(Message):
        """Searching done."""

    def action_first_result(self):
        self.post_message(self.Done())


class SearchResults(Static):

    results = reactive(list, recompose=True)

    def compose(self):
        for name, character in self.results:
            yield Result(name, character)


class UnicodeApp(App):
    """A Textual app to search Unicode characters."""

    CSS_PATH = "utf.tcss"

    NOTIFICATION_TIMEOUT = 10
    BINDINGS = [
        ("ctrl+t", "toggle_dark", "Toggle dark mode"),
        ("ctrl+l", "clear_search", "Clear search"),
        Binding("up", "move_up", "Move up", priority=True, show=False),
        Binding("down", "move_down", "Move down", priority=True, show=False),
        Binding("left", "move_left", "Move left", show=False),
        Binding("right", "move_right", "Move right", show=False),
    ]

    results = reactive(list)

    def compose(self):
        """Called to add widgets to the app."""
        self.dark = is_dark()
        yield Footer()
        yield SearchBox(placeholder="Search for a character")
        yield SmartScroll(
            SearchResults(id="results").data_bind(results=UnicodeApp.results)
        )

    def action_clear_search(self):
        self.query_one(SearchBox).focus()
        self.query_one(SearchBox).value = ""

    def clear_results(self):
        self.results = get_character_cache()

    def action_move_up(self):
        if not isinstance(self.focused, Result):
            return
        queries = self.query(Result)
        index = list(queries).index(self.focused)
        index -= self.grid_size
        if index >= 0:
            self.query(Result)[index].focus()
        else:
            self.query_one(SearchBox).focus()

    def action_move_down(self):
        if not isinstance(self.focused, Result):
            self.query(Result)[0].focus()
            return
        queries = self.query(Result)
        index = list(queries).index(self.focused)
        index += self.grid_size
        if index < len(queries):
            self.query(Result)[index].focus()

    def action_move_left(self):
        queries = self.query(Result)
        index = list(queries).index(self.focused)
        index -= 1
        if index >= 0 and (index+1) % self.grid_size > 0:
            self.query(Result)[index].focus()

    def action_move_right(self):
        queries = self.query(Result)
        index = list(queries).index(self.focused)
        index += 1
        if index < len(queries) and index % self.grid_size > 0:
            self.query(Result)[index].focus()

    def on_resize(self, event):
        if event.size.width > 200:
            self.query_one(SearchResults).set_classes("large")
            self.grid_size = 5
        elif event.size.width > 150:
            self.query_one(SearchResults).set_classes("medium")
            self.grid_size = 4
        elif event.size.width > 100:
            self.query_one(SearchResults).set_classes("small")
            self.grid_size = 3
        elif event.size.width > 70:
            self.query_one(SearchResults).set_classes("tiny")
            self.grid_size = 2
        else:
            self.query_one(SearchResults).set_classes("")
            self.grid_size = 1

    def on_load(self):
        self.clear_results()

    def on_search_box_done(self, message):
        if not isinstance(self.focused, Result):
            self.query(Result)[0].focus()
            return

    def on_input_changed(self, message):
        if message.value:
            self.results = find_character(message.value)
        else:
            self.clear_results()

app = UnicodeApp()
