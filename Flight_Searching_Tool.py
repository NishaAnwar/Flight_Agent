import json
import requests
from datetime import datetime
from IATA_Code import CITY_TO_IATA, get_airline_code


def city_to_iata(city_name):
    return CITY_TO_IATA.get(city_name.lower().replace(" ", "_"))


def search_flights(input_dict):
    if isinstance(input_dict, str):
        input_dict = json.loads(input_dict)

    token = input_dict.get("token")
    airline = get_airline_code(input_dict.get("airline_detected", ""))
    flight_data = input_dict.get("data", input_dict)
    # Patch if departure_date and return_date are at the top-level (like tool input)
    if "departure_date" in input_dict:
        flight_data["departure_date"] = input_dict["departure_date"]
    if "return_date" in input_dict:
        flight_data["return_date"] = input_dict["return_date"]

    travel_class = flight_data.get("TravelClass", "economy")
    trip_type = flight_data.get("TripType", "one_way")

    travelers = flight_data.get("Travelers", [
        {"Type": "adult", "Count": 1},
        {"Type": "child", "Count": 0},
        {"Type": "infant", "Count": 0}
    ])

    if airline:
        airlines_to_search = [airline]
    else:
        airlines_to_search = ["pia", "serene", "airblue", "flyjinnah", "airsial", "amadeus"]

    found_flight = False
    results = []

    def format_response(data, provider):
        nonlocal found_flight
        output = []
        if not data.get("Itineraries"):
            return f"No flights found for {provider.title()}.\n"
        found_flight = True
        output.append(f"Available Flights from {provider.title()}:\n")
        for itinerary in data["Itineraries"]:
            for flight in itinerary["Flights"]:
                from_city = flight["From"]["city"]["name"]
                to_city = flight["To"]["city"]["name"]
                dep = flight["DepartureAt"]
                arr = flight["ArrivalAt"]
                airline_name = flight["MarketingCarrier"]["name"]

                try:
                    dep_fmt = datetime.fromisoformat(dep).strftime("%I:%M %p, %d %b %Y")
                    arr_fmt = datetime.fromisoformat(arr).strftime("%I:%M %p, %d %b %Y")
                except:
                    dep_fmt, arr_fmt = dep, arr

                output.append(f"🛫 {airline_name} flight from {from_city} to {to_city}")
                output.append(f"   Departure: {dep_fmt} | Arrival: {arr_fmt}")

                for fare in flight.get("Fares", []):
                    output.append(f"   Fare: {fare['Name'].upper()} - PKR {fare['ChargedTotalPrice']}")

                pax_summary = ", ".join(f"{t['Count']} {t['Type']}(s)" for t in travelers if t['Count'] > 0)
                #output.append(f" Passengers: {pax_summary}\n")
        return "\n".join(output)

    for provider in airlines_to_search:
        payload = {}
        if trip_type == "one_way":
            source_iata = city_to_iata(flight_data.get("source", ""))
            destination_iata = city_to_iata(flight_data.get("destination", ""))
            date_str = flight_data.get("date", "")

            if not source_iata or not destination_iata:
                continue

            payload = {
                "Locations": [{"IATA": source_iata, "Type": "airport"}, {"IATA": destination_iata, "Type": "airport"}],
                "ContentProvider": provider,
                "Currency": "PKR",
                "TravelClass": travel_class,
                "TripType": "one_way",
                "TravelingDates": [date_str],
                "Travelers": travelers
            }


        elif trip_type in ["round_trip", "return"]:

            source_iata = city_to_iata(flight_data.get("source", ""))

            destination_iata = city_to_iata(flight_data.get("destination", ""))

            dep_date = flight_data.get("departure_date", "")

            ret_date = flight_data.get("return_date", "")

            if not all([source_iata, destination_iata, dep_date, ret_date]):
                continue

            payload = {

                "Locations": [

                    {"IATA": source_iata, "Type": "airport"},

                    {"IATA": destination_iata, "Type": "airport"}

                ],
                "ContentProvider": provider,
                "Currency": "PKR",
                "TravelClass": travel_class,
                "TripType": "return",
                "TravelingDates": [dep_date, ret_date],
                "Travelers": travelers
            }


        elif trip_type == "multi_city":

            locations = flight_data.get("Locations", [])

            dates = flight_data.get("TravelingDates", [])

            # Validate multi-city requirements

            if len(locations) < 4 or len(dates) < 2:  # Need at least 4 locations (2x source/dest) and 2 dates

                continue

            payload = {

                "Locations": locations,

                "ContentProvider": provider,

                "Currency": "PKR",

                "TravelClass": travel_class,

                "TripType": "multi_city",

                "TravelingDates": dates,

                "Travelers": travelers

            }

        else:
            continue  # Unsupported trip type

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post("https://bookmesky.com/air/api/search", headers=headers, json=payload)
            if response.status_code != 200:
                results.append(f"Failed to fetch flights from {provider.title()} (Status {response.status_code})\n")
                continue
            data = response.json()
            results.append(format_response(data, provider))
        except Exception as e:
            results.append(f"Error while connecting to {provider.title()}: {str(e)}")

    return "\n".join(results) if found_flight else "No flights available for the given route and date."
