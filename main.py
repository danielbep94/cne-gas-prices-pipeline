import functions_framework
import requests
import pytz
from datetime import datetime, timedelta
from google.cloud import storage
import os
import logging

logging.basicConfig(level=logging.INFO)

PRICES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
PLACES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/places"
BUCKET_NAME = os.environ.get("BUCKET_NAME")

def get_business_date() -> str:
    cdmx_tz = pytz.timezone('America/Mexico_City')
    now_cdmx = datetime.now(cdmx_tz)

    # CNE updates at 18:00 hrs. If running at 02:00 AM, fetch yesterday's date.
    if now_cdmx.hour < 18:
        business_date = (now_cdmx - timedelta(days=1)).date()
    else:
        business_date = now_cdmx.date()

    return business_date.strftime('%Y-%m-%d')

def fetch_and_upload(url: str, blob_path: str, bucket):
    logging.info(f"Fetching {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        blob = bucket.blob(blob_path)
        blob.upload_from_string(response.content, content_type='application/xml')
        logging.info(f"Successfully uploaded to gs://{bucket.name}/{blob_path}")

    except Exception as e:
        logging.error(f"Failed to process {url}: {e}")
        raise

@functions_framework.http
def ingest_cne_data(request):
    if not BUCKET_NAME:
        return "BUCKET_NAME environment variable not set.", 500

    business_date = get_business_date()
    logging.info(f"Starting ingestion for business date: {business_date}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    # Partitioning format: raw/type/year=YYYY/month=MM/file.xml
    year = business_date[:4]
    month = business_date[5:7]

    prices_path = f"raw/prices/year={year}/month={month}/prices_{business_date}.xml"
    places_path = f"raw/places/year={year}/month={month}/places_{business_date}.xml"

    fetch_and_upload(PRICES_URL, prices_path, bucket)
    fetch_and_upload(PLACES_URL, places_path, bucket)

    return "Ingestion complete.", 200