"""
Folliscope — Sistem Peringatan Kebotakan Dini berbasis Computational Biology
Entry point: uvicorn main:app --reload
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router

app = FastAPI(
    title="Folliscope API",
    description="Sistem Peringatan Kebotakan Dini berbasis Computational Biology",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
frontend_dir = os.path.join(BASE_DIR, "frontend")
sample_data_dir = os.path.join(BASE_DIR, "sample_data")

# ── 1. API routes — harus didaftarkan paling awal ─────────────────────────────
app.include_router(router)

# ── 2. HTML page routes (clean URL tanpa .html) ───────────────────────────────
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/analyze")
async def serve_analyze():
    return FileResponse(os.path.join(frontend_dir, "analyze.html"))

@app.get("/about")
async def serve_about():
    return FileResponse(os.path.join(frontend_dir, "about.html"))

@app.get("/database")
async def serve_database():
    return FileResponse(os.path.join(frontend_dir, "database.html"))

# ── 3. Static mounts — harus paling bawah (catch-all terakhir) ───────────────
# /sample_data/* → file FASTA & TSV contoh (dipakai tombol "Sample Data" di JS)
if os.path.exists(sample_data_dir):
    app.mount("/sample_data", StaticFiles(directory=sample_data_dir), name="sample_data")

# / catch-all → melayani css/, js/, *.html, font, dll.
# Harus SETELAH semua route eksplisit di atas agar /api/* dan /about tidak tertimpa.
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
