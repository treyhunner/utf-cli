import importlib.resources
import unicodedata
import sqlite3

from darkdetect import isDark as is_dark, listener as dark_toggle_listener
import pyperclip
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Static

from .generate_db import make_database, db_path


__version__ = "0.2.0"

if not db_path.exists():
    make_database()
db = sqlite3.connect(db_path)


def find_character(query):
    cursor = db.execute("""
        SELECT DISTINCT symbols.name, symbols.glyph
        FROM keywords
        INNER JOIN symbols ON keywords.glyph = symbols.glyph
        WHERE keyword LIKE ?
        ORDER BY -symbols.priority
        LIMIT 100
    """, [f"%{query}%"])
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


class Result(Static):

    __slots__ = ("name", "character")

    def __init__(self, name, character):
        name = name.title()
        self.name = name
        self.character = character
        super().__init__(f"[bold]{name}[/bold]\n\n{character}")

    @property
    def can_focus(self):
        return True

    def copy(self):
        pyperclip.copy(self.character)
        self.notify(f"Copied {self.character}  ({self.name})")
        increment_copy_count(self.name, self.character)

    def on_key(self, event):
        if event.key == "enter":
            self.copy()

    def on_click(self, event):
        self.copy()


class SearchResults(Static):

    results = reactive(list, recompose=True)

    def compose(self):
        for name, character in self.results:
            yield Result(name, character)


class UnicodeApp(App):
    """A Textual app to search Unicode characters."""

    CSS_PATH = "utf.tcss"

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
        yield Input(placeholder="Search for a character")
        yield SmartScroll(
            SearchResults(id="results").data_bind(results=UnicodeApp.results)
        )

    def action_clear_search(self):
        self.query_one(Input).focus()
        self.query_one(Input).value = ""

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
            self.query_one(Input).focus()

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

    def on_input_changed(self, message):
        if message.value:
            self.results = find_character(message.value)
        else:
            self.clear_results()

app = UnicodeApp()
