# Lokales YOLO-Training

Dieser Ordner enthält manuell gestartete Werkzeuge für den Windows-PC. Sie verwenden dieselben versionierten YOLO-Exporte wie die Weboberfläche, verändern aber weder die Pi-Kamera noch den laufenden Monitor.

## Vollautomatischer Schnellablauf

Das Pi-Passwort wird nicht gespeichert. Einmalig einen eigenen SSH-Schluessel
fuer den Trainings-PC einrichten; dabei fragt Windows das Pi-Passwort nur dieses
eine Mal ab:

~~~powershell
.\training\initialize_pi_training_key.ps1
~~~

Danach fuehrt ein Befehl den ganzen sicheren Zyklus aus: Ereignisbilder und
Annotationen vom Pi abrufen, YOLO-Datensatz exportieren, auf der GPU trainieren,
auswerten und das Modell samt Kennzahlen zurueck auf den Pi importieren.

~~~powershell
.\training\run_local_training.ps1 -Epochs 50
~~~

Das neue Modell bleibt bewusst inaktiv. Nach dem Lauf auf dem Pi unter
**Modell & Training** pruefen und erst dann mit **Modell verwenden** aktivieren.
Mit `-SkipImport` kann der automatische Ruecktransfer ausgelassen werden.

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

## Schnellablauf für jeden Trainingslauf

Nach der einmaligen Einrichtung erledigt ein PowerShell-Skript den wiederholten Ablauf: Daten vom Pi kopieren, exportieren, auf der GPU trainieren und auf dem Validierungs-Split auswerten.

~~~powershell
.\training\run_local_training.ps1 -Epochs 50
~~~

Falls PowerShell die Ausführung lokaler Skripte blockiert, nur für das aktuelle Fenster erlauben:

~~~powershell
Set-ExecutionPolicy -Scope Process Bypass
.\training\run_local_training.ps1 -Epochs 50
~~~

Der Standard-Pi ist hornet@hornet.local. Für einen anderen Host:

~~~powershell
.\training\run_local_training.ps1 -PiHost hornet@192.168.178.67 -Epochs 50
~~~

Wenn Ereignisbilder und Annotationen bereits aktuell lokal vorhanden sind, kann der Download übersprungen werden:

~~~powershell
.\training\run_local_training.ps1 -SkipDownload -Epochs 50
~~~

Das Skript beendet sich bei einem fehlgeschlagenen Kopier-, Export-, Trainings- oder Evaluierungsschritt mit einer verständlichen Fehlermeldung. Es aktiviert niemals automatisch ein Modell auf dem Pi.

## Daten vom Pi übernehmen

Zuerst den lokalen Zielordner anlegen. Die Inhalte von events müssen unter data/events landen, damit die relativen Pfade der Annotationen passen:

~~~powershell
New-Item -ItemType Directory -Force .\data\events | Out-Null
scp -r hornet@hornet.local:~/svgAsiaHornetMonitor/data/events/. .\data\events\
scp hornet@hornet.local:~/svgAsiaHornetMonitor/data/annotations.jsonl .\data\
~~~

Alternativ kann das Backup aus der Seite **Systemstatus** auf dem Pi heruntergeladen und lokal entpackt werden. Die Dateien unter data/events und data/annotations.jsonl sind Laufzeitdaten und bleiben absichtlich außerhalb von Git.

## 1. YOLO-Datensatz exportieren

Nur geprüfte Boxen der Klassen vespa_velutina, vespa_crabro, wasp, bee, ant, other, goldfly, fleshfly und blue_blowfly werden exportiert. empty wird als Bild ohne Label-Datei aufgenommen. Der Split ist stabil: 70 % Training, 20 % Validierung, 10 % Test. Alle Bilder einer Ereignisserie bleiben dabei gemeinsam in genau einem Split, damit nahezu identische Burst-Frames die Validierung nicht verfälschen.

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

Die Ergebnisse liegen getrennt vom Pi-Modellbestand unter data/models/local-experiments/Laufname; wichtig ist weights/best.pt. Für Windows bleibt --workers 0 der zuverlässige Standard. Bei knappem GPU-Speicher --batch 1 verwenden. Die neben `weights/` liegende `results.csv` enthält die Validierungskennzahlen und wird beim Modellimport automatisch als mAP, Precision und Recall in die Pi-Modellversion übernommen.

## 3. Modell auswerten

~~~powershell
.\.venv-gpu\Scripts\python.exe training\evaluate_model.py data/models/local-experiments/local_20260901_220000/weights/best.pt --device 0
~~~

Standardmäßig wird die Validierungsmenge ausgewertet. Für die einmalige Schlussprüfung --split test verwenden. Ein Test-Split kann bei sehr wenigen Bildern leer sein; dann zuerst mehr unterschiedliche, geprüfte Events sammeln.

## Übernahme auf den Pi

Ein Modell erst übernehmen, wenn die Validierung plausibel ist und die Bilder manuell geprüft wurden. Das Importskript kopiert best.pt als neue Modellversion und legt die erforderliche model.json an:

~~~powershell
.\training\import_model_to_pi.ps1 `
  -Model .\data\models\local-experiments\local_20260901_112400\weights\best.pt `
  -Version 20260901_112400
~~~

Nach erfolgreichem Import auf dem Pi im Menü **Modell & Training** die neue Version prüfen und erst mit **Modell verwenden** aktivieren. Das Importskript schreibt absichtlich keine latest.json und startet den Monitor nicht neu; ein ungeprüftes Modell kann dadurch nie automatisch die Erkennung übernehmen.

Wurde ein Modell bereits ohne Kennzahlen importiert, denselben Importbefehl mit identischer `-Version` nochmals ausführen. Das Skript aktualisiert dann die `model.json` auf dem Pi mit den Werten aus der lokalen `results.csv`; danach die Seite **Modell & Training** neu laden.

> Mit 5–10 Bildern nicht auf Kennzahlen vertrauen: Die ersten Durchläufe dienen vor allem dazu, Export, Boxen und Bildqualität zu kontrollieren. Für robuste Erkennung sind viele unterschiedliche lokale Ereignisse, Perspektiven und Lichtbedingungen nötig.
