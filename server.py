# ==========================================
# MY SCHOOL LIFE: SDN KUNINGAN 03
# Unified HTTP & WebSocket Multiplayer Server
# ==========================================

import asyncio
import http.server
import json
import logging
import os
import socket
import sys
import threading
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HTTP_PORT = 8080
WS_PORT = 8081

# Connected WebSocket clients: { websocket: player_dict }
CONNECTED_PLAYERS = {}

def get_local_ip():
    """Detect local LAN IP for mobile phone connection over Wi-Fi"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# 1. HTTP Static Web Server
class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and caching headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        # Keep logs clean
        pass

def start_http_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server_address = ('0.0.0.0', HTTP_PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, QuietHTTPRequestHandler)
    logging.info(f"HTTP Web Server running at http://localhost:{HTTP_PORT}/")
    httpd.serve_forever()

# 2. WebSocket Real-Time Multiplayer Server
async def broadcast(message, sender_ws=None):
    """Send message to all connected players (except sender if specified)"""
    if not CONNECTED_PLAYERS:
        return
    
    msg_str = json.dumps(message)
    dead_sockets = []
    
    for ws in list(CONNECTED_PLAYERS.keys()):
        if sender_ws and ws == sender_ws:
            continue
        try:
            await ws.send(msg_str)
        except Exception:
            dead_sockets.append(ws)
            
    for ws in dead_sockets:
        if ws in CONNECTED_PLAYERS:
            del CONNECTED_PLAYERS[ws]

async def ws_handler(websocket):
    player_id = None
    try:
        async for raw_message in websocket:
            try:
                data = json.loads(raw_message)
            except Exception:
                continue

            msg_type = data.get("type")

            # A. Player Joined
            if msg_type == "join":
                player_id = data.get("id")
                player_info = {
                    "id": player_id,
                    "name": data.get("name", "Murid"),
                    "gender": data.get("gender", "boy"),
                    "pos": data.get("pos", {"x": 0, "y": 0, "z": 44}),
                    "rotY": data.get("rotY", 0),
                    "isMoving": False
                }
                CONNECTED_PLAYERS[websocket] = player_info
                logging.info(f"Pemain bergabung: {player_info['name']} (ID: {player_id}) | Total: {len(CONNECTED_PLAYERS)}")

                # 1. Send existing players to new player
                existing_list = [p for ws, p in CONNECTED_PLAYERS.items() if ws != websocket]
                await websocket.send(json.dumps({
                    "type": "welcome",
                    "yourId": player_id,
                    "players": existing_list
                }))

                # 2. Notify other players about new player
                await broadcast({
                    "type": "player_joined",
                    "player": player_info
                }, sender_ws=websocket)

            # B. Player Position / Movement Update
            elif msg_type == "update":
                if websocket in CONNECTED_PLAYERS:
                    p = CONNECTED_PLAYERS[websocket]
                    p["pos"] = data.get("pos", p["pos"])
                    p["rotY"] = data.get("rotY", p["rotY"])
                    p["isMoving"] = data.get("isMoving", False)
                    p["isRunning"] = data.get("isRunning", False)
                    p["isGrounded"] = data.get("isGrounded", True)

                    # Forward update to other players
                    await broadcast({
                        "type": "player_moved",
                        "id": player_id,
                        "pos": p["pos"],
                        "rotY": p["rotY"],
                        "isMoving": p["isMoving"],
                        "isRunning": p["isRunning"],
                        "isGrounded": p["isGrounded"]
                    }, sender_ws=websocket)

            # C. Chat / Greeting Emote
            elif msg_type == "chat":
                await broadcast({
                    "type": "chat_message",
                    "id": player_id,
                    "name": data.get("name", "Murid"),
                    "text": data.get("text", "")
                })

            # D. Soccer Ball Kick Sync
            elif msg_type == "kick_ball":
                await broadcast({
                    "type": "sync_ball",
                    "pos": data.get("pos"),
                    "vel": data.get("vel")
                }, sender_ws=websocket)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Player Disconnected
        if websocket in CONNECTED_PLAYERS:
            leaving_player = CONNECTED_PLAYERS.pop(websocket)
            logging.info(f"Pemain keluar: {leaving_player['name']} (ID: {player_id}) | Tersisa: {len(CONNECTED_PLAYERS)}")
            await broadcast({
                "type": "player_left",
                "id": player_id
            })

async def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    local_ip = get_local_ip()

    print("=" * 60)
    print("MY SCHOOL LIFE: SDN KUNINGAN 03 - MULTIPLAYER SERVER")
    print("=" * 60)
    print(f"Main di PC/Laptop ini : http://localhost:{HTTP_PORT}/")
    print(f"Mabar via HP (Wi-Fi) : http://{local_ip}:{HTTP_PORT}/")
    print(f"WebSocket Port       : ws://{local_ip}:{WS_PORT}")
    print("=" * 60)

    # Run HTTP Server in background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Run WebSocket Server on 0.0.0.0:8081
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
