# 👁️ EYE — In Your Eyes

> **A mesmerizing procedural ASCII shader experience in Python.**  
> Dive through a living eye into the depths of a cosmic nebula.

---

## ✨ Features

- **🌈 Shifting Kaleidoscopic Iris:** Amber, emerald, and sapphire sectors rotate with procedural noise fibers.
- **✨ Golden Limbal Ring & Neon Rim:** Pulsing cyan-to-magenta glowing pupil border and golden outer iris contour.
- **🌌 Cosmic Nebula Dive:** As the camera plunges into the pupil, a multi-layered starfield and glowing striped planet emerge from deep space.
- **⚡ 60+ FPS Anti-Aliased Rendering:** High-performance vectorized NumPy math and subpixel glyph rasterization.
- **🪟 Sleek Floating HUD Popup:** Opens directly as a floating, subtly translucent window positioned cleanly on screen, with full keyboard shortcuts.
- **📟 Terminal Fallback:** Supports truecolor ANSI escape sequence rendering directly inside terminal emulators.

---

## 🎬 Story Timeline

```
  0.0s –  3.0s   Eye with eyebrow, lashes, and skin opens, looks around, and blinks.
  3.0s – 10.5s   Camera dives smoothly toward the pupil; the iris fills the view.
 10.5s – 15.0s   Inside the pupil: Infinite space, twinkling stars, and a striped planet.
```

---

## 🚀 Quick Start

### 1. Requirements

Make sure you have Python 3.9+ installed, then install dependencies:

```bash
pip install numpy pillow
```

### 2. Run

#### 🖥️ Floating Window (Default)
```bash
python eye.py
```
*Or simply click the **▶ Run** button in VS Code.*

#### 📟 Terminal Mode
```bash
python eye.py --terminal
```

---

## ⌨️ Controls & Hotkeys

| Key | Action |
|:---:|:---|
| <kbd>Space</kbd> | Pause / Resume animation |
| <kbd>R</kbd> | Restart animation from beginning |
| <kbd>→</kbd> (Right Arrow) | Snap window to the **Right side** |
| <kbd>C</kbd> | Snap window to **Center** |
| <kbd>T</kbd> | Toggle **Always-on-Top** |
| <kbd>Esc</kbd> or <kbd>Q</kbd> | Close window |

---

## 🛠️ CLI Options

```bash
python eye.py [options]

Options:
  --fps FPS           Frame rate (default: 30)
  --duration SECONDS  Timeline duration in seconds (default: 15.0)
  --width COLS        Width in characters (default: 90)
  --height ROWS       Height in characters (default: 40)
  --loop              Loop continuously (default: enabled)
  --no-loop           Play once and exit
  --terminal, --cli   Run in terminal ANSI text mode
```

---

## 📄 License

MIT © [brocodesorg](https://github.com/brocodesorg) & [Avi Bhosale](https://github.com/AviBhosale01)
