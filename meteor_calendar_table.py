import pandas as pd
from pprint import pprint
import json
import requests
import os
from skyfield.api import Loader
from skyfield.errors import EphemerisRangeError
from skyfield.framelib import ecliptic_frame
import pytz

pd.set_option("display.width", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# globals are generally bad, but these are okay
load = Loader("/var/data")  # reuse ephemeris across projects
eph = load("de421.bsp")
ts = load.timescale()
est_timezone = pytz.timezone("US/Eastern")


def find_solar_longitude(year, sl):
    # finds the date and team to the nearest half-hour for a given solar longitude (0-306 degrees) and year

    # nearest midnight of the year
    t = ts.utc(year, 1, range(1, 367))
    dt = sldate(t, sl)

    # nearest hour
    t = ts.utc(year, dt.month, dt.day, range(-24, 25))
    dt = sldate(t, sl)

    # nearest half hour
    t = ts.utc(year, dt.month, dt.day, dt.hour, range(-60, 60, 30))
    dt = sldate(t, sl)
    return dt


def sldate(t, sl):
    # returns datetime in the given list closest to the given solar longitude
    global eph
    try:
        astrometric = eph["Earth"].at(t).observe(eph["Sun"])
    except EphemerisRangeError:
        # try DE430's wider date range (though lower accuracy)
        eph.close()
        eph = load("de430t.bsp")
        astrometric = eph["Earth"].at(t).observe(eph["Sun"])
        eph.close()
        eph = load("de421.bsp")  # switch back

    lat, lon, distance = astrometric.frame_latlon(ecliptic_frame)
    i = min(range(len(lon.degrees)), key=lambda i: abs(lon.degrees[i] - sl))
    dt = t[i].utc_datetime()
    return dt


def get_json_from_urlfile(
    url="https://raw.githubusercontent.com/Stellarium/stellarium/c266ab5e0d75503ff05d7767820a1d570ab20581/plugins/MeteorShowers/resources/MeteorShowers.json",
):
    r = requests.get(url)
    data = None
    filename = url.split("/")[-1]
    if not os.path.exists(filename):
        with open(filename, "wb") as f:
            f.write(r.content)

    with open(filename, "rb") as f:
        data = json.load(f)
    return data


greek_letters = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
}


def convert_utf8(s):
    for english in greek_letters:
        s = s.replace(greek_letters[english], english)
    return s


def main(csv_filename='meteor_showers.csv'):
    foo = get_json_from_urlfile()

    results = []
    for key, data in foo["showers"].items():
        if key == "ANT":  # ignore antihelion, too broad for our purposes
            continue
        shower = {
            "name_utf8": data["designation"],
            "name": convert_utf8(data["designation"]),
            "abbrev": key,
            "IAUNo": data["IAUNo"],
            "date_peak": None,
            "zhr": None,
            "class": None,
            "past_last_year": None,
            "past_last_zhr": None,
            "past_last_peak": None,
            "past_last_date": None,
            "past_outburst_year": None,
            "past_outburst_date": None,
            "past_outburst_zhr": None,
            "past_outburst_peak": None,
        }
        for attr in ["parentObj", "speed"]:
            if attr in data:
                shower[attr] = data[attr]
        results.append(shower)
        process_activity(data, shower)


    df = pd.DataFrame(results)
    if csv_filename is not None:
        df.to_csv(csv_filename, index=False)
    return df



def process_activity(data, shower):
    # processes list of activity records for the shower, recording information about the most recent and the largest (past)
    for activity in data["activity"]:
        if activity["year"] == "generic":
            # estimate for coming years
            shower["date_peak"] = find_solar_longitude(2025, activity["peak"])
            shower["date_peak"] = shower["date_peak"].astimezone(
                pytz.timezone("US/Eastern")
            )
            shower["sl_start"] = activity["start"]
            shower["sl_peak"] = activity["peak"]
            shower["sl_finish"] = activity["finish"]
            for attr in ["zhr", "variable"]:
                if attr in activity:
                    if attr == "variable":
                        low, high = activity[attr].split("-")
                        shower["zhr_high"] = int(high)
                        shower["zhr_low"] = int(low)
                    else:
                        shower[attr] = activity[attr]
            if 'zhr' in activity:
                if 'variable' in activity:
                    shower['class'] = 'variable'
                elif activity['zhr'] >= 15:
                    shower['class'] = 'major'
                elif 0 < activity['zhr'] < 15:
                    shower['class'] = 'minor'
                else:
                    pprint(activity)
                    pprint(shower)
                    raise

        else:
            activity["year"] = int(activity["year"])

            # outburst
            if "zhr" in activity and (
                    shower["past_outburst_year"] is None
                    or shower["past_outburst_zhr"] < activity["zhr"]
            ):
                measurement = "outburst"
                past_columns(activity, measurement, shower)

            # most recent past
            if (
                    shower["past_last_year"] is None
                    or shower["past_last_year"] < activity["year"]
            ):
                measurement = "last"
                past_columns(activity, measurement, shower)


def past_columns(activity, measurement, shower):
    shower[f"past_{measurement}_year"] = activity["year"]
    if (
        "peak" not in activity
    ):  # no specific solar longitude recorded for that year, use the generic one
        activity["peak"] = shower["sl_peak"]
    for attr in ["zhr", "peak"]:
        if attr in activity:
            shower[f"past_{measurement}_{attr}"] = activity[attr]
            if attr == "peak":
                shower[f"past_{measurement}_date"] = find_solar_longitude(
                    activity["year"], activity["peak"]
                ).astimezone(pytz.timezone("US/Eastern"))


if __name__ == "__main__":
    main()
