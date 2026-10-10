"""
rfid_reader.py - Liest RFID-Tags über einen PN532 (I2C) am Raspberry Pi.

Benötigt:  pip install adafruit-circuitpython-pn532
I2C aktivieren:  sudo raspi-config -> Interface Options -> I2C
"""
import threading
import time

READ_TIMEOUT = 15  # Sekunden, die auf einen Tag gewartet wird


class ReaderError(RuntimeError):
    """Lesegerät nicht erreichbar oder Fehler beim Lesen."""


class ReaderBusy(RuntimeError):
    """Es läuft bereits ein Lesevorgang."""


class ReadTimeout(RuntimeError):
    """Innerhalb der Wartezeit wurde kein Tag erkannt."""


class ReadCancelled(RuntimeError):
    """Lesevorgang wurde abgebrochen."""


_pn532 = None
_busy = threading.Lock()
_cancel = threading.Event()


def _get_reader():
    """Initialisiert den PN532 beim ersten Gebrauch."""
    global _pn532
    if _pn532 is None:
        try:
            import board
            import busio
            from adafruit_pn532.i2c import PN532_I2C

            pn532 = PN532_I2C(busio.I2C(board.SCL, board.SDA), debug=False)
            pn532.SAM_configuration()
        except Exception as e:
            raise ReaderError(f"PN532 nicht erreichbar: {e}") from e
        _pn532 = pn532
    return _pn532


def read_tag_id(timeout=READ_TIMEOUT):
    """Wartet auf einen Tag und gibt dessen ID als Hex-String zurück (z.B. '04A1B2C3')."""
    global _pn532
    if not _busy.acquire(blocking=False):
        raise ReaderBusy("Es wird bereits ein Tag eingelesen.")
    try:
        _cancel.clear()
        reader = _get_reader()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if _cancel.is_set():
                raise ReadCancelled("Abgebrochen.")
            try:
                uid = reader.read_passive_target(timeout=0.5)
            except Exception as e:
                _pn532 = None  # beim nächsten Mal neu initialisieren
                raise ReaderError(f"Fehler beim Lesen: {e}") from e
            if uid:
                return uid.hex().upper()
        raise ReadTimeout("Kein Tag erkannt.")
    finally:
        _busy.release()


def cancel_read():
    """Bricht einen laufenden Lesevorgang ab."""
    _cancel.set()


if __name__ == "__main__":
    print(f"Bitte Tag an das Lesegerät halten ({READ_TIMEOUT} s) ...")
    print("Tag-ID:", read_tag_id())
