import unittest

from meteor_calendar_table import (
    find_solar_longitude,
    get_json_from_urlfile,
    main,
)
import os


class MyTestCase(unittest.TestCase):

    def test_fetch_json_from_setellarium_source(self):
        foo = get_json_from_urlfile(
            "https://raw.githubusercontent.com/Stellarium/stellarium/c266ab5e0d75503ff05d7767820a1d570ab20581/plugins/MeteorShowers/resources/MeteorShowers.json"
        )
        self.assertIsNotNone(foo)
        self.assertTrue("showers" in foo)
        self.assertTrue("ORI" in foo["showers"])

    def test_sl2date_march_equinox(self):
        year = 2025
        target_longitude = 0.0
        date_time = find_solar_longitude(year, target_longitude)
        self.assertEqual(date_time.year, 2025)
        self.assertEqual(date_time.month, 3)
        self.assertEqual(date_time.day, 20)

    def test_sl2date_june_solstice(self):
        year = 2025
        target_longitude = 90.0
        date_time = find_solar_longitude(year, target_longitude)
        self.assertEqual(date_time.year, 2025)
        self.assertEqual(date_time.month, 6)
        self.assertEqual(date_time.day, 21)

    def test_main(self):
        df = main()
        print(df)
        self.assertGreater(len(df), 40)
        self.assertTrue("date_peak" in df.columns)
        self.assertEqual(df.zhr.max(), 700)
        self.assertEqual(df.zhr.min(), 2)
        self.assertTrue(os.path.exists("meteor_showers.csv"))


if __name__ == "__main__":
    unittest.main()
