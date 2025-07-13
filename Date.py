from datetime import datetime, timedelta
import dateparser
import re

def resolve_date(text: str) -> str:
    text = text.lower().strip()
    today = datetime.today().date()

    # Handle common typos
    corrections = {
        "tommorow": "tomorrow",
        "tommorrow": "tomorrow"
    }
    text = corrections.get(text, text)

    # Basic keywords
    if text == "today":
        return today.strftime("%Y-%m-%d")
    if text == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # Match patterns like "2 days after"
    match = re.search(r"(\d+)\s+day[s]?\s+(after|later|from\s+now)", text)
    if match:
        days = int(match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    # Let dateparser handle complex patterns and natural language
    parsed = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
    if parsed:
        return parsed.date().strftime('%Y-%m-%d')

    return "Could not resolve the date."
