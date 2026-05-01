-- ==============================================================================
-- CAPA PLATA (SILVER LAYER) - VISTA IDEMPOTENTE DE PRECIOS NACIONALES
-- ==============================================================================
-- Propósito: Esta vista limpia, enriquece y deduplica los datos crudos en tiempo real.
-- Al ser una vista, no consume almacenamiento extra y siempre refleja la última verdad 
-- disponible, protegiendo el Data Warehouse de fallos y reintentos del pipeline.
-- ==============================================================================

CREATE OR REPLACE VIEW `cne-pipeline-mx-2026.cne_historical_data.vw_precios_nacionales_latest` AS
SELECT 
  -- 1. DATOS DESCRIPTIVOS
  p.station_name,
  e.state_name, 

  -- 2. MÉTRICAS (HECHOS)
  f.regular_price, 
  f.premium_price, 
  f.diesel_price,
  
  -- 3. TIEMPO
  f.business_date

-- CAPA BRONCE (Datos Crudos)
FROM `cne-pipeline-mx-2026.cne_historical_data.fact_prices` f

-- CRUCE ESTÁNDAR: Catálogo de gasolineras
JOIN `cne-pipeline-mx-2026.cne_historical_data.fact_places` p
  ON f.place_id = p.place_id
  AND f.business_date = p.business_date

-- CRUCE ESPACIAL: Mapeo de coordenadas al estado correspondiente
JOIN `cne-pipeline-mx-2026.cne_historical_data.dim_estados` e
  ON ST_CONTAINS(e.geometry, ST_GEOGPOINT(p.longitude, p.latitude))

-- REGLAS DE CALIDAD DE DATOS
WHERE f.regular_price IS NOT NULL
  AND p.latitude IS NOT NULL 
  AND p.longitude IS NOT NULL
  -- Filtro de Cordura: Precios entre $10 y $40 MXN
  AND (
    f.regular_price BETWEEN 10 AND 40
    OR f.premium_price BETWEEN 10 AND 40
    OR f.diesel_price BETWEEN 10 AND 40
  )

-- MOTOR DE IDEMPOTENCIA (DEDUPLICACIÓN)
-- Filtra filas duplicadas generadas por múltiples reintentos del Cloud Scheduler en un mismo día.
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY f.business_date, f.place_id
  ORDER BY f.business_date DESC
) = 1;