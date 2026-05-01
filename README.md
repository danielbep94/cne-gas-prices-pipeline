# ⛽ Mexico Gas Prices - Serverless Data Pipeline

![Google Cloud](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?style=for-the-badge&logo=google&logoColor=white)
![Cloud Functions](https://img.shields.io/badge/Cloud_Functions-000000?style=for-the-badge&logo=google-cloud&logoColor=white)

An automated, serverless, and idempotent data pipeline engineered to ingest, clean, enrich, and store daily gasoline prices from Mexico's Comisión Nacional de Energía (CNE).

## 🏗️ Architecture Overview

The pipeline implements a **Medallion Data Architecture (Bronze -> Silver)** entirely within the Google Cloud ecosystem, optimizing for zero-maintenance overhead and automatic scaling.

```mermaid
graph TD;
    A[CNE Government XML] -->|Extract| B(Cloud Function);
    C[Cloud Scheduler 2:00 AM] -->|Trigger| B;
    B -->|Backup Raw XML| D[Cloud Storage Data Lake];
    B -->|Parse & WRITE_APPEND| E[(BigQuery: Bronze Layer)];
    F[Official WGS84 GeoJSON] -->|Upload| G[(BigQuery: Spatial Dimension)];
    E -->|QUALIFY ROW_NUMBER & ST_CONTAINS| H[(BigQuery: Silver Layer View)];
    G -->|Geospatial Join| H;
    H -->|Query| I[Analytics & Dashboards];