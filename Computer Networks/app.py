"""
FastAPI Server providing Web Dashboard and WebSocket streaming for Network Performance Monitor.
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from network_collector import NetworkCollector
from traffic_generator import TrafficGenerator

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Network Performance Monitor")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

collector = NetworkCollector(history_len=60)
traffic = TrafficGenerator()


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/metrics")
async def get_metrics():
    return JSONResponse(collector.collect())


@app.get("/api/history")
async def get_history():
    return JSONResponse(collector.get_history())


@app.post("/api/traffic/start")
async def start_traffic():
    traffic.start()
    return {"status": "started", "active": traffic.is_running}


@app.post("/api/traffic/stop")
async def stop_traffic():
    traffic.stop()
    return {"status": "stopped", "active": traffic.is_running}


@app.get("/api/traffic/status")
async def traffic_status():
    return {"active": traffic.is_running}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Initial push: send current snapshot and history
        init_payload = {
            "type": "init",
            "history": collector.get_history(),
            "traffic_active": traffic.is_running,
        }
        await websocket.send_json(init_payload)

        while True:
            await asyncio.sleep(1.0)
            data = collector.collect()
            payload = {
                "type": "tick",
                "data": data,
                "traffic_active": traffic.is_running,
            }
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.on_event("shutdown")
def shutdown_event():
    traffic.stop()
    collector.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)

