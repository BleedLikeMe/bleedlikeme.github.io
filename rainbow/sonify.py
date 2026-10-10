#!/usr/bin/env python3
"""Sonify light spectra by transposing them down 40 octaves (divide by 2**40).

Each clip is synthesised from a *model* spectrum, not a measurement:
continuous parts are shaped noise (built in the frequency domain with random
phases), spectral lines are near-pure tones.  Writes WAVs to ./audio/ and
prints the line-to-note table used in the paper.

    python3 rainbow/sonify.py
"""
import json, math, os
import numpy as np
from scipy.io import wavfile
from scipy.special import airy

C = 299_792_458.0
SHIFT = 2.0 ** 40              # 40 octaves
SR = 44_100
DUR = 8.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
rng = np.random.default_rng(1955)  # year of the song

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def audio_hz(nm):
    return C / (nm * 1e-9) / SHIFT


def note(hz):
    m = 69 + 12 * math.log2(hz / 440.0)
    n = round(m)
    cents = round((m - n) * 100)
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}", cents


def planck(nm, T):
    lam = nm * 1e-9
    return 1.0 / (lam ** 5 * (np.exp(6.62607e-34 * C / (lam * 1.380649e-23 * T)) - 1.0))


def gauss(x, mu, fwhm):
    s = fwhm / 2.3548
    return np.exp(-0.5 * ((x - mu) / s) ** 2)


def noise_from_spectrum(spec_nm, n=None):
    """Shaped noise whose power spectrum follows spec_nm(wavelength_nm) (per nm)."""
    n = n or int(SR * DUR)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    amp = np.zeros_like(freqs)
    ok = freqs > 1
    nm = C / (freqs[ok] * SHIFT) * 1e9
    vis = (nm >= 380) & (nm <= 750)
    # per-nm density -> per-Hz density: S_f = S_lam * lam^2 / c
    p = np.where(vis, spec_nm(np.clip(nm, 380, 750)) * nm ** 2, 0.0)
    amp[ok] = np.sqrt(p)
    ph = np.exp(2j * np.pi * rng.random(len(freqs)))
    return np.fft.irfft(amp * ph, n)


def tones(lines, n=None, width_hz=0.4):
    """Sum of near-pure tones, one per (nm, relative power).  A little random
    frequency drift keeps them from sounding like a test oscillator."""
    n = n or int(SR * DUR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for nm, pw in lines:
        f = audio_hz(nm)
        drift = np.cumsum(rng.normal(0, 1, n)) / SR
        drift = width_hz * drift / (np.abs(drift).max() + 1e-9)
        out += math.sqrt(pw) * np.sin(2 * np.pi * (f * t + np.cumsum(drift) / SR) + rng.random() * 6.28)
    return out


def finish(x, fade=0.4, rms_db=-20.0):
    x = x - x.mean()
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-12) * 10 ** (rms_db / 20)
    nf = int(fade * SR)
    env = np.ones(len(x))
    env[:nf] = np.linspace(0, 1, nf) ** 2
    env[-nf:] = np.linspace(1, 0, nf) ** 2
    x = x * env
    peak = np.abs(x).max()
    if peak > 0.95:
        x *= 0.95 / peak
    return x


def save(name, x):
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (finish(x) * 32767).astype(np.int16))
    print("wrote", name + ".wav")


# ---------- model spectra -------------------------------------------------
FRAUNHOFER = [(393.4, .9, 1.5), (396.8, .9, 1.5), (430.8, .5, .6), (486.1, .6, .4),
              (516.7, .4, .4), (527.0, .4, .3), (589.0, .7, .3), (589.6, .7, .3),
              (656.3, .7, .5)]


def sun(nm):
    s = planck(nm, 5778)
    for c, depth, w in FRAUNHOFER:
        s = s * (1 - depth * gauss(nm, c, w))
    return s


def incandescent(nm):
    return planck(nm, 2700)


def white_led(nm):
    blue = 1.0 * gauss(nm, 450, 22)
    phosphor = 0.55 * gauss(nm, 565, 110)
    return blue + phosphor


# Triphosphor fluorescent: line emission (nm, relative power).
FLUORESCENT = [(404.7, .06), (435.8, .35), (487.0, .25), (543.5, .9), (546.1, .45),
               (577.0, .05), (579.1, .05), (611.0, 1.0), (587.6, .12), (630.0, .1)]
FLUOR_BLUE = lambda nm: 0.18 * gauss(nm, 450, 50)  # broad blue europium phosphor

SODIUM = [(588.995, 1.0), (589.592, 0.5)]  # low-pressure sodium D lines
HYDROGEN = [(656.28, 1.0), (486.13, .35), (434.05, .15), (410.17, .07)]
NEON = [(585.2, .5), (588.2, .25), (603.0, .2), (607.4, .3), (609.6, .35),
        (614.3, .45), (616.4, .2), (621.7, .2), (626.6, .25), (633.4, .4),
        (638.3, .35), (640.2, .7), (650.6, .3), (659.9, .2), (692.9, .25), (703.2, .3)]


# ---------- rainbow scan --------------------------------------------------
def n_water(nm):
    um = nm / 1000
    return 1.3246 + 0.00308 / um ** 2   # Cauchy fit: 1.3435 @404 nm, 1.3335 @589, 1.3308 @706


