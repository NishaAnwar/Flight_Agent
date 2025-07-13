import json
import re
from datetime import datetime
import google.generativeai as genai
from Date import resolve_date
from Default_Values import DEFAULTS
from IATA_Code import CITY_TO_IATA
def today_str():
    return datetime.today().strftime("%Y-%m-%d")


def city_to_iata(city):
    return CITY_TO_IATA.get(city.strip().lower().replace(" ", "_"))


def extract_flight_details(query: str) -> str:
    prompt = f"""
You are a smart flight assistant. Extract only flight booking information. Follow these rules:

1. If the query is abusive, return:
{{"message": "Please be respectful. If you continue this behavior, it reflects very poor manners."}}

2. If the query is not flight related, return:
{{"message": "This doesn't seem to be a flight-related query. Please ask something related to flights."}}

3. Assume date like "12 July" is for year 2025.
4. Travelers must be structured as:
   [{{"Type": "adult", "Count": N}}, ...]

5. Fix misspelled cities like:
   Karachi, Lahore, Islamabad, Faisalabad, Multan, Quetta, Peshawar

6. Normalize `TripType` to one of:
   - one_way (includes 'one way', 'one-way', etc.)
   - round_trip (includes 'roundtrip', 'return', etc.)
   - multi_city (includes 'multi-city', 'multi city')

7. If `TripType` is multi_city:
   - Return an array like:
     "flights": [
       {{ "source": "City1", "destination": "City2", "date": "14 July" }},
       ...
     ]
   - If less than 2 segments are provided, fallback to one_way.

8. If `TripType` is round_trip:
   - Return:
     "departure_date": "", "return_date": ""
   - If dates are missing:
     - Use today's date
     - If only one date is mentioned, use it for both

9. If no specific airline is mentioned, leave `airline_detected` empty.

Return ONLY this JSON:
{{
  "TripType": "one_way | round_trip | multi_city",
  "source": "",
  "destination": "",
  "date": "",  <-- for one_way only "Enter as-is (e.g., 'tomorrow', '2 days later', '12 July',) — DO NOT convert to YYYY-MM-DD here"
  "departure_date": "",  <-- for round_trip
  "return_date": "",     <-- for round_trip
  "flights": [],         <-- for multi_city
  "TravelClass": "",
  "Travelers": [],
  "airline_detected": ""
}}

Query:
\"\"\"{query}\"\"\"
"""

    response = genai.GenerativeModel("models/gemini-1.5-flash-latest").generate_content(prompt)
    text = re.sub(r"^```json|```$", "", response.text, flags=re.MULTILINE).strip()

    try:
        data = json.loads(text)

        if "message" in data:
            return json.dumps(data)

        trip_type = data.get("TripType", "").lower()

        # Common defaults
        data["TravelClass"] = data.get("TravelClass") or DEFAULTS["TravelClass"]
        data["Travelers"] = data.get("Travelers") or DEFAULTS["Travelers"]

        if all(isinstance(t, str) for t in data["Travelers"]):
            traveler_counts = {"adult": 0, "child": 0, "infant": 0}
            for t in data["Travelers"]:
                match = re.match(r"(\d+)\s*(adult|child|infant)s?", t.strip().lower())
                if match:
                    traveler_counts[match.group(2)] += int(match.group(1))
            data["Travelers"] = [
                {"Type": "adult", "Count": traveler_counts["adult"]},
                {"Type": "child", "Count": traveler_counts["child"]},
                {"Type": "infant", "Count": traveler_counts["infant"]},
            ]

        ###  ONE-WAY FLIGHT
        if trip_type == "one_way":
            if not data.get("date"):
                data["date"] = today_str()
            else:
                data["date"] = resolve_date(data["date"])
            return json.dumps({
                "source": data.get("source", ""),
                "destination": data.get("destination", ""),
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "TripType": data["TripType"],
                "TravelClass": data["TravelClass"],
                "Travelers": data["Travelers"],
                **({"airline_detected": data["airline_detected"]} if data.get("airline_detected") else {})
            })




        ###  ROUND TRIP
        elif trip_type == "round_trip":
            # Get dates directly without fallback to 'date'
            departure = data.get("departure_date")
            return_date = data.get("return_date")

            # Handle missing dates
            if not departure and not return_date:
                departure = return_date = today_str()
            elif departure and not return_date:
                return_date = departure
            elif not departure and return_date:
                departure = return_date

            # Resolve both dates
            resolved_departure = resolve_date(departure)
            resolved_return = resolve_date(return_date)

            return json.dumps({
                "source": data.get("source", ""),  # Keep original city name
                "destination": data.get("destination", ""),  # Keep original city name
                "departure_date": resolved_departure,
                "return_date": resolved_return,
                "time": "",
                "TripType": "return",
                "TravelClass": data["TravelClass"],
                "Travelers": data["Travelers"],
                **({"airline_detected": data["airline_detected"]} if data.get("airline_detected") else {})
            })






        ### ✅ MULTI CITY
        elif trip_type == "multi_city":
            flights = data.get("flights", [])

            # Normalize and resolve dates
            normalized_flights = []
            for leg in flights:
                src = leg.get("source", "").strip()
                dst = leg.get("destination", "").strip()
                if not src or not dst:
                    continue
                if not city_to_iata(src) or not city_to_iata(dst):
                    continue  # Skip invalid cities

                date = resolve_date(leg.get("date", today_str()))
                normalized_flights.append({
                    "source": src,
                    "destination": dst,
                    "date": date
                })

            if len(normalized_flights) < 2:
                # Fallback to one_way
                fallback = normalized_flights[0] if normalized_flights else {}
                return json.dumps({
                    "TripType": "one_way",
                    "source": fallback.get("source", ""),
                    "destination": fallback.get("destination", ""),
                    "date": fallback.get("date", today_str()),
                    "TravelClass": data["TravelClass"],
                    "Travelers": data["Travelers"],
                    **({"airline_detected": data["airline_detected"]} if data.get("airline_detected") else {})
                })

            # Build locations array (alternating source/destination)
            locations = []
            dates = []
            for leg in normalized_flights:
                locations.append({"IATA": city_to_iata(leg["source"]), "Type": "airport"})
                locations.append({"IATA": city_to_iata(leg["destination"]), "Type": "airport"})
                dates.append(leg["date"])

            return json.dumps({
                "TripType": "multi_city",
                "Locations": locations,
                "TravelingDates": dates,
                "TravelClass": data["TravelClass"],
                "Travelers": data["Travelers"],
                **({"airline_detected": data["airline_detected"]} if data.get("airline_detected") else {})
            })
        # Fallback if unknown trip type
        return json.dumps({"error": "Unknown or unsupported TripType."})

    except Exception as e:
        return json.dumps({"error": f"Could not parse flight details. {str(e)}"})
