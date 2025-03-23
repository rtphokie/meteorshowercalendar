import pandas as pd
import json
import requests
import os
from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame
import pytz

# globals are generally bad, but these are okay
load = Loader('/var/data')
eph = load('de421.bsp')
ts = load.timescale()
est_timezone = pytz.timezone('US/Eastern')


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
    astrometric = eph['Earth'].at(t).observe(eph['Sun'])
    lat, lon, distance = astrometric.frame_latlon(ecliptic_frame)
    i = min(range(len(lon.degrees)), key=lambda i: abs(lon.degrees[i] - sl))
    dt = t[i].utc_datetime()
    return dt


def get_json_from_urlfile(url):
    r = requests.get(url)
    print(url)
    data = None
    filename = url.split('/')[-1]
    if not os.path.exists(filename):
        with open(filename, 'wb') as f:
            f.write(r.content)

    with open(filename, 'rb') as f:
        data = json.load(f)
    return data


greek_letters = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω"
}


def convert_utf8(s):
    for greek in greek_letters:
        s = s.replace(greek, greek_letters[greek])
    return s


class MyTestCase(unittest.TestCase):

    def test_sl2date(self):
        year = 2025
        target_longitude = 0.0
        date_time = find_solar_longitude(year, target_longitude)
        print(date_time)
        date_time = find_solar_longitude(year, 90)
        print(date_time)
        date_time = find_solar_longitude(year, 180)
        print(date_time)
        date_time = find_solar_longitude(year, 270)
        print(date_time)

    def test_meteor_table(self):
        foo = download_file(
            "https://raw.githubusercontent.com/Stellarium/stellarium/c266ab5e0d75503ff05d7767820a1d570ab20581/plugins/MeteorShowers/resources/MeteorShowers.json")
        # pprint(foo)
        results = []
        for key, data in foo['showers'].items():
            if key == 'ANT':
                continue
            shower = {'name': data['designation'],
                      'abbrev': key,
                      'IAUNo': data['IAUNo'],
                      'date_peak': None,
                      'outburst_year_last': None,
                      'outburst_zhr_last': None,
                      'outburst_peak_last': None,
                      'outburst_date_last': None,
                      'outburst_year_largest': None,
                      'outburst_date_largest': None,
                      'outburst_zhr_largest': None,
                      'outburst_peak_largest': None,
                      'zhr': None,
                      'variable': False,
                      }
            for attr in ['parentObj', "speed"]:
                if attr in data:
                    shower[attr] = data[attr]
            results.append(shower)
            for activity in data['activity']:
                if activity['year'] == 'generic':
                    # estimate for coming years
                    zhr = activity['zhr']
                    shower['date_peak'] = find_solar_longitude(2025, activity['peak'])
                    shower['date_peak'] = shower['date_peak'].astimezone(pytz.timezone('US/Eastern'))
                    shower['sl_start'] = activity['start']
                    shower['sl_peak'] = activity['peak']
                    shower['sl_finish'] = activity['finish']
                    for attr in ['zhr', 'variable']:
                        if attr in activity:
                            if attr == 'variable':
                                shower['variable'] = True
                                low, high = activity[attr].split('-')
                                shower['zhr'] = high
                                shower['zhr_low'] = low
                            else:
                                shower[attr] = activity[attr]
                else:
                    activity['year'] = int(activity['year'])

                    # largest outburst
                    if 'zhr' in activity and (
                            shower['outburst_year_largest'] is None or shower['outburst_zhr_largest'] < activity[
                        'zhr']):
                        measurement = 'largest'
                        self.outburst_columns(activity, measurement, shower)

                    # most recent outburst
                    if shower['outburst_year_last'] is None or shower['outburst_year_last'] < activity['year']:
                        measurement = 'last'
                        self.outburst_columns(activity, measurement, shower)

        pd.set_option('display.width', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        df = pd.DataFrame(results)
        print(df[['name', 'zhr_low', 'zhr', 'variable', 'date_peak', 'outburst_zhr_largest', 'outburst_date_largest',
                  'outburst_zhr_last', 'outburst_date_last']])
        # print(df)

    def outburst_columns(self, activity, measurement, shower):
        shower[f'outburst_year_{measurement}'] = activity['year']
        if 'peak' not in activity:  # no specific solar longitude recorded for that year, use the generic one
            activity['peak'] = shower['sl_peak']
        for attr in ['zhr', 'peak']:
            if attr in activity:
                shower[f'outburst_{attr}_{measurement}'] = activity[attr]
                if attr == 'peak':
                    shower[f'outburst_date_{measurement}'] = find_solar_longitude(activity['year'],
                                                                                  activity['peak']).astimezone(
                        pytz.timezone('US/Eastern'))


if __name__ == '__main__':
    unittest.main()
