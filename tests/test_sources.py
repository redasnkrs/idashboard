import unittest
from types import SimpleNamespace

from adapters.ac import AcSource
from adapters.ams2 import Ams2Source
from adapters.ams2_defs import (CAR_ENGINE_ACTIVE, CAR_HEADLIGHT,
                                GAME_INGAME_PLAYING)
from adapters.auto import AutoSource


class AcMappingTest(unittest.TestCase):
    def test_mapping(self):
        src = AcSource()
        src._structs = (
            SimpleNamespace(speedKmh=100.0, rpms=5000.0, gear=3, fuel=20.0,
                            gas=.8, brake=.1, clutch=0.0, turboBoost=1.2,
                            airTemp=25.0, brakeBias=.56, pitLimiterOn=0,
                            tc=0.0, abs=1.0),
            SimpleNamespace(status=2, iCurrentTime=1234, iLastTime=0,
                            iBestTime=0, position=3, numCars=10,
                            normalizedCarPosition=.25, isInPitLine=0,
                            isInPit=0),
            SimpleNamespace(maxRpm=8000, maxFuel=60.0, airTemp=25.0,
                            carModel="Ferrari 488 GTB", track="Monza",
                            trackConfiguration="", numCars=10),
        )
        dash = src.read()
        self.assertEqual("ac", dash["game_id"])
        self.assertEqual("Assetto Corsa", dash["game"])
        self.assertEqual(100, dash["v"])
        self.assertEqual(5000, dash["r"])
        self.assertEqual(2, dash["g"])
        self.assertAlmostEqual(20 / .75, dash["fuel"], places=3)
        self.assertAlmostEqual((20 / .75) / 60, dash["fp"], places=3)
        self.assertEqual(3, dash["pos"])
        self.assertEqual(10, dash["nd"])
        self.assertAlmostEqual(.25, dash["npos"])
        self.assertTrue(dash["abs"])


class Ams2MappingTest(unittest.TestCase):
    def test_mapping(self):
        player = SimpleNamespace(mCurrentLapDistance=500.0,
                                 mRacePosition=4)
        view = SimpleNamespace(
            mVersion=9, mViewedParticipantIndex=0, mNumParticipants=10,
            mParticipantInfo=[player],
            mCarFlags=CAR_HEADLIGHT | CAR_ENGINE_ACTIVE,
            mTrackLength=2000.0, mWaterTempCelsius=90.0,
            mOilTempCelsius=100.0, mOilPressureKPa=400.0,
            mTurboBoostPressure=.8, mBrakeBias=.56,
            mGameState=GAME_INGAME_PLAYING,
            mTranslatedTrackLocation="Monza",
            mTranslatedTrackVariation="GP", mTrackLocation="monza",
            mTrackVariation="", mSpeed=50.0, mRpm=5000.0,
            mMaxRPM=8000.0, mGear=3, mThrottle=.8, mBrake=.0,
            mClutch=0.0, mHandBrake=0.0, mFuelLevel=.5,
            mFuelCapacity=60.0, mPitMode=0, mAntiLockActive=False,
            mAmbientTemperature=25.0, mCurrentTime=12.3,
            mLastLapTime=-1.0, mBestLapTime=98.5,
            mLapInvalidated=False, mCarName=b"McLaren 720S",
        )
        src = Ams2Source()
        src._view = view
        dash = src.read()
        self.assertEqual("ams2", dash["game_id"])
        self.assertAlmostEqual(180.0, dash["v"], places=3)
        self.assertEqual(5000, dash["r"])
        self.assertEqual(3, dash["g"])
        self.assertAlmostEqual(30.0, dash["fuel"], places=3)
        self.assertAlmostEqual(.25, dash["npos"], places=3)
        self.assertEqual(4, dash["pos"])
        self.assertEqual(10, dash["nd"])
        self.assertTrue(dash["low"])
        self.assertTrue(dash["run"])
        self.assertEqual(12300, dash["lap"])
        self.assertEqual("Monza", dash["track"])
        self.assertEqual("GP", dash["cfg"])


class AutoSourceTest(unittest.TestCase):
    class Dummy:
        def __init__(self, name, data):
            self.name = name
            self.data = data

        def read(self):
            return self.data

        def ets2(self):
            return {"game": {"connected": True, "gameName": self.name}}

    def test_switches_active_source(self):
        a = self.Dummy("a", None)
        b = self.Dummy("b", {"c": True, "game_id": "b"})
        auto = AutoSource([a, b])
        self.assertEqual("b", auto.read()["game_id"])
        self.assertEqual("b", auto.ets2()["game"]["gameName"])
        b.data = None
        a.data = {"c": True, "game_id": "a"}
        self.assertEqual("a", auto.read()["game_id"])
        self.assertEqual("a", auto.ets2()["game"]["gameName"])


if __name__ == "__main__":
    unittest.main()
