from urllib import response
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from scipy.stats import percentileofscore
import telegram
#import google.generativeai as genai


def get_arome_data(url):

#url = 'https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.658&run=9&mode=8&sort=0'  # Replace this with the URL containing the table

    url = url

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table element with class "gefs"
    table = soup.find('table', {'class': 'gefs'})

    # Get table rows
    rows = table.find_all('tr')

    # Extract headers from the first row
    headers = [header.get_text(strip=True) for header in rows[0].find_all('td')]

    # Extract data from the remaining rows
    data = []
    for row in rows[1:]:
        columns = row.find_all('td')
        row_data = [column.get_text(strip=True) for column in columns]
        data.append(row_data)

    # Create a DataFrame from the data
    df = pd.DataFrame(data, columns=headers)
    df.index = pd.to_datetime(df["Date"])

    df.index = df.index.tz_convert('Europe/Madrid')
    df = df.drop("Date",axis=1)
    df = df.drop("Ech.",axis=1)
    df = df.astype("float")

    return df


def get_last_arome_run():

    runs = [3, 9, 15, 21]
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=43.35&lon=-4.047&mode=8&sort=0'

    first_index = pd.Timestamp(year=2017, month=1, day=1,tz="UTC")

    for run in runs:
        url_run = f'{url}&run={run}'
        first_index_run = get_arome_data(url_run).index[0]

        if first_index_run > first_index:
            first_index = first_index_run
            valid_run = run
        else:
            pass

    return valid_run


#GOOGLE_KEY = st.secrets["GOOGLE_KEY"]
#client = genai.Client(api_key=GOOGLE_KEY)

valid_run = get_last_arome_run()


st.header("Ávila")


aemet_horario = pd.read_csv("https://www.aemet.es/es/eltiempo/observacion/ultimosdatos_2444_datos-horarios.csv?k=mad&l=2444&datos=det&w=0&f=temperatura&x=h24" ,
                            encoding="latin-1",skiprows=2,parse_dates=True,index_col=0,dayfirst=True)
aemet_horario.index = aemet_horario.index.tz_localize('Europe/Madrid')



aemet_horario_acumulado = pd.read_excel("Histórico/Acumulado Ávila.xlsx",index_col=0)
aemet_horario_acumulado.index = aemet_horario_acumulado.index.tz_localize('Europe/Madrid')

aemet_horario_acumulado = pd.concat([aemet_horario_acumulado,aemet_horario])

aemet_horario_acumulado = aemet_horario_acumulado[~aemet_horario_acumulado.index.duplicated(keep='first')]

aemet_horario_acumulado = aemet_horario_acumulado.sort_index(ascending=False)

aemet_horario_acumulado.index = aemet_horario_acumulado.index.tz_localize(None)

aemet_horario_acumulado.to_excel("Histórico/Acumulado Ávila.xlsx")













def get_temp_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.659&lon=-4.680&mode=8&sort=0'
    url_run = f'{url}&run={valid_run}'

    temp_data = get_arome_data(url_run)

    return temp_data

def get_wind_gust_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.659&lon=-4.680&mode=13&sort=0'
    url_run = f'{url}&run={valid_run}'

    wind_gust_data = get_arome_data(url_run)

    return wind_gust_data

def get_pressure_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.659&lon=-4.680&mode=1&sort=0'
    url_run = f'{url}&run={valid_run}'

    pressure_data = get_arome_data(url_run)

    return pressure_data

def get_mucape_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.659&lon=-4.680&mode=0&sort=0'
    url_run = f'{url}&run={valid_run}'

    mucape_data = get_arome_data(url_run)

    return mucape_data

def get_prec_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.659&lon=-4.680&mode=10&sort=0'
    url_run = f'{url}&run={valid_run}'

    prec_data = get_arome_data(url_run)

    return prec_data


#####################################################

datos_df_global = pd.read_csv("pages/avila 1990.csv",index_col="fecha",parse_dates=True)

datos_df_global = datos_df_global[~((datos_df_global.index.month == 2) & (datos_df_global.index.day == 29) & datos_df_global.index.is_leap_year)]

datos_df_global['día_del_año'] = datos_df_global.index.day_of_year

es_bisiesto = datos_df_global.index.year % 4 == 0
es_bisiesto &= (datos_df_global.index.year % 100 != 0) | (datos_df_global.index.year % 400 == 0)
marzo_en_adelante = datos_df_global.index.month >= 3
datos_df_global.loc[es_bisiesto & marzo_en_adelante, 'día_del_año'] -= 1

temp_medias = datos_df_global[["día_del_año","tmed","tmax","tmin"]]
temp_medias = temp_medias.dropna(how="any")

temp_medias_rolling = temp_medias[["tmed","tmax","tmin"]].rolling(15,center=True).mean().dropna()
temp_medias_rolling["día del año"] = temp_medias_rolling.index.day_of_year

es_bisiesto = temp_medias_rolling.index.year % 4 == 0
es_bisiesto &= (temp_medias_rolling.index.year % 100 != 0) | (temp_medias_rolling.index.year % 400 == 0)
marzo_en_adelante = temp_medias_rolling.index.month >= 3
temp_medias_rolling.loc[es_bisiesto & marzo_en_adelante, 'día del año'] -= 1

temp_medias_rolling = temp_medias_rolling.groupby("día del año").quantile([0.15, 0.85]).unstack()

#####################################################

año_max_maxima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmax"].idxmax().year
año_min_maxima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmin"].idxmax().year

año_min_minima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmin"].idxmin().year
año_max_minima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmax"].idxmin().year

max_maxima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmax"].max()
min_maxima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmin"].max()

min_minima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmin"].min()
max_minima = datos_df_global[datos_df_global["día_del_año"]==int(datetime.today().strftime("%j"))]["tmax"].min()

records_dia = pd.DataFrame(columns=["T. max","T. min"],index=["Record calor","Record frío"])
records_dia["T. max"] = ["{} ({})".format(max_maxima, año_max_maxima),"{} ({})".format(max_minima, año_max_minima)]
records_dia["T. min"] = ["{} ({})".format(min_maxima, año_min_maxima),"{} ({})".format(min_minima, año_min_minima)]
records_dia = records_dia.style.apply(lambda x: ['background-color: rgba(255, 204, 204, 0.4)' if x.name == 'T. max' else 'background-color: rgba(204, 204, 255, 0.4)' for i in x], 
                        axis=0, subset=pd.IndexSlice[:, ['T. max', 'T. min']])


#st.write(aemet_horario.index[0].strftime("%A %d %B %H:%M: "),str(aemet_horario["Temperatura (ºC)"].iloc[0])+"º")

st.sidebar.subheader("Previsión más reciente: "+str(valid_run+2)+" horas")

st.sidebar.subheader("Datos más recientes: "+str(aemet_horario.index[0].hour)+" horas")


