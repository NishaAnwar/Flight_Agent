from difflib import get_close_matches


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

AIRLINE_NAMES = {
    "PIA": "pia",
    "Air Sial": "airsial",
    "Airblue": "airblue",
    "Air Blue": "airblue",
    "Serene Air": "serene",
    "Fly Jinnah": "flyjinnah",
    "Amadeus" :"amadeus"
}





def get_airline_code(user_input: str) -> str:
    if not user_input:
        return ""

    normalized_input = user_input.strip().lower()

    # Prepare lowercase variants
    name_map = {k.lower(): v for k, v in AIRLINE_NAMES.items()}

    # Get closest match
    match = get_close_matches(normalized_input, name_map.keys(), n=1, cutoff=0.6)
    if match:
        return name_map[match[0]]  # Return the provider code
    return ""  # Return empty if no match found
