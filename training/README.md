# Lokales YOLO-Training

Dieser Ordner enthält manuell gestartete Werkzeuge für den Windows-PC. Sie verwenden dieselben versionierten YOLO-Exporte wie die Weboberfläche, verändern aber weder die Pi-Kamera noch den laufenden Monitor.

## Einmalige Einrichtung auf Windows

Die normale Projektumgebung wird für Export und Tests verwendet. Für eine NVIDIA-GPU wird zusätzlich eine getrennte lokale Trainingsumgebung angelegt. So bleibt der für den Raspberry Pi gelockte CPU-Abhängigkeitsbestand unverändert.

~~~powershell
irm https://astral.sh/uv/install.ps1 | iex
uv sync --locked
~~~

Bei einer NVIDIA-Grafikkarte zuerst den Treiber prüfen:

~~~powershell
nvidia-smi
~~~

Dann die GPU-Trainingsumgebung erzeugen. Der Parameter --torch-backend=auto wählt passend zum installierten NVIDIA-Treiber ein CUDA-PyTorch-Paket aus:

~~~powershell
uv venv .venv-gpu
uv pip install --python .venv-gpu\Scripts\python.exe ultralytics torch torchvision --torch-backend=auto
~~~

Die GPU-Nutzung prüfen:

~~~powershell
.\.venv-gpu\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
~~~

Bei einer RTX 4070 müssen torch.cuda.is_available() den Wert True und der Gerätename NVIDIA GeForce RTX 4070 ausgeben. Falls False erscheint, zuerst mit nvidia-smi auf einen fehlenden oder zu alten NVIDIA-Treiber prüfen. Ein separates CUDA Toolkit ist normalerweise nicht erforderlich.

## Daten vom Pi übernehmen

Zuerst den lokalen Zielordner anlegen. Die Inhalte von events müssen unter data/events landen, damit die relativen Pfade der Annotationen passen:

~~~powershell
New-Item -ItemType Directory -Force .\data\events | Out-Null
scp -r hornet@hornet.local:~/svgAsiaHornetMonitor/data/events/. .\data\events\
scp hornet@hornet.local:~/svgAsiaHornetMonitor/data/annotations.jsonl .\data\
~~~

Alternativ kann das Backup aus der Seite **Systemstatus** auf dem Pi heruntergeladen und lokal entpackt werden. Die Dateien unter data/events und data/annotations.jsonl sind Laufzeitdaten und bleiben absichtlich außerhalb von Git.

## 1. YOLO-Datensatz exportieren

Nur geprüfte Boxen der Klassen vespa_velutina, vespa_crabro, wasp, bee, other, goldfly und fleshfly werden exportiert. empty wird als Bild ohne Label-Datei aufgenommen. Der Split ist stabil: 70 % Training, 20 % Validierung, 10 % Test.

~~~powershell
uv run python training/export_yolo.py
~~~

Das Ergebnis ist ein neuer Ordner unter data/datasets/Zeitstempel. Die Ausgabe nennt den vollständigen Pfad zur dataset.yaml. Der Export kann gefahrlos wiederholt werden und startet kein Training.

## 2. Lokal trainieren

Das folgende Beispiel verwendet automatisch die neueste lokale dataset.yaml, das kleine vortrainierte Modell yolo11n.pt und die GPU:

~~~powershell
.\.venv-gpu\Scripts\python.exe training\train_local.py --epochs 50 --image-size 640 --device 0
~~~

Für einen bestimmten, reproduzierbaren Export:

~~~powershell
.\.venv-gpu\Scripts\python.exe training\train_local.py --dataset data/datasets/20260901_220000/dataset.yaml --epochs 50 --device 0
~~~

Die Ergebnisse liegen getrennt vom Pi-Modellbestand unter data/models/local-experiments/Laufname; wichtig ist weights/best.pt. Für Windows bleibt --workers 0 der zuverlässige Standard. Bei knappem GPU-Speicher --batch 1 verwenden.

## 3. Modell auswerten

~~~powershell
.\.venv-gpu\Scripts\python.exe training\evaluate_model.py data/models/local-experiments/local_20260901_220000/weights/best.pt --device 0
~~~

Standardmäßig wird die Validierungsmenge ausgewertet. Für die einmalige Schlussprüfung --split test verwenden. Ein Test-Split kann bei sehr wenigen Bildern leer sein; dann zuerst mehr unterschiedliche, geprüfte Events sammeln.

## Übernahme auf den Pi

Ein Modell erst übernehmen, wenn die Validierung plausibel ist und die Bilder manuell geprüft wurden. Kopiere best.pt nach data/models/Version/weights/best.pt auf dem Pi und lege die zugehörige model.json mit Datensatz- und Evaluationsdaten an. Das bestehende Pi-Training erzeugt diese Metadaten automatisch; diese lokalen Skripte überschreiben niemals ein aktives Pi-Modell.

> Mit 5–10 Bildern nicht auf Kennzahlen vertrauen: Die ersten Durchläufe dienen vor allem dazu, Export, Boxen und Bildqualität zu kontrollieren. Für robuste Erkennung sind viele unterschiedliche lokale Ereignisse, Perspektiven und Lichtbedingungen nötig.
