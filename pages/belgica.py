import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from scipy.stats import percentileofscore
import pytz
from astral import LocationInfo
from astral.sun import sun, elevation


# ── Coordenadas de cada ciudad ──────────────────────────────────────
CITIES = {
    "Bruselas": {"lat": 50.8503, "lon": 4.3517},
    "Gante":    {"lat": 51.0543, "lon": 3.7174},
    "Brujas":   {"lat": 51.2093, "lon": 3.2247},
}

TIMEZONE = "Europe/Brussels"


# ── Funciones de datos (genéricas por coordenada) ───────────────────

def get_arome_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'class': 'gefs'})
    rows = table.find_all('tr')

    headers = [header.get_text(strip=True) for header in rows[0].find_all('td')]

    data = []
    for row in rows[1:]:
        columns = row.find_all('td')
        row_data = [column.get_text(strip=True) for column in columns]
        data.append(row_data)

    df = pd.DataFrame(data, columns=headers)
    df.index = pd.to_datetime(df["Date"])
    df.index = df.index.tz_convert('Europe/Madrid')
    df = df.drop("Date", axis=1)
    df = df.drop("Ech.", axis=1)
    df = df.astype("float")
    return df


def _base_url(lat, lon, mode):
    return (
        f"https://www.meteociel.fr/modeles/pe-arome_table.php?"
        f"x=0&y=0&lat={lat}&lon={lon}&mode={mode}&sort=0"
    )


def get_last_arome_run(lat, lon):
    runs = [3, 9, 15, 21]
    url = _base_url(lat, lon, mode=8)
    first_index = pd.Timestamp(year=2017, month=1, day=1, tz="UTC")

    for run in runs:
        url_run = f'{url}&run={run}'
        first_index_run = get_arome_data(url_run).index[0]
        if first_index_run > first_index:
            first_index = first_index_run
            valid_run = run

    return valid_run


def get_temp_data(lat, lon, run):
    url = f'{_base_url(lat, lon, 8)}&run={run}'
    return get_arome_data(url)


def get_wind_gust_data(lat, lon, run):
    url = f'{_base_url(lat, lon, 13)}&run={run}'
    return get_arome_data(url)


def get_pressure_data(lat, lon, run):
    url = f'{_base_url(lat, lon, 1)}&run={run}'
    return get_arome_data(url)


def get_prec_data(lat, lon, run):
    url = f'{_base_url(lat, lon, 10)}&run={run}'
    return get_arome_data(url)


# ── Funciones de gráficos ───────────────────────────────────────────

