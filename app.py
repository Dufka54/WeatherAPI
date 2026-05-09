import streamlit as st
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Session Management

def buildSession(retries=3, backoff=0.5):
    s = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(['GET']),
    )
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s

# Mapping the weather

def wmo_code_to_text(code: int) -> str:
    mapping = {
        0: "Clear sky ☀️",
        1: "Mainly clear 🌤️",
        2: "Partly cloudy ⛅",
        3: "Overcast ☁️",
        45: "Fog 🌫️",
        48: "Depositing rime fog 🌫️",
        51: "Light drizzle 🌧️",
        53: "Moderate drizzle 🌧️",
        55: "Dense drizzle 🌧️",
        61: "Slight rain 🌦️",
        63: "Moderate rain 🌧️",
        65: "Heavy rain ⛈️",
        71: "Slight snow ❄️",
        73: "Moderate snow ❄️",
        75: "Heavy snow ❄️",
        77: "Snow grains ❄️",
        80: "Slight rain showers 🌦️",
        81: "Moderate rain showers 🌧️",
        82: "Violent rain showers ⛈️",
        85: "Slight snow showers 🌨️",
        86: "Heavy snow showers 🌨️",
        95: "Thunderstorm 🌩️",
        96: "Thunderstorm with slight hail ⛈️",
        99: "Thunderstorm with heavy hail ⛈️",
    }
    return mapping.get(code, f"Unknown Condition (Code {code})")

# Data Fetching

def geoCodeCity(session, city: str, timeout=5):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {'name': city, 'count': 1, 'language': 'en', 'format': 'json'}
    try:
        r = session.get(url, params=params, timeout=timeout)
        r.raise_for_status() # Trigger except block if HTTP error
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None
        top = results[0]
        return {
            "name": top.get("name", city),
            "country": top.get("country", ""),
            "lat": top.get("latitude"),
            "lon": top.get("longitude"),
            "timezone": top.get("timezone", "UTC"),
        }
    except requests.exceptions.Timeout:
        st.error("⏳ Geocoding timeout. The server took too long to respond.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Network error in geocoding: {e}")
    return None

def getWeather(session, lat, lon, days=7, timezone="auto", timeout=5):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": timezone,
        "forecast_days": days
    }
    try:
        r = session.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        st.error("⏳ Weather API timeout. Try again.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Network error in weather fetch: {e}")
    return None


st.set_page_config(page_title="Pro Weather Dashboard", layout="wide")
st.title("🌊 Advanced Weather Analytics")

st.sidebar.header("User Requirements")
city_input = st.sidebar.text_input("Enter City", "IIT Mandi")
duration = st.sidebar.selectbox("Select Forecast Period", ["1 Week", "2 Weeks"])
chart_type = st.sidebar.radio("Visualization Style", ["Line Graph", "Bar Chart"])

days_map = {"1 Week": 7, "2 Weeks": 14}
selected_days = days_map[duration]

if city_input:
    session = buildSession()
    city_info = geoCodeCity(session, city_input)

    if city_info:
        weather_data = getWeather(session, city_info["lat"], city_info["lon"], days=selected_days, timezone=city_info["timezone"])
        
        if weather_data:
            cur = weather_data["current"]
            st.subheader(f"📍 {city_info['name']}, {city_info['country']}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Temperature", f"{cur['temperature_2m']}°C")
            m2.metric("Feels Like", f"{cur['apparent_temperature']}°C")
            m3.metric("Humidity", f"{cur['relative_humidity_2m']}%")
            m4.metric("Wind Speed", f"{cur['wind_speed_10m']} km/h")
            
            st.write(f"**Current Condition:** {wmo_code_to_text(cur['weather_code'])}")
            
            st.divider()

            st.header(f"📊 Historical & Forecast Trends ({duration})")
            
            df = pd.DataFrame({
                "Date": pd.to_datetime(weather_data["daily"]["time"]),
                "Max Temp (°C)": weather_data["daily"]["temperature_2m_max"],
                "Min Temp (°C)": weather_data["daily"]["temperature_2m_min"],
                "Precipitation (mm)": weather_data["daily"]["precipitation_sum"]
            })
            df.set_index("Date", inplace=True)

            if chart_type == "Line Graph":
                st.line_chart(df[["Max Temp (°C)", "Min Temp (°C)"]])
            else:
                st.bar_chart(df[["Max Temp (°C)", "Min Temp (°C)"]])
            with st.expander("View Raw Data Table"):
                st.dataframe(df)
    else:
        st.warning("Could not find that city. Please refine your search.")