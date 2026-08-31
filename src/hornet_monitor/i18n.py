"""Small local German/English translation catalogue for the web UI."""

from __future__ import annotations

CATALOGUE = {
    "de": {
        "Live monitor": "Live-Überwachung",
        "Image gallery": "Bildergalerie",
        "ROI settings": "ROI-Einstellungen",
        "Model & training": "Modell & Training",
        "System status": "Systemstatus",
        "Region of interest": "Interessensbereich",
        "Save ROI": "ROI speichern",
        "Save all": "Alle speichern",
        "Add box": "Box hinzufügen",
        "Suggest objects": "Objekte vorschlagen",
        "Delete event": "Ereignis löschen",
        "Update background image": "Hintergrundbild aktualisieren",
        "No model yet": "Noch kein Modell",
        "Model status": "Modellstatus",
        "Username": "Benutzername",
        "Password": "Passwort",
        "Sign in": "Anmelden",
        "Class": "Klasse",
        "Remove": "Entfernen",
        "Empty": "Leer",
        "Other": "Andere",
        "Uncertain": "Unsicher",
        "Wasp": "Wespe",
        "Bee": "Biene",
        "Asian hornet": "Asiatische Hornisse",
        "European hornet": "Europäische Hornisse",
        "Loading…": "Lädt…",
        "Loading events…": "Ereignisse werden geladen…",
        "Saved locally.": "Lokal gespeichert.",
        "Status unavailable": "Status nicht verfügbar",
        "Gallery unavailable.": "Galerie nicht verfügbar.",
        "Draw a box first.": "Bitte zuerst eine Box zeichnen.",
        "Saved.": "Gespeichert.",
        "Suggestions added as uncertain.": "Vorschläge als unsicher hinzugefügt.",
        "No suggestions; update the background first.": (
            "Keine Vorschläge – bitte zuerst Hintergrund aktualisieren."
        ),
        "Delete event?": "Ereignis löschen?",
        "Background updated.": "Hintergrund aktualisiert.",
    }
}


def translations(language: str) -> dict[str, str]:
    return CATALOGUE.get(language, {})
