# StatReportBuilder

A desktop app for building statistical reports from CSV data.

## Download (Windows)

1. Go to the [Releases page](https://github.com/theomegasauce/StatReportBuilder/releases) and download the latest `StatReportBuilder-vX.Y.Z-win64.zip`.
2. Unzip the folder anywhere on your computer (e.g. `Desktop` or `Documents`).
3. Open the unzipped folder and double-click `StatReportBuilder.exe`.

**First-run note:** Windows may show a "Windows protected your PC" SmartScreen warning because the app is not code-signed. Click **More info** → **Run anyway**. This is expected for unsigned apps and only happens the first time.

No Python install is required — everything is bundled.

## Run from source (developers)

```
pip install -r requirements.txt
python main.py
```

## Building a release locally

```
pip install pyinstaller
pyinstaller --noconfirm StatReportBuilder.spec
```

The bundled app is written to `dist/StatReportBuilder/`.
