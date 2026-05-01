import json
import csv

def convertir_a_csv():
    print("Leyendo el mapa original...")
    with open('mx-estados.json', 'r', encoding='utf-8') as f:
        mapa = json.load(f)
        
    estados = mapa.get('features', [])
    
    print("Creando archivo CSV para BigQuery...")
    with open('mx-estados.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Nombres de las columnas
        writer.writerow(['state_name', 'geometry_string']) 
        
        for estado in estados:
            # Extraemos el nombre del estado
            nombre = estado['properties'].get('name', 'Desconocido')
            # Convertimos el bloque de coordenadas a un texto plano seguro
            geometria_texto = json.dumps(estado['geometry'])
            
            writer.writerow([nombre, geometria_texto])
            
    print("¡Éxito! Archivo listo para la interfaz web: mx-estados.csv")

if __name__ == "__main__":
    convertir_a_csv()