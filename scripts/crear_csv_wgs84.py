"""Convert a local GeoJSON file into a CSV that BigQuery can ingest easily."""

import json
import csv

def convertir_a_csv():
    """Read the saved GeoJSON file and emit one CSV row per state."""
    print("Leyendo el mapa original...")
    with open('mx-estados.json', 'r', encoding='utf-8') as f:
        mapa = json.load(f)
        
    estados = mapa.get('features', [])
    
    print("Creando archivo CSV para BigQuery...")
    with open('mx-estados.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # The SQL step expects a plain name column plus a JSON geometry string.
        writer.writerow(['state_name', 'geometry_string']) 
        
        for estado in estados:
            # Extract the human-readable state name for downstream joins and QA.
            nombre = estado['properties'].get('name', 'Desconocido')
            # Store the geometry as serialized JSON so the CSV remains a simple
            # tabular file and BigQuery can convert it later.
            geometria_texto = json.dumps(estado['geometry'])
            
            writer.writerow([nombre, geometria_texto])
            
    print("¡Éxito! Archivo listo para la interfaz web: mx-estados.csv")

if __name__ == "__main__":
    convertir_a_csv()
