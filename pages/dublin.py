import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pytz
from astral import LocationInfo
from astral.sun import sun, elevation

st.set_page_config(page_title="Dublin - Meteo Dash", layout="wide")

def apply_global_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #e8e3da !important;
        color: #2a241f !important;
    }

    header[data-testid="stHeader"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    header[data-testid="stHeader"] * {
        color: #2a241f !important;
    }
    [data-testid="stDecoration"] {
        display: none !important;
    }

    hr, [data-testid="stDivider"], .stDivider {
        border: none !important;
        height: 1.5px !important;
        background: linear-gradient(90deg, transparent 0%, #b8b0a2 15%, #948b7d 50%, #b8b0a2 85%, transparent 100%) !important;
        margin: 2rem 0 !important;
        opacity: 1 !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #ded8cd !important;
        border-right: 1px solid #c8c0b2;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #2a241f;
    }

    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarExpandButton"] *,
    [data-testid="stHeader"] button *,
    button[kind="header"] *,
    .material-symbols-outlined,
    [data-testid="stIcon"] {
        font-family: inherit !important;
    }

    input, textarea, select, button {
        background-color: #f7f4ee !important;
        color: #2a241f !important;
        border: 1px solid #c8c0b2 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_global_styles()

def apply_custom_plotly_theme(fig, title_text, yaxis_title="", show_legend=True, hovermode="x unified"):
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(color='#2a241f', size=16, family="Plus Jakarta Sans, Inter"),
            x=0, y=0.98
        ),
        xaxis=dict(
            title='',
            showgrid=True,
            gridcolor='rgba(60, 50, 40, 0.12)',
            linecolor='rgba(60, 50, 40, 0.25)',
            tickcolor='rgba(60, 50, 40, 0.25)',
            color='#2a241f',
            tickfont=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11),
            tickformat='%a %d\n%H:%M'
        ),
        yaxis=dict(
            title=dict(text=yaxis_title, font=dict(family="Plus Jakarta Sans, Inter", size=12, color='#2a241f')),
            showgrid=True,
            gridcolor='rgba(60, 50, 40, 0.12)',
            linecolor='rgba(60, 50, 40, 0.25)',
            color='#2a241f',
            tickfont=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11)
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(
            bgcolor='rgba(247, 244, 238, 0.96)',
            bordercolor='#d6cfc4',
            font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12),
            align='left'
        ),
        hovermode=hovermode,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11),
            bgcolor='rgba(0,0,0,0)'
        ) if show_legend else None,
        showlegend=show_legend
    )

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
    df.index = df.index.tz_convert('Europe/Dublin')
    df = df.drop("Date", axis=1)
    df = df.drop("Ech.", axis=1)
    df = df.astype("float")
    return df

def get_last_arome_run():
    runs = [3, 9, 15, 21]
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=8&sort=0'
    first_index = pd.Timestamp(year=2017, month=1, day=1, tz="UTC")
    valid_run = 3

    for run in runs:
        url_run = f'{url}&run={run}'
        try:
            first_index_run = get_arome_data(url_run).index[0]
            if first_index_run > first_index:
                first_index = first_index_run
                valid_run = run
        except Exception:
            pass

    return valid_run

valid_run = get_last_arome_run()

st.header("Dublin 🇮🇪")

def get_temp_data(valid_run):
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=8&sort=0'
    return get_arome_data(f'{url}&run={valid_run}')

def get_wind_gust_data(valid_run):
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=13&sort=0'
    return get_arome_data(f'{url}&run={valid_run}')

def get_pressure_data(valid_run):
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=1&sort=0'
    return get_arome_data(f'{url}&run={valid_run}')

def get_mucape_data(valid_run):
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=0&sort=0'
    return get_arome_data(f'{url}&run={valid_run}')

def get_prec_data(valid_run):
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=53.338&lon=-6.28&mode=10&sort=0'
    return get_arome_data(f'{url}&run={valid_run}')

st.sidebar.subheader("Previsión más reciente: " + str(valid_run + 2) + " horas")

temp_data = get_temp_data(valid_run)

dia_mañana = (datetime.now() + timedelta(hours=26)).day
hora = (datetime.now() + timedelta(hours=2)).hour

temp_mañana = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].mean(axis=1)[0].round(1)
desv_temp = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].std(axis=1).round(1)[0]
fiabilidad = 10 * np.exp(-0.05 * desv_temp ** 2.5)

día_año_hoy = (datetime.now() + timedelta(hours=2)).timetuple().tm_yday
día_año_mañana = día_año_hoy + 1
hora_día = (datetime.now() + timedelta(hours=2)).hour

