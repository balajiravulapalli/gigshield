"""
GigShield Weather Utility
==========================
Calls OpenWeatherMap API to check for qualifying disruptions.

>>> OPENWEATHER_API_KEY is set in config.py
"""

import requests
from datetime import date, datetime
from flask import current_app
from app import db
from models import WeatherLog
import json


def get_weather_by_pincode(pincode: str, city: str = None):
    """
    Fetch current weather from OpenWeatherMap.
    Uses city name if available, falls back to pincode-based lookup for India.

    >>> KEY USED: current_app.config['OPENWEATHER_API_KEY']
    """
    api_key = current_app.config['OPENWEATHER_API_KEY']
    base_url = current_app.config['OPENWEATHER_BASE_URL']

    # India pincode to lat/lon lookup (using geocoding API)
    if city:
        query = f"{city},IN"
    else:
        # Use geocoding to convert pincode
        geo_url = f"http://api.openweathermap.org/geo/1.0/zip?zip={pincode},IN&appid={api_key}"
        try:
            geo_resp = requests.get(geo_url, timeout=5)
            geo_data = geo_resp.json()
            lat = geo_data.get('lat')
            lon = geo_data.get('lon')
            city = geo_data.get('name', pincode)
        except Exception as e:
            # Mock response if API unavailable
            return _mock_weather_response(pincode)

        if lat and lon:
            weather_url = f"{base_url}/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        else:
            return _mock_weather_response(pincode)
    else:
        weather_url = f"{base_url}/weather?q={query}&appid={api_key}&units=metric"

    try:
        resp = requests.get(weather_url, timeout=5)
        data = resp.json()
        return data
    except Exception:
        return _mock_weather_response(pincode)


def check_weather_disruption(pincode: str, city: str = None) -> dict:
    """
    Main function: check weather and determine if a parametric disruption trigger is met.
    Logs result to WeatherLog table.

    Returns dict with:
        - disruption_triggered: bool
        - disruption_type: str
        - severity: 'full' | 'half' | None
        - weather_data: raw dict
    """
    thresholds = current_app.config['WEATHER_THRESHOLDS']
    weather_data = get_weather_by_pincode(pincode, city)

    result = {
        'disruption_triggered': False,
        'disruption_type': None,
        'severity': None,
        'weather_data': weather_data,
    }

    if not weather_data or 'main' not in weather_data:
        return result

    temp = weather_data['main'].get('temp', 25)
    rain_1h = weather_data.get('rain', {}).get('1h', 0)
    wind_speed = weather_data['wind'].get('speed', 0) * 3.6  # m/s to km/h
    visibility = weather_data.get('visibility', 10000)
    weather_main = weather_data['weather'][0].get('main', '') if weather_data.get('weather') else ''
    weather_id = weather_data['weather'][0].get('id', 0) if weather_data.get('weather') else 0

    disruption_type = None
    severity = None

    # Heavy rain / thunderstorm
    if rain_1h >= thresholds['heavy_rain_mm'] or weather_id in range(200, 232) or weather_id in range(502, 532):
        disruption_type = 'heavy_rain'
        severity = 'full' if rain_1h >= thresholds['heavy_rain_mm'] * 2 else 'half'

    # Extreme heat
    elif temp >= thresholds['extreme_heat_c']:
        disruption_type = 'extreme_heat'
        severity = 'full' if temp >= 45 else 'half'

    # Extreme cold
    elif temp <= thresholds['extreme_cold_c']:
        disruption_type = 'extreme_cold'
        severity = 'half'

    # High winds
    elif wind_speed >= thresholds['high_wind_kmh']:
        disruption_type = 'high_wind'
        severity = 'full' if wind_speed >= 90 else 'half'

    # Very low visibility (fog, sandstorm)
    elif visibility <= thresholds['visibility_m']:
        disruption_type = 'low_visibility'
        severity = 'half'

    # Flood / Squall
    elif weather_id in range(600, 622) or weather_main in ('Squall', 'Tornado'):
        disruption_type = 'severe_weather'
        severity = 'full'

    if disruption_type:
        result['disruption_triggered'] = True
        result['disruption_type'] = disruption_type
        result['severity'] = severity

    # Log to database
    try:
        log = WeatherLog(
            pincode=pincode,
            city=city or pincode,
            log_date=date.today(),
            temperature_c=temp,
            rainfall_mm=rain_1h,
            wind_kmh=wind_speed,
            visibility_m=visibility,
            weather_main=weather_main,
            weather_desc=weather_data['weather'][0].get('description', '') if weather_data.get('weather') else '',
            raw_response=json.dumps(weather_data),
            disruption_triggered=result['disruption_triggered'],
            disruption_type=disruption_type
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"WeatherLog error: {e}")

    return result


def _mock_weather_response(pincode: str) -> dict:
    """Mock weather for development/testing when API key not configured"""
    return {
        'main': {'temp': 28, 'humidity': 65, 'feels_like': 30},
        'wind': {'speed': 3.5},
        'rain': {},
        'visibility': 8000,
        'weather': [{'id': 800, 'main': 'Clear', 'description': 'clear sky', 'icon': '01d'}],
        '_mock': True
    }
