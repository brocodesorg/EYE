"""
In Your Eyes - Procedural ASCII Animation (Terminal & Popup Window).

Story (about 15 seconds):
  0.0 -  3.0s  an eye with skin, eyebrow, lashes opens, looks around and blinks
  3.0 - 10.5s  camera dives into the iris; the pupil grows and fills the screen
 10.5 - 15.0s  inside the pupil: a starfield with sparkles and a striped planet

Run:
    python eye.py                 # Opens the sleek popup window on screen
    python eye.py --terminal      # Runs in the terminal with ANSI colors
    python eye.py --loop          # Repeat animation continuously
"""
import argparse
import os
import shutil
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Dark -> bright character ramp
RAMP = " .`'^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
RAMP_ARR = np.array(list(RAMP))

F32 = np.float32


# ----------------------------------------------------------------------------
# Math helpers
# ----------------------------------------------------------------------------
def ss(a, b, x):
    """smoothstep(a, b, x) - works if a > b as well"""
    t = np.clip((x - a) / (b - a + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hash2(ix, iy, seed=0.0):
    n = np.sin(ix * 127.1 + iy * 311.7 + seed * 74.7) * 43758.5453
    return n - np.floor(n)


def vnoise(x, y, seed=0.0):
    """value noise in [0, 1]"""
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = hash2(ix, iy, seed)
    b = hash2(ix + 1, iy, seed)
    c = hash2(ix, iy + 1, seed)
    d = hash2(ix + 1, iy + 1, seed)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


def fbm(x, y, octaves=4, seed=0.0):
    total, amp, freq, norm = 0.0, 0.5, 1.0, 0.0
    for _ in range(octaves):
        total = total + amp * vnoise(x * freq, y * freq, seed)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def col(r, g, b):
    return np.array([r, g, b], np.float32)


# ----------------------------------------------------------------------------
# SPACE (seen through the pupil)
# ----------------------------------------------------------------------------
def star_layer(x, y, t, cell, seed, density):
    fx, fy = x / cell, y / cell
    ix, iy = np.floor(fx), np.floor(fy)
    lx, ly = fx - ix, fy - iy
    exists = hash2(ix, iy, seed) > (1.0 - density)
    px = 0.3 + 0.4 * hash2(ix, iy, seed + 1.0)
    py = 0.3 + 0.4 * hash2(ix, iy, seed + 2.0)
    dx, dy = lx - px, ly - py
    phase = hash2(ix, iy, seed + 3.0) * 6.2831
    bright = 0.35 + 0.65 * hash2(ix, iy, seed + 4.0)
    twinkle = 0.55 + 0.45 * np.sin(t * 3.0 + phase)
    core = np.exp(-(dx * dx + dy * dy) / 0.0009)
    arm_h = np.exp(-np.abs(dy) / 0.012) * np.exp(-np.abs(dx) / 0.32)
    arm_v = np.exp(-np.abs(dx) / 0.012) * np.exp(-np.abs(dy) / 0.32)
    s = (core + 0.7 * (arm_h + arm_v)) * bright * twinkle * exists
    s = np.clip(s, 0, 1)

    # Per-star vivid color tinting: blue, gold, magenta-pink, crystal white
    star_hue = hash2(ix, iy, seed + 5.0)
    tint_r = np.where(star_hue < 0.25, 0.55,
             np.where(star_hue < 0.50, 1.00,
             np.where(star_hue < 0.75, 1.00, 0.95)))
    tint_g = np.where(star_hue < 0.25, 0.70,
             np.where(star_hue < 0.50, 0.82,
             np.where(star_hue < 0.75, 0.55, 0.92)))
    tint_b = np.where(star_hue < 0.25, 1.00,
             np.where(star_hue < 0.50, 0.45,
             np.where(star_hue < 0.75, 0.90, 1.00)))
    tint = np.stack([tint_r, tint_g, tint_b], axis=-1).astype(np.float32)
    return s[..., None] * tint


def planet(x, y, t, strength):
    rp = 0.40 * (1.0 + 0.015 * np.sin(t * 2.0))
    d = np.hypot(x, y)
    nx, ny = x / rp, y / rp
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0, 1))
    light = np.array([-0.45, 0.55, 0.70])
    light = light / np.linalg.norm(light)
    diff = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)

    # Horizontal bands that drift slowly, like gas-giant stripes
    warp = fbm(nx * 2.0 + t * 0.25, ny * 6.0, 3, 7.0)
    bands = 0.5 + 0.5 * np.sin(ny * 34.0 + warp * 5.0)
    pink = col(0.95, 0.35, 0.55)
    deep = col(0.45, 0.04, 0.18)
    cream = col(1.00, 0.88, 0.93)
    base = lerp(deep, pink, bands[..., None])
    stripe_hi = (np.clip(np.sin(ny * 17.0 + 1.3 + warp * 3.0), 0, 1) ** 4)[..., None]
    base = lerp(base, cream, stripe_hi * 0.65)

    # Electric blue accent band
    blue_band = (np.clip(np.sin(ny * 23.0 + 0.7 + warp * 2.0), 0, 1) ** 6)[..., None]
    base = lerp(base, col(0.15, 0.60, 0.98), blue_band * 0.35)

    lit = base * (0.22 + 0.95 * diff)[..., None]
    mask = ss(rp, rp - 0.02, d)[..., None]

    glow = (np.exp(-np.maximum(d - rp, 0) / 0.12) * 0.40)[..., None] * col(0.90, 0.20, 0.55)
    return (lit * mask + glow * (1 - mask)) * strength


