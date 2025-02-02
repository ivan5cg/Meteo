import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from scipy.stats import percentileofscore
import asyncio

#st.set_option('deprecation.showPyplotGlobalUse', False)

#st.write(datetime.now()+ timedelta(hours=2))


import requests
import telegram
import google.generativeai as genai



TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
GOOGLE_KEY = st.secrets["GOOGLE_KEY"]


genai.configure(api_key=GOOGLE_KEY)

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_message(message):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def send_telegram_message_sync(message):
    asyncio.run(send_telegram_message(message))


async def main():
    await send_telegram_message(output_str)



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

col1,col2,col3 = st.columns(3,gap="small")

col1.metric(":thermometer: Actual (ºC)",temp_actual,(temp_actual-temp_ayer).round(1),delta_color="inverse")
col2.metric(":thermometer: Mañana (ºC)",temp_mañana,(temp_mañana-temp_actual).round(1),delta_color="inverse")
col3.metric("Fiabilidad",fiabilidad.round(1),help="Sobre la temperatura de mañana a esta hora, calculada sobre 10")

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


if hora_día < 9:

    col1,col2,col3,col4 = st.columns(4,gap="small")

    col1.metric(":thermometer: Mínima hoy (ºC)",valor_min,int(percentil_min_hoy.round(0)),delta_color="off",help=texto_percentil)
    col2.metric(":thermometer: Máxima hoy (ºC)",valor_max,int(percentil_max_hoy.round(0)),delta_color="off",help=texto_percentil)
    col3.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,int(percentil_min_mañana.round(0)),delta_color="off",help=texto_percentil)
    col4.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,int(percentil_max_mañana.round(0)),delta_color="off",help=texto_percentil)


else:
    col1,col2,col3 = st.columns(3,gap="small")
    
    col1.metric(":thermometer: Máxima hoy (ºC)",valor_max,int(percentil_max_hoy.round(0)),delta_color="off",help=texto_percentil)
    col2.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,int(percentil_min_mañana.round(0)),delta_color="off",help=texto_percentil)
    col3.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,int(percentil_max_mañana.round(0)),delta_color="off",help=texto_percentil)


col1aviso,col2aviso = st.columns(2,gap="small")


if percentil_max_hoy > 80:     
     col1aviso.warning("Hoy hará mucho calor :fire:")
elif percentil_max_hoy < 20:
    col1aviso.info("Hoy hará mucho frío :cold_face:")


if percentil_max_mañana > 80:     
     col1aviso.warning("Mañana hará mucho calor :fire:")
elif percentil_max_mañana < 20:
    col1aviso.info("Mañana hará mucho frío :cold_face:")


if (percentil_max_mañana - percentil_max_hoy) > 50:     
     col1aviso.warning("Mañana subirán mucho las temperaturas :arrow_up_small:")
elif (percentil_max_hoy - percentil_max_mañana) > 50 :
    col1aviso.info("Mañana bajarán mucho las temperaturas :arrow_down_small:")



st.divider()




def plot_temp_data(data):
        

        data = data
        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)

        ax.plot(data["Actual data"], alpha=1,linewidth=4,color="black")

        # Add title and labels


        plt.title('Temperature Forecast for the next 2 days', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Temperature (°C)', fontsize=12)



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
        for i, temp in enumerate(min_temps):
            min_temp = "{:.1f}".format(temp)
            ax.text(min_idx[i], temp, min_temp, ha='left', va='top', color='blue',fontweight="bold")

        # Add the maximum temperature text to the plot
        for i, temp in enumerate(max_temps):
            max_temp = "{:.1f}".format(temp)
            ax.text(max_idx[i], temp, max_temp, ha='left', va='bottom', color='red',fontweight="bold")


        max_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[0]
        max_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[1]

        ax.fill_between(data.index,max_usual_temp_upper,max_usual_temp_lower, alpha=0.2, color='red')

        min_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[0]
        min_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[1]

        ax.fill_between(data.index,min_usual_temp_upper,min_usual_temp_lower, alpha=0.2, color='blue')



        # Format x-axis ticks
        # Format x-axis ticks
        ticks = []
        tick_labels = []
        for date in data.index:
                if date.hour == 0:
                    tick_labels.append(date.strftime('%A %d %B'))
                    ticks.append(date)
                    ax.axvline(date,0,1,color="black",linewidth=2)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks);
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center');

        return fig


fig = plot_temp_data(temp_data)

