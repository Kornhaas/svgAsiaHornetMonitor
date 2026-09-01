# Lokales YOLO-Training

Dieser Ordner enthält bewusst **manuell gestartete** Werkzeuge für den Windows-PC. Sie greifen auf den gleichen, versionierten YOLO-Export zu wie die Weboberfläche, verändern aber weder die Pi-Kamera noch den laufenden Monitor.

## Einmalige Einrichtung auf Windows

Im Projektordner reicht `uv`; eine zusätzliche virtuelle Umgebung oder `pip`-Installation ist nicht nötig:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv sync --locked
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Bei einer NVIDIA-Grafikkarte sollte zusätzlich `nvidia-smi` funktionieren. `True` in der letzten Zeile bedeutet, dass das Skript mit `--device auto` die GPU verwendet. Bei `False` funktioniert das Training auf der CPU, dauert aber deutlich länger.

## Daten vom Pi übernehmen

Zuerst Ereignisbilder und Annotationen vom Pi in den lokalen Projektordner kopieren. Auf Windows PowerShell beispielsweise:

```powershell
scp -r hornet@hornet.local:~/svgAsiaHornetMonitor/data/events .\data\
scp hornet@hornet.local:~/svgAsiaHornetMonitor/data/annotations.jsonl .\data\
```

Alternativ kann das Backup aus **Systemstatus** auf dem Pi heruntergeladen und lokal entpackt werden. Die Dateien `data/events/` und `data/annotations.jsonl` sind Laufzeitdaten und bleiben daher absichtlich außerhalb von Git.

## 1. YOLO-Datensatz exportieren

Nur geprüfte Boxen der Klassen `vespa_velutina`, `vespa_crabro`, `wasp`, `bee`, `other` und `goldfly` werden exportiert. `empty` wird als Bild ohne Label-Datei aufgenommen. Der Split ist stabil: 70 % Training, 20 % Validierung, 10 % Test.

```powershell
uv run python training/export_yolo.py
```

Das Ergebnis ist ein neuer Ordner unter `data/datasets/<Zeitstempel>/`. Die Ausgabe nennt den vollständigen Pfad zur `dataset.yaml`. Der Export kann ohne Risiko wiederholt werden und startet kein Training.

## 2. Lokal trainieren

Das folgende Beispiel verwendet automatisch die neueste lokale `dataset.yaml`, das kleine vortrainierte Modell `yolo11n.pt` und wählt GPU oder CPU automatisch:

```powershell
uv run python training/train_local.py --epochs 50 --image-size 640
```

Für einen bestimmten, reproduzierbaren Export:

```powershell
uv run python training/train_local.py --dataset data/datasets/20260901_220000/dataset.yaml --epochs 50 --device 0
```

Die Ergebnisse liegen getrennt vom Pi-Modellbestand unter `data/models/local-experiments/<Laufname>/`; wichtig ist `weights/best.pt`. Für Windows bleibt `--workers 0` der zuverlässige Standard. Bei knappen GPU-Speicher `--batch 1` verwenden.

## 3. Modell auswerten

```powershell
uv run python training/evaluate_model.py data/models/local-experiments/local_20260901_220000/weights/best.pt
```

Standardmäßig wird die Validierungsmenge (`val`) ausgewertet. Für die einmalige Schlussprüfung `--split test` verwenden. Ein Test-Split kann bei sehr wenigen Bildern leer sein; dann zuerst mehr unterschiedliche, geprüfte Events sammeln.

## Übernahme auf den Pi

Erst ein Modell übernehmen, wenn die Validierung plausibel ist und die Bilder manuell geprüft wurden. Kopiere `best.pt` nach `data/models/<version>/weights/best.pt` auf dem Pi und lege die zugehörige `model.json` mit Datensatz- und Evaluationsdaten an, oder nutze einen künftig vorgesehenen Import im UI. Das bestehende Pi-Training erzeugt diese Metadaten automatisch; diese lokalen Skripte überschreiben niemals ein aktives Pi-Modell.

> Mit 5–10 Bildern nicht auf Kennzahlen vertrauen: Die ersten Durchläufe dienen vor allem dazu, Export, Boxen und Bildqualität zu kontrollieren. Für robuste Erkennung sind viele unterschiedliche lokale Ereignisse, Perspektiven und Lichtbedingungen nötig.
