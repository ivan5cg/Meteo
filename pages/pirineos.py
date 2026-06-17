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
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Coordenadas de cada localización ─────────────────────────────────
CITIES = {
    "Sallent de Gállego": {"lat": 42.77147619941324, "lon": -0.3307980233574127},
    "Tramacastilla de Tena": {"lat": 42.71396690891642, "lon": -0.3163249093993428},
    "Torla-Ordesa": {"lat": 42.640, "lon": 0.000},
}

TIMEZONE = "Europe/Madrid"


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
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns:
        if column in ["Actual data", "Moy", "Ctrl"]:
            continue
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Control deterministic prediction
    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines',
            line=dict(color='white', width=2.5),
            name='Control',
            hovertemplate='%{x|%a %d %H:%M}<br><b>Control: %{y:.1f}°C</b><extra></extra>'
        ))

    # Add Max/Min annotations per day
    dates = list(set(data.index.date))
    for date in dates:
        df_day = data.loc[data.index.date == date]
        cols = [c for c in df_day.columns if c not in ["Actual data", "Moy"]]
        if not df_day.empty and cols:
            sub = df_day[cols]
            min_temp = sub.min().min()
            max_temp = sub.max().max()
            
            idx_min = sub.min(axis=1).idxmin()
            idx_max = sub.max(axis=1).idxmax()

            fig.add_annotation(
                x=idx_min, y=min_temp,
                text=f"{min_temp:.1f}º",
                showarrow=False,
                yshift=-15,
                font=dict(color="#4facfe", size=12, family="Inter", weight="bold")
            )
            fig.add_annotation(
                x=idx_max, y=max_temp,
                text=f"{max_temp:.1f}º",
                showarrow=False,
                yshift=15,
                font=dict(color="#ff6b6b", size=12, family="Inter", weight="bold")
            )

    # Midnight lines
    tz = pytz.timezone("Europe/Madrid")
    for date in list(set(data.index.date)):
        midnight = tz.localize(datetime.combine(date, datetime.min.time()))
        fig.add_vline(x=midnight, line_width=1.5, line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        title=dict(text='Previsión de Temperaturas (48h)', font=dict(color='white', size=18, family="Inter")),
        xaxis=dict(
            title='', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickformat='%a %d\n%H:%M',
            color='white'
        ),
        yaxis=dict(
            title='Temperatura (°C)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def plot_rain_chance(chance_prec, avg_prec):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        row_heights=[0.5, 0.5],
                        vertical_spacing=0.1)

    # Gráfico 1 (Arriba): Lluvia media en L/m2 (Línea + Área rellena azul)
    fig.add_trace(go.Scatter(
        x=avg_prec.index,
        y=avg_prec.iloc[:,0],
        mode='lines+markers',
        fill='tozeroy',
        name='Media (L/m2)',
        line=dict(color='#4facfe', width=2),
        marker=dict(size=4),
        hovertemplate='%{x|%a %d %H:%M}<br><b>Media: %{y} L/m2</b><extra></extra>'
    ), row=1, col=1)

    # Gráfico 2 (Abajo): Probabilidad de lluvia (Bar chart)
    fig.add_trace(go.Bar(
        x=chance_prec.index,
        y=chance_prec.iloc[:,0],
        name='Probabilidad (%)',
        marker=dict(color='#00f2fe', line=dict(color='rgba(255,255,255,0.2)', width=1)),
        hovertemplate='%{x|%a %d %H:%M}<br><b>Probabilidad: %{y}%</b><extra></extra>'
    ), row=2, col=1)

    # Líneas verticales indicando medianoche
    tz = pytz.timezone("Europe/Madrid")
    dates_unique = list(set(avg_prec.index.date))
    for date in dates_unique:
        midnight = tz.localize(datetime.combine(date, datetime.min.time()))
        fig.add_vline(x=midnight, line_width=1.5, line_color="rgba(255,255,255,0.3)", row='all', col=1)

    fig.update_layout(
        title=dict(text='Previsión de Lluvia (48h)', font=dict(color='white', size=18, family="Inter")),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )
    
    fig.update_xaxes(
        showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='white',
        tickformat='%a %d\n%H:%M'
    )
    fig.update_yaxes(title_text="L/m2", showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='white', row=1, col=1, rangemode='tozero')
    fig.update_yaxes(title_text="Probabilidad %", showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='white', range=[0, 105], row=2, col=1)

    return fig


def plot_wind_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns:
        if column in ["Actual data", "Moy", "Ctrl"]:
            continue
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Control deterministic prediction
    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines',
            line=dict(color='white', width=2.5),
            name='Control',
            hovertemplate='%{x|%a %d %H:%M}<br><b>Control: %{y:.0f} km/h</b><extra></extra>'
        ))

    # Add Max/Min annotations per day
    dates = list(set(data.index.date))
    for date in dates:
        df_day = data.loc[data.index.date == date]
        cols = [c for c in df_day.columns if c not in ["Actual data", "Moy"]]
        if not df_day.empty and cols:
            sub = df_day[cols]
            min_wind = sub.min().min()
            max_wind = sub.max().max()
            
            idx_min = sub.min(axis=1).idxmin()
            idx_max = sub.max(axis=1).idxmax()

            fig.add_annotation(
                x=idx_min, y=min_wind,
                text=f"{min_wind:.0f}",
                showarrow=False,
                yshift=-15,
                font=dict(color="#4facfe", size=12, family="Inter", weight="bold")
            )
            fig.add_annotation(
                x=idx_max, y=max_wind,
                text=f"{max_wind:.0f}",
                showarrow=False,
                yshift=15,
                font=dict(color="#ff6b6b", size=12, family="Inter", weight="bold")
            )

    # Midnight lines
    tz = pytz.timezone("Europe/Madrid")
    for date in list(set(data.index.date)):
        midnight = tz.localize(datetime.combine(date, datetime.min.time()))
        fig.add_vline(x=midnight, line_width=1.5, line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        title=dict(text='Previsión de Viento (Rachas) (48h)', font=dict(color='white', size=18, family="Inter")),
        xaxis=dict(
            title='', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickformat='%a %d\n%H:%M',
            color='white'
        ),
        yaxis=dict(
            title='Velocidad (km/h)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            rangemode='tozero'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def plot_pressure_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns:
        if column in ["Actual data", "Moy", "Ctrl"]:
            continue
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Control deterministic prediction
    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines',
            line=dict(color='white', width=2.5),
            name='Control',
            hovertemplate='%{x|%a %d %H:%M}<br><b>Control: %{y:.0f} hPa</b><extra></extra>'
        ))

    # Midnight lines
    tz = pytz.timezone("Europe/Madrid")
    for date in list(set(data.index.date)):
        midnight = tz.localize(datetime.combine(date, datetime.min.time()))
        fig.add_vline(x=midnight, line_width=1.5, line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        title=dict(text='Previsión de Presión Atmosférica (48h)', font=dict(color='white', size=18, family="Inter")),
        xaxis=dict(
            title='', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickformat='%a %d\n%H:%M',
            color='white'
        ),
        yaxis=dict(
            title='Presión (hPa)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            range=[980, 1040]
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )

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

    fig = go.Figure()

    elev_day = np.where(elevaciones_array >= 0, elevaciones_array, 0)
    elev_night = np.where(elevaciones_array < 0, elevaciones_array, 0)

    # Daylight fill
    fig.add_trace(go.Scatter(
        x=listahoras, y=elev_day,
        fill='tozeroy',
        fillcolor='rgba(255, 218, 185, 0.25)', 
        line=dict(color='rgba(0,0,0,0)', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Night fill
    fig.add_trace(go.Scatter(
        x=listahoras, y=elev_night,
        fill='tozeroy',
        fillcolor='rgba(173, 216, 230, 0.15)', 
        line=dict(color='rgba(0,0,0,0)', width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Main elevation line
    fig.add_trace(go.Scatter(
        x=listahoras, y=elevaciones_array,
        mode='lines',
        line=dict(color='rgba(255, 255, 255, 0.4)', width=2),
        showlegend=False,
        hoverinfo='skip'
    ))

    # Current position marker
    current_elevation = elevaciones_array[current_time_index]
    fig.add_trace(go.Scatter(
        x=[listahoras[current_time_index]], y=[current_elevation],
        mode='markers',
        marker=dict(color='#4facfe', size=10, line=dict(color='white', width=1)),
        name='Posición Actual',
        hovertemplate='<b>Posición Actual</b><br>Hora: %{x|%H:%M}<br>Elevación: %{y:.1f}°<extra></extra>'
    ))

    # Sunrise/Sunset times
    sunrise_time = f"{sunrise_local.hour:02d}:{sunrise_local.minute:02d}"
    sunset_time = f"{sunset_local.hour:02d}:{sunset_local.minute:02d}"

    # Sunrise marker and annotation
    fig.add_trace(go.Scatter(
        x=[listahoras[sunrise_index]], y=[0],
        mode='markers',
        marker=dict(color='gold', size=12),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_annotation(
        x=listahoras[sunrise_index], y=0,
        text=f"Amanecer<br><b>{sunrise_time}</b>",
        showarrow=False,
        yshift=-25,
        font=dict(color="orange", size=11, family="Inter")
    )

    # Sunset marker and annotation
    fig.add_trace(go.Scatter(
        x=[listahoras[sunset_index]], y=[0],
        mode='markers',
        marker=dict(color='darkorange', size=12),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_annotation(
        x=listahoras[sunset_index], y=0,
        text=f"Atardecer<br><b>{sunset_time}</b>",
        showarrow=False,
        yshift=-25,
        font=dict(color="darkorange", size=11, family="Inter")
    )

    # Max elevation marker and annotation
    fig.add_trace(go.Scatter(
        x=[listahoras[max_elevation_index]], y=[elevaciones_array[max_elevation_index]],
        mode='markers',
        marker=dict(color='#ff6b6b', size=10),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_annotation(
        x=listahoras[max_elevation_index], y=elevaciones_array[max_elevation_index],
        text=f"Cénit: {max_elevation_time}<br><b>{elevaciones_array[max_elevation_index]:.1f}°</b>",
        showarrow=False,
        yshift=20,
        font=dict(color="#ff6b6b", size=11, family="Inter")
    )

    # Daylight change box
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.95,
        text=f"Cambio tiempo de luz:<br><b>{daylight_change}</b>",
        showarrow=False,
        align="left",
        bgcolor="rgba(255, 255, 255, 0.05)",
        bordercolor="rgba(255, 255, 255, 0.2)",
        borderwidth=1,
        borderpad=6,
        font=dict(color="white", size=11, family="Inter")
    )

    fig.update_layout(
        title=dict(
            text=f'Perfil de Elevación Solar | {today.strftime("%Y-%m-%d")} | Duración del día: {day_length_hours}h {day_length_minutes}m', 
            font=dict(color='white', size=16, family="Inter")
        ),
        xaxis=dict(
            title='', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickformat='%H:%M',
            color='white'
        ),
        yaxis=dict(
            title='Elevación (grados)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False
    )

    return fig


# ── Función que renderiza toda la previsión para UNA localización ───

def render_city_forecast(city_name, lat, lon, valid_run):
    """Dibuja métricas + gráficos para una localización concreta."""

    temp_data = get_temp_data(lat, lon, valid_run)

    dia_mañana = (datetime.now() + timedelta(hours=2)).day
    hora = (datetime.now() + timedelta(hours=2)).hour

    temp_mañana = temp_data.loc[
        temp_data.index[(temp_data.index.hour == hora) & (temp_data.index.day == dia_mañana)]
    ].mean(axis=1)[0].round(1)
    desv_temp = temp_data.loc[
        temp_data.index[(temp_data.index.hour == hora) & (temp_data.index.day == dia_mañana)]
    ].std(axis=1).round(1)[0]

    fiabilidad = 10 * np.exp(-0.05 * desv_temp ** 2.5)

    # ── Máximas / mínimas hoy y mañana ──
    día_año_hoy = (datetime.now() + timedelta(hours=2)).timetuple().tm_yday
    día_año_mañana = día_año_hoy + 1
    hora_día = (datetime.now() + timedelta(hours=2)).hour

    valor_max = temp_data[temp_data.index.day_of_year == día_año_hoy].mean(axis=1).max().round(1)
    valor_min = temp_data[temp_data.index.day_of_year == día_año_hoy].mean(axis=1).min().round(1)
    valor_max_manana = temp_data[temp_data.index.day_of_year == día_año_mañana].mean(axis=1).max().round(1)
    valor_min_manana = temp_data[temp_data.index.day_of_year == día_año_mañana].mean(axis=1).min().round(1)

    # ── Mapeo de color para las tarjetas de temperatura ──
    def get_temp_hue(t):
        norm = max(0, min(1, (t + 10) / 55)) 
        return int(240 * (1 - norm))

    hue_min_hoy = get_temp_hue(valor_min)
    hue_max_hoy = get_temp_hue(valor_max)
    hue_min_manana = get_temp_hue(valor_min_manana)
    hue_max_manana = get_temp_hue(valor_max_manana)
    
    fiab_val = fiabilidad.round(1)

    # Construcción de las tarjetas en HTML
    if hora_día < 9:
        cards_html = f"""
        <div class="weather-grid">
            <div class="metric-card static-card">
                <div class="metric-label">Fiabilidad</div>
                <div class="metric-value">{fiab_val}<span style="font-size: 1.1rem; opacity: 0.4; font-weight: 400;">/10</span></div>
                <div class="progress-bg">
                    <div class="progress-fill" style="width: {fiab_val * 10}%;"></div>
                </div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_min_hoy};">
                <div class="metric-label">Mínima Hoy</div>
                <div class="metric-value">{valor_min}º</div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_max_hoy};">
                <div class="metric-label">Máxima Hoy</div>
                <div class="metric-value">{valor_max}º</div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_min_manana};">
                <div class="metric-label">Mínima Mañana</div>
                <div class="metric-value">{valor_min_manana}º</div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_max_manana};">
                <div class="metric-label">Máxima Mañana</div>
                <div class="metric-value">{valor_max_manana}º</div>
            </div>
        </div>
        """
    else:
        cards_html = f"""
        <div class="weather-grid">
            <div class="metric-card static-card">
                <div class="metric-label">Fiabilidad</div>
                <div class="metric-value">{fiab_val}<span style="font-size: 1.1rem; opacity: 0.4; font-weight: 400;">/10</span></div>
                <div class="progress-bg">
                    <div class="progress-fill" style="width: {fiab_val * 10}%;"></div>
                </div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_max_hoy};">
                <div class="metric-label">Máxima Hoy</div>
                <div class="metric-value">{valor_max}º</div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_min_manana};">
                <div class="metric-label">Mínima Mañana</div>
                <div class="metric-value">{valor_min_manana}º</div>
            </div>
            <div class="metric-card temp-card" style="--card-hue: {hue_max_manana};">
                <div class="metric-label">Máxima Mañana</div>
                <div class="metric-value">{valor_max_manana}º</div>
            </div>
        </div>
        """

    st.markdown(cards_html, unsafe_allow_html=True)
    st.divider()

    # ── Gráfico de temperatura ──
    st.plotly_chart(plot_temp_data(temp_data), use_container_width=True)

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

    st.plotly_chart(plot_rain_chance(chance_prec, avg_prec), use_container_width=True)

    # ── Viento ──
    wind_data = get_wind_gust_data(lat, lon, valid_run)
    st.plotly_chart(plot_wind_data(wind_data), use_container_width=True)

    # ── Elevación solar ──
    st.plotly_chart(plot_sun_elevation(lat, lon, TIMEZONE), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# ██  PÁGINA PRINCIPAL  ███████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════

st.header("Pirineos 🏔️")

st.markdown(
    """
    <style>
    /* Fuerza fondo oscuro global */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161a23;
    }

    /* Widgets comunes */
    input, textarea, select {
        background-color: #262730 !important;
        color: #fafafa !important;
    }

    /* Dataframes */
    .dataframe {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Importamos fuente minimalista Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .weather-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin-bottom: 25px;
        font-family: 'Inter', sans-serif;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 16px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        position: relative;
        --card-hue: 220; 
    }
    
    /* Efecto Hover Dinámico */
    .metric-card.temp-card:hover {
        border-color: hsla(var(--card-hue), 85%, 60%, 0.8);
        box-shadow: 0 0 25px -5px hsla(var(--card-hue), 80%, 50%, 0.4);
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.06);
    }
    
    /* Hover simple para tarjeta de fiabilidad (sin color temperatura) */
    .metric-card.static-card:hover {
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.06);
    }
    
    .metric-label {
        font-size: 0.7rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        line-height: 1;
    }
    
    /* Barra de progreso para fiabilidad */
    .progress-bg {
        background: rgba(255,255,255,0.08);
        height: 6px;
        border-radius: 3px;
        width: 100%;
        margin-top: 15px;
        overflow: hidden;
    }
    .progress-fill {
        background: linear-gradient(90deg, #a1c4fd 0%, #c2e9fb 100%);
        height: 100%;
        transition: width 1s ease-out;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Determinar el último run disponible (usamos Sallent de Gállego como referencia)
ref = CITIES["Sallent de Gállego"]
valid_run = get_last_arome_run(ref["lat"], ref["lon"])

st.sidebar.subheader("Previsión más reciente: " + str(valid_run + 2) + " horas")

# ── Tabs por localización ──
tab_sallent, tab_tramacastilla, tab_torla = st.tabs(["⛰️ Sallent de Gállego", "🏡 Tramacastilla de Tena", "🏞️ Torla-Ordesa"])

with tab_sallent:
    coords = CITIES["Sallent de Gállego"]
    render_city_forecast("Sallent de Gállego", coords["lat"], coords["lon"], valid_run)

with tab_tramacastilla:
    coords = CITIES["Tramacastilla de Tena"]
    render_city_forecast("Tramacastilla de Tena", coords["lat"], coords["lon"], valid_run)

with tab_torla:
    coords = CITIES["Torla-Ordesa"]
    render_city_forecast("Torla-Ordesa", coords["lat"], coords["lon"], valid_run)
