# utf-cli

[![PyPI - Version](https://img.shields.io/pypi/v/utf-cli.svg)](https://pypi.org/project/utf-cli)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/utf-cli.svg)](https://pypi.org/project/utf-cli)

Like a mashup of https://unicode.party/ and https://utf8.xyz/ but it's completely local in your terminal!

[![typing "sparkles" and copying sparkles character](https://asciinema.org/a/Pyf3UCAkuG0BXn10HOBFx68vO.svg)](https://asciinema.org/a/Pyf3UCAkuG0BXn10HOBFx68vO)

## Installation

```console
pipx install utf-cli
```

## Usage

Run `utf`:

```console
utf
```

Then:

1. Type your query
2. Hit Enter, Tab, or the down arrow key to select the first result
3. Use Tab or arrow keys to move between results
4. Hit Enter to copy the character

To copy the Python code point escape sequence (e.g. `\u2728` or `\U00002728`) hit the `c` key.

To copy the HTML escape entity for a character (e.g. `&copy;`) hit the `h` key.

To copy the name for a character (e.g. `Sparkling Heart`) hit the `n` key.

Note that the mouse works also:

- Clicking on a result will also copy the character.
- Scrolling should work as expected

## Features

Before you start typing a query, a default character list will show up.
The default characters are commonly searched for characters (by Trey's best guess of what's common).

The `utf` program will keep track of every time you search for a character.
The characters you search for most often will show up near the beginning of the default character list.

## License

This package is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