temp_data = get_temp_data(valid_run)
temp_data["Actual data"] = aemet_horario["Temperatura (ºC)"]

temp_actual = aemet_horario["Temperatura (ºC)"].iloc[0]
temp_ayer = aemet_horario.iloc[-1]["Temperatura (ºC)"]

dia_mañana = (datetime.now() + timedelta(hours=26)).day
hora = (datetime.now() + timedelta(hours=2)).hour

temp_mañana = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].mean(axis=1)[0].round(1)
desv_temp = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].std(axis=1).round(1)[0]

fiabilidad = 10*np.exp(-0.05*desv_temp**2.5)

# --- CÁLCULOS DE LÓGICA ---
delta_hoy = (temp_actual - temp_ayer).round(1)
delta_manana = (temp_mañana - temp_actual).round(1)
fiab_val = fiabilidad.round(1)

# Lógica de Delta (Colores e Iconos)
c_up = "#ff6b6b"
c_down = "#51cf66"
color_hoy = c_up if delta_hoy > 0 else c_down
color_manana = c_up if delta_manana > 0 else c_down
arrow_hoy = "▲" if delta_hoy > 0 else "▼"
arrow_manana = "▲" if delta_manana > 0 else "▼"

# --- LÓGICA DE COLOR TEMPERATURA (Dinámico) ---
# Mapeamos rango -10ºC (Azul) a 45ºC (Rojo) usando modelo de color HSL.
# Hue: 240 es Azul puro, 0 es Rojo puro.
def get_temp_hue(t):
    # Normalizamos la temperatura entre 0 y 1 (clamped)
    norm = max(0, min(1, (t + 10) / 55)) 
    # Invertimos para que frío sea alto (azul 240) y calor bajo (rojo 0)
    return int(240 * (1 - norm))

hue_actual = get_temp_hue(temp_actual)
hue_manana = get_temp_hue(temp_mañana)

# --- RENDERIZADO HTML ---
st.markdown(f"""
<style>
/* Importamos fuente minimalista Inter */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

.weather-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 20px;
    margin-bottom: 25px;
    font-family: 'Inter', sans-serif;
}}

.metric-card {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 24px;
    border-radius: 16px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    /* Variable por defecto si no se define inline */
    --card-hue: 220; 
}}

/* Efecto Hover Dinámico */
.metric-card.temp-card:hover {{
    /* Usamos el Hue calculado en Python */
    border-color: hsla(var(--card-hue), 85%, 60%, 0.8);
    box-shadow: 0 0 25px -5px hsla(var(--card-hue), 80%, 50%, 0.4);
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.06);
}}

/* Hover simple para tarjeta de fiabilidad (sin color temperatura) */
.metric-card.static-card:hover {{
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.06);
}}

.metric-label {{
    font-size: 0.75rem;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 10px;
    font-weight: 600;
}}

.metric-value {{
    font-size: 2.5rem;
    font-weight: 700; /* Extra bold minimalista */
    color: #ffffff;
    margin: 0;
    line-height: 1;
    letter-spacing: -1px;
}}

.metric-delta {{
    font-size: 0.95rem;
    margin-top: 12px;
    font-weight: 700; /* Petición: Delta en Bold */
    display: flex;
    align-items: center;
    gap: 6px;
}}

/* Barra de progreso */
.progress-bg {{
    background: rgba(255,255,255,0.08);
    height: 6px;
    border-radius: 3px;
    width: 100%;
    margin-top: 20px;
    overflow: hidden;
}}
.progress-fill {{
    background: linear-gradient(90deg, #a1c4fd 0%, #c2e9fb 100%);
    height: 100%;
    width: {fiab_val * 10}%;
    transition: width 1s ease-out;
}}
</style>

<div class="weather-grid">

<!-- CARD 1: ACTUAL (Con variable de color dinámica) -->
<div class="metric-card temp-card" style="--card-hue: {hue_actual};">
<div class="metric-label">Actual</div>
<div class="metric-value">{temp_actual}º</div>
<div class="metric-delta" style="color: {color_hoy}">
{arrow_hoy} {abs(delta_hoy)}º <span style="font-weight: 400; opacity: 0.6; font-size: 0.85em;">vs ayer</span>
</div>
</div>

<!-- CARD 2: MAÑANA (Con variable de color dinámica) -->
<div class="metric-card temp-card" style="--card-hue: {hue_manana};">
<div class="metric-label">Mañana</div>
<div class="metric-value">{temp_mañana}º</div>
<div class="metric-delta" style="color: {color_manana}">
{arrow_manana} {abs(delta_manana)}º <span style="font-weight: 400; opacity: 0.6; font-size: 0.85em;">previsto</span>
</div>
</div>

<!-- CARD 3: FIABILIDAD (Estática) -->
<div class="metric-card static-card">
<div class="metric-label">Fiabilidad</div>
<div class="metric-value">{fiab_val}<span style="font-size: 1.2rem; opacity: 0.4; font-weight: 400;">/10</span></div>
<div class="progress-bg">
<div class="progress-fill"></div>
</div>
</div>

</div>
""", unsafe_allow_html=True)


st.divider()


########################################################



#st.write("A esta hora ayer hacía",str(temp_ayer), "grados, y mañana se esperan", str(temp_mañana), "+/-",str(desv_temp))


##########################################################

st.sidebar.subheader("")
st.sidebar.subheader("Records para un día como hoy:")

st.sidebar.dataframe(records_dia)



########################################################

día_año_hoy = (datetime.now()+timedelta(hours=2)).timetuple().tm_yday

día_año_mañana = día_año_hoy + 1 #(datetime.now()+timedelta(hours=0)).timetuple().tm_yday

hora_día = (datetime.now()+timedelta(hours=2)).hour



# Definir el array de valores
arr_max = datos_df_global[datos_df_global["día_del_año"]==día_año_hoy]["tmax"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_max = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).max().round(1)


# Definir el array de valores
arr_min = datos_df_global[datos_df_global["día_del_año"]==día_año_hoy]["tmin"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_min = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).min().round(1)

# Calcular el percentil

percentil_max_hoy = percentileofscore(arr_max, valor_max)

percentil_min_hoy = percentileofscore(arr_min, valor_min)



# Definir el array de valores
arr_max = datos_df_global[datos_df_global["día_del_año"]==día_año_mañana]["tmax"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_max_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).max().round(1)


# Definir el array de valores
arr_min = datos_df_global[datos_df_global["día_del_año"]==día_año_mañana]["tmin"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_min_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).min().round(1)

# Calcular el percentil

percentil_max_mañana = percentileofscore(arr_max, valor_max_mañana)

percentil_min_mañana = percentileofscore(arr_min, valor_min_mañana)



texto_percentil = "El percentil indica cómo es la temperatura frente a los registros históricos, un valor cercano a 100 indica un registro extremadamente alto, uno cercano a 0 indica un registro extremadamente bajo."


