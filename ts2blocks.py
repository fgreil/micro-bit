#!/usr/bin/env python3
"""ts2blocks.py - draw a MakeCode micro:bit program (.ts) as MakeCode-style blocks in an SVG.

Usage:
    python3 ts2blocks.py egoshooter.ts                 # writes egoshooter.svg
    python3 ts2blocks.py game.ts -o out.svg -c 3       # 3 columns
    python3 ts2blocks.py game.ts --wrap 60             # wider comment notes

Reads the JavaScript/TypeScript that MakeCode produces (functions, events, if/else,
loops, variables, expressions, // comments). Known micro:bit APIs get their English
MakeCode block text and category color; unknown calls are drawn generically.
Pillow (PIL) is optional and only used for exact text widths.
"""
import argparse, html, re, sys, textwrap

# ---------------------------------------------------------------- tokenizer
TOKEN_RE = re.compile(r'''
 (?P<ws>\s+)
|(?P<lc>//[^\n]*)
|(?P<bc>/\*.*?\*/)
|(?P<num>0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+)
|(?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
|(?P<tmpl>`(?:\\.|[^`\\])*`)
|(?P<id>[A-Za-z_$][\w$]*)
|(?P<op>===|!==|=>|==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|\*=|/=|%=|[-+*/%=<>!&|^~?:;,.(){}\[\]])
''', re.S | re.X)


class Tok:
    def __init__(s, k, v, c): s.k, s.v, s.c = k, v, c


def tokenize(src):
    toks, pending, pos = [], [], 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f'unexpected character {src[pos]!r} at line {src.count(chr(10), 0, pos) + 1}')
        pos, k, v = m.end(), m.lastgroup, m.group()
        if k == 'ws':
            continue
        if k == 'lc':
            pending.append(v[2:].strip())
        elif k == 'bc':
            pending += [l.strip(' *') for l in v[2:-2].splitlines() if l.strip(' *')]
        else:
            toks.append(Tok(k, v, pending))
            pending = []
    toks.append(Tok('eof', '', pending))
    return toks


