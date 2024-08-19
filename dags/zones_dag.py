from __future__ import annotations
from datetime import datetime
from airflow.models.dag import DAG
from airflow.decorators import task
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
import time
import pyodbc
import json
import os
import pendulum
import xml.etree.ElementTree as ET
import pandas as pd

def polygons(root):
    polygon_lst = []
    coordinate_lst = [] 
    # Loops through the "polygons" tag in zones.xml
    for item in root[0].iter():
        if item.attrib:
            polygon_lst.append(item.attrib)
        for sub_item in item:
            if len(sub_item.text) > 7: # Filters out empty strings with length of 7
                coordinate_lst.append(str(sub_item.text))
    # Creates data frame to structure XML data
    df = pd.DataFrame(polygon_lst, columns=['name', 'guid', 'capacity'])
    df.loc[:,"coordinates"] = coordinate_lst # Adds coordinates column to DataFrame
    return df

def permits(root):
    permit_lst = []
    # Loops through the "permits" tag in zones.xml
    for item in root[1].iter():
        if item.attrib:
            permit_lst.append(item.attrib)
    # Creates DataFrame to structure XML data
    df = pd.DataFrame(permit_lst, columns=['name', 'guid'])
    return df

def zones(root):
    row_dict = {}
    rows_lst = []
    zone = ['name', 'guid', 'isOvertime']
    polygon = ""
    zone_dict = {}
    # Loops through the "zones" tag in zones.xml
    for item in root[2].iter():
        permit = ['color', 'names', 'hours', 'days', 'validityRange', 'polygons']
        permit_dict = dict.fromkeys(permit)
        polygon_dict = {}
        # Verifies not an emty XML tag
        if item.attrib:
            item_lst = list(item.attrib.keys())
            for sub_item in item:
                if sub_item.text:
                    polygon = sub_item.text

            if isZone(item_lst):
                zone_dict = dict.fromkeys(zone)
                zone_dict.update({'name' : item.attrib.get("name")})
                zone_dict.update({'guid' : item.attrib.get("guid")})
                zone_dict.update({'isOvertime' : item.attrib.get("isOvertime")})
                row_dict.update(zone_dict)
            
            if isPermitRestriction(item_lst):
                polygon_dict.update(row_dict.copy())
                polygon_dict.update(permit_dict.copy())
                polygon_dict.update({'polygons' : polygon})
                permit_dict.update({'color' : item.attrib.get("color")})
                row_dict.update(permit_dict)
                rows_lst.append(row_dict.copy())
                rows_lst.append(polygon_dict.copy())

            if isPermit(item_lst):
                permit_dict = dict.fromkeys(permit)
                permit_dict.update({'names' : item.attrib.get("names")})
                permit_dict.update({'hours' : item.attrib.get("hours")})
                permit_dict.update({'days' : item.attrib.get("days")})
                permit_dict.update({'validityRange' : item.attrib.get("validityRange")})
                row_dict.update(permit_dict)
                rows_lst.append(row_dict.copy())

    # Creates DataFrame to structure XML data
    df = pd.DataFrame(rows_lst, columns=['name', 'guid', 'isOvertime', 'color', 'names', 'hours', 'days', 'validityRange', 'polygons'])
    return df

def isZone(lst):
    if lst[0] == 'name':
        return True
    else:
        return False

def isPermitRestriction(lst):
    if lst[0] == 'color':
        return True
    else:
        return False

def isPermit(lst):
    if lst[0] == 'names':
        return True
    else:
        return False

# [START instantiate_dag]
with DAG(
    "zones_dag",
    # [START default_args]
    # These args will get passed on to each operator
    # You can override them on a per-task basis during operator initialization
    default_args={"retries": 2},
    # [END default_args]
    description="Zone.xml DAG",
    schedule=None,
    start_date=pendulum.datetime(2024, 6, 25, tz="UTC"),
    catchup=False,
    tags=["LPR"],
) as dag:
# [END instantiate_dag]

    # [START documentation]
    dag.doc_md = __doc__
    # [END documentation]

    # [START extract_function]
    @task()
    def extract(**context):
        """
        ### Extract task
        A simple extract task which reads an xml file from a mounted 
        drive and parses the XML to a Element Tree.
        """
        #Pass the path of the xml document
        #The document (zones.xml) is NOT in this GitHub project. 
        print("Reading Document...")
        try:
            file_path = '/opt/airflow/drives/zones.xml'
            tree = ET.parse(file_path)
            xml_str = ET.tostring(tree.getroot(), encoding='unicode')
        except Exception as e:
            print(f"Debug: Failed to read the document: {e}")
            return f"Error: {e}"
        
        return xml_str
    # [END extract_function]

    # [START transform_function]
    @task
    def transform(xml_str: str, **contex):
        """
        ### Transform task
        A simple transform task which traverses an Element Tree
        and loads each element into a dataframe. The dataframes are stored in a list.
        """
        root = ET.fromstring(xml_str)
        df_list = []
        #transforms from xml -> dataframe
        poly_df = polygons(root)
        permits_df = permits(root)
        zones_df = zones(root)
        #add all df to a list
        df_list.append(poly_df)
        df_list.append(permits_df)
        df_list.append(zones_df)
        return df_list
    # [END transform_function]

    # [START load_function]
    @task
    def load(df_list):
        poly_df = pd.DataFrame.from_dict(df_list[0])
        permits_df = pd.DataFrame.from_dict(df_list[1])
        zones_df = pd.DataFrame.from_dict(df_list[2])

        mssql_hook = MsSqlHook(mssql_conn_id='[INSERT_SERVER_NAME]', schema='LorenzoTest')

        # Truncate the tables before inserting new data
        mssql_hook.run("TRUNCATE TABLE polygons")
        mssql_hook.run("TRUNCATE TABLE permits")
        mssql_hook.run("TRUNCATE TABLE zones")

        # Create and populate polygons table
        mssql_hook.run("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'polygons')
            CREATE TABLE polygons (
                name NVARCHAR(MAX),
                guid NVARCHAR(MAX),
                capacity NVARCHAR(MAX),
                coordinates NVARCHAR(MAX)
            )
        """)
        mssql_hook.insert_rows(table='polygons', rows=poly_df.values.tolist(), target_fields=poly_df.columns.tolist())

        # Create and populate permits table
        mssql_hook.run("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'permits')
            CREATE TABLE permits (
                name NVARCHAR(MAX),
                guid NVARCHAR(MAX)
            )
        """)
        mssql_hook.insert_rows(table='permits', rows=permits_df.values.tolist(), target_fields=permits_df.columns.tolist())

        # Create and populate zones table
        mssql_hook.run("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'zones')
            CREATE TABLE zones (
                name NVARCHAR(MAX),
                guid NVARCHAR(MAX),
                isOvertime NVARCHAR(MAX),
                color NVARCHAR(MAX),
                names NVARCHAR(MAX),
                hours NVARCHAR(MAX),
                days NVARCHAR(MAX),
                validityRange NVARCHAR(MAX),
                polygons NVARCHAR(MAX)
            )
        """)
        mssql_hook.insert_rows(table='zones', rows=zones_df.values.tolist(), target_fields=zones_df.columns.tolist())
    # [END load_function]

    # [START main_flow]
    element_tree = extract()
    df_list = transform(element_tree)
    load(df_list)

# [END main_flow]
