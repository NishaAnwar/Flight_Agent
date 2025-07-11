import json
import requests
from datetime import datetime

CITY_TO_IATA = {
    "islamabad": "ISB",
    "karachi": "KHI",
    "lahore": "LHE",
    "peshawar": "PEW",
    "quetta": "UET",
    "multan": "MUX",
    "faisalabad": "LYP",
    "sialkot": "SKT",
    "skardu": "KDU",
    "gilgit": "GIL",
    "chitral": "CJL",
    "sukkur": "SKZ",
    "rahim_yar_khan": "RYK",
    "gwadar": "GWD",
    "turbat": "TUK",
    "panjgur": "PJG",
    "pasni": "PSI",
    "jiwani": "JIW",
    "dalbandin": "DBA",
    "khuzdar": "KDD",
    "nawabshah": "WNS",
    "jacobabad": "JAG",
    "dera_ghazi_khan": "DEA",
    "dera_ismail_khan": "DSK",
    "parachinar": "PAJ",
    "zhob": "PZH",
    "muzaffarabad": "MFG",
    "saidu_sharif": "SDT",
    "mohenjodaro": "MJD",
    "mianwali": "MWD",
    "sibi": "SBQ",
    "sui": "SUL",
    "ormara": "ORW",
    "kohat": "OHT"
}


def search_flights(input_dict):
    # 👇 FIX: Parse JSON string to dictionary
    if isinstance(input_dict, str):
        input_dict = json.loads(input_dict)

    token = input_dict.get("token")
    # ✅ Handle both possible structures
    if "data" in input_dict:
        flight_data = input_dict["data"]
    else:
        flight_data = input_dict

    source = flight_data.get("source", "").strip().lower()
    destination = flight_data.get("destination", "").strip().lower()

    source_iata = CITY_TO_IATA.get(source)
    destination_iata = CITY_TO_IATA.get(destination)

    if not source_iata or not destination_iata:
        return f"Missing IATA code for source or destination: {source} → {source_iata}, {destination} → {destination_iata}"

    # Validate and parse date
    date_str = flight_data.get("date", "")
    try:
        travel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if travel_date < datetime.today().date():
            return "Error: Travel date must be today or in the future."
    except ValueError:
        return "Error: Invalid date format. Expected YYYY-MM-DD."

    # Normalize travelers
    travelers_input = flight_data.get("Travelers", [])
    if travelers_input and isinstance(travelers_input[0], dict):
        t = travelers_input[0]
        travelers = [
            {"Type": "adult", "Count": t.get("adult", t.get("adults", 1))},
            {"Type": "child", "Count": t.get("child", t.get("children", 0))},
            {"Type": "infant", "Count": t.get("infant", t.get("infants", 0))}
        ]
    else:
        travelers = [
            {"Type": "adult", "Count": 1},
            {"Type": "child", "Count": 0},
            {"Type": "infant", "Count": 0}
        ]

    payload = {
        "Locations": [
            {"IATA": source_iata, "Type": "airport"},
            {"IATA": destination_iata, "Type": "airport"}
        ],
        "ContentProvider": "PIA",
        "Currency": "PKR",
        "TravelClass": flight_data.get("TravelClass", "economy"),
        "TripType": flight_data.get("TripType", "one_way"),
        "TravelingDates": [date_str],
        "Travelers": travelers
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    url = "https://bookmesky.com/air/api/search"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Flight search failed. Status: {response.status_code}\n{response.text}"

    data = response.json()
    if not data.get("Itineraries"):
        return "No flights found for the selected route and date."

    results = ["✅ Available Flights:\n"]
    for itinerary in data["Itineraries"]:
        for flight in itinerary["Flights"]:
            from_city = flight["From"]["city"]["name"]
            to_city = flight["To"]["city"]["name"]
            departure = flight["DepartureAt"]
            arrival = flight["ArrivalAt"]
            airline = flight["MarketingCarrier"]["name"]

            # Convert ISO datetime strings to readable format
            try:
                departure_time = datetime.fromisoformat(departure).strftime("%I:%M %p, %d %b %Y")
                arrival_time = datetime.fromisoformat(arrival).strftime("%I:%M %p, %d %b %Y")
            except ValueError:
                departure_time = departure
                arrival_time = arrival

            results.append(f"🛫 {airline} flight from {from_city} to {to_city}")
            results.append(f"   Departure: {departure_time} | Arrival: {arrival_time}")

            for fare in flight.get("Fares", []):
                name = fare["Name"]
                price = fare["ChargedTotalPrice"]
                results.append(f"   Fare: {name.upper()} - PKR {price}")

            # Add passengers info
            passenger_info = []
            for t in flight_data.get("Travelers", []):
                count = t.get("Count", 0)
                t_type = t.get("Type", "")
                if count > 0:
                    passenger_info.append(f"{count} {t_type}(s)")
            results.append(f"👤 Passengers: {','.join(passenger_info)}")

            results.append("")

    return "\n".join(results)
