from datetime import datetime
from datetime import timedelta
from time import sleep
import lxml.html as lh
import requests
import re
import numpy as np
import math


class TideInterpolator:
    def __init__(self):
        self.previous_tidal_tables = (
            {}
        )  # Store tidal tables to prevent duplicated requests

    def interpolate_tide(self, date_time, port):
        # Tidal interpolation is done based on the Portuguese National Hydrographic Institute data
        # There's no real API to interpolate, so I have to make my own
        date_time = date_time.split(".")[0]
        date_time = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S")
        starting_date = date_time - timedelta(days=1)
        starting_date = starting_date.strftime("%Y%m%d")
        tidal_table_id = f"{starting_date}_{port}"

        # If we queried these dates before, retrieve the stored tidal table
        if tidal_table_id in self.previous_tidal_tables.keys():
            table = self.previous_tidal_tables[tidal_table_id]
        else:  # If date is new, query and scrape the data
            query_str = f"https://www.hidrografico.pt/json/mare.port.val.php?po={port}&dd={starting_date}&nd=2"
            page = requests.get(query_str)
            i = 0
            while not page.ok:
                print(f"Retrying tidal query in {i**2} seconds", end="\r")
                sleep(i**2)
                page = requests.get(query_str)
                i += 1

            table_elements = lh.fromstring(page.content).xpath("//tr")

            # If all days are in the same time fuse, 3 columns are returned
            if len(table_elements[0]) == 3:
                table = {"date_time_utc": [], "height": [], "phenomenon": []}

                time_zone = re.findall("(?<=\\().*?(?=\\))", str(page.content))
                time_delta = re.findall("[+-][0-9]+$", time_zone[0])
                if len(time_delta) == 0:
                    time_delta = 0
                else:
                    time_delta = float(re.findall("[+-][0-9]+$", time_zone[0])[0])
                time_delta = timedelta(hours=-time_delta)

                for row in table_elements[1:]:
                    # Skip moon events
                    if re.search("mar", row[2].text_content()) is None:
                        continue
                    row_date_time = datetime.strptime(
                        row[0].text_content(), "%Y-%m-%d %H:%M"
                    )
                    row_date_time = row_date_time + time_delta
                    table["date_time_utc"].append(row_date_time)
                    table["height"].append(row[1].text_content())
                    table["phenomenon"].append(row[2].text_content())
            # If returned results go across time fuses, 4 columns are returned
            elif len(table_elements[0]) == 4:
                table = {"date_time_utc": [], "height": [], "phenomenon": []}

                time_zones = re.findall("(?<=\\().*?(?=\\))", str(page.content))
                # Extract the number used to assign a timezone to each row
                time_zone_code = [
                    time_zone
                    for i, time_zone in enumerate(time_zones)
                    if i % 2 == 0
                ]
                # Extract the time shift for each timezone
                time_zone_shift = [
                    time_zone
                    for i, time_zone in enumerate(time_zones)
                    if not i % 2 == 0
                ]
                time_zone_shift = [
                    re.findall("[+-][0-9]+$", time_zone) for time_zone in time_zone_shift
                ]

                time_zones = {}
                for i, code in enumerate(time_zone_code):
                    # If there is no shift in the hour, set as zero
                    if len(time_zone_shift[i]) == 0:
                        time_zones[code] = timedelta(hours=0)
                    else:
                        time_zones[code] = timedelta(hours=int(time_zone_shift[i][0])) 

                for row in table_elements[1:]:
                    # Skip moon events
                    if re.search("mar", row[2].text_content()) is None:
                        continue
                    
                    # Correct local time (in which tides are given) to UTC (in which satellite picture capture times are given)
                    row_time_zone = str(row[3].text_content()) 
                    row_time_delta = time_zones[row_time_zone]
                    row_date_time = datetime.strptime(
                        row[0].text_content(), "%Y-%m-%d %H:%M"
                    )
                    row_date_time = row_date_time - row_time_delta

                    table["date_time_utc"].append(row_date_time)
                    table["height"].append(row[1].text_content())
                    table["phenomenon"].append(row[2].text_content())

            # How long from does each tidal event take to occur (from previous to current)?
            table["duration"] = []
            for i in range(len(table["date_time_utc"])):
                if i == 0:
                    duration = None
                else:
                    duration = table["date_time_utc"][i] - table["date_time_utc"][i - 1]
                table["duration"].append(duration)

            sleep(0.1)  # To avoid overloading the server with requests
            self.previous_tidal_tables[
                tidal_table_id
            ] = table  # Store queried table for next assets

        # Calculate time difference between tidal events and time to be interpolated
        time_from_phenomenom = []
        for phenomenom_time in table["date_time_utc"]:
            time_from_phenomenom.append(phenomenom_time - date_time)
        table["time_from_interpolation"] = time_from_phenomenom
        time_from_phenomenom = np.array(time_from_phenomenom)

        # Find the closest event BEFORE the interpolation time
        previous_event = np.where(
            time_from_phenomenom < timedelta(days=0),
            time_from_phenomenom,
            timedelta(days=-100),
        ).argmax()
        previous_event = {
            "date_time_utc": table["date_time_utc"][previous_event],
            "height": float(table["height"][previous_event].replace(" m", "")),
            "phenomenon": table["phenomenon"][previous_event],
            "duration": table["duration"][previous_event] / timedelta(hours=1),
            "time_from_interpolation": abs(
                table["time_from_interpolation"][previous_event] / timedelta(hours=1)
            ),
        }
        # Find the closest event AFTER the interpolation time
        next_event = np.where(
            time_from_phenomenom > timedelta(days=0),
            time_from_phenomenom,
            timedelta(days=100),
        ).argmin()
        next_event = {
            "date_time_utc": table["date_time_utc"][next_event],
            "height": float(table["height"][next_event].replace(" m", "")),
            "phenomenon": table["phenomenon"][next_event],
            "duration": table["duration"][next_event] / timedelta(hours=1),
            "time_from_interpolation": abs(
                table["time_from_interpolation"][next_event] / timedelta(hours=1)
            ),
        }

        if previous_event["phenomenon"] == "preia-mar":
            H = previous_event["height"]
            h = next_event["height"]
            T = previous_event["duration"]
            t = previous_event["time_from_interpolation"]
            q1 = (H + h) / 2
            q2 = (H - h) / 2
        else:
            H = next_event["height"]
            h = previous_event["height"]
            T = previous_event["duration"]
            t = previous_event["time_from_interpolation"]
            q1 = (h + H) / 2
            q2 = (h - H) / 2

        q3 = math.cos((math.pi * t) / T)

        tidal_height = q1 + q2 * q3
        tidal_height = round(tidal_height, 2)

        return tidal_height

