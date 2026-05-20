# network.py
import asyncio
import websockets
import json
import threading

# ⚠️  L'URL doit être en ws:// (WebSocket), pas https://
# Remplace par ton URL Render exacte si elle diffère.
RELAY_URL = "wss://smile-relay.onrender.com"

class Network:
    def __init__(self):
        self.ws           = None
        self.role         = None          # "host" ou "client"
        self.session_code = None          # code reçu du serveur après "create"
        self.peer_joined  = False         # True quand le 2e joueur a rejoint (host)
        self.connected    = False         # True dès que la WS est ouverte
        self.error        = None          # dernier message d'erreur réseau
        self.incoming     = []            # messages reçus, lus par le jeu
        self._loop        = asyncio.new_event_loop()
        self._thread      = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ── Connexion ─────────────────────────────────────────────────

    def connect(self):
        """Ouvre la connexion WebSocket (bloquant, timeout 5 s)."""
        future = asyncio.run_coroutine_threadsafe(self._connect(), self._loop)
        try:
            future.result(timeout=5)
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
        """Boucle de réception — tourne en arrière-plan."""
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                # Le serveur envoie {"action":"session_created","code":"XXXX"}
                if msg.get("action") == "created":
                    self.session_code = msg.get("code")
                # Le serveur envoie {"action":"client_joined"} au host quand le client arrive
                elif msg.get("action") == "joined":
                    # Confirmation que le code était valide, on attend le game_state du host
                    self.peer_joined = True   # réutilise le flag pour signaler "prêt"
                elif msg.get("action") == "error":
                    self.error = msg.get("msg", "Erreur inconnue")
                else:
                    self.incoming.append(msg)
        except Exception as e:
            self.error     = str(e)
            self.connected = False

    # ── Actions ───────────────────────────────────────────────────

    def create_session(self):
        """Host : demande la création d'une session et attend le code."""
        self.role = "host"
        self._send({"action": "create"})

    def join_session(self, code: str):
        """Client : rejoint une session avec le code fourni."""
        self.role = "client"
        self._send({"action": "join", "code": code.strip().upper()})

    def send_game_state(self, state: dict):
        """Appelé par le host ~20×/s avec l'état sérialisé du jeu."""
        self._send({"action": "game_state", **state})

    def send_input(self, keys: list):
        """Appelé par le client à chaque frame avec les touches pressées."""
        self._send({"action": "input", "keys": keys})

    def poll(self) -> list:
        """Retourne et vide la liste des messages reçus."""
        msgs, self.incoming = self.incoming[:], []
        return msgs

    def _send(self, data: dict):
        if self.ws and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(data)), self._loop
            )
