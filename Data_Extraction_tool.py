import json
import re
from datetime import datetime
import google.generativeai as genai
from Date import resolve_date
from Default_Values import DEFAULTS
from IATA_Code import CITY_TO_IATA,AIRLINE_NAMES

def today_str():
    return datetime.today().strftime("%Y-%m-%d")

def get_today_day_name():
    today = datetime.today()
    return today.strftime("%A")

def city_to_iata(city):
    return CITY_TO_IATA.get(city.strip().lower().replace(" ", "_"))

def validate_airlines(raw_list):
    if not raw_list:
        return []
    valid_airlines = []
    for name in raw_list:
        for key, val in AIRLINE_NAMES.items():
            if name.strip().lower() in [key.lower(), val.lower()]:
                valid_airlines.append(val)
    return list(set(valid_airlines))  # Deduplicate

def extract_flight_details(query: str) -> str:
    prompt = f"""
    You are a smart flight assistant. Extract only flight booking information. Follow these rules:

    1. If the query is abusive, return:
    {{"message": "Please be respectful. If you continue this behavior, it reflects very poor manners."}}

    2. If the query is not flight related, return:
    {{"message": "This doesn't seem to be a flight-related query. Please ask something related to flights."}}

    3. Handle all date formats carefully:
       - Assume dates like "12 July" are for the year 2025. If month spellings are incorrect (e.g., "Octovfrt"), correct them before using.
       - If the user enters natural language expressions such as:
         - "today", "tomorrow", "next Monday", "this Sunday"
         - or relative phrases like "2 weeks", "4 months", "2 weeks 3 days", etc.
         - or weekday names: calculate using function: {get_today_day_name}
       - Convert them into format: YYYY-MM-DD
       - Base all calculations on today's date: {today_str()}
       - If no date is mentioned:
         - For one_way and multi_city → leave it empty and let the user re-enter the request with a proper date.
         - For round_trip → If only one date is mentioned, use it for both departure and return. If both dates are missing, leave them empty.
         - For phrases like  without mentioning the departure date(e.g., I want to return on the same day,return 3 days later,etc ) .leave it empty and let the user re-enter the request with a proper date.

    4. Travelers must be structured as:
       [{{"Type": "adult", "Count": N}}, ...]

    5. Fix misspelled cities like:
       Karachi, Lahore, Islamabad, Faisalabad, Multan, Quetta, Peshawar

    6. Normalize TripType to one of:
       - one_way (includes 'one way', 'one-way', etc.)
       - round_trip (includes 'roundtrip', 'return', etc.)
       - multi_city (includes 'multi-city', 'multi city')

    7. If TripType is multi_city:
       - Return an array like:
         "flights": [
           {{ "source": "City1", "destination": "City2", "date": "14 July" }},
           ...
         ]
       - If less than 2 segments are provided, fallback to one_way.
       - If any flight segment is missing a date, leave it empty so the user is prompted again.

    8. If TripType is round_trip:
       - Return:
         "departure_date": "", "return_date": ""
       - If only one date is given, use it for both.
       - If both are missing, leave both fields empty and let the user re-enter.

    9. If one or more specific airlines are mentioned,correct their spellings and detect them using correct mapping from {AIRLINE_NAMES}. Populate "airline_detected" as a list of valid airline names. Example:
   "airline_detected": ["PIA", "Emirates"]

10. If no specific airline is mentioned, set "airline_detected": []

    Return ONLY this JSON:
    {{
      "TripType": "one_way | round_trip | multi_city",
      "source": "",
      "destination": "",
      "date": "", 
      "departure_date": "",
      "return_date": "",
      "flights": [],
      "TravelClass": "",
      "Travelers": [],
      "airline_detected": []
    }}

    Query:
    \"\"\"{query}\"\"\"
    """

    response = genai.GenerativeModel("models/gemini-1.5-flash-latest").generate_content(prompt)
    text = re.sub(r"^```json|```$", "", response.text, flags=re.MULTILINE).strip()

    try:
        data = json.loads(text)
        # Normalize airline_detected to a list
        airline = data.get("airline_detected")

        # Case 1: Single airline as string → wrap into list
        if isinstance(airline, str):
            airline = [airline]
        # Case 2: Already a list → okay
        elif not isinstance(airline, list):
            airline = []

        # Validate and clean
        data["airline_detected"] = validate_airlines(airline)

        if "message" in data:
            return json.dumps(data)

        trip_type = data.get("TripType", "").lower()

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

        ### ONE-WAY
        if trip_type == "one_way":
            if not data.get("date"):
                return json.dumps({
                    "message": "You did not provide a travel date. Please re-enter your request with the date.",
                    "partial_data": {
                        "source": data.get("source", ""),
                        "destination": data.get("destination", ""),
                        "TripType": "one_way",
                        "TravelClass": data["TravelClass"],
                        "Travelers": data["Travelers"],
                        **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})

                    }
                })

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

        ### ROUND TRIP
        elif trip_type == "round_trip":
            departure = resolve_date(data.get("departure_date", "")) if data.get("departure_date") else ""
            return_date = resolve_date(data.get("return_date", "")) if data.get("return_date") else ""

            if not departure and not return_date:
                return json.dumps({
                    "message": "You did not provide any travel dates. Please provide both departure and return dates.",
                    "partial_data": {
                        "source": data.get("source", ""),
                        "destination": data.get("destination", ""),
                        "TripType": "round_trip",
                        "TravelClass": data["TravelClass"],
                        "Travelers": data["Travelers"],
                        **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})

                    }
                })
            elif departure and not return_date:
                return_date = departure
            elif not departure and return_date:
                return json.dumps({
                    "message": "You did not provide a departure date. Please provide it.",
                    "partial_data": {
                        "source": data.get("source", ""),
                        "destination": data.get("destination", ""),
                        "return_date": return_date,
                        "TripType": "round_trip",
                        "TravelClass": data["TravelClass"],
                        "Travelers": data["Travelers"],
                        **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})
                    }
                })

            return json.dumps({
                "source": data.get("source", ""),
                "destination": data.get("destination", ""),
                "departure_date": resolve_date(departure),
                "return_date": resolve_date(return_date),
                "time": "",
                "TripType": "return",
                "TravelClass": data["TravelClass"],
                "Travelers": data["Travelers"],
                **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})
            })

        ###  MULTI CITY
        elif trip_type == "multi_city":
            flights = data.get("flights", [])
            normalized_flights = []
            has_missing_data = False

            for leg in flights:
                src = leg.get("source", "").strip()
                dst = leg.get("destination", "").strip()
                date_raw = leg.get("date", "").strip()
                date = resolve_date(date_raw)  # Resolve date before checking

                if not src or not dst or not date:
                    has_missing_data = True
                    break
                if not city_to_iata(src) or not city_to_iata(dst):
                    continue

                normalized_flights.append({
                    "source": src,
                    "destination": dst,
                    "date": date
                })

            if has_missing_data or len(normalized_flights) < 2:
                return json.dumps({
                    "message": "Some flight legs are missing date, source, or destination. Please provide complete multi-city details.",
                    "partial_data": {
                        "TripType": "multi_city",
                        "TravelClass": data["TravelClass"],
                        "Travelers": data["Travelers"],
                        **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})
                    }
                })

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
                **({"airline_detected": data["airline_detected"]} if data["airline_detected"] else {})
            })

        return json.dumps({"error": "Unknown or unsupported TripType."})

    except Exception as e:
        return json.dumps({"error": f"Could not parse flight details. {str(e)}"})


