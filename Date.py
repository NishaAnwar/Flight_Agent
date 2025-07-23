from datetime import datetime, timedelta
import re
import dateparser
from dateutil.relativedelta import relativedelta #
import copy

def resolve_date(text: str) -> str:
    text = text.lower().strip()
    today = datetime.today().date()

    # Common typo corrections
    corrections = {
        "tommorow": "tomorrow",
        "tommorrow": "tomorrow",
        "todai": "today",
        "tmrw": "tomorrow"
    }
    text = corrections.get(text, text)

    # Handle direct keywords
    if text == "today":
        return today.strftime("%Y-%m-%d")
    if text == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # Match phrases like "2 weeks 3 days", "1 month and 2 weeks", etc.
    pattern = re.findall(r"(\d+)\s*(day|week|month|year)s?", text)
    if pattern:
        result_date = today
        for value, unit in pattern:
            value = int(value)
            if unit == "day":
                result_date += timedelta(days=value)
            elif unit == "week":
                result_date += timedelta(weeks=value)
            elif unit == "month":
                result_date += relativedelta(months=value)
            elif unit == "year":
                result_date += relativedelta(years=value)
        return result_date.strftime("%Y-%m-%d")

    # Match patterns like "3 days after", "2 weeks later"
    match = re.search(r"(\d+)\s+(day|week|month|year)s?\s+(after|later|from now)", text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "day":
            return (today + timedelta(days=value)).strftime("%Y-%m-%d")
        elif unit == "week":
            return (today + timedelta(weeks=value)).strftime("%Y-%m-%d")
        elif unit == "month":
            return (today + relativedelta(months=value)).strftime("%Y-%m-%d")
        elif unit == "year":
            return (today + relativedelta(years=value)).strftime("%Y-%m-%d")

    # Fallback to dateparser
    parsed = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
    if parsed:
        return parsed.date().strftime('%Y-%m-%d')

    return "Could not resolve the date."

