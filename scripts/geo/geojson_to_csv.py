"""Convert the local reference GeoJSON into a BigQuery-friendly CSV."""

from pathlib import Path
import csv
import json


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / "data" / "reference" / "mx-estados.json"
OUTPUT_PATH = REPO_ROOT / "data" / "generated" / "mx-estados.csv"


def convertir_a_csv() -> None:
    """Read the tracked reference GeoJSON and export one CSV row per state."""
    if not INPUT_PATH.exists():
        raise SystemExit(
            f"No existe el archivo de entrada {INPUT_PATH.relative_to(REPO_ROOT)}. "
            "Ejecuta scripts/geo/download_wgs84.py primero."
        )

    print(f"Leyendo el mapa de referencia: {INPUT_PATH.relative_to(REPO_ROOT)}")
    with INPUT_PATH.open("r", encoding="utf-8") as file_handle:
        mapa = json.load(file_handle)

    estados = mapa.get("features", [])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Creando archivo CSV para BigQuery: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(["state_name", "geometry_string"])

        for estado in estados:
            nombre = estado["properties"].get("name", "Desconocido")
            geometria_texto = json.dumps(estado["geometry"])
            writer.writerow([nombre, geometria_texto])

    print("Conversion completada.")


if __name__ == "__main__":
    convertir_a_csv()
