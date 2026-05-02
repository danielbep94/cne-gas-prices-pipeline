"""Validate the local reference GeoJSON before exporting a safe CSV for BigQuery."""

from pathlib import Path
import csv
import json


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / "data" / "reference" / "mx-estados.json"
OUTPUT_PATH = REPO_ROOT / "data" / "generated" / "mx-estados-validado.csv"


def extraer_coords(lista, longitudes, latitudes) -> None:
    """Walk nested polygon coordinates until a [lon, lat] pair is found."""
    for item in lista:
        if isinstance(item, list) and len(item) == 2 and isinstance(item[0], (int, float)):
            longitudes.append(item[0])
            latitudes.append(item[1])
        elif isinstance(item, list):
            extraer_coords(item, longitudes, latitudes)


def validar_y_crear() -> None:
    """Check coordinate bounds and only then generate the validated CSV."""
    if not INPUT_PATH.exists():
        raise SystemExit(
            f"No existe el archivo de entrada {INPUT_PATH.relative_to(REPO_ROOT)}. "
            "Ejecuta scripts/geo/download_wgs84.py primero."
        )

    print(f"1. Leyendo mapa de referencia: {INPUT_PATH.relative_to(REPO_ROOT)}")
    with INPUT_PATH.open("r", encoding="utf-8") as file_handle:
        mapa = json.load(file_handle)

    estados = mapa.get("features", [])

    print("\n2. Ejecutando validacion de coordenadas geograficas...")
    latitudes = []
    longitudes = []

    for estado in estados:
        geometria = estado["geometry"]
        extraer_coords(geometria["coordinates"], longitudes, latitudes)

    min_lat, max_lat = min(latitudes), max(latitudes)
    min_lon, max_lon = min(longitudes), max(longitudes)

    print(f"Rango de Latitud  (Y): {min_lat:.4f} a {max_lat:.4f}  (Requisito BQ: -90 a 90)")
    print(f"Rango de Longitud (X): {min_lon:.4f} a {max_lon:.4f} (Requisito BQ: -180 a 180)")

    if min_lat < -90 or max_lat > 90 or min_lon < -180 or max_lon > 180:
        print("ERROR: Las coordenadas no son validas. Abortando creacion de CSV.")
        return

    print("Validacion exitosa: coordenadas compatibles con BigQuery.")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n3. Creando archivo CSV seguro: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(["state_name", "geometry_string"])

        for estado in estados:
            nombre = estado["properties"].get("name", "Desconocido")
            writer.writerow([nombre, json.dumps(estado["geometry"])])

    print("Archivo validado generado correctamente.")


if __name__ == "__main__":
    validar_y_crear()
