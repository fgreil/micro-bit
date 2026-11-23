# micro:bit Dice

A small MakeCode program for the BBC micro:bit **V2**. It flips a coin, rolls a normal 6-sided die (D6) or picks a number from 0 to 9. It's a classroom example and also a test case for `ts2blocks.py`. Code comments are in simple German for 3rd-grade pupils.

## Files

| File | Purpose |
|---|---|
| `dice.ts` | MakeCode JavaScript. Paste it into the JavaScript tab, then switch to Blocks. |
| `dice.md` | This documentation. |

## Controls

| Input | Action |
|---|---|
| Shake | Roll |
| **A+B** | Roll |
| **A** | Previous mode (from 0 it goes to 2) |
| **B** | Next mode (from 2 it goes to 0) |

The program starts in mode 1 (D6) with a blank screen.

## Modes

| Mode | Name | Values | Display |
|---|---|---|---|
| 0 | Coin flip | 0, 1 | 1 = head (filled circle), 0 = tail (empty ring) |
| 1 | D6 | 1–6 | Dots like on a die |
| 2 | Number | 0–9 | The digit |

The smallest and largest value of each mode are stored in two lists, `von = [0, 1, 0]` and `bis = [1, 6, 9]`. The current mode number is the position in these lists.

### Dot layout (mode 1)

The dice branch of `zeigen(wert)` builds every die face from four rules instead of six separate pictures:

| Rule | LEDs (x, y) |
|---|---|
| Odd number (1, 3, 5) | Centre (2,2) |
| 2 or more | Top left (0,0) and bottom right (4,4) |
| 4 or more | Top right (4,0) and bottom left (0,4) |
| Exactly 6 | Middle left (0,2) and middle right (4,2) |

```
1            2            3            4            5            6
. . . . .    # . . . .    # . . . .    # . . . #    # . . . #    # . . . #
. . . . .    . . . . .    . . . . .    . . . . .    . . . . .    . . . . .
. . # . .    . . . . .    . . # . .    . . . . .    . . # . .    # . . . #
. . . . .    . . . . .    . . . . .    . . . . .    . . . . .    . . . . .
. . . . .    . . . . #    . . . . #    # . . . #    # . . . #    # . . . #
```

## Roll sequence (`wuerfeln`)

1. **Spinner**: four pixels run clockwise along the edge, one on each side. There are 4 steps per round, 50 ms per step and 3 rounds, about 0.6 s in total:

   ```
   step 0       step 1       step 2       step 3
   # . . . #    . # . . .    . . # . .    . . . # .
   . . . . .    . . . . #    . . . . .    # . . . .
   . . . . .    . . . . .    # . . . #    . . . . .
   . . . . .    # . . . .    . . . . .    . . . . #
   # . . . #    . . . # .    . . # . .    . # . . .
   ```

2. **Result**: the roll sound (`JumpUp`) starts together with the result, which is `randint(von[modus], bis[modus])`. The result stays on the screen.

## Mode change sequence (`modusWechseln`)

1. **New mode**: `modus = (modus + richtung) % 3`. A passes `richtung = 2`, which works like one step back. B passes `1`.
2. **Flash**: all possible values of the new mode flash one after another.
   - Coin and D6 values get an extra 200 ms pause each.
   - The digits 0–9 get no extra pause. They only stay up for the short built-in wait of `show number`, so the whole sequence runs much faster than with the pause.
   - `show leds` (coin) also waits a little by itself, so the two coin pictures stay up slightly longer than the dice faces.
3. **Arrival**: the mode sound (`BaDing`) starts together with a smiley (`show icon Happy`). The smiley stays until the next roll or mode change.

## Sounds

| Event | Melody | When |
|---|---|---|
| Roll | `JumpUp` | Together with the result |
| Mode change | `BaDing` | Together with the smiley, after the values have flashed |

Both use `play melody … in background`. The built-in speaker requires a micro:bit V2. On a V1, the sounds only work with headphones or a buzzer on pin 0.

## Implementation notes

- **One display function**: `zeigen(wert)` handles all display logic, and both the roll and the mode flash use it.
- **Adding a mode**: change `zeigen`, `von` and `bis`, the `3` in `% 3`, and the step passed by button A, which is always the number of modes minus one.
- **Loop start**: the MakeCode *for* block always counts from 0. `modusWechseln` therefore loops from 0 to `bis[modus]` and skips the values below `von[modus]`.
- **Global variables**: all MakeCode variables are global, including loop variables and function parameters. The parameter of `modusWechseln` is called `richtung` so it doesn't clash with the loop variable `schritt` in `wuerfeln`.
- **Blocks used**: there are no sprites and no game engine. Only Basic, Input, LED, Music, Logic, Loops, Math, Variables, Arrays and Functions blocks are used.

## Use as a ts2blocks.py test case

`dice.ts` uses constructs that `egoshooter.ts` doesn't:

| Construct | Example in `dice.ts` |
|---|---|
| Nested math reporters | `(modus + richtung) % 3` (remainder block around a sum) |
| Remainder in a comparison | `wert % 2 == 1` |
| `≥` and `≠` comparisons | `wert >= 2`, `index >= von[modus]`, `modus != 2` |
| Array literals and indexing | `[0, 1, 0]`, `von[modus]` |
| Reporters nested three deep | `zeigen(randint(von[modus], bis[modus]))` |
| *repeat* loop with an unused counter | `for (let runde = 0; runde < 3; runde++)` |
| Counting loop with a reporter as the end | `for (let index = 0; index <= bis[modus]; index++)` |
| Nested loops | *repeat* around *for* in `wuerfeln` |
| Math reporters as API arguments | `led.plot(4 - schritt, 4)` |
| Nested `if` / `else` inside `if` / `else if` / `else` | Coin branch inside `zeigen` |
| Top-level variables declared after the event handlers | `let modus`, `von`, `bis` at the end of the file |

**Findings while building it:**
- **Faint outlines**: in the first version, a math block nested in another math block (same color) was hard to see. As a result, reporter outlines were darkened.
- **Image blocks added**: `images.arrowImage`, `images.arrowNumber` and `image.plotImage` were added to the API table while trying an arrow animation.
- **Variable clashes aren't detected**: ts2blocks doesn't warn when a function parameter and a loop variable share a name. MakeCode treats both as the same global variable. This was caught by hand.

## Known limitations

- **Overlapping actions**: rolling or changing the mode while an animation runs starts the next action right after the current one. A mode change during a roll can affect that roll's result.
- **Hidden mode**: the smiley confirms a mode change but doesn't say which mode is active. The flashed values show it.
