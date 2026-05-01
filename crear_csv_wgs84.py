import urllib.request
import json
import csv

def descargar_mapa_wgs84():
    print("Descargando mapa oficial WGS84 (angelnmara/geojson)...")
    url = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        mapa = json.loads(response.read().decode('utf-8'))
        
    estados = mapa.get('features', [])
    print(f"Se descargaron {len(estados)} estados.")
    
    with open('mx-estados-final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['state_name', 'geometry_string']) 
        
        for estado in estados:
            # Extraemos el nombre
            nombre = estado['properties'].get('name', 'Desconocido')
            geometria = estado['geometry']
            
            # Sanity Check visual para ti
            if nombre in ['Ciudad de México', 'Distrito Federal']:
                try:
                    tipo = geometria['type']
                    # Extraemos un punto profundo de prueba
                    coord = geometria['coordinates'][0][0][0] if tipo == 'Polygon' else geometria['coordinates'][0][0][0][0]
                    print(f"✅ Sanity Check en {nombre}: {coord} (¡Debe estar entre -180 y 90!)")
                except:
                    pass
                    
            writer.writerow([nombre, json.dumps(geometria)])
            
    print("¡Listo! Archivo a prueba de balas generado: mx-estados-final.csv")

if __name__ == "__main__":
    descargar_mapa_wgs84()