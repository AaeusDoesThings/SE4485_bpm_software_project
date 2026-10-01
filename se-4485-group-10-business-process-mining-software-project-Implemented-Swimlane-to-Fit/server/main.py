import io
import json
import uuid

from websockets import Response

from fastapi import FastAPI, File, UploadFile
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

from os import listdir
from os.path import isfile, join

import xml.etree.ElementTree as ET

app = FastAPI()

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

  return df.head(50).to_dict(orient="records")

@app.get("/diagram/{file_name}")
def read_diagram(file_name: str):
  df = pd.read_csv(f'examples/{file_name}')

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

  return df.head(50).to_dict(orient="records")

@app.post("/diagram")
async def create_diagram(file: UploadFile = File(...)):
  contents = await file.read()
  df = pd.read_csv(io.StringIO(contents.decode('utf-8')))

  # Convert the 'Timestamp' column to a datetime format
  df['Timestamp'] = pd.to_datetime(df['Timestamp'])

  role_to_activities = (
        df.groupby('Role')['Activity']
        .apply(set)
        .to_dict()
    )
  

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

  # Serialize roleToActivities with list values for JSON embedding
  role_map_json = json.dumps({
      role: list(activities)
      for role, activities in role_to_activities.items()
  })

  tree = ET.parse(temp_file_path)
  root = tree.getroot()
  BPMN_NS = 'http://www.omg.org/spec/BPMN/20100524/MODEL'

  process_el = root.find(f'{{{BPMN_NS}}}process')

  # Embed role map as a custom attribute — the frontend reads this to
  # know which activities belong to which lane before injecting lanes
  process_el.set('data-role-map', role_map_json)

  tree.write(temp_file_path, xml_declaration=True, encoding='unicode')

  return FileResponse(
    path=temp_file_path,
    media_type="application/xml",
    filename="discovered_process.bpmn"
  )
