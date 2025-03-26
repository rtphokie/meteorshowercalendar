import unittest
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from skyfield.api import Loader
import pytz
from datetime import datetime
from skyfield.elementslib import osculating_elements_of

pd.set_option("display.width", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# move Y 0 out from center to better represent Earth's orbital path
INNER_RADIUS = 20

load = Loader("/var/data")  # reuse ephemeris across projects
eph = load("de421.bsp")
ts = load.timescale()
ts = load.timescale()
eph = load('de421.bsp')
earth = eph['earth']
sun = eph['sun']


def get_solar_longitude(date_str, timezone_str='UTC'):
    """
    Calculates the solar longitude for a given date and time.

    Args:
        date_str (str): Date and time string in the format 'YYYY-MM-DD HH:MM:SS'.
        timezone_str (str, optional): Timezone string. Defaults to 'UTC'.

    Returns:
        float: Solar longitude in degrees.
    """
    dt_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    tz = pytz.timezone(timezone_str)
    aware_dt = tz.localize(dt_obj)
    t = ts.from_datetime(aware_dt)

    position = (sun - earth).at(t)
    elements = osculating_elements_of(position)
    solar_longitude = elements.mean_longitude.degrees

    return solar_longitude, aware_dt


def main():
    df = pd.read_csv('meteor_showers.csv')
    # cap variable zhr at 200, lets be reasonable here
    df['zhr_high'] = df['zhr_high'].apply(lambda y: 200 if y > 200 else y)

    date_str = '2025-01-01 01:00:00'
    timezone_str = 'US/Eastern'
    jan_1_solar_longitude, _ = get_solar_longitude(date_str, timezone_str)

    for col in df.columns:
        if 'date' in col:
            df[col] = pd.to_datetime(df[col])

    df = df[['name', 'sl_peak', 'zhr', 'zhr_low', 'zhr_high', 'class', 'date_peak', 'name_utf8']]
    df.sort_values('sl_peak', inplace=True)
    df['heights'] = df['zhr'] + INNER_RADIUS

    df['angles_radians'] = np.radians(df['sl_peak'])
    df_reg = df[df['zhr'] > 0]
    df_variable = df[df['zhr'] < 0]

    # Different sades of grey used in the plot
    GREY88 = "#e0e0e0"
    GREY85 = "#d9d9d9"
    GREY82 = "#d1d1d1"
    GREY79 = "#c9c9c9"
    GREY97 = "#f7f7f7"
    GREY60 = "#999999"
    #
    # # Category values for the colors
    # CATEGORY_CODES = pd.Categorical(df["class"]).codes
    #
    # # # Colormap taken from https://carto.com/carto-colors/
    # # COLORMAP = [
    # #     "#5F4690",
    # #     "#1D6996",
    # #     "#38A6A5",
    # #     # "#0F8554",
    # #     # "#73AF48",
    # #     # "#EDAD08",
    # #     # "#E17C05",
    # #     # "#CC503E",
    # #     # "#94346E",
    # #     # "#666666",
    # # ]
    # #
    # # Select colors for each password according to its category.
    # COLORS = np.array(COLORMAP)[CATEGORY_CODES]

    # Create a data frame with the information for the four passwords that are going to be labeled
    LABELS_DF = df[df["zhr"] > 15].reset_index()
    # Create labels
    LABELS_DF["label"] = [
        f"{name}\n{dt.strftime('%b %-d')}"
        for name, dt in zip(LABELS_DF["name"], LABELS_DF["date_peak"])
    ]

    # Initialize layout in polar coordinates
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_rscale("symlog")
    ax.set_theta_offset(math.pi / jan_1_solar_longitude)
    ax.set_theta_direction(-1)

    # lines, and round toppers for meteor showers
    df_reg['width'] = np.log10(df_reg['heights']) * 2.5
    ax.vlines(df_reg['angles_radians'], INNER_RADIUS, df_reg['heights'], color='orange', lw=df_reg['width'])
    ax.scatter(df_reg['angles_radians'], df_reg['heights'], df_reg['heights'] / 2, color='orange')
    ax.vlines(df_variable['angles_radians'], INNER_RADIUS, df_variable['zhr_high'], alpha=.3, color='blue', lw=2)

    solstices_label = ['March Equinox', 'June Solstice', 'September Equinox', 'December Solstice']
    solstices_deg = [0, 90, 180, 270]
    solstices_rotation = [0, 90, 0, 90]
    solstices_ha = ["left", "center", "right", "center"]
    solstices_va = ["center", "top", "center", "bottom"]
    solstices_rad = [math.radians(degree) for degree in solstices_deg]
    ax.vlines(solstices_rad, INNER_RADIUS, INNER_RADIUS + 5, color=GREY82, lw=1.0)

    for label, ha, va, deg, rotation in zip(solstices_label, solstices_ha, solstices_va, solstices_deg,
                                            solstices_rotation):
        # print(label, deg)
        ax.text(
            s=f"{label}",
            x=math.radians(deg),
            y=INNER_RADIUS + 10,
            ha=ha, va=va, ma="center", rotation=rotation,
            size=10, family="Arial", weight="bold", color=GREY82,
        )

    for month in range(1, 13):
        date_str = f'2025-{month:02d}-15 12:00:00'
        solar_longitude, dt = get_solar_longitude(date_str, 'UTC')
        if solar_longitude > 180:
            month_rotation = 270 - solar_longitude
        else:
            month_rotation = 90 - solar_longitude
        ax.text(
            s=dt.strftime('%b'),
            x=math.radians(solar_longitude),
            y=INNER_RADIUS - 10,
            ha='center', va='center', ma="center", rotation=month_rotation,
            size=10, family="Arial", weight="bold", color=GREY82,
        )
        date_str = f'2025-{month:02d}-01 12:00:00'
        solar_longitude, dt = get_solar_longitude(date_str, 'UTC')
        ax.vlines(math.radians(solar_longitude), INNER_RADIUS, INNER_RADIUS + 2, color=GREY82, lw=1.0)

    # Remove outer spines, grid lines, ticks, and tick labels.
    ax.spines["start"].set_color("none")
    ax.spines["polar"].set_color("none")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticklabels([])

    # add a circle for the orbit
    HANGLES = np.linspace(0, 2 * np.pi, 200)
    ax.plot(HANGLES, np.repeat(INNER_RADIUS, 200), color='k', lw=1.0)


    print(df_variable)
    # for idx, row in LABELS_DF.iterrows():
    #     ax.text(
    #         s=f"{row["name_utf8"]}\n{row['date_peak'].strftime('%b-%d')}",
    #         x=math.radians(row['sl_peak']),
    #         y=INNER_RADIUS + row['heights'] + 70,
    #         ha='center', va='bottom', ma="center", rotation=0,
    #         size=10, family="Arial", weight="bold", color='k',
    #     )

    filename = "meteor_shower_circular_calendar.png"
    plt.savefig(filename, dpi=300)
    print(f"Saved {filename}")


class MyTestCase(unittest.TestCase):
    def test_something(self):
        main()

    def test_date_to_sl(self):
        # Example usage:
        date_str = '2025-01-01 01:00:00'
        timezone_str = 'US/Eastern'
        solar_longitude, dt = get_solar_longitude(date_str, timezone_str)
        print(f"Solar Longitude on {date_str} ({timezone_str}): {solar_longitude:.6f} degrees")


if __name__ == "__main__":
    unittest.main()
