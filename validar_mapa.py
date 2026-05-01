"""Validate GeoJSON coordinates before exporting them to CSV for BigQuery."""

import urllib.request
import json
import csv

def validar_y_crear():
    """Check coordinate ranges and only write the CSV when the map looks valid."""
    print("1. Descargando mapa oficial WGS84 (angelnmara/geojson)...")
    url = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        mapa = json.loads(response.read().decode('utf-8'))
        
    estados = mapa.get('features', [])
    
    print("\n2. Ejecutando Validación de Coordenadas Geográficas...")
    latitudes = []
    longitudes = []
    
    # Recorrer todos los estados para extraer todas las coordenadas
    for estado in estados:
        geometria = estado['geometry']
        coordenadas = geometria['coordinates']
        
        # Recorremos cualquier nivel de anidación hasta llegar a pares [lon, lat].
        def extraer_coords(lista):
            for item in lista:
                if isinstance(item, list) and len(item) == 2 and isinstance(item[0], (int, float)):
                    longitudes.append(item[0]) # X
                    latitudes.append(item[1])  # Y
                elif isinstance(item, list):
                    extraer_coords(item)
                    
        extraer_coords(coordenadas)
        
    min_lat, max_lat = min(latitudes), max(latitudes)
    min_lon, max_lon = min(longitudes), max(longitudes)
    
    print(f"Rango de Latitud  (Y): {min_lat:.4f} a {max_lat:.4f}  (Requisito BQ: -90 a 90)")
    print(f"Rango de Longitud (X): {min_lon:.4f} a {max_lon:.4f} (Requisito BQ: -180 a 180)")
    
    if min_lat < -90 or max_lat > 90 or min_lon < -180 or max_lon > 180:
        print("❌ ERROR: Las coordenadas NO son válidas. Abortando creación de CSV.")
        return
        
    print("✅ VALIDACIÓN EXITOSA: Coordenadas 100% compatibles con BigQuery.")
    
    print("\n3. Creando archivo CSV seguro...")
    with open('mx-estados-validado.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['state_name', 'geometry_string']) 
        for estado in estados:
            nombre = estado['properties'].get('name', 'Desconocido')
            # Cada fila conserva el GeoJSON completo como texto para convertirlo
            # después a GEOGRAPHY dentro de BigQuery.
            writer.writerow([nombre, json.dumps(estado['geometry'])])
        
    print("¡Listo! Archivo generado: mx-estados-validado.csv")

if __name__ == "__main__":
    validar_y_crear()