valor_max = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).max().round(1)
valor_min = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).min().round(1)
valor_max_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).max().round(1)
valor_min_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).min().round(1)

# --- CÁLCULOS Y RENDERIZADO DE KPIs ---
fiab_val = fiabilidad.round(1)

def get_temp_hue(t):
    if pd.isna(t): return 220
    norm = max(0, min(1, (t + 10) / 55)) 
    return int(240 * (1 - norm))

hue_manana = get_temp_hue(temp_mañana)
hue_max = get_temp_hue(valor_max)
hue_min = get_temp_hue(valor_min)
hue_max_m = get_temp_hue(valor_max_mañana)
hue_min_m = get_temp_hue(valor_min_mañana)

min_card_html = f'''<div class="metric-card temp-card" style="--card-hue: {hue_min};">
<div class="metric-label">Mínima hoy</div>
<div class="metric-value">{valor_min}º</div>
</div>''' if hora_día < 9 else ""

st.markdown(f'''
<style>
.weather-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}}

.metric-card {{
    background: #f7f4ee;
    border: 1px solid #d6cfc4;
    padding: 18px 20px;
    border-radius: 14px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    box-shadow: 0 4px 16px -2px rgba(60, 50, 40, 0.08);
    --card-hue: 30; 
}}

.metric-card.temp-card:hover {{
    border-color: hsla(var(--card-hue), 85%, 45%, 0.5);
    box-shadow: 0 8px 24px -4px hsla(var(--card-hue), 85%, 40%, 0.18);
    transform: translateY(-3px);
    background: #ffffff;
}}

.metric-card.static-card:hover {{
    border-color: rgba(217, 119, 6, 0.4);
    box-shadow: 0 8px 24px -4px rgba(217, 119, 6, 0.15);
    transform: translateY(-3px);
    background: #ffffff;
}}

.metric-label {{
    font-size: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #635b53;
    margin-bottom: 6px;
    font-weight: 600;
}}

.metric-value {{
    font-size: 2.2rem;
    font-weight: 700;
    color: #2a241f;
    margin: 0;
    line-height: 1;
    letter-spacing: -0.025em;
}}

.progress-bg {{
    background: #ded8cd;
    height: 6px;
    border-radius: 3px;
    width: 100%;
    margin-top: 14px;
    overflow: hidden;
}}
.progress-fill {{
    background: linear-gradient(90deg, #d97706 0%, #d93856 100%);
    height: 100%;
    width: {fiab_val * 10}%;
    transition: width 1s ease-out;
}}
</style>

<div class="weather-grid">

<div class="metric-card temp-card" style="--card-hue: {hue_manana};">
<div class="metric-label">Mañana (Previsto)</div>
<div class="metric-value">{temp_mañana}º</div>
</div>

<div class="metric-card static-card">
<div class="metric-label">Fiabilidad</div>
<div class="metric-value">{fiab_val}<span style="font-size: 1.1rem; opacity: 0.4; font-weight: 400;"> / 10</span></div>
<div class="progress-bg">
<div class="progress-fill"></div>
</div>
</div>

</div>

<div class="weather-grid">

{min_card_html}

<div class="metric-card temp-card" style="--card-hue: {hue_max};">
<div class="metric-label">Máxima hoy</div>
<div class="metric-value">{valor_max}º</div>
</div>

<div class="metric-card temp-card" style="--card-hue: {hue_min_m};">
<div class="metric-label">Mínima mañana</div>
<div class="metric-value">{valor_min_mañana}º</div>
</div>

<div class="metric-card temp-card" style="--card-hue: {hue_max_m};">
<div class="metric-label">Máxima mañana</div>
<div class="metric-value">{valor_max_mañana}º</div>
</div>

</div>
''', unsafe_allow_html=True)
st.divider()

