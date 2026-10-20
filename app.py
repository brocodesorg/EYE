"""
Eye -> Space Web Server (FastAPI + WebSockets)
Hosts the procedural ASCII animation live for Render and local web browsers.

Usage:
    python app.py       # Runs locally on http://localhost:10000
On Render:
    Render runs: uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import asyncio
import os
import sys
import time
import webbrowser
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

import eye

app = FastAPI(title="Eye -> Space ASCII Web")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eye -> Space</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #060709;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at 50% 50%, rgba(20, 15, 35, 0.8), #030406 80%),
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
            background-size: 100% 100%, 32px 32px, 32px 32px;
        }

        .window {
            background: rgba(8, 8, 12, 0.94);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            box-shadow: 0 24px 64px rgba(0, 0, 0, 0.8), 0 0 32px rgba(90, 40, 120, 0.25);
            backdrop-filter: blur(12px);
            overflow: hidden;
            max-width: 96vw;
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.8s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(16px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .titlebar {
            background: #111318;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            user-select: none;
        }

        .title-left {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            font-weight: 500;
            color: #d1d5db;
            letter-spacing: 0.5px;
        }

        .title-icon {
            font-size: 15px;
            filter: drop-shadow(0 0 4px #38bdf8);
        }

        .window-dots {
            display: flex;
            gap: 8px;
        }

        .dot {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            display: inline-block;
        }
        .dot-red { background: #ef4444; }
        .dot-yellow { background: #eab308; }
        .dot-green { background: #22c55e; }

        .terminal-container {
            background: #000000;
            padding: 14px 18px;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
        }

        pre#screen {
            font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
            font-size: 12.5px;
            line-height: 1.15;
            letter-spacing: 0px;
            white-space: pre;
            background: transparent;
            user-select: none;
            text-shadow: 0 0 1px rgba(255,255,255,0.3);
        }

        .toolbar {
            background: #0c0e12;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 12px;
            color: #9ca3af;
        }

        .badges {
            display: flex;
            gap: 12px;
        }

        .badge {
            background: rgba(255, 255, 255, 0.06);
            padding: 3px 8px;
            border-radius: 4px;
            color: #cbd5e1;
            font-family: monospace;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 8px #22c55e;
        }
    </style>
</head>
<body>

<div class="window">
    <div class="titlebar">
        <div class="title-left">
            <span class="title-icon">👁️</span>
            <span>Eye -&gt; Space</span>
        </div>
        <div class="window-dots">
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
            <span class="dot dot-red"></span>
        </div>
    </div>

    <div class="terminal-container">
        <pre id="screen">Connecting to procedural stream...</pre>
    </div>

    <div class="toolbar">
        <div class="badges">
            <span class="badge">[Space] Pause</span>
            <span class="badge">[R] Restart</span>
        </div>
        <div class="status">
            <span class="status-dot" id="statusDot"></span>
            <span id="statusText">Live 30 FPS</span>
        </div>
    </div>
</div>

<script>
    const screen = document.getElementById('screen');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;

    function parseAnsi(text) {
        // Fast converter: \x1b[38;2;R;G;Bm -> <span style="color:rgb(R,G,B)">, \x1b[0m -> </span>
        return text
            .replace(/\\x1b\\[38;2;(\\d+);(\\d+);(\\d+)m/g, '<span style="color:rgb($1,$2,$3)">')
            .replace(/\\x1b\\[0m/g, '</span>')
            .replace(/\\x1b\\[[0-9;]*[a-zA-Z]/g, '');
    }

    function connect() {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            statusDot.style.background = '#22c55e';
            statusDot.style.boxShadow = '0 0 8px #22c55e';
            statusText.innerText = 'Connected';
        };

        ws.onmessage = (event) => {
            screen.innerHTML = parseAnsi(event.data);
        };

        ws.onclose = () => {
            statusDot.style.background = '#ef4444';
            statusDot.style.boxShadow = '0 0 8px #ef4444';
            statusText.innerText = 'Disconnected. Reconnecting...';
            setTimeout(connect, 2000);
        };
    }

    connect();

    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            if (ws && ws.readyState === WebSocket.OPEN) ws.send('toggle_pause');
        } else if (e.key === 'r' || e.key === 'R') {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send('restart');
        }
    });
</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_PAGE


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    W, H = 88, 38
    fps = 26
    duration = 15.0
    frame_delay = 1.0 / fps

    start_time = time.perf_counter()
    paused = False
    pause_start = 0.0

    async def listen_commands():
        nonlocal paused, pause_start, start_time
        try:
            while True:
                msg = await websocket.receive_text()
                if msg == "toggle_pause":
                    if paused:
                        start_time += time.perf_counter() - pause_start
                        paused = False
                    else:
                        paused = True
                        pause_start = time.perf_counter()
                elif msg == "restart":
                    start_time = time.perf_counter()
                    paused = False
        except Exception:
            pass

    listener_task = asyncio.create_task(listen_commands())

    try:
        while True:
            t0 = time.perf_counter()
            if not paused:
                elapsed = (t0 - start_time) % duration
                chars, rgb = eye.render_frame(elapsed, W, H, duration)
                ansi_str = eye.frame_to_ansi(chars, rgb)
                await websocket.send_text(ansi_str)

            compute_time = time.perf_counter() - t0
            sleep_time = max(0.005, frame_delay - compute_time)
            await asyncio.sleep(sleep_time)

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        listener_task.cancel()


def main():
    port = int(os.environ.get("PORT", 10000))
    print(f"\\n🚀 Eye -> Space Web Server starting at http://localhost:{port}")
    if "PORT" not in os.environ:
        # Running locally: open browser automatically after 1 second
        import threading
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()

    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False, log_level="warning")


if __name__ == "__main__":
    main()