def space(x, y, t, planet_strength):
    img = np.zeros(x.shape + (3,), np.float32)
    img += col(0.0, 0.0, 0.012)

    # Cosmic nebula clouds
    n1 = fbm(x * 1.5 + t * 0.05, y * 1.5, 5, 42.0)
    n2 = fbm(x * 2.0 - t * 0.03, y * 1.8 + 0.5, 4, 17.0)
    n3 = fbm(x * 1.2 + 1.0, y * 1.0 + t * 0.02, 3, 31.0)
    nebula = np.zeros(x.shape + (3,), np.float32)
    nebula += (n1 ** 2.0)[..., None] * col(0.35, 0.05, 0.55) * 0.55    # Purple
    nebula += (n2 ** 2.5)[..., None] * col(0.05, 0.30, 0.45) * 0.45    # Teal
    nebula += (n3 ** 3.0)[..., None] * col(0.50, 0.08, 0.25) * 0.35    # Magenta
    img = img + nebula

    drift = t * 0.03
    s1 = star_layer(x + drift, y, t, 0.34, 11.0, 0.62)
    s2 = star_layer(x + drift * 0.5, y + 0.1, t, 0.21, 23.0, 0.28)
    img = img + s1 + 0.7 * s2

    pl = planet(x, y, t, planet_strength)
    img = np.maximum(img * (1.0 - 0.9 * (np.hypot(x, y) < 0.40)[..., None]), 0) + pl
    return np.clip(img, 0, 1)


