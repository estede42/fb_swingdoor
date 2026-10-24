"""
swingdoor_web.py - Webserver zum Anlegen von Tags.

Erwartet im selben Ordner (~/fb_swingdoor):
  - swingdoor_sr.py
  - freibad.jpg
  - rfid_reader.py
  - templates/index.html
  - libs/ (jQuery, DataTables)

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
from swingdoor_sr import TAG_TYPES, TagError, add_tag, delete_tag, get_tags, update_tag

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


@app.get("/libs/<path:filename>")
def libs(filename):
    """Lokale Kopien von jQuery und DataTables (funktioniert auch ohne Internet)."""
    return send_from_directory(BASE_DIR / "libs", filename)


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


@app.get("/api/tags")
def list_tags():
    """Alle Tags für die DataTables-Tabelle (DataTables erwartet die Zeilen unter "data")."""
    try:
        return jsonify(data=get_tags())
    except Exception as e:
        app.logger.exception("Fehler beim Lesen")
        return jsonify(message=f"Datenbankfehler: {e}"), 500


@app.delete("/api/tags/<tag_id>")
def remove_tag(tag_id):
    try:
        delete_tag(tag_id)
    except TagError as e:
        return jsonify(message=str(e)), 404
    except Exception as e:
        app.logger.exception("Fehler beim Löschen")
        return jsonify(message=f"Datenbankfehler: {e}"), 500
    return jsonify(message=f"Tag '{tag_id}' gelöscht.")


@app.put("/api/tags/<tag_id>")
def edit_tag(tag_id):
    try:
        update_tag(
            tag_id,
            request.form.get("pin", ""),
            request.form.get("type", ""),
            request.form.get("zaehler", ""),
            request.form.get("besitzer", ""),
            request.form.get("ausgabedatum", ""),
            # Checkboxen werden nur mitgeschickt, wenn sie angehakt sind
            aktiv="aktiv" in request.form,
            geklaut="geklaut" in request.form,
        )
    except TagError as e:
        return jsonify(message=str(e)), 400
    except Exception as e:
        app.logger.exception("Fehler beim Ändern")
        return jsonify(message=f"Datenbankfehler: {e}"), 500
    return jsonify(message="Änderungen gespeichert.")


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
