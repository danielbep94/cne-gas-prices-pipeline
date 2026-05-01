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

    if data_type == 'prices':
        for place in root.findall('place'):
            place_id = place.get('place_id')
            prices = {'regular': None, 'premium': None, 'diesel': None}
            for gas_price in place.findall('gas_price'):
                p_type = gas_price.get('type')
                if p_type in prices:
                    prices[p_type] = float(gas_price.text)
            # Convert the nested XML fuel entries into one wide record per station/day.
            records.append({
                'place_id': place_id,
                'regular_price': prices['regular'],
                'premium_price': prices['premium'],
                'diesel_price': prices['diesel'],
                'business_date': business_date
            })
    elif data_type == 'places':
        for place in root.findall('place'):
            place_id = place.get('place_id')
            name = place.findtext('name')
            cre_id = place.findtext('cre_id')
            location = place.find('location')
            lon = location.findtext('x') if location is not None else None
            lat = location.findtext('y') if location is not None else None
            # Places and prices are stored separately so each raw feed preserves the
            # exact structure published by the source system.
            records.append({
                'place_id': place_id,
                'station_name': name,
                'cre_permit': cre_id,
                'longitude': lon,
                'latitude': lat,
                'business_date': business_date
            })

    # Load to BigQuery
    bq_client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_ID}.fact_{data_type}"
    
    # Configure BigQuery to automatically detect schema and append data
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        autodetect=True
    )
    
    job = bq_client.load_table_from_json(records, table_id, job_config=job_config)
    job.result()  # Wait for the job to complete
    logging.info(f"Successfully appended {job.output_rows} rows to {table_id}")

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
    
    # Keep the raw archive partitioned by source, year, and month so historical
    # reprocessing and manual audits are easy later.
    prices_path = f"raw/prices/year={year}/month={month}/prices_{business_date}.xml"
    places_path = f"raw/places/year={year}/month={month}/places_{business_date}.xml"
    
    fetch_upload_and_parse(PRICES_URL, prices_path, bucket, 'prices', business_date)
    fetch_upload_and_parse(PLACES_URL, places_path, bucket, 'places', business_date)
    
    return "Ingestion and BigQuery Load complete.", 200
