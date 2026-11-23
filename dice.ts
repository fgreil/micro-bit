// Einen Wert zeigen, passend zum Modus.
function zeigen (wert: number) {
    if (modus == 0) {
        // Münze: 1 = voller Kreis (Kopf), 0 = Ring (Zahl)
        if (wert == 1) {
            basic.showLeds(`
                . # # # .
                # # # # #
                # # # # #
                # # # # #
                . # # # .
                `)
        } else {
            basic.showLeds(`
                . # # # .
                # . . . #
                # . . . #
                # . . . #
                . # # # .
                `)
        }
    } else if (modus == 2) {
        // Zahl von 0 bis 9
        basic.showNumber(wert)
    } else {
        // Würfel mit 6 Seiten: Augen malen
        basic.clearScreen()
        // Ungerade Zahl (1, 3, 5): Punkt in der Mitte
        if (wert % 2 == 1) {
            led.plot(2, 2)
        }
        // Ab 2: oben links und unten rechts
        if (wert >= 2) {
            led.plot(0, 0)
            led.plot(4, 4)
        }
        // Ab 4: oben rechts und unten links
        if (wert >= 4) {
            led.plot(4, 0)
            led.plot(0, 4)
        }
        // Bei 6: links und rechts in der Mitte
        if (wert == 6) {
            led.plot(0, 2)
            led.plot(4, 2)
        }
    }
}
// Würfeln: 4 Punkte drehen sich 3 Runden am Rand entlang.
// Dann kommt das Ergebnis mit Ton.
function wuerfeln () {
    for (let runde = 0; runde < 3; runde++) {
        for (let schritt = 0; schritt <= 3; schritt++) {
            basic.clearScreen()
            // Ein Punkt auf jeder Seite: oben, rechts, unten, links
            led.plot(schritt, 0)
            led.plot(4, schritt)
            led.plot(4 - schritt, 4)
            led.plot(0, 4 - schritt)
            basic.pause(50)
        }
    }
    music.play(music.builtInPlayableMelody(Melodies.JumpUp), music.PlaybackMode.InBackground)
    zeigen(randint(von[modus], bis[modus]))
}
// Modus wechseln: alle möglichen Werte blitzen kurz auf.
// Dann kommt ein Ton und ein Smiley: Der neue Modus ist da.
function modusWechseln (richtung: number) {
    modus = (modus + richtung) % 3
    for (let index = 0; index <= bis[modus]; index++) {
        if (index >= von[modus]) {
            zeigen(index)
            // Die Zahlen 0 bis 9 blitzen schneller (ohne Extra-Pause).
            if (modus != 2) {
                basic.pause(200)
            }
        }
    }
    music.play(music.builtInPlayableMelody(Melodies.BaDing), music.PlaybackMode.InBackground)
    basic.showIcon(IconNames.Happy)
}
// Knopf A: ein Modus zurück (2 weiter ist wie 1 zurück).
input.onButtonPressed(Button.A, function () {
    modusWechseln(2)
})
// Knopf B: ein Modus weiter. Nach 2 kommt wieder 0.
input.onButtonPressed(Button.B, function () {
    modusWechseln(1)
})
// Knopf A und B zusammen: würfeln
input.onButtonPressed(Button.AB, function () {
    wuerfeln()
})
// Schütteln: würfeln
input.onGesture(Gesture.Shake, function () {
    wuerfeln()
})
// Modus 0 = Münze, 1 = Würfel, 2 = Zahl 0 bis 9
// Wir fangen mit dem Würfel an.
let modus = 1
// Kleinster und größter Wert in jedem Modus
let von = [0, 1, 0]
let bis = [1, 6, 9]
