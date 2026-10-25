import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DRUGS_FILE = Path(__file__).resolve().parent / "drugs.json"
_DB: Dict[str, Any] = {}

def load_drugs_db() -> Dict[str, Any]:
    global _DB
    if not _DB and DRUGS_FILE.exists():
        with open(DRUGS_FILE, "r", encoding="utf-8") as f:
            _DB = json.load(f)
    return _DB

def _normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name.lower())
    # Common variations map
    variations = {
        "dolo": "paracetamol",
        "dolo650": "paracetamol",
        "crocin": "paracetamol",
        "calpol": "paracetamol",
        "pan": "pantoprazole",
        "pan40": "pantoprazole",
        "pand": "pantoprazole",
        "pantocid": "pantoprazole",
        "azithral": "azithromycin",
        "azee": "azithromycin",
        "augmentin": "amoxicillin",
        "amox": "amoxicillin",
        "cetzine": "cetirizine",
        "okacet": "cetirizine",
        "glycomet": "metformin",
        "amlong": "amlodipine",
        "stamlo": "amlodipine",
        "brufen": "ibuprofen",
        "combiflam": "ibuprofen",
        "electral": "ors",
        "walyte": "ors",
        "montek": "montelukast",
        "monair": "montelukast",
        "telma": "telmisartan",
        "atorva": "atorvastatin",
        "o2": "ofloxacin",
        "vomitstop": "domperidone",
        "domstal": "domperidone",
        "rantac": "ranitidine",
        "thyronorm": "levothyroxine",
        "voveran": "diclofenac",
        "calcirol": "vitamin_d3",
        "ascoril": "cough_syrup",
        "benadryl": "cough_syrup"
    }
    for word in cleaned.split():
        if word in variations:
            return variations[word]
    for key in variations:
        if key in cleaned:
            return variations[key]
    return cleaned

def extract_medicines(input_data: Any) -> List[Dict[str, str]]:
    """Validates and normalizes extracted medicine list."""
    results = []
    if isinstance(input_data, str):
        # Try JSON parsing
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, list):
                input_data = parsed
            elif isinstance(parsed, dict) and "medicines" in parsed:
                input_data = parsed["medicines"]
        except Exception:
            # Fallback regex extraction from free text
            lines = [l.strip() for l in input_data.splitlines() if l.strip()]
            for line in lines:
                parts = line.split("-") if "-" in line else line.split(",")
                name = parts[0].strip()
                freq = parts[1].strip() if len(parts) > 1 else "1-0-1"
                results.append({
                    "name": name,
                    "strength": "Standard",
                    "frequency": freq,
                    "duration": "As advised"
                })
            return results

    if isinstance(input_data, list):
        for item in input_data:
            if isinstance(item, dict):
                results.append({
                    "name": str(item.get("name", "Unknown Medicine")).strip(),
                    "strength": str(item.get("strength", "Standard")).strip(),
                    "frequency": str(item.get("frequency", "As directed by physician")).strip(),
                    "duration": str(item.get("duration", "Full prescribed course")).strip()
                })
            elif isinstance(item, str):
                results.append({
                    "name": item.strip(),
                    "strength": "Standard",
                    "frequency": "As directed",
                    "duration": "Full course"
                })
    return results

def lookup_drug(name: str) -> Dict[str, Any]:
    """
    Looks up drug details from local database of ~20 common Indian medicines.
    Phased responsibly as 'label usually says'.
    """
    db = load_drugs_db()
    drugs = db.get("drugs", {})
    norm_key = _normalize_name(name)

    # 1. Exact match on normalized key
    if norm_key in drugs:
        data = drugs[norm_key]
        return {
            "found": True,
            "query": name,
            "canonical_name": norm_key,
            "generic_name": data.get("generic_name"),
            "brand_names": data.get("brand_names", []),
            "label_usually_says": data.get("label_usually_says"),
            "timing": data.get("timing"),
            "common_warnings": data.get("common_warnings"),
            "emoji": data.get("emoji", "💊"),
            "purpose": data.get("purpose", "Therapeutic medication")
        }

    # 2. Check brand name matches
    lower_query = name.lower()
    for key, data in drugs.items():
        if key in lower_query:
            return {
                "found": True,
                "query": name,
                "canonical_name": key,
                "generic_name": data.get("generic_name"),
                "brand_names": data.get("brand_names", []),
                "label_usually_says": data.get("label_usually_says"),
                "timing": data.get("timing"),
                "common_warnings": data.get("common_warnings"),
                "emoji": data.get("emoji", "💊"),
                "purpose": data.get("purpose", "Therapeutic medication")
            }
        for brand in data.get("brand_names", []):
            if brand.lower() in lower_query or lower_query in brand.lower():
                return {
                    "found": True,
                    "query": name,
                    "canonical_name": key,
                    "generic_name": data.get("generic_name"),
                    "brand_names": data.get("brand_names", []),
                    "label_usually_says": data.get("label_usually_says"),
                    "timing": data.get("timing"),
                    "common_warnings": data.get("common_warnings"),
                    "emoji": data.get("emoji", "💊"),
                    "purpose": data.get("purpose", "Therapeutic medication")
                }

    # Not found -> recommend escalation
    return {
        "found": False,
        "query": name,
        "label_usually_says": "Medicine not found in our reference database of common over-the-counter and outpatient drugs.",
        "common_warnings": "Please verify the spelling or check directly with a pharmacist or licensed physician.",
        "emoji": "💊",
        "purpose": "Prescribed medicine (unverified in local database)"
    }

