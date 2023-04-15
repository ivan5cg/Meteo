import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import streamlit as st

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
    df = df.drop("Date",axis=1)
    df = df.drop("Ech.",axis=1)
    df = df.astype("float")

    return df



runs = [3, 9, 15, 21]
url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.658&mode=8&sort=0'

last_index = pd.Timestamp(year=2017, month=1, day=1,tz="UTC")

for run in runs:
    url_run = f'{url}&run={run}'
    last_index_run = get_arome_data(url_run).index[-1]

    if last_index_run > last_index:
        last_index = last_index_run
        valid_run = run
    else:
        pass


url ='https://www.meteociel.fr/modeles/pe-arome_table.php?x=0&y=0&lat=40.41&lon=-3.658&mode=8&sort=0'
url_run = f'{url}&run={valid_run}'

temp_data = get_arome_data(url_run)


import matplotlib.pyplot as plt

# Set figure size and resolution
fig, ax = plt.subplots(figsize=(10, 6), dpi=80)

# Set plot style
plt.style.use('ggplot')

# Iterate over the columns and plot each one
for column in temp_data.columns:
    ax.plot(temp_data.index, temp_data[column], label=column, alpha=0.9)

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
for hour in temp_data.index:
    ax.axvline(hour, linestyle='--', color='black', alpha=0.1)

# Remove gridlines
plt.grid(True)

# Compute the minimum and maximum temperature for each day and their respective indexes
dates = list(set(temp_data.index.date))
min_temps = []
max_temps = []
min_idx = []
max_idx = []

for date in dates:
    df = temp_data.loc[temp_data.index.date == date]
    min_temp = df.min().min()
    max_temp = df.max().max()
    min_idx.append(temp_data.loc[temp_data.index.date == date].idxmin().min())
    max_idx.append(temp_data.loc[temp_data.index.date == date].idxmax().min())
    min_temps.append(min_temp)
    max_temps.append(max_temp)

# Add the minimum temperature text to the plot
for i, temp in enumerate(min_temps):
    min_temp = "{:.1f}°C".format(temp)
    ax.text(min_idx[i], temp, min_temp, ha='left', va='top', color='blue',fontweight="bold")

# Add the maximum temperature text to the plot
for i, temp in enumerate(max_temps):
    max_temp = "{:.1f}°C".format(temp)
    ax.text(max_idx[i], temp, max_temp, ha='left', va='bottom', color='red',fontweight="bold")


# Format x-axis ticks
# Format x-axis ticks
ticks = []
tick_labels = []
for date in temp_data.index:
        if date.hour == 0:
            tick_labels.append(date.strftime('%a, %b %d'))
            ticks.append(date)
        if date.hour % 6 == 0:
            tick_labels.append(date.strftime('%H'))
            ticks.append(date)
            pass

        #else:
            #tick_labels.append(temp_data.index[hour].strftime('%H'))
            #ticks.append(temp_data.index[hour])

ax.set_xticks(ticks)
ax.set_xticklabels(tick_labels, fontsize=10, rotation=0, ha='center')

st.pyplot(fig)