# ---------------------------------------------------------------- parser (MakeCode subset of TypeScript)
class Parser:
    BIN = [('||',), ('&&',), ('==', '!=', '===', '!=='), ('<', '<=', '>', '>='), ('+', '-'), ('*', '/', '%')]

    def __init__(s, toks): s.t, s.i = toks, 0
    def peek(s, o=0): return s.t[min(s.i + o, len(s.t) - 1)]
    def nxt(s):
        tok = s.t[s.i]; s.i += 1; return tok
    def at(s, v): return s.peek().k in ('op', 'id') and s.peek().v == v
    def at_op(s, *vs): return s.peek().k == 'op' and s.peek().v in vs
    def eat(s, v): return s.nxt() if s.at(v) else None
    def need(s, v):
        if not s.at(v):
            raise SyntaxError(f'expected {v!r} but found {s.peek().v!r}')
        return s.nxt()

    def skip_type(s):
        depth = 0
        while s.peek().k != 'eof':
            v = s.peek().v
            if depth == 0 and v in (',', ')', '=', ';', '{', '=>', '}'):
                return
            depth += v in ('(', '<', '[') and 1 or (v in (')', '>', ']') and -1 or 0)
            s.nxt()

    def program(s):
        body = []
        while s.peek().k != 'eof':
            body.append(s.stmt())
        return body

    def block(s):
        s.need('{'); body = []
        while not s.at('}'):
            body.append(s.stmt())
        s.need('}'); return body

    def body_of(s): return s.block() if s.at('{') else [s.stmt()]

    def stmt(s):
        com, s.peek().c = s.peek().c, []
        n = s._stmt(); n['com'] = com
        s.eat(';'); return n

    def _stmt(s):
        t = s.peek()
        if t.k == 'id':
            v = t.v
            if v == 'function' and s.peek(1).k == 'id':
                s.nxt(); name = s.nxt().v; ps = s.params()
                if s.eat(':'): s.skip_type()
                return dict(k='func', name=name, params=ps, body=s.block())
            if v in ('let', 'const', 'var'):
                s.nxt(); name = s.nxt().v
                if s.eat(':'): s.skip_type()
                return dict(k='let', name=name, val=s.expr() if s.eat('=') else None)
            if v == 'if':
                s.nxt(); branches, els = [(s.paren(), s.body_of())], None
                while s.eat('else'):
                    if s.eat('if'):
                        branches.append((s.paren(), s.body_of()))
                    else:
                        els = s.body_of(); break
                return dict(k='if', branches=branches, els=els)
            if v == 'while':
                s.nxt(); return dict(k='while', cond=s.paren(), body=s.body_of())
            if v == 'for':
                s.nxt(); s.need('(')
                s.eat('let') or s.eat('const') or s.eat('var')
                var = s.nxt().v
                if s.eat('of'):
                    arr = s.expr(); s.need(')')
                    return dict(k='forof', var=var, arr=arr, body=s.body_of())
                s.need('='); start = s.expr(); s.need(';')
                cond = s.expr(); s.need(';'); s.expr(); s.need(')')
                return dict(k='for', var=var, start=start, cond=cond, body=s.body_of())
            if v == 'return':
                s.nxt()
                val = None if s.at(';') or s.at('}') else s.expr()
                return dict(k='return', val=val)
            if v in ('break', 'continue'):
                s.nxt(); return dict(k=v)
        if s.at('{'):
            return dict(k='blockstmt', body=s.block())
        if s.at(';'):
            return dict(k='empty')
        return dict(k='expr', e=s.expr())

    def paren(s):
        s.need('('); e = s.expr(); s.need(')'); return e

    def params(s):
        s.need('('); ps = []
        while not s.at(')'):
            ps.append(s.nxt().v)
            if s.eat('?'): pass
            if s.eat(':'): s.skip_type()
            if s.eat('='): s.expr()
            s.eat(',')
        s.need(')'); return ps

    def expr(s):
        left = s.binary(0)
        if s.at_op('=', '+=', '-=', '*=', '/=', '%='):
            op = s.nxt().v
            return dict(k='assign', op=op, target=left, val=s.expr())
        if s.eat('?'):
            a = s.expr(); s.need(':')
            return dict(k='cond', c=left, a=a, b=s.expr())
        return left

    def binary(s, lvl):
        if lvl == len(s.BIN): return s.unary()
        left = s.binary(lvl + 1)
        while s.at_op(*s.BIN[lvl]):
            op = s.nxt().v
            left = dict(k='bin', op=op, a=left, b=s.binary(lvl + 1))
        return left

    def unary(s):
        if s.at_op('!', '-', '+'):
            op = s.nxt().v; return dict(k='un', op=op, e=s.unary())
        if s.at_op('++', '--'):
            op = s.nxt().v; return dict(k='upd', op=op, e=s.unary())
        return s.postfix()

    def postfix(s):
        e = s.primary()
        while True:
            if s.eat('.'):
                e = dict(k='mem', obj=e, name=s.nxt().v)
            elif s.at('('):
                e = dict(k='call', fn=e, args=s.args())
            elif s.eat('['):
                i = s.expr(); s.need(']'); e = dict(k='idx', obj=e, i=i)
            elif s.at_op('++', '--'):
                e = dict(k='upd', op=s.nxt().v, e=e)
            elif s.at('as'):
                s.nxt(); s.skip_type()
            else:
                return e

    def args(s):
        s.need('('); a = []
        while not s.at(')'):
            a.append(s.expr()); s.eat(',')
        s.need(')'); return a

    def arrow(s, ps):
        body = s.block() if s.at('{') else [dict(k='return', val=s.expr(), com=[])]
        return dict(k='fn', params=ps, body=body)

    def primary(s):
        t = s.nxt()
        if t.k == 'num': return dict(k='num', v=t.v)
        if t.k == 'str': return dict(k='str', v=t.v[1:-1])
        if t.k == 'tmpl': return dict(k='tmpl', v=t.v[1:-1])
        if t.k == 'id':
            if t.v in ('true', 'false'): return dict(k='bool', v=t.v)
            if t.v == 'function':
                if s.peek().k == 'id': s.nxt()
                ps = s.params()
                if s.eat(':'): s.skip_type()
                return dict(k='fn', params=ps, body=s.block())
            if t.v == 'new': return s.postfix()
            if s.eat('=>'): return s.arrow([t.v])
            return dict(k='id', v=t.v)
        if t.v == '(':
            depth, j = 1, s.i
            while depth and s.t[j].k != 'eof':
                if s.t[j].k == 'op': depth += (s.t[j].v == '(') - (s.t[j].v == ')')
                j += 1
            if s.t[j].v == '=>':
                s.i -= 1; ps = s.params(); s.need('=>'); return s.arrow(ps)
            e = s.expr(); s.need(')'); return e
        if t.v == '[':
            items = []
            while not s.at(']'):
                items.append(s.expr()); s.eat(',')
            s.need(']'); return dict(k='arr', items=items)
        raise SyntaxError(f'unexpected {t.v!r}')


# ---------------------------------------------------------------- MakeCode look
FONT, CFONT, PAD, GAP, ARM, NOTCH_X, FOOT = 13, 12, 10, 6, 16, 16, 22
CAT = dict(basic='#1E90FF', input='#D400D4', music='#E63022', led='#5C2D91', radio='#E3008C',
           loops='#00AA00', logic='#00A4A6', variables='#DC143C', math='#9400D3',
           functions='#3455DB', game='#007A4B', images='#7600A8', pins='#B22222',
           serial='#002050', control='#333333', text='#B8860B', arrays='#E65722', other='#7F7F7F')

try:
    from PIL import ImageFont
    _FONT = ImageFont.truetype('DejaVuSans.ttf', 100)
    def tw(t, size=FONT): return _FONT.getlength(t) * size / 100
except Exception:  # no Pillow or font: estimate
    def tw(t, size=FONT): return len(t) * size * 0.62


def shade(c, f=0.8):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02X%02X%02X' % tuple(int(v * f) for v in (r, g, b))


