import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from scipy.stats import percentileofscore
import asyncio
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from arome_maps import render_arome_maps

#st.set_option('deprecation.showPyplotGlobalUse', False)

#st.write(datetime.now()+ timedelta(hours=2))

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    
    /* Fondo intermedio cálido global (Sepia / Arena Lino) y tipografía */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #e8e3da !important;
        color: #2a241f !important;
    }

    /* Cabecera superior integrada con el fondo (elimina la barra negra) */
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

    /* Separadores (dividers) visibles y elegantes */
    hr, [data-testid="stDivider"], .stDivider {
        border: none !important;
        height: 1.5px !important;
        background: linear-gradient(90deg, transparent 0%, #b8b0a2 15%, #948b7d 50%, #b8b0a2 85%, transparent 100%) !important;
        margin: 2rem 0 !important;
        opacity: 1 !important;
    }

    /* Sidebar intermedio cálido */
    section[data-testid="stSidebar"] {
        background-color: #ded8cd !important;
        border-right: 1px solid #c8c0b2;
    }
    
    /* Texto del Sidebar */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #2a241f;
    }

    /* Proteger iconos de Streamlit para que no aparezca el texto "keyboard_double_arrow_left" */
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarExpandButton"] *,
    [data-testid="stHeader"] button *,
    button[kind="header"] *,
    .material-symbols-outlined,
    [data-testid="stIcon"] {
        font-family: inherit !important;
    }

    /* Controles e Inputs */
    input, textarea, select, button {
        background-color: #f7f4ee !important;
        color: #2a241f !important;
        border: 1px solid #c8c0b2 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    /* Estilo minimalista para tablas HTML */
    .records-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 15px;
        font-size: 0.85rem;
    }
    .records-table th {
        text-align: left;
        padding: 8px;
        color: #635b53;
        font-weight: 600;
        border-bottom: 1px solid #c8c0b2;
    }
    .records-table td {
        padding: 8px;
        border-bottom: 1px solid #dcd5c9;
        color: #2a241f;
    }
    .records-table tr:hover {
        background-color: rgba(217, 119, 6, 0.06);
    }
    .records-table td.temp-max {
        color: #d93856 !important; /* Coral cálido */
        font-weight: 600;
    }
    .records-table td.temp-min {
        color: #0277bd !important; /* Teal/Azul cálido */
        font-weight: 600;
    }

    /* Rejilla responsiva para cámaras */
    .camera-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;
        margin-top: 15px;
    }
    .camera-card {
        border-radius: 14px;
        overflow: hidden;
        background: #f7f4ee;
        border: 1px solid #d6cfc4;
        box-shadow: 0 4px 14px -2px rgba(60, 50, 40, 0.08);
    }
    .camera-card img {
        width: 100%;
        height: auto;
        display: block;
    }
    </style>
    """,
    unsafe_allow_html=True
)


import requests
import telegram




#TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
#TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]





#bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

#async def send_telegram_message(message):
 #   await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


#def send_telegram_message_sync(message):
 #   asyncio.run(send_telegram_message(message))


#async def main():
#    await send_telegram_message(output_str)



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



prevision_tab, mapas_tab = st.tabs(
    [":material/dashboard: Previsión", ":material/map: Mapas AROME"],
    key="madrid_view",
    on_change="rerun",
)

if prevision_tab.open:
    with prevision_tab:
        st.header("Madrid")


        valid_run = get_last_arome_run()


        ###############

        aemet_horario = pd.read_csv("https://www.aemet.es/es/eltiempo/observacion/ultimosdatos_3195_datos-horarios.csv?k=mad&l=3195&datos=det&w=0&f=temperatura&x=h24" ,
                                    encoding="latin-1",skiprows=2,parse_dates=True,index_col=0,dayfirst=True)
        aemet_horario.index = aemet_horario.index.tz_localize('Europe/Madrid')



        aemet_horario_acumulado = pd.read_excel("Histórico/Acumulado Madrid.xlsx",index_col=0)
        aemet_horario_acumulado.index = aemet_horario_acumulado.index.tz_localize('Europe/Madrid')

        aemet_horario_acumulado = pd.concat([aemet_horario_acumulado,aemet_horario])

        aemet_horario_acumulado = aemet_horario_acumulado[~aemet_horario_acumulado.index.duplicated(keep='first')]

        aemet_horario_acumulado = aemet_horario_acumulado.sort_index(ascending=False)

        aemet_horario_acumulado.index = aemet_horario_acumulado.index.tz_localize(None)

        #aemet_horario_acumulado.to_excel("Histórico/Acumulado Madrid.xlsx")


        #####################################################

        def get_temp_data(valid_run):

            url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.659&mode=8&sort=0'
            url_run = f'{url}&run={valid_run}'

            temp_data = get_arome_data(url_run)

            return temp_data

        def get_wind_gust_data(valid_run):

            url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.659&mode=13&sort=0'
            url_run = f'{url}&run={valid_run}'

            wind_gust_data = get_arome_data(url_run)

            return wind_gust_data

        def get_pressure_data(valid_run):

            url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.659&mode=1&sort=0'
            url_run = f'{url}&run={valid_run}'

            pressure_data = get_arome_data(url_run)

            return pressure_data

        def get_mucape_data(valid_run):

            url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.659&mode=0&sort=0'
            url_run = f'{url}&run={valid_run}'

            mucape_data = get_arome_data(url_run)

            return mucape_data

        def get_prec_data(valid_run):

            url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.659&mode=10&sort=0'
            url_run = f'{url}&run={valid_run}'

            prec_data = get_arome_data(url_run)

            return prec_data

        temp_data = get_temp_data(valid_run)
        wind_gust_data = get_wind_gust_data(valid_run)
        pressure_data = get_pressure_data(valid_run)
        mucape_data = get_mucape_data(valid_run)
        prec_data = get_prec_data(valid_run)




        #########################################################


        #####################################################

        datos_df_global = pd.read_csv("retiro 1950.csv",index_col="fecha",parse_dates=True)

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

        #col1,col2,col3 = st.columns(3,gap="small")

        #col1.metric(":thermometer: Actual (ºC)",temp_actual,(temp_actual-temp_ayer).round(1),delta_color="inverse")
        #col2.metric(":thermometer: Mañana (ºC)",temp_mañana,(temp_mañana-temp_actual).round(1),delta_color="inverse")
        #col3.metric("Fiabilidad",fiabilidad.round(1),help="Sobre la temperatura de mañana a esta hora, calculada sobre 10")


        # --- CÁLCULOS DE LÓGICA ---
        delta_hoy = (temp_actual - temp_ayer).round(1)
        delta_manana = (temp_mañana - temp_actual).round(1)
        fiab_val = fiabilidad.round(1)

        # Lógica de Delta (Colores e Iconos Cálidos)
        c_up = "#d93856"    # Coral cálido
        c_down = "#0277bd"  # Teal/Cielo cálido
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
        .weather-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 25px;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        }}

        .metric-card {{
            background: #f7f4ee;
            border: 1px solid #d6cfc4;
            padding: 20px;
            border-radius: 14px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            box-shadow: 0 4px 16px -2px rgba(60, 50, 40, 0.08);
            --card-hue: 30; 
        }}

        /* Efecto Hover Dinámico */
        .metric-card.temp-card:hover {{
            border-color: hsla(var(--card-hue), 85%, 45%, 0.5);
            box-shadow: 0 8px 24px -4px hsla(var(--card-hue), 85%, 40%, 0.18);
            transform: translateY(-3px);
            background: #ffffff;
        }}

        /* Hover simple para tarjeta de fiabilidad */
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
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #2a241f;
            margin: 0;
            line-height: 1;
            letter-spacing: -0.025em;
        }}

        .metric-delta {{
            font-size: 0.85rem;
            margin-top: 10px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        /* Barra de progreso */
        .progress-bg {{
            background: #ded8cd;
            height: 6px;
            border-radius: 3px;
            width: 100%;
            margin-top: 18px;
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

        <!-- CARD 1: ACTUAL -->
        <div class="metric-card temp-card" style="--card-hue: {hue_actual};">
        <div class="metric-label">Actual</div>
        <div class="metric-value">{temp_actual}º</div>
        <div class="metric-delta" style="color: {color_hoy}">
        {arrow_hoy} {abs(delta_hoy)}º <span style="font-weight: 400; opacity: 0.6; font-size: 0.9em; margin-left: 2px;">vs ayer</span>
        </div>
        </div>

        <!-- CARD 2: MAÑANA -->
        <div class="metric-card temp-card" style="--card-hue: {hue_manana};">
        <div class="metric-label">Mañana</div>
        <div class="metric-value">{temp_mañana}º</div>
        <div class="metric-delta" style="color: {color_manana}">
        {arrow_manana} {abs(delta_manana)}º <span style="font-weight: 400; opacity: 0.6; font-size: 0.9em; margin-left: 2px;">previsto</span>
        </div>
        </div>

        <!-- CARD 3: FIABILIDAD -->
        <div class="metric-card static-card">
        <div class="metric-label">Fiabilidad</div>
        <div class="metric-value">{fiab_val}<span style="font-size: 1.1rem; opacity: 0.4; font-weight: 400;"> / 10</span></div>
        <div class="progress-bg">
        <div class="progress-fill"></div>
        </div>
        </div>

        </div>
        """, unsafe_allow_html=True)

        st.divider()


        ##########################################################

        st.sidebar.markdown("### Récords para hoy:")

        records_html = f"""
        <table class="records-table">
          <thead>
            <tr>
              <th>Categoría</th>
              <th>T. Máx</th>
              <th>T. Mín</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Récord Calor</td>
              <td class="temp-max">{max_maxima}º <span style="font-size: 0.85em; opacity: 0.5;">({año_max_maxima})</span></td>
              <td class="temp-min">{min_maxima}º <span style="font-size: 0.85em; opacity: 0.5;">({año_min_maxima})</span></td>
            </tr>
            <tr>
              <td>Récord Frío</td>
              <td class="temp-max">{max_minima}º <span style="font-size: 0.85em; opacity: 0.5;">({año_max_minima})</span></td>
              <td class="temp-min">{min_minima}º <span style="font-size: 0.85em; opacity: 0.5;">({año_min_minima})</span></td>
            </tr>
          </tbody>
        </table>
        """
        st.sidebar.markdown(records_html, unsafe_allow_html=True)



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
        <div class="perc-text">{perc_val}<span style="font-size:0.75em; font-weight:400; opacity:0.6; margin-left:2px">perc</span></div>
        <div class="perc-track">
        <div class="perc-fill" style="width: {perc_val}%; background-size: {bg_size_percent:.0f}% 100%;"></div>
        </div>
        </div>
        </div>
        """

        # --- RENDERIZADO FINAL ---
        st.markdown(f"""
        <style>
        .weather-grid-perc {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 25px;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        }}

        .weather-grid-perc .metric-card {{
            background: #f7f4ee;
            border: 1px solid #d6cfc4;
            padding: 20px;
            border-radius: 14px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            box-shadow: 0 4px 16px -2px rgba(60, 50, 40, 0.08);
            --card-hue: 30; 
            cursor: help;
        }}

        .weather-grid-perc .metric-card.temp-card:hover {{
            border-color: hsla(var(--card-hue), 85%, 45%, 0.5);
            box-shadow: 0 8px 24px -4px hsla(var(--card-hue), 85%, 40%, 0.18);
            transform: translateY(-3px);
            background: #ffffff;
        }}

        .weather-grid-perc .metric-label {{
            font-size: 0.75rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #635b53;
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .weather-grid-perc .metric-value {{
            font-size: 2.25rem;
            font-weight: 700;
            color: #2a241f;
            margin: 0;
            line-height: 1;
            letter-spacing: -0.025em;
        }}

        .perc-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 12px;
        }}

        .perc-text {{
            font-size: 0.85rem;
            font-weight: 700;
            color: #403831;
            white-space: nowrap;
            width: 45px;
        }}

        .perc-track {{
            flex-grow: 1;
            height: 8px;
            background: #ded8cd;
            border-radius: 4px;
            overflow: hidden;
        }}

        .perc-fill {{
            height: 100%;
            /* Degradado cálido Turquesa - Ámbar - Coral */
            background-image: linear-gradient(90deg, #0277bd 0%, #d97706 50%, #d93856 100%);
            background-repeat: no-repeat;
            background-position: left center;
            border-radius: 4px;
            transition: width 0.5s ease-out;
        }}
        </style>

        <div class="weather-grid-perc">
        {html_content}
        </div>
        """, unsafe_allow_html=True)

        st.divider()




        # --- LÓGICA DE AVISOS Y GENERACIÓN HTML ---
        # Iconos SVG vectoriales para alertas (sin emoticonos)
        svg_warm = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="alert-svg"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>'
        svg_cold = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="alert-svg"><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/><path d="M20 12h-8M4 12h8M12 4v8M12 20v-8M16.39 8.39l-6.39 6.39M7.61 15.61l6.39-6.39M16.39 15.61L10 10M7.61 8.39L14 14"/></svg>'
        svg_rise = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="alert-svg"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>'
        svg_fall = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="alert-svg"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>'

        alerts_html = ""

        def create_alert(type_alert, svg_icon, text):
            c_class = "alert-warm" if type_alert == "warm" else "alert-cold"
            return f'<div class="alert-item {c_class}"><span class="alert-icon-container">{svg_icon}</span><span class="alert-text">{text}</span></div>'

        # --- CONDICIONALES ---

        # 1. Hoy
        if percentil_max_hoy > 80:     
             alerts_html += create_alert("warm", svg_warm, "Hoy hará mucho calor")
        elif percentil_max_hoy < 20:
             alerts_html += create_alert("cold", svg_cold, "Hoy hará mucho frío")

        # 2. Mañana
        if percentil_max_mañana > 80:     
             alerts_html += create_alert("warm", svg_warm, "Mañana hará mucho calor")
        elif percentil_max_mañana < 20:
             alerts_html += create_alert("cold", svg_cold, "Mañana hará mucho frío")

        # 3. Diferencia
        if (percentil_max_mañana - percentil_max_hoy) > 50:     
             alerts_html += create_alert("warm", svg_rise, "Mañana subirán mucho las temperaturas")
        elif (percentil_max_hoy - percentil_max_mañana) > 50:
             alerts_html += create_alert("cold", svg_fall, "Mañana bajarán mucho las temperaturas")

        # --- RENDERIZADO ---
        if alerts_html:
            st.markdown(f"""
        <style>
        .alerts-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 25px;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        }}
        .alert-item {{
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid;
            transition: transform 0.2s ease;
            flex: 1 1 auto;
            min-width: 200px;
            max-width: fit-content;
        }}
        .alert-item:hover {{
            transform: translateY(-2px);
        }}
        .alert-warm {{
            background: #fdf6e7;
            border-color: #fce7c6;
            color: #b45309;
        }}
        .alert-cold {{
            background: #eefbfe;
            border-color: #c5f3fa;
            color: #0369a1;
        }}
        .alert-icon-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            color: currentColor;
            flex-shrink: 0;
        }}
        .alert-text {{
            font-size: 0.9rem;
            font-weight: 500;
            letter-spacing: 0.01em;
        }}
        </style>
        <div class="alerts-container">
        {alerts_html}
        </div>
        """, unsafe_allow_html=True)

        st.divider()


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

        def plot_temp_data(data):
            fig = go.Figure()

            ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
            ens_data = data[ens_cols]
            ens_mean = ens_data.mean(axis=1)
            ens_p10 = ens_data.quantile(0.1, axis=1)
            ens_p90 = ens_data.quantile(0.9, axis=1)

            # Ensemble runs (líneas sutiles tono taupe, sin saturar el hover)
            for column in ens_cols:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data[column],
                    mode='lines',
                    line=dict(color='rgba(99, 91, 83, 0.22)', width=1),
                    name=f"Miembro {column}",
                    showlegend=False,
                    hoverinfo='skip'
                ))

            # Media Ensemble + Rango en línea dedicada debajo
            fig.add_trace(go.Scatter(
                x=data.index, y=ens_mean,
                mode='lines',
                line=dict(color='#635b53', width=1.5, dash='dot'),
                name='Media Ens',
                customdata=np.stack([ens_p10, ens_p90], axis=-1),
                hovertemplate='Media Ens: <b>%{y:.1f}°C</b><br>Rango 10-90%: <b>%{customdata[0]:.1f}° - %{customdata[1]:.1f}°C</b><extra></extra>'
            ))

            # Run Control (Ctrl) destacada en Ámbar/Terracota
            if "Ctrl" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Ctrl"],
                    mode='lines',
                    line=dict(color='#d97706', width=2.5, dash='dash'),
                    name='Run Control (Ctrl)',
                    hovertemplate='Control (Ctrl): <b>%{y:.1f}°C</b><extra></extra>'
                ))

            # Actual data (Línea destacada carbón/espresso profundo)
            if "Actual data" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Actual data"],
                    mode='lines',
                    line=dict(color='#2a241f', width=3),
                    name='Datos Actuales',
                    hovertemplate='Actual: <b>%{y:.1f}°C</b><extra></extra>'
                ))

            # Calculamos medias históricas
            max_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[0]
            max_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[1]
            min_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[0]
            min_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[1]

            # Rango máx habitual (Relleno coral cálido)
            fig.add_trace(go.Scatter(
                x=data.index.tolist() + data.index.tolist()[::-1],
                y=[max_usual_temp_upper]*len(data.index) + [max_usual_temp_lower]*len(data.index),
                fill='toself',
                fillcolor='rgba(217, 56, 86, 0.1)',
                line=dict(color='rgba(255,0,0,0)'),
                name='Rango Máx Habitual',
                hoverinfo='skip'
            ))

            # Rango mín habitual (Relleno teal cálido)
            fig.add_trace(go.Scatter(
                x=data.index.tolist() + data.index.tolist()[::-1],
                y=[min_usual_temp_upper]*len(data.index) + [min_usual_temp_lower]*len(data.index),
                fill='toself',
                fillcolor='rgba(2, 119, 189, 0.1)',
                line=dict(color='rgba(0,0,255,0)'),
                name='Rango Mín Habitual',
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
                        text=f"<b>{min_temp:.1f}º</b>",
                        showarrow=False,
                        yshift=-15,
                        font=dict(color="#0277bd", size=11, family="Plus Jakarta Sans, Inter")
                    )
                    fig.add_annotation(
                        x=idx_max, y=max_temp,
                        text=f"<b>{max_temp:.1f}º</b>",
                        showarrow=False,
                        yshift=15,
                        font=dict(color="#d93856", size=11, family="Plus Jakarta Sans, Inter")
                    )

            apply_custom_plotly_theme(fig, 'Previsión de Temperaturas (48h)', 'Temperatura (°C)', hovermode="x unified")
            return fig

        st.plotly_chart(plot_temp_data(temp_data), use_container_width=True)


        ##############################################

        #prec_data = get_prec_data(valid_run)
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

        def plot_rain_chance(chance_prec,avg_prec):

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                row_heights=[0.5, 0.5],
                                vertical_spacing=0.1)

            # Gráfico 1 (Arriba): Lluvia media en L/m2 (Línea + Área rellena turquesa)
            fig.add_trace(go.Scatter(
                x=avg_prec.index,
                y=avg_prec.iloc[:,0],
                mode='lines+markers',
                fill='tozeroy',
                fillcolor='rgba(2, 119, 189, 0.12)',
                name='Media (L/m2)',
                line=dict(color='#0277bd', width=2),
                marker=dict(size=4),
                hovertemplate='Lluvia Media: <b>%{y} L/m2</b><extra></extra>'
            ), row=1, col=1)

            # Gráfico 2 (Abajo): Probabilidad de lluvia (Bar chart ámbar)
            fig.add_trace(go.Bar(
                x=chance_prec.index,
                y=chance_prec.iloc[:,0],
                name='Probabilidad (%)',
                marker=dict(color='#d97706', line=dict(color='rgba(0,0,0,0.05)', width=1)),
                hovertemplate='Probabilidad: <b>%{y}%</b><extra></extra>'
            ), row=2, col=1)

            # Líneas verticales indicando medianoche (muy tenues)
            dates_unique = list(set(avg_prec.index.date))
            for date in dates_unique:
                midnight = datetime.combine(date, datetime.min.time())
                fig.add_vline(x=midnight, line_width=1, line_color="rgba(60, 50, 40, 0.15)", row='all', col=1)

            fig.update_layout(
                title=dict(text='Previsión de Lluvia (48h)', font=dict(color='#2a241f', size=16, family="Plus Jakarta Sans, Inter")),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                hoverlabel=dict(
                    bgcolor='rgba(247, 244, 238, 0.96)',
                    bordercolor='#d6cfc4',
                    font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12),
                    align='left'
                ),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=60, b=10),
                showlegend=False
            )
    
            fig.update_xaxes(
                showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)',
                linecolor='rgba(60, 50, 40, 0.25)', tickcolor='rgba(60, 50, 40, 0.25)',
                color='#2a241f', tickfont=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11),
                tickformat='%a %d\n%H:%M'
            )
            fig.update_yaxes(title_text="L/m2", title_font=dict(color='#2a241f', size=11, family="Plus Jakarta Sans, Inter"), showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)', linecolor='rgba(60, 50, 40, 0.25)', color='#2a241f', tickfont=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11), row=1, col=1, rangemode='tozero')
            fig.update_yaxes(title_text="Probabilidad %", title_font=dict(color='#2a241f', size=11, family="Plus Jakarta Sans, Inter"), showgrid=True, gridcolor='rgba(60, 50, 40, 0.12)', linecolor='rgba(60, 50, 40, 0.25)', color='#2a241f', tickfont=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=11), range=[0, 105], row=2, col=1)

            return fig


        st.plotly_chart(plot_rain_chance(chance_prec,avg_prec), use_container_width=True)

        #######################################################
        #wind_data = get_wind_gust_data(valid_run)
        wind_gust_data["Actual data"] = aemet_horario["Racha (km/h)"]

        def plot_wind_data(data):
            fig = go.Figure()

            ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
            ens_data = data[ens_cols]
            ens_mean = ens_data.mean(axis=1)

            # Ensemble runs (líneas naranja cálido tenues, sin saturar hover)
            for column in ens_cols:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data[column],
                    mode='lines',
                    line=dict(color='rgba(217, 119, 6, 0.22)', width=1),
                    name=f"Miembro {column}",
                    showlegend=False,
                    hoverinfo='skip'
                ))

            # Media Ensemble
            fig.add_trace(go.Scatter(
                x=data.index, y=ens_mean,
                mode='lines',
                line=dict(color='#b45309', width=1.5, dash='dot'),
                name='Media Ensemble',
                hovertemplate='Media Ens: <b>%{y:.0f} km/h</b><extra></extra>'
            ))

            # Run Control (Ctrl) destacada en Ámbar/Terracota
            if "Ctrl" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Ctrl"],
                    mode='lines',
                    line=dict(color='#d97706', width=2.5, dash='dash'),
                    name='Run Control (Ctrl)',
                    hovertemplate='Control (Ctrl): <b>%{y:.0f} km/h</b><extra></extra>'
                ))

            # Actual data (Línea destacada carbón/espresso profundo)
            if "Actual data" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Actual data"],
                    mode='lines',
                    line=dict(color='#2a241f', width=3),
                    name='Datos Actuales',
                    hovertemplate='Racha Actual: <b>%{y:.0f} km/h</b><extra></extra>'
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
                        text=f"<b>{min_temp:.0f}</b>",
                        showarrow=False,
                        yshift=-15,
                        font=dict(color="#0277bd", size=11, family="Plus Jakarta Sans, Inter")
                    )
                    fig.add_annotation(
                        x=idx_max, y=max_temp,
                        text=f"<b>{max_temp:.0f}</b>",
                        showarrow=False,
                        yshift=15,
                        font=dict(color="#d93856", size=11, family="Plus Jakarta Sans, Inter")
                    )

            apply_custom_plotly_theme(fig, 'Previsión de Viento (Rachas) (48h)', 'Velocidad (km/h)', hovermode="x unified")
            return fig


        st.plotly_chart(plot_wind_data(wind_gust_data), use_container_width=True)

        #@#############################################

        #pressure_data = get_pressure_data(valid_run)

        def plot_pressure_data(data):
            fig = go.Figure()

            ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
            ens_data = data[ens_cols]
            ens_mean = ens_data.mean(axis=1)

            # Ensemble runs (líneas sutiles tono stone, sin saturar hover)
            for column in ens_cols:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data[column],
                    mode='lines',
                    line=dict(color='rgba(99, 91, 83, 0.22)', width=1),
                    name=f"Miembro {column}",
                    showlegend=False,
                    hoverinfo='skip'
                ))

            # Media Ensemble
            fig.add_trace(go.Scatter(
                x=data.index, y=ens_mean,
                mode='lines',
                line=dict(color='#635b53', width=1.5, dash='dot'),
                name='Media Ensemble',
                hovertemplate='Media Ens: <b>%{y:.1f} hPa</b><extra></extra>'
            ))

            # Run Control (Ctrl) destacada en Ámbar/Terracota
            if "Ctrl" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Ctrl"],
                    mode='lines',
                    line=dict(color='#d97706', width=2.5, dash='dash'),
                    name='Run Control (Ctrl)',
                    hovertemplate='Control (Ctrl): <b>%{y:.1f} hPa</b><extra></extra>'
                ))

            # Actual data (si existiera)
            if "Actual data" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Actual data"],
                    mode='lines',
                    line=dict(color='#2a241f', width=3),
                    name='Datos Actuales',
                    hovertemplate='Presión Actual: <b>%{y:.1f} hPa</b><extra></extra>'
                ))

            apply_custom_plotly_theme(fig, 'Previsión de Presión Atmosférica (48h)', 'Presión (hPa)', hovermode="x unified")
            fig.update_layout(yaxis=dict(range=[980, 1040]))
            return fig


        st.plotly_chart(plot_pressure_data(pressure_data), use_container_width=True)

        ################################################

        #mucape_data = get_mucape_data(valid_run)

        def plot_mucape_data(data):
            fig = go.Figure()

            ens_cols = [c for c in data.columns if c not in ["Actual data", "Ctrl"]]
            ens_data = data[ens_cols]
            ens_mean = ens_data.mean(axis=1)
            ens_max = ens_data.max(axis=1)

            # Ensemble runs (líneas coral cálido tenues)
            for column in ens_cols:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data[column],
                    mode='lines',
                    line=dict(color='rgba(225, 29, 72, 0.2)', width=1),
                    name=f"Miembro {column}",
                    showlegend=False,
                    hoverinfo='skip'
                ))

            # Media Ensemble + Máximo (Resumen activo en hover)
            fig.add_trace(go.Scatter(
                x=data.index, y=ens_mean,
                mode='lines',
                line=dict(color='#d97706', width=1.5, dash='dot'),
                name='Media Ens',
                customdata=ens_max,
                hovertemplate='Media CAPE: <b>%{y:.0f} J/kg</b><br>Máx Ens: <b>%{customdata:.0f} J/kg</b><extra></extra>'
            ))

            # Run Control (Ctrl) destacada en Coral/Rojo
            if "Ctrl" in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data["Ctrl"],
                    mode='lines',
                    line=dict(color='#d93856', width=2.5, dash='dash'),
                    name='Run Control (Ctrl)',
                    hovertemplate='Control (Ctrl): <b>%{y:.0f} J/kg</b><extra></extra>'
                ))

            # Add danger zones (extremely subtle)
            fig.add_hrect(y0=0, y1=300, fillcolor="#10b981", opacity=0.04, line_width=0, layer="below")
            fig.add_hrect(y0=300, y1=1000, fillcolor="#fbbf24", opacity=0.04, line_width=0, layer="below")
            fig.add_hrect(y0=1000, y1=3000, fillcolor="#ef4444", opacity=0.04, line_width=0, layer="below")

            apply_custom_plotly_theme(fig, 'Potencial de Tormentas (MUCAPE) (48h)', 'J/kg', hovermode="x unified")
            return fig


        st.plotly_chart(plot_mucape_data(mucape_data), use_container_width=True)



        st.divider()


        @st.cache_data(ttl=60*60)
        def get_forecast_data():
             data = pd.read_json("https://api.open-meteo.com/v1/forecast?latitude=40.41&longitude=-3.659&hourly=temperature_2m,precipitation,pressure_msl,cloudcover,windspeed_10m,windgusts_10m,cape&current_weather=true&timezone=Europe%2FBerlin&past_days=1&models=ecmwf_ifs04,gfs_global,icon_eu,meteofrance_arpege_europe,meteofrance_arome_france_hd")
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

            dates_str = pd.to_datetime(data_temp_min.index).strftime('%A %d').tolist()

            summary_x = []
            summary_max_val = []
            summary_max_p20 = []
            summary_max_p80 = []
            summary_min_val = []
            summary_min_p20 = []
            summary_min_p80 = []

            for i in range(min(8, len(dates_str))):
                min_day_data = data_temp_min.iloc[i,:].dropna()
                max_day_data = data_temp_max.iloc[i,:].dropna()

                if min_day_data.empty or max_day_data.empty:
                    continue

                # Mínima Boxplot (sin tooltip ruidoso)
                fig.add_trace(go.Box(
                    y=min_day_data, x=[dates_str[i]]*len(min_day_data),
                    name='Mínima',
                    marker_color='#0284c7',
                    line_color='#0284c7',
                    fillcolor='rgba(2, 132, 199, 0.15)',
                    boxpoints='outliers',
                    offsetgroup='A',
                    showlegend=(i == 0),
                    width=0.35,
                    line_width=2,
                    hoverinfo='skip'
                ))

                # Máxima Boxplot (sin tooltip ruidoso)
                fig.add_trace(go.Box(
                    y=max_day_data, x=[dates_str[i]]*len(max_day_data),
                    name='Máxima',
                    marker_color='#d93856',
                    line_color='#d93856',
                    fillcolor='rgba(217, 56, 86, 0.15)',
                    boxpoints='outliers',
                    offsetgroup='B',
                    showlegend=(i == 0),
                    width=0.35,
                    line_width=2,
                    hoverinfo='skip'
                ))

                # Valores de Control o Media para anotación y hover
                max_ctrl = max_day_data["ECMWF"] if "ECMWF" in max_day_data.index and not pd.isna(max_day_data["ECMWF"]) else max_day_data.mean()
                min_ctrl = min_day_data["ECMWF"] if "ECMWF" in min_day_data.index and not pd.isna(min_day_data["ECMWF"]) else min_day_data.mean()

                max_p20 = max_day_data.quantile(0.20)
                max_p80 = max_day_data.quantile(0.80)
                min_p20 = min_day_data.quantile(0.20)
                min_p80 = min_day_data.quantile(0.80)

                summary_x.append(dates_str[i])
                summary_max_val.append(max_ctrl)
                summary_max_p20.append(max_p20)
                summary_max_p80.append(max_p80)
                summary_min_val.append(min_ctrl)
                summary_min_p20.append(min_p20)
                summary_min_p80.append(min_p80)

                # Anotación ploteada en el gráfico: VALOR DE CONTROL / MEDIA
                fig.add_annotation(
                    x=dates_str[i], y=min_ctrl,
                    text=f"<b>{min_ctrl:.1f}º</b>",
                    showarrow=False,
                    yshift=-15,
                    font=dict(color="#0284c7", size=10.5, family="Plus Jakarta Sans, Inter")
                )
                fig.add_annotation(
                    x=dates_str[i], y=max_ctrl,
                    text=f"<b>{max_ctrl:.1f}º</b>",
                    showarrow=False,
                    yshift=15,
                    font=dict(color="#d93856", size=10.5, family="Plus Jakarta Sans, Inter")
                )

            # Trazada de resumen para la tarjeta de hover limpia (Máxima y Mínima en la misma tarjeta, solo Control + 20-80%)
            if summary_x:
                fig.add_trace(go.Scatter(
                    x=summary_x,
                    y=summary_max_val,
                    mode='markers',
                    marker=dict(size=0.1, color='rgba(0,0,0,0)'),
                    name='Resumen',
                    showlegend=False,
                    customdata=np.stack([
                        summary_max_val, summary_max_p20, summary_max_p80,
                        summary_min_val, summary_min_p20, summary_min_p80
                    ], axis=-1),
                    hovertemplate=(
                        '<b>Máxima:</b> <b>%{customdata[0]:.1f}°C</b> (20-80%: %{customdata[1]:.1f}° - %{customdata[2]:.1f}°C)<br>'
                        '<b>Mínima:</b> <b>%{customdata[3]:.1f}°C</b> (20-80%: %{customdata[4]:.1f}° - %{customdata[5]:.1f}°C)<extra></extra>'
                    )
                ))

            apply_custom_plotly_theme(fig, 'Evolución Temperaturas (Próxima Semana)', 'Temperatura (°C)')
            fig.update_layout(
                boxmode='group',
                hoverlabel=dict(
                    bgcolor='rgba(247, 244, 238, 0.96)',
                    bordercolor='#d6cfc4',
                    font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12),
                    align='left'
                )
            )

            return fig


        st.plotly_chart(plot_long_forecast(), use_container_width=True)


        def plot_long_rain_forecast():
            fig = go.Figure()

            daily_prec = data_preci_df.groupby(data_preci_df.index.date).sum()
            daily_prec = daily_prec.dropna(how='all')
            dates_str = pd.to_datetime(daily_prec.index).strftime('%A %d').tolist()

            summary_x = []
            summary_ctrl = []
            summary_p20 = []
            summary_p80 = []

            for i in range(len(dates_str)):
                day_vals = daily_prec.iloc[i].dropna()
                if day_vals.empty:
                    continue

                fig.add_trace(go.Box(
                    y=day_vals, x=[dates_str[i]]*len(day_vals),
                    name='Acumulado Lluvia',
                    marker_color='#0284c7',
                    line_color='#0284c7',
                    fillcolor='rgba(2, 132, 199, 0.15)',
                    boxpoints='all',
                    showlegend=False,
                    width=0.45,
                    line_width=2,
                    hoverinfo='skip'
                ))

                ctrl_val = day_vals["ECMWF"] if "ECMWF" in day_vals.index and not pd.isna(day_vals["ECMWF"]) else day_vals.mean()
                p20_val = day_vals.quantile(0.20)
                p80_val = day_vals.quantile(0.80)

                summary_x.append(dates_str[i])
                summary_ctrl.append(ctrl_val)
                summary_p20.append(p20_val)
                summary_p80.append(p80_val)

                # Anotación: Valor de Control / Media
                if ctrl_val > 0.1:
                    fig.add_annotation(
                        x=dates_str[i], y=ctrl_val,
                        text=f"<b>{ctrl_val:.1f} L/m²</b>",
                        showarrow=False,
                        yshift=14,
                        font=dict(color="#0284c7", size=10.5, family="Plus Jakarta Sans, Inter")
                    )

            if summary_x:
                fig.add_trace(go.Scatter(
                    x=summary_x,
                    y=summary_ctrl,
                    mode='markers',
                    marker=dict(size=0.1, color='rgba(0,0,0,0)'),
                    name='Resumen Lluvia',
                    showlegend=False,
                    customdata=np.stack([summary_ctrl, summary_p20, summary_p80], axis=-1),
                    hovertemplate='Control/Media: <b>%{customdata[0]:.1f} L/m²</b> (20-80%: %{customdata[1]:.1f} - %{customdata[2]:.1f} L/m²)<extra></extra>'
                ))

            apply_custom_plotly_theme(fig, 'Evolución Precipitación Diaria (Próxima Semana)', 'Lluvia Acumulada (L/m²)')
            fig.update_layout(
                boxmode='group',
                hoverlabel=dict(
                    bgcolor='rgba(247, 244, 238, 0.96)',
                    bordercolor='#d6cfc4',
                    font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12),
                    align='left'
                )
            )

            return fig


        st.plotly_chart(plot_long_rain_forecast(), use_container_width=True)


        def plot_long_wind_forecast():
            fig = go.Figure()

            daily_wind = data_rachas_df.groupby(data_rachas_df.index.date).max()
            daily_wind = daily_wind.dropna(how='all')
            dates_str = pd.to_datetime(daily_wind.index).strftime('%A %d').tolist()

            summary_x = []
            summary_ctrl = []
            summary_p20 = []
            summary_p80 = []

            for i in range(len(dates_str)):
                day_vals = daily_wind.iloc[i].dropna()
                if day_vals.empty:
                    continue

                fig.add_trace(go.Box(
                    y=day_vals, x=[dates_str[i]]*len(day_vals),
                    name='Racha Máxima',
                    marker_color='#ea580c',
                    line_color='#ea580c',
                    fillcolor='rgba(234, 88, 12, 0.15)',
                    boxpoints='all',
                    showlegend=False,
                    width=0.45,
                    line_width=2,
                    hoverinfo='skip'
                ))

                ctrl_val = day_vals["ECMWF"] if "ECMWF" in day_vals.index and not pd.isna(day_vals["ECMWF"]) else day_vals.mean()
                p20_val = day_vals.quantile(0.20)
                p80_val = day_vals.quantile(0.80)

                summary_x.append(dates_str[i])
                summary_ctrl.append(ctrl_val)
                summary_p20.append(p20_val)
                summary_p80.append(p80_val)

                # Anotación: Valor de Control / Media
                fig.add_annotation(
                    x=dates_str[i], y=ctrl_val,
                    text=f"<b>{ctrl_val:.0f} km/h</b>",
                    showarrow=False,
                    yshift=14,
                    font=dict(color="#ea580c", size=10.5, family="Plus Jakarta Sans, Inter")
                )

            if summary_x:
                fig.add_trace(go.Scatter(
                    x=summary_x,
                    y=summary_ctrl,
                    mode='markers',
                    marker=dict(size=0.1, color='rgba(0,0,0,0)'),
                    name='Resumen Viento',
                    showlegend=False,
                    customdata=np.stack([summary_ctrl, summary_p20, summary_p80], axis=-1),
                    hovertemplate='Control/Media: <b>%{customdata[0]:.0f} km/h</b> (20-80%: %{customdata[1]:.0f} - %{customdata[2]:.0f} km/h)<extra></extra>'
                ))

            apply_custom_plotly_theme(fig, 'Evolución Viento Rachas (Próxima Semana)', 'Racha Máxima (km/h)')
            fig.update_layout(
                boxmode='group',
                hoverlabel=dict(
                    bgcolor='rgba(247, 244, 238, 0.96)',
                    bordercolor='#d6cfc4',
                    font=dict(color='#2a241f', family="Plus Jakarta Sans, Inter", size=12),
                    align='left'
                )
            )

            return fig


        st.plotly_chart(plot_long_wind_forecast(), use_container_width=True)

        st.divider()

        # --- GRÁFICO HISTÓRICO DE BOLITAS ---
        st.subheader("Temperaturas Históricas vs. Previsión")
        st.markdown("Distribución de las temperaturas registradas un día como hoy desde 1950. Los puntos destacados indican la previsión para hoy y mañana.")

        # Preparar datos históricos para el gráfico
        df_min_hist = pd.DataFrame({
            'Tipo': 'Mínima',
            'Temperatura': datos_df_global[datos_df_global["día_del_año"] == día_año_hoy]["tmin"].dropna(),
            'Año': datos_df_global[datos_df_global["día_del_año"] == día_año_hoy]["tmin"].dropna().index.year.astype(str),
        })

        df_max_hist = pd.DataFrame({
            'Tipo': 'Máxima',
            'Temperatura': datos_df_global[datos_df_global["día_del_año"] == día_año_hoy]["tmax"].dropna(),
            'Año': datos_df_global[datos_df_global["día_del_año"] == día_año_hoy]["tmax"].dropna().index.year.astype(str),
        })

        # Concatenamos y dibujamos un strip plot
        df_hist_plot = pd.concat([df_min_hist, df_max_hist])

        fig_hist = px.strip(
            df_hist_plot, 
            x="Tipo", 
            y="Temperatura", 
            color="Tipo",
            hover_data=["Año"],
            stripmode="overlay",
            color_discrete_sequence=['#0284c7', '#d93856'] 
        )

        # Ajustar las "bolitas" históricas (más discretas)
        fig_hist.update_traces(
            jitter=0.8,
            opacity=0.35,
            marker=dict(size=8, line=dict(width=0.5, color='rgba(99, 91, 83, 0.2)')),
            hovertemplate='<b>Año %{customdata[0]}</b><br>Temp %{x}: <b>%{y:.1f}°C</b><extra></extra>'
        )

        # Añadir los valores de Hoy (Esmeralda)
        fig_hist.add_trace(go.Scatter(
            x=['Mínima', 'Máxima'],
            y=[valor_min, valor_max],
            mode='markers+text',
            name='Prev. Hoy',
            marker=dict(size=16, color=['#059669', '#059669'], line=dict(width=2, color='white'), symbol='circle'),
            text=[f"<b>Hoy: {valor_min}º</b>", f"<b>Hoy: {valor_max}º</b>"],
            textposition='middle left',
            textfont=dict(color='#2a241f', size=11, family="Plus Jakarta Sans, Inter"),
            hovertemplate='<b>Previsión Hoy (%{x}): %{y:.1f}°C</b><extra></extra>'
        ))

        # Añadir los valores de Mañana (Ámbar)
        fig_hist.add_trace(go.Scatter(
            x=['Mínima', 'Máxima'],
            y=[valor_min_mañana, valor_max_mañana],
            mode='markers+text',
            name='Prev. Mañana',
            marker=dict(size=16, color=['#d97706', '#d97706'], line=dict(width=2, color='white'), symbol='diamond'),
            text=[f"<b>Mañana: {valor_min_mañana}º</b>", f"<b>Mañana: {valor_max_mañana}º</b>"],
            textposition='middle right',
            textfont=dict(color='#2a241f', size=11, family="Plus Jakarta Sans, Inter"),
            hovertemplate='<b>Previsión Mañana (%{x}): %{y:.1f}°C</b><extra></extra>'
        ))

        apply_custom_plotly_theme(fig_hist, '', 'Temperatura (°C)', show_legend=True, hovermode='closest')
        fig_hist.update_layout(xaxis=dict(showgrid=False))

        st.plotly_chart(fig_hist, use_container_width=True)

        st.divider()
        import pytz
        from astral import LocationInfo
        from astral.sun import sun, elevation
        import matplotlib.pyplot as plt
        import numpy as np

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

        #
        fig = plot_sun_elevation(40.41144776110279, -3.6787949052050672, 'Europe/Madrid')

        st.plotly_chart(fig, use_container_width=True)

        st.divider()


        def get_gfs_data(url):

        #url = 'https://www.meteociel.fr/modeles/gefs_table.php?x=0&y=0&lat=40.4165&lon=-3.70256&run=12&ext=1&mode=7&sort=2'  # Replace this with the URL containing the table

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

        def get_last_gfs_run():

            runs = [0, 6, 12, 18]  # GFS runs at 00, 06, 12, and 18 UTC
            url ='https://www.meteociel.fr/modeles/gefs_table.php?x=0&y=0&lat=40.4165&lon=-3.70256&ext=1&mode=7&sort=2'

            first_index = pd.Timestamp(year=2017, month=1, day=1,tz="UTC")

            for run in runs:
                url_run = f'{url}&run={run}'
                first_index_run = get_gfs_data(url_run).index[0]

                if first_index_run > first_index:
                    first_index = first_index_run
                    valid_run = run
                else:
                    pass

            return valid_run


        valid_run_gfs = get_last_gfs_run()


        def get_temp_data_gfs(valid_run_gfs):

            url ='https://www.meteociel.fr/modeles/gefs_table.php?x=0&y=0&lat=40.4165&lon=-3.70256&ext=1&mode=7&sort=0'
            url_run = f'{url}&run={valid_run_gfs}'

            temp_data = get_gfs_data(url_run)

            return temp_data

        temp_data_gfs = get_temp_data_gfs(valid_run_gfs)


        # Resample to get daily forecasts for maximum and minimum temperatures separately
        daily_data_max = temp_data_gfs.resample('D').max()
        daily_data_min = temp_data_gfs.resample('D').min()

        # Exclude the current day
        today = pd.Timestamp.now(tz=daily_data_max.index.tz).normalize()
        daily_data_max = daily_data_max[daily_data_max.index > today]
        daily_data_min = daily_data_min[daily_data_min.index > today]

        # Use the same daily index for the x-axis
        x = daily_data_max.index

        # For the ensemble forecasts, exclude the "GFS" column
        ensemble_cols_max = [col for col in daily_data_max.columns if col != "GFS"]
        ensemble_cols_min = [col for col in daily_data_min.columns if col != "GFS"]

        # Compute the envelope bounds for the maximum forecasts
        lower_bound_max = daily_data_max[ensemble_cols_max].min(axis=1)
        upper_bound_max = daily_data_max[ensemble_cols_max].max(axis=1)

        # Compute the envelope bounds for the minimum forecasts
        lower_bound_min = daily_data_min[ensemble_cols_min].min(axis=1)
        upper_bound_min = daily_data_min[ensemble_cols_min].max(axis=1)

        fig, ax = plt.subplots(figsize=(12, 6), facecolor='none')
        ax.set_facecolor('none')

        # Plot ensemble envelope for daily maximum temperatures
        ax.fill_between(x, lower_bound_max, upper_bound_max,
                        color="#d93856", alpha=0.1, label="Rango del Ensemble (máximas)")
        # Plot ensemble envelope for daily minimum temperatures
        ax.fill_between(x, lower_bound_min, upper_bound_min,
                        color="#0277bd", alpha=0.12, label="Rango del Ensemble (mínimas)")

        # Plot GFS forecast for maximum temperatures
        ax.plot(x, daily_data_max["GFS"], color="#d93856", linewidth=2,
                label="Predicción GFS (máx)")
        # Plot GFS forecast for minimum temperatures
        ax.plot(x, daily_data_min["GFS"], color="#0277bd", linewidth=2,
                label="Predicción GFS (mín)")

        # Add vertical gridlines for each day
        for day in x:
            ax.axvline(x=day, color="#635b53", linestyle="--", alpha=0.15)

        # Add small datalabels showing the GFS temperature for each day.
        for day, temp in zip(x, daily_data_max["GFS"]):
            ax.text(day, temp + 0.8, f"{temp:.1f}", ha="center", va="bottom", fontsize=8.5, color="#9f1239", weight="bold")
        for day, temp in zip(x, daily_data_min["GFS"]):
            ax.text(day, temp - 0.8, f"{temp:.1f}", ha="center", va="top", fontsize=8.5, color="#075985", weight="bold")

        ax.set_xlabel("Fecha", color="#2a241f", fontsize=10, fontweight='bold')
        ax.set_ylabel("Temperatura (°C)", color="#2a241f", fontsize=10, fontweight='bold')
        ax.set_title("Previsión Diaria GFS con Envolventes del Ensemble", color="#2a241f", fontsize=12, fontweight='bold', pad=15)

        # Customize tick colors
        ax.tick_params(colors="#2a241f", labelsize=9)

        ax.legend(facecolor='none', edgecolor='none', labelcolor='#2a241f', loc='upper right')
        ax.grid(True, linestyle=':', linewidth=0.5, color='#635b53', alpha=0.15)

        # Remove unnecessary spines
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#a89f91')
            ax.spines[spine].set_linewidth(0.5)

        fig.tight_layout()

        st.pyplot(fig)




        st.divider()

        # URLs of the images
        image_urls = [
            "https://informo.madrid.es/cameras/Camara03310.jpg?rand=1716226504287",
            "https://informo.madrid.es/cameras/Camara14303.jpg?rand=1716226713266",
            "https://informo.madrid.es/cameras/Camara01304.jpg?rand=1716226729161",
            "https://informo.madrid.es/cameras/Camara07306.jpg?rand=1716227117756",
            "https://informo.madrid.es/cameras/Camara04301.jpg?rand=1716227208671",
            "https://informo.madrid.es/cameras/Camara12305.jpg?rand=1716227304969"
        ]

        # Function to create a 2x2 grid
        def display_images_in_grid(image_urls):
            html_grid = '<div class="camera-grid">'
            for url in image_urls:
                html_grid += f'<div class="camera-card"><img src="{url}" alt="Cámara de tráfico"></div>'
            html_grid += '</div>'
            st.markdown(html_grid, unsafe_allow_html=True)

        # Display the images
        display_images_in_grid(image_urls)


        with st.sidebar:
            st.markdown("### Controls")
            if st.button('Refresh Page'):
                st.cache_data.clear()
                st.rerun()


        st.sidebar.markdown("""
            <style>
                .sidebar .sidebar-content {
                    background-color: #f0f0f5;
                    padding: 20px;
                    border-radius: 10px;
                }
                .sidebar .btn-primary {
                    background-color: #007bff;
                    color: white;
                    border-radius: 5px;
                }
            </style>
            """, unsafe_allow_html=True)




        string_update = "Datos de las " + str(valid_run+2)  +  " horas \n"

        def generate_ensemble_weather_story(temp_data, wind_gust_data, pressure_data, mucape_data, prec_data):
            today = pd.Timestamp.now(tz='Europe/Madrid').floor('D')
            tomorrow = today + timedelta(days=1)
    
            def get_day_data(df, day):
                return df[df.index.date == day.date()]
    
            def describe_temperature_pattern(temp_df):
                ctrl_temp = temp_df['Ctrl']
                ensemble_temps = temp_df.iloc[:, 1:]
        
                max_temp = ctrl_temp.max()
                min_temp = ctrl_temp.min()
                max_temp_time = ctrl_temp.idxmax().strftime('%H:%M')
        
                ensemble_max = ensemble_temps.max().max()
                ensemble_min = ensemble_temps.min().min()
        
                temp_range = max_temp - min_temp
                ensemble_range = ensemble_max - ensemble_min
        
                story = f"The control forecast suggests temperatures will range from {min_temp:.1f}°C to {max_temp:.1f}°C, peaking around {max_temp_time}. "
        
                if ensemble_range > temp_range + 5:
                    story += f"However, some models show a wider range of {ensemble_min:.1f}°C to {ensemble_max:.1f}°C, indicating uncertainty in the forecast. "
        
                if temp_range < 5:
                    story += "Overall, we're looking at a day of stable temperatures. "
                elif temp_range < 10:
                    story += "Expect a mild day with noticeable but not extreme temperature changes. "
                else:
                    story += "Prepare for significant temperature swings throughout the day. "
        
                return story

            def describe_wind_conditions(wind_df):
                ctrl_wind = wind_df['Ctrl']
                ensemble_winds = wind_df.iloc[:, 1:]
        
                max_wind = ctrl_wind.max()
                avg_wind = ctrl_wind.mean()
                max_wind_time = ctrl_wind.idxmax().strftime('%H:%M')
        
                ensemble_max = ensemble_winds.max().max()
        
                story = f"The primary forecast shows wind gusts peaking at {max_wind:.1f} km/h around {max_wind_time}. "
        
                if ensemble_max > max_wind + 10:
                    story += f"Some models suggest gusts could reach as high as {ensemble_max:.1f} km/h. "
        
                if max_wind < 20:
                    story += "Overall, expect gentle breezes throughout most of the day. "
                elif max_wind < 40:
                    story += "Be prepared for some lively winds that might rustle leaves and affect loose objects. "
                else:
                    story += "It's going to be a blustery day! Secure any loose items outdoors. "
        
                return story

            def describe_pressure_trend(pressure_df):
                ctrl_pressure = pressure_df['Ctrl']
                ensemble_pressures = pressure_df.iloc[:, 1:]
        
                start_pressure = ctrl_pressure.iloc[0]
                end_pressure = ctrl_pressure.iloc[-1]
                pressure_change = end_pressure - start_pressure
        
                ensemble_change = ensemble_pressures.iloc[-1] - ensemble_pressures.iloc[0]
                max_change = ensemble_change.max()
                min_change = ensemble_change.min()
        
                story = f"Barometric pressure is expected to {'rise' if pressure_change > 0 else 'fall'} by about {abs(pressure_change):.1f} hPa over the day."
        
                if abs(max_change - min_change) > 2:
                    story += "However, there's some disagreement between models on the extent of this change. "
        
                if abs(pressure_change) < 2:
                    story += "This suggests relatively stable weather conditions. "
                elif pressure_change > 0:
                    story += "Rising pressure often indicates improving weather. "
                else:
                    story += "Falling pressure might bring some changes, possibly unsettled conditions. "
        
                return story

            def describe_thunderstorm_potential(mucape_df):
                ctrl_mucape = mucape_df['Ctrl']
                ensemble_mucape = mucape_df.iloc[:, 1:]
        
                max_mucape = ctrl_mucape.max()
                max_mucape_time = ctrl_mucape.idxmax().strftime('%H:%M')
        
                ensemble_max = ensemble_mucape.max().max()
        
                story = f"The control forecast shows a peak MUCAPE value of {max_mucape:.0f} J/kg around {max_mucape_time}. "
        
                if ensemble_max > max_mucape + 500:
                    story += f"Some models suggest it could reach as high as {ensemble_max:.0f} J/kg. "
        
                if max_mucape < 500:
                    story += "The atmosphere appears stable, with clear skies likely to dominate. "
                elif max_mucape < 1000:
                    story += "There's a slight chance of some dramatic clouds forming, but thunderstorms are unlikely. "
                elif max_mucape < 2000:
                    story += "Keep an ear out for thunder - there's potential for some storms to develop. "
                else:
                    story += "The ingredients are there for some impressive thunderstorms. Keep an eye on the sky! "
        
                return story

            def describe_precipitation(prec_df):
                ctrl_prec = prec_df['Ctrl']
                ensemble_prec = prec_df.iloc[:, 1:]
        
                total_prec = ctrl_prec.sum()
                max_hourly_prec = ctrl_prec.max()
                max_prec_time = ctrl_prec.idxmax().strftime('%H:%M')
        
                ensemble_total = ensemble_prec.sum()
                max_ensemble_total = ensemble_total.max()
        
                story = f"The main forecast predicts a total of {total_prec:.1f}mm of rain, with the heaviest period around {max_prec_time}. "
        
                if max_ensemble_total > total_prec + 5:
                    story += f"However, some models suggest we could see up to {max_ensemble_total:.1f}mm. "
        
                if total_prec == 0:
                    story += "It looks like it's going to be a dry day in Madrid. "
                elif total_prec < 5:
                    story += "You might want to pack a light umbrella - we could see some sprinkles throughout the day. "
                elif max_hourly_prec > 10:
                    story += f"Prepare for a good soaking! Heavy rain is expected, particularly around {max_prec_time}. "
                else:
                    story += "Expect some wet weather spread throughout the day. "
        
                prob_rain = (ensemble_prec.sum() > 0.1).mean() * 100
                story += f"The probability of measurable rain is about {prob_rain:.0f}%. "
        
                return story

            story = []
            for day, day_name in [(today, "Today"), (tomorrow, "Tomorrow")]:
                day_temp = get_day_data(temp_data, day)
                day_wind = get_day_data(wind_gust_data, day)
                day_pressure = get_day_data(pressure_data, day)
                day_mucape = get_day_data(mucape_data, day)
                day_prec = get_day_data(prec_data, day)
        
                day_story = f"Weather Story for Madrid - {day_name}, {day.strftime('%B %d')}:\n\n"
                day_story += describe_temperature_pattern(day_temp) + "\n\n"
                day_story += describe_wind_conditions(day_wind) + "\n\n"
                day_story += describe_pressure_trend(day_pressure) + "\n\n"
                day_story += describe_thunderstorm_potential(day_mucape) + "\n\n"
                day_story += describe_precipitation(day_prec) + "\n\n"
        
                # Add a summary of the day's weather
                day_story += "In summary: "
                if day_prec['Ctrl'].sum() > 5:
                    day_story += "A wet day with periods of rain. "
                elif day_wind['Ctrl'].max() > 40:
                    day_story += "A windy day with strong gusts. "
                elif day_temp['Ctrl'].max() - day_temp['Ctrl'].min() > 15:
                    day_story += "A day of significant temperature changes. "
                else:
                    day_story += "A relatively stable day weather-wise. "
        
                if day_mucape['Ctrl'].max() > 1500:
                    day_story += "Keep an eye out for potential thunderstorms."
        
                story.append(day_story)
    
            return "\n\n".join(story)


        #temp_data = get_temp_data(valid_run)
        #wind_gust_data = get_wind_gust_data(valid_run)
        #pressure_data = get_pressure_data(valid_run)
        #mucape_data = get_mucape_data(valid_run)
        #prec_data = get_prec_data(valid_run)

        #commentary = generate_ensemble_weather_story(temp_data, wind_gust_data, pressure_data, mucape_data, prec_data)




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
            'wind': process_multi_model_dataframe(wind_gust_data),
            'precipitation': process_multi_model_dataframe(prec_data),
            'pressure': process_multi_model_dataframe(pressure_data),
            'mucape': process_multi_model_dataframe(mucape_data)
        }

        weather_json = json.dumps(weather_data)

        def generate_llm_input(weather_json):
            # Load the meteorological data
            meteo_data = weather_json

            # Define the prompt
            prompt = """ PROVIDE THE WHOLE RESPONSE IN SPANISH FROM SPAIN. THE FORECAST IS FOR MADRID, SPAIN. USE THIS AS CLIMATE CONTEXT FOR YOUR ANSWERS.

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
        4. Risk Assessment and Warnings. Include emojis identifying every field. Organize this information in a table.


        Please provide your analysis in clear, concise language suitable for both meteorological professionals and informed members of the public. Use meteorological terminology where appropriate, but explain complex concepts when necessary.

        ## Meteorological Data:
        """

            # Combine the prompt and the data
            combined_input = f"{prompt}\n\n{json.dumps(meteo_data, indent=2)}"

            return combined_input






if mapas_tab.open:
    with mapas_tab:
        render_arome_maps()