def check_interaction(drug_a: str, drug_b: str) -> Dict[str, Any]:
    """Checks interaction between two drugs from local safety database."""
    db = load_drugs_db()
    interactions = db.get("interactions", [])
    norm_a = _normalize_name(drug_a)
    norm_b = _normalize_name(drug_b)

    for item in interactions:
        pair = [_normalize_name(d) for d in item.get("drugs", [])]
        if (norm_a in pair and norm_b in pair) or (norm_a == norm_b and len(pair) == 1):
            return {
                "has_interaction": True,
                "severity": item.get("severity", "Moderate"),
                "warning": item.get("warning"),
                "drugs": [drug_a, drug_b]
            }

    return {
        "has_interaction": False,
        "severity": "None",
        "warning": "No known critical interaction between these two medicines in our reference database.",
        "drugs": [drug_a, drug_b]
    }

def find_generic(name: str) -> Dict[str, Any]:
    """Finds generic equivalent and returns Jan Aushadhi cost-saving guidance."""
    lookup = lookup_drug(name)
    db = load_drugs_db()
    jan_aushadhi_note = db.get("generic_schemes", {}).get(
        "jan_aushadhi_note",
        "Cheaper generic equivalents may be available at Pradhan Mantri Jan Aushadhi Kendras at 50-90% savings."
    )
    if lookup.get("found"):
        return {
            "query": name,
            "generic_name": lookup.get("generic_name"),
            "jan_aushadhi_available": True,
            "note": jan_aushadhi_note,
            "tip": f"Ask your pharmacist for generic '{lookup.get('generic_name')}' to save significantly on pharmacy bills."
        }
    return {
        "query": name,
        "generic_name": name,
        "jan_aushadhi_available": True,
        "note": jan_aushadhi_note,
        "tip": f"Show this prescription to a Jan Aushadhi Kendra to ask for the government generic equivalent."
    }

def build_timeline(medicines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a structured Morning / Afternoon / Night Daily Medicine Timeline card.
    Each slot includes medicine name, strength, emoji, timing, and one-line plain language purpose.
    """
    morning = []
    afternoon = []
    night = []

    for med in medicines:
        name = med.get("name", "Medicine")
        strength = med.get("strength", "")
        freq = med.get("frequency", "").lower()
        dur = med.get("duration", "")
        lookup = lookup_drug(name)

        emoji = lookup.get("emoji", "💊")
        purpose = lookup.get("purpose", "Prescribed treatment")
        timing_note = lookup.get("timing", "As prescribed")

        # Parse schedule patterns (e.g. 1-0-1, 1-1-1, twice daily, night, etc.)
        is_morning = False
        is_afternoon = False
        is_night = False

        if "1-0-1" in freq or "twice" in freq or "bd" in freq or "bid" in freq:
            is_morning = True
            is_night = True
        elif "1-1-1" in freq or "thrice" in freq or "tid" in freq:
            is_morning = True
            is_afternoon = True
            is_night = True
        elif "1-0-0" in freq or "morning" in freq or "subah" in freq or "empty stomach" in freq or "khali pet" in freq:
            is_morning = True
        elif "0-1-0" in freq or "afternoon" in freq or "dopahar" in freq:
            is_afternoon = True
        elif "0-0-1" in freq or "night" in freq or "bedtime" in freq or "raat" in freq or "shaam" in freq:
            is_night = True
        else:
            # Default distribution based on common drug timings
            canon = lookup.get("canonical_name", "")
            if canon in ("pantoprazole", "levothyroxine"):
                is_morning = True
            elif canon in ("cetirizine", "montelukast", "atorvastatin"):
                is_night = True
            elif canon in ("dolo", "paracetamol", "amoxicillin", "ofloxacin"):
                is_morning = True
                is_night = True
            else:
                is_morning = True

        entry = {
            "name": name,
            "strength": strength,
            "emoji": emoji,
            "purpose": purpose,
            "duration": dur,
            "instruction": timing_note
        }

        if is_morning:
            morning.append(dict(entry))
        if is_afternoon:
            afternoon.append(dict(entry))
        if is_night:
            night.append(dict(entry))

    return {
        "title": "Daily Medicine Timeline (दैनिक दवा अनुसूची)",
        "slots": {
            "morning": {
                "label": "Morning (सुबह)",
                "period": "8:00 AM - 9:00 AM",
                "icon": "🌅",
                "medicines": morning
            },
            "afternoon": {
                "label": "Afternoon (दोपहर)",
                "period": "1:00 PM - 2:00 PM",
                "icon": "☀️",
                "medicines": afternoon
            },
            "night": {
                "label": "Night (रात)",
                "period": "8:30 PM - 9:30 PM",
                "icon": "🌙",
                "medicines": night
            }
        },
        "summary": f"{len(morning)} in morning, {len(afternoon)} in afternoon, {len(night)} at night"
    }

def escalate(reason: str) -> Dict[str, Any]:
    """Tells the user to consult a registered doctor or pharmacist."""
    return {
        "escalated": True,
        "reason": reason,
        "advisory": (
            "⚠️ IMPORTANT MEDICAL NOTICE: "
            f"{reason}. "
            "Please consult your treating physician or a licensed clinical pharmacist immediately. "
            "Do NOT alter or self-administer dosages without professional medical verification."
        ),
        "helpline": "National Health Helpline: 1075 (Toll-free across India)"
    }