def plot_temp_data(data):
    fig = go.Figure()

    ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
    ens_data = data[ens_cols]
    ens_mean = ens_data.mean(axis=1)
    ens_p10 = ens_data.quantile(0.1, axis=1)
    ens_p90 = ens_data.quantile(0.9, axis=1)

    for column in ens_cols:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines', line=dict(color='rgba(99, 91, 83, 0.22)', width=1),
            name=f"Miembro {column}", showlegend=False, hoverinfo='skip'
        ))

    fig.add_trace(go.Scatter(
        x=data.index, y=ens_mean,
        mode='lines', line=dict(color='#635b53', width=1.5, dash='dot'),
        name='Media Ens', customdata=np.stack([ens_p10, ens_p90], axis=-1),
        hovertemplate='Media Ens: <b>%{y:.1f}°C</b><br>Rango 10-90%: <b>%{customdata[0]:.1f}° - %{customdata[1]:.1f}°C</b><extra></extra>'
    ))

    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines', line=dict(color='#d97706', width=2.5, dash='dash'),
            name='Run Control (Ctrl)', hovertemplate='Control (Ctrl): <b>%{y:.1f}°C</b><extra></extra>'
        ))

    if "Actual data" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Actual data"],
            mode='lines', line=dict(color='#2a241f', width=3),
            name='Datos Actuales', hovertemplate='Actual: <b>%{y:.1f}°C</b><extra></extra>'
        ))

    dates = list(set(data.index.date))
    for date in dates:
        df_day = data.loc[data.index.date == date]
        if not df_day.empty:
            min_temp = df_day.min().min()
            max_temp = df_day.max().max()
            idx_min = df_day.min(axis=1).idxmin()
            idx_max = df_day.max(axis=1).idxmax()

            fig.add_annotation(
                x=idx_min, y=min_temp, text=f"<b>{min_temp:.1f}º</b>", showarrow=False, yshift=-15,
                font=dict(color="#0277bd", size=11, family="Plus Jakarta Sans, Inter")
            )
            fig.add_annotation(
                x=idx_max, y=max_temp, text=f"<b>{max_temp:.1f}º</b>", showarrow=False, yshift=15,
                font=dict(color="#d93856", size=11, family="Plus Jakarta Sans, Inter")
            )

    apply_custom_plotly_theme(fig, 'Previsión de Temperaturas (48h)', 'Temperatura (°C)', hovermode="x unified")
    return fig


st.plotly_chart(plot_temp_data(temp_data), use_container_width=True)

prec_data = get_prec_data(valid_run)
chance_prec = 100 * pd.DataFrame(prec_data.apply(lambda row: sum(row != 0), axis=1) / len(prec_data.columns))

avg_prec = []
for i in range(len(prec_data)):
    try:
        non_zero = prec_data.iloc[i][prec_data.iloc[i] != 0]
        avg_prec.append(sum(non_zero) / len(non_zero))
    except:
        avg_prec.append(0)

avg_prec = pd.DataFrame(avg_prec).round(1)
avg_prec.index = prec_data.index

def plot_rain_chance(chance_prec, avg_prec):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.1)

    fig.add_trace(go.Scatter(
        x=avg_prec.index, y=avg_prec.iloc[:,0],
        mode='lines+markers', fill='tozeroy',
        fillcolor='rgba(2, 119, 189, 0.12)',
        name='Media (L/m2)', line=dict(color='#0277bd', width=2),
        marker=dict(size=4), hovertemplate='Lluvia Media: <b>%{y} L/m2</b><extra></extra>'
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=chance_prec.index, y=chance_prec.iloc[:,0],
        name='Probabilidad (%)',
        marker=dict(color='#d97706', line=dict(color='rgba(0,0,0,0.05)', width=1)),
        hovertemplate='Probabilidad: <b>%{y}%</b><extra></extra>'
    ), row=2, col=1)

    dates_unique = list(set(avg_prec.index.date))
    for date in dates_unique:
        midnight = datetime.combine(date, datetime.min.time())
        fig.add_vline(x=midnight, line_width=1, line_color="rgba(60, 50, 40, 0.15)", row='all', col=1)

    fig.update_layout(
        title=dict(text='Previsión de Lluvia (48h)', font=dict(color='#2a241f', size=16, family="Plus Jakarta Sans, Inter")),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(bgcolor='rgba(247, 244, 238, 0.96)', bordercolor='#d6cfc4', font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12), align='left'),
        hovermode="x unified", margin=dict(l=10, r=10, t=60, b=10), showlegend=False
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)', linecolor='rgba(60, 50, 40, 0.25)', color='#2a241f', tickfont=dict(color='#2a241f', size=11), tickformat='%a %d\n%H:%M')
    fig.update_yaxes(title_text="L/m2", title_font=dict(color='#2a241f', size=11), showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)', linecolor='rgba(60, 50, 40, 0.25)', color='#2a241f', row=1, col=1, rangemode='tozero')
    fig.update_yaxes(title_text="Probabilidad %", title_font=dict(color='#2a241f', size=11), showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)', linecolor='rgba(60, 50, 40, 0.25)', color='#2a241f', range=[0, 105], row=2, col=1)

    return fig

st.plotly_chart(plot_rain_chance(chance_prec, avg_prec), use_container_width=True)

wind_gust_data = get_wind_gust_data(valid_run)

