"""
swingdoor_web.py - Webserver zum Anlegen von Tags.

Erwartet im selben Ordner (~/fb_swingdoor):
  - swingdoor_sr.py
  - freibad.jpg
  - rfid_reader.py
  - templates/index.html

Start:  python3 swingdoor_web.py   ->  http://<rechner>:8080
"""
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from rfid_reader import (
    ReadCancelled,
    ReaderBusy,
    ReaderError,
    ReadTimeout,
    cancel_read,
    read_tag_id,
)
from swingdoor_sr import TAG_TYPES, TagError, add_tag

BASE_DIR = Path(__file__).resolve().parent
HOST = "0.0.0.0"
PORT = 8080

# Flask sucht HTML-Dateien im Ordner "templates" neben diesem Script
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))


@app.get("/")
def index():
  return render_template("index.html", types=TAG_TYPES)

@app.get("/freibad.jpg")
def background():
    return send_from_directory(BASE_DIR, "freibad.jpg")


@app.post("/api/tags")
def create_tag():
    try:
        add_tag(
            request.form.get("tagID", ""),
            request.form.get("pin", ""),
            request.form.get("type", ""),
            request.form.get("zaehler", ""),
            request.form.get("besitzer", ""),
            request.form.get("ausgabedatum", ""),
        )
    except TagError as e:
        return jsonify(message=str(e)), 400
    except Exception as e:  # z.B. DB fehlt oder Tabelle nicht vorhanden
        app.logger.exception("Fehler beim Eintragen")
        return jsonify(message=f"Datenbankfehler: {e}"), 500
    return jsonify(message="Tag gespeichert.")


@app.post("/api/read_tag")
def read_tag():
    """Wartet, bis ein Tag an den PN532 gehalten wird, und liefert dessen ID."""
    try:
        return jsonify(tagID=read_tag_id())
    except ReadTimeout:
        return jsonify(message="Kein Tag erkannt. Bitte erneut versuchen."), 408
    except ReadCancelled:
        return jsonify(message="Einlesen abgebrochen."), 409
    except ReaderBusy as e:
        return jsonify(message=str(e)), 409
    except ReaderError as e:
        app.logger.exception("RFID-Fehler")
        return jsonify(message=str(e)), 500


@app.post("/api/read_tag/cancel")
def read_tag_cancel():
    cancel_read()
    return jsonify(message="ok")


if __name__ == "__main__":
    # threaded=True: während auf einen Tag gewartet wird, bleibt der Server erreichbar
    app.run(host=HOST, port=PORT, threaded=True)