# ----------------------------------------------------------------------------
# EYE (Faithful to Reference: Distinct Eyebrows, Dark Lids, Vignette)
# ----------------------------------------------------------------------------
def eye(u, v, x, y, t, openness, gx, gy, pr, space_strength):
    """u,v = zoomed eye coords, x,y = screen coords (used for the space inside the pupil)"""
    L = 1.25
    s = u / L
    inx = np.abs(s) < 1.0
    bow = np.clip(1.0 - s * s, 0.0, 1.0)
    up = 0.60 * openness * bow * (1.0 + 0.15 * s)
    lo = -0.36 * openness * bow
    d_up = up - v
    d_lo = v - lo
    edge = np.minimum(d_up, d_lo)
    inside = ss(0.0, 0.015, edge) * inx

    # ---- Skin with Vignette (Corners fade softly into dark) ----
    dist = np.hypot(u * 0.60, v * 0.85)
    vignette = np.clip(1.0 - ss(0.65, 1.35, dist), 0.0, 1.0)

    skin_base = col(0.68, 0.42, 0.24)  # Warm glowing amber/orange
    sk = skin_base * (0.75 + 0.35 * fbm(u * 6, v * 6, 4, 3.0))[..., None]
    sk = sk * (0.80 + 0.30 * ss(-1.0, 1.0, v))[..., None]
    sk = sk * (0.18 + 0.82 * vignette)[..., None] * 0.45

    # ---- Eyebrow (Prominent arched dark band with distinct texture) ----
    brow_y = 1.00 - 0.20 * (s * s)
    brow_dist = np.abs(v - brow_y)
    eb_shape = np.exp(-((brow_dist / 0.11) ** 2)) * (np.abs(s) < 1.05)
    eb_hair = ss(0.20, 0.70, fbm(u * 28, v * 9 + u * 5, 4, 5.0))
    sk = lerp(sk, col(0.02, 0.015, 0.01), np.clip(eb_shape * eb_hair * 2.2, 0.0, 0.96)[..., None])

    # ---- Upper Eyelid Crease (Deep dark crease line above upper lid) ----
    crease_v = up + 0.18 * openness + 0.04
    crease = np.exp(-(((v - crease_v) / 0.025) ** 2)) * (v > 0) * (np.abs(s) < 1.1)
    sk = sk * (1.0 - 0.78 * crease)[..., None]

    # ---- Lower Bag Shadow Line ----
    bag = np.exp(-(((v - (lo - 0.14)) / 0.05) ** 2)) * inx
    sk = sk * (1.0 - 0.45 * bag)[..., None]

    # ---- Eyeball ----
    du, dv = u - gx, v - gy
    r = np.hypot(du, dv)
    ang = np.arctan2(dv, du)
    R = 0.48

    sclera = col(0.92, 0.86, 0.82) * (1.0 - 0.40 * s * s)[..., None]
    vein = (1.0 - np.abs(2.0 * fbm(u * 9, v * 9, 3, 9.0) - 1.0)) ** 9
    sclera = lerp(sclera, col(0.82, 0.25, 0.22), (vein * ss(0.35, 1.0, np.abs(s)) * 0.7)[..., None])

    fib = fbm(np.cos(ang) * 5 + r * 1.5, np.sin(ang) * 5 + r * 1.5, 4, 2.0)
    rad = np.clip((r - pr) / (R - pr + 1e-6), 0.0, 1.0)

    # Multi-color iris: shifting amber, emerald, sapphire sectors
    hue_ang = ang + t * 0.4
    h1 = np.sin(hue_ang * 1.5) * 0.5 + 0.5
    h2 = np.sin(hue_ang * 1.5 + 2.094) * 0.5 + 0.5

    amber    = col(0.95, 0.58, 0.12)
    emerald  = col(0.12, 0.78, 0.42)
    sapphire = col(0.20, 0.35, 0.92)
    gold_dk  = col(0.52, 0.28, 0.06)
    deep_bl  = col(0.08, 0.15, 0.45)

    iris_bright = lerp(amber, lerp(emerald, sapphire, h2[..., None]), h1[..., None])
    iris_dark   = lerp(gold_dk, deep_bl, h1[..., None])

    iris = lerp(iris_bright, iris_dark, rad[..., None])
    iris = iris * (0.55 + 0.9 * fib)[..., None]

    # Glowing golden ring at iris boundary
    ring = np.exp(-((r - R * 0.93) / 0.022) ** 2)
    iris = iris + (ring * 0.55)[..., None] * col(1.0, 0.88, 0.30)

    iris = iris * (1.0 - 0.8 * ss(0.78 * R, R, r))[..., None]
    eyeball = lerp(sclera, iris, ss(R, R - 0.02, r)[..., None])

    # Pupil = window into deep space
    sp = space(x, y, t, space_strength)
    pup_edge = ss(0.0, 0.04, pr - r)[..., None]
    pupil_col = sp * (0.35 + 0.65 * pup_edge)
    eyeball = lerp(eyeball, pupil_col, ss(pr, pr - 0.01, r)[..., None])

    # Neon glowing pupil rim (cyan <-> magenta shift)
    pup_glow = np.exp(-((r - pr) / 0.025) ** 2) * (pr < 0.9)
    glow_shift = np.sin(t * 2.5) * 0.5 + 0.5
    glow_col = lerp(col(0.0, 0.92, 0.95), col(0.88, 0.15, 0.90), glow_shift)
    eyeball = eyeball + (pup_glow * 0.45)[..., None] * glow_col

    # Specular highlight with subtle rainbow halo
    hl_cx, hl_cy = gx - 0.16, gy + 0.17
    hl_d2 = (u - hl_cx) ** 2 + (v - hl_cy) ** 2
    hl = np.exp(-(hl_d2 / 0.0025))
    hl = hl * (pr < 1.0)
    hl_r = np.exp(-(hl_d2 / 0.0045))
    hl_fringe = np.clip(hl_r - hl, 0.0, 1.0)
    fringe_ang = np.arctan2(v - hl_cy, u - hl_cx)
    fr_r = (0.5 + 0.5 * np.sin(fringe_ang * 2.0)).astype(np.float32)
    fr_g = (0.5 + 0.5 * np.sin(fringe_ang * 2.0 + 2.094)).astype(np.float32)
    fr_b = (0.5 + 0.5 * np.sin(fringe_ang * 2.0 + 4.189)).astype(np.float32)
    fringe_rgb = np.stack([fr_r, fr_g, fr_b], axis=-1)
    eyeball = eyeball + (hl * 0.9)[..., None] + (hl_fringe * 0.35)[..., None] * fringe_rgb

    # Eyelids shadow
    eyeball = eyeball * (0.40 + 0.60 * ss(0.0, 0.28, d_up))[..., None]

    out = lerp(sk, eyeball, inside[..., None])

    # ---- Dark Lines in Eyes (Eyelashes & Deep Contour Framing) ----
    lash_up = np.exp(-((d_up / 0.024) ** 2)) * inx
    lash_lo = np.exp(-((d_lo / 0.018) ** 2)) * inx
    dark_contour = np.clip(lash_up * 1.35 + lash_lo * 0.95, 0.0, 1.0)
    out = lerp(out, col(0.015, 0.01, 0.01), (dark_contour * 0.94)[..., None])

    water = np.exp(-(((d_lo - 0.004) / 0.018) ** 2)) * inx
    out = lerp(out, col(0.85, 0.30, 0.38), (water * 0.8)[..., None])
    return np.clip(out, 0.0, 1.0)