st.pyplot(fig=fig)

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

    chance_prec = chance_prec 
    avg_prec = avg_prec 
    
    fig, axs = plt.subplots(2,gridspec_kw={'height_ratios': [0.5,0.5]},figsize=(10, 10),sharex=True) 

    axs[1].bar(chance_prec.index, chance_prec.iloc[:,0],width=0.025)
    axs[1].set_ylim(bottom=0,top=100)


    axs[0].bar(avg_prec.index, avg_prec.iloc[:,0],width=0.025)

    ticks = []
    tick_labels = []
    for date in avg_prec.index:
            if date.hour == 0:
                tick_labels.append(date.strftime('%a, %b %d'))
                ticks.append(date)
                axs[0].axvline(date,0,1,color="black",linewidth=2)
                axs[1].axvline(date,0,1,color="black",linewidth=2)
            if date.hour % 6 == 0:
                tick_labels.append(date.strftime('%H'))
                ticks.append(date)
                pass

    for hour in avg_prec.index:
        axs[0].axvline(hour, linestyle='--', color='black', alpha=0.1)
        axs[1].axvline(hour, linestyle='--', color='black', alpha=0.1)

    axs[0].set_xticks(ticks)
    axs[0].set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

    axs[1].set_xticks(ticks)
    axs[1].set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

    axs[0].grid(True)
    axs[1].grid(True)

    plt.suptitle("Rain forecast",y=0.91)

    axs[0].set_ylabel('Average L/m2 in case of rain')
    axs[1].set_ylabel('Chance of rain')

    return fig
#st.write(prec_data)


#st.pyplot(plot_prec_data(prec_data))

fig = plot_rain_chance(chance_prec,avg_prec)

st.pyplot(fig=fig)

#######################################################
#wind_data = get_wind_gust_data(valid_run)
wind_gust_data["Actual data"] = aemet_horario["Racha (km/h)"]