#if hora_día < 9:

#    col1,col2,col3,col4 = st.columns(4,gap="small")

#    col1.metric(":thermometer: Mínima hoy (ºC)",valor_min,int(percentil_min_hoy.round(0)),delta_color="off",help=texto_percentil)
#    col2.metric(":thermometer: Máxima hoy (ºC)",valor_max,int(percentil_max_hoy.round(0)),delta_color="off",help=texto_percentil)
#    col3.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,int(percentil_min_mañana.round(0)),delta_color="off",help=texto_percentil)
#    col4.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,int(percentil_max_mañana.round(0)),delta_color="off",help=texto_percentil)


#else:
#    col1,col2,col3 = st.columns(3,gap="small")
    
#    col1.metric(":thermometer: Máxima hoy (ºC)",valor_max,int(percentil_max_hoy.round(0)),delta_color="off",help=texto_percentil)
#    col2.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,int(percentil_min_mañana.round(0)),delta_color="off",help=texto_percentil)
#    col3.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,int(percentil_max_mañana.round(0)),delta_color="off",help=texto_percentil)



# --- FUNCIÓN DE COLOR DINÁMICO ---
def get_temp_hue(t):
    norm = max(0, min(1, (t + 10) / 55))
    return int(240 * (1 - norm))

# --- PREPARACIÓN DE DATOS SEGÚN HORA ---
cards_data = []

if hora_día < 9:
    cards_data = [
        {"label": "Mínima Hoy", "temp": valor_min, "perc": percentil_min_hoy},
        {"label": "Máxima Hoy", "temp": valor_max, "perc": percentil_max_hoy},
        {"label": "Mínima Mañana", "temp": valor_min_mañana, "perc": percentil_min_mañana},
        {"label": "Máxima Mañana", "temp": valor_max_mañana, "perc": percentil_max_mañana}
    ]
else:
    cards_data = [
        {"label": "Máxima Hoy", "temp": valor_max, "perc": percentil_max_hoy},
        {"label": "Mínima Mañana", "temp": valor_min_mañana, "perc": percentil_min_mañana},
        {"label": "Máxima Mañana", "temp": valor_max_mañana, "perc": percentil_max_mañana}
    ]

# --- GENERACIÓN DEL HTML ---
html_content = ""

for card in cards_data:
    hue = get_temp_hue(card['temp'])
    perc_val = int(card['perc'].round(0))
    
    # TRUCO DEL DEGRADADO:
    # Para que el degradado no se comprima, calculamos el 'background-size' inverso.
    # Ejemplo: Si el ancho es 50%, el fondo debe ser 200% para que parezca que solo vemos la mitad.
    safe_perc = max(1, perc_val) # Evitamos división por cero
    bg_size_percent = (100 / safe_perc) * 100
    
    html_content += f"""
<div class="metric-card temp-card" style="--card-hue: {hue};" title="{texto_percentil}">
<div class="metric-label">{card['label']}</div>
<div class="metric-value">{card['temp']}º</div>
<div class="perc-row">
<div class="perc-text">{perc_val}<span style="font-size:0.7em; font-weight:400; opacity:0.6; margin-left:2px">perc</span></div>
<div class="perc-track">
<div class="perc-fill" style="width: {perc_val}%; background-size: {bg_size_percent:.0f}% 100%;"></div>
</div>
</div>
</div>
"""

# --- RENDERIZADO FINAL ---
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

.weather-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
    font-family: 'Inter', sans-serif;
}}

.metric-card {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 20px;
    border-radius: 16px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    --card-hue: 220; 
    cursor: help;
}}

.metric-card.temp-card:hover {{
    border-color: hsla(var(--card-hue), 85%, 60%, 0.8);
    box-shadow: 0 0 20px -5px hsla(var(--card-hue), 80%, 50%, 0.3);
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.06);
}}

.metric-label {{
    font-size: 0.7rem;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
    font-weight: 600;
}}

.metric-value {{
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    line-height: 1;
}}

.perc-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
}}

.perc-text {{
    font-size: 0.95rem;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
    white-space: nowrap;
    width: 45px; /* Ancho fijo para alinear las barras verticalmente */
}}

.perc-track {{
    flex-grow: 1;
    height: 8px; /* Un poco más gruesa para que se aprecie mejor */
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    overflow: hidden;
}}