def esc(t): return html.escape(t, quote=True)


# API: dotted name -> (category, English block text, kind). kind: s=statement r=reporter b=boolean h=event
API = {
    'basic.forever': ('basic', 'forever', 'h'),
    'basic.showNumber': ('basic', 'show number {0}', 's'),
    'basic.showString': ('basic', 'show string {0}', 's'),
    'basic.showIcon': ('basic', 'show icon {0}', 's'),
    'basic.showLeds': ('basic', 'show leds {0}', 's'),
    'basic.showArrow': ('basic', 'show arrow {0}', 's'),
    'basic.clearScreen': ('basic', 'clear screen', 's'),
    'basic.pause': ('basic', 'pause (ms) {0}', 's'),
    'input.onButtonPressed': ('input', 'on button {0} pressed', 'h'),
    'input.onGesture': ('input', 'on {0}', 'h'),
    'input.onLogoEvent': ('input', 'on logo {0}', 'h'),
    'input.onPinPressed': ('input', 'on pin {0} pressed', 'h'),
    'input.onPinReleased': ('input', 'on pin {0} released', 'h'),
    'input.onSound': ('input', 'on {0} sound', 'h'),
    'input.buttonIsPressed': ('input', 'button {0} is pressed', 'b'),
    'input.logoIsPressed': ('input', 'logo is pressed', 'b'),
    'input.pinIsPressed': ('input', 'pin {0} is pressed', 'b'),
    'input.isGesture': ('input', 'is {0} gesture', 'b'),
    'input.acceleration': ('input', 'acceleration (mg) {0}', 'r'),
    'input.compassHeading': ('input', 'compass heading (°)', 'r'),
    'input.lightLevel': ('input', 'light level', 'r'),
    'input.temperature': ('input', 'temperature (°C)', 'r'),
    'input.soundLevel': ('input', 'sound level', 'r'),
    'input.rotation': ('input', 'rotation (°) {0}', 'r'),
    'input.magneticForce': ('input', 'magnetic force (µT) {0}', 'r'),
    'input.runningTime': ('input', 'running time (ms)', 'r'),
    'led.plot': ('led', 'plot x {0} y {1}', 's'),
    'led.unplot': ('led', 'unplot x {0} y {1}', 's'),
    'led.toggle': ('led', 'toggle x {0} y {1}', 's'),
    'led.point': ('led', 'point x {0} y {1}', 'b'),
    'led.plotBrightness': ('led', 'plot x {0} y {1} brightness {2}', 's'),
    'led.plotBarGraph': ('led', 'plot bar graph of {0} up to {1}', 's'),
    'led.setBrightness': ('led', 'set brightness {0}', 's'),
    'led.brightness': ('led', 'brightness', 'r'),
    'music.play': ('music', 'play {0} {1}', 's'),
    'music.builtInPlayableMelody': ('music', 'melody {0}', 'r'),
    'music.builtinPlayableSoundEffect': ('music', 'sound {0}', 'r'),
    'music.stringPlayable': ('music', 'melody {0} at tempo {1} (bpm)', 'r'),
    'music.tonePlayable': ('music', 'tone {0} for {1}', 'r'),
    'music.playTone': ('music', 'play tone {0} for {1}', 's'),
    'music.ringTone': ('music', 'ring tone (Hz) {0}', 's'),
    'music.rest': ('music', 'rest {0}', 's'),
    'music.stopAllSounds': ('music', 'stop all sounds', 's'),
    'music.setVolume': ('music', 'set volume {0}', 's'),
    'music.setTempo': ('music', 'set tempo to (bpm) {0}', 's'),
    'music.startMelody': ('music', 'start melody {0} repeating {1}', 's'),
    'music.builtInMelody': ('music', '{0}', 'r'),
    'music.beat': ('music', '{0} beat', 'r'),
    'game.createSprite': ('game', 'create sprite at x: {0} y: {1}', 'r'),
    'game.pause': ('game', 'pause', 's'),
    'game.resume': ('game', 'resume', 's'),
    'game.isPaused': ('game', 'is paused', 'b'),
    'game.isRunning': ('game', 'is running', 'b'),
    'game.isGameOver': ('game', 'is game over', 'b'),
    'game.gameOver': ('game', 'game over', 's'),
    'game.addScore': ('game', 'change score by {0}', 's'),
    'game.setScore': ('game', 'set score {0}', 's'),
    'game.score': ('game', 'score', 'r'),
    'game.setLife': ('game', 'set life {0}', 's'),
    'game.addLife': ('game', 'add life {0}', 's'),
    'game.removeLife': ('game', 'remove life {0}', 's'),
    'game.startCountdown': ('game', 'start countdown (ms) {0}', 's'),
    'radio.setGroup': ('radio', 'radio set group {0}', 's'),
    'radio.sendNumber': ('radio', 'radio send number {0}', 's'),
    'radio.sendString': ('radio', 'radio send string {0}', 's'),
    'radio.sendValue': ('radio', 'radio send value {0} = {1}', 's'),
    'radio.onReceivedNumber': ('radio', 'on radio received', 'h'),
    'radio.onReceivedString': ('radio', 'on radio received', 'h'),
    'radio.onReceivedValue': ('radio', 'on radio received', 'h'),
    'pins.digitalWritePin': ('pins', 'digital write pin {0} to {1}', 's'),
    'pins.digitalReadPin': ('pins', 'digital read pin {0}', 'r'),
    'pins.analogWritePin': ('pins', 'analog write pin {0} to {1}', 's'),
    'pins.analogReadPin': ('pins', 'analog read pin {0}', 'r'),
    'pins.servoWritePin': ('pins', 'servo write pin {0} to {1}', 's'),
    'randint': ('math', 'pick random {0} to {1}', 'r'),
    'Math.randomRange': ('math', 'pick random {0} to {1}', 'r'),
    'Math.randomBoolean': ('math', 'random true or false', 'b'),
    'Math.abs': ('math', 'absolute of {0}', 'r'),
    'Math.round': ('math', 'round {0}', 'r'),
    'Math.floor': ('math', 'floor {0}', 'r'),
    'Math.ceil': ('math', 'ceiling {0}', 'r'),
    'Math.sqrt': ('math', 'square root {0}', 'r'),
    'Math.min': ('math', 'min of {0} and {1}', 'r'),
    'Math.max': ('math', 'max of {0} and {1}', 'r'),
    'Math.idiv': ('math', 'integer {0} ÷ {1}', 'r'),
    'Math.map': ('math', 'map {0} from low {1} high {2} to low {3} high {4}', 'r'),
    'Math.constrain': ('math', 'constrain {0} between {1} and {2}', 'r'),
    'control.reset': ('control', 'reset', 's'),
    'control.inBackground': ('control', 'run in background', 'h'),
    'serial.writeLine': ('serial', 'serial write line {0}', 's'),
    'serial.writeNumber': ('serial', 'serial write number {0}', 's'),
    'serial.writeValue': ('serial', 'serial write value {0} = {1}', 's'),
    'images.createImage': ('images', '{0}', 'r'),
    'images.createBigImage': ('images', '{0}', 'r'),
    'images.iconImage': ('images', 'icon image {0}', 'r'),
    'images.arrowImage': ('images', 'arrow image {0}', 'r'),
    'images.arrowNumber': ('images', 'arrow {0}', 'r'),
    'convertToText': ('text', 'convert {0} to text', 'r'),
    'parseInt': ('text', 'parse to number {0}', 'r'),
}
# instance methods (sprites, images, arrays, text): {0} is the object
METHODS = {
    'change': ('game', '{0} change {1} by {2}', 's'),
    'set': ('game', '{0} set {1} to {2}', 's'),
    'get': ('game', '{0} {1}', 'r'),
    'move': ('game', '{0} move by {1}', 's'),
    'turn': ('game', '{0} turn {1} by (°) {2}', 's'),
    'ifOnEdgeBounce': ('game', '{0} if on edge, bounce', 's'),
    'isTouching': ('game', 'is {0} touching {1}', 'b'),
    'isTouchingEdge': ('game', 'is {0} touching edge', 'b'),
    'delete': ('game', 'delete {0}', 's'),
    'showImage': ('images', 'show image {0} at offset {1}', 's'),
    'plotImage': ('images', 'plot image {0} at offset {1}', 's'),
    'scrollImage': ('images', 'scroll image {0} with offset {1} and interval (ms) {2}', 's'),
    'push': ('arrays', '{0} add value {1} to end', 's'),
    'pop': ('arrays', 'get and remove last value from {0}', 'r'),
    'removeAt': ('arrays', '{0} remove value at {1}', 'r'),
    'insertAt': ('arrays', '{0} insert at {1} value {2}', 's'),
    'indexOf': ('arrays', '{0} find index of {1}', 'r'),
    'charAt': ('text', 'char from {0} at {1}', 'r'),
    'substr': ('text', 'substring of {0} from {1} of length {2}', 'r'),
    'compare': ('text', 'compare {0} to {1}', 'r'),
}
NAMESPACES = set(CAT) | {'Math', 'neopixel', 'bluetooth', 'datalogger', 'power'}
KEEP_CASE = {'Button', 'DigitalPin', 'AnalogPin', 'TouchPin', 'AnalogReadWritePin'}
SYMBOLS = {'*': '×', '/': '÷', '==': '=', '===': '=', '!=': '≠', '!==': '≠', '<=': '≤', '>=': '≥',
           '&&': 'and', '||': 'or'}


