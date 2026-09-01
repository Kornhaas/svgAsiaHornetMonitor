"""Local German and English user-interface translations."""

from __future__ import annotations

GERMAN = {
    "Live monitor": "Live-Überwachung",
    "Image gallery": "Bildergalerie",
    "ROI settings": "ROI-Einstellungen",
    "Model & training": "Modell & Training",
    "System status": "Systemstatus",
    "Camera settings": "Kameraeinstellungen",
    "Sign in to manage your local monitor.": (
        "Melde dich an, um deinen lokalen Monitor zu verwalten."
    ),
    "Username": "Benutzername",
    "Password": "Passwort",
    "Sign in": "Anmelden",
    "Observe activity in the configured region of interest.": (
        "Beobachte Aktivitäten im konfigurierten Interessensbereich."
    ),
    "Connecting…": "Verbinde…",
    "Activity log": "Aktivitätsprotokoll",
    "Loading activity…": "Aktivität wird geladen…",
    "System update": "Systemaktualisierung",
    "Check whether an update is available.": "Prüfe, ob eine Aktualisierung verfügbar ist.",
    "Check for update": "Auf Aktualisierung prüfen",
    "Install update": "Aktualisierung installieren",
    "Class": "Klasse",
    "Asian hornet": "Asiatische Hornisse",
    "European hornet": "Europäische Hornisse",
    "Wasp": "Wespe",
    "Bee": "Biene",
    "Other": "Andere",
    "Goldfly": "Goldfliege",
    "Flesh fly": "Echte Fleischfliege",
    "Blue blowfly": "Blaue Schmeißfliege",
    "Empty": "Leer",
    "Uncertain": "Unsicher",
    "Add box": "Box hinzufügen",
    "Suggest objects": "Objekte vorschlagen",
    "Save all": "Alle speichern",
    "Delete event": "Ereignis löschen",
    "Show reviewed images": "Bewertete Bilder anzeigen",
    "Show": "Anzeigen",
    "Unreviewed events": "Unbewertete Ereignisse",
    "Model suggestions": "Modellvorschläge",
    "Reviewed events with animals": "Bewertete Ereignisse mit Tieren",
    "All reviewed events": "Alle bewerteten Ereignisse",
    "All events": "Alle Ereignisse",
    "Burst frames": "Bildserie",
    "Choose the sharpest image for annotation.": (
        "Wähle das schärfste Bild für die Markierung aus."
    ),
    "Reviewed": "Bewertet",
    "Unreviewed": "Unbewertet",
    "No events available.": "Keine Ereignisse verfügbar.",
    "Night mode · preview disabled": "Nachtmodus · Vorschau deaktiviert",
    "Night mode active · live preview disabled": "Nachtmodus aktiv · Live-Vorschau deaktiviert",
    "Night mode pending": "Nachtmodus wird aktiviert",
    "Night mode active": "Nachtmodus aktiv",
    "night mode pending — preview disabled": "Nachtmodus wird aktiviert — Vorschau deaktiviert",
    "Refresh inbox": "Eingang aktualisieren",
    "Model suggestion:": "Modellvorschlag:",
    "Accept suggestion": "Vorschlag übernehmen",
    (
        "Confirm only if the animal and box are correct. You can adjust the box or select another "
        "class instead."
    ): (
        "Bitte nur übernehmen, wenn Tier und Box stimmen. Du kannst die Box anpassen oder eine "
        "andere Klasse wählen."
    ),
    "All visible events have been reviewed.": "Alle sichtbaren Ereignisse wurden bewertet.",
    "Remove": "Entfernen",
    "Image and trigger regions": "Bild- und Auslösebereiche",
    "Outer image ROI": "Äußerer Bild-ROI",
    "Inner trigger ROI": "Innerer Auslöse-ROI",
    "Save image ROI": "Bild-ROI speichern",
    "Save trigger ROI": "Auslöse-ROI speichern",
    (
        "Choose a region below and draw its rectangle directly on the live image. "
        "The outer yellow area is saved in event images. The inner blue area starts an "
        "event only after the animal has moved further into the image."
    ): (
        "Wähle unten einen Bereich und zeichne sein Rechteck direkt im Livebild. "
        "Der äußere gelbe Bereich wird in Ereignisbildern gespeichert. Der innere blaue "
        "Bereich startet ein Ereignis erst, wenn sich das Tier weiter ins Bild bewegt hat."
    ),
    "Draw image ROI": "Bild-ROI zeichnen",
    "Draw trigger ROI": "Auslöse-ROI zeichnen",
    "Drag to draw a rectangle.": "Ziehe, um ein Rechteck zu zeichnen.",
    "Camera dimensions are unavailable.": "Kameraabmessungen sind nicht verfügbar.",
    "Camera device": "Kameragerät",
    "Width": "Breite",
    "Height": "Höhe",
    "Save and restart": "Speichern und neu starten",
    "Training status": "Trainingsstatus",
    "Model versions and evaluation": "Modellversionen und Auswertung",
    "Recent predictions": "Aktuelle Erkennungen",
    "No trained model yet.": "Noch kein trainiertes Modell.",
    "Use model": "Modell verwenden",
    "Active model:": "Aktives Modell:",
    "Active": "Aktiv",
    "Loading…": "Wird geladen…",
    "No predictions yet.": "Noch keine Erkennungen.",
    "Training starts only during this dark-time window.": (
        "Das Training startet nur in diesem nächtlichen Zeitfenster."
    ),
    "YOLO dataset export": "YOLO-Datensatzexport",
    "Current split estimate:": "Aktuelle Aufteilungsprognose:",
    "Create backup": "Backup erstellen",
    "Storage:": "Speicher:",
    "Start training now": "Training jetzt starten",
    (
        "Export reviewed animal boxes as a versioned local YOLO dataset with train, "
        "validation, and test splits. The export does not start training."
    ): (
        "Exportiere bewertete Tierboxen als versionierten lokalen YOLO-Datensatz mit "
        "Trainings-, Validierungs- und Testaufteilung. Der Export startet kein Training."
    ),
    "Export YOLO dataset": "YOLO-Datensatz exportieren",
    "Class distribution": "Klassenverteilung",
    "Active-learning quality": "Active-Learning-Qualität",
    "Review feedback:": "Prüfungsrückmeldung:",
    "Brightness drift signal:": "Helligkeits-Driftsignal:",
    "Prioritize more examples for:": "Weitere Beispiele priorisieren für:",
    "Automatic acceptance is unavailable.": "Automatische Übernahme ist nicht verfügbar.",
    "Automatic acceptance is disabled until explicitly enabled.": (
        "Die automatische Übernahme ist bis zur ausdrücklichen Aktivierung deaktiviert."
    ),
    "Only classes passing their evidence gate may be accepted automatically.": (
        "Nur Klassen mit erfüllter Nachweis-Freigabe dürfen automatisch übernommen werden."
    ),
    "High-confidence reviews": "Prüfungen mit hoher Konfidenz",
    "Observed precision": "Beobachtete Präzision",
    "Automatic gate": "Automatische Freigabe",
    "ready": "bereit",
    "not ready": "nicht bereit",
    "No labelled boxes yet.": "Noch keine markierten Boxen.",
    "Update background image": "Hintergrundbild aktualisieren",
    "Telegram notifications": "Telegram-Benachrichtigungen",
    "Enable Telegram": "Telegram aktivieren",
    "Bot token": "Bot-Token",
    "Chat ID": "Chat-ID",
    "Confidence threshold": "Konfidenzschwelle",
    "Cooldown seconds": "Sperrzeit in Sekunden",
    "Save Telegram settings": "Telegram-Einstellungen speichern",
    "Night mode:": "Nachtmodus:",
    "active — motion paused": "aktiv — Bewegung pausiert",
    "daylight monitoring": "Tagesüberwachung",
    "Background:": "Hintergrund:",
    "available": "vorhanden",
    "not captured": "nicht aufgenommen",
    "Disk:": "Festplatte:",
    "Memory:": "Arbeitsspeicher:",
    "Code update:": "Code-Aktualisierung:",
    "Saved locally.": "Lokal gespeichert.",
    "Draw a box first.": "Bitte zuerst eine Box zeichnen.",
    "Draw a box, or choose Empty.": "Bitte eine Box zeichnen oder Leer auswählen.",
    "Add a box, or choose Empty.": "Bitte eine Box hinzufügen oder Leer auswählen.",
    (
        "For an empty image, choose Empty and select Save all. For an animal, draw and add every "
        "box, then save all boxes together. Suggestions require review."
    ): (
        "Für ein leeres Bild Leer auswählen und Alle speichern klicken. Für ein Tier jede Box "
        "zeichnen und hinzufügen, dann alle Boxen gemeinsam speichern. Vorschläge bitte prüfen."
    ),
    "Suggestions added as uncertain.": "Vorschläge als unsicher hinzugefügt.",
    "No suggestions; update the background first.": (
        "Keine Vorschläge; bitte zuerst Hintergrund aktualisieren."
    ),
    "Saved.": "Gespeichert.",
    "Model suggestion accepted. Save to confirm it for training.": (
        "Modellvorschlag übernommen. Zum Bestätigen für das Training speichern."
    ),
    "Saved and marked unannotated frames as empty.": (
        "Gespeichert und alle unbewerteten Bilder der Serie als Leer markiert."
    ),
    "Delete event?": "Ereignis löschen?",
    "Status unavailable": "Status nicht verfügbar",
    "No activity recorded yet.": "Noch keine Aktivität erfasst.",
    "Activity log unavailable.": "Aktivitätsprotokoll nicht verfügbar.",
    "Gallery unavailable.": "Galerie nicht verfügbar.",
    "Motion detected in ROI": "Bewegung im ROI erkannt",
    "Watching ROI": "ROI wird überwacht",
    "Update installed; reconnecting the monitor…": (
        "Aktualisierung installiert; Monitor wird neu verbunden…"
    ),
    "Could not save settings.": "Einstellungen konnten nicht gespeichert werden.",
    "Background updated.": "Hintergrund aktualisiert.",
}


def translations(language: str) -> dict[str, str]:
    return GERMAN if language == "de" else {}
