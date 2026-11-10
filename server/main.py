import io
import json
import uuid

from websockets import Response

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import tempfile

import pandas as pd

from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.objects.bpmn.exporter import exporter as bpmn_exporter
from pm4py.visualization.bpmn import visualizer as bpmn_visualizer
from pm4py.objects.bpmn.obj import BPMN
from io import BytesIO
import pm4py

from event_log_mapping import normalize_case_id_column
from event_log_store import (
    connect_to_event_log_store,
    get_event_log_dataframe,
    get_event_log_events,
    initialize_event_log_store,
    list_event_logs,
    parse_event_log_csv,
    store_event_log,
)
import mysql.connector

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET

app = FastAPI()


@app.on_event("startup")
def initialize_persistent_event_logs() -> None:
  initialize_event_log_store()

# Define the exact URL of your frontend
# If you use localhost:3000 in the browser, use localhost:3000 here.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Solves "Missing Access-Control-Allow-Origin"
    allow_credentials=True,
    allow_methods=["*"],               # Required for the 'Preflight' OPTIONS request
    allow_headers=["*"],               # Allows 'Content-Type', 'Authorization', etc.
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/")
def read_root():
  return {"hello": "World"}

@app.get("/availible-logs")
def read_availible_logs():
  files = [f for f in listdir("examples") if isfile(join("examples", f))]

  return files


@app.get("/event-log/{file_name}")
def read_event_log(file_name: str):
  df = pd.read_csv(f'examples/{file_name}')
  df = normalize_case_id_column(df)

  return df.head(50).to_dict(orient="records")

@app.get("/diagram/{file_name}")
def read_diagram(file_name: str):
  df = pd.read_csv(f'examples/{file_name}')
  df = normalize_case_id_column(df)

  # Convert the 'Timestamp' column to a datetime format
  df['Timestamp'] = pd.to_datetime(df['Timestamp'])

  # Use the exact column names from the diagnostic output
  df.rename(columns={'Case_ID': 'case:concept:name',
                    'Activity': 'concept:name',
                    'Timestamp': 'time:timestamp'}, inplace=True)

  # Convert the DataFrame to a PM4Py event log object
  event_log = log_converter.apply(df)

  bpmn_graph = pm4py.discover_bpmn_inductive(event_log)

  temp_file = tempfile.NamedTemporaryFile(
    mode='w',
    suffix='.bpmn',
    delete=False
  )

  temp_file_path = temp_file.name
  temp_file.close()

  pm4py.write_bpmn(bpmn_graph, temp_file_path)



  return FileResponse(
    path=temp_file_path,
    media_type="application/xml",
    filename="discovered_process.bpmn"
  )

@app.post("/event-log")
async def read_event_log(file: UploadFile = File(...)):
  contents = await file.read()
  df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
  df = normalize_case_id_column(df)

  return df.head(50).to_dict(orient="records")


@app.get("/event-logs")
def read_saved_event_logs():
  try:
    connection = connect_to_event_log_store()
    try:
      return list_event_logs(connection)
    finally:
      connection.close()
  except mysql.connector.Error as error:
    raise HTTPException(status_code=503, detail="Event-log storage is unavailable") from error


@app.post("/event-logs", status_code=status.HTTP_201_CREATED)
async def import_event_log(file: UploadFile = File(...)):
  contents = await file.read()
  try:
    events = parse_event_log_csv(contents)
  except ValueError as error:
    raise HTTPException(status_code=400, detail=str(error)) from error

  try:
    connection = connect_to_event_log_store()
    try:
      event_log_id = store_event_log(connection, file.filename or "uploaded.csv", events)
    finally:
      connection.close()
  except mysql.connector.Error as error:
    raise HTTPException(status_code=503, detail="Unable to save the uploaded event log") from error

  return {
    "id": event_log_id,
    "name": file.filename or "uploaded.csv",
    "event_count": len(events),
  }


@app.get("/event-logs/{event_log_id}/events")
def read_saved_event_log_events(event_log_id: int):
  try:
    connection = connect_to_event_log_store()
    try:
      events = get_event_log_events(connection, event_log_id)
    finally:
      connection.close()
  except mysql.connector.Error as error:
    raise HTTPException(status_code=503, detail="Event-log storage is unavailable") from error
  if events is None:
    raise HTTPException(status_code=404, detail="Saved event log not found")
  return events


def create_diagram_response(df: pd.DataFrame):
  df = df.copy()
  df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True)
  role_to_activities = (
      df.groupby("Role")["Activity"]
      .apply(set)
      .to_dict()
  )

  df.rename(
      columns={
          "Case_ID": "case:concept:name",
          "Activity": "concept:name",
          "Timestamp": "time:timestamp",
      },
      inplace=True,
  )
  event_log = log_converter.apply(df)
  bpmn_graph = pm4py.discover_bpmn_inductive(event_log)

  temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".bpmn", delete=False)
  temp_file_path = temp_file.name
  temp_file.close()
  pm4py.write_bpmn(bpmn_graph, temp_file_path)

  role_map_json = json.dumps(
      {role: list(activities) for role, activities in role_to_activities.items()}
  )
  tree = ET.parse(temp_file_path)
  root = tree.getroot()
  bpmn_ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
  process_el = root.find(f"{{{bpmn_ns}}}process")
  if process_el is None:
    raise RuntimeError("Generated BPMN does not contain a process element")
  process_el.set("data-role-map", role_map_json)
  tree.write(temp_file_path, xml_declaration=True, encoding="unicode")

  return FileResponse(
      path=temp_file_path,
      media_type="application/xml",
      filename="discovered_process.bpmn",
  )


@app.get("/event-logs/{event_log_id}/diagram")
def create_saved_event_log_diagram(event_log_id: int):
  try:
    connection = connect_to_event_log_store()
    try:
      df = get_event_log_dataframe(connection, event_log_id)
    finally:
      connection.close()
  except mysql.connector.Error as error:
    raise HTTPException(status_code=503, detail="Event-log storage is unavailable") from error
  if df is None:
    raise HTTPException(status_code=404, detail="Saved event log not found")
  return create_diagram_response(df)


@app.post("/diagram")
async def create_diagram(file: UploadFile = File(...)):
  contents = await file.read()
  df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
  df = normalize_case_id_column(df)
  return create_diagram_response(df)
