import json
import re
from datetime import datetime
import google.generativeai as genai

DEFAULTS = {
    "TripType": "one_way",
    "TravelClass": "economy",
    "Travelers": [
        {"Type": "adult", "Count": 1},
        {"Type": "child", "Count": 0},
        {"Type": "infant", "Count": 0}
    ]
}

AVAILABLE_AIRLINES = ["PIA", "Fly Jinnah", "Air Sial", "Air Blue", "Air Serene"]

def extract_flight_details(query: str) -> str:
    prompt = f"""
You are a smart flight assistant. Extract only flight booking information. Follow these rules:

1. If the query is abusive, return:
{{"message": "Please be respectful. If you continue this behavior, it reflects very poor manners."}}

2. If the query is not flight related, return:
{{"message": "This doesn't seem to be a flight-related query. Please ask something related to flights."}}

3. If the user provides a date like "12 July", assume it's for the year 2025.
4. Travelers must be converted to:
   [{{"Type": "adult", "Count": N}}, ...]

5. If the user **specifies a travel company/airline**, it will be mentioned in your structured result **under a key called `airline_detected`**.

Return ONLY this JSON:
{{
  "source": "",
  "destination": "",
  "date": "",
  "time": "",
  "TripType": "",
  "TravelClass": "",
  "Travelers": [],
  "airline_detected": ""  <-- this field is optional; leave it empty if no specific airline mentioned
}}

Query:
\"\"\"{query}\"\"\"
"""

    response = genai.GenerativeModel("models/gemini-1.5-flash-latest").generate_content(prompt)
    text = re.sub(r"^```json|```$", "", response.text, flags=re.MULTILINE).strip()

    try:
        data = json.loads(text)

        # Handle abusive or unrelated queries immediately
        if "message" in data:
            return json.dumps(data)

        # Normalize date if in "14th July" format
        if data.get("date") and re.match(r"^\d{1,2}(st|nd|rd|th)?\s+\w+", data["date"], re.IGNORECASE):
            try:
                parsed_date = datetime.strptime(data["date"], "%d %B")
                data["date"] = parsed_date.replace(year=2025).strftime("%Y-%m-%d")
            except:
                pass

        # Set defaults
        data["TripType"] = data.get("TripType") or DEFAULTS["TripType"]
        data["TravelClass"] = data.get("TravelClass") or DEFAULTS["TravelClass"]
        data["Travelers"] = data.get("Travelers") or DEFAULTS["Travelers"]

        # Convert Travelers list of strings to dict format
        if all(isinstance(t, str) for t in data["Travelers"]):
            traveler_counts = {"adult": 0, "child": 0, "infant": 0}
            for t in data["Travelers"]:
                match = re.match(r"(\d+)\s*(adult|child|infant)s?", t.strip().lower())
                if match:
                    count = int(match.group(1))
                    t_type = match.group(2)
                    traveler_counts[t_type] += count
            data["Travelers"] = [
                {"Type": "adult", "Count": traveler_counts["adult"]},
                {"Type": "child", "Count": traveler_counts["child"]},
                {"Type": "infant", "Count": traveler_counts["infant"]},
            ]

        # Ask for missing values via input()
        if not data.get("source"):
            data["source"] = input("Please enter your departure city: ").strip()

        if not data.get("destination"):
            data["destination"] = input("Please enter your destination city: ").strip()

        if not data.get("date"):
            date_input = input("Please enter your travel date (YYYY-MM-DD or 12 July): ").strip()
            try:
                if re.match(r"^\d{1,2}(st|nd|rd|th)?\s+\w+", date_input, re.IGNORECASE):
                    parsed_date = datetime.strptime(date_input, "%d %B")
                    data["date"] = parsed_date.replace(year=2025).strftime("%Y-%m-%d")
                else:
                    data["date"] = datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
            except:
                data["date"] = date_input  # Use raw input if parsing fails

        # Final response — matches API call format
        return json.dumps({
            "source": data.get("source", ""),
            "destination": data.get("destination", ""),
            "date": data.get("date", ""),
            "time": data.get("time", ""),
            "TripType": data["TripType"],
            "TravelClass": data["TravelClass"],
            "Travelers": data["Travelers"],
            "airline_detected": data.get("airline_detected", "")
        })

    except Exception:
        return json.dumps({"error": "Could not parse flight details."})