# ----------------------------------------------------------------------------
# Frame Renderer
# ----------------------------------------------------------------------------
def render_frame(t, W, H, T=15.0):
    """Returns (chars[H, W], rgb[H, W, 3] uint8)."""
    cx = np.arange(W, dtype=np.float32) + 0.5 - W / 2
    cy = (np.arange(H, dtype=np.float32) + 0.5 - H / 2) * 2.0
    scale = min((W / 2) / 1.7, H / 1.5)
    x = (cx[None, :] / scale) * np.ones((H, 1), np.float32)
    y = -(cy[:, None] / scale) * np.ones((1, W), np.float32)

    p = float(ss(2.5, 10.8, t))
    zoom = float(np.exp(p * np.log(16.0)))
    gaze_amt = 1.0 - float(ss(2.0, 5.0, t))
    gx = gaze_amt * 0.14 * np.sin(t * 1.3)
    gy = gaze_amt * 0.05 * np.cos(t * 1.7)

    blink = np.exp(-(((t - 1.55) / 0.09) ** 2))
    opening = float(ss(0.0, 0.9, t)) * (1.0 - 0.95 * blink)
    pr_eye = 0.20 * (1.0 + 0.10 * np.sin(t * 2.4))

    plan = float(ss(5.0, 9.5, t))

    if t > 11.2:
        rgb = space(x, y, t, plan)
    else:
        u = gx + x / zoom
        v = gy + y / zoom
        rgb = eye(u, v, x, y, t, opening, gx, gy, pr_eye, plan)

    fade = float(ss(T, T - 0.6, t)) * float(ss(0.0, 0.4, t))
    rgb = rgb * fade

    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    idx = np.clip((lum ** 0.80) * (len(RAMP) - 1), 0, len(RAMP) - 1).astype(int)
    chars = RAMP_ARR[idx]
    peak = np.maximum(rgb.max(axis=2, keepdims=True), 1e-4)
    shown = rgb / peak * np.clip(0.35 + peak * 1.10, 0.0, 1.0)
    shown = np.where(lum[..., None] < 0.02, 0.0, shown)
    return chars, (np.clip(shown, 0.0, 1.0) * 255).astype(np.uint8)


