import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime,timedelta
from scipy.stats import percentileofscore



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
    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=8&sort=0'

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


valid_run = get_last_arome_run()


st.header("Dublin")


#aemet_horario = pd.read_csv("https://www.aemet.es/es/eltiempo/observacion/ultimosdatos_1154H_datos-horarios.csv?k=can&l=1154H&datos=det&w=0&f=temperatura&x=" ,
                            #encoding="latin-1",skiprows=2,parse_dates=True,index_col=0,dayfirst=True)
#aemet_horario.index = aemet_horario.index.tz_localize('Europe/Madrid')





def get_temp_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=8&sort=0'
    url_run = f'{url}&run={valid_run}'

    temp_data = get_arome_data(url_run)

    return temp_data

def get_wind_gust_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=13&sort=0'
    url_run = f'{url}&run={valid_run}'

    wind_gust_data = get_arome_data(url_run)

    return wind_gust_data

def get_pressure_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=1&sort=0'
    url_run = f'{url}&run={valid_run}'

    pressure_data = get_arome_data(url_run)

    return pressure_data

def get_mucape_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=0&sort=0'
    url_run = f'{url}&run={valid_run}'

    mucape_data = get_arome_data(url_run)

    return mucape_data

def get_prec_data(valid_run):

    url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=45.46&lon=9.20&mode=10&sort=0'
    url_run = f'{url}&run={valid_run}'

    prec_data = get_arome_data(url_run)

    return prec_data


#####################################################


st.sidebar.subheader("Previsión más reciente: "+str(valid_run+2)+" horas")

#st.sidebar.subheader("Datos más recientes: "+str(aemet_horario.index[0].hour)+" horas")


temp_data = get_temp_data(valid_run)
#temp_data["Actual data"] = aemet_horario["Temperatura (ºC)"]

#temp_actual = aemet_horario["Temperatura (ºC)"].iloc[0]
#temp_ayer = aemet_horario.iloc[-1]["Temperatura (ºC)"]

dia_mañana = (datetime.now() + timedelta(hours=26)).day
hora = (datetime.now() + timedelta(hours=2)).hour

temp_mañana = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].mean(axis=1)[0].round(1)
desv_temp = temp_data.loc[temp_data.index[(temp_data.index.hour==hora) & (temp_data.index.day ==dia_mañana)]].std(axis=1).round(1)[0]

fiabilidad = 10*np.exp(-0.05*desv_temp**2.5)

col1,col2,col3 = st.columns(3,gap="small")

#col1.metric(":thermometer: Actual (ºC)",temp_actual,(temp_actual-temp_ayer).round(1),delta_color="inverse")
#col2.metric(":thermometer: Mañana (ºC)",temp_mañana,(temp_mañana-temp_actual).round(1),delta_color="inverse")
col1.metric("Fiabilidad",fiabilidad.round(1),help="Sobre la temperatura de mañana a esta hora, calculada sobre 10")

st.divider()

##########################


día_año_hoy = (datetime.now()+timedelta(hours=2)).timetuple().tm_yday

día_año_mañana = día_año_hoy + 1 #(datetime.now()+timedelta(hours=0)).timetuple().tm_yday

hora_día = (datetime.now()+timedelta(hours=2)).hour



# Definir el array de valores
#arr_max = datos_df_global[datos_df_global["día_del_año"]==día_año_hoy]["tmax"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_max = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).max().round(1)


# Definir el array de valores
#arr_min = datos_df_global[datos_df_global["día_del_año"]==día_año_hoy]["tmin"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_min = temp_data[temp_data.index.day_of_year==día_año_hoy].mean(axis=1).min().round(1)

# Calcular el percentil

#percentil_max_hoy = percentileofscore(arr_max, valor_max)

#percentil_min_hoy = percentileofscore(arr_min, valor_min)



# Definir el array de valores
#arr_max = datos_df_global[datos_df_global["día_del_año"]==día_año_mañana]["tmax"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_max_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).max().round(1)


# Definir el array de valores
#arr_min = datos_df_global[datos_df_global["día_del_año"]==día_año_mañana]["tmin"].sort_values().dropna()

# Definir el valor para el cual deseas calcular el percentil
valor_min_mañana = temp_data[temp_data.index.day_of_year==día_año_mañana].mean(axis=1).min().round(1)

# Calcular el percentil

#percentil_max_mañana = percentileofscore(arr_max, valor_max_mañana)

#percentil_min_mañana = percentileofscore(arr_min, valor_min_mañana)



#texto_percentil = "El percentil indica cómo es la temperatura frente a los registros históricos, un valor cercano a 100 indica un registro extremadamente alto, uno cercano a 0 indica un registro extremadamente bajo."


if hora_día < 9:

    col1,col2,col3,col4 = st.columns(4,gap="small")

    col1.metric(":thermometer: Mínima hoy (ºC)",valor_min,delta_color="off")
    col2.metric(":thermometer: Máxima hoy (ºC)",valor_max,delta_color="off")
    col3.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,delta_color="off")
    col4.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,delta_color="off")


else:
    col1,col2,col3 = st.columns(3,gap="small")
    
    col1.metric(":thermometer: Máxima hoy (ºC)",valor_max,delta_color="off")
    col2.metric(":thermometer: Mínima mañana (ºC)",valor_min_mañana,delta_color="off")
    col3.metric(":thermometer: Máxima mañana (ºC)",valor_max_mañana,delta_color="off")





st.divider()



#########################



def plot_temp_data(data):
        

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


        max_usual_temp_upper = 22.5
        max_usual_temp_lower = 25.5

        #ax.fill_between(data.index,max_usual_temp_upper,max_usual_temp_lower, alpha=0.2, color='red')

        min_usual_temp_upper = 15
        min_usual_temp_lower = 18

        #ax.fill_between(data.index,min_usual_temp_upper,min_usual_temp_lower, alpha=0.2, color='blue')



        # Format x-axis ticks
        # Format x-axis ticks
        ticks = []
        tick_labels = []
        for date in data.index:
                if date.hour == 0:
                    tick_labels.append(date.strftime('%a %b %d'))
                    ax.axvline(date,0,1,color="black",linewidth=2)
                    ticks.append(date)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks);
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center');

        return fig


st.pyplot(plot_temp_data(temp_data))

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

st.pyplot(plot_rain_chance(chance_prec,avg_prec))




#######################################################
wind_data = get_wind_gust_data(valid_run)
#wind_data["Actual data"] = aemet_horario["Racha (km/h)"]

def plot_wind_data(data):

        data = data

        # Set figure size and resolution
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        # Set plot style
        plt.style.use('default')

        # Iterate over the columns and plot each one
        for column in data.columns[:-1]:
            ax.plot(data.index, data[column], alpha=0.9)

        #ax.plot(data["Actual data"], alpha=1,linewidth=5,color="black")

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
                    ax.axvline(date,0,1,color="black",linewidth=2)
                    ticks.append(date)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

        return fig 

st.pyplot(plot_wind_data(wind_data))

#@#############################################

pressure_data = get_pressure_data(valid_run)

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
                    ax.axvline(date,0,1,color="black",linewidth=2)
                    ticks.append(date)
                if date.hour % 6 == 0:
                    tick_labels.append(date.strftime('%H'))
                    ticks.append(date)
                    pass

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

        return fig

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
    plt.show()

    return fig
#
st.pyplot(plot_sun_elevation(53.34035472693258, -6.271568680463857, 'Europe/London'))
