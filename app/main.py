#!/usr/bin/env python3

from pathlib import Path
import traceback

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from werkzeug.utils import secure_filename

from .cashflow import cashflow

SMOKE_TEST = False
WORKDIR = Path.cwd() / "app" if SMOKE_TEST else Path("/code")
UPLOAD_DIR = WORKDIR / "upload"
STATIC_DIR = WORKDIR / "static"
TMPLT_DIR = WORKDIR / "templates"
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

app = FastAPI()
app.mount(str(STATIC_DIR), StaticFiles(directory=STATIC_DIR), name="static")
app.mount(
    str(TMPLT_DIR),
    StaticFiles(directory=TMPLT_DIR),
    name="templates",
)
templates = Jinja2Templates(directory=TMPLT_DIR)


@app.exception_handler(RequestValidationError)
async def http_exception_handler(request: Request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/display/")
async def display(request: Request, file: UploadFile = File(...)):
    def _allowed_file(filename):
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    if _allowed_file(file.filename):
        try:
            contents = await file.read()
            filename = secure_filename(file.filename)
            filename = UPLOAD_DIR / filename
            print(filename)
            with open(filename, "wb") as f:
                f.write(contents)
        except Exception:
            return templates.TemplateResponse(
                "error.html", {"request": request, "error": traceback.format_exc()}
            )
        finally:
            await file.close()
        plot, transactions = cashflow(filename, jsonflag=True)
        return templates.TemplateResponse(
            "display.html",
            {"request": request, "plot": plot, "transactions": transactions},
        )