def frame_to_ansi(chars, rgb):
    H, W = chars.shape
    q = (rgb >> 2) << 2
    lines = []
    for j in range(H):
        out, prev = [], None
        for i in range(W):
            c = chars[j, i]
            if c == " ":
                out.append(" ")
                continue
            k = (int(q[j, i, 0]), int(q[j, i, 1]), int(q[j, i, 2]))
            if k != prev:
                out.append("\x1b[38;2;%d;%d;%dm" % k)
                prev = k
            out.append(c)
        lines.append("".join(out))
    return "\x1b[H" + "\x1b[0m\n".join(lines) + "\x1b[0m"


# ----------------------------------------------------------------------------
# Glyph Atlas for Instant Anti-Aliased Rendering
# ----------------------------------------------------------------------------
def build_glyph_atlas(font_size=12):
    font_names = ["consola.ttf", "cascadiacode.ttf", "cour.ttf", "arial.ttf"]
    font = None
    for fname in font_names:
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    gw = int(getattr(font, "getlength", lambda s: 7)("M"))
    gw = max(gw, 7)
    try:
        ascent, descent = font.getmetrics()
        gh = ascent + descent
    except Exception:
        gh = max(int(gw * 1.85), 13)

    glyph_masks = np.zeros((len(RAMP), gh, gw), dtype=np.float32)
    for i, ch in enumerate(RAMP):
        im = Image.new("L", (gw, gh), 0)
        dr = ImageDraw.Draw(im)
        dr.text((0, 0), ch, fill=255, font=font)
        glyph_masks[i] = np.array(im, dtype=np.float32) / 255.0

    return gw, gh, glyph_masks


