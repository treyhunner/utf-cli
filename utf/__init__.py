import importlib.resources
import unicodedata
import sqlite3

from darkdetect import isDark as is_dark, listener as dark_toggle_listener
import pyperclip
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Static

from .generate_db import make_database, db_path


__version__ = "0.1.0.a1"

if not db_path.exists():
    make_database()
db = sqlite3.connect(db_path)


def find_character(name):
    cursor = db.execute("""
        SELECT name, glyph
        FROM symbols
        WHERE name LIKE ?
        ORDER BY -PRIORITY
        LIMIT 100;
    """, [f"%{name}%"])
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
        ORDER BY -copies
    """)
    return [
        (name, glyph)
        for name, glyph in cursor.fetchall()
    ]


class SmartScroll(VerticalScroll, can_focus=False):
    def watch_show_vertical_scrollbar(self) -> None:
        self.can_focus = self.show_vertical_scrollbar



class Result(Static):

    __slots__ = ("name", "character")

    def __init__(self, name, character):
        name = name.replace("-", " ").title()
        self.name = name
        self.character = character
        super().__init__(f"[bold]{name}[/bold]\n\n{character}")

    @property
    def can_focus(self):
        return True

    def copy(self):
        character = str(self.renderable)
        pyperclip.copy(character)
        self.notify(f"Copied {character}")
        increment_copy_count(self.name, character)

    def on_key(self, event):
        if event.key == "enter":
            self.copy()

    def on_click(self, event):
        self.copy()


class SearchResults(Static):

    results = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        for name, character in self.results:
            yield Result(name, character)


class UnicodeApp(App):
    """A Textual app to search Unicode characters."""

    CSS_PATH = "utf.tcss"

    BINDINGS = [
        ("ctrl+t", "toggle_dark", "Toggle dark mode"),
        ("ctrl+l", "clear_search", "Clear search"),
    ]

    results = reactive(list)

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        self.dark = is_dark()
        yield Footer()
        yield Input(placeholder="Search for a character")
        yield SmartScroll(
            SearchResults(id="results").data_bind(results=UnicodeApp.results)
        )

    def action_toggle_dark(self):
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_clear_search(self):
        self.query_one(Input).value = ""

    def clear_results(self):
        self.results = get_character_cache()

    def on_load(self):
        self.clear_results()

    def on_input_changed(self, message):
        if message.value:
            self.results = find_character(message.value)
        else:
            self.clear_results()

app = UnicodeApp()
