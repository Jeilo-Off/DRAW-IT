
import asyncio
import json
import random
import secrets
import string
import unicodedata
import os
from http import HTTPStatus
import websockets

WORDS = [
    "cochon", "pomme", "fusée", "girafe", "pizza",
    "dragon", "vélo", "maison", "dinosaure", "banane",
    "requin", "chaussette", "robot", "château",
    "licorne", "parapluie", "tortue", "hamburger",
    "fantôme", "avion", "soleil", "ordinateur",
    "grenouille", "couronne", "glace", "citrouille",
]

rooms = {}


def clean_word(value):
    value = unicodedata.normalize("NFD", value.lower().strip())
    value = "".join(
        c for c in value
        if unicodedata.category(c) != "Mn"
    )
    return "".join(c for c in value if c.isalnum())


def new_code():
    alphabet = string.ascii_uppercase + "23456789"
    while True:
        code = "".join(
            secrets.choice(alphabet) for _ in range(6)
        )
        if code not in rooms:
            return code


async def send(ws, data):
    try:
        await ws.send(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


async def broadcast(room, data):
    await asyncio.gather(
        *(send(p["ws"], data)
          for p in list(room["players"].values()))
    )


def players_list(room):
    return [
        {"id": p["id"], "name": p["name"]}
        for p in room["players"].values()
    ]


def scores(room):
    return {
        p["name"]: p["score"]
        for p in room["players"].values()
    }


async def lobby_update(room):
    await broadcast(room, {
        "type": "lobby_update",
        "players": players_list(room)
    })


async def begin_round(room):
    if room["round"] >= room["rounds"]:
        ranking = sorted(
            room["players"].values(),
            key=lambda p: p["score"],
            reverse=True
        )
        winner = ranking[0]["name"] if ranking else "Personne"

        await broadcast(room, {
            "type": "game_over",
            "winner": winner,
            "scores": scores(room),
            "players": players_list(room)
        })
        room["playing"] = False
        return

    room["round"] += 1

    ids = list(room["players"].keys())
    eligible = [
        pid for pid in ids
        if pid != room.get("last_artist")
    ]
    if not eligible:
        eligible = ids

    artist_id = random.choice(eligible)
    room["last_artist"] = artist_id
    room["artist"] = artist_id
    room["word"] = random.choice(WORDS)
    room["strokes"] = []
    room["revealed"] = False
    room["guessed"] = set()
    room["round_ending"] = False

    for pid, player in room["players"].items():
        await send(player["ws"], {
            "type": "round",
            "round": room["round"],
            "total": room["rounds"],
            "artist": artist_id,
            "word": room["word"] if pid == artist_id else "",
            "status": (
                f"{room['players'][artist_id]['name']} dessine..."
            ),
            "scores": scores(room)
        })


async def reveal_timeout(room, round_number):
    # Le délai de réponse commence quand le dessin est révélé.
    await asyncio.sleep(60)
    if (
        room.get("playing")
        and room.get("round") == round_number
        and room.get("revealed")
    ):
        await finish_round(room, round_number)


async def finish_round(room, round_number=None):
    # Empêche deux événements (chrono + bonnes réponses) de finir
    # la même manche plusieurs fois.
    if (
        not room.get("playing")
        or room.get("round_ending", False)
        or (round_number is not None and room.get("round") != round_number)
    ):
        return

    room["round_ending"] = True
    finished_round = room["round"]

    await broadcast(room, {
        "type": "round_end",
        "answer": f"Le mot était : {room['word']}",
        "scores": scores(room)
    })

    await asyncio.sleep(4)

    if room.get("playing") and room.get("round") == finished_round:
        await begin_round(room)


async def handler(ws):
    player_id = secrets.token_hex(4)
    room_code = None

    try:
        first = json.loads(await ws.recv())
        action = first.get("type")
        name = (first.get("name") or "Player")[:16]

        if action == "create":
            room_code = new_code()
            rooms[room_code] = {
                "host": player_id,
                "players": {},
                "rounds": 3,
                "round": 0,
                "playing": False,
                "last_artist": None,
                "artist": None,
                "word": "",
                "strokes": [],
                "revealed": False,
                "guessed": set(),
                "round_ending": False
            }

        elif action == "join":
            room_code = (first.get("code") or "").upper()
            if room_code not in rooms:
                await send(ws, {
                    "type": "error",
                    "message": "Code de lobby introuvable."
                })
                return

        else:
            await send(ws, {
                "type": "error",
                "message": "Action inconnue."
            })
            return

        room = rooms[room_code]

        if room["playing"]:
            await send(ws, {
                "type": "error",
                "message": "Cette partie a déjà commencé."
            })
            return

        if len(room["players"]) >= 5:
            await send(ws, {
                "type": "error",
                "message": "Lobby complet (5 joueurs maximum)."
            })
            return

        room["players"][player_id] = {
            "id": player_id,
            "name": name,
            "ws": ws,
            "score": 0
        }

        await send(ws, {
            "type": "lobby",
            "code": room_code,
            "you": player_id,
            "players": players_list(room),
            "scores": scores(room)
        })

        await lobby_update(room)

        async for raw in ws:
            msg = json.loads(raw)
            typ = msg.get("type")

            if typ == "start" and player_id == room["host"] and not room["playing"]:
                if len(room["players"]) < 2:
                    await send(ws, {
                        "type": "chat",
                        "text": "Il faut au moins 2 joueurs."
                    })
                    continue

                room["rounds"] = int(msg.get("rounds", 3))
                if room["rounds"] not in (3, 5, 10):
                    room["rounds"] = 3

                room["round"] = 0
                room["playing"] = True

                for p in room["players"].values():
                    p["score"] = 0

                await begin_round(room)

            elif typ == "chat_message":
                text = str(msg.get("text", "")).strip()[:200]
                if text:
                    await broadcast(room, {
                        "type": "chat",
                        "text": f"{name} : {text}"
                    })

            elif typ == "stroke" and room.get("playing") and player_id == room.get("artist") and not room.get("revealed"):
                stroke = msg.get("stroke", {})
                room["strokes"].append(stroke)

            elif typ == "clear" and player_id == room.get("artist") and not room.get("revealed"):
                room["strokes"] = []

            elif typ == "reveal" and player_id == room.get("artist") and room.get("playing") and not room.get("revealed"):
                room["revealed"] = True

                await broadcast(room, {
                    "type": "revealed",
                    "artist_name": name,
                    "strokes": room["strokes"]
                })

                asyncio.create_task(reveal_timeout(room, room["round"]))

            elif typ == "guess" and room.get("playing") and room.get("revealed") and player_id != room.get("artist"):
                guess = str(msg.get("text", ""))[:40]
                player = room["players"][player_id]

                if player_id in room["guessed"]:
                    continue

                if clean_word(guess) == clean_word(room["word"]):
                    player["score"] += 10
                    room["guessed"].add(player_id)

                    await broadcast(room, {
                        "type": "guess_result",
                        "correct": True,
                        "text": (
                            f"🎉 {player['name']} a trouvé le mot ! +10 points"
                        ),
                        "scores": scores(room)
                    })

                    if len(room["guessed"]) >= len(room["players"]) - 1:
                        await finish_round(room, room["round"])

                else:
                    await send(ws, {
                        "type": "guess_result",
                        "correct": False,
                        "text": f"{name} : {guess}"
                    })

    except websockets.ConnectionClosed:
        pass

    except Exception as e:
        await send(ws, {
            "type": "error",
            "message": str(e)
        })

    finally:
        if room_code and room_code in rooms:
            room = rooms[room_code]
            room["players"].pop(player_id, None)

            if not room["players"]:
                rooms.pop(room_code, None)
            else:
                if room["host"] == player_id:
                    room["host"] = next(iter(room["players"]))

                await lobby_update(room)


async def health_check(path, request_headers):
    # Render utilise cette route HTTP pour vérifier que le service est actif.
    if path == "/health":
        return HTTPStatus.OK, [("Content-Type", "text/plain")], b"DRAW IT! OK"
    return None


async def main():
    port = int(os.environ.get("PORT", "8765"))
    print(f"DRAW IT! server started on port {port}")
    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        max_size=2**20,
        process_request=health_check
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
