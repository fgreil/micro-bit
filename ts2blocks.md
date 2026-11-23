# ts2blocks.py

`ts2blocks.py` draws a Microsoft MakeCode micro:bit program (`.ts`) as an SVG image of MakeCode-style blocks. It's meant for printouts and worksheets: it shows the Blocks view of a program without opening the MakeCode editor.

## Usage

```
python3 ts2blocks.py egoshooter.ts            # writes egoshooter.svg
python3 ts2blocks.py game.ts -o out.svg       # choose the output file
python3 ts2blocks.py game.ts -c 1             # one column instead of two
python3 ts2blocks.py game.ts --wrap 60        # wrap comment notes after 60 characters
```

| Option | Default | Meaning |
|---|---|---|
| `source` | – | MakeCode JavaScript/TypeScript file |
| `-o`, `--output` | `<source>.svg` | SVG file to write |
| `-c`, `--columns` | `2` | Number of columns the block stacks are spread across |
| `--wrap` | `45` | Maximum characters per line in comment notes |

**Requirements**:
- Python 3.8 or newer.
- Pillow (`PIL`) is optional. When it's installed and finds `DejaVuSans.ttf`, text widths are measured exactly. Otherwise they're estimated, so some blocks may be slightly too wide or too narrow.

**Converting the SVG**: open it in a browser or Inkscape. To make a PDF or PNG, use for example `rsvg-convert -f pdf egoshooter.svg -o egoshooter.pdf`.

## What it draws

| Source code | Drawn as |
|---|---|
| Top-level statements | Collected in an **on start** block |
| `function name(params) {}` | Function block with the parameters as variable pills, called with **call name** |
| Calls with a callback (`input.onButtonPressed(…, function () {})`, arrow functions) | Event block with the body inside, plus callback parameters |
| `let`, `=`, `+=`, `-=`, `++`, `--` | **set … to** / **change … by** |
| `if` / `else if` / `else` | One logic block with several sections |
| `while` | **while** loop |
| `for (let i = 0; i < n; i++)` | **repeat n times** |
| Other counting `for` loops | **for i from … to …** |
| `for (const x of list)` | **for element x of list** |
| `break`, `continue`, `return` | Matching blocks |
| `+ - * / %`, comparisons, `&&`, `\|\|`, `!` | Math reporters (round) and logic reporters (hexagonal) |
| `a ? b : c` | **if … then … else** reporter |
| Arrays and indexing | **array of …** / **get value at** |
| Enum values (`Button.A`, `Gesture.Shake`, …) | Dropdowns, e.g. "A ▾" or "shake ▾" |
| `` basic.showLeds(`…`) `` and `IconNames.Happy` etc. | 5×5 LED grid |
| `//` and `/* */` comments | Yellow notes next to the following block, joined to it by a dashed line |

## Recognised APIs

About 120 micro:bit APIs from these categories are mapped to their English MakeCode text and category color:

- basic, input, led, music, game, radio, pins, math, control, serial, images, text
- instance methods of sprites, images, arrays and strings, for example `sprite.change`, `list.push`

The mapping is two plain dictionaries:

- `API`: the full call name mapped to its category, block text and kind (`'basic.showNumber': ('basic', 'show number {0}', 's')`).
- `METHODS`: instance methods, where `{0}` stands for the object (`'isTouching': ('game', 'is {0} touching {1}', 'b')`).

The block kind is one of: `s` statement, `r` round reporter, `b` boolean, `h` event.

To add a block, add one line to `API` or `METHODS`. Calls the script doesn't know, for example from extensions, are still drawn as grey generic blocks with their name and arguments.

## How it works

1. **Tokenizer**: splits the source into tokens with one regular expression. Comments are attached to the next token.
2. **Parser**: a recursive-descent parser for the TypeScript subset MakeCode produces. Type annotations are skipped. The result is a tree of plain dictionaries.
3. **Block model**:
   - Expressions become inline elements: `Label`, `Box` for fields, dropdowns and reporters, and `LEDGrid`.
   - Statements become `Stmt`, a single block with notches.
   - Statements with bodies become `CBlock`: if, loops, events and functions.
   - Sizes are calculated from the text widths.
4. **Layout**:
   - Each top-level block stack is drawn with its comment notes on its right side.
   - The stacks are placed in columns, each new stack going into the currently shortest column.
   - The result is one SVG with a white background.

## Test programs

- `egoshooter.ts`: sprites, events, functions, `if` / `else if` and the `forever` loop.
- `dice.ts`: arrays and indexing, nested loops (*repeat* around *for*), nested math reporters, remainder, `≥`, and reporters nested three deep as function arguments (see `dice.md`).

ts2blocks doesn't check program logic. For example, it doesn't warn when a function parameter and a loop variable share a name, which MakeCode treats as one global variable.

## Limitations

- **Not identical to MakeCode**: the result looks like MakeCode but isn't pixel-identical. Colors are the MakeCode category colors, but shapes and spacing are approximations.
- **Not supported**: classes, `switch`, `try`/`catch`, string interpolation (`${…}`) and object literals. Generics in type annotations are skipped without being checked.
- **Lost comments**: comments directly before `}` or `else` are dropped.
- **Labels and order may differ**: block texts follow the English MakeCode editor at the time of writing and may differ slightly from the current editor. The order of the stacks also isn't the same as in the MakeCode workspace.
- **Simplified display**: enum values are shown as their name in lower case with spaces, so `Melodies.PowerUp` becomes "power up". Only the icons listed in `ICONS` are drawn as LED grids. Other icons are shown by name.
