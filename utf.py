import unicodedata
import sqlite3

import pyperclip
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Static


__version__ = "0.0.1"


db = sqlite3.connect("utf8.db").cursor()


def find_character(name):
    db.execute("""
        SELECT name, ordinal
        FROM chars
        WHERE name LIKE ?
        LIMIT 100;
    """, [f"%{name}%"])
    return [
        (name, chr(ordinal))
        for name, ordinal in db.fetchall()
    ]


class SmartScroll(VerticalScroll, can_focus=False):
    def watch_show_vertical_scrollbar(self) -> None:
        self.can_focus = self.show_vertical_scrollbar



class Result(Static):
    @property
    def can_focus(self):
        return True

    def on_key(self, event):
        if event.key == "enter":
            pyperclip.copy(str(self.renderable))


class SearchResults(Static):

    results = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        for name, character in self.results:
            yield Result(character)


class UnicodeApp(App):
    """A Textual app to search Unicode characters."""

    CSS_PATH = "utf.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    results = reactive(list)

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Footer()
        yield Input(placeholder="Search for a character")
        yield SmartScroll(
            SearchResults(id="results").data_bind(results=UnicodeApp.results)
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.value:
            self.results = find_character(message.value)
        else:
            self.results = []


def main():
    app = UnicodeApp()
    app.run()


if __name__ == "__main__":
    main()