# ----------------------------------------------------------------------------
# POPUP WINDOW MODE (Right Side Positioned + Slight Transparency + Eyebrows)
# ----------------------------------------------------------------------------
def run_popup(fps=30, duration=15.0, width=90, height=40, loop=True):
    import tkinter as tk
    from PIL import ImageTk

    gw, gh, glyph_masks = build_glyph_atlas(font_size=12)
    win_w = width * gw
    win_h = height * gh

    root = tk.Tk()
    root.title("Eye -> Space")
    root.configure(bg="#000000")
    root.resizable(False, False)

    # Slight transparency (very slight, subtle frosted effect over VS Code)
    try:
        root.attributes("-alpha", 0.94)
    except Exception:
        pass

    # Position on the MAJOR RIGHT SIDE of the screen by default
    def snap_right(event=None):
        curr_sw = root.winfo_screenwidth()
        curr_sh = root.winfo_screenheight()
        r_px = max(0, curr_sw - win_w - 70)
        r_py = max(0, (curr_sh - win_h) // 2 - 20)
        root.geometry(f"{win_w}x{win_h}+{r_px}+{r_py}")

    def snap_center(event=None):
        curr_sw = root.winfo_screenwidth()
        curr_sh = root.winfo_screenheight()
        c_px = max(0, (curr_sw - win_w) // 2)
        c_py = max(0, (curr_sh - win_h) // 2 - 20)
        root.geometry(f"{win_w}x{win_h}+{c_px}+{c_py}")

    # Apply right-side position immediately and ensure it persists after focus
    snap_right()
    root.update_idletasks()
    snap_right()

    # Elevate window on top of VS Code
    root.lift()
    root.attributes("-topmost", True)
    root.after(600, lambda: root.attributes("-topmost", False))
    root.focus_force()

    # Lock right-side position on launch
    root.after_idle(snap_right)
    root.after(50, snap_right)
    root.after(150, snap_right)

    label = tk.Label(root, bg="#000000", bd=0, highlightthickness=0)
    label.pack(fill="both", expand=True)

    state = {
        "running": True,
        "paused": False,
        "start_time": time.perf_counter(),
        "pause_start": 0.0,
        "is_topmost": False
    }

    def toggle_pause(event=None):
        if state["paused"]:
            paused_duration = time.perf_counter() - state["pause_start"]
            state["start_time"] += paused_duration
            state["paused"] = False
        else:
            state["paused"] = True
            state["pause_start"] = time.perf_counter()

    def restart(event=None):
        state["start_time"] = time.perf_counter()
        state["paused"] = False

    def toggle_topmost(event=None):
        state["is_topmost"] = not state["is_topmost"]
        root.attributes("-topmost", state["is_topmost"])


    def on_close(event=None):
        state["running"] = False
        try:
            root.destroy()
        except Exception:
            pass

    # Keyboard shortcuts
    root.bind("<space>", toggle_pause)
    root.bind("<r>", restart)
    root.bind("<R>", restart)
    root.bind("<t>", toggle_topmost)
    root.bind("<T>", toggle_topmost)
    root.bind("<c>", snap_center)
    root.bind("<C>", snap_center)
    root.bind("<Right>", snap_right)
    root.bind("<Escape>", on_close)
    root.bind("<q>", on_close)
    root.bind("<Q>", on_close)
    root.protocol("WM_DELETE_WINDOW", on_close)

    def tick():
        if not state["running"]:
            return

        now = time.perf_counter()
        if not state["paused"]:
            elapsed = now - state["start_time"]
            if elapsed > duration:
                if loop:
                    state["start_time"] = now
                    elapsed = 0.0
                else:
                    on_close()
                    return

            chars, rgb = render_frame(elapsed, width, height, duration)
            
            # Correct normalized luminance mapping across full ASCII ramp
            lum_norm = (rgb @ np.array([0.299, 0.587, 0.114], np.float32)) / 255.0
            idx = np.clip((lum_norm ** 0.80) * (len(RAMP) - 1), 0, len(RAMP) - 1).astype(int)

            selected = glyph_masks[idx]
            mask = selected.transpose(0, 2, 1, 3).reshape(win_h, win_w, 1)
            rgb_exp = np.repeat(np.repeat(rgb, gh, axis=0), gw, axis=1)
            frame_pixels = (rgb_exp * mask).astype(np.uint8)

            img = Image.fromarray(frame_pixels)
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo)
            label.image = photo

        frame_ms = max(1, int(1000 / fps))
        if state["running"]:
            root.after(frame_ms, tick)

    tick()
    root.mainloop()


# ----------------------------------------------------------------------------
# TERMINAL MODE (Fallback if user runs with --terminal)
# ----------------------------------------------------------------------------
def run_terminal(fps=24, duration=15.0, width=0, height=0, loop=False):
    if os.name == "nt":
        os.system("")

    size = shutil.get_terminal_size((120, 40))
    W = width or size.columns
    H = height or max(10, size.lines - 1)

    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    try:
        while True:
            start = time.time()
            frame_no = 0
            while True:
                t = frame_no / fps
                if t > duration:
                    break
                chars, rgb = render_frame(t, W, H, duration)
                sys.stdout.write(frame_to_ansi(chars, rgb))
                sys.stdout.flush()
                frame_no += 1
                delay = start + frame_no / fps - time.time()
                if delay > 0:
                    time.sleep(delay)
            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="In Your Eyes - ASCII Animation")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=float, default=15.0)
    ap.add_argument("--width", type=int, default=90)
    ap.add_argument("--height", type=int, default=40)
    ap.add_argument("--loop", action="store_true", default=True, help="Repeat animation continuously")
    ap.add_argument("--no-loop", action="store_false", dest="loop")
    ap.add_argument("--terminal", "--cli", action="store_true", help="Run in terminal ANSI text mode")
    a = ap.parse_args()

    if a.terminal:
        run_terminal(fps=a.fps, duration=a.duration, width=a.width, height=a.height, loop=a.loop)
    else:
        run_popup(fps=a.fps, duration=a.duration, width=a.width, height=a.height, loop=a.loop)


if __name__ == "__main__":
    main()
