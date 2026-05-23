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
        future = asyncio.run_coroutine_threadsafe(self._connect(), self._loop)
        try:
            # On augmente le timeout à 45s car le serveur gratuit Render met du temps à se réveiller
            future.result(timeout=45)
        except Exception as e:
            self.error = f"Connexion impossible : {e}"

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
        self._send({"action": "create"})

    def join_session(self, code: str):
        self.role = "client"
        self._send({"action": "join", "code": code.strip().upper()})

    def send_game_state(self, state: dict):
        self._send({"action": "game_state", **state})

    def send_input(self, keys: list):
        self._send({"action": "input", "keys": keys})

    def poll(self) -> list:
        msgs, self.incoming = self.incoming[:], []
        return msgs

    def _send(self, data: dict):
        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(data)), self._loop
            )
