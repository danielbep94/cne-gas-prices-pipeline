"""Download the canonical Mexico GeoJSON into the repository reference-data folder."""

from pathlib import Path
import json
import urllib.request


URL = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = REPO_ROOT / "data" / "reference"
OUTPUT_PATH = REFERENCE_DIR / "mx-estados.json"


def descargar_mapa_wgs84() -> None:
    """Download the source GeoJSON used by the local geo-preparation scripts."""
    print("Descargando mapa oficial WGS84 (angelnmara/geojson)...")

    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        mapa = json.loads(response.read().decode("utf-8"))

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(mapa, file_handle, ensure_ascii=False, indent=2)

    estados = mapa.get("features", [])
    print(f"Se descargaron {len(estados)} estados.")
    print(f"Archivo guardado en: {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    descargar_mapa_wgs84()
