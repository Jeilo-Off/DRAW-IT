
import asyncio
import json
import threading
import queue
import os
import tkinter as tk
from tkinter import messagebox
import websockets

DEFAULT_SERVER = "wss://draw-it-server-bs9j.onrender.com"

BG = "#21151e"
PANEL = "#35232e"
PINK = "#ff3988"
PURPLE = "#a35bff"
WHITE = "#fff4ed"


class DrawItApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DRAW IT!")
        self.root.geometry("1150x750")
        self.root.minsize(950, 650)
        self.root.configure(bg=BG)

        self.events = queue.Queue()
        self.ws = None
        self.loop = None
        self.connected = False
        self.server_url = DEFAULT_SERVER

        self.room_code = None
        self.player_id = None
        self.player_name = "Player"
        self.players = []
        self.points = {}

        self.is_artist = False
        self.can_draw = False
        self.revealed = False
        self.strokes = []
        self.last_xy = None
        self.current_color = "#24243a"
        self.brush_size = 5

        self.avatar_shirt = "#2878e8"
        self.avatar_hair = "#38243a"
        self.avatar_hat = False

        self.build_home()
        self.root.after(50, self.process_events)

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def button(self, parent, text, command, color=PURPLE):
        return tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white", activebackground=PINK,
            activeforeground="white", relief="flat",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2", padx=15, pady=10
        )

    def heading(self, parent, text, size=24):
        return tk.Label(
            parent, text=text, bg=parent["bg"], fg=WHITE,
            font=("Segoe UI", size, "bold")
        )

    # ---------------- HOME ----------------

    def build_home(self):
        self.clear()
        self.screen = "home"

        top = tk.Frame(self.root, bg="#171019", height=65)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(
            top, text="DRAW IT!",
            bg="#171019", fg=PINK,
            font=("Segoe UI", 23, "bold")
        ).pack(side="left", padx=25)

        tk.Label(
            top, text="PARTY GAME",
            bg="#171019", fg="#c5aaba",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.button(top, "⚙ PARAMÈTRES",
                    self.settings_window, "#493342").pack(
            side="right", padx=20, pady=10
        )

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=35, pady=25)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        left = tk.Frame(main, bg=PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.heading(left, "TON PERSONNAGE", 19).pack(pady=20)

        self.avatar_canvas = tk.Canvas(
            left, width=350, height=330,
            bg="#49313c", highlightthickness=0
        )
        self.avatar_canvas.pack(padx=15, pady=10)
        self.draw_avatar()

        tk.Label(
            left, text="COULEUR DU T-SHIRT",
            bg=PANEL, fg=WHITE
        ).pack()

        colors = tk.Frame(left, bg=PANEL)
        colors.pack(pady=8)

        for color in ["#2878e8", "#ef476f", "#21a179",
                      "#f4a261", "#a35bff", "#f2f2f2"]:
            tk.Button(
                colors, bg=color, width=3, relief="flat",
                command=lambda c=color: self.change_shirt(c)
            ).pack(side="left", padx=4)

        right = tk.Frame(main, bg=PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self.heading(right, "PRÊT À JOUER ?", 24).pack(pady=(55, 10))

        tk.Label(
            right,
            text="Crée un salon privé et invite tes amis !",
            bg=PANEL, fg="#c5aaba",
            font=("Segoe UI", 11)
        ).pack(pady=10)

        tk.Label(
            right, text="TON PSEUDO",
            bg=PANEL, fg=WHITE
        ).pack(anchor="w", padx=35, pady=(35, 5))

        self.name_entry = tk.Entry(
            right, font=("Segoe UI", 14),
            bg="#49313c", fg="white",
            insertbackground="white", relief="flat"
        )
        self.name_entry.insert(0, "Player")
        self.name_entry.pack(fill="x", padx=35, ipady=10)

        self.button(
            right, "▶ CRÉER UN LOBBY",
            self.create_lobby
        ).pack(fill="x", padx=35, pady=(35, 12))

        tk.Label(
            right, text="OU REJOINDRE UN AMI",
            bg=PANEL, fg=WHITE
        ).pack(pady=(20, 8))

        self.join_entry = tk.Entry(
            right, font=("Segoe UI", 14),
            bg="#49313c", fg="white",
            insertbackground="white", relief="flat",
            justify="center"
        )
        self.join_entry.insert(0, "CODE")
        self.join_entry.pack(fill="x", padx=35, ipady=10)

        self.button(
            right, "REJOINDRE",
            self.join_lobby, "#493342"
        ).pack(fill="x", padx=35, pady=12)

        tk.Label(
            right, text="Jusqu'à 5 joueurs • 3, 5 ou 10 manches",
            bg=PANEL, fg="#b69baa"
        ).pack(pady=20)

    def draw_avatar(self):
        if not hasattr(self, "avatar_canvas"):
            return

        c = self.avatar_canvas
        c.delete("all")

        c.create_oval(75, 15, 275, 215, fill="#634454", outline="")
        c.create_polygon(
            100, 310, 115, 205, 235, 205, 250, 310,
            fill=self.avatar_shirt, outline=""
        )
        c.create_rectangle(
            155, 175, 195, 220, fill="#e9b895", outline=""
        )
        c.create_oval(
            115, 70, 235, 190, fill="#e9b895", outline=""
        )
        c.create_arc(
            112, 58, 238, 145, start=0, extent=180,
            fill=self.avatar_hair, outline=self.avatar_hair
        )
        c.create_oval(145, 125, 155, 137, fill="#241820")
        c.create_oval(195, 125, 205, 137, fill="#241820")
        c.create_arc(
            160, 140, 190, 165, start=200, extent=140,
            style=tk.ARC, outline="#9b514f", width=3
        )
        c.create_line(
            110, 220, 80, 280,
            fill="#e9b895", width=18, capstyle=tk.ROUND
        )
        c.create_line(
            240, 220, 270, 280,
            fill="#e9b895", width=18, capstyle=tk.ROUND
        )

    def change_shirt(self, color):
        self.avatar_shirt = color
        self.draw_avatar()

    # ---------------- SETTINGS ----------------

    def settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("Paramètres")
        win.geometry("430x390")
        win.configure(bg=BG)
        win.resizable(False, False)

        self.heading(win, "⚙ PARAMÈTRES", 21).pack(pady=20)

        try:
            import sounddevice as sd
            devices = sd.query_devices()
            inputs = [
                f"{i} - {d['name']}"
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
            outputs = [
                f"{i} - {d['name']}"
                for i, d in enumerate(devices)
                if d["max_output_channels"] > 0
            ]
        except Exception:
            inputs = ["Périphériques indisponibles"]
            outputs = ["Périphériques indisponibles"]

        tk.Label(
            win, text="MICROPHONE (ENTRÉE)",
            bg=BG, fg=WHITE
        ).pack(anchor="w", padx=25, pady=(15, 5))

        self.input_device = tk.StringVar(
            value=inputs[0] if inputs else ""
        )
        tk.OptionMenu(
            win, self.input_device, *inputs
        ).pack(fill="x", padx=25)

        tk.Label(
            win, text="CASQUE / HAUT-PARLEURS (SORTIE)",
            bg=BG, fg=WHITE
        ).pack(anchor="w", padx=25, pady=(20, 5))

        self.output_device = tk.StringVar(
            value=outputs[0] if outputs else ""
        )
        tk.OptionMenu(
            win, self.output_device, *outputs
        ).pack(fill="x", padx=25)

        tk.Label(
            win,
            text="La sélection des appareils est disponible.\n"
                 "Le chat vocal en ligne sera ajouté séparément.",
            bg=BG, fg="#c5aaba",
            justify="center"
        ).pack(pady=25)

        self.button(win, "FERMER", win.destroy).pack(pady=5)

    # ---------------- CONNECTION ----------------

    def connect(self, action, code=None):
        self.player_name = self.name_entry.get().strip()[:16] or "Player"

        if self.connected:
            messagebox.showinfo("Connexion", "Tu es déjà connecté.")
            return

        threading.Thread(
            target=self.network_thread,
            args=(action, code),
            daemon=True
        ).start()

    def create_lobby(self):
        self.connect("create")

    def join_lobby(self):
        code = self.join_entry.get().strip().upper()
        if not code or code == "CODE":
            messagebox.showinfo("Code", "Entre le code de ton ami.")
            return
        self.connect("join", code)

    def network_thread(self, action, code):
        async def runner():
            try:
                self.loop = asyncio.get_running_loop()
                async with websockets.connect(
                    self.server_url, max_size=2**20
                ) as ws:
                    self.ws = ws
                    await ws.send(json.dumps({
                        "type": action,
                        "name": self.player_name,
                        "code": code
                    }))
                    self.events.put({"type": "_connected"})
                    async for raw in ws:
                        self.events.put(json.loads(raw))
            except Exception as e:
                self.events.put({
                    "type": "_error",
                    "message": str(e)
                })

        asyncio.run(runner())

    def send(self, payload):
        if self.ws and self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(payload)),
                self.loop
            )

    # ---------------- EVENTS ----------------

    def process_events(self):
        try:
            while True:
                msg = self.events.get_nowait()
                self.handle_message(msg)
        except queue.Empty:
            pass

        self.root.after(50, self.process_events)

    def handle_message(self, msg):
        typ = msg.get("type")

        if typ == "_connected":
            self.connected = True

        elif typ in ("_error", "error"):
            self.connected = False
            messagebox.showerror(
                "Connexion impossible",
                msg.get("message", "Erreur inconnue")
            )

        elif typ == "lobby":
            self.room_code = msg["code"]
            self.player_id = msg["you"]
            self.points = msg.get("scores", {})
            self.build_lobby(msg)

        elif typ == "lobby_update":
            self.players = msg.get("players", [])
            if self.screen == "lobby":
                self.render_lobby_players()

        elif typ in ("round", "game_started"):
            self.start_round_view(msg)

        elif typ == "drawing":
            if not self.is_artist:
                self.draw_remote(msg.get("strokes", []))

        elif typ == "revealed":
            self.revealed = True
            self.can_draw = False
            self.draw_remote(msg.get("strokes", []))
            self.status_label.config(
                text=f"🎨 {msg.get('artist_name')} a montré son dessin !"
            )

        elif typ in ("chat", "guess_result"):
            self.chat_insert(msg.get("text", ""))
            if msg.get("correct"):
                self.refresh_scores(msg.get("scores", {}))

        elif typ == "round_end":
            self.can_draw = False
            self.status_label.config(
                text="Manche terminée ! " + msg.get("answer", "")
            )
            self.refresh_scores(msg.get("scores", {}))

        elif typ == "game_over":
            self.can_draw = False
            messagebox.showinfo(
                "Partie terminée",
                f"🏆 Gagnant : {msg.get('winner', 'Personne')}"
            )
            self.build_lobby({
                "code": self.room_code,
                "players": msg.get("players", []),
                "you": self.player_id,
                "scores": msg.get("scores", {})
            })

    # ---------------- LOBBY ----------------

    def build_lobby(self, msg):
        self.clear()
        self.screen = "lobby"
        self.players = msg.get("players", [])

        top = tk.Frame(self.root, bg="#171019", height=65)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(
            top, text="DRAW IT!",
            bg="#171019", fg=PINK,
            font=("Segoe UI", 22, "bold")
        ).pack(side="left", padx=25)

        self.button(
            top, "⚙ PARAMÈTRES",
            self.settings_window, "#493342"
        ).pack(side="right", padx=20, pady=10)

        self.stage = tk.Canvas(
            self.root, bg="#593b37",
            highlightthickness=0
        )
        self.stage.pack(fill="both", expand=True, padx=20, pady=15)

        self.stage.bind("<Configure>", lambda e: self.draw_stage())

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill="x", padx=25, pady=10)

        tk.Label(
            bottom,
            text=f"CODE DU LOBBY : {self.room_code}",
            bg=BG, fg=PINK,
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")

        settings = tk.Frame(bottom, bg=BG)
        settings.pack(side="right")

        tk.Label(
            settings, text="MANCHES",
            bg=BG, fg=WHITE
        ).pack(side="left", padx=5)

        self.round_var = tk.IntVar(value=3)
        tk.OptionMenu(
            settings, self.round_var, 3, 5, 10
        ).pack(side="left", padx=5)

        self.button(
            settings, "LANCER LA PARTIE",
            self.start_game
        ).pack(side="left", padx=10)

        self.render_lobby_players()
        self.draw_stage()

    def render_lobby_players(self):
        self.draw_stage()

    def draw_stage(self):
        if not hasattr(self, "stage"):
            return

        c = self.stage
        c.delete("all")

        w = max(c.winfo_width(), 700)
        h = max(c.winfo_height(), 350)

        c.create_rectangle(0, 0, w, h, fill="#563a3b", outline="")
        c.create_rectangle(
            0, h * .70, w, h,
            fill="#75452e", outline=""
        )

        # Plancher
        for x in range(0, w, 70):
            c.create_line(
                x, h * .70, x - 25, h,
                fill="#593623", width=2
            )

        # Logo
        c.create_text(
            w / 2, h * .18,
            text="DRAW IT!",
            fill="#ffc83d",
            font=("Segoe UI", 35, "bold")
        )
        c.create_text(
            w / 2, h * .27,
            text="PARTY STAGE",
            fill=PINK,
            font=("Segoe UI", 16, "bold")
        )

        # Enceintes
        for x in (55, w - 105):
            c.create_rectangle(
                x, h * .38, x + 55, h * .72,
                fill="#25263d", outline="#a9a4c7", width=3
            )
            c.create_oval(
                x + 9, h * .43, x + 46, h * .53,
                fill="#615d88"
            )
            c.create_oval(
                x + 9, h * .56, x + 46, h * .66,
                fill="#615d88"
            )

        players = self.players or [
            {"name": self.player_name, "id": self.player_id}
        ]

        count = min(len(players), 5)
        for i, player in enumerate(players[:5]):
            x = w * (i + 1) / (count + 1)
            y = h * .52

            shirt = [
                "#ef476f", "#2878e8", "#f4a261",
                "#21a179", "#a35bff"
            ][i % 5]

            c.create_oval(
                x - 24, y - 45, x + 24, y + 3,
                fill="#e8b38d", outline=""
            )
            c.create_arc(
                x - 25, y - 52, x + 25, y - 10,
                start=0, extent=180,
                fill="#38243a", outline=""
            )
            c.create_polygon(
                x - 30, y + 5, x + 30, y + 5,
                x + 40, y + 75, x - 40, y + 75,
                fill=shirt, outline=""
            )
            c.create_line(
                x - 23, y + 20, x - 38, y + 60,
                fill="#e8b38d", width=10
            )
            c.create_line(
                x + 23, y + 20, x + 38, y + 60,
                fill="#e8b38d", width=10
            )
            c.create_text(
                x, y - 65,
                text=player.get("name", "Player"),
                fill="white",
                font=("Segoe UI", 11, "bold")
            )

        c.create_text(
            w / 2, h - 18,
            text=f"{len(players)}/5 JOUEURS",
            fill="#ffe8d9",
            font=("Segoe UI", 10, "bold")
        )

    def start_game(self):
        self.send({
            "type": "start",
            "rounds": self.round_var.get()
        })

    # ---------------- GAME ----------------

    def start_round_view(self, msg):
        self.clear()
        self.screen = "game"
        self.is_artist = msg.get("artist") == self.player_id
        self.can_draw = self.is_artist
        self.revealed = False
        self.strokes = []

        self.heading(
            self.root,
            f"DRAW IT! • MANCHE {msg.get('round', 1)}/{msg.get('total', 3)}",
            22
        ).pack(pady=10)

        self.status_label = tk.Label(
            self.root, text=msg.get("status", ""),
            bg=BG, fg=PINK,
            font=("Segoe UI", 12, "bold")
        )
        self.status_label.pack()

        self.prompt_label = tk.Label(
            self.root,
            text=("TON MOT : " + msg.get("word", ""))
            if self.is_artist else "Un joueur dessine...",
            bg=BG, fg=WHITE,
            font=("Segoe UI", 18, "bold")
        )
        self.prompt_label.pack(pady=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=8)

        self.canvas = tk.Canvas(
            body, bg="white",
            highlightthickness=0
        )
        self.canvas.pack(
            side="left", fill="both",
            expand=True, padx=(0, 15)
        )

        side = tk.Frame(body, bg=PANEL, width=270, padx=12, pady=12)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        tk.Label(
            side, text="SCORES",
            bg=PANEL, fg=WHITE
        ).pack(anchor="w")

        self.score_label = tk.Label(
            side, text="", bg=PANEL,
            fg=WHITE, justify="left"
        )
        self.score_label.pack(anchor="w", pady=8)

        tk.Label(
            side, text="CHAT",
            bg=PANEL, fg=PINK
        ).pack(anchor="w", pady=(10, 5))

        self.chat = tk.Text(
            side, height=12, bg="#171019",
            fg=WHITE, relief="flat",
            font=("Segoe UI", 9),
            state="disabled"
        )
        self.chat.pack(fill="both", expand=True)

        self.chat_entry = tk.Entry(
            side, bg="#49313c", fg="white",
            insertbackground="white", relief="flat"
        )
        self.chat_entry.pack(fill="x", pady=7, ipady=7)
        self.chat_entry.bind(
            "<Return>", lambda e: self.send_chat()
        )

        self.button(
            side, "ENVOYER MESSAGE",
            self.send_chat, "#493342"
        ).pack(fill="x")

        self.guess_entry = tk.Entry(
            side, bg="#49313c", fg="white",
            insertbackground="white", relief="flat"
        )
        self.guess_entry.pack(fill="x", pady=(15, 5), ipady=7)

        self.button(
            side, "DEVINER",
            self.submit_guess
        ).pack(fill="x")

        tools = tk.Frame(self.root, bg=BG)
        tools.pack(fill="x", padx=20, pady=12)

        for name, color in [
            ("NOIR", "#24243a"),
            ("ROUGE", "#ef476f"),
            ("BLEU", "#2878e8"),
            ("VERT", "#21a179"),
            ("GOMME", "white")
        ]:
            self.button(
                tools, name,
                lambda c=color: self.set_color(c),
                "#493342"
            ).pack(side="left", padx=3)

        self.button(
            tools, "EFFACER",
            self.clear_canvas, "#493342"
        ).pack(side="left", padx=8)

        self.show_btn = self.button(
            tools, "MONTRER LE DESSIN",
            self.reveal_drawing
        )
        self.show_btn.pack(side="right")

        if not self.is_artist:
            self.show_btn.config(state="disabled")
        else:
            self.canvas.bind("<Button-1>", self.begin_draw)
            self.canvas.bind("<B1-Motion>", self.paint)

        self.refresh_scores(msg.get("scores", {}))

    def set_color(self, color):
        self.current_color = color

    def begin_draw(self, event):
        self.last_xy = (event.x, event.y)

    def paint(self, event):
        if not self.can_draw or self.revealed:
            return

        x, y = event.x, event.y
        if self.last_xy:
            x0, y0 = self.last_xy
            self.canvas.create_line(
                x0, y0, x, y,
                fill=self.current_color,
                width=self.brush_size,
                capstyle=tk.ROUND,
                smooth=True
            )
            stroke = {
                "x0": x0, "y0": y0,
                "x1": x, "y1": y,
                "color": self.current_color,
                "width": self.brush_size
            }
            self.strokes.append(stroke)
            self.send({"type": "stroke", "stroke": stroke})

        self.last_xy = (x, y)

    def clear_canvas(self):
        if self.is_artist and not self.revealed:
            self.canvas.delete("all")
            self.strokes = []
            self.send({"type": "clear"})

    def reveal_drawing(self):
        if self.is_artist and not self.revealed:
            self.send({"type": "reveal"})
            self.revealed = True
            self.can_draw = False
            self.show_btn.config(state="disabled")
            self.status_label.config(
                text="Dessin révélé ! À vous de deviner !"
            )

    def draw_remote(self, strokes):
        self.canvas.delete("all")
        for s in strokes:
            self.canvas.create_line(
                s["x0"], s["y0"], s["x1"], s["y1"],
                fill=s["color"], width=s["width"],
                capstyle=tk.ROUND, smooth=True
            )

    def submit_guess(self):
        guess = self.guess_entry.get().strip()
        if guess:
            self.send({"type": "guess", "text": guess})
            self.guess_entry.delete(0, "end")

    def send_chat(self):
        text = self.chat_entry.get().strip()
        if text:
            self.send({"type": "chat_message", "text": text})
            self.chat_entry.delete(0, "end")

    def chat_insert(self, text):
        if hasattr(self, "chat"):
            self.chat.config(state="normal")
            self.chat.insert("end", text + "\n")
            self.chat.see("end")
            self.chat.config(state="disabled")

    def refresh_scores(self, scores):
        self.points = scores
        if hasattr(self, "score_label"):
            lines = [
                f"{name} : {score} pts"
                for name, score in scores.items()
            ]
            self.score_label.config(
                text="\n".join(lines) if lines else "Aucun score"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = DrawItApp(root)
    root.mainloop()
