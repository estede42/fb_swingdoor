"""
swingdoor_sr.py - Datenbankfunktionen für die Swingdoor.

Liegt in ~/fb_swingdoor und schreibt in ~/fb/swingdoor/db/swingdoor.db
"""
import re # RegEx-Modul
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

# Ordner, in dem dieses Script liegt (~/fb_swingdoor)
SCRIPT_DIR = Path(__file__).resolve().parent
# Datenbank relativ zum Script: ./sql/swingdoor.db
DB_PATH = SCRIPT_DIR / "sql" / "swingdoor.db"

# Kürzel (wird in der DB gespeichert) -> Anzeigename (wird im Formular angezeigt)
TAG_TYPES = {
    "10er": "10er Karte",
    "JK": "Jahreskarte",
    "FJK": "Familienjahreskarte",
}

_TAG_RE = re.compile(r"[A-Za-z0-9]+") #Erzeugt ein RegEx Objekt. das r am Anfang steht für raw und sorgt für dafür das z.B. \ keine Escape-Zeichen sind
_PIN_RE = re.compile(r"[0-9]{3,}") #RegEx Objekt, damit PIN nur aus Zahlen besteht und mind 3 ZTeichen lang ist
# Die UpperCase Schreibweise deutet übrigens darauf hin, das dieses RegEx-Objekt als Konstante netrachtet werden sol. Der _ hat die Bedeutung, dass die Variable nur intern innerhalb dieses Moduls genutzt werden solen. Quasi Private Variablen sind

class TagError(ValueError):
    """Ungültige Eingabe oder Tag bereits vorhanden."""


def add_tag(tag_id, pin, tag_type, zaehler=0, besitzer=None, ausgabedatum=None, db_path=DB_PATH):
    #Trägt einen Tag in die Tabelle 'tags' (Spalten tagID, pin, typ, zaehler, besitzer, ausgabedatum) ein."""
    tag_id = str(tag_id).strip() # strip Entfernt unnötige Leerzeichen    
    pin = str(pin).strip()
    tag_type = str(tag_type).strip()
    # Leere Eingaben bekommen ihre Initialwerte: zaehler 0, besitzer NULL, ausgabedatum heute
    zaehler = str(zaehler).strip() if zaehler is not None else ""
    besitzer = str(besitzer).strip() if besitzer is not None else ""
    besitzer = besitzer or None # leerer String -> NULL in der DB
    ausgabedatum = str(ausgabedatum).strip() if ausgabedatum is not None else ""
    #Überprüfung mit RegExObkekten, ob der String Syntaktisch richtig ist
    if not _TAG_RE.fullmatch(tag_id):
        raise TagError("Die Tag Nummer darf nur Buchstaben und Ziffern enthalten.") # mit dem RegEx-Objekt aus Zeile 15 ff 
    if not _PIN_RE.fullmatch(pin):
        raise TagError("Die PIN muss aus mindestens 3 Ziffern bestehen.")
    if tag_type not in TAG_TYPES:
        erlaubt = ", ".join(f"{k} ({v})" for k, v in TAG_TYPES.items())
        raise TagError(f"Ungültiger Typ. Erlaubt: {erlaubt}")
    try:
        zaehler = int(zaehler) if zaehler else 0
    except ValueError:
        raise TagError("Der Zähler muss eine ganze Zahl sein.")
    if zaehler < 0:
        raise TagError("Der Zähler darf nicht negativ sein.")
    try:
        # erwartet das Format JJJJ-MM-TT (so liefert es auch <input type="date">)
        ausgabedatum = date.fromisoformat(ausgabedatum) if ausgabedatum else date.today()
    except ValueError:
        raise TagError("Das Ausgabedatum muss im Format JJJJ-MM-TT sein.")

    #Die Variablen wurden vorbereitet. Jetzt müssen sie in die DB
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {db_path}")

    try:
        with closing(sqlite3.connect(db_path)) as conn, conn:
            #die sqlite Datenbank wird am Ende dieses with-Blocks auf jeden 
            #Fall geschlossen! Das Komma (, conn:) macht aus diesem einen with 
            #Block zwei verschachtelte. Es verhält sich hier also wie with
            #swl { with conn { } }
            conn.execute( #execute kümmert sich un die Transaktion. Bei Fehlerfreiem durchlauf wird das sql comittet. Sonst Rollback aufgerufen. Jedoch wird die DB danach nicht geschlossen. Darum kümmert sich ja aber das closing im ersten with
                "INSERT INTO tags (tagID, pin, typ, zaehler, besitzer, ausgabedatum)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (tag_id, pin, tag_type, zaehler, besitzer, ausgabedatum.isoformat()),
            )
    except sqlite3.IntegrityError:
        raise TagError(f"Der Tag '{tag_id}' existiert bereits.")


if __name__ == "__main__": #Dieser Block ist pyhon typisch und ermöglciht, das Script auch eigenständig aufzurufen. Für meine Nutzung theoretisch irrelevant.
    import sys

    if not 4 <= len(sys.argv) <= 7:
        print('Aufruf: python3 swingdoor_sr.py <tagID> <pin> "<typ>" [zaehler] ["<besitzer>"] [ausgabedatum]')
        sys.exit(1)
    add_tag(*sys.argv[1:])
    print("Tag eingetragen.")