def grid(s): return [r.split() for r in s.strip().split('/')]


ICONS = {
    'Heart': grid('. # . # . / # # # # # / # # # # # / . # # # . / . . # . .'),
    'SmallHeart': grid('. . . . . / . # . # . / . # # # . / . . # . . / . . . . .'),
    'Yes': grid('. . . . . / . . . . # / . . . # . / # . # . . / . # . . .'),
    'No': grid('# . . . # / . # . # . / . . # . . / . # . # . / # . . . #'),
    'Happy': grid('. . . . . / . # . # . / . . . . . / # . . . # / . # # # .'),
    'Sad': grid('. . . . . / . # . # . / . . . . . / . # # # . / # . . . #'),
    'Square': grid('# # # # # / # . . . # / # . . . # / # . . . # / # # # # #'),
    'SmallSquare': grid('. . . . . / . # # # . / . # . # . / . # # # . / . . . . .'),
    'Diamond': grid('. . # . . / . # . # . / # . . . # / . # . # . / . . # . .'),
    'SmallDiamond': grid('. . . . . / . . # . . / . # . # . / . . # . . / . . . . .'),
}


# ---------------------------------------------------------------- inline elements
class Label:
    def __init__(s, t, fill='#fff', size=FONT):
        s.t, s.fill, s.size = t, fill, size
        s.w, s.h = tw(t, size), size + 4

    def svg(s, x, y, out):
        out.append(f'<text x="{x:.1f}" y="{y + s.h / 2 + s.size * 0.36:.1f}" fill="{s.fill}" '
                   f'font-size="{s.size}">{esc(s.t)}</text>')


