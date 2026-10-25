import os
import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Load .env first
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and val:
                    os.environ[key] = val

from sarvam_client import (
    transcribe_audio,
    text_to_speech,
    translate_text,
    extract_prescription_with_vision,
    LANGUAGES
)
from agent import DawaiDostAgent

app = FastAPI(
    title="Dawai Dost API",
    description="Multimodal Indic AI Prescription Assistant powered by Sarvam AI",
    version="1.0.0"
)

# CORS middleware for seamless local and preview testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent
agent = DawaiDostAgent(max_steps=5)

# --- Pydantic Models ---

class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: Optional[float] = 1.0

class MedicineItem(BaseModel):
    name: str
    strength: Optional[str] = "Standard"
    frequency: Optional[str] = "As prescribed"
    duration: Optional[str] = "Full course"

class ExtractResponse(BaseModel):
    medicines: List[Dict[str, Any]]
    count: int

class ChatRequest(BaseModel):
    text: str
    language: str = "hi-IN"
    medicines: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    reply_text: str
    tool_trace: List[Dict[str, Any]]
    timeline: Optional[Dict[str, Any]] = None
    escalated: bool = False

class SpeakRequest(BaseModel):
    text: str
    language: str = "hi-IN"

class SpeakResponse(BaseModel):
    audio_base64: Optional[str] = None
    language: str

class DemoResponse(BaseModel):
    sample_query: str
    sample_medicines: List[Dict[str, Any]]
    sample_language: str
    description: str

# --- Endpoints ---

@app.post("/api/transcribe", response_model=TranscribeResponse)
async def api_transcribe(
    file: UploadFile = File(...),
    language: str = Form("unknown")
):
    """
    Transcribes spoken voice audio (browser MediaRecorder or uploaded file)
    using Sarvam Saaras with automatic Indic language detection.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio recording received.")

        result = transcribe_audio(
            file_bytes_or_path=content,
            language_code=language if language in LANGUAGES else "unknown"
        )
        return TranscribeResponse(
            text=result.get("transcript", ""),
            language=result.get("language_code", "hi-IN"),
            confidence=result.get("language_probability", 1.0)
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Voice transcription failed gracefully: {str(e)}", "text": "", "language": "hi-IN"}
        )

@app.post("/api/extract", response_model=ExtractResponse)
async def api_extract(file: UploadFile = File(...)):
    """
    Upload prescription image -> extracts structured medicines list using Sarvam DocAI / Vision.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty image uploaded.")

        medicines = extract_prescription_with_vision(
            file_bytes=content,
            filename=file.filename or "prescription.jpg"
        )
        return ExtractResponse(medicines=medicines, count=len(medicines))
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Prescription extraction fallback engaged: {str(e)}",
                "medicines": [
                    {"name": "Dolo 650", "strength": "650mg", "frequency": "1-0-1 after food", "duration": "3 days"},
                    {"name": "Pan 40", "strength": "40mg", "frequency": "1-0-0 empty stomach", "duration": "5 days"}
                ],
                "count": 2
            }
        )

@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """
    Agentic reasoning loop: LLM decides tool sequence, looks up drugs,
    verifies interactions, generates daily timeline, and produces safety-checked response.
    """
    try:
        result = agent.run(
            user_query=req.text,
            medicines=req.medicines or [],
            language=req.language or "hi-IN"
        )
        return ChatResponse(
            reply_text=result["reply_text"],
            tool_trace=result["tool_trace"],
            timeline=result["timeline"],
            escalated=result["escalated"]
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "reply_text": "नमस्ते! कृपया इन दवाओं को डॉक्टर द्वारा बताए गए समय पर ही लें। अधिक जानकारी के लिए अपने फार्मासिस्ट से संपर्क करें।",
                "tool_trace": [{"step": 1, "tool": "fallback", "summary": f"Recovered from error: {str(e)}"}],
                "timeline": None,
                "escalated": True
            }
        )

@app.post("/api/speak", response_model=SpeakResponse)
async def api_speak(req: SpeakRequest):
    """
    Converts text explanation into spoken Indic audio via Sarvam Bulbul.
    Returns base64 audio string to play directly in browser.
    """
    try:
        audio_b64 = text_to_speech(
            text=req.text,
            language_code=req.language or "hi-IN"
        )
        return SpeakResponse(
            audio_base64=audio_b64,
            language=req.language or "hi-IN"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"TTS synthesis error: {str(e)}", "audio_base64": None, "language": req.language}
        )

@app.get("/api/demo", response_model=DemoResponse)
async def api_demo():
    """
    Returns realistic sample prescription and Hindi query for instant 1-click live demo.
    """
    return DemoResponse(
        sample_query="डॉक्टर साहब, ये पर्ची मुझे समझाइए। ये दवाइयाँ मुझे कब और कैसे लेनी हैं? क्या कोई दवा खाली पेट लेनी है?",
        sample_medicines=[
            {
                "name": "Pan 40",
                "strength": "40mg",
                "frequency": "1-0-0 (सुबह खाली पेट / Before Breakfast)",
                "duration": "5 days"
            },
            {
                "name": "Dolo 650",
                "strength": "650mg",
                "frequency": "1-0-1 (सुबह व रात खाने के बाद / After Meals)",
                "duration": "3 days"
            },
            {
                "name": "Azithral 500",
                "strength": "500mg",
                "frequency": "0-0-1 (रात को खाने के बाद / After Dinner)",
                "duration": "3 days"
            },
            {
                "name": "Cetzine",
                "strength": "10mg",
                "frequency": "0-0-1 (रात को सोते समय / Bedtime)",
                "duration": "5 days"
            }
        ],
        sample_language="hi-IN",
        description="Sample clinical prescription for acute fever, throat infection, and acidity."
    )

# Static directory and frontend serving
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        response = HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return HTMLResponse("<h1>Dawai Dost Frontend is loading...</h1>")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
