#!/usr/bin/env python3
"""Figures for the LaTeX paper (vector PDFs next to this file).

    python3 rainbow/paper/figures.py
"""
import math, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sonify as S  # noqa: E402

from matplotlib import font_manager
for _f in font_manager.findSystemFonts(["/usr/share/texmf/fonts/opentype/public/lm"]):
    font_manager.fontManager.addfont(_f)   # Latin Modern, to match the LaTeX text
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Latin Modern Roman", "DejaVu Serif"], "mathtext.fontset": "cm",
    "font.size": 9, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "pdf.fonttype": 3,
})
GREY, ACCENT, GRID = "#9a9a92", "#1f5fbf", "#e3e3df"
NOTES = [("F$\\sharp$4", 370.0), ("G4", 392.0), ("G$\\sharp$4", 415.3), ("A4", 440.0),
         ("A$\\sharp$4", 466.2), ("B4", 493.9), ("C5", 523.3), ("C$\\sharp$5", 554.4),
         ("D5", 587.3), ("D$\\sharp$5", 622.3), ("E5", 659.3), ("F5", 698.5)]


def note_axis(ax, lo=360, hi=720):
    ax.set_xscale("log", base=2)
    ax.set_xlim(lo, hi)
    ax.set_xticks([hz for _, hz in NOTES])
    ax.set_xticklabels([f"{n}\n{hz:.0f}" for n, hz in NOTES], fontsize=7.5)
    ax.minorticks_off()
    for _, hz in NOTES:
        ax.axvline(hz, color=GRID, lw=0.5, zorder=0)


def fig_sources():
    rows = [("Sunlight", S.sun, None), ("Incandescent bulb", S.incandescent, None),
            ("White LED", S.white_led, None), ("Fluorescent tube", None, S.FLUORESCENT),
            ("Sodium lamp", None, S.SODIUM), ("Hydrogen tube", None, S.HYDROGEN),
            ("Neon sign", None, S.NEON)]
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    h = 0.8
    for i, (name, fn, lines) in enumerate(rows):
        y0 = len(rows) - 1 - i
        accent = name == "Fluorescent tube"
        if fn is not None:
            nm = np.linspace(380, 750, 400)
            p = fn(nm) * nm ** 2
            p /= p.max()
            hz = S.audio_hz(nm)
            ax.fill_between(hz, y0, y0 + h * p, color=GREY, alpha=0.45, lw=0)
            ax.plot(hz, y0 + h * p, color=GREY, lw=0.7)
        else:
            m = max(pw for _, pw in lines)
            for nm, pw in lines:
                ax.vlines(S.audio_hz(nm), y0, y0 + h * max(pw / m, 0.08),
                          color=ACCENT if accent else GREY, lw=1.6)
        ax.text(357, y0 + 0.25, name, ha="right", va="center", fontsize=8.5,
                color=ACCENT if accent else "black", fontweight="bold" if accent else "normal")
    note_axis(ax)
    ax.set_ylim(-0.1, len(rows))
    ax.set_yticks([])
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Transposed frequency (Hz) and nearest note")
    ax.text(362, len(rows) - 0.05, "red (750 nm)", fontsize=7, color="0.4", va="bottom")
    ax.text(715, len(rows) - 0.05, "violet (380 nm)", fontsize=7, color="0.4", va="bottom", ha="right")
    fig.subplots_adjust(left=0.2, right=0.98, top=0.95, bottom=0.17)
    fig.savefig(os.path.join(HERE, "fig_sources.pdf"))


def scan_model(radius_mm=0.25):
    """Brightness I(theta, lambda) from the same Airy model sonify.rainbow_scan() uses."""
    theta = np.linspace(44.0, 37.0, 700)
    lams = np.linspace(400, 700, 150)
    sun_off = np.linspace(-0.265, 0.265, 15)
    disc = np.sqrt(1 - (sun_off / 0.265) ** 2)
    disc /= disc.sum()
    from scipy.special import airy
    I = np.zeros((len(lams), len(theta)))
    for j, lam in enumerate(lams):
        th0 = S.bow_angle_deg(lam)
        k = 4.3 * (radius_mm * 1e-3 / (lam * 1e-9)) ** (2 / 3) / 1000
        for off, w in zip(sun_off, disc):
            I[j] += w * airy(-(th0 - (theta + off)) * k * 10)[0] ** 2
        I[j] *= S.sun(np.array([lam]))[0]
    return theta, lams, I / I.max()


def fig_scan():
    theta, lams, I = scan_model()
    hz = S.audio_hz(lams)
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    ax.pcolormesh(theta, hz, I ** 0.6, shading="auto", cmap="Greys", vmin=0, vmax=1, rasterized=True)
    ax.set_yscale("log", base=2)
    ax.set_ylim(hz.min(), hz.max())
    ticks = [(n, f) for n, f in NOTES if hz.min() <= f <= hz.max()]
    ax.set_yticks([f for _, f in ticks])
    ax.set_yticklabels([n for n, _ in ticks], fontsize=7.5)
    ax.minorticks_off()
    ax.set_xlim(44, 37)
    ax.set_xlabel("Angle from the antisolar point (degrees); the scan runs outside $\\rightarrow$ inside")
    ax.set_ylabel("Pitch (transposed)")
    edge = np.array([S.bow_angle_deg(l) for l in lams])
    ax.plot(edge, hz, color=ACCENT, lw=1.0, ls="--")
    ax.text(43.9, 600, "geometric bow edge\n(red 42.4$^\\circ$, violet 40.5$^\\circ$)", fontsize=7.5,
            color=ACCENT, ha="left", va="center")
    ax.text(43.85, 420, "Alexander's\ndark band\n(silent)", fontsize=7.5, color="0.3", va="center")
    ax.text(38.6, 420, "bright sky inside\nthe bow: full hiss", fontsize=7.5, color="white", va="center", ha="center")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.96, bottom=0.18)
    fig.savefig(os.path.join(HERE, "fig_scan.pdf"), dpi=300)


if __name__ == "__main__":
    fig_sources()
    fig_scan()
    print("ok")
