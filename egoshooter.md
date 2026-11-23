# egoshooter.ts

A minimal shooter for the BBC micro:bit **V2**, played on the 5×5 LED display. It uses sprites from the MakeCode **Game** category and built-in melodies from the **Music** category. Code comments are in simple German for 3rd-grade pupils.

## Files

| File | Purpose |
|---|---|
| `egoshooter.ts` | MakeCode JavaScript. Paste it into the JavaScript tab, then switch to Blocks. |
| `egoshooter.md` | This documentation. |
| `Kurzanleitung.md` | How to play, in German, for children. It doesn't mention the code. |

## Gameplay rules

- **Spaceship**: a sprite at the bottom row (y = 4), starting at x = 2. **A** moves it left and **B** moves it right. It stops at the edges because sprite coordinates are clamped to 0–4.
- **Laser**: pressing **A+B** draws a vertical line of 4 LEDs (rows 0–3) above the ship for 200 ms and plays a sound. Shooting has no limit or cost. Each shot pauses the engine, and the `forever` loop skips steps while paused, so firing repeatedly slows the monster down. This is intended: pupils are meant to discover it themselves, so `Kurzanleitung.md` doesn't mention it.
- **Monster**: one sprite at a time. It starts at y = 0 in a random column and drops 1 pixel every `800 − 50 × lives` ms. It falls faster the more lives the player has:

  | Lives | Time per pixel |
  |---|---|
  | 1 | 750 ms |
  | 3 | 650 ms |
  | 8 | 400 ms |

- **Monster hits the ship**: when the monster arrives in row 4 at the ship's x, the ship is destroyed. The full screen flashes, a crash sound plays and the player loses a life.
- **Monster misses**: after one step's time in row 4 it disappears and a new monster spawns. Nothing else happens.
- **Laser hits the monster**: if the monster is in the ship's column and y < 4, a sound plays, the player gains a life and a new monster spawns.
- **Lives**: the player starts with 3. Whenever the number changes, the new value is shown for about 0.5 s while the game is paused.
- **End**:
  - At 9 lives the player wins: a win sound plays and a happy face is shown.
  - At 0 lives the game is over: a lose sound plays and a sad face is shown.
  - The face stays on screen and the game stops.
- **Restart**: shaking the micro:bit after the end starts a new game with 3 lives, the ship back in the middle and a new monster. Shaking during a game does nothing.

## Sounds

| Event | Melody |
|---|---|
| Laser shot | `JumpUp` |
| Monster killed | `BaDing` |
| Ship destroyed | `Wawawawaa` |
| Win | `PowerUp` |
| Game over | `PowerDown` |

On a micro:bit V1, the sounds only work with headphones or a buzzer on pin 0.

## Implementation notes

- **Rendering**: the sprite engine continuously redraws the screen, which would overwrite `showNumber`, `showLeds`, `showIcon` and `plot`. Every overlay is therefore drawn after `game.pause()`.
- **Pause as the single state flag**:
  - `game.isPaused()` doubles as the game-state flag. The `forever` loop and the A+B handler do nothing while the engine is paused.
  - At the end, `lebenAendern` doesn't resume the engine, so the game stays stopped.
  - The shake handler identifies the end state by `leben == 0 || leben == 9` and resumes the engine.
- **No built-in lives**: the Game category's built-in lives and game-over screen (`game.setLife`, `game.removeLife`, `game.gameOver`) are deliberately not used. Lives are kept in the variable `leben`.
- **Functions**:
  - `neuesMonster()`: puts the monster at a random x with y = 0.
  - `lebenAendern(zahl)`:
    1. Pauses the engine.
    2. Adds `zahl` to the lives and shows the new number.
    3. Then it does one of three things:
       - at 9: win sound and happy face
       - at 0: lose sound and sad face
       - otherwise: resumes the game
- **Ship flash**: the flash is drawn with `showLeds` (about 400 ms) directly before `lebenAendern(-1)`. The number then replaces it.
- **A+B**: the A and B handlers don't fire when both buttons are pressed together (micro:bit multi-button behaviour).

## Known limitations

- **Hard button combination**: A+B has to be pressed exactly together. Otherwise it registers as A or B and moves the ship instead. The V2 touch logo could be a simpler fire button.
- **Overlapping sounds**: sounds play in the background. A sound that starts while another is playing may cut it off or overlap it.
- **Late speed change**: the new speed applies from the next step, because the current wait has already started.
- **Silent controls at the end**: after the game ends, A and B still move the invisible ship. The ship is reset to the middle on restart.
- **No starting display**: the starting value of 3 lives isn't shown at the start or after a restart.