def plot_temp_data(data):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    plt.style.use('default')

    for column in data.columns[:-1]:
        ax.plot(data.index, data[column], alpha=0.9)

    plt.title('Temperature Forecast for the next 2 days', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.xticks(fontsize=10, rotation=0, ha='right')
    plt.yticks(fontsize=10)

    for hour in data.index:
        ax.axvline(hour, linestyle='--', color='black', alpha=0.1)
    plt.grid(True)

    dates = list(set(data.index.date))
    min_temps, max_temps, min_idx, max_idx = [], [], [], []
    for date in dates:
        df = data.loc[data.index.date == date]
        min_temps.append(df.min().min())
        max_temps.append(df.max().max())
        min_idx.append(df.idxmin().min())
        max_idx.append(df.idxmax().min())

    for i, temp in enumerate(min_temps):
        ax.text(min_idx[i], temp, f"{temp:.1f}", ha='left', va='top', color='blue', fontweight="bold")
    for i, temp in enumerate(max_temps):
        ax.text(max_idx[i], temp, f"{temp:.1f}", ha='left', va='bottom', color='red', fontweight="bold")

    ticks, tick_labels = [], []
    for date in data.index:
        if date.hour == 0:
            tick_labels.append(date.strftime('%a %b %d'))
            ax.axvline(date, 0, 1, color="black", linewidth=2)
            ticks.append(date)
        if date.hour % 6 == 0:
            tick_labels.append(date.strftime('%H'))
            ticks.append(date)

    ax.set_xticks(ticks)
    ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')
    return fig


def plot_rain_chance(chance_prec, avg_prec):
    fig, axs = plt.subplots(2, gridspec_kw={'height_ratios': [0.5, 0.5]}, figsize=(10, 10), sharex=True)

    axs[1].bar(chance_prec.index, chance_prec.iloc[:, 0], width=0.025)
    axs[1].set_ylim(bottom=0, top=100)
    axs[0].bar(avg_prec.index, avg_prec.iloc[:, 0], width=0.025)

    ticks, tick_labels = [], []
    for date in avg_prec.index:
        if date.hour == 0:
            tick_labels.append(date.strftime('%a, %b %d'))
            ticks.append(date)
            axs[0].axvline(date, 0, 1, color="black", linewidth=2)
            axs[1].axvline(date, 0, 1, color="black", linewidth=2)
        if date.hour % 6 == 0:
            tick_labels.append(date.strftime('%H'))
            ticks.append(date)

    for hour in avg_prec.index:
        axs[0].axvline(hour, linestyle='--', color='black', alpha=0.1)
        axs[1].axvline(hour, linestyle='--', color='black', alpha=0.1)

    axs[0].set_xticks(ticks);  axs[0].set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')
    axs[1].set_xticks(ticks);  axs[1].set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')
    axs[0].grid(True);         axs[1].grid(True)

    plt.suptitle("Rain forecast", y=0.91)
    axs[0].set_ylabel('Average L/m2 in case of rain')
    axs[1].set_ylabel('Chance of rain')
    return fig


def plot_wind_data(data):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    plt.style.use('default')

    for column in data.columns[:-1]:
        ax.plot(data.index, data[column], alpha=0.9)

    plt.title('Wind Forecast for the next 2 days', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Speed (km/h)', fontsize=12)

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.xticks(fontsize=10, rotation=0, ha='right')
    plt.yticks(fontsize=10)

    for hour in data.index:
        ax.axvline(hour, linestyle='--', color='black', alpha=0.1)
    plt.grid(True)

    dates = list(set(data.index.date))
    min_temps, max_temps, min_idx, max_idx = [], [], [], []
    for date in dates:
        df = data.loc[data.index.date == date]
        min_temps.append(df.min().min())
        max_temps.append(df.max().max())
        min_idx.append(df.idxmin().min())
        max_idx.append(df.idxmax().min())

    for i, temp in enumerate(min_temps):
        ax.text(min_idx[i], temp, f"{temp:.0f}", ha='left', va='top', color='blue', fontweight="bold")
    for i, temp in enumerate(max_temps):
        ax.text(max_idx[i], temp, f"{temp:.0f}", ha='left', va='bottom', color='red', fontweight="bold")

    ticks, tick_labels = [], []
    for date in data.index:
        if date.hour == 0:
            tick_labels.append(date.strftime('%a, %b %d'))
            ax.axvline(date, 0, 1, color="black", linewidth=2)
            ticks.append(date)
        if date.hour % 6 == 0:
            tick_labels.append(date.strftime('%H'))
            ticks.append(date)

    ax.set_xticks(ticks)
    ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')
    return fig


def plot_pressure_data(data):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    plt.style.use('default')

    for column in data.columns[:-1]:
        ax.plot(data.index, data[column], alpha=0.9)

    plt.title('Pressure Forecast for the next 2 days', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Pressure (hpa)', fontsize=12)
    ax.set_ylim(bottom=980, top=1040)

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    plt.xticks(fontsize=10, rotation=0, ha='right')
    plt.yticks(fontsize=10)

    for hour in data.index:
        ax.axvline(hour, linestyle='--', color='black', alpha=0.1)
    plt.grid(True)

    dates = list(set(data.index.date))
    min_temps, max_temps, min_idx, max_idx = [], [], [], []
    for date in dates:
        df = data.loc[data.index.date == date]
        min_temps.append(df.min().min())
        max_temps.append(df.max().max())
        min_idx.append(df.idxmin().min())
        max_idx.append(df.idxmax().min())

    for i, temp in enumerate(min_temps):
        ax.text(min_idx[i], temp, f"{temp:.0f}", ha='left', va='top', color='blue', fontweight="bold")
    for i, temp in enumerate(max_temps):
        ax.text(max_idx[i], temp, f"{temp:.0f}", ha='left', va='bottom', color='red', fontweight="bold")

    ticks, tick_labels = [], []
    for date in data.index:
        if date.hour == 0:
            tick_labels.append(date.strftime('%a, %b %d'))
            ax.axvline(date, 0, 1, color="black", linewidth=2)
            ticks.append(date)
        if date.hour % 6 == 0:
            tick_labels.append(date.strftime('%H'))
            ticks.append(date)

    ax.set_xticks(ticks)
    ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')
    return fig


def plot_sun_elevation(latitude, longitude, timezone_str='UTC'):
    import datetime as dt

    location = LocationInfo("Custom Location", "Custom Region", timezone_str, latitude, longitude)
    timezone = pytz.timezone(timezone_str)
    today = dt.datetime.now(tz=timezone)
    yesterday = today - dt.timedelta(days=1)
    year, month, day = today.year, today.month, today.day

    s_today = sun(location.observer, date=today)
    s_yesterday = sun(location.observer, date=yesterday)

    sunrise_local = s_today['sunrise'].astimezone(timezone)
    sunset_local = s_today['sunset'].astimezone(timezone)

    day_length_today = (s_today['sunset'] - s_today['sunrise']).total_seconds()
    day_length_yesterday = (s_yesterday['sunset'] - s_yesterday['sunrise']).total_seconds()

    day_length_diff = day_length_today - day_length_yesterday
    diff_minutes, diff_seconds = divmod(abs(int(day_length_diff)), 60)
    daylight_change = f"{diff_minutes} min {diff_seconds} seg {'ganados' if day_length_diff > 0 else 'perdidos'}"

    sunrise_index = sunrise_local.hour * 60 + sunrise_local.minute
    sunset_index = sunset_local.hour * 60 + sunset_local.minute

    listahoras = [timezone.localize(dt.datetime(year, month, day, hour, minute))
                  for hour in range(24) for minute in range(60)]

    elevaciones = [elevation(location.observer, d) for d in listahoras]

    max_elevation_index = np.argmax(elevaciones)
    max_elevation_time = listahoras[max_elevation_index].strftime('%H:%M')

    current_time_index = today.hour * 60 + today.minute
    elevaciones_array = np.array(elevaciones)

    day_length_seconds = (sunset_local - sunrise_local).total_seconds()
    day_length_hours = int(day_length_seconds // 3600)
    day_length_minutes = int((day_length_seconds % 3600) / 60)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')

    ax.fill_between(np.arange(len(elevaciones)), elevaciones_array, where=elevaciones_array > 0,
                    color='peachpuff', alpha=0.5)
    ax.fill_between(np.arange(len(elevaciones)), elevaciones_array, where=elevaciones_array < 0,
                    color='lightblue', alpha=0.5)

    current_elevation = elevaciones_array[current_time_index]
    ax.plot(current_time_index, current_elevation, 'o', color='darkblue', markersize=8, label='Current Position')

    sunrise_time = f"{sunrise_local.hour:02d}:{sunrise_local.minute:02d}"
    sunset_time = f"{sunset_local.hour:02d}:{sunset_local.minute:02d}"

    ax.plot(sunrise_index, 0, marker='o', color='gold', markersize=10)
    ax.text(sunrise_index, -10, sunrise_time, ha='center', fontsize=10, color='orange')

    ax.plot(sunset_index, 0, marker='o', color='darkorange', markersize=10)
    ax.text(sunset_index, -10, sunset_time, ha='center', fontsize=10, color='darkorange')

    ax.plot(max_elevation_index, elevaciones_array[max_elevation_index], 'o', color='red', markersize=8)
    ax.text(max_elevation_index, elevaciones_array[max_elevation_index] + 2, max_elevation_time,
            ha='center', fontsize=10, color='red')

    ax.set_xlabel('Time of Day (hours)', fontsize=12, fontweight='light')
    ax.set_ylabel('Sun Elevation (degrees)', fontsize=12, fontweight='light')
    ax.set_title(
        f'Sun Elevation Profile | Date: {today.strftime("%Y-%m-%d")} | Day Length: {day_length_hours}h {day_length_minutes}m',
        fontsize=14, fontweight='bold')

    hours = np.arange(0, len(elevaciones), 60)
    ax.set_xticks(hours)
    ax.set_xticklabels([str(i // 60) for i in hours], fontsize=10, fontweight='light')
    ax.yaxis.set_tick_params(labelsize=10, labelcolor='grey', width=0.5)
    ax.grid(True, linestyle=':', linewidth=0.5, color='grey', alpha=0.7)

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('grey')
        ax.spines[spine].set_linewidth(0.5)

    ax.legend(loc='upper left', frameon=False, fontsize=10)

    daylight_change_text = f"Cambio tiempo de luz: {daylight_change}"
    plt.text(0.02, 0.88, daylight_change_text, transform=ax.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='grey', alpha=0.7))

    plt.tight_layout()
    return fig


# ── Función que renderiza toda la previsión para UNA ciudad ─────────

def render_city_forecast(city_name, lat, lon, valid_run):
    """Dibuja métricas + gráficos para una ciudad concreta."""

    temp_data = get_temp_data(lat, lon, valid_run)

    dia_mañana = (datetime.now() + timedelta(hours=26)).day
    hora = (datetime.now() + timedelta(hours=2)).hour

    temp_mañana = temp_data.loc[
        temp_data.index[(temp_data.index.hour == hora) & (temp_data.index.day == dia_mañana)]
    ].mean(axis=1)[0].round(1)
    desv_temp = temp_data.loc[
        temp_data.index[(temp_data.index.hour == hora) & (temp_data.index.day == dia_mañana)]
    ].std(axis=1).round(1)[0]

    fiabilidad = 10 * np.exp(-0.05 * desv_temp ** 2.5)

    col1, col2, col3 = st.columns(3, gap="small")
    col1.metric("Fiabilidad", fiabilidad.round(1),
                help="Sobre la temperatura de mañana a esta hora, calculada sobre 10")

    st.divider()

    # ── Máximas / mínimas hoy y mañana ──
    día_año_hoy = (datetime.now() + timedelta(hours=2)).timetuple().tm_yday
    día_año_mañana = día_año_hoy + 1
    hora_día = (datetime.now() + timedelta(hours=2)).hour

    valor_max = temp_data[temp_data.index.day_of_year == día_año_hoy].mean(axis=1).max().round(1)
    valor_min = temp_data[temp_data.index.day_of_year == día_año_hoy].mean(axis=1).min().round(1)
    valor_max_mañana = temp_data[temp_data.index.day_of_year == día_año_mañana].mean(axis=1).max().round(1)
    valor_min_mañana = temp_data[temp_data.index.day_of_year == día_año_mañana].mean(axis=1).min().round(1)

    if hora_día < 9:
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric(":thermometer: Mínima hoy (ºC)", valor_min, delta_color="off")
        c2.metric(":thermometer: Máxima hoy (ºC)", valor_max, delta_color="off")
        c3.metric(":thermometer: Mínima mañana (ºC)", valor_min_mañana, delta_color="off")
        c4.metric(":thermometer: Máxima mañana (ºC)", valor_max_mañana, delta_color="off")
    else:
        c1, c2, c3 = st.columns(3, gap="small")
        c1.metric(":thermometer: Máxima hoy (ºC)", valor_max, delta_color="off")
        c2.metric(":thermometer: Mínima mañana (ºC)", valor_min_mañana, delta_color="off")
        c3.metric(":thermometer: Máxima mañana (ºC)", valor_max_mañana, delta_color="off")

    st.divider()

    # ── Gráfico de temperatura ──
    st.pyplot(plot_temp_data(temp_data))

    # ── Lluvia ──
    prec_data = get_prec_data(lat, lon, valid_run)
    chance_prec = 100 * pd.DataFrame(
        prec_data.apply(lambda row: sum(row != 0), axis=1) / len(prec_data.columns)
    )

    avg_prec = []
    for i in range(len(prec_data)):
        try:
            non_zero = prec_data.iloc[i][prec_data.iloc[i] != 0]
            avg_prec.append(sum(non_zero) / len(non_zero))
        except:
            avg_prec.append(0)

    avg_prec = pd.DataFrame(avg_prec).round(1)
    avg_prec.index = prec_data.index

    st.pyplot(plot_rain_chance(chance_prec, avg_prec))

    # ── Viento ──
    wind_data = get_wind_gust_data(lat, lon, valid_run)
    st.pyplot(plot_wind_data(wind_data))

    # ── Elevación solar ──
    st.pyplot(plot_sun_elevation(lat, lon, TIMEZONE))


# ══════════════════════════════════════════════════════════════════════
# ██  PÁGINA PRINCIPAL  ███████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════

st.header("Bélgica 🇧🇪")

# Determinar el último run disponible (usamos Bruselas como referencia)
ref = CITIES["Bruselas"]
valid_run = get_last_arome_run(ref["lat"], ref["lon"])

st.sidebar.subheader("Previsión más reciente: " + str(valid_run + 2) + " horas")

# ── Tabs por ciudad ──
tab_bruselas, tab_gante, tab_brujas = st.tabs(["🏛️ Bruselas", "⛪ Gante", "🏰 Brujas"])

with tab_bruselas:
    coords = CITIES["Bruselas"]
    render_city_forecast("Bruselas", coords["lat"], coords["lon"], valid_run)

with tab_gante:
    coords = CITIES["Gante"]
    render_city_forecast("Gante", coords["lat"], coords["lon"], valid_run)

with tab_brujas:
    coords = CITIES["Brujas"]
    render_city_forecast("Brujas", coords["lat"], coords["lon"], valid_run)