def plot_wind_data(data):

        data = data

        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)

        ax.plot(data["Actual data"], alpha=1,linewidth=5,color="black")

        # Add title and labels


        plt.title('Wind Forecast for the next 2 days', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Speed (km/h)', fontsize=12)

       

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
        for i, temp in enumerate(min_temps):
            min_temp = "{:.0f}".format(temp)
            ax.text(min_idx[i], temp, min_temp, ha='left', va='top', color='blue',fontweight="bold")

        # Add the maximum temperature text to the plot
        for i, temp in enumerate(max_temps):
            max_temp = "{:.0f}".format(temp)
            ax.text(max_idx[i], temp, max_temp, ha='left', va='bottom', color='red',fontweight="bold")


        # Format x-axis ticks
        # Format x-axis ticks
        ticks = []
        tick_labels = []
        for date in data.index:
                if date.hour == 0:
                    tick_labels.append(date.strftime('%a, %b %d'))
                    ticks.append(date)
                    ax.axvline(date,0,1,color="black",linewidth=2)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

        return fig

fig = plot_wind_data(wind_gust_data)

st.pyplot(fig=fig)

#@#############################################

#pressure_data = get_pressure_data(valid_run)

def plot_pressure_data(data):

        data = data

        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)

        #ax.plot(data["Actual data"], alpha=1,linewidth=4,color="black")

        # Add title and labels


        plt.title('Pressure Forecast for the next 2 days', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Pressure (hpa)', fontsize=12)

        ax.set_ylim(bottom=980,top=1040)

       

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
        for i, temp in enumerate(min_temps):
            min_temp = "{:.0f}".format(temp)
            ax.text(min_idx[i], temp, min_temp, ha='left', va='top', color='blue',fontweight="bold")

        # Add the maximum temperature text to the plot
        for i, temp in enumerate(max_temps):
            max_temp = "{:.0f}".format(temp)
            ax.text(max_idx[i], temp, max_temp, ha='left', va='bottom', color='red',fontweight="bold")


        # Format x-axis ticks
        # Format x-axis ticks
        ticks = []
        tick_labels = []
        for date in data.index:
                if date.hour == 0:
                    tick_labels.append(date.strftime('%a, %b %d'))
                    ticks.append(date)
                    ax.axvline(date,0,1,color="black",linewidth=2)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

        return fig

fig = plot_pressure_data(pressure_data)

st.pyplot(fig=fig)

################################################

#mucape_data = get_mucape_data(valid_run)

def plot_mucape_data(data):

        data = data.astype("int")

        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)

        #ax.plot(data["Actual data"], alpha=1,linewidth=4,color="black")

        # Add title and labels


        plt.title('Storm Potential Forecast for the next 2 days', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('J/kg', fontsize=12)

       

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

        ax.axhspan(0,300,facecolor='green', alpha=0.17)
        ax.axhspan(300,1000,facecolor='yellow', alpha=0.17)
        ax.axhspan(1000,2000,facecolor='red', alpha=0.17)

        return fig


fig = plot_mucape_data(mucape_data)

st.pyplot(fig=fig)



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
     
    fig,ax = plt.subplots(figsize=(10, 6), dpi=100)



    day0 = data_temp_min.iloc[0,:].dropna()
    day1 = data_temp_min.iloc[1,:].dropna()
    day2 = data_temp_min.iloc[2,:].dropna()
    day3 = data_temp_min.iloc[3,:].dropna()
    day4 = data_temp_min.iloc[4,:].dropna()
    day5 = data_temp_min.iloc[5,:].dropna()
    day6 = data_temp_min.iloc[6,:].dropna()
    day7 = data_temp_min.iloc[7,:].dropna()

    data_plotted = [day0,day1,day2,day3,day4,day5,day6,day7]


    boxprops =  dict(linewidth=1, color='black', facecolor='lightblue')
    whiskerprops = dict(linewidth=1, color='black',linestyle='dashed')
    flierprops = dict(marker='o', markerfacecolor='blue', markersize=4, linestyle='none')
    medianprops = dict(linewidth=1, color='black')

    ax.boxplot(data_plotted, positions=[0.25,1.25,2.25,3.25,4.25,5.25,6.25,7.25], patch_artist=True,boxprops=boxprops, 
                whiskerprops=whiskerprops,flierprops=flierprops,medianprops=medianprops);



    day0 = data_temp_max.iloc[0,:].dropna()
    day1 = data_temp_max.iloc[1,:].dropna()
    day2 = data_temp_max.iloc[2,:].dropna()
    day3 = data_temp_max.iloc[3,:].dropna()
    day4 = data_temp_max.iloc[4,:].dropna()
    day5 = data_temp_max.iloc[5,:].dropna()
    day6 = data_temp_max.iloc[6,:].dropna()
    day7 = data_temp_max.iloc[7,:].dropna()

    data_plotted = [day0,day1,day2,day3,day4,day5,day6,day7]

    boxprops =  dict(linewidth=1, color='black', facecolor='lightcoral')
    whiskerprops = dict(linewidth=1, color='black',linestyle='dashed')
    flierprops = dict(marker='o', markerfacecolor='red', markersize=4, linestyle='none')
    medianprops = dict(linewidth=1, color='black')


    ax.boxplot(data_plotted, positions=[0.75,1.75,2.75,3.75,4.75,5.75,6.75,7.75], patch_artist=True,boxprops=boxprops, 
                whiskerprops=whiskerprops,flierprops=flierprops,medianprops=medianprops);


    max_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[0]
    max_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmax"].iloc[1]

    ax.fill_between(data.index,max_usual_temp_upper,max_usual_temp_lower, alpha=0.2, color='red')

    min_usual_temp_upper = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[0]
    min_usual_temp_lower = temp_medias_rolling.iloc[temp_data.index.day_of_year[27]]["tmin"].iloc[1]

    ax.fill_between(data.index,min_usual_temp_upper,min_usual_temp_lower, alpha=0.2, color='blue')


    ax.set_xlim(0,8)

    ax.axvline(((datetime.now().hour+2) / 24 + 1),color="black",linewidth=.4)


    ax.set_title("Evolución temperaturas a una semana")
    ax.set_ylabel("Temperatura")


    ax.set_xticks([0,1,2,3,4,5,6,7], pd.to_datetime(data_temp_min.index).strftime('%A %d'),ha="center")
    ax.set_xticklabels(labels=pd.to_datetime(data_temp_min.index).strftime('%A %d'), rotation=0, ha='left', fontsize=9)

    ax.grid();

    return fig


fig = plot_long_forecast()

st.pyplot(fig=fig)



def plot_long_rain_forecast():
     
    fig,ax = plt.subplots(figsize=(10, 6), dpi=100)

    data_plotted = (6* data_preci_df.resample("6H",closed="left",label="left").mean()).dropna(axis=1,how="all").T.iloc[:,:-10]


    boxprops =  dict(linewidth=1, color='black', facecolor='lightblue')
    whiskerprops = dict(linewidth=1, color='black',linestyle='dashed')
    flierprops = dict(marker='o', markerfacecolor='blue', markersize=4, linestyle='none')
    medianprops = dict(linewidth=1, color='black')

    ax.boxplot(data_plotted, positions=[x+0.5 for x in range(0,len(data_plotted.columns))] , patch_artist=True,boxprops=boxprops, 
                whiskerprops=whiskerprops,flierprops=flierprops,medianprops=medianprops);


    date_list = []
    for item in data_plotted.columns.date:
        if item not in date_list:
            date_list.append(item)



    ax.set_xticks([x for x in range(0,len(data_plotted.columns),4)], date_list,ha="center");
    ax.set_xticklabels(labels=pd.to_datetime(date_list).strftime('%A %d'),rotation=0, ha='left', fontsize=9);
    ax.grid()
    ax.set_ylim(0)
    #ax.axvline(((datetime.now().hour+2) ),color="black",linewidth=.4)

    ax.set_title("Evolución precipitación");
    ax.set_ylabel("L/m2");

    return fig

fig = plot_long_rain_forecast()

st.pyplot(fig=fig)


def plot_long_wind_forecast():
     
    fig,ax = plt.subplots(figsize=(10, 6), dpi=100)

    data_plotted = data_rachas_df.resample("6H",closed="left",label="left").mean().dropna(axis=1,how="all").T.iloc[:,:-18]


    boxprops =  dict(linewidth=1, color='black', facecolor='gold')
    whiskerprops = dict(linewidth=1, color='black',linestyle='dashed')
    flierprops = dict(marker='o', markerfacecolor='gold', markersize=4, linestyle='none')
    medianprops = dict(linewidth=1, color='black')

    ax.boxplot(data_plotted, positions=[x+0.5 for x in range(0,len(data_plotted.columns))] , patch_artist=True,boxprops=boxprops, 
                whiskerprops=whiskerprops,flierprops=flierprops,medianprops=medianprops);


    date_list = []
    for item in data_plotted.columns.date:
        if item not in date_list:
            date_list.append(item)



    ax.set_xticks([x for x in range(0,len(data_plotted.columns),4)], date_list,ha="center");
    ax.set_xticklabels(labels=pd.to_datetime(date_list).strftime('%A %d'),rotation=0, ha='left', fontsize=9);
    ax.grid()
    ax.set_ylim(0)
    #ax.axvline(((datetime.now().hour+2)  + 1),color="black",linewidth=.4)

    ax.set_title("Evolución viento");
    ax.set_ylabel("Km/h");

    return fig

fig = plot_long_wind_forecast()

st.pyplot(fig=fig)


import datetime
import pytz
from astral import LocationInfo
from astral.sun import sun, elevation
import matplotlib.pyplot as plt
import numpy as np

def plot_sun_elevation(latitude, longitude, timezone_str='UTC'):
    # Define location information
    location = LocationInfo("Custom Location", "Custom Region", timezone_str, latitude, longitude)

    # Get current date and time in the specified timezone
    timezone = pytz.timezone(timezone_str)
    today = datetime.datetime.now(tz=timezone)
    yesterday = today - datetime.timedelta(days=1)
    year, month, day = today.year, today.month, today.day

    # Calculate exact sunrise and sunset times for today and yesterday
    s_today = sun(location.observer, date=today)
    s_yesterday = sun(location.observer, date=yesterday)

    # Convert sunrise and sunset times to local timezone
    sunrise_local = s_today['sunrise'].astimezone(timezone)
    sunset_local = s_today['sunset'].astimezone(timezone)

    # Calculate day length for today and yesterday
    day_length_today = (s_today['sunset'] - s_today['sunrise']).total_seconds()
    day_length_yesterday = (s_yesterday['sunset'] - s_yesterday['sunrise']).total_seconds()

    # Calculate the difference in day length
    day_length_diff = day_length_today - day_length_yesterday
    diff_minutes, diff_seconds = divmod(abs(int(day_length_diff)), 60)
    daylight_change = f"{diff_minutes} min {diff_seconds} seg {'ganados' if day_length_diff > 0 else 'perdidos'}"

    # Convert sunrise and sunset times to indices
    sunrise_index = sunrise_local.hour * 60 + sunrise_local.minute
    sunset_index = sunset_local.hour * 60 + sunset_local.minute

    # Generate datetime objects for every minute of the day
    listahoras = [timezone.localize(datetime.datetime(year, month, day, hour, minute))
                  for hour in range(24) for minute in range(60)]

    # Calculate sun elevation for each minute
    elevaciones = [elevation(location.observer, dt) for dt in listahoras]

    # Find the index of the maximum elevation
    max_elevation_index = np.argmax(elevaciones)

    # Convert the maximum elevation index to a corresponding time
    max_elevation_time = listahoras[max_elevation_index].strftime('%H:%M')

    # Current time index
    current_time_index = today.hour * 60 + today.minute

    # Convert to numpy array for efficient plotting
    elevaciones_array = np.array(elevaciones)

    # Compute length of the day
    day_length_seconds = (sunset_local - sunrise_local).total_seconds()
    day_length_hours = int(day_length_seconds // 3600)  # Convert seconds to hours
    day_length_minutes = int((day_length_seconds % 3600) / 60)  # Extract remaining minutes

    # Set up the plot
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')

    # Plot the sun elevation profile
    ax.fill_between(np.arange(len(elevaciones)), elevaciones_array, where=elevaciones_array > 0, 
                    color='peachpuff', alpha=0.5)
    ax.fill_between(np.arange(len(elevaciones)), elevaciones_array, where=elevaciones_array < 0, 
                    color='lightblue', alpha=0.5)

    # Mark the current time
    current_elevation = elevaciones_array[current_time_index]
    ax.plot(current_time_index, current_elevation, 'o', color='darkblue', markersize=8, label='Current Position')

    # Format sunrise, sunset, and max elevation times as hh:mm
    sunrise_time = f"{sunrise_local.hour:02d}:{sunrise_local.minute:02d}"
    sunset_time = f"{sunset_local.hour:02d}:{sunset_local.minute:02d}"

    # Mark sunrise, sunset, and max elevation with labels
    ax.plot(sunrise_index, 0, marker='o', color='gold', markersize=10)
    ax.text(sunrise_index, -10, sunrise_time, ha='center', fontsize=10, color='orange')

    ax.plot(sunset_index, 0, marker='o', color='darkorange', markersize=10)
    ax.text(sunset_index, -10, sunset_time, ha='center', fontsize=10, color='darkorange')

    ax.plot(max_elevation_index, elevaciones_array[max_elevation_index], 'o', color='red', markersize=8)
    ax.text(max_elevation_index, elevaciones_array[max_elevation_index] + 2, max_elevation_time, ha='center', fontsize=10, color='red')

    # Add labels and title
    ax.set_xlabel('Time of Day (hours)', fontsize=12, fontweight='light')
    ax.set_ylabel('Sun Elevation (degrees)', fontsize=12, fontweight='light')
    ax.set_title(f'Sun Elevation Profile | Date: {today.strftime("%Y-%m-%d")} | Day Length: {day_length_hours}h {day_length_minutes}m', 
                 fontsize=14, fontweight='bold')

    # Customize the x-axis labels to show hours
    hours = np.arange(0, len(elevaciones), 60)
    ax.set_xticks(hours)
    ax.set_xticklabels([str(i // 60) for i in hours], fontsize=10, fontweight='light')

    # Customize the y-axis labels
    ax.yaxis.set_tick_params(labelsize=10, labelcolor='grey', width=0.5)

    # Make the grid lines more subtle
    ax.grid(True, linestyle=':', linewidth=0.5, color='grey', alpha=0.7)

    # Remove unnecessary spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('grey')
        ax.spines[spine].set_linewidth(0.5)

    # Minimalist legend
    ax.legend(loc='upper left', frameon=False, fontsize=10)

    # Add a text box with daylight change information
    daylight_change_text = f"Cambio tiempo de luz: {daylight_change}"
    plt.text(0.02, 0.88, daylight_change_text, transform=ax.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='grey', alpha=0.7))

    # Display the plot
    plt.tight_layout()


    return fig

#
fig = plot_sun_elevation(40.41144776110279, -3.6787949052050672, 'Europe/Madrid')

st.pyplot(fig=fig)

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
    # Calculate the number of rows needed (each row has 2 columns)
    num_images = len(image_urls)
    num_rows = (num_images + 1) // 2  # Ensure correct number of rows for odd/even number of images

    # Display images in a 2xN grid
    image_idx = 0
    for _ in range(num_rows):
        cols = st.columns(2)
        for col in cols:
            if image_idx < num_images:
                col.image(image_urls[image_idx], use_container_width=True)
                image_idx += 1

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

model = genai.GenerativeModel(('gemini-2.0-flash-thinking-exp-01-21'))
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
    'wind': process_multi_model_dataframe(wind_gust_data),
    'precipitation': process_multi_model_dataframe(prec_data),
    'pressure': process_multi_model_dataframe(prec_data),
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
   - Pressure: Note any significant pressure changes that might indicate approaching weather systems.
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


prompt = generate_llm_input(weather_json)
response = model.generate_content(prompt)

st.write(response.text)

#send_telegram_message_sync(string_update + response.text)

