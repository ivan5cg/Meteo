import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from scipy.stats import percentileofscore
import asyncio

st.set_option('deprecation.showPyplotGlobalUse', False)

#st.write(datetime.now()+ timedelta(hours=2))


import requests
import telegram



TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

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

aemet_horario_acumulado.to_excel("Histórico/Acumulado Madrid.xlsx")

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

#########################################################


string_update = "Datos de las " + str(valid_run+2)  +  " horas \n"




rain_chance = get_prec_data(valid_run)

rain_chance = rain_chance.loc[rain_chance.index.dayofyear==día_año_hoy]

rain_chance = 100 * pd.DataFrame((rain_chance.apply(lambda row: sum(row != 0), axis=1) / len(rain_chance.columns)) )

rain_chance = rain_chance[rain_chance > 20].dropna().index.hour

if len(rain_chance) > 0:
    hours_list = list(map(str, rain_chance))
    if len(hours_list) > 1:
        hours_str = ", ".join(hours_list[:-1]) + " y " + hours_list[-1]
    else:
        hours_str = hours_list[0]
        
    output_str_rain = f" Las horas de mayor probabilidad de lluvia son {hours_str}. \n"
    #send_telegram_message_sync(output_str)
else: 
    output_str_rain = ""








storm_chance = get_mucape_data(valid_run)

storm_chance = storm_chance.loc[storm_chance.index.dayofyear==día_año_hoy]

percentile_80 = storm_chance.apply(lambda x: x.quantile(0.8), axis=1) 

percentile_80 = percentile_80[percentile_80 > 500].index.hour


if len(percentile_80) > 0:
    hours_list = list(map(str, percentile_80))
    if len(hours_list) > 1:
        hours_str = ", ".join(hours_list[:-1]) + " y " + hours_list[-1]
    else:
        hours_str = hours_list[0]
    output_str_storm = f" Puede haber tormentas a las {hours_str}. \n"
    #send_telegram_message_sync(output_str)
else:
    output_str_storm = ""


send_telegram_message_sync(string_update + output_str_rain + output_str_storm)


#########################################################


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

        return 

st.pyplot(plot_temp_data(temp_data))

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
#st.write(prec_data)


#st.pyplot(plot_prec_data(prec_data))

st.pyplot(plot_rain_chance(chance_prec,avg_prec))

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

        return 

st.pyplot(plot_wind_data(wind_gust_data))

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

        return 

st.pyplot(plot_pressure_data(pressure_data))

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

        return 

st.pyplot(plot_mucape_data(mucape_data))



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

st.pyplot(plot_long_forecast())



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

st.pyplot(plot_long_rain_forecast())


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

st.pyplot(plot_long_wind_forecast())







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
    year, month, day = today.year, today.month, today.day

    # Calculate exact sunrise and sunset times
    s = sun(location.observer, date=today)

    # Convert sunrise and sunset times to local timezone
    sunrise_local = s['sunrise'].astimezone(timezone)
    sunset_local = s['sunset'].astimezone(timezone)

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

    # Display the plot
    plt.tight_layout()
    plt.show()

#
st.pyplot(plot_sun_elevation(40.41144776110279, -3.6787949052050672, 'Europe/Madrid'))


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
                col.image(image_urls[image_idx], use_column_width=True)
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
