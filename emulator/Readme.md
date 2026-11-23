# micro-bit-emulator.html

A one-page micro:bit emulator for MakeCode programs. Paste a `.ts` file, press **Run**, and use the buttons **A**, **B**, **A+B** and **Shake**. It's a quick way to try programs like `egoshooter.ts` and `dice.ts` without opening the MakeCode editor. It has no block view and needs no installation, server or internet connection.

## Usage

1. Open `micro-bit-emulator.html` in a browser on a computer, tablet or phone (Chrome, Edge, Firefox or Safari).
2. Open the **Programm** section and paste the content of a MakeCode `.ts` file.
3. Press **▶ Start** (EN: **Run**). **■ Stop** ends the program. After starting, you can fold the code section away.
4. Click or tap the buttons on the board, or use the keyboard:

   | Key | Input |
   |---|---|
   | `A` | Button A |
   | `B` | Button B |
   | `C` | A+B |
   | `S` | Shake |

   The keyboard only works when the text box isn't focused.

The page needs the first click on **Start** to switch on the sound, because browsers only allow audio after a click.

## Layout

The page uses the same receipt-style template as f418.eu: a white card with a Courier font, the purple accent `#502379`, dashed dividers and a DE/EN language switch. German is the default.

| Part | Content |
|---|---|
| Header | Language switch, title, one-line subtitle |
| Board | Start/Stop buttons, the simplified micro:bit (5×5 LEDs, A, B, A+B, Shake), status line and error messages. Always visible. |
| **Programm** | The code box. Collapsible, open by default. |
| **Bedienung** | Buttons and keys, plus short instructions. Collapsible, closed by default. |
| **Unterstützt** | Supported block categories and what's missing. Collapsible, closed by default. |
| Footer | Repository link, e-mail, date |

**Mobile**:
- On narrow screens the board shrinks to fit the card.
- The code box uses 16 px text, so iPhones don't zoom in while typing.
- Buttons react to taps without the double-tap delay.

The texts on the page switch between German and English. Error messages from the emulator are always in English.

## What it runs

### Language

Everything MakeCode generates in the JavaScript view:

- variables (`let`, `const`), numbers, text, `true` / `false`
- arithmetic, comparisons, `&&`, `||`, `!`, `? :`
- `if` / `else if` / `else`, `while`, `for`, `for … of`, `break`, `continue`
- your own functions with parameters and `return`, and arrow functions
- arrays (indexing, `push`, `length` and so on) and template strings for LED pictures
- TypeScript type annotations (`: number`, `: string`, `: boolean`, `: Image`, `: game.LedSprite`, with or without `[]`), which are removed before running

### Blocks

| Category | Supported |
|---|---|
| Basic | `show number`, `show string`, `show leds`, `show icon`, `show arrow`, `clear screen`, `pause`, `forever` |
| Input | `on button A / B / A+B pressed`, `on shake`, `running time` |
| LED | `plot`, `unplot`, `toggle`, `point`, `plot brightness` |
| Game | `create sprite`, sprite `change`, `set`, `get`, `move`, `go to`, `is touching`, `is touching edge`, `delete`, `pause`, `resume`, `is paused` |
| Images | `create image`, `create big image`, `icon image`, `arrow image`, `plot image`, `show image` |
| Music | `play` with built-in melodies or sound effects (in background or until done), `play tone`, `rest`, `stop all sounds` |
| Math | `pick random`, `random true or false`, `integer ÷`, `constrain`, `map`, and the normal `Math` functions |

### Timing

The built-in waits are the same as in MakeCode's source code (`pxt-microbit/libs/core`):

| Block | Wait |
|---|---|
| `show leds`, `show image` | 400 ms |
| `show icon`, `show arrow` | 600 ms |
| `show number` / `show string` with one character | 750 ms (5 × the 150 ms interval) |
| `show number` / `show string` with several characters | Scrolls one column every 150 ms, then clears the screen |
| `forever` | 20 ms between repetitions |
| Sprite engine | Redraws the screen every 30 ms and after every sprite change, unless the game is paused |

### Not supported

- radio, pins, sensors (temperature, light level, compass, acceleration, rotation) and the logo
- gestures other than shake, and "button is pressed"
- the built-in game score, lives, countdown and game-over screen
- sprite `turn`, `if on edge, bounce` and blinking
- letters and most symbols in `show string`: digits, `-`, `.` and spaces are drawn, every other character appears as a small square
- icons other than the 16 in the built-in list, and serial output

Using an unsupported block stops the program with a message such as *"radio" is not supported by this emulator*.

## How it works

The page is a single HTML file with no libraries. The favicon link (`../favicon.png`) expects the page to sit one folder below the site's favicon, as on f418.eu.

1. **Translation**: a few regular expressions turn the MakeCode code into JavaScript that the browser can run:
   - type annotations are removed
   - all functions and callbacks become `async`
   - calls of your own functions and of waiting blocks (`pause`, `show …`, `music.play`) get an `await`
   - every loop gets a small yield point (`await __tick()`), so even a loop without a pause can't freeze the page
2. **Running**:
   - the translated program runs as one function. Its parameters are the micro:bit namespaces (`basic`, `input`, `led`, `game`, `images`, `music`, …), which are simple JavaScript objects.
   - an unknown name, either a function inside a namespace or a whole namespace, ends the program with a clear message.
3. **Fibers**: like the real micro:bit, each event handler and each `forever` loop runs side by side. If a button is pressed while its handler is still running, the press is queued and handled afterwards. **Stop** and **Run** cancel all running code at its next wait.
4. **Display**: 25 LEDs with brightness 0–255, redrawn on every browser frame.
5. **Sound**: built-in melodies such as `JumpUp`, `BaDing`, `PowerUp` and `Wawawawaa` are played as short square-wave note sequences through the Web Audio API. They sound similar to MakeCode but aren't the same.

## Tests

The emulator was tested in headless Chrome (Playwright) with the programs from the repository:

- **`dice.ts`**:
  - the spinner runs and a die face appears
  - B switches to the 0–9 mode, which flashes the digits and ends with a smiley
  - shaking rolls a digit, and A switches modes backwards
- **`egoshooter.ts`**:
  - the monster falls
  - a hit flashes the screen and shows the new number of lives
  - A moves the ship, and A+B fires the laser
- **Phone sizes**: both programs were also run in a 375 px and a 320 px wide phone view with touch input. The page doesn't scroll sideways, and tapping A+B rolls the die.
- **Error cases**:
  - an unsupported namespace (`radio`) and a syntax error are both reported
  - an endless loop without a pause keeps the page responsive
  - arrow functions with typed parameters and scrolling numbers work

## Limits

- **Not a real emulator**: it doesn't execute ARM code and doesn't use MakeCode's own simulator. Timing is close but not exact, and the sounds are approximations.
- **Regex translation**: the translation works on text, not on a parsed program. Unusual code can trip it, for example the word `function` or `=>` inside a string, or a function name that is also used as a property name.
- **No strict compiler**: the code is never fully compiled, so errors MakeCode would report while compiling (wrong types, unknown variables in branches that never run) only show up when that line actually runs, or not at all.
