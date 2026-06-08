import streamlit as st
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# --- Global styling ---
st.set_page_config(page_title="SkyCast Enterprise | Weather Intelligence", layout="wide")

# Custom Dark Theme Stylesheet
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    /* Global Overrides */
    .stApp {
        background-color: #0c0f16;
        color: #f3f4f6;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Headers & Subheaders */
    h1, h2, h3 {
        color: #00d4ff !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    
    /* Glassmorphic Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #161b25 0%, #11141d 100%);
        border: 1px solid #1f293d;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: #00d4ff;
    }
    .metric-title {
        color: #9ca3af;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .metric-value {
        color: #ffffff;
        font-size: 32px;
        font-weight: 700;
    }
    .metric-unit {
        color: #00d4ff;
        font-size: 18px;
    }
    
    /* Stylized Custom Text Input Container to replace broken markdown divs */
    div[data-testid="stTextInput"] {
        background-color: #161b25;
        border: 1px solid #1f293d;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    /* Custom divider line */
    .cyan-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #00d4ff, transparent);
        margin: 30px 0;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Session management ---
def buildSession():
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(['GET'])
    )
    s.mount('https://', HTTPAdapter(max_retries=retry))
    return s

# --- Explicit error-guarded API wrappers ---
def get_city_suggestions(session, query):
    if not query or len(query.strip()) < 2:
        return []
    url = "https://geocoding-api.open-meteo.com/v1/search"
    try:
        r = session.get(url, params={'name': query, 'count': 5}, timeout=5)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception:
        pass # Silently drop exception to keep UI clean during fast typing
    return []

def get_weather(session, lat, lon, tz):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "hourly": "precipitation_probability,uv_index",
        "daily": "temperature_2m_max,temperature_2m_min",
        "forecast_days": 15  
    }
    try:
        r = session.get(url, params=params, timeout=5)
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"Weather server responded with status code: {r.status_code}. Detail: {r.text}")
    except Exception as e:
        st.error(f"Connection error while fetching forecast: {e}")
    return None

def wmo_to_text(code):
    mapping = {
        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        51: ("Light drizzle", "🌧️"),
        61: ("Rain showers", "🌦️"),
        95: ("Thunderstorm", "🌩️")
    }
    return mapping.get(code, ("Atmospheric changes", "🌡️"))

# --- Streamlit reactve application entry ---
session = buildSession()

