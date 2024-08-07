# Apache Airflow ETL with MS SQL Integration

This repository showcases an ETL (Extract, Transform, Load) process using Apache Airflow, aimed at demonstrating my capabilities as a data engineer. The project includes custom Docker configurations to set up the environment, and an Airflow DAG that extracts data from an XML file, transforms it into structured data, and loads it into an MS SQL database.

## Features

- **Custom Docker Setup**: Utilizes a custom Dockerfile to install necessary Python dependencies and extends the official Apache Airflow image through a Docker Compose file.
- **ETL Process**: Implements an Airflow DAG that:
  - Extracts data from an XML file.
  - Transforms the XML data into pandas DataFrames.
  - Loads the transformed data into an MS SQL database.
- **Python Scripts**: Includes Python scripts for handling XML data and interacting with the MS SQL database.

## Repository Structure

- **Dockerfile**: Custom Dockerfile to set up the Airflow environment with required Python dependencies.
- **docker-compose.yaml**: Docker Compose file to configure and extend the official Apache Airflow image.
- **dags/**: Contains the main Airflow DAG script for the ETL process.
- **scripts/**: Python scripts for data extraction, transformation, and loading.

## Airflow DAG

The main DAG (`zones_dag`) is structured as follows:

1. **Extract Task**: Reads an XML file from a mounted drive and parses it into an Element Tree.
2. **Transform Task**: Converts the parsed XML data into pandas DataFrames for each relevant section (polygons, permits, and zones).
3. **Load Task**: Inserts the transformed data into corresponding tables in an MS SQL database.

### Code Snippet

```python
from datetime import datetime
from airflow.models.dag import DAG
from airflow.decorators import task
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
import pandas as pd
import xml.etree.ElementTree as ET

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    return root

def extract_polygons(root):
    # Extraction logic for polygons
    pass

def extract_permits(root):
    # Extraction logic for permits
    pass

def extract_zones(root):
    # Extraction logic for zones
    pass

with DAG(
    "zones_dag",
    default_args={"retries": 2},
    description="ETL DAG for zones.xml",
    schedule_interval=None,
    start_date=datetime(2024, 6, 25),
    catchup=False,
    tags=["example"],
) as dag:

    @task()
    def extract():
        root = parse_xml('/opt/airflow/drives/zones.xml')
        return root

    @task()
    def transform(root):
        poly_df = extract_polygons(root)
        permits_df = extract_permits(root)
        zones_df = extract_zones(root)
        return [poly_df, permits_df, zones_df]

    @task()
    def load(dataframes):
        mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
        # Loading logic
        pass

    root = extract()
    dataframes = transform(root)
    load(dataframes)