class LEDGrid:
    def __init__(s, rows, color, small=False):
        s.rows, s.off = rows, shade(color, 0.45 if small else 0.55)
        s.cell, s.gap = (6, 1.5) if small else (13, 3)
        s.w = len(rows[0]) * s.cell + (len(rows[0]) - 1) * s.gap
        s.h = len(rows) * s.cell + (len(rows) - 1) * s.gap

    def svg(s, x, y, out):
        for r, row in enumerate(s.rows):
            for c, ch in enumerate(row):
                out.append(f'<rect x="{x + c * (s.cell + s.gap):.1f}" y="{y + r * (s.cell + s.gap):.1f}" '
                           f'width="{s.cell}" height="{s.cell}" rx="{s.cell * 0.2:.1f}" '
                           f'fill="{"#fff" if ch == "#" else s.off}"/>')


def row_w(parts): return sum(p.w for p in parts) + GAP * max(len(parts) - 1, 0)
def row_h(parts): return max([p.h for p in parts] + [FONT + 4])


def draw_row(parts, x, y, h, out):
    for p in parts:
        p.svg(x, y + (h - p.h) / 2, out); x += p.w + GAP


class Box:
    """Reporter/boolean block, input field or dropdown that sits inside a block."""
    def __init__(s, parts, fill, shape='round', stroke=None):
        s.p, s.fill, s.shape, s.stroke = parts, fill, shape, stroke or shade(fill, 0.6)
        s.h = max(24, row_h(parts) + 8)
        s.pad = s.h / 2 if shape == 'bool' else 8
        s.w = max(row_w(parts) + 2 * s.pad, s.h if shape == 'round' else 0)

    def svg(s, x, y, out):
        w, h = s.w, s.h
        if s.shape == 'bool':
            pts = [(x + h / 2, y), (x + w - h / 2, y), (x + w, y + h / 2), (x + w - h / 2, y + h),
                   (x + h / 2, y + h), (x, y + h / 2)]
            out.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" '
                       f'fill="{s.fill}" stroke="{s.stroke}"/>')
        else:
            rx = h / 2 if s.shape == 'round' else 4
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" '
                       f'fill="{s.fill}" stroke="{s.stroke}"/>')
        draw_row(s.p, x + (w - row_w(s.p)) / 2, y, h, out)


def field(t): return Box([Label(t, '#333')], '#fff', 'round', '#C8C8C8')
def dropdown(t, color): return Box([Label(t + ' ▾')], shade(color), 'rect', shade(color, 0.65))
def var_pill(name): return Box([Label(name)], CAT['variables'])


# ---------------------------------------------------------------- stack blocks
def notch_r(): return 'l 6,4 3,0 6,-4'      # drawn going right: dent into the block
def notch_l(): return 'l -6,4 -3,0 -6,-4'   # drawn going left: tab sticking out below


class Stmt:
    def __init__(s, parts, color, com=None):
        s.p, s.c, s.com = parts, color, com or []
        s.h = max(40, row_h(parts) + 16)
        s.w = max(row_w(parts) + 2 * PAD, 60)

    def render(s, x, y, out, coms):
        r, w, h = 4, s.w, s.h
        d = (f'M {x},{y + r} a {r},{r} 0 0 1 {r},{-r} H {x + NOTCH_X} {notch_r()} H {x + w - r} '
             f'a {r},{r} 0 0 1 {r},{r} V {y + h - r} a {r},{r} 0 0 1 {-r},{r} '
             f'H {x + NOTCH_X + 15} {notch_l()} H {x + r} a {r},{r} 0 0 1 {-r},{-r} Z')
        out.append(f'<path d="{d}" fill="{s.c}" stroke="{shade(s.c)}"/>')
        draw_row(s.p, x + PAD, y, h, out)
        if s.com: coms.append((x + s.w, y, s.com))


