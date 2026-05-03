"""Cloud Function entry point for the CNE gas price ingestion pipeline."""

import functions_framework
import requests
import pytz
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud import bigquery
import xml.etree.ElementTree as ET
import os
import logging

logging.basicConfig(level=logging.INFO)

PRICES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
PLACES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/places"
BUCKET_NAME = os.environ.get("BUCKET_NAME")
PROJECT_ID = os.environ.get("PROJECT_ID")
DATASET_ID = "cne_historical_data"

def get_business_date() -> str:
    """Return the business date that the ingestion should represent."""
    cdmx_tz = pytz.timezone('America/Mexico_City')
    now_cdmx = datetime.now(cdmx_tz)
    # The source data is refreshed after 18:00 local time, so early-morning runs
    # must still be labeled with the previous calendar day.
    if now_cdmx.hour < 18:
        business_date = (now_cdmx - timedelta(days=1)).date()
    else:
        business_date = now_cdmx.date()
    return business_date.strftime('%Y-%m-%d')

def parse_and_load_bq(xml_content: bytes, data_type: str, business_date: str) -> None:
    """Transform one XML payload into rows and append them to the matching table."""
    logging.info(f"Parsing {data_type} and loading to BigQuery...")
    root = ET.fromstring(xml_content)
    records = []
    
    # Generate the exact processing timestamp for traceability
    date_processing = datetime.now(pytz.utc).isoformat()

    if data_type == 'prices':
        places_dict = {}
        # The XML fragments prices into multiple <place> nodes with the same place_id.
        # We pivot this using a dictionary to aggregate all fuels into a single row.
        for place in root.findall('.//place'):
            place_id = place.get('place_id')
            if not place_id:
                continue
                
            place_id_int = int(place_id)
            
            # Initialize the base row if it's the first time we see this place_id
            if place_id_int not in places_dict:
                places_dict[place_id_int] = {
                    'place_id': place_id_int,
                    'regular_price': None,
                    'premium_price': None,
                    'diesel_price': None,
                    'business_date': business_date,
                    'date_processing': date_processing
                }
            
            # Fill the specific fuel prices found in this fragment
            for gas_price in place.findall('gas_price'):
                p_type = gas_price.get('type')
                if not gas_price.text:
                    continue
                    
                price_val = float(gas_price.text)
                if p_type == 'regular':
                    places_dict[place_id_int]['regular_price'] = price_val
                elif p_type == 'premium':
                    places_dict[place_id_int]['premium_price'] = price_val
                elif p_type == 'diesel':
                    places_dict[place_id_int]['diesel_price'] = price_val
                    
        # Extract the aggregated rows from the dictionary
        records = list(places_dict.values())
        
    elif data_type == 'places':
        for place in root.findall('.//place'):
            place_id = place.get('place_id')
            if not place_id:
                continue
                
            name = place.findtext('name')
            cre_id = place.findtext('cre_id')
            location = place.find('location')
            lon = location.findtext('x') if location is not None else None
            lat = location.findtext('y') if location is not None else None
            
            records.append({
                'place_id': int(place_id),
                'station_name': name,
                'cre_permit': cre_id,
                'longitude': float(lon) if lon else None,
                'latitude': float(lat) if lat else None,
                'business_date': business_date,
                'date_processing': date_processing
            })

    # Load to BigQuery
    bq_client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_ID}.fact_{data_type}"
    
    # Configure BigQuery to automatically detect schema and append data
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        autodetect=True
    )
    
    if records:
        job = bq_client.load_table_from_json(records, table_id, job_config=job_config)
        job.result()  # Wait for the job to complete
        logging.info(f"Successfully appended {job.output_rows} rows to {table_id}")
    else:
        logging.warning(f"No records parsed to load for {data_type}.")

def fetch_upload_and_parse(
    url: str,
    blob_path: str,
    bucket,
    data_type: str,
    business_date: str,
) -> None:
    """Fetch a source feed, archive it raw, and append its parsed rows to BigQuery."""
    logging.info(f"Fetching {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    xml_content = response.content
    
    # 1. Save Raw XML to Storage
    blob = bucket.blob(blob_path)
    blob.upload_from_string(xml_content, content_type='application/xml')
    logging.info(f"Saved raw {data_type} to gs://{bucket.name}/{blob_path}")
    
    # 2. Parse and Load to BigQuery
    parse_and_load_bq(xml_content, data_type, business_date)

@functions_framework.http
def ingest_cne_data(request):
    """HTTP-triggered Cloud Function used by Cloud Scheduler."""
    business_date = get_business_date()
    logging.info(f"Starting ingestion for business date: {business_date}")
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    year, month = business_date.split('-')[0], business_date.split('-')[1]
    
    # Keep the raw archive partitioned by source, year, and month
    prices_path = f"raw/prices/year={year}/month={month}/prices_{business_date}.xml"
    places_path = f"raw/places/year={year}/month={month}/places_{business_date}.xml"
    
    fetch_upload_and_parse(PRICES_URL, prices_path, bucket, 'prices', business_date)
    fetch_upload_and_parse(PLACES_URL, places_path, bucket, 'places', business_date)
    
    return "Ingestion and BigQuery Load complete.", 200

# Trigger CI/CD pipeline