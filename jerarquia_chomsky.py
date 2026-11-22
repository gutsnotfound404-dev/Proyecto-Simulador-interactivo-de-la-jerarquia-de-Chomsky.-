#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de la Jerarquía de Chomsky
====================================
Aplicación con interfaz gráfica (Tkinter, solo librería estándar) con un panel
principal y cuatro módulos interactivos:

  Nivel 3 · Lenguajes regulares            → Autómata Finito Determinista (AFD)
  Nivel 2 · Lenguajes libres de contexto   → Autómata de Pila (AP)
  Nivel 1 · Lenguajes sensibles al contexto→ Autómata Linealmente Acotado (LBA)
  Nivel 0 · Recursivamente enumerables     → Máquina de Turing (MT)

Ejecución:  python jerarquia_chomsky.py      (Python 3.8+)

Cada módulo precalcula o calcula paso a paso una secuencia de "instantáneas"
(snapshots) de la computación, lo que permite avanzar, retroceder, reproducir
automáticamente o ejecutar hasta el final.
"""
import math
import tkinter as tk
from tkinter import ttk, messagebox

# ───────────────────────────── Paleta y fuentes ──────────────────────────────
BG = "#f4f6fb"
CARD = "#ffffff"
LINE = "#44506b"
EDGE = "#5b6784"
EDGE_ACTIVE = "#e4572e"
ACTIVE = "#ffd166"      # celda / nodo activo
DONE = "#d4edda"        # símbolo ya consumido
DELIM = "#d9d9ee"       # delimitadores ⊢ ⊣
HEAD = "#c1121f"
MUTED = "#6b7490"
OK = "#1b8a3c"
BAD = "#c1121f"
INFO = "#1d4e89"
PUSH = "#8fe3a2"
POP = "#f4a6a6"

F_TXT = ("Helvetica", 10)
F_BOLD = ("Helvetica", 10, "bold")
F_SMALL = ("Helvetica", 8)
F_H1 = ("Helvetica", 16, "bold")
F_H2 = ("Helvetica", 11, "bold")
F_MONO = ("Courier", 12)
F_MONO_S = ("Courier", 10)
F_MONO_B = ("Courier", 15, "bold")


# ═════════════════════════════ Utilidades de dibujo ══════════════════════════
def draw_tape(cv, cells, head, rng=None, consumed=-1, head_text="",
              blank_char="", infinite=False):
    """Dibuja una cinta. `cells` es un dict índice→símbolo.

    rng      : (lo, hi) si la cinta es finita (solo se dibujan esas celdas);
               None si es extendible en ambos sentidos.
    consumed : celdas con 0 <= i < consumed se sombrean como ya leídas.
    """
    cv.delete("all")
    W = max(cv.winfo_width(), 300)
    cw = 40
    fit = max(5, (W - 60) // cw)
    if rng is not None:
        lo, hi = rng
        size = hi - lo + 1
        if size <= fit:
            first, count = lo, size
        else:
            first, count = min(max(head - fit // 2, lo), hi - fit + 1), fit
    else:
        count = fit if fit % 2 == 1 else fit - 1
        first = head - count // 2
    x0 = (W - count * cw) / 2
    top, bot = 26, 26 + cw - 4
    for k in range(count):
        i = first + k
        x = x0 + k * cw
        sym = cells.get(i, "")
        if i == head:
            fill = ACTIVE
        elif sym in ("⊢", "⊣"):
            fill = DELIM
        elif 0 <= i < consumed:
            fill = DONE
        else:
            fill = CARD
        cv.create_rectangle(x, top, x + cw, bot, fill=fill, outline=LINE, width=2)
        cv.create_text(x + cw / 2, (top + bot) / 2, text=sym or blank_char,
                       font=F_MONO_B, fill="#222" if sym else MUTED)
        cv.create_text(x + cw / 2, top - 9, text=str(i), font=F_SMALL, fill=MUTED)
        if i == head:
            cx = x + cw / 2
            cv.create_polygon(cx, bot + 4, cx - 8, bot + 18, cx + 8, bot + 18,
                              fill=HEAD, outline="")
            cv.create_text(cx, bot + 31, text=head_text, font=F_BOLD, fill=HEAD)
    if infinite:
        y = (top + bot) / 2
        cv.create_text(x0 - 18, y, text="⋯", font=F_MONO_B, fill=MUTED)
        cv.create_text(x0 + count * cw + 18, y, text="⋯", font=F_MONO_B, fill=MUTED)


def draw_graph(cv, states, edges, start, accepts, current=None, active=None):
    """Dibuja un diagrama de estados con los nodos en círculo.

    edges: dict (origen, destino) → texto de la etiqueta (puede tener '\\n').
    """
    cv.delete("all")
    W, H = max(cv.winfo_width(), 240), max(cv.winfo_height(), 220)
    cx, cy = W / 2, H / 2
    n = len(states)
    r = 22 if n <= 8 else 17
    if n == 1:
        pos = {states[0]: (cx, cy)}
    else:
        R = min(W * 0.34, H * 0.32)
        pos = {s: (cx + R * math.cos(math.pi + 2 * math.pi * k / n),
                   cy + R * math.sin(math.pi + 2 * math.pi * k / n))
               for k, s in enumerate(states)}

    def outward(p):
        ux, uy = p[0] - cx, p[1] - cy
        L = math.hypot(ux, uy)
        return (0.0, -1.0) if L < 1 else (ux / L, uy / L)

    def on_circle(p, t):
        d = math.hypot(t[0] - p[0], t[1] - p[1]) or 1
        return p[0] + (t[0] - p[0]) / d * r, p[1] + (t[1] - p[1]) / d * r

    for (a, b), label in edges.items():
        col = EDGE_ACTIVE if active == (a, b) else EDGE
        w = 3 if active == (a, b) else 1.5
        ax, ay = pos[a]
        bx, by = pos[b]
        lines = label.count("\n") + 1
        if a == b:
            ux, uy = outward(pos[a])
            lr = 13
            lcx, lcy = ax + ux * (r + lr - 4), ay + uy * (r + lr - 4)
            ang = math.degrees(math.atan2(-(ay - lcy), ax - lcx))
            cv.create_arc(lcx - lr, lcy - lr, lcx + lr, lcy + lr, start=ang + 35,
                          extent=290, style="arc", outline=col, width=w)
            th = math.radians(ang - 35)             # punta de flecha al final del arco
            ex_, ey_ = lcx + lr * math.cos(th), lcy - lr * math.sin(th)
            tx, ty = -math.sin(th), -math.cos(th)   # tangente (sentido antihorario)
            pxx, pyy = -ty, tx
            cv.create_polygon(ex_ + tx * 6, ey_ + ty * 6,
                              ex_ - tx * 3 + pxx * 4, ey_ - ty * 3 + pyy * 4,
                              ex_ - tx * 3 - pxx * 4, ey_ - ty * 3 - pyy * 4,
                              fill=col, outline=col)
            d = r + 2 * lr + 6 + (lines - 1) * 6
            cv.create_text(ax + ux * d, ay + uy * d, text=label, font=F_SMALL,
                           fill=col, justify="center")
        else:
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy) or 1
            nx, ny = dy / L, -dx / L
            off = 36 if (b, a) in edges else 0
            mx, my = (ax + bx) / 2 + nx * off, (ay + by) / 2 + ny * off
            sx, sy = on_circle(pos[a], (mx, my))
            ex, ey = on_circle(pos[b], (mx, my))
            if off:
                cv.create_line(sx, sy, mx, my, ex, ey, smooth=True, arrow="last",
                               fill=col, width=w)
                px, py = (sx + 2 * mx + ex) / 4, (sy + 2 * my + ey) / 4
            else:
                cv.create_line(sx, sy, ex, ey, arrow="last", fill=col, width=w)
                px, py = (sx + ex) / 2, (sy + ey) / 2
            cv.create_text(px + nx * (12 + 4 * (lines - 1)),
                           py + ny * (12 + 4 * (lines - 1)), text=label,
                           font=F_SMALL, fill=col, justify="center")

    for s in states:                                   # nodos
        x, y = pos[s]
        cv.create_oval(x - r, y - r, x + r, y + r, width=2, outline=LINE,
                       fill=ACTIVE if s == current else CARD)
        if s in accepts:
            cv.create_oval(x - r + 5, y - r + 5, x + r - 5, y + r - 5, width=2,
                           outline=LINE)
        cv.create_text(x, y, text=s, font=F_BOLD)

    sx_, sy_ = pos[start]                              # flecha de inicio
    ux, uy = outward(pos[start]) if n > 1 else (-1.0, 0.0)
    a0 = math.atan2(uy, ux) - math.radians(50)
    dx, dy = math.cos(a0), math.sin(a0)
    cv.create_line(sx_ + dx * (r + 32), sy_ + dy * (r + 32), sx_ + dx * r,
                   sy_ + dy * r, arrow="last", width=2, fill=LINE)
    cv.create_text(sx_ + dx * (r + 42), sy_ + dy * (r + 42), text="inicio",
                   font=F_SMALL, fill=MUTED)


def draw_stack(cv, stack, flash=None, popped=None):
    """Dibuja la pila (el fondo es stack[0], el tope es stack[-1])."""
    cv.delete("all")
    W, H = max(cv.winfo_width(), 200), max(cv.winfo_height(), 200)
    cv.create_text(W / 2, 14, text="PILA (LIFO)", font=F_BOLD)
    bw = 100
    x = (W - bw) / 2 + 20
    base = H - 18
    n = len(stack)
    bh = max(16, min(36, (H - 90) / max(n + 1, 1)))
    cv.create_line(x - 12, base, x + bw + 12, base, width=5, fill=LINE)
    for i, sym in enumerate(stack):
        y1, y0 = base - i * bh, base - (i + 1) * bh
        top = i == n - 1
        fill = CARD
        if top:
            fill = {"push": PUSH}.get(flash, ACTIVE)
        cv.create_rectangle(x, y0, x + bw, y1, fill=fill, outline=LINE, width=2)
        cv.create_text(x + bw / 2, (y0 + y1) / 2, text="Z₀" if sym == "Z" else sym,
                       font=F_MONO_B)
        if top:
            cv.create_text(x - 8, (y0 + y1) / 2, text="tope ▶", anchor="e",
                           font=F_BOLD, fill=HEAD)
    if popped and flash == "pop":
        y1, y0 = base - n * bh, base - (n + 1) * bh
        cv.create_rectangle(x, y0, x + bw, y1, fill=POP, outline=BAD, dash=(4, 3), width=2)
        cv.create_text(x + bw / 2, (y0 + y1) / 2, text="Z₀" if popped == "Z" else popped,
                       font=F_MONO_B, fill=BAD)
        cv.create_text(x + bw + 8, (y0 + y1) / 2, text="pop", anchor="w",
                       font=F_BOLD, fill=BAD)
    if not stack:
        cv.create_text(W / 2, base - 20, text="(pila vacía)", fill=MUTED, font=F_TXT)


# ═══════════════════════════ Clase base de los módulos ═══════════════════════
class SimBase(ttk.Frame):
    """Marco común: controles (Cargar / Atrás / Paso / Reproducir / Ejecutar),
    estado, bitácora y navegación sobre una lista de instantáneas `snaps`.

    Cada instantánea es un dict con al menos: 'msg' (texto de la bitácora) y
    'final' (None mientras corre, True si acepta, False si rechaza).
    """
    title = ""
    blurb = ""
    default_word = ""
    max_steps = 5000

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.snaps, self.pos = [], 0
        self.job = None
        self.flash_on = False

        head = ttk.Frame(self)
        head.pack(fill="x", padx=12, pady=(10, 2))
        ttk.Button(head, text="← Menú principal", command=app.show_menu).pack(side="left")
        ttk.Label(head, text=self.title, font=F_H1).pack(side="left", padx=14)
        ttk.Label(self, text=self.blurb, foreground=MUTED, wraplength=1150,
                  justify="left").pack(fill="x", padx=14)

        self.opts = ttk.LabelFrame(self, text=" Configuración ")
        self.opts.pack(fill="x", padx=12, pady=6)
        self.build_options(self.opts)

        ctl = ttk.Frame(self)
        ctl.pack(fill="x", padx=12, pady=2)
        ttk.Label(ctl, text="Cadena de entrada:").pack(side="left")
        self.word = tk.StringVar(value=self.default_word)
        ent = ttk.Entry(ctl, textvariable=self.word, width=26, font=F_MONO)
        ent.pack(side="left", padx=6)
        ent.bind("<Return>", lambda e: self.load())
        ttk.Button(ctl, text="Cargar", command=self.load).pack(side="left")
        ttk.Separator(ctl, orient="vertical").pack(side="left", fill="y", padx=8)
        for text, cmd in (("⏮ Reiniciar", self.restart), ("◀ Atrás", self.back),
                          ("Paso ▶", self.step)):
            ttk.Button(ctl, text=text, command=cmd).pack(side="left", padx=2)
        self.play = ttk.Button(ctl, text="▶ Reproducir", command=self.toggle_play)
        self.play.pack(side="left", padx=2)
        ttk.Button(ctl, text="⏭ Ejecutar todo", command=self.run_all).pack(side="left", padx=2)
        ttk.Label(ctl, text="  lento").pack(side="left")
        self.speed = tk.IntVar(value=1000)
        ttk.Scale(ctl, from_=100, to=1600, variable=self.speed, length=110).pack(side="left")
        ttk.Label(ctl, text="rápido").pack(side="left")

        exrow = ttk.Frame(self)
        exrow.pack(fill="x", padx=12, pady=(4, 0))
        ttk.Label(exrow, text="Ejemplos de prueba:").pack(side="left")
        self.ex_cb = ttk.Combobox(exrow, state="readonly", width=46)
        self.ex_cb.pack(side="left", padx=6)
        self.ex_cb.bind("<<ComboboxSelected>>", self.on_example)
        ttk.Label(exrow, text="(elija uno para cargarlo y ejecútelo con Paso / Reproducir)",
                  foreground=MUTED).pack(side="left")
        self.ex_items = []

        self.status = ttk.Label(self, text="", font=F_H2)
        self.status.pack(fill="x", padx=14, pady=(6, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=12, pady=6)
        self.left = ttk.Frame(body)
        self.left.pack(side="left", fill="both", expand=True)
        self.right = ttk.Frame(body, width=340)
        self.right.pack(side="right", fill="y", padx=(10, 0))
        self.right.pack_propagate(False)
        self.build_left(self.left)
        self.build_right_extra(self.right)
        ttk.Label(self.right, text="Bitácora de la computación", font=F_H2).pack(anchor="w")
        box = ttk.Frame(self.right)
        box.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(box)
        sb.pack(side="right", fill="y")
        self.log = tk.Listbox(box, font=F_MONO_S, activestyle="none", bg=CARD,
                              yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.config(command=self.log.yview)
        self.post_init()

    # ---- ganchos para las subclases ----
    def build_options(self, parent): pass
    def build_left(self, parent): pass
    def build_right_extra(self, parent): pass
    def post_init(self): self.load()
    def make_snaps(self, word): raise NotImplementedError
    def advance(self): return False          # genera la siguiente instantánea
    def render(self, snap): pass

    # ---- ejemplos de prueba ----
    def set_examples(self, items):
        """items: lista de (cadena, etiqueta). La etiqueta indica el resultado esperado."""
        self.ex_items = list(items)
        self.ex_cb.config(values=[f"{w or 'ε':<14} {lab}" for w, lab in self.ex_items])
        self.ex_cb.set("")

    def on_example(self, _e=None):
        i = self.ex_cb.current()
        if i >= 0:
            self.word.set(self.ex_items[i][0] or "ε")
            self.load()

    # ---- control de la simulación ----
    def load(self):
        self.stop_play()
        w = self.word.get().replace(" ", "")
        if w == "ε":
            w = ""
        self.snaps = self.make_snaps(w)
        self.pos = 0
        self.refresh()

    def restart(self):
        self.stop_play()
        self.pos = 0
        self.refresh()

    def back(self):
        self.stop_play()
        if self.pos > 0:
            self.pos -= 1
            self.refresh()

    def step(self):
        self.stop_play()
        self.forward(flash=True)

    def forward(self, flash=False):
        if self.snaps[self.pos].get("final") is not None:
            return False
        if self.pos + 1 >= len(self.snaps) and not self.advance():
            return False
        self.pos += 1
        self.refresh(flash)
        return True

    def run_all(self):
        self.stop_play()
        while self.snaps[self.pos].get("final") is None:
            if self.pos + 1 >= len(self.snaps) and not self.advance():
                break
            self.pos += 1
        self.refresh()

    def toggle_play(self):
        if self.job:
            self.stop_play()
            return
        if self.snaps[self.pos].get("final") is not None:
            self.pos = 0
            self.refresh()
        self.play.config(text="⏸ Pausar")
        self._tick()

    def _tick(self):
        if not self.forward(flash=True):
            self.stop_play()
            return
        self.job = self.after(max(80, 1700 - int(self.speed.get())), self._tick)

    def stop_play(self):
        if self.job:
            self.after_cancel(self.job)
            self.job = None
        self.play.config(text="▶ Reproducir")

    def refresh(self, flash=False):
        if not self.snaps:
            return
        s = self.snaps[self.pos]
        self.flash_on = flash
        self.render(s)
        self.log.delete(0, "end")
        for i in range(self.pos + 1):
            self.log.insert("end", f"{i:>3}. {self.snaps[i]['msg']}")
        self.log.see("end")
        fin = s.get("final")
        if fin is None:
            self.status.config(text=f"Paso {self.pos}: en ejecución…", foreground=INFO)
        elif fin:
            self.status.config(text="✔ CADENA ACEPTADA  " + s.get("result", ""), foreground=OK)
        else:
            self.status.config(text="✘ CADENA RECHAZADA", foreground=BAD)
        if flash:
            self.after(450, self._unflash)

    def _unflash(self):
        if self.flash_on and self.snaps:
            self.flash_on = False
            self.render(self.snaps[self.pos])

    def redraw(self, _event=None):
        if self.snaps:
            self.render(self.snaps[self.pos])


# ═════════════════════════════ NIVEL 3 · AFD ═════════════════════════════════
LANGS_DFA = [
    "Número par de 0s (binario)",
    "Termina en «ab»  (Σ = {a,b})",
    "Binarios divisibles por k   [parámetro: k]",
    "Contiene la subcadena P   [parámetros: P y alfabeto]",
]


def build_dfa(kind, param, alpha):
    """Devuelve un dict con la definición del AFD o lanza ValueError."""
    if kind == 0:
        sigma = ["0", "1"]
        states = ["q0", "q1"]
        delta = {("q0", "0"): "q1", ("q0", "1"): "q0",
                 ("q1", "0"): "q0", ("q1", "1"): "q1"}
        acc, desc = {"q0"}, "L = { w ∈ {0,1}* : #₀(w) es par }"
    elif kind == 1:
        sigma = ["a", "b"]
        states = ["q0", "q1", "q2"]
        delta = {("q0", "a"): "q1", ("q0", "b"): "q0",
                 ("q1", "a"): "q1", ("q1", "b"): "q2",
                 ("q2", "a"): "q1", ("q2", "b"): "q0"}
        acc, desc = {"q2"}, "L = { w ∈ {a,b}* : w termina en ab }"
    elif kind == 2:
        try:
            k = int(param)
        except ValueError:
            raise ValueError("El parámetro k debe ser un entero.")
        if not 2 <= k <= 10:
            raise ValueError("Use un k entre 2 y 10.")
        sigma = ["0", "1"]
        states = [f"q{r}" for r in range(k)]
        delta = {(f"q{r}", d): f"q{(2 * r + int(d)) % k}" for r in range(k) for d in sigma}
        acc, desc = {"q0"}, f"L = {{ w ∈ {{0,1}}* : w, leída en binario, es divisible por {k} }}"
    else:
        p = param.strip()
        if not p or len(p) > 9:
            raise ValueError("P debe tener entre 1 y 9 símbolos.")
        sigma = sorted(set(alpha.replace(" ", "")) | set(p))
        m = len(p)
        states = [f"q{i}" for i in range(m + 1)]
        d = {}
        for c in sigma:
            d[(0, c)] = 0
        d[(0, p[0])] = 1
        x = 0
        for j in range(1, m + 1):                 # construcción tipo KMP
            for c in sigma:
                d[(j, c)] = d[(x, c)]
            if j < m:
                d[(j, p[j])] = j + 1
                x = d[(x, p[j])]
        for c in sigma:
            d[(m, c)] = m                         # estado final absorbente
        delta = {(f"q{i}", c): f"q{t}" for (i, c), t in d.items()}
        acc = {f"q{m}"}
        desc = f"L = {{ w ∈ {{{','.join(sigma)}}}* : w contiene la subcadena «{p}» }}"
    edges = {}
    for (q, c), t in delta.items():
        edges.setdefault((q, t), []).append(c)
    edges = {k: ",".join(v) for k, v in edges.items()}
    return dict(states=states, sigma=sigma, delta=delta, start="q0", accepts=acc,
                edges=edges, desc=desc)


def dfa_examples(d, must=()):
    """Genera cadenas de prueba (aceptadas y rechazadas) recorriendo cadenas cortas de Σ*."""
    import itertools
    cand = itertools.islice(itertools.chain.from_iterable(
        itertools.product(d["sigma"], repeat=n) for n in range(8)), 4000)
    acc, rej = list(must), []
    for t in cand:
        w, q = "".join(t), d["start"]
        for c in w:
            q = d["delta"][(q, c)]
        (acc if q in d["accepts"] else rej).append(w)

    def spread(lst, k):
        lst = list(dict.fromkeys(lst))
        return lst if len(lst) <= k else [lst[i * (len(lst) - 1) // (k - 1)] for i in range(k)]
    return [(w, "✔ acepta") for w in spread(acc, 4)] + [(w, "✘ rechaza") for w in spread(rej, 4)]


class DFAFrame(SimBase):
    title = "Nivel 3 · Lenguajes regulares — Autómata Finito Determinista"
    blurb = ("M = (Q, Σ, δ, q₀, F). No tiene memoria auxiliar: solo conoce su estado actual. "
             "Lea la cadena símbolo a símbolo y observe cómo cambia el estado activo (amarillo). "
             "Los estados con doble círculo son finales.")
    default_word = "1001"

    def build_options(self, p):
        self.lang = tk.StringVar(value=LANGS_DFA[0])
        self.param = tk.StringVar(value="3")
        self.alpha = tk.StringVar(value="ab")
        ttk.Label(p, text="Lenguaje:").grid(row=0, column=0, padx=6, pady=4, sticky="e")
        cb = ttk.Combobox(p, textvariable=self.lang, values=LANGS_DFA, state="readonly", width=48)
        cb.grid(row=0, column=1, padx=4)
        cb.bind("<<ComboboxSelected>>", self.on_lang)
        ttk.Label(p, text="Parámetro (k / P):").grid(row=0, column=2, padx=(14, 4))
        self.e_param = ttk.Entry(p, textvariable=self.param, width=10)
        self.e_param.grid(row=0, column=3)
        ttk.Label(p, text="Alfabeto:").grid(row=0, column=4, padx=(14, 4))
        self.e_alpha = ttk.Entry(p, textvariable=self.alpha, width=8)
        self.e_alpha.grid(row=0, column=5)
        ttk.Button(p, text="Construir autómata", command=self.rebuild).grid(row=0, column=6, padx=12)
        self.info = ttk.Label(p, text="", foreground=INFO, font=F_BOLD)
        self.info.grid(row=1, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 4))

    def build_left(self, parent):
        self.cv = tk.Canvas(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.cv.pack(fill="both", expand=True)
        self.tape = tk.Canvas(parent, bg=BG, height=110, highlightthickness=0)
        self.tape.pack(fill="x", pady=(6, 0))
        self.cv.bind("<Configure>", self.redraw)
        self.tape.bind("<Configure>", self.redraw)

    def post_init(self):
        self.on_lang()

    def on_lang(self, _e=None):
        k = LANGS_DFA.index(self.lang.get())
        self.e_param.config(state="normal" if k >= 2 else "disabled")
        self.e_alpha.config(state="normal" if k == 3 else "disabled")
        if k == 2 and not self.param.get().isdigit():
            self.param.set("3")
        if k == 3 and self.param.get().isdigit():
            self.param.set("aba")
        self.rebuild()

    def rebuild(self):
        try:
            self.dfa = build_dfa(LANGS_DFA.index(self.lang.get()), self.param.get(), self.alpha.get())
        except ValueError as ex:
            messagebox.showwarning("Parámetro no válido", str(ex))
            return
        d = self.dfa
        self.info.config(text=f"{d['desc']}     |     Σ = {{{','.join(d['sigma'])}}}   "
                              f"|   |Q| = {len(d['states'])}")
        kind = LANGS_DFA.index(self.lang.get())
        self.set_examples(dfa_examples(d, [self.param.get().strip()] if kind == 3 else []))
        self.load()

    def make_snaps(self, word):
        d = self.dfa
        q = d["start"]
        snaps = [dict(state=q, idx=0, last=None, word=word, final=None,
                      msg=f"Inicio: estado {q}, cabezal en la posición 0")]
        for i, ch in enumerate(word):
            nq = d["delta"].get((q, ch))
            if nq is None:
                snaps.append(dict(state=q, idx=i, last=None, word=word, final=False,
                                  msg=f"'{ch}' no pertenece a Σ → no hay transición"))
                return snaps
            snaps.append(dict(state=nq, idx=i + 1, last=(q, nq), word=word, final=None,
                              msg=f"δ({q}, {ch}) = {nq}"))
            q = nq
        ok = q in d["accepts"]
        snaps[-1]["final"] = ok
        snaps[-1]["msg"] += ("  | fin de cadena: estado FINAL" if ok
                             else "  | fin de cadena: estado NO final")
        return snaps

    def render(self, s):
        d = self.dfa
        draw_graph(self.cv, d["states"], d["edges"], d["start"], d["accepts"],
                   s["state"], s["last"])
        w = s["word"]
        draw_tape(self.tape, dict(enumerate(w)), s["idx"], rng=(0, len(w)),
                  consumed=s["idx"], head_text=f"estado: {s['state']}")


# ═════════════════════════════ NIVEL 2 · AP ══════════════════════════════════
def pda_delta(rules):
    return {(q, a, x): (p, push) for q, a, x, p, push in rules}


PDAS = {
    "aⁿbⁿ   (n ≥ 0)": dict(
        desc="L = { aⁿbⁿ : n ≥ 0 }   — apila una A por cada a y desapila una por cada b",
        sigma="ab", states=["q0", "q1", "q2"], accepts={"q2"}, word="aaabbb",
        examples=[("", "✔ acepta"), ("ab", "✔ acepta"), ("aabb", "✔ acepta"), ("aaabbb", "✔ acepta"),
                  ("aab", "✘ rechaza"), ("abb", "✘ rechaza"), ("ba", "✘ rechaza"), ("abab", "✘ rechaza")],
        delta=pda_delta([
            ("q0", "a", "Z", "q0", "AZ"), ("q0", "a", "A", "q0", "AA"),
            ("q0", "b", "A", "q1", ""), ("q1", "b", "A", "q1", ""),
            ("q0", "", "Z", "q2", "Z"), ("q1", "", "Z", "q2", "Z")])),
    "Paréntesis balanceados": dict(
        desc="L = { cadenas de ( ) correctamente balanceadas }   — apila en '(' y desapila en ')'",
        sigma="()", states=["q0", "q1"], accepts={"q1"}, word="(()())",
        examples=[("", "✔ acepta"), ("()", "✔ acepta"), ("(()())", "✔ acepta"), ("((()))()", "✔ acepta"),
                  ("(()", "✘ rechaza"), ("())(", "✘ rechaza"), (")(", "✘ rechaza"), ("(()))", "✘ rechaza")],
        delta=pda_delta([
            ("q0", "(", "Z", "q0", "AZ"), ("q0", "(", "A", "q0", "AA"),
            ("q0", ")", "A", "q0", ""), ("q0", "", "Z", "q1", "Z")])),
    "w c wᴿ   (palíndromos con centro)": dict(
        desc="L = { w c wᴿ : w ∈ {a,b}* }   — apila w, cambia de estado al ver c y compara en orden inverso",
        sigma="abc", states=["q0", "q1", "q2"], accepts={"q2"}, word="abcba",
        examples=[("c", "✔ acepta"), ("aca", "✔ acepta"), ("abcba", "✔ acepta"), ("abbcbba", "✔ acepta"),
                  ("abcab", "✘ rechaza"), ("abc", "✘ rechaza"), ("ab", "✘ rechaza"), ("acb", "✘ rechaza")],
        delta=pda_delta(
            [("q0", s, x, "q0", s.upper() + x) for s in "ab" for x in "ZAB"]
            + [("q0", "c", x, "q1", x) for x in "ZAB"]
            + [("q1", "a", "A", "q1", ""), ("q1", "b", "B", "q1", ""),
               ("q1", "", "Z", "q2", "Z")])),
}


def run_pda(pda, word):
    delta, acc = pda["delta"], pda["accepts"]
    q, stack, i = "q0", ["Z"], 0
    snaps = [dict(state=q, idx=0, stack=list(stack), last=None, op=None, popped=None,
                  word=word, final=None, msg="Inicio: q0, pila = [Z₀]")]
    for _ in range(10000):
        top = stack[-1] if stack else None
        key = None
        if top is not None and i < len(word) and (q, word[i], top) in delta:
            key = (q, word[i], top)
        elif top is not None and (q, "", top) in delta:
            key = (q, "", top)
        if key is None:
            break
        p, push = delta[key]
        a = key[1]
        stack.pop()
        for ch in reversed(push):
            stack.append(ch)
        if a:
            i += 1
        if push == "":
            op, desc = "pop", f"desapila {top}"
        elif len(push) == 1 and push == top:
            op, desc = None, "la pila no cambia"
        elif push.endswith(top):
            op, desc = "push", f"apila {push[:-1]}"
        else:
            op, desc = "push", f"reemplaza {top} por {push}"
        snaps.append(dict(state=p, idx=i, stack=list(stack), last=(q, p), op=op,
                          popped=top if op == "pop" else None, word=word, final=None,
                          msg=f"δ({q}, {a or 'ε'}, {top}) = ({p}, {push or 'ε'}) · {desc}"))
        q = p
    ok = (i == len(word)) and q in acc
    last = snaps[-1]
    last["final"] = ok
    if ok:
        last["msg"] += "  | cadena consumida y estado FINAL"
    elif i < len(word):
        last["msg"] += f"  | sin transición para '{word[i]}' con tope {stack[-1] if stack else '∅'}"
    else:
        last["msg"] += f"  | cadena consumida pero {q} no es final"
    return snaps


class PDAFrame(SimBase):
    title = "Nivel 2 · Lenguajes libres de contexto — Autómata de Pila"
    blurb = ("M = (Q, Σ, Γ, δ, q₀, Z₀, F). Memoria LIFO: solo se lee y modifica el tope de la pila. "
             "Etiqueta de transición  a,X/γ  = «leyendo a con tope X, reemplaza X por γ» "
             "(γ = ε desapila). Verde = apilado, rojo = desapilado.")
    default_word = "aaabbb"

    def build_options(self, p):
        self.lang = tk.StringVar(value=list(PDAS)[0])
        ttk.Label(p, text="Lenguaje:").grid(row=0, column=0, padx=6, pady=4)
        cb = ttk.Combobox(p, textvariable=self.lang, values=list(PDAS), state="readonly", width=36)
        cb.grid(row=0, column=1)
        cb.bind("<<ComboboxSelected>>", self.on_lang)
        self.info = ttk.Label(p, text="", foreground=INFO, font=F_BOLD)
        self.info.grid(row=0, column=2, padx=14, sticky="w")

    def build_left(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="both", expand=True)
        self.cv = tk.Canvas(top, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.cv.pack(side="left", fill="both", expand=True)
        self.stack_cv = tk.Canvas(top, bg=CARD, width=230, highlightthickness=1,
                                  highlightbackground=LINE)
        self.stack_cv.pack(side="right", fill="y", padx=(8, 0))
        self.tape = tk.Canvas(parent, bg=BG, height=110, highlightthickness=0)
        self.tape.pack(fill="x", pady=(6, 0))
        for c in (self.cv, self.stack_cv, self.tape):
            c.bind("<Configure>", self.redraw)

    def post_init(self):
        self.on_lang()

    def on_lang(self, _e=None):
        self.pda = PDAS[self.lang.get()]
        edges = {}
        for (q, a, x), (p, push) in self.pda["delta"].items():
            edges.setdefault((q, p), []).append(f"{a or 'ε'},{x}/{push or 'ε'}")
        self.edges = {k: "\n".join(v) for k, v in edges.items()}
        self.info.config(text=self.pda["desc"])
        self.word.set(self.pda["word"])
        self.set_examples(self.pda["examples"])
        self.load()

    def make_snaps(self, word):
        return run_pda(self.pda, word)

    def render(self, s):
        draw_graph(self.cv, self.pda["states"], self.edges, "q0", self.pda["accepts"],
                   s["state"], s["last"])
        flash = s["op"] if self.flash_on else None
        draw_stack(self.stack_cv, s["stack"], flash, s["popped"])
        w = s["word"]
        draw_tape(self.tape, dict(enumerate(w)), s["idx"], rng=(0, len(w)),
                  consumed=s["idx"], head_text=f"estado: {s['state']}")


# ═════════════════ NIVELES 1 y 0 · LBA y Máquina de Turing ═══════════════════
BLANK = "_"


def tm_rules(rules):
    """rules: (estado, símbolos, nuevo_estado, escribe, mov). '=' → reescribe el mismo símbolo."""
    d = {}
    for q, syms, q2, w, mv in rules:
        for s in syms:
            d[(q, s)] = (q2, s if w == "=" else w, mv)
    return d


def show(sym):
    return "□" if sym == BLANK else sym


LBAS = {
    "aⁿbⁿcⁿ   (n ≥ 0)": dict(
        desc="L = { aⁿbⁿcⁿ : n ≥ 0 }  (no libre de contexto). Marca una a (X), una b (Y) y una c (Z) por ronda.",
        sigma="abc", start="q0", accepts={"qa"}, word="aabbcc", kind="accept",
        examples=[("", "✔ acepta"), ("abc", "✔ acepta"), ("aabbcc", "✔ acepta"), ("aaabbbccc", "✔ acepta"),
                  ("aabbc", "✘ rechaza"), ("abcabc", "✘ rechaza"), ("aabcc", "✘ rechaza"), ("cba", "✘ rechaza")],
        delta=tm_rules([
            ("q0", "⊢", "q1", "=", "R"),
            ("q1", "a", "q2", "X", "R"), ("q1", "Y", "q5", "=", "R"), ("q1", "⊣", "qa", "=", "S"),
            ("q2", "aY", "q2", "=", "R"), ("q2", "b", "q3", "Y", "R"),
            ("q3", "bZ", "q3", "=", "R"), ("q3", "c", "q4", "Z", "L"),
            ("q4", "abYZ", "q4", "=", "L"), ("q4", "X", "q1", "=", "R"),
            ("q5", "Y", "q5", "=", "R"), ("q5", "Z", "q6", "=", "R"),
            ("q6", "Z", "q6", "=", "R"), ("q6", "⊣", "qa", "=", "S")])),
    "#a = #b = #c   (en cualquier orden)": dict(
        desc="L = { w ∈ {a,b,c}* : #a = #b = #c }. Marca una a, una b y una c por ronda y verifica que no sobre nada.",
        sigma="abc", start="q0", accepts={"qa"}, word="bcaacb", kind="accept",
        examples=[("", "✔ acepta"), ("cba", "✔ acepta"), ("bcaacb", "✔ acepta"), ("aabbcc", "✔ acepta"),
                  ("ab", "✘ rechaza"), ("abca", "✘ rechaza"), ("aabbc", "✘ rechaza"), ("ccab", "✘ rechaza")],
        delta=tm_rules([
            ("q0", "⊢", "q1", "=", "R"),
            ("q1", "XYZbc", "q1", "=", "R"), ("q1", "a", "q2", "X", "L"), ("q1", "⊣", "q7", "=", "L"),
            ("q2", "abcXYZ", "q2", "=", "L"), ("q2", "⊢", "q3", "=", "R"),
            ("q3", "aXYZc", "q3", "=", "R"), ("q3", "b", "q4", "Y", "L"),
            ("q4", "abcXYZ", "q4", "=", "L"), ("q4", "⊢", "q5", "=", "R"),
            ("q5", "abXYZ", "q5", "=", "R"), ("q5", "c", "q6", "Z", "L"),
            ("q6", "abcXYZ", "q6", "=", "L"), ("q6", "⊢", "q1", "=", "R"),
            ("q7", "XYZ", "q7", "=", "L"), ("q7", "⊢", "qa", "=", "S")])),
}

TMS = {
    "Suma unaria  1ᵐ+1ⁿ → 1ᵐ⁺ⁿ": dict(
        desc="Función f(m,n) = m+n en unario. Convierte '+' en 1 y borra el último 1.",
        sigma="1+", start="q0", accepts={"qa"}, word="111+11", kind="function",
        examples=[("111+11", "→ 11111  (3+2=5)"), ("1+1", "→ 11  (1+1=2)"), ("1111+", "→ 1111  (4+0=4)"),
                  ("+111", "→ 111  (0+3=3)"), ("+", "→ ε  (0+0=0)"), ("1+1+1", "✘ rechaza (dos signos +)")],
        fmt=lambda t: f"Resultado: {t or 'ε'}  (= {len(t)})",
        delta=tm_rules([
            ("q0", "1", "q0", "=", "R"), ("q0", "+", "q1", "1", "R"),
            ("q1", "1", "q1", "=", "R"), ("q1", BLANK, "q2", BLANK, "L"),
            ("q2", "1", "qa", BLANK, "S")])),
    "Incremento binario  n → n+1": dict(
        desc="Función f(n) = n+1 en binario. Va al extremo derecho y propaga el acarreo hacia la izquierda.",
        sigma="01", start="q0", accepts={"qa"}, word="10111", kind="function",
        examples=[("0", "→ 1"), ("1", "→ 10"), ("1011", "→ 1100  (11+1=12)"), ("111", "→ 1000  (7+1=8)"),
                  ("10111", "→ 11000  (23+1=24)"), ("ε", "→ 1  (cinta vacía)")],
        fmt=lambda t: f"Resultado: {t}" + (f"  (decimal {int(t, 2)})" if t else ""),
        delta=tm_rules([
            ("q0", "01", "q0", "=", "R"), ("q0", BLANK, "q1", BLANK, "L"),
            ("q1", "1", "q1", "0", "L"), ("q1", "0", "qa", "1", "S"),
            ("q1", BLANK, "qa", "1", "S")])),
    "Palíndromos sobre {a,b}": dict(
        desc="Acepta w = wᴿ. Borra el primer símbolo, viaja al final y exige que el último coincida; repite.",
        sigma="ab", start="q0", accepts={"qa"}, word="abbaabba", kind="accept",
        examples=[("", "✔ acepta"), ("a", "✔ acepta"), ("aba", "✔ acepta"), ("abbaabba", "✔ acepta"),
                  ("ab", "✘ rechaza"), ("abb", "✘ rechaza"), ("aabb", "✘ rechaza"), ("abaab", "✘ rechaza")],
        delta=tm_rules([
            ("q0", "a", "q1", BLANK, "R"), ("q0", "b", "q3", BLANK, "R"), ("q0", BLANK, "qa", BLANK, "S"),
            ("q1", "ab", "q1", "=", "R"), ("q1", BLANK, "q2", BLANK, "L"),
            ("q2", "a", "q4", BLANK, "L"), ("q2", BLANK, "qa", BLANK, "S"),
            ("q3", "ab", "q3", "=", "R"), ("q3", BLANK, "q5", BLANK, "L"),
            ("q5", "b", "q4", BLANK, "L"), ("q5", BLANK, "qa", BLANK, "S"),
            ("q4", "ab", "q4", "=", "L"), ("q4", BLANK, "q0", BLANK, "R")])),
}


def tm_initial(m, word, bounded):
    if bounded:
        tape = {0: "⊢", len(word) + 1: "⊣"}
        tape.update({i + 1: c for i, c in enumerate(word)})
        msg = "Inicio: q0, cabezal sobre ⊢ (cinta acotada por ⊢ y ⊣)"
    else:
        tape = dict(enumerate(word))
        msg = "Inicio: q0, cabezal sobre la celda 0"
    return dict(state=m["start"], head=0, tape=tape, n=len(word), steps=0, last=None,
                final=None, msg=msg)


def tm_step(m, s, bounded):
    """Aplica una transición. Devuelve la nueva instantánea o None si ya terminó."""
    q = s["state"]
    if q in m["accepts"] or s.get("final") is not None:
        return None
    sym = s["tape"].get(s["head"], BLANK)
    rule = m["delta"].get((q, sym))
    if rule is None:
        return dict(s, final=False, last=None,
                    msg=f"Sin transición para ({q}, {show(sym)}) → la máquina se detiene y RECHAZA")
    q2, w, mv = rule
    tape = dict(s["tape"])
    if w == BLANK and not bounded:
        tape.pop(s["head"], None)
    else:
        tape[s["head"]] = w
    head = s["head"] + {"R": 1, "L": -1, "S": 0}[mv]
    new = dict(s, state=q2, head=head, tape=tape, steps=s["steps"] + 1, last=(q, sym), final=None,
               msg=f"δ({q}, {show(sym)}) = ({q2}, {show(w)}, {mv})")
    if bounded and not 0 <= head <= s["n"] + 1:
        new["final"] = False
        new["msg"] += "  | el cabezal intentó salir de los delimitadores → RECHAZA"
    elif q2 in m["accepts"]:
        new["final"] = True
        new["msg"] += "  | estado de aceptación"
        if m.get("kind") == "function":
            text = "".join(tape[i] for i in sorted(tape) if tape[i] != BLANK)
            new["result"] = m["fmt"](text)
            new["msg"] += f"  | {new['result']}"
    return new


class TMFrame(SimBase):
    """Módulo genérico de cinta: Nivel 0 (cinta infinita) y Nivel 1 (acotada)."""
    bounded = False
    presets = TMS

    def build_options(self, p):
        self.lang = tk.StringVar(value=list(self.presets)[0])
        ttk.Label(p, text="Máquina:").grid(row=0, column=0, padx=6, pady=4)
        cb = ttk.Combobox(p, textvariable=self.lang, values=list(self.presets), state="readonly", width=36)
        cb.grid(row=0, column=1)
        cb.bind("<<ComboboxSelected>>", self.on_preset)
        self.info = ttk.Label(p, text="", foreground=INFO, font=F_BOLD)
        self.info.grid(row=0, column=2, padx=14, sticky="w")
        self.info2 = ttk.Label(p, text="", foreground=MUTED)
        self.info2.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 4))

    def build_left(self, parent):
        panel = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        panel.pack(fill="x")
        self.lbl_state = tk.Label(panel, text="", bg=CARD, font=("Helvetica", 20, "bold"), fg=HEAD)
        self.lbl_state.pack(side="left", padx=18, pady=10)
        self.lbl_info = tk.Label(panel, text="", bg=CARD, font=F_TXT, justify="left", anchor="w")
        self.lbl_info.pack(side="left", padx=10)
        self.tape = tk.Canvas(parent, bg=CARD, height=130, highlightthickness=1, highlightbackground=LINE)
        self.tape.pack(fill="x", pady=8)
        self.tape.bind("<Configure>", self.redraw)
        self.legend = tk.Label(parent, bg=BG, fg=MUTED, justify="left", anchor="w", font=F_TXT)
        self.legend.pack(fill="x")

    def build_right_extra(self, parent):
        ttk.Label(parent, text="Función de transición δ", font=F_H2).pack(anchor="w")
        box = ttk.Frame(parent)
        box.pack(fill="x")
        sb = ttk.Scrollbar(box)
        sb.pack(side="right", fill="y")
        self.table = tk.Text(box, height=13, font=F_MONO_S, bg=CARD, wrap="none",
                             yscrollcommand=sb.set, state="disabled")
        self.table.pack(side="left", fill="x", expand=True)
        sb.config(command=self.table.yview)
        self.table.tag_config("next", background=ACTIVE)
        self.table.tag_config("last", background="#f6b8a6")
        self.line_of = {}

    def post_init(self):
        self.on_preset()

    def on_preset(self, _e=None):
        self.m = self.presets[self.lang.get()]
        m = self.m
        gamma = {s for (_q, s) in m["delta"]} | {w for (_q2, w, _m) in m["delta"].values()} | set(m["sigma"])
        gamma_txt = ", ".join(sorted(show(g) for g in gamma))
        states = sorted({q for q, _ in m["delta"]} | m["accepts"])
        self.info.config(text=m["desc"])
        self.info2.config(text=f"Σ = {{{', '.join(m['sigma'])}}}    Γ = {{{gamma_txt}}}    "
                               f"Q = {{{', '.join(states)}}}    q₀ = {m['start']}    "
                               f"F = {{{', '.join(sorted(m['accepts']))}}}    □ = blanco")
        self.legend.config(text=(
            "⊢ y ⊣ delimitan la cinta: tiene exactamente |w|+2 celdas y el cabezal no puede salir de ellas.\n"
            "Cabezal bidireccional (L/R); memoria acotada por la longitud de la entrada."
            if self.bounded else
            "La cinta es extensible en ambos sentidos con blancos (□). Movimientos: L, R o S (quieto)."))
        self.table.config(state="normal")
        self.table.delete("1.0", "end")
        self.line_of = {}
        for ln, key in enumerate(sorted(m["delta"]), start=1):
            q, s = key
            q2, w, mv = m["delta"][key]
            self.table.insert("end", f"δ({q},{show(s)}) → ({q2},{show(w)},{mv})\n")
            self.line_of[key] = ln
        self.table.config(state="disabled")
        self.word.set(m["word"])
        self.set_examples(m["examples"])
        self.load()

    def make_snaps(self, word):
        bad = sorted({c for c in word if c not in self.m["sigma"]})
        if bad:
            messagebox.showwarning("Cadena no válida",
                                   f"Símbolos fuera de Σ: {' '.join(bad)}\nΣ = {{{', '.join(self.m['sigma'])}}}")
            s = tm_initial(self.m, "", self.bounded)
            return [dict(s, final=False, msg=f"Cadena inválida (símbolos fuera de Σ: {' '.join(bad)})")]
        return [tm_initial(self.m, word, self.bounded)]

    def advance(self):
        cur = self.snaps[-1]
        if len(self.snaps) > self.max_steps:
            self.snaps.append(dict(cur, final=False, last=None,
                                   msg=f"Límite de {self.max_steps} pasos alcanzado (posible bucle infinito)"))
            return True
        nxt = tm_step(self.m, cur, self.bounded)
        if nxt is None:
            return False
        self.snaps.append(nxt)
        return True

    def render(self, s):
        sym = s["tape"].get(s["head"], BLANK)
        rng = (0, s["n"] + 1) if self.bounded else None
        draw_tape(self.tape, s["tape"], s["head"], rng=rng, head_text=f"{s['state']}",
                  blank_char="□", infinite=not self.bounded)
        nxt_rule = self.m["delta"].get((s["state"], sym))
        done = s.get("final") is not None
        rule_txt = "—" if (nxt_rule is None or done) else \
            f"δ({s['state']},{show(sym)}) = ({nxt_rule[0]},{show(nxt_rule[1])},{nxt_rule[2]})"
        self.lbl_state.config(text=f"Estado activo:  {s['state']}")
        self.lbl_info.config(text=(f"Símbolo leído: {show(sym)}     Posición del cabezal: {s['head']}     "
                                   f"Pasos: {s['steps']}\nPróxima regla: {rule_txt}"))
        self.table.tag_remove("next", "1.0", "end")
        self.table.tag_remove("last", "1.0", "end")
        if s["last"] in self.line_of:
            ln = self.line_of[s["last"]]
            self.table.tag_add("last", f"{ln}.0", f"{ln}.end")
        if not done and (s["state"], sym) in self.line_of:
            ln = self.line_of[(s["state"], sym)]
            self.table.tag_add("next", f"{ln}.0", f"{ln}.end")
            self.table.see(f"{ln}.0")


class LBAFrame(TMFrame):
    title = "Nivel 1 · Lenguajes sensibles al contexto — Autómata Linealmente Acotado"
    blurb = ("Máquina de Turing no determinista cuya cinta está limitada a la entrada, encerrada entre los "
             "delimitadores ⊢ y ⊣ (que nunca se sobrescriben ni se cruzan). Naranja = última regla "
             "aplicada, amarillo = regla que se aplicará a continuación.")
    bounded = True
    presets = LBAS
    default_word = "aabbcc"


class TuringFrame(TMFrame):
    title = "Nivel 0 · Lenguajes recursivamente enumerables — Máquina de Turing"
    blurb = ("M = (Q, Σ, Γ, δ, q₀, □, F). Cinta infinita en ambos sentidos, cabezal de lectura/escritura "
             "y control finito. Puede aceptar una cadena o calcular una función dejando el resultado en la cinta.")
    bounded = False
    presets = TMS
    default_word = "111+11"


# ═════════════════════════════ Panel principal ═══════════════════════════════
class MenuFrame(ttk.Frame):
    CARDS = [
        (3, "#2a9d8f", "Nivel 3 · Tipo 3", "Lenguajes regulares",
         "Autómata Finito Determinista\nSin memoria auxiliar. Muestra los estados y\nel estado actual símbolo a símbolo."),
        (2, "#e9a820", "Nivel 2 · Tipo 2", "Lenguajes libres de contexto",
         "Autómata de Pila\nMemoria LIFO. Animación de la pila\nmientras se consume la cadena."),
        (1, "#e76f51", "Nivel 1 · Tipo 1", "Lenguajes sensibles al contexto",
         "Autómata Linealmente Acotado\nCinta acotada con delimitadores ⊢ ⊣ y\ncabezal bidireccional."),
        (0, "#6a4c93", "Nivel 0 · Tipo 0", "Recursivamente enumerables",
         "Máquina de Turing\nCinta extendible, alfabeto de cinta,\ncabezal R/W y estado activo."),
    ]

    def __init__(self, master, app):
        super().__init__(master)
        ttk.Label(self, text="Simulador de la Jerarquía de Chomsky", font=("Helvetica", 24, "bold")).pack(pady=(28, 2))
        ttk.Label(self, text="Seleccione un módulo interactivo", foreground=MUTED, font=("Helvetica", 12)).pack()
        grid = ttk.Frame(self)
        grid.pack(pady=24)
        for n, (lvl, color, tag, name, desc) in enumerate(self.CARDS):
            card = tk.Frame(grid, bg=CARD, highlightthickness=2, highlightbackground=color, width=420, height=190)
            card.grid(row=n // 2, column=n % 2, padx=14, pady=14)
            card.pack_propagate(False)
            tk.Label(card, text=tag, bg=color, fg="white", font=F_BOLD, anchor="w", padx=10).pack(fill="x")
            tk.Label(card, text=name, bg=CARD, font=("Helvetica", 14, "bold"), pady=6).pack()
            tk.Label(card, text=desc, bg=CARD, fg=MUTED, font=F_TXT, justify="center").pack()
            ttk.Button(card, text="Abrir módulo", command=lambda L=lvl: app.open_level(L)).pack(pady=10)
        ttk.Label(self, text="Tipo 3 (regular) ⊂ Tipo 2 (libre de contexto) ⊂ Tipo 1 (sensible al contexto) "
                             "⊂ Tipo 0 (recursivamente enumerable)", foreground=MUTED).pack(pady=6)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de la Jerarquía de Chomsky")
        self.geometry("1320x820")
        self.minsize(1150, 720)
        self.configure(bg=BG)
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=BG, font=F_TXT)
        st.configure("TLabelframe", background=BG)
        st.configure("TLabelframe.Label", background=BG, font=F_BOLD)
        st.configure("TButton", padding=5)
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.menu = MenuFrame(self.container, self)
        self.frames = {3: DFAFrame(self.container, self), 2: PDAFrame(self.container, self),
                       1: LBAFrame(self.container, self), 0: TuringFrame(self.container, self)}
        self.show_menu()

    def _hide_all(self):
        for f in [self.menu, *self.frames.values()]:
            f.pack_forget()
        for f in self.frames.values():
            f.stop_play()

    def show_menu(self):
        self._hide_all()
        self.menu.pack(fill="both", expand=True)

    def open_level(self, lvl):
        self._hide_all()
        self.frames[lvl].pack(fill="both", expand=True)
        self.frames[lvl].after(50, self.frames[lvl].redraw)


if __name__ == "__main__":
    App().mainloop()