class CBlock:
    """Block with one or more mouths: if/else, loops, events, functions."""
    def __init__(s, sections, color, hat=False, com=None):
        s.sec, s.c, s.hat, s.com = sections, color, hat, com or []
        s.hh = [max(40, row_h(p) + 16) for p, _ in sections]
        s.bh = [max(24, sum(b.h for b in body)) for _, body in sections]
        s.W = max(max(row_w(p) for p, _ in sections) + 2 * PAD, ARM + NOTCH_X + 50)
        s.w = max([s.W] + [ARM + b.w for _, body in sections for b in body])
        s.h = sum(s.hh) + sum(s.bh) + FOOT

    def render(s, x, y, out, coms):
        r, W, A = (8 if s.hat else 4), s.W, ARM
        d = [f'M {x},{y + r} a {r},{r} 0 0 1 {r},{-r}']
        if not s.hat: d.append(f'H {x + NOTCH_X} {notch_r()}')
        d.append(f'H {x + W - r} a {r},{r} 0 0 1 {r},{r}')
        cy = y
        for hh, bh in zip(s.hh, s.bh):
            d.append(f'V {cy + hh - 4} a 4,4 0 0 1 -4,4 H {x + A + NOTCH_X + 15} {notch_l()} '
                     f'H {x + A} V {cy + hh + bh} H {x + A + NOTCH_X} {notch_r()} H {x + W - 4} a 4,4 0 0 1 4,4')
            cy += hh + bh
        d.append(f'V {cy + FOOT - r} a {r},{r} 0 0 1 {-r},{r}')
        if not s.hat: d.append(f'H {x + NOTCH_X + 15} {notch_l()}')
        d.append(f'H {x + r} a {r},{r} 0 0 1 {-r},{-r} Z')
        out.append(f'<path d="{" ".join(d)}" fill="{s.c}" stroke="{shade(s.c)}"/>')
        if s.com: coms.append((x + W, y, s.com))
        cy = y
        for (parts, body), hh, bh in zip(s.sec, s.hh, s.bh):
            draw_row(parts, x + PAD, cy, hh, out)
            by = cy + hh
            for b in body:
                b.render(x + A, by, out, coms); by += b.h
            cy += hh + bh


# ---------------------------------------------------------------- AST -> blocks
FUNCS = set()


def dotted(e):
    if e['k'] == 'id': return e['v']
    if e['k'] == 'mem':
        o = dotted(e['obj'])
        return o and f'{o}.{e["name"]}'


def enum_label(d):
    segs = d.split('.')
    if segs[-1] == 'AB': return 'A+B'
    if len(segs) > 1 and segs[-2] in KEEP_CASE: return segs[-1]
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', segs[-1]).lower()


def led_rows(t):
    if set(t) - set('#. \n\t\r'): return None
    rows = [re.findall(r'[#.]', l) for l in t.splitlines()]
    rows = [r for r in rows if r]
    return rows if rows and len(rows) == 5 and len({len(r) for r in rows}) == 1 else None


def E(e, color):
    """Expression -> inline element."""
    k = e['k']
    if k == 'num': return field(e['v'])
    if k == 'str': return field(f'"{e["v"]}"')
    if k == 'tmpl':
        rows = led_rows(e['v'])
        return LEDGrid(rows, color) if rows else field(e['v'].strip())
    if k == 'bool': return Box([Label(e['v'])], CAT['logic'], 'bool')
    if k == 'id': return field(e['v']) if e['v'] in ('null', 'undefined') else var_pill(e['v'])
    if k == 'mem':
        d = dotted(e)
        if d and any(seg[:1].isupper() for seg in d.split('.')[:-1]):
            if d.startswith('IconNames.') and e['name'] in ICONS:
                return Box([LEDGrid(ICONS[e['name']], shade(color), small=True), Label('▾')],
                           shade(color), 'rect', shade(color, 0.65))
            return dropdown(enum_label(d), color)
        if e['name'] == 'length':
            return Box([Label('length of'), E(e['obj'], CAT['arrays'])], CAT['arrays'])
        return Box([E(e['obj'], CAT['other']), Label(e['name'])], CAT['other'])
    if k == 'bin':
        op = e['op']
        if op == '%':
            return Box([Label('remainder of'), E(e['a'], CAT['math']), Label('÷'), E(e['b'], CAT['math'])], CAT['math'])
        cat = 'math' if op in '+-*/' else 'logic'
        return Box([E(e['a'], CAT[cat]), Label(SYMBOLS.get(op, op)), E(e['b'], CAT[cat])], CAT[cat],
                   'round' if cat == 'math' else 'bool')
    if k == 'un':
        if e['op'] == '!': return Box([Label('not'), E(e['e'], CAT['logic'])], CAT['logic'], 'bool')
        if e['e']['k'] == 'num': return field(e['op'].strip('+') + e['e']['v'])
        return Box([Label(e['op']), E(e['e'], CAT['math'])], CAT['math'])
    if k == 'call': return call_block(e, color, stmt=False)
    if k == 'cond':
        L = CAT['logic']
        return Box([Label('if'), E(e['c'], L), Label('then'), E(e['a'], L), Label('else'), E(e['b'], L)], L)
    if k == 'arr':
        return Box([Label('array of')] + [E(i, CAT['arrays']) for i in e['items']], CAT['arrays'])
    if k == 'idx':
        A = CAT['arrays']
        return Box([E(e['obj'], A), Label('get value at'), E(e['i'], A)], A)
    if k == 'fn': return Label('function')
    return Label('?')


