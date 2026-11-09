import unittest

from adapters.scs import map_data


DATA = {
    "sdkActive": True, "paused": False, "game": 1,
    "speed": 24.4, "engineRpm": 1300, "engineRpmMax": 2500,
    "gear": 6, "fuel": 400, "fuelCapacity": 700, "speedLimit": 25,
    "time_abs": 875, "time_abs_delivery": 947,
    "cityDst": "Paris", "compDst": "EuroGoodies",
    "wearChassis": .97, "trailer": [
        {"attached": True, "wearChassis": .93, "cargoDamage": .91}],
    "truckBrand": "Scania", "truckName": "R500",
    "coordinateX": 853.4857, "coordinateY": 5416.1333,
    "rotationY": 0.2, "userThrottle": .4, "userBrake": 0,
    "userClutch": 0, "waterTemperature": 89, "oilTemperature": 104,
    "oilPressure": 4.2, "lightsBeamLow": True,
    "blinkerLeftActive": False, "blinkerRightActive": False,
}


class ScsSourceTest(unittest.TestCase):
    def test_map_data(self):
        dash = map_data(DATA)
        self.assertEqual("ets2", dash["game_id"])
        self.assertAlmostEqual(87.84, dash["v"])
        self.assertEqual(6, dash["g"])
        self.assertEqual(90, dash["speed_limit"])
        self.assertEqual("14:35", dash["game_time"])
        self.assertEqual("Paris EuroGoodies", dash["destination"])
        self.assertEqual(97, dash["wear_truck"])
        self.assertEqual(93, dash["wear_trailer"])
        self.assertEqual(91, dash["wear_cargo"])
        self.assertEqual(700, dash["fuel_capacity"])
        self.assertEqual(853.4857, dash["map_x"])
        self.assertEqual(5416.1333, dash["map_y"])
        self.assertAlmostEqual(11.459, dash["map_heading"], places=3)

    def test_inactive(self):
        self.assertIsNone(map_data({"sdkActive": False}))


if __name__ == "__main__":
    unittest.main()
