// Ein neues Monster fängt oben an, in einer zufälligen Spalte.
function neuesMonster () {
    monster.set(LedSpriteProperty.X, randint(0, 4))
    monster.set(LedSpriteProperty.Y, 0)
}
// Die Leben ändern sich. Wir zeigen die neue Zahl.
// Bei 9 hast du gewonnen: fröhliches Gesicht.
// Bei 0 hast du verloren: trauriges Gesicht.
// Dann ist das Spiel aus, bis du den micro:bit schüttelst.
function lebenAendern (zahl: number) {
    game.pause()
    leben += zahl
    basic.showNumber(leben)
    basic.pause(500)
    if (leben == 9) {
        music.play(music.builtInPlayableMelody(Melodies.PowerUp), music.PlaybackMode.InBackground)
        basic.showIcon(IconNames.Happy)
    } else if (leben == 0) {
        music.play(music.builtInPlayableMelody(Melodies.PowerDown), music.PlaybackMode.InBackground)
        basic.showIcon(IconNames.Sad)
    } else {
        game.resume()
    }
}
// Knopf A: Das Raumschiff fliegt nach links.
input.onButtonPressed(Button.A, function () {
    schiff.change(LedSpriteProperty.X, -1)
})
// Knopf B: Das Raumschiff fliegt nach rechts.
input.onButtonPressed(Button.B, function () {
    schiff.change(LedSpriteProperty.X, 1)
})
// Knopf A und B zusammen: Laser!
// Der Laser ist ein Strich mit 4 Lichtern über dem Raumschiff.
input.onButtonPressed(Button.AB, function () {
    if (!(game.isPaused())) {
        game.pause()
        music.play(music.builtInPlayableMelody(Melodies.JumpUp), music.PlaybackMode.InBackground)
        for (let zeile = 0; zeile <= 3; zeile++) {
            led.plot(schiff.get(LedSpriteProperty.X), zeile)
        }
        basic.pause(200)
        game.resume()
        // Getroffen? Das Monster ist in der gleichen Spalte und noch nicht ganz unten.
        if (monster.get(LedSpriteProperty.X) == schiff.get(LedSpriteProperty.X) && monster.get(LedSpriteProperty.Y) < 4) {
            music.play(music.builtInPlayableMelody(Melodies.BaDing), music.PlaybackMode.InBackground)
            neuesMonster()
            lebenAendern(1)
        }
    }
})
// Schütteln: Wenn das Spiel aus ist, fängt es neu an.
input.onGesture(Gesture.Shake, function () {
    if (leben == 0 || leben == 9) {
        leben = 3
        schiff.set(LedSpriteProperty.X, 2)
        neuesMonster()
        game.resume()
    }
})
// Du hast am Anfang 3 Leben.
let leben = 3
// Dein Raumschiff steht unten in der Mitte.
let schiff = game.createSprite(2, 4)
// Das Monster
let monster = game.createSprite(0, 0)
neuesMonster()
// Immer wieder: Das Monster fällt ein Stück nach unten.
// Je mehr Leben du hast, desto schneller fällt es.
// Wenn das Spiel Pause macht, wartet das Monster.
basic.forever(function () {
    basic.pause(800 - 50 * leben)
    if (!(game.isPaused())) {
        if (monster.get(LedSpriteProperty.Y) == 4) {
            neuesMonster()
        } else {
            monster.change(LedSpriteProperty.Y, 1)
            // Unten angekommen und auf dem Raumschiff? Krach! Alles blitzt hell auf.
            if (monster.isTouching(schiff)) {
                game.pause()
                music.play(music.builtInPlayableMelody(Melodies.Wawawawaa), music.PlaybackMode.InBackground)
                basic.showLeds(`
                    # # # # #
                    # # # # #
                    # # # # #
                    # # # # #
                    # # # # #
                    `)
                lebenAendern(-1)
            }
        }
    }
})
