# network.py
import asyncio
import websockets
import json
import threading

RELAY_URL = "wss://smile-relay.onrender.com"

class Network:
    def __init__(self):
        self.ws           = None
        self.role         = None
        self.session_code = None
        self.peer_joined  = False
        self.connected    = False
        self.error        = None
        self.incoming     = []
        self._loop        = asyncio.new_event_loop()
        self._thread      = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def connect(self):
        # On lance la connexion en arrière-plan sans bloquer Pygame
        asyncio.run_coroutine_threadsafe(self._connect(), self._loop)

    async def _wait_and_send(self, data: dict):
        # Attend jusqu'à 45 secondes (450 * 0.1s)
        timeout = 450
        while not self.connected and timeout > 0:
            if self.error:
                return
            await asyncio.sleep(0.1)
            timeout -= 1
        
        if self.connected and self.ws:
            await self.ws.send(json.dumps(data))
        else:
            if not self.error:
                self.error = "Timeout : Impossible de joindre le serveur."

    async def _connect(self):
        try:
            self.ws        = await websockets.connect(RELAY_URL)
            self.connected = True
            asyncio.ensure_future(self._listen())
        except Exception as e:
            self.error = str(e)

    async def _listen(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                print(f"[NET] recu : {msg}")   # DEBUG — retire apres tests
                action = msg.get("action")

                if action == "created":
                    # HOST : le serveur confirme la creation et donne le code
                    self.session_code = msg.get("code")

                elif action == "client_joined":
                    # HOST : un client vient de rejoindre
                    self.peer_joined = True

                elif action == "joined":
                    # CLIENT : le serveur confirme que le code etait valide
                    self.peer_joined = True

                elif action == "error":
                    self.error = msg.get("msg", "Erreur inconnue")

                else:
                    self.incoming.append(msg)

        except Exception as e:
            self.error     = str(e)
            self.connected = False

    def create_session(self):
        self.role = "host"
        asyncio.run_coroutine_threadsafe(self._wait_and_send({"action": "create"}), self._loop)

    def join_session(self, code: str):
        self.role = "client"
        asyncio.run_coroutine_threadsafe(self._wait_and_send({"action": "join", "code": code.strip().upper()}), self._loop)

    def send_game_state(self, state: dict):
        self._send({"action": "game_state", **state})

    def send_client_state(self, state: dict):
        self._send({"action": "client_state", **state})

    def poll(self) -> list:
        msgs, self.incoming = self.incoming[:], []
        return msgs

    def _send(self, data: dict):
        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(data)), self._loop
            )