def tpl_parts(tpl, args, color):
    out = []
    for piece in re.split(r'(\{\d+\})', tpl):
        m = re.fullmatch(r'\{(\d+)\}', piece)
        if m:
            if int(m[1]) < len(args): out.append(E(args[int(m[1])], color))
        elif piece.strip():
            out.append(Label(piece.strip()))
    return out


def call_block(e, color, stmt, com=None):
    fn, args = e['fn'], e['args']
    name = dotted(fn)
    plain = [a for a in args if a['k'] != 'fn']
    fns = [a for a in args if a['k'] == 'fn']
    if name in API:
        cat, tpl, kind = API[name]; targs = plain
    elif name in FUNCS:
        cat, kind, targs = 'functions', 's', plain
        tpl = f'call {name}' + ''.join(f' {{{i}}}' for i in range(len(plain)))
    elif fn['k'] == 'mem' and fn['name'] in METHODS and (dotted(fn['obj']) or '').split('.')[0] not in NAMESPACES:
        cat, tpl, kind = METHODS[fn['name']]; targs = [fn['obj']] + plain
    elif name and name.split('.')[0] in NAMESPACES:   # unknown API call
        segs = name.split('.')
        cat, kind, targs = (segs[0] if segs[0] in CAT else 'other'), 's', plain
        tpl = ' '.join(segs[1:] if segs[0] in CAT else segs) + ''.join(f' {{{i}}}' for i in range(len(plain)))
    elif fn['k'] == 'mem':                              # unknown method on a variable
        cat, kind, targs = 'other', 's', [fn['obj']] + plain
        tpl = '{0} ' + fn['name'] + ''.join(f' {{{i + 1}}}' for i in range(len(plain)))
    else:
        cat, kind, targs = 'other', 's', plain
        tpl = (name or 'call') + ''.join(f' {{{i}}}' for i in range(len(plain)))
    c = CAT.get(cat, CAT['other'])
    parts = tpl_parts(tpl, targs, c)
    if fns:  # event handler / callback -> hat block with body
        parts += [var_pill(p) for p in fns[-1]['params']]
        return CBlock([(parts, build_stmts(fns[-1]['body']))], c, hat=True, com=com)
    if stmt: return Stmt(parts, c, com)
    return Box(parts, c, 'bool' if kind == 'b' else 'round')


def assign_block(e, com):
    V, t, op, val = CAT['variables'], e['target'], e['op'], e['val']
    if t['k'] != 'id':
        return Stmt([Label('set'), E(t, V), Label('to'), E(val, V)], V, com)
    if op == '=':
        return Stmt([Label('set'), dropdown(t['v'], V), Label('to'), E(val, V)], V, com)
    if op in ('+=', '-='):
        by = val if op == '+=' else dict(k='un', op='-', e=val)
        return Stmt([Label('change'), dropdown(t['v'], V), Label('by'), E(by, V)], V, com)
    return Stmt([Label('set'), dropdown(t['v'], V), Label('to'),
                 E(dict(k='bin', op=op[0], a=t, b=val), V)], V, com)


def build_stmts(stmts): return [b for n in stmts for b in build_stmt(n)]


def build_stmt(n):
    k, com = n['k'], n.get('com', [])
    L, LP, F, V = CAT['logic'], CAT['loops'], CAT['functions'], CAT['variables']
    if k == 'func':
        parts = [Label('function ' + n['name'])] + [var_pill(p) for p in n['params']]
        return [CBlock([(parts, build_stmts(n['body']))], F, hat=True, com=com)]
    if k == 'let':
        return [Stmt([Label('set'), dropdown(n['name'], V), Label('to'),
                      E(n['val'], V) if n['val'] else field('0')], V, com)]
    if k == 'if':
        secs = [([Label('if' if i == 0 else 'else if'), E(c, L), Label('then')], build_stmts(b))
                for i, (c, b) in enumerate(n['branches'])]
        if n['els'] is not None: secs.append(([Label('else')], build_stmts(n['els'])))
        return [CBlock(secs, L, com=com)]
    if k == 'while':
        return [CBlock([([Label('while'), E(n['cond'], LP)], build_stmts(n['body']))], LP, com=com)]
    if k == 'for':
        c, var, start = n['cond'], n['var'], n['start']
        if c['k'] == 'bin' and c['op'] in ('<', '<=') and c['a'] == dict(k='id', v=var):
            if c['op'] == '<' and start == dict(k='num', v='0'):
                hdr = [Label('repeat'), E(c['b'], LP), Label('times')]
            else:
                end = c['b'] if c['op'] == '<=' else dict(k='bin', op='-', a=c['b'], b=dict(k='num', v='1'))
                hdr = [Label('for'), var_pill(var), Label('from'), E(start, LP), Label('to'), E(end, LP)]
        else:
            hdr = [Label('for'), var_pill(var), Label('from'), E(start, LP), Label('while'), E(c, LP)]
        return [CBlock([(hdr, build_stmts(n['body']))], LP, com=com)]
    if k == 'forof':
        hdr = [Label('for element'), var_pill(n['var']), Label('of'), E(n['arr'], LP)]
        return [CBlock([(hdr, build_stmts(n['body']))], LP, com=com)]
    if k == 'return':
        return [Stmt([Label('return')] + ([E(n['val'], F)] if n['val'] else []), F, com)]
    if k in ('break', 'continue'): return [Stmt([Label(k)], LP, com)]
    if k == 'blockstmt': return build_stmts(n['body'])
    if k == 'empty': return []
    e = n['e']
    if e['k'] == 'call': return [call_block(e, CAT['other'], True, com)]
    if e['k'] == 'assign': return [assign_block(e, com)]
    if e['k'] == 'upd' and e['e']['k'] == 'id':
        return [Stmt([Label('change'), dropdown(e['e']['v'], V), Label('by'),
                      field('1' if e['op'] == '++' else '-1')], V, com)]
    return [Stmt([E(e, CAT['other'])], CAT['other'], com)]