def plot_wind_data(data):
    fig = go.Figure()

    ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
    ens_data = data[ens_cols]
    ens_mean = ens_data.mean(axis=1)

    for column in ens_cols:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines', line=dict(color='rgba(217, 119, 6, 0.22)', width=1),
            name=f"Miembro {column}", showlegend=False, hoverinfo='skip'
        ))

    fig.add_trace(go.Scatter(
        x=data.index, y=ens_mean,
        mode='lines', line=dict(color='#b45309', width=1.5, dash='dot'),
        name='Media Ensemble', hovertemplate='Media Ens: <b>%{y:.0f} km/h</b><extra></extra>'
    ))

    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines', line=dict(color='#d97706', width=2.5, dash='dash'),
            name='Run Control (Ctrl)', hovertemplate='Control (Ctrl): <b>%{y:.0f} km/h</b><extra></extra>'
        ))

    apply_custom_plotly_theme(fig, 'Previsión de Viento (Rachas) (48h)', 'Velocidad (km/h)', hovermode="x unified")
    return fig

st.plotly_chart(plot_wind_data(wind_gust_data), use_container_width=True)

pressure_data = get_pressure_data(valid_run)

def plot_pressure_data(data):
    fig = go.Figure()

    ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
    ens_data = data[ens_cols]
    ens_mean = ens_data.mean(axis=1)

    for column in ens_cols:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines', line=dict(color='rgba(99, 91, 83, 0.22)', width=1),
            name=f"Miembro {column}", showlegend=False, hoverinfo='skip'
        ))

    fig.add_trace(go.Scatter(
        x=data.index, y=ens_mean,
        mode='lines', line=dict(color='#635b53', width=1.5, dash='dot'),
        name='Media Ensemble', hovertemplate='Media Ens: <b>%{y:.1f} hPa</b><extra></extra>'
    ))

    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines', line=dict(color='#d97706', width=2.5, dash='dash'),
            name='Run Control (Ctrl)', hovertemplate='Control (Ctrl): <b>%{y:.1f} hPa</b><extra></extra>'
        ))

    apply_custom_plotly_theme(fig, 'Previsión de Presión Atmosférica (48h)', 'Presión (hPa)', hovermode="x unified")
    fig.update_layout(yaxis=dict(range=[980, 1040]))
    return fig

st.plotly_chart(plot_pressure_data(pressure_data), use_container_width=True)

mucape_data = get_mucape_data(valid_run)

def plot_mucape_data(data):
    fig = go.Figure()

    ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
    ens_data = data[ens_cols]
    ens_mean = ens_data.mean(axis=1)
    ens_max = ens_data.max(axis=1)

    for column in ens_cols:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines', line=dict(color='rgba(225, 29, 72, 0.2)', width=1),
            name=f"Miembro {column}", showlegend=False, hoverinfo='skip'
        ))

    fig.add_trace(go.Scatter(
        x=data.index, y=ens_mean,
        mode='lines', line=dict(color='#d97706', width=1.5, dash='dot'),
        name='Media Ens', customdata=ens_max,
        hovertemplate='Media CAPE: <b>%{y:.0f} J/kg</b><br>Máx Ens: <b>%{customdata:.0f} J/kg</b><extra></extra>'
    ))

    if "Ctrl" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Ctrl"],
            mode='lines', line=dict(color='#d93856', width=2.5, dash='dash'),
            name='Run Control (Ctrl)', hovertemplate='Control (Ctrl): <b>%{y:.0f} J/kg</b><extra></extra>'
        ))

    fig.add_hrect(y0=0, y1=300, fillcolor="#10b981", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=300, y1=1000, fillcolor="#fbbf24", opacity=0.04, line_width=0, layer="below")
    fig.add_hrect(y0=1000, y1=3000, fillcolor="#ef4444", opacity=0.04, line_width=0, layer="below")

    apply_custom_plotly_theme(fig, 'Potencial de Tormentas (MUCAPE) (48h)', 'J/kg', hovermode="x unified")
    return fig

st.plotly_chart(plot_mucape_data(mucape_data), use_container_width=True)

st.divider()

