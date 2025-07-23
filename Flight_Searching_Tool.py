import json
import requests
from IATA_Code import CITY_TO_IATA, get_airline_code
from datetime import datetime
from Data_Extraction_tool import extract_flight_details

def city_to_iata(city_name):
    return CITY_TO_IATA.get(city_name.lower().replace(" ", "_"))

def search_flights(input_dict):
    global dep_date, ret_date

    if isinstance(input_dict, str):
        input_dict = json.loads(input_dict)


    token = input_dict.get("token")
    # Step 1: Extract airlines (should be a list now)
    airline_detected = input_dict.get("airline", [])
    if isinstance(airline_detected, str):
        airline_detected = [airline_detected]
    elif not isinstance(airline_detected, list):
        airline_detected = []

    # Step 2: Map airline names to internal codes using get_airline_code
    airlines_requested = [get_airline_code(name) for name in airline_detected if get_airline_code(name)]



    flight_data = input_dict.get("data", input_dict)

    # Override dates if present in outer layer
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

    # Choose content providers based on airline

    avaible_airlines = ["sereneair", "airblue", "airsial", "amadeus", "oneapi"]

    # Step 3: Filter only valid airlines that exist in available providers
    airlines_to_search = [a for a in airlines_requested if a in avaible_airlines]

    # Fallback: If none of the mentioned airlines are available, search all
    if not airlines_to_search:
        airlines_to_search = avaible_airlines

    found_flight = False
    results = []

    def format_response(data, provider):
        nonlocal found_flight
        output = []

        if not data.get("Itineraries"):
            return ""

        for itinerary in data["Itineraries"]:
            for flight in itinerary["Flights"]:
                carrier_name = flight["MarketingCarrier"]["name"]
                carrier_code = get_airline_code(carrier_name)



                found_flight = True
                from_city = flight["From"]["city"]["name"]
                to_city = flight["To"]["city"]["name"]
                dep = flight["DepartureAt"]
                arr = flight["ArrivalAt"]

                try:
                    dep_fmt = datetime.fromisoformat(dep).strftime("%I:%M %p, %d %b %Y")
                    arr_fmt = datetime.fromisoformat(arr).strftime("%I:%M %p, %d %b %Y")
                except:
                    dep_fmt, arr_fmt = dep, arr

                output.append(f"\n{carrier_name.title()} flight from {from_city} to {to_city}")
                output.append(f"   Departure: {dep_fmt} | Arrival: {arr_fmt}")

                for fare in flight.get("Fares", []):
                    output.append(f"   Fare: {fare['Name'].upper()} - PKR {fare['ChargedTotalPrice']}")

        if output:

            header = f"\n-------------------------------------------------------\n Available Flights from {provider.title()}:\n"
            return header + "\n".join(output)
        return ""

    for provider in airlines_to_search:
        payload = {}

        # Handle One-Way Flights
        if trip_type == "one_way":
            source_iata = city_to_iata(flight_data.get("source", ""))
            destination_iata = city_to_iata(flight_data.get("destination", ""))
            date_str = flight_data.get("date", "")

            if not source_iata or not destination_iata or not date_str:
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

        # Handle Round Trip
        elif trip_type in ["round_trip", "return"]:
            source_iata = city_to_iata(flight_data.get("source", ""))
            destination_iata = city_to_iata(flight_data.get("destination", ""))
            dep_date = flight_data.get("departure_date", "")
            ret_date = flight_data.get("return_date", "")

            if not all([source_iata, destination_iata, dep_date, ret_date]):
                continue

            payload = {
                "Locations": [{"IATA": source_iata, "Type": "airport"}, {"IATA": destination_iata, "Type": "airport"}],
                "ContentProvider": provider,
                "Currency": "PKR",
                "TravelClass": travel_class,
                "TripType": "return",
                "TravelingDates": [dep_date, ret_date],
                "Travelers": travelers
            }

        # Handle Multi-City Flights
        elif trip_type == "multi_city":
            locations = flight_data.get("Locations", [])
            dates = flight_data.get("TravelingDates", [])

            if len(locations) < 4 or len(dates) < 2:
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
            continue

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post("https://bookmesky.com/air/api/search", headers=headers, json=payload)
            if response.status_code != 200:
                continue

            data = response.json()
            formatted = format_response(data, provider)
            if formatted:
                results.append(formatted)

        except Exception as e:
            results.append(f"Error while connecting to {provider.title()}: {str(e)}")

    final_output = "\n".join(results)
    if trip_type in ["round_trip", "return"] and dep_date == ret_date:
        final_output += "\n\nYou can also check flights on other return dates."

    if found_flight:
        return final_output
    else:
        return "No Flight Found for the given route"