def bow_angle_deg(nm):
    """Primary rainbow radius (angle from antisolar point), Descartes ray."""
    n = n_water(nm)
    i = math.acos(math.sqrt((n * n - 1) / 3))
    r = math.asin(math.sin(i) / n)
    dev = math.pi + 2 * i - 4 * r
    return 180 - math.degrees(dev)


def rainbow_scan(radius_mm=0.25):
    """Scan from 44 deg (outside, dark Alexander band) in to 37 deg (inside the bow).
    Per-wavelength Airy intensity, smeared by the 0.53 deg solar disc."""
    n = int(SR * DUR)
    t = np.linspace(0, 1, n)
    theta = 44.0 - 7.0 * t                       # degrees from antisolar point
    lams = np.linspace(400, 700, 90)
    out = np.zeros(n)
    sun_off = np.linspace(-0.265, 0.265, 15)
    disc = np.sqrt(1 - (sun_off / 0.265) ** 2)
    disc /= disc.sum()
    for lam in lams:
        th0 = bow_angle_deg(lam)
        # Airy argument; scale so supernumerary spacing is ~0.6 deg for 0.25 mm drops
        k = 4.3 * (radius_mm * 1e-3 / (lam * 1e-9)) ** (2 / 3) / 1000
        coarse = np.linspace(theta[0], theta[-1], 4000)   # envelope is slow: compute coarse, interpolate
        env_c = np.zeros(len(coarse))
        for off, w in zip(sun_off, disc):
            z = -(th0 - (coarse + off)) * k * 10
            env_c += w * airy(z)[0] ** 2
        env = np.interp(theta, coarse[::-1], env_c[::-1])
        # band of noise ~0.6% wide around this wavelength
        band = noise_from_spectrum(lambda nm: gauss(nm, lam, 3.4) * sun(np.array([lam]))[0])
        out += band * np.sqrt(env)
    return out, {round(l): round(bow_angle_deg(l), 2) for l in (400, 450, 500, 550, 600, 650, 700)}


# ---------- "Sing a Rainbow" ---------------------------------------------
SONG = [("red", [(650, 1)]), ("yellow", [(580, 1)]), ("pink", [(650, 1), "white"]),
        ("green", [(530, 1)]), ("purple", [(650, .7), (430, .8)]),
        ("orange", [(605, 1)]), ("blue", [(470, 1)])]


def sing_a_rainbow():
    """Each colour as a sung note (vibrato, soft attack).  Pink and purple are
    not spectral colours: pink = red plus a white-light wash, purple = red + blue."""
    note_len = 0.9
    t = np.arange(int(SR * note_len)) / SR
    env = np.minimum(1, t / 0.08) * np.minimum(1, (note_len - t) / 0.15)
    out = []
    for _, parts in SONG + [("rest", [])]:
        seg = np.zeros(len(t))
        for p in parts:
            if p == "white":
                seg += 0.5 * noise_from_spectrum(sun, len(t)) / 0.02
                continue
            nm, a = p
            f = audio_hz(nm)
            vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t)
            ph = 2 * np.pi * np.cumsum(f * vib) / SR
            seg += a * (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph))
        out.append(seg * env)
    return np.concatenate(out)


def fluorescent_photodiode():
    """What a photodiode + amplifier hears from a tube on a magnetic ballast
    (UK 50 Hz mains): light flickers at 100 Hz, rich in harmonics."""
    n = int(SR * DUR)
    t = np.arange(n) / SR
    mains = np.abs(np.sin(2 * np.pi * 50 * t)) ** 1.5   # rectified-ish light output
    return mains + 0.002 * rng.normal(0, 1, n)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["scan"]:
        scan, angles = rainbow_scan()
        save("08_rainbow_scan_outside_to_inside", scan)
        print(angles)
        sys.exit()
    save("01_sunlight", noise_from_spectrum(sun))
    save("02_incandescent_2700K", noise_from_spectrum(incandescent))
    save("03_white_led", noise_from_spectrum(white_led))
    save("04_fluorescent_tube", tones(FLUORESCENT) + 0.6 * noise_from_spectrum(FLUOR_BLUE) / 0.02 * 0.02)
    save("05_low_pressure_sodium", tones(SODIUM, width_hz=0.0))
    save("06_hydrogen_tube", tones(HYDROGEN))
    save("07_neon_sign", tones(NEON))
    scan, angles = rainbow_scan()
    save("08_rainbow_scan_outside_to_inside", scan)
    save("09_sing_a_rainbow", sing_a_rainbow())
    save("10_fluorescent_photodiode_100Hz", fluorescent_photodiode())

    table = {}
    for label, lines in [("fluorescent", FLUORESCENT), ("sodium", SODIUM),
                         ("hydrogen", HYDROGEN), ("neon", NEON),
                         ("song", [(p[0], 0) for _, ps in SONG for p in ps if p != "white"])]:
        table[label] = [(nm, round(audio_hz(nm), 1), *note(audio_hz(nm))) for nm, _ in lines]
    table["bow_angles_deg"] = angles
    table["band_edges"] = [(nm, round(audio_hz(nm), 1), *note(audio_hz(nm))) for nm in (380, 400, 700, 750)]
    print(json.dumps(table, indent=1))