def plot_sun_elevation(latitude, longitude, timezone_str='UTC'):
    location = LocationInfo("Custom Location", "Custom Region", timezone_str, latitude, longitude)
    timezone = pytz.timezone(timezone_str)
    today = datetime.now(tz=timezone)
    yesterday = today - timedelta(days=1)
    year, month, day = today.year, today.month, today.day

    s_today = sun(location.observer, date=today)
    s_yesterday = sun(location.observer, date=yesterday)

    sunrise_local = s_today['sunrise'].astimezone(timezone)
    sunset_local = s_today['sunset'].astimezone(timezone)

    day_length_today = (s_today['sunset'] - s_today['sunrise']).total_seconds()
    day_length_yesterday = (s_yesterday['sunset'] - s_yesterday['sunrise']).total_seconds()
    day_length_diff = day_length_today - day_length_yesterday
    diff_minutes, diff_seconds = divmod(abs(int(day_length_diff)), 60)
    daylight_change = f"{diff_minutes} m {diff_seconds} s {'ganados' if day_length_diff > 0 else 'perdidos'}"

    sunrise_index = sunrise_local.hour * 60 + sunrise_local.minute
    sunset_index = sunset_local.hour * 60 + sunset_local.minute

    listahoras = [timezone.localize(datetime(year, month, day, hour, minute))
                  for hour in range(24) for minute in range(60)]

    elevaciones = [elevation(location.observer, dt) for dt in listahoras]
    max_elevation_index = np.argmax(elevaciones)
    current_time_index = today.hour * 60 + today.minute
    elevaciones_array = np.array(elevaciones)

    day_length_seconds = (sunset_local - sunrise_local).total_seconds()
    day_length_hours = int(day_length_seconds // 3600)
    day_length_minutes = int((day_length_seconds % 3600) / 60)

    time_labels = [dt.strftime('%H:%M') for dt in listahoras]

    fig = go.Figure()

    elev_day = np.where(elevaciones_array >= 0, elevaciones_array, 0)
    fig.add_trace(go.Scatter(
        x=time_labels, y=elev_day,
        mode='lines', fill='tozeroy',
        fillcolor='rgba(217, 119, 6, 0.18)',
        line=dict(color='#d97706', width=2.5),
        name='Día', hoverinfo='skip'
    ))

    elev_night = np.where(elevaciones_array <= 0, elevaciones_array, 0)
    fig.add_trace(go.Scatter(
        x=time_labels, y=elev_night,
        mode='lines', fill='tozeroy',
        fillcolor='rgba(2, 119, 189, 0.12)',
        line=dict(color='#0277bd', width=1.5),
        name='Noche', hoverinfo='skip'
    ))

    fig.add_trace(go.Scatter(
        x=time_labels, y=elevaciones_array,
        mode='lines', line=dict(color='rgba(0,0,0,0)', width=0),
        name='Elevación Solar',
        hovertemplate='Hora: <b>%{x}</b><br>Elevación Solar: <b>%{y:.1f}°</b><extra></extra>'
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="#a89f91", line_width=1)

    current_elevation = elevaciones_array[current_time_index]
    current_time_str = time_labels[current_time_index]
    fig.add_trace(go.Scatter(
        x=[current_time_str], y=[current_elevation],
        mode='markers+text',
        marker=dict(size=12, color='#0277bd', symbol='circle', line=dict(width=2, color='white')),
        text=[f"<b>Posición Actual ({current_elevation:.1f}°)</b>"],
        textposition="top center",
        textfont=dict(color='#0277bd', size=11, family="Plus Jakarta Sans, Inter"),
        name='Posición Actual',
        hovertemplate='Actual (%{x}): <b>%{y:.1f}°</b><extra></extra>'
    ))

    sunrise_str = time_labels[sunrise_index]
    sunset_str = time_labels[sunset_index]
    max_str = time_labels[max_elevation_index]

    fig.add_trace(go.Scatter(
        x=[sunrise_str, max_str, sunset_str],
        y=[0, elevaciones_array[max_elevation_index], 0],
        mode='markers+text',
        marker=dict(size=9, color=['#d97706', '#d93856', '#ea580c']),
        text=[f"<b>Amanecer {sunrise_str}</b>", f"<b>Cénit {max_str} ({elevaciones_array[max_elevation_index]:.1f}°)</b>", f"<b>Atardecer {sunset_str}</b>"],
        textposition=['bottom center', 'top center', 'bottom center'],
        textfont=dict(color='#2a241f', size=10.5, family="Plus Jakarta Sans, Inter"),
        showlegend=False,
        hovertemplate='Hito Solar: <b>%{x}</b> (%{y:.1f}°)<extra></extra>'
    ))

    apply_custom_plotly_theme(
        fig, 
        f'Perfil de Elevación Solar | Duración del día: {day_length_hours}h {day_length_minutes}m ({daylight_change})', 
        'Elevación (°)', 
        show_legend=False,
        hovermode="x unified"
    )

    tick_indices = list(range(0, 1440, 120))
    tick_vals = [time_labels[i] for i in tick_indices]
    fig.update_xaxes(tickvals=tick_vals, tickfont=dict(size=11, color='#2a241f'))

    return fig

st.plotly_chart(plot_sun_elevation(53.338, -6.28, 'Europe/Dublin'), use_container_width=True)
