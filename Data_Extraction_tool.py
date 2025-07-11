
import json
import re
from datetime import datetime
import google.generativeai as genai



DEFAULTS = {
    "TripType": "one_way",
    "TravelClass": "economy",
    "ContentProvider": "airblue",
    "Currency": "PKR",
    "Travelers": [
        {"Type": "adult", "Count": 1},
        {"Type": "child", "Count": 0},
        {"Type": "infant", "Count": 0}
    ]
}

def extract_flight_details(query: str) -> str:
    prompt = f"""
You are a flight assistant. Extract these fields if mentioned:
- source
- destination
- date (resolve today/tomorrow into YYYY-MM-DD)
- time (24-hour format)
- TripType (e.g., one_way, round_trip)
- TravelClass (economy, business, etc.)
- Travelers (adults, children, infants)

If any field is missing, leave it empty.

Return ONLY JSON like:
{{
  "source": "",
  "destination": "",
  "date": "",
  "time": "",
  "TripType": "",
  "TravelClass": "",
  "Travelers": []
}}

Query:
\"\"\"{query}\"\"\"
"""

    response = genai.GenerativeModel("models/gemini-1.5-flash-latest").generate_content(prompt)
    text = re.sub(r"^```json|```$", "", response.text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
        # Fill in defaults
        data["date"] = data.get("date") or datetime.today().strftime("%Y-%m-%d")
        data["TripType"] = data.get("TripType") or DEFAULTS["TripType"]
        data["TravelClass"] = data.get("TravelClass") or DEFAULTS["TravelClass"]
        data["Travelers"] = data.get("Travelers") or DEFAULTS["Travelers"]
        return json.dumps(data)
    except:
        return json.dumps({"error": "Could not parse flight details."})
