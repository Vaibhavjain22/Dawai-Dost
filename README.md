# 💊 Dawai Dost (दवाई दोस्त)
### *India's Multimodal AI Prescription Companion — Powered by Sarvam AI*

[![Sarvam AI](https://img.shields.io/badge/Powered%20By-Sarvam%20AI-0d9488.svg)](https://sarvam.ai)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Indic Languages](https://img.shields.io/badge/Languages-11%2B%20Indic-orange.svg)](#supported-languages)

---

## 📖 Overview

**Dawai Dost (दवाई दोस्त)** is an agentic, multimodal healthcare assistant designed to bridge India’s prescription literacy gap. Patients and caregivers in India frequently struggle to decipher handwritten prescriptions, complex dosage schedules (*1-0-1*, *before/after food*), potential drug-drug interactions, and expensive brand names.

With **Dawai Dost**, users can:
1. 📷 **SHOW** their prescription photo (OPD slip, discharge summary, or doctor's note).
2. 🎙️ **SPEAK** their questions in Hindi, English, or any of 10+ Indian languages directly through their microphone.
3. 💬 **READ** a clear, empathetic explanation phrased responsibly as *"What the label usually says"*.
4. 🔊 **LISTEN** to a natural spoken audio response in their mother tongue.
5. 📅 **VIEW** an interactive **Daily Medicine Timeline** categorized into Morning (सुबह), Afternoon (दोपहर), and Night (रात) schedules.
6. 💰 **SAVE** 50% to 90% on medical expenses through **Pradhan Mantri Jan Aushadhi (PMBJP)** generic medicine recommendations.

---

## 🌟 Key Features & Multimodal Stack

| Modality | Technology / Sarvam API | Functionality |
| :--- | :--- | :--- |
| **Image In** | **Sarvam DocAI / Vision 1.5** | High-accuracy Indic OCR and schema-based medicine extraction from prescription photos. |
| **Voice In** | **Sarvam Saaras v3 STT** | Browser `MediaRecorder` audio recording with automatic Indic language identification. |
| **Text In** | Text Box Fallback | Fallback for typing queries, equipped with instant quick-prompt chips. |
| **Agent Reasoning** | **Sarvam-105B Conversations** | Multi-step agentic tool-calling loop (reasoning trace, safety lookups, interaction checks). |
| **Translation** | **Sarvam Mayura v1** | Context-preserving translation across 11 Indian languages. |
| **Voice Out** | **Sarvam Bulbul v3 TTS** | Fluid Indic medical voice synthesis (`ritu`), with automatic sentence chunking & WAV stitching for continuous playback. |
| **Visual Out** | Custom Interactive Timeline | Structured Morning 🌅 / Afternoon ☀️ / Night 🌙 schedule with emojis, timings, and purpose. |

---

## 🧠 Visible Agentic Architecture

Dawai Dost employs an explicit tool-calling reasoning loop (`agent.py`). Every decision made by the model is logged and returned in the `tool_trace` accordion for full transparency:

```
                      [ User Input: Image / Voice / Text ]
                                      │
                                      ▼
                        [ Dawai Dost Agent Loop ]
                     (Powered by Sarvam-105B Model)
                                      │
         ┌───────────────┬────────────┴────────────┬───────────────┐
         ▼               ▼                         ▼               ▼
 ┌──────────────┐ ┌──────────────┐         ┌──────────────┐ ┌──────────────┐
 │ extract_meds │ │ lookup_drug  │         │ check_inter  │ │ find_generic │
 │ (Schema OCR) │ │ (drugs.json) │         │ (Interactions│ │(Jan Aushadhi)│
 └──────────────┘ └──────────────┘         └──────────────┘ └──────────────┘
         │               │                         │               │
         └───────────────┴────────────┬────────────┴───────────────┘
                                      │
                                      ▼
                           [ Safety & Escalation ]
                     (Flags pregnancy, child, risks)
                                      │
                                      ▼
                    [ Visual Timeline & Bulbul TTS Voice ]
```

### Deterministic Tool Layer (`tools.py`):
- `extract_medicines(input)`: Validates and normalizes raw medicine entries into `{name, strength, frequency, duration}`.
- `lookup_drug(name)`: Queries a curated clinical database of ~20 common Indian drugs (Dolo 650, Pan 40, Azithral, Augmentin, Cetzine, Metformin, etc.) for dosage timing and precautions.
- `check_interaction(drug_a, drug_b)`: Identifies dangerous cross-reactions (e.g. NSAID duplication like Ibuprofen + Paracetamol).
- `find_generic(name)`: Maps branded formulations to government Jan Aushadhi generic alternatives.
- `build_timeline(medicines)`: Assembles medicines into structured morning, afternoon, and night cards.
- `escalate(reason)`: Immediately triggers doctor/pharmacist advisories and National Health Helpline **1075** details for high-risk queries.

---

## 📁 Repository Structure

```
Dawai-Dost/
├── .env.example          # Template for environment configuration
├── .gitignore            # Git exclusions (.env, __pycache__, etc.)
├── drugs.json            # Reference database of ~20 common Indian drugs & interactions
├── tools.py              # 6 deterministic tools (lookup, interactions, timeline, generics)
├── sarvam_client.py      # Modular SDK wrappers for Saaras STT, Bulbul TTS, Mayura, 105B
├── agent.py              # Multi-step Agent tool-calling loop (max 5 steps + trace)
├── main.py               # FastAPI backend + Pydantic models + CORS + static hosting
├── README.md             # Project documentation
└── static/
    └── index.html        # Modern single-page responsive UI (Vanilla HTML, CSS, JS)
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed
- A valid [Sarvam AI API Key](https://sarvam.ai)

### 2. Clone Repository
```bash
git clone https://github.com/Vaibhavjain22/Dawai-Dost.git
cd Dawai-Dost
```

### 3. Install Dependencies
```bash
pip install sarvamai fastapi uvicorn python-multipart
```

### 4. Configure Environment
Create a `.env` file in the root directory:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
```
*(Never commit `.env` to version control; it is gitignored by default).*

### 5. Launch Application
Start the development server:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 🎮 How to Demo

1. **1-Click Demo**:
   - Tap the **"✨ Try Demo Mode"** button in the header.
   - Instantly loads a realistic clinical prescription (`Pan 40`, `Dolo 650`, `Azithral 500`, `Cetzine`) with a Hindi voice query.
   - Watches the agent construct the daily timeline and starts voice playback.

2. **Prescription Image Upload**:
   - Drag and drop an OPD prescription or discharge paper.
   - Click **"Extract Medicines with Sarvam Vision"**.
   - Review and adjust detected medicines in the confirmation list before analyzing.

3. **Live Microphone Recording**:
   - Tap the large circular microphone icon.
   - Speak in Hindi, English, Bengali, Tamil, Telugu, etc. (e.g. *"मुझे ये दवाइयां कब और कैसे लेनी हैं?"*).
   - Sarvam Saaras transcribes and answers via Sarvam Bulbul voice.

---

## 🌐 Supported Languages

Dawai Dost supports 11 primary Indian languages for Speech Synthesis and Translation:

| Language | Native Script | TTS Voice Model |
| :--- | :--- | :--- |
| **Hindi** | हिन्दी | Bulbul v3 (`ritu`) |
| **English (Indian)** | English | Bulbul v3 (`neha`) |
| **Bengali** | বাংলা | Bulbul v3 (`roopa`) |
| **Tamil** | தமிழ் | Bulbul v3 (`vijay`) |
| **Telugu** | తెలుగు | Bulbul v3 (`kavitha`) |
| **Marathi** | मराठी | Bulbul v3 (`ishita`) |
| **Gujarati** | ગુજરાતી | Bulbul v3 (`pooja`) |
| **Kannada** | ಕನ್ನಡ | Bulbul v3 (`mani`) |
| **Malayalam** | മലയാളം | Bulbul v3 (`priya`) |
| **Punjabi** | ਪੰਜਾਬੀ | Bulbul v3 (`anand`) |
| **Odia** | ଓଡ଼ିଆ | Bulbul v3 (`shreya`) |

---

## 🔒 Safety & Medical Disclaimer

> **⚠️ IMPORTANT NOTICE:**
> Dawai Dost is an educational and informational AI prototype designed to assist patients in understanding their doctor's prescription. It **does NOT diagnose diseases, prescribe personal dosages, or replace professional medical advice**. 
> 
> - All guidance is framed strictly as *"What the label usually says"*.
> - For emergencies, high-risk conditions, pregnancy, or pediatric care, always consult a licensed doctor or call the **National Health Helpline: 1075**.

---

## 🤝 Contributing & License

Contributions are welcome! Please feel free to submit a Pull Request.
This project is open source and available under the [MIT License](LICENSE).
