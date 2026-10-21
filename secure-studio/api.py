"""Private G15 165-member case API. Configured secrets and private inputs REQUIRED.

No model, token, password, drawing or user identity is committed to Git.
The API fails closed unless a protected (server-side) Gate08 ZIP and secret exist.
Run behind HTTPS and deployment-level authentication, never from GitHub Pages.
"""
from __future__ import annotations
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, ConfigDict

app=FastAPI(title="JP private G15 analysis",docs_url=None,redoc_url=None,openapi_url=None)
ZIP_FILE="G15_GATE08_PRIVATE_EXECUTION_v0.1.zip"
PRIVATE_PREFIX="G15_GATE08_PRIVATE_PACKET_v0.1/"
SCRIPT=PRIVATE_PREFIX+"scripts/run_gate08_mass_calibrated.py"
MODEL=PRIVATE_PREFIX+"source_snapshot/gate03/scenario_frame.json"
PRIVATE_ZIP_SHA="c237a8a0f99bff0400969afaa77dd9c02ce77ba0718f2a5a294e522e7e5dda15"
MAX_BYTES=30*1024*1024

class Scenario(BaseModel):
    model_config=ConfigDict(extra="forbid")
    beam_width_mm:float=Field(default=304.8,ge=200,le=600)
    concrete_E_MPa:float=Field(default=22360.6798,ge=10000,le=50000)
    stiffness_state:str=Field(default="ULS",pattern="^(GROSS|ULS|SLS)$")
    diaphragm:str=Field(default="FLEXIBLE",pattern="^(FLEXIBLE|RIGID_TRIAL)$")
    wall_proxy:bool=False
    footprint_proxy:str=Field(default="COLUMN_CONVEX_HULL",pattern="^(GRID_BBOX|COLUMN_CONVEX_HULL)$")
    bridges:bool=True
    # No arbitrary path, code, shell command, or customer-provided model input.

def access(token:str|None):
    secret=os.getenv("JP_STUDIO_SERVER_TOKEN")
    if not secret or len(secret)<32 or not token or not token.startswith("Bearer "):
        raise HTTPException(503,"Private deployment authentication not configured")
    import hmac
    if not hmac.compare_digest(token[7:],secret):
        raise HTTPException(401,"Unauthorized")

def source_path():
    p=os.getenv("JP_G15_PRIVATE_ZIP_PATH")
    if not p:return None
    x=pathlib.Path(p)
    if not x.is_file() or x.stat().st_size>MAX_BYTES or x.stat().st_size<100000:
        return None
    if hashlib.sha256(x.read_bytes()).hexdigest()!=PRIVATE_ZIP_SHA:
        return None
    return x

def validate_archive(z):
    names=set(z.namelist())
    required={SCRIPT,MODEL}
    if not required.issubset(names):raise RuntimeError("Required private model missing")
    for i in z.infolist():
        pp=pathlib.PurePosixPath(i.filename)
        if pp.is_absolute() or ".." in pp.parts or not i.filename.startswith(PRIVATE_PREFIX):
            raise RuntimeError("Unsafe archive entry")
        if i.file_size>MAX_BYTES:raise RuntimeError("Oversized archive entry")

def load_model():
    path=source_path()
    if path is None:raise HTTPException(503,"Private source archive unavailable or checksum mismatch")
    with zipfile.ZipFile(path) as z:
        validate_archive(z)
        d=json.loads(z.read(MODEL))
    if len(d.get("members",[]))!=165 or len(d.get("columns",[]))!=23:
        raise HTTPException(503,"Private model validation failed")
    return d

@app.middleware("http")
async def secure_headers(request:Request,call_next):
    if request.method=="OPTIONS":return JSONResponse({"error":"cross-site access prohibited"},status_code=405)
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store"
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Content-Security-Policy"]="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    return response

@app.get("/api/status")
def status(authorization:str|None=Header(default=None)):
    access(authorization)
    d=load_model()
    return {"schema":"jp.private.g15.status.v1","members":len(d["members"]),
            "columns":len(d["columns"]),"nodes":92,
            "source_status":"WORKING_HYPOTHESIS_NOT_AS_BUILT",
            "engineering_approval":False,"F3_one_way_shear":"SOURCE_FAIL"}

@app.post("/api/analyze")
def analyze(req:Scenario,authorization:str|None=Header(default=None)):
    access(authorization)
    path=source_path()
    if path is None:raise HTTPException(503,"Private source unavailable")
    payload=req.model_dump()
    # The source physics is kept as a reproducible private Gate08 module.
    # We never execute user-provided code; all override fields are allowlisted.
    with tempfile.TemporaryDirectory(prefix="g15-private-") as td:
        root=pathlib.Path(td)
        with zipfile.ZipFile(path) as z:
            validate_archive(z)
            z.extractall(root)
        packet=root/PRIVATE_PREFIX
        args=[sys.executable,str(packet/"secure_one_case.py")]
        # A controlled small wrapper, bundled and supplied by the application
        # build, not from request input.
        wrapper=pathlib.Path(__file__).with_name("secure_one_case.py")
        if not wrapper.is_file():raise HTTPException(503,"Solver wrapper unavailable")
        (packet/"secure_one_case.py").write_bytes(wrapper.read_bytes())
        try:
            run=subprocess.run(args,input=json.dumps(payload),text=True,capture_output=True,
                               cwd=str(packet),timeout=105,check=False,env={"PATH":os.getenv("PATH",""),
                               "PYTHONPATH":str(packet/"scripts"),"HOME":td})
        except subprocess.TimeoutExpired:
            raise HTTPException(503,"Analysis time limit; reduce scenario scope")
        if run.returncode!=0:
            raise HTTPException(422,"Structural solver rejected this scenario; inspect server audit logs")
        try: result=json.loads(run.stdout)
        except ValueError:raise HTTPException(503,"Invalid solver result")
        if result.get("model_counts",{}).get("members")!=165 or not result.get("engineering_approval") is False:
            raise HTTPException(503,"Invalid model count or missing engineering HOLD")
        return result

@app.get("/")
def interface():
    return FileResponse(pathlib.Path(__file__).with_name("index.html"),
                        media_type="text/html")

@app.get("/studio.js")
def studio_script():
    return FileResponse(pathlib.Path(__file__).with_name("studio.js"),
                        media_type="text/javascript")

@app.get("/studio.css")
def studio_css():
    return FileResponse(pathlib.Path(__file__).with_name("studio.css"),
                        media_type="text/css")