# Page Header
st.markdown("<h1 style='text-align: center; margin-top: 20px;'>SKYCAST ENTERPRISE</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 1.1rem; margin-bottom: 30px;'>Continuous global meteorological monitoring platform</p>", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([1, 2, 1])
selected_city_data = None

with col_mid:
    query = st.text_input("🔍 Start typing city name...", placeholder="Type at least 2 characters (e.g. Guwahati, Tokyo)...")
    
    if query:
        suggestions = get_city_suggestions(session, query)
        if suggestions:
            option_map = {f"{res['name']}, {res.get('admin1', '')} ({res.get('country_code', '')})": res for res in suggestions}
            choice = st.selectbox(
                "✨ Select matched location below:", 
                options=list(option_map.keys()),
                index=None,
                placeholder="Click here to inspect matching locations..."
            )
            if choice:
                selected_city_data = option_map[choice]
        else:
            st.warning("No global matches found. Verify spelling.")

st.markdown("<div class='cyan-divider'></div>", unsafe_allow_html=True)

# --- Data rendering and visualization ---
if selected_city_data:
    with st.spinner("Synchronizing real-time telemetry datasets..."):
        weather = get_weather(
            session, 
            selected_city_data['latitude'], 
            selected_city_data['longitude'], 
            selected_city_data.get('timezone') or 'UTC'
        )
        
    if weather and 'current' in weather:
        cur = weather['current']
        daily = weather['daily']
        hourly = weather['hourly']
        
        # Local time computation (api returns timezone-specific timestamp in 'time')
        api_time = datetime.fromisoformat(cur['time'])
        formatted_time = api_time.strftime("%A, %b %d | %I:%M %p")
        
        weather_desc, weather_emoji = wmo_to_text(cur['weather_code'])
        
        # Upper Layout Display containing Location details and observation timestamps
        col_title, col_time = st.columns([2, 1])
        with col_title:
            st.markdown(f"<h2>📍 {selected_city_data['name']}, {selected_city_data.get('country', '')}</h2>", unsafe_allow_html=True)
        with col_time:
            st.markdown(f"<p style='text-align: right; font-size: 1.1rem; color: #9ca3af; margin-top: 10px;'>⏱️ <b>Local Time:</b> {formatted_time}</p>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Air Temperature</div>
                    <div class="metric-value">{cur['temperature_2m']}<span class="metric-unit">°C</span></div>
                    <div style="color: #9ca3af; margin-top: 8px; font-size: 14px;">{weather_emoji} {weather_desc}</div>
                </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Thermal Index</div>
                    <div class="metric-value">{cur['apparent_temperature']}<span class="metric-unit">°C</span></div>
                    <div style="color: #9ca3af; margin-top: 8px; font-size: 14px;">"Feels Like" Temperature</div>
                </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Relative Humidity</div>
                    <div class="metric-value">{cur['relative_humidity_2m']}<span class="metric-unit">%</span></div>
                    <div style="color: #9ca3af; margin-top: 8px; font-size: 14px;">Water vapor pressure</div>
                </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Wind Velocity</div>
                    <div class="metric-value">{cur['wind_speed_10m']}<span class="metric-unit">km/h</span></div>
                    <div style="color: #9ca3af; margin-top: 8px; font-size: 14px;">Velocity at 10m altitude</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Interactive Graphic Analytics Section
        st.markdown("<h3>📊 Visual Analytics & Forecast Models</h3>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["📅 15-Day Temp Outlook", "🌧️ Next 24-Hour Rain Probability", "☀️ Ultraviolet Index Profile"])
        
        # Generation of unified forecast dataframe (Daily)
        df_daily = pd.DataFrame({
            "Date": pd.to_datetime(daily['time']),
            "Max Temp (°C)": daily['temperature_2m_max'],
            "Min Temp (°C)": daily['temperature_2m_min']
        }).set_index("Date")
        
        df_hourly = pd.DataFrame({
            "Time": pd.to_datetime(hourly['time'][:24]),
            "Precipitation Probability (%)": hourly['precipitation_probability'][:24],
            "UV Index": hourly['uv_index'][:24]
        }).set_index("Time")
        
        with tab1:
            st.markdown("<p style='color:#9ca3af; margin-bottom:20px;'>Daily extremes progression tracking across the upcoming 15-day meteorological period.</p>", unsafe_allow_html=True)
            st.line_chart(df_daily, color=["#00d4ff", "#ff4b4b"], x_label="Forecast Date", y_label="Temperature (°C)")
            
        with tab2:
            st.markdown("<p style='color:#9ca3af; margin-bottom:20px;'>Real-time dynamic tracking of upcoming precipitation events across the next 24 hours.</p>", unsafe_allow_html=True)
            st.area_chart(df_hourly["Precipitation Probability (%)"], color="#00d4ff", x_label="Hour (Next 24 hrs)", y_label="Rain Probability (%)")
            
        with tab3:
            st.markdown("<p style='color:#9ca3af; margin-bottom:20px;'>Projected solar Ultraviolet Radiation tracking index for outer activity scheduling safety.</p>", unsafe_allow_html=True)
            st.bar_chart(df_hourly["UV Index"], color="#ffcc00", x_label="Hour (Next 24 hrs)", y_label="UV Radiation Index")
            
    else:
        st.error("Failed to parse weather telemetry data. Please select another city or try again later.")
else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; color: #4b5563;">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #1f293d; margin-bottom: 16px;">
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
            </svg>
            <h3 style="color: #4b5563 !important; font-weight: 400 !important;">Awaiting system initialization parameters...</h3>
            <p>Please enter a geographic location above to synchronize satellite telemetry pipelines.</p>
        </div>
    """, unsafe_allow_html=True)
