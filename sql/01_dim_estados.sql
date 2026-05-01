-- ==============================================================================
-- DIMENSIÓN ESPACIAL: dim_estados
-- ==============================================================================
-- Propósito: Convierte el archivo CSV crudo (que contiene las coordenadas WGS84 
-- en texto) en una tabla con objetos GEOGRAPHY nativos de BigQuery.
-- Esta tabla es el catálogo base para realizar cruces de Spatial Join.
-- ==============================================================================

CREATE OR REPLACE TABLE `cne-pipeline-mx-2026.cne_historical_data.dim_estados` AS
SELECT 
  string_field_0 AS state_name,
  -- La función ST_GEOGFROMGEOJSON transforma el string de coordenadas
  -- en un polígono matemático que BigQuery puede analizar espacialmente.
  ST_GEOGFROMGEOJSON(string_field_1) AS geometry
FROM `cne-pipeline-mx-2026.cne_historical_data.raw_estados_final`
-- Filtramos la fila de encabezados en caso de que la detección automática del CSV la haya incluido
WHERE string_field_0 != 'state_name';