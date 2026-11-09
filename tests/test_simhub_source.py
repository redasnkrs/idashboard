import unittest

from adapters.simhub import SimHubSource


DATA = {
    "GameRunning": True,
    "GameName": "ETS2",
    "GameData": {"NewData": {
        "SpeedKmh": 50, "Gear": "D1", "FuelPercent": 35,
        "Rpms": 1200, "MaxRpm": 2000,
        "TurnIndicatorLeft": True, "Throttle": 0.4,
    }},
    "GameRawData": {
        "Job": {"CityDestination": "Paris",
                "CompanyDestination": "EuroGoodies",
                "NavigationTime": "0001-01-01T01:00:00",
                "SpeedLimitKmh": 50},
        "Damage": {"WearChassis": 0.95, "WearTrailer": 0.9},
        "TrailerValues01": {"DamageValues": {"Chassis": 0.8}},
        "TimeAbsolute": "0001-01-08T10:00:00",
    },
}


class SimHubSourceTest(unittest.TestCase):
    def test_mapping(self):
        source = SimHubSource()
        source._fetch = lambda: DATA
        dash = source.read()
        self.assertIsNotNone(dash)
        self.assertEqual("ets2", dash["game_id"])
        self.assertEqual(50, dash["v"])
        self.assertEqual(1, dash["g"])
        self.assertEqual("D1", dash["gear_text"])
        self.assertAlmostEqual(0.35, dash["fp"])
        self.assertEqual("Paris EuroGoodies", dash["destination"])
        self.assertEqual("10:00", dash["game_time"])
        self.assertEqual("ETA : 01:00", dash["eta_text"])
        self.assertEqual(95, dash["wear_truck"])
        self.assertEqual(90, dash["wear_trailer"])
        self.assertEqual(80, dash["wear_cargo"])
        self.assertEqual(50, dash["speed_limit"])
        self.assertTrue(dash["L"])
        self.assertEqual("Euro Truck Simulator 2", dash["game"])

    def test_unreachable(self):
        source = SimHubSource()
        source._fetch = lambda: (_ for _ in ()).throw(OSError("off"))
        self.assertIsNone(source.read())


if __name__ == "__main__":
    unittest.main()
