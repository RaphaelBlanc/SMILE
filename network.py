# network.py
import asyncio
import websockets
import json
import threading

RELAY_URL = "https://smile-relay.onrender.com"  # ton URL de relay

class Network:
    def __init__(self):
        self.ws = None
        self.role = None          # "host" ou "client"
        self.session_code = None
        self.incoming = []        # messages reçus, lus par le jeu
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ── Connexion ─────────────────────────────────────────────────
    def connect(self):
        future = asyncio.run_coroutine_threadsafe(self._connect(), self._loop)
        future.result(timeout=5)

    async def _connect(self):
        self.ws = await websockets.connect(RELAY_URL)
        asyncio.ensure_future(self._listen())

    async def _listen(self):
        async for raw in self.ws:
            self.incoming.append(json.loads(raw))

    # ── Actions ───────────────────────────────────────────────────
    def create_session(self):
        self._send({"action": "create"})
        self.role = "host"

    def join_session(self, code):
        self._send({"action": "join", "code": code})
        self.role = "client"

    def send_game_state(self, state: dict):
        """Appelé par le host ~20x/s avec l'état sérialisé."""
        self._send({"action": "game_state", **state})

    def send_input(self, keys: list):
        """Appelé par le client à chaque frame avec les touches pressées."""
        self._send({"action": "input", "keys": keys})

    def poll(self):
        """Retourne et vide la liste des messages reçus."""
        msgs, self.incoming = self.incoming[:], []
        return msgs

    def _send(self, data: dict):
        if self.ws:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(data)), self._loop
            )