.perc-fill {{
    height: 100%;
    /* Degradado fijo: Azul -> Cian -> Naranja -> Rojo */
    background-image: linear-gradient(90deg, #4facfe 0%, #00f2fe 30%, #ff9f43 70%, #ff6b6b 100%);
    background-repeat: no-repeat;
    /* La posición es clave: anclada a la izquierda */
    background-position: left center;
    border-radius: 4px;
    transition: width 0.5s ease-out;
}}
</style>

<div class="weather-grid">
{html_content}
</div>
""", unsafe_allow_html=True)

st.divider()




# --- LÓGICA DE AVISOS Y GENERACIÓN HTML ---
alerts_html = ""

# Función corregida: HTML compactado sin espacios a la izquierda
def create_alert(type_alert, icon, text):
    c_class = "alert-warm" if type_alert == "warm" else "alert-cold"
    # Todo en una línea o pegado al margen para evitar error de renderizado
    return f'<div class="alert-item {c_class}"><span class="alert-icon">{icon}</span><span class="alert-text">{text}</span></div>'

# --- TUS CONDICIONALES (Sin tocar lógica) ---

# 1. Hoy
if percentil_max_hoy > 80:     
     alerts_html += create_alert("warm", "🔥", "Hoy hará mucho calor")
elif percentil_max_hoy < 20:
    alerts_html += create_alert("cold", "🥶", "Hoy hará mucho frío")

# 2. Mañana
if percentil_max_mañana > 80:     
     alerts_html += create_alert("warm", "🔥", "Mañana hará mucho calor")
elif percentil_max_mañana < 20:
    alerts_html += create_alert("cold", "🥶", "Mañana hará mucho frío")

# 3. Diferencia
if (percentil_max_mañana - percentil_max_hoy) > 50:     
     alerts_html += create_alert("warm", "📈", "Mañana subirán mucho las temperaturas")
elif (percentil_max_hoy - percentil_max_mañana) > 50 :
    alerts_html += create_alert("cold", "📉", "Mañana bajarán mucho las temperaturas")


# --- RENDERIZADO ---
if alerts_html:
    # IMPORTANTE: Todo el bloque style y div pegado a la izquierda
    st.markdown(f"""
<style>
.alerts-container {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 25px; font-family: 'Inter', sans-serif; }}
.alert-item {{ display: flex; align-items: center; padding: 12px 16px; border-radius: 12px; border: 1px solid; backdrop-filter: blur(8px); transition: transform 0.2s ease; flex: 1 1 auto; min-width: 200px; max-width: fit-content; }}
.alert-item:hover {{ transform: translateY(-2px); }}
.alert-warm {{ background: rgba(255, 107, 107, 0.1); border-color: rgba(255, 107, 107, 0.3); color: #ffcccc; }}
.alert-cold {{ background: rgba(77, 171, 247, 0.1); border-color: rgba(77, 171, 247, 0.3); color: #ccedff; }}
.alert-icon {{ font-size: 1.2rem; margin-right: 10px; }}
.alert-text {{ font-size: 0.9rem; font-weight: 500; letter-spacing: 0.3px; }}
</style>
<div class="alerts-container">
{alerts_html}
</div>
""", unsafe_allow_html=True)

st.divider()

#########################################################


def plot_temp_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one (model runs)
    for column in data.columns[:-1]:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Actual data (black thick line)
    fig.add_trace(go.Scatter(
        x=data.index, y=data["Actual data"],
        mode='lines',
        line=dict(color='white', width=4),
        name='Datos Actuales',
        hovertemplate='%{x|%a %d %H:%M}<br><b>Actual: %{y:.1f}°C</b><extra></extra>'
    ))

    # Calculamos medias históricas
    max_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[0]
    max_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[1]
    min_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[0]
    min_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[1]

    # Fill between for typical max temperatures
    fig.add_trace(go.Scatter(
        x=data.index.tolist() + data.index.tolist()[::-1],
        y=[max_usual_temp_upper]*len(data.index) + [max_usual_temp_lower]*len(data.index),
        fill='toself',
        fillcolor='rgba(255, 0, 0, 0.1)',
        line=dict(color='rgba(255,0,0,0)'),
        name='Rango Max Habitual',
        hoverinfo='skip'
    ))

    # Fill between for typical min temperatures
    fig.add_trace(go.Scatter(
        x=data.index.tolist() + data.index.tolist()[::-1],
        y=[min_usual_temp_upper]*len(data.index) + [min_usual_temp_lower]*len(data.index),
        fill='toself',
        fillcolor='rgba(0, 0, 255, 0.1)',
        line=dict(color='rgba(0,0,255,0)'),
        name='Rango Min Habitual',
        hoverinfo='skip'
    ))

    # Add Max/Min annotations per day
    dates = list(set(data.index.date))
    for date in dates:
        df_day = data.loc[data.index.date == date]
        if not df_day.empty:
            min_temp = df_day.min().min()
            max_temp = df_day.max().max()
            
            idx_min = df_day.min(axis=1).idxmin()
            idx_max = df_day.max(axis=1).idxmax()

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

st.plotly_chart(plot_temp_data(temp_data), use_container_width=True)
st.divider()

##############################################

prec_data = get_prec_data(valid_run)
#prec_data["Actual data"] = aemet_horario["Precipitación (mm)"]

chance_prec = 100 * pd.DataFrame((prec_data.apply(lambda row: sum(row != 0), axis=1) / len(prec_data.columns)) )

avg_prec = []
for i in range(len(prec_data)):

    try:
        avg_prec.append(sum(prec_data.iloc[i][prec_data.iloc[i]!=0])/len(prec_data.iloc[i][prec_data.iloc[i]!=0]))

    except:
        avg_prec.append(0)

avg_prec = pd.DataFrame(avg_prec)
avg_prec = avg_prec.round(1)
avg_prec.index = prec_data.index

def plot_prec_data(data):

        data = data

        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)
            ax.plot(data.index,data[column].cumsum(),alpha=0.5,linestyle="--")

        ax.plot(data["Actual data"], alpha=1,linewidth=4,color="black")

        # Add title and labels


        plt.title('Rain Forecast for the next 2 days', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('L/m2', fontsize=12)

       

        # Remove top and right spines
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        # Set x-axis tick parameters
        plt.xticks(fontsize=10, rotation=0, ha='right')

        # Set y-axis tick parameters
        plt.yticks(fontsize=10)

        # Add vertical lines for each hour
        for hour in data.index:
            ax.axvline(hour, linestyle='--', color='black', alpha=0.1)

        # Remove gridlines
        plt.grid(True)

        # Compute the minimum and maximum temperature for each day and their respective indexes
        dates = list(set(data.index.date))
        min_temps = []
        max_temps = []
        min_idx = []
        max_idx = []

        for date in dates:
            df = data.loc[data.index.date == date]
            min_temp = df.min().min()
            max_temp = df.max().max()
            min_idx.append(data.loc[data.index.date == date].idxmin().min())
            max_idx.append(data.loc[data.index.date == date].idxmax().min())
            min_temps.append(min_temp)
            max_temps.append(max_temp)

        # Add the minimum temperature text to the plot
        #for i, temp in enumerate(min_temps):
         #   min_temp = "{:.1f}".format(temp)
         #   ax.text(min_idx[i], temp, min_temp, ha='left', va='top', color='blue',fontweight="bold")

        # Add the maximum temperature text to the plot
        for i, temp in enumerate(max_temps):
            max_temp = "{:.1f}".format(temp)
            ax.text(max_idx[i], temp, max_temp, ha='left', va='bottom', color='red',fontweight="bold")


        # Format x-axis ticks
        # Format x-axis ticks
        ticks = []
        tick_labels = []
        for date in data.index:
                if date.hour == 0:
                    tick_labels.append(date.strftime('%a, %b %d'))
                    ax.axvline(date,0,1,color="black",linewidth=2)
                    ticks.append(date)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

        ax.set_ylim(bottom=0)

        return fig

def plot_rain_chance(chance_prec,avg_prec):

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
    dates_unique = list(set(avg_prec.index.date))
    for date in dates_unique:
        midnight = datetime.combine(date, datetime.min.time())
        fig.add_vline(x=midnight, line_width=1.5, line_color="rgba(255,255,255,0.5)", row='all', col=1)

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

st.plotly_chart(plot_rain_chance(chance_prec,avg_prec), use_container_width=True)
st.divider()

#######################################################
wind_data = get_wind_gust_data(valid_run)
wind_data["Actual data"] = aemet_horario["Racha (km/h)"]

def plot_wind_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns[:-1]:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Actual data
    fig.add_trace(go.Scatter(
        x=data.index, y=data["Actual data"],
        mode='lines',
        line=dict(color='white', width=4),
        name='Datos Actuales',
        hovertemplate='%{x|%a %d %H:%M}<br><b>Racha Actual: %{y:.0f} km/h</b><extra></extra>'
    ))

    # Add Max/Min annotations per day
    dates = list(set(data.index.date))
    for date in dates:
        df_day = data.loc[data.index.date == date]
        if not df_day.empty:
            min_temp = df_day.min().min()
            max_temp = df_day.max().max()
            
            idx_min = df_day.min(axis=1).idxmin()
            idx_max = df_day.max(axis=1).idxmax()

            fig.add_annotation(
                x=idx_min, y=min_temp,
                text=f"{min_temp:.0f}",
                showarrow=False,
                yshift=-15,
                font=dict(color="#4facfe", size=12, family="Inter", weight="bold")
            )
            fig.add_annotation(
                x=idx_max, y=max_temp,
                text=f"{max_temp:.0f}",
                showarrow=False,
                yshift=15,
                font=dict(color="#ff6b6b", size=12, family="Inter", weight="bold")
            )

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

st.plotly_chart(plot_wind_data(wind_data), use_container_width=True)
st.divider()

#@#############################################

pressure_data = get_pressure_data(valid_run)

def plot_pressure_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns[:-1]:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

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

st.plotly_chart(plot_pressure_data(pressure_data), use_container_width=True)
st.divider()

################################################

mucape_data = get_mucape_data(valid_run)

def plot_mucape_data(data):
    fig = go.Figure()

    # Iterate over the columns and plot each one
    for column in data.columns[:-1]:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[column],
            mode='lines',
            line=dict(width=1),
            opacity=0.6,
            name=str(column),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Add danger zones
    fig.add_hrect(y0=0, y1=300, fillcolor="green", opacity=0.1, line_width=0, layer="below")
    fig.add_hrect(y0=300, y1=1000, fillcolor="yellow", opacity=0.1, line_width=0, layer="below")
    fig.add_hrect(y0=1000, y1=3000, fillcolor="red", opacity=0.1, line_width=0, layer="below")

    fig.update_layout(
        title=dict(text='Potencial de Tormentas (MUCAPE) (48h)', font=dict(color='white', size=18, family="Inter")),
        xaxis=dict(
            title='', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)', 
            tickformat='%a %d\n%H:%M',
            color='white'
        ),
        yaxis=dict(
            title='J/kg', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            rangemode='tozero'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )

    return fig

st.plotly_chart(plot_mucape_data(mucape_data), use_container_width=True)
st.divider()




st.divider()


@st.cache_data(ttl=60*60)
def get_forecast_data():
     data = pd.read_json("https://api.open-meteo.com/v1/forecast?latitude=40.65&longitude=-4.69&hourly=temperature_2m,precipitation,pressure_msl,cloudcover,windspeed_10m,windgusts_10m,cape&current_weather=true&timezone=Europe%2FBerlin&past_days=1&models=ecmwf_ifs04,gfs_global,icon_eu,meteofrance_arpege_europe,meteofrance_arome_france_hd")
     return data

data = get_forecast_data()

nombre_cape = "cape_"
nombre_nubes = "cloudcover_"
nombre_preci = "precipitation_"
nombre_presion = "pressure_msl_"
nombre_temp = "temperature_2m_"
nombre_rachas = "windgusts_10m_"
nombre_viento = "windspeed_10m_"

modelo_gfs = "gfs_global"
modelo_europeo = "ecmwf_ifs04"
modelo_icon = "icon_eu"
modelo_arome = "meteofrance_arome_france_hd"
modelo_arpege = "meteofrance_arpege_europe"

time = data.loc["time"]["hourly"]


data_presion_df = pd.DataFrame(index=pd.to_datetime(time))
data_presion_df["ECMWF"] = data.loc[nombre_presion+modelo_europeo]["hourly"]
data_presion_df["GFS"] = data.loc[nombre_presion+modelo_gfs]["hourly"]
data_presion_df["AROME"] = data.loc[nombre_presion+modelo_arome]["hourly"]
data_presion_df["ARPEGE"] = data.loc[nombre_presion+modelo_arpege]["hourly"]
data_presion_df["ICON"] = data.loc[nombre_presion+modelo_icon]["hourly"]



data_cape_df = pd.DataFrame(index=pd.to_datetime(time))
data_cape_df["GFS"] = data.loc[nombre_cape+modelo_gfs]["hourly"]
data_cape_df["AROME"] = data.loc[nombre_cape+modelo_arome]["hourly"]
data_cape_df["ARPEGE"] = data.loc[nombre_cape+modelo_arpege]["hourly"]
data_cape_df["ICON"] = data.loc[nombre_cape+modelo_icon]["hourly"]


data_preci_df = pd.DataFrame(index=pd.to_datetime(time))
data_preci_df["ECMWF"] = data.loc[nombre_preci+modelo_europeo]["hourly"]
data_preci_df["GFS"] = data.loc[nombre_preci+modelo_gfs]["hourly"]
data_preci_df["AROME"] = data.loc[nombre_preci+modelo_arome]["hourly"]
data_preci_df["ARPEGE"] = data.loc[nombre_preci+modelo_arpege]["hourly"]
data_preci_df["ICON"] = data.loc[nombre_preci+modelo_icon]["hourly"]



data_rachas_df = pd.DataFrame(index=pd.to_datetime(time))
data_rachas_df["GFS"] = data.loc[nombre_rachas+modelo_gfs]["hourly"]
data_rachas_df["AROME"] = data.loc[nombre_rachas+modelo_arome]["hourly"]
data_rachas_df["ARPEGE"] = data.loc[nombre_rachas+modelo_arpege]["hourly"]
data_rachas_df["ICON"] = data.loc[nombre_rachas+modelo_icon]["hourly"]



data_nubes_df = pd.DataFrame(index=pd.to_datetime(time))
data_nubes_df["ECMWF"] = data.loc[nombre_nubes+modelo_europeo]["hourly"]
data_nubes_df["GFS"] = data.loc[nombre_nubes+modelo_gfs]["hourly"]
data_nubes_df["AROME"] = data.loc[nombre_nubes+modelo_arome]["hourly"]
data_nubes_df["ARPEGE"] = data.loc[nombre_nubes+modelo_arpege]["hourly"]
data_nubes_df["ICON"] = data.loc[nombre_nubes+modelo_icon]["hourly"]



data_temp_df = pd.DataFrame(index=pd.to_datetime(time))
data_temp_df["ECMWF"] = data.loc[nombre_temp+modelo_europeo]["hourly"]
data_temp_df["GFS"] = data.loc[nombre_temp+modelo_gfs]["hourly"]
data_temp_df["AROME"] = data.loc[nombre_temp+modelo_arome]["hourly"]
data_temp_df["ARPEGE"] = data.loc[nombre_temp+modelo_arpege]["hourly"]
data_temp_df["ICON"] = data.loc[nombre_temp+modelo_icon]["hourly"]



def all_hours_have_data(group):
    return group.notnull().all()

groups = data_temp_df.groupby(data_temp_df.index.date).apply(all_hours_have_data)
data_temp_max = data_temp_df.groupby(data_temp_df.index.date).max() * groups[groups==True]
data_temp_min = data_temp_df.groupby(data_temp_df.index.date).min() * groups[groups==True]


import matplotlib.pyplot as plt


def plot_long_forecast():
    fig = go.Figure()

    # Preparamos fechas para el eje x
    dates_str = pd.to_datetime(data_temp_min.index).strftime('%A %d').tolist()

    # Boxplot Temperaturas Mínimas (Azul)
    for i in range(8):
        day_data = data_temp_min.iloc[i,:].dropna()
        fig.add_trace(go.Box(
            y=day_data, x=[dates_str[i]]*len(day_data),
            name='Min',
            marker_color='#4facfe',
            line_color='#4facfe',
            fillcolor='rgba(77, 171, 247, 0.85)',
            boxpoints='outliers',
            offsetgroup='A',
            showlegend=False,
            width=0.35,
            line_width=2
        ))

    # Boxplot Temperaturas Máximas (Rojo)
    for i in range(8):
        day_data = data_temp_max.iloc[i,:].dropna()
        fig.add_trace(go.Box(
            y=day_data, x=[dates_str[i]]*len(day_data),
            name='Max',
            marker_color='#ff6b6b',
            line_color='#ff6b6b',
            fillcolor='rgba(255, 107, 107, 0.85)',
            boxpoints='outliers',
            offsetgroup='B',
            showlegend=False,
            width=0.35,
            line_width=2
        ))

    # Add Max/Min annotations per day
    for i in range(min(8, len(dates_str))):
        min_data = data_temp_min.iloc[i,:].dropna()
        max_data = data_temp_max.iloc[i,:].dropna()
        if not min_data.empty:
            fig.add_annotation(
                x=dates_str[i], y=min_data.min(),
                text=f"{min_data.min():.1f}º",
                showarrow=False,
                yshift=-15,
                font=dict(color="#4facfe", size=12, family="Inter", weight="bold")
            )
        if not max_data.empty:
            fig.add_annotation(
                x=dates_str[i], y=max_data.max(),
                text=f"{max_data.max():.1f}º",
                showarrow=False,
                yshift=15,
                font=dict(color="#ff6b6b", size=12, family="Inter", weight="bold")
            )

    # Actualizar diseño
    fig.update_layout(
        title=dict(text='Evolución Temperaturas (Próxima Semana)', font=dict(color='white', size=18, family="Inter")),
        boxmode='group',
        yaxis=dict(
            title='Temperatura (°C)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white'
        ),
        xaxis=dict(
            title='', 
            showgrid=False,
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified"
    )

    return fig

st.plotly_chart(plot_long_forecast(), use_container_width=True)
st.divider()



def plot_long_rain_forecast():
    fig = go.Figure()

    data_plotted = (6 * data_preci_df.resample("6H", closed="left", label="left").mean()).dropna(axis=1, how="all").T.iloc[:, :-10]
    
    date_list = []
    for item in data_plotted.columns.date:
        if item not in date_list:
            date_list.append(item)
    dates_str = pd.to_datetime(date_list).strftime('%A %d').tolist()

    # Cada iteración crea un boxplot para un bloque de 6 horas
    for i, col in enumerate(data_plotted.columns):
        day_date = col.date()
        date_idx = date_list.index(day_date)
        day_str = dates_str[date_idx]
        
        # Etiqueta por franja horaria
        hour_label = f"{col.hour:02d}:00"
        slot_label = f"{day_str}\n{hour_label}"
        
        fig.add_trace(go.Box(
            y=data_plotted[col].dropna(),
            x=[slot_label] * len(data_plotted[col].dropna()),
            name=hour_label,
            marker_color='#4facfe',
            line_color='#4facfe',
            fillcolor='rgba(77, 171, 247, 0.85)',
            boxpoints='outliers',
            showlegend=False,
            width=0.6,
            line_width=2
        ))

    # Actualizar diseño
    fig.update_layout(
        title=dict(text='Evolución Precipitación Diaria (Próxima Semana)', font=dict(color='white', size=18, family="Inter")),
        boxmode='group',
        yaxis=dict(
            title='Lluvia (L/m2)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            rangemode='tozero'
        ),
        xaxis=dict(
            title='', 
            showgrid=False,
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified"
    )

    return fig

st.plotly_chart(plot_long_rain_forecast(), use_container_width=True)
st.divider()


def plot_long_wind_forecast():
    fig = go.Figure()

    data_plotted = data_rachas_df.resample("6H", closed="left", label="left").mean().dropna(axis=1, how="all").T.iloc[:, :-18]
    
    date_list = []
    for item in data_plotted.columns.date:
        if item not in date_list:
            date_list.append(item)
    dates_str = pd.to_datetime(date_list).strftime('%A %d').tolist()

    for i, col in enumerate(data_plotted.columns):
        day_date = col.date()
        date_idx = date_list.index(day_date)
        day_str = dates_str[date_idx]
        
        hour_label = f"{col.hour:02d}:00"
        slot_label = f"{day_str}\n{hour_label}"
        
        fig.add_trace(go.Box(
            y=data_plotted[col].dropna(),
            x=[slot_label] * len(data_plotted[col].dropna()),
            name=hour_label,
            marker_color='gold',
            line_color='gold',
            fillcolor='rgba(255, 215, 0, 0.85)',
            boxpoints='outliers',
            showlegend=False,
            width=0.6,
            line_width=2
        ))

    # Actualizar diseño
    fig.update_layout(
        title=dict(text='Evolución Viento Rachas (Próxima Semana)', font=dict(color='white', size=18, family="Inter")),
        boxmode='group',
        yaxis=dict(
            title='Velocidad (km/h)', 
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            color='white',
            rangemode='tozero'
        ),
        xaxis=dict(
            title='', 
            showgrid=False,
            color='white'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified"
    )

    return fig

st.plotly_chart(plot_long_wind_forecast(), use_container_width=True)


import pytz
from astral import LocationInfo
from astral.sun import sun, elevation
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
import matplotlib.patheffects as pe

def plot_sun_elevation(latitude, longitude, timezone_str='UTC'):
    # Define location information
    location = LocationInfo("Custom Location", "Custom Region", timezone_str, latitude, longitude)

    # Get current date and time in the specified timezone
    tz = pytz.timezone(timezone_str)
    today = datetime.now(tz=tz)
    yesterday = today - timedelta(days=1)
    year, month, day = today.year, today.month, today.day

    # Calculate exact sunrise and sunset times for today and yesterday
    s_today = sun(location.observer, date=today)
    s_yesterday = sun(location.observer, date=yesterday)

    # Convert sunrise and sunset times to local timezone
    sunrise_local = s_today['sunrise'].astimezone(tz)
    sunset_local = s_today['sunset'].astimezone(tz)

    # Calculate day length for today and yesterday
    day_length_today = (s_today['sunset'] - s_today['sunrise']).total_seconds()
    day_length_yesterday = (s_yesterday['sunset'] - s_yesterday['sunrise']).total_seconds()

    # Calculate the difference in day length
    day_length_diff = day_length_today - day_length_yesterday
    diff_minutes, diff_seconds = divmod(abs(int(day_length_diff)), 60)
    daylight_change = f"{diff_minutes}m {diff_seconds}s {'ganados' if day_length_diff > 0 else 'perdidos'}"

    # Format sunrise/sunset times and day length for display
    sunrise_time = sunrise_local.strftime('%H:%M')
    sunset_time = sunset_local.strftime('%H:%M')
    day_length_hours = int(day_length_today // 3600)
    day_length_minutes = int((day_length_today % 3600) // 60)

    # Convert sunrise and sunset times to fractional hours
    sunrise_h = sunrise_local.hour + sunrise_local.minute / 60
    sunset_h = sunset_local.hour + sunset_local.minute / 60

    # Generate datetime objects for every minute of the day
    listahoras = [tz.localize(datetime(year, month, day, hour, minute))
                  for hour in range(24) for minute in range(60)]

    # Calculate sun elevation for each minute
    elevaciones = [elevation(location.observer, dt) for dt in listahoras]
    elevaciones_array = np.array(elevaciones)

    # Find the index of the maximum elevation
    max_elevation_index = int(np.argmax(elevaciones))
    max_elevation_time = listahoras[max_elevation_index].strftime('%H:%M')
    max_elev_val = elevaciones_array[max_elevation_index]

    # Current time
    current_time_index = today.hour * 60 + today.minute
    current_h = current_time_index / 60
    current_elev = elevaciones_array[min(current_time_index, 1439)]

    # Hours array
    hours = np.array([i / 60 for i in range(1440)])

    # ── Matplotlib figure ──
    fig, ax = plt.subplots(figsize=(14, 8), dpi=130)
    fig.patch.set_alpha(0)
    ax.set_facecolor('none')

    # ── Twilight bands (horizontal zones) ──
    twilight_zones = [
        (-18, -12, '#0c1445', 0.5, 'Astronómica'),
        (-12, -6, '#1a1b5e', 0.5, 'Náutica'),
        (-6,   0, '#2d2b6e', 0.5, 'Civil'),
    ]
    for y_lo, y_hi, color, alpha, label in twilight_zones:
        ax.axhspan(y_lo, y_hi, color=color, alpha=alpha, zorder=1, lw=0)

    # ── Daytime sky gradient fill (above horizon) ──
    elev_pos = np.maximum(elevaciones_array, 0)
    # Create vertical gradient effect for the day fill
    n_strips = 80
    max_e = max(elev_pos)
    if max_e > 0:
        for i in range(n_strips):
            y_lo = max_e * i / n_strips
            y_hi = max_e * (i + 1) / n_strips
            frac = i / n_strips
            # Warm gradient: deep amber at horizon → bright gold at top
            r = 1.0
            g = 0.55 + 0.35 * frac
            b = 0.05 + 0.15 * frac
            strip_y_lo = np.full_like(hours, y_lo)
            strip_y_hi = np.minimum(elev_pos, y_hi)
            strip_y_hi = np.maximum(strip_y_hi, y_lo)
            ax.fill_between(hours, strip_y_lo, strip_y_hi,
                          color=(r, g, b), alpha=0.6 - 0.2 * frac,
                          zorder=2, lw=0)

    # ── Night fill (below horizon) ──
    elev_neg = np.minimum(elevaciones_array, 0)
    ax.fill_between(hours, elev_neg, 0, color='#0d1b3e', alpha=0.7, zorder=2, lw=0)

    # ── Main elevation curve with gradient color ──
    points = np.array([hours, elevaciones_array]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Color by elevation: blues below, golds above
    norm_vals = (elevaciones_array[:-1] + elevaciones_array[1:]) / 2
    norm_range = max(abs(norm_vals.min()), abs(norm_vals.max()))
    norm_vals_normalized = (norm_vals + norm_range) / (2 * norm_range) if norm_range > 0 else norm_vals * 0 + 0.5

    curve_cmap = LinearSegmentedColormap.from_list('curve', [
        '#1a237e',   # deep blue (far below horizon)
        '#3949ab',   # medium blue
        '#7c4dff',   # purple (near horizon night)
        '#ff9100',   # orange (near horizon day)
        '#ffd54f',   # bright gold (high elevation)
        '#fff9c4',   # near-white gold (zenith)
    ])
    lc = LineCollection(segments, cmap=curve_cmap, norm=plt.Normalize(0, 1), zorder=5)
    lc.set_array(norm_vals_normalized)
    lc.set_linewidth(3)
    ax.add_collection(lc)

    # ── Horizon line ──
    ax.axhline(y=0, color='#b0bec5', linewidth=1.2, linestyle='--', alpha=0.6, zorder=4)
    ax.text(23.8, 0.8, 'HORIZONTE', fontsize=7, color='#78909c',
            ha='right', va='bottom', fontfamily='sans-serif', fontweight='bold',
            alpha=0.6, zorder=6)

    # ── Twilight labels (right side) ──
    tw_labels = [
        (-15, 'Tw. Astronómico', '#5c6bc0'),
        (-9, 'Tw. Náutico', '#7986cb'),
        (-3, 'Tw. Civil', '#9fa8da'),
    ]
    for y_pos, label, color in tw_labels:
        if y_pos > elevaciones_array.min():
            ax.text(23.8, y_pos, label, fontsize=6.5, color=color,
                    ha='right', va='center', fontfamily='sans-serif',
                    alpha=0.7, fontstyle='italic', zorder=6)

    # ── Sun marker at zenith ──
    zenith_h = max_elevation_index / 60
    # Outer glow
    for r, a in [(28, 0.05), (22, 0.08), (16, 0.12)]:
        ax.plot(zenith_h, max_elev_val, 'o', color='#ffab00', markersize=r, alpha=a, zorder=6)
    # Sun disc
    ax.plot(zenith_h, max_elev_val, 'o', color='#ffd740', markersize=14,
            markeredgecolor='#ff6f00', markeredgewidth=2, zorder=7)
    ax.plot(zenith_h, max_elev_val, 'o', color='#fff9c4', markersize=6, zorder=8)
    # Zenith label
    ax.annotate(f'CENIT  {max_elevation_time}\n{max_elev_val:.1f}°',
                xy=(zenith_h, max_elev_val), xytext=(0, 22),
                textcoords='offset points', ha='center', va='bottom',
                fontsize=9, fontweight='bold', color='#ffd740',
                fontfamily='sans-serif', zorder=8,
                path_effects=[pe.withStroke(linewidth=3, foreground='#111')])

    # ── Sunrise marker ──
    ax.plot(sunrise_h, 0, 'D', color='#ffab40', markersize=9,
            markeredgecolor='#e65100', markeredgewidth=1.5, zorder=7)
    ax.annotate(f'Amanecer\n{sunrise_time}',
                xy=(sunrise_h, 0), xytext=(-15, -28),
                textcoords='offset points', ha='center', va='top',
                fontsize=9, fontweight='bold', color='#ffcc80',
                fontfamily='sans-serif', zorder=8,
                path_effects=[pe.withStroke(linewidth=3, foreground='#111')])

    # ── Sunset marker ──
    ax.plot(sunset_h, 0, 'D', color='#ff7043', markersize=9,
            markeredgecolor='#bf360c', markeredgewidth=1.5, zorder=7)
    ax.annotate(f'Ocaso\n{sunset_time}',
                xy=(sunset_h, 0), xytext=(15, -28),
                textcoords='offset points', ha='center', va='top',
                fontsize=9, fontweight='bold', color='#ffab91',
                fontfamily='sans-serif', zorder=8,
                path_effects=[pe.withStroke(linewidth=3, foreground='#111')])

    # ── Current position marker ──
    # Dashed vertical line from horizon to current position
    ax.plot([current_h, current_h], [0, current_elev], '--',
            color='#e0e0e0', linewidth=1, alpha=0.5, zorder=5)
    # Pulsing glow
    for r, a in [(18, 0.06), (13, 0.1)]:
        ax.plot(current_h, current_elev, 'o', color='white', markersize=r, alpha=a, zorder=6)
    ax.plot(current_h, current_elev, 'o', color='white', markersize=8,
            markeredgecolor='#424242', markeredgewidth=1.5, zorder=7)
    ax.annotate(f'AHORA\n{today.strftime("%H:%M")}',
                xy=(current_h, current_elev), xytext=(0, 16),
                textcoords='offset points', ha='center', va='bottom',
                fontsize=8, fontweight='bold', color='white',
                fontfamily='sans-serif', zorder=8,
                path_effects=[pe.withStroke(linewidth=3, foreground='#111')])

    # ── Axes styling ──
    ax.set_xlim(0, 24)
    ax.set_ylim(elevaciones_array.min() - 5, max_elev_val + 15)
    ax.set_xticks(range(0, 25, 2))
    ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)],
                       fontsize=8, color='#b0bec5', fontfamily='sans-serif')
    ax.set_yticks(range(int(elevaciones_array.min() // 10) * 10, int(max_elev_val) + 10, 10))
    ax.set_yticklabels([f'{v}°' for v in range(int(elevaciones_array.min() // 10) * 10, int(max_elev_val) + 10, 10)],
                       fontsize=8, color='#b0bec5', fontfamily='sans-serif')

    ax.tick_params(axis='both', colors='#546e7a', length=4, width=0.8)
    ax.grid(True, alpha=0.08, color='#b0bec5', linewidth=0.5)

    # Spines
    for spine in ax.spines.values():
        spine.set_color('#1a237e')
        spine.set_linewidth(0.8)

    # ── Title ──
    ax.set_title(
        f'Perfil de Elevación Solar  ·  {today.strftime("%A %d de %B, %Y")}',
        fontsize=15, fontweight='bold', color='#e0e0e0',
        fontfamily='sans-serif', pad=20
    )
    ax.text(0.5, 1.02,
            f'Duracion del dia: {day_length_hours}h {day_length_minutes}m  |  {daylight_change}  |  {sunrise_time} -- {sunset_time}',
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=9, color='#90a4ae', fontfamily='sans-serif')

    ax.set_xlabel('')
    ax.set_ylabel('')

    fig.tight_layout(pad=2)

    return fig

st.pyplot(plot_sun_elevation(40.65744607301477, -4.696006449529498, 'Europe/Madrid'), use_container_width=True)

#model = genai.GenerativeModel(('gemini-3-flash-preview'))
import json

def process_multi_model_dataframe(df):
    """Process a dataframe with timestamp index and 17 forecast columns."""
    processed_data = []
    for timestamp, row in df.iterrows():
        forecasts = row.tolist()
        processed_data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),  # Convert timestamp to string
            'forecasts': forecasts
        })
    return processed_data


weather_data = {
    'temperature': process_multi_model_dataframe(temp_data),
    'wind': process_multi_model_dataframe(wind_data),
    'precipitation': process_multi_model_dataframe(prec_data),
    'pressure': process_multi_model_dataframe(pressure_data),
    'mucape': process_multi_model_dataframe(mucape_data)
}

weather_json = json.dumps(weather_data)

def generate_llm_input(weather_json):
    # Load the meteorological data
    meteo_data = weather_json

    # Define the prompt
    prompt = """ PROVIDE THE WHOLE RESPONSE IN SPANISH FROM SPAIN. THE FORECAST IS FOR ÁVILA, SPAIN. USE THIS AS CLIMATE CONTEXT FOR YOUR ANSWERS.

You are a professional meteorologist tasked with analyzing and commenting on weather forecast data for the next 48 hours. The data provided includes hourly information on temperature, wind, precipitation, pressure, and MUCAPE (Most Unstable Convective Available Potential Energy).

## Data Analysis Tasks:

1. Summarize the overall weather pattern for the 48-hour period.

2. Identify and report on key data points:
   - Temperature: Highlight daily highs and lows, and any significant temperature changes.
   - Wind: Report on average wind speeds, signalling hazardous values.
   - Precipitation: Summarize total expected precipitation and identify periods of heaviest rainfall.
   - MUCAPE: Interpret MUCAPE values to assess the potential for thunderstorm development. For your analysis, take into account only those values higher than 250. Consider that severe thunderstorm only develop when MUCAPE is at least 1000.

3. Model Alignment:
   - Analyze the consistency of the data across different weather models.
   - Highlight any significant discrepancies between models and explain their potential implications.

4. Risk Assessment:
   - Identify any potential weather risks or hazards, such as:
     - Extreme temperatures (heat waves or cold snaps)
     - Strong winds or wind gusts
     - Heavy precipitation leading to flooding risks
     - Severe thunderstorm potential based on MUCAPE values and other factors
   - Provide a severity rating for each identified risk (e.g., low, moderate, high, extreme).

5. Special Weather Phenomena:
   - Note any unusual or noteworthy weather patterns or events that may occur during this period.

## Output Format:

1. Executive Summary (2-3 sentences overview)
2. Detailed Analysis (broken down by weather component). Include emojis identifying every field.
3. Model Comparison and Uncertainty Discussion
4. Risk Assessment and Warnings. Include emojis identifying every field.
5. Concluding Remarks and Forecast Confidence

Please provide your analysis in clear, concise language suitable for both meteorological professionals and informed members of the public. Use meteorological terminology where appropriate, but explain complex concepts when necessary.

## Meteorological Data:
"""

    # Combine the prompt and the data
    combined_input = f"{prompt}\n\n{json.dumps(meteo_data, indent=2)}"

    return combined_input


#prompt = generate_llm_input(weather_json)
#response = client.models.generate_content(
#    model="gemini-3-flash-preview",
#    contents=prompt
#)

#st.write(response.text)