def build_program(ast):
    FUNCS.update(n['name'] for n in ast if n['k'] == 'func')
    stacks, start = [], []
    for n in ast:
        hat = n['k'] == 'func' or (n['k'] == 'expr' and n['e']['k'] == 'call'
                                    and any(a['k'] == 'fn' for a in n['e']['args']))
        (stacks.extend(build_stmt(n)) if hat else start.append(n))
    if start:
        stacks.insert(0, CBlock([([Label('on start')], build_stmts(start))], CAT['basic'], hat=True))
    return stacks


# ---------------------------------------------------------------- page layout
def layout_stack(block, wrap):
    out, coms, lines = [], [], []
    block.render(0, 0, out, coms)
    cx, nexty, maxw = block.w + 30, 0, 0
    for bx, by, text in sorted(coms, key=lambda c: c[1]):
        rows = [r for t in text for r in (textwrap.wrap(t, wrap) or [''])]
        cw = max(tw(r, CFONT) for r in rows) + 16
        ch = len(rows) * (CFONT + 5) + 10
        cy = max(by, nexty)
        lines.append(f'<path d="M {bx:.1f},{by + 20:.1f} L {cx:.1f},{cy + min(20, ch / 2):.1f}" '
                     f'stroke="#B9A400" stroke-dasharray="3,3" fill="none"/>')
        out.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch}" rx="4" '
                   f'fill="#FEF49C" stroke="#D6C63A"/>')
        for i, r in enumerate(rows):
            Label(r, '#333', CFONT).svg(cx + 8, cy + 5 + i * (CFONT + 5), out)
        nexty, maxw = cy + ch + 8, max(maxw, cw)
    w = cx + maxw if coms else block.w
    return lines + out, w, max(block.h + 4, nexty)


def render(stacks, columns, wrap, margin=20, gap=40):
    laid = [layout_stack(b, wrap) for b in stacks]
    cols = [[0, 0, []] for _ in range(max(1, columns))]   # height, width, items
    for item in laid:
        col = min(cols, key=lambda c: c[0])
        col[2].append((col[0], item)); col[0] += item[2] + gap; col[1] = max(col[1], item[1])
    body, x = [], margin
    for h, w, items in cols:
        for y, (svg, _, _) in items:
            body.append(f'<g transform="translate({x:.1f},{y + margin:.1f})">' + ''.join(svg) + '</g>')
        x += w + gap
    W = x - gap + margin
    H = max(c[0] for c in cols) - gap + 2 * margin
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
            f'viewBox="0 0 {W:.0f} {H:.0f}">\n'
            f'<style>text{{font-family:"DejaVu Sans",Verdana,sans-serif}}</style>\n'
            f'<rect width="100%" height="100%" fill="#fff"/>\n' + '\n'.join(body) + '\n</svg>\n')


def main():
    ap = argparse.ArgumentParser(description='Draw a MakeCode micro:bit .ts program as MakeCode-style blocks (SVG).')
    ap.add_argument('source', help='MakeCode JavaScript/TypeScript file, e.g. egoshooter.ts')
    ap.add_argument('-o', '--output', help='SVG file to write (default: same name as source, .svg)')
    ap.add_argument('-c', '--columns', type=int, default=2, help='number of columns (default 2)')
    ap.add_argument('--wrap', type=int, default=45, help='wrap comment lines after N characters (default 45)')
    a = ap.parse_args()
    src = open(a.source, encoding='utf-8').read()
    try:
        ast = Parser(tokenize(src)).program()
    except SyntaxError as err:
        sys.exit(f'{a.source}: {err}')
    out = a.output or re.sub(r'\.\w+$', '', a.source) + '.svg'
    open(out, 'w', encoding='utf-8').write(render(build_program(ast), a.columns, a.wrap))
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
