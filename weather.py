# ============================================================
#  weather.py  -  GETS REAL WEATHER (FREE, NO SIGN UP, NO KEY)
# ============================================================
#  VERY IMPORTANT - READ THIS
#  --------------------------
#  The FREE version of Google Gemini cannot look things up on the
#  internet. Google keeps that feature ("Grounding with Google
#  Search") for paying customers only.
#
#  So if you ask free Gemini "what is the weather in Lagos?" it will
#  NOT say "I don't know". It will invent a confident wrong answer.
#
#  The fix: we fetch the REAL weather ourselves from Open-Meteo,
#  then hand the real numbers to the AI to say nicely.
#
#  Open-Meteo is:
#     * completely free
#     * no account needed
#     * no API key needed
#     * used by real companies
#
#  Other files use it like this:
#
#       import weather
#       print(weather.get_weather_text())
# ============================================================

import requests

import config


# Open-Meteo sends back a NUMBER for the sky condition.
# This table turns that number into plain English.
WEATHER_CODES = {
    0: "clear sky",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy with ice",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "very heavy rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "a thunderstorm",
    96: "a thunderstorm with hail",
    99: "a severe thunderstorm with hail",
}


def _guess_city_from_internet():
    """
    If the user did not type a city in config.ini, we guess it
    from where their internet connection exits.

    This is a free service with no key. It is usually right,
    but on mobile data it can point at the wrong city.
    """
    try:
        answer = requests.get("https://ipapi.co/json/", timeout=6)
        data = answer.json()
        return data.get("city", "")
    except Exception:
        return ""


def _find_coordinates(city_name):
    """
    Turn a city name into numbers on the map (latitude, longitude).
    Open-Meteo also does this for free, with no key.

    Returns:
        (lat, lon, name)  -> found it
        []                -> the service worked but that place does not exist
        None              -> could not reach the service at all

    We keep those last two different on purpose. "No internet" and
    "that city is not real" need different messages, otherwise the
    app tells you a lie when the network is down.
    """
    try:
        answer = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_name, "count": 1},
            timeout=6,
        )
        results = answer.json().get("results")
        if not results:
            return []
        first = results[0]
        return first["latitude"], first["longitude"], first["name"]
    except Exception:
        return None


def _fetch_weather(latitude, longitude):
    """Ask Open-Meteo for the current conditions at a spot on the map."""
    try:
        answer = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            },
            timeout=8,
        )
        return answer.json().get("current")
    except Exception:
        return None


def get_weather_text():
    """
    The main function. Returns a plain-English sentence about the
    weather, or a sentence explaining why it could not get it.

    This text is then given to the AI brain so it can speak it
    in a natural way.
    """
    # Step 1: which city?
    city = config.CITY
    if not city:
        city = _guess_city_from_internet()
    if not city:
        return ("I could not work out which city you are in. "
                "Please set your city in the config.ini file.")

    # Step 2: where is that city on the map?
    found = _find_coordinates(city)

    if found is None:
        # Could not reach the service. Do not blame the city name.
        return ("I could not reach the weather service. "
                "Check your internet connection.")

    if not found:
        # Service worked, but that place does not exist.
        return ("I could not find a place called " + city +
                ". Please check the city spelling in the config.ini file.")

    latitude, longitude, real_city_name = found

    # Step 3: what is the weather there right now?
    current = _fetch_weather(latitude, longitude)
    if not current:
        return "I reached the weather service but it sent back no data."

    # Step 4: turn the numbers into words
    condition_code = current.get("weather_code", -1)
    condition = WEATHER_CODES.get(condition_code, "unknown conditions")

    temperature = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")

    text = (
        "Current weather in " + real_city_name + ": " + condition + ". "
        "Temperature is " + str(round(temperature)) + " degrees Celsius, "
        "and it feels like " + str(round(feels_like)) + " degrees. "
        "Humidity is " + str(humidity) + " percent, "
        "wind speed is " + str(round(wind)) + " kilometres per hour."
    )
    return text
