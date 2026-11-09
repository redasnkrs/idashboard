import base64
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core import simhub, simhub_faithful, studio


PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82").decode()


def item(kind, name, **extra):
    data = {"$type": "SimHub.Models.%s, SimHub" % kind, "Name": name}
    data.update(extra)
    return data


def screen(items, name="Dashboard"):
    return {"$id": "s1", "Name": name, "InGameScreen": True,
            "IdleScreen": False, "Items": {"$values": items}}


def archive(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, json.dumps(data))
    return base64.b64encode(buf.getvalue()).decode()


class SimHubImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_imports = simhub.IMPORTS_DIR
        self.old_studio_imports = studio.IMPORTS_DIR
        simhub.IMPORTS_DIR = Path(self.tmp.name) / "imports"
        studio.IMPORTS_DIR = simhub.IMPORTS_DIR

    def tearDown(self):
        simhub.IMPORTS_DIR = self.old_imports
        studio.IMPORTS_DIR = self.old_studio_imports
        self.tmp.cleanup()

    def dashboard(self):
        hidden = item(
            "RectangleItem", "Ignition", Left=0, Top=0, Width=800,
            Height=480, BackgroundColor="#FFFF0000", Visible=True,
            Bindings={"Visible": {"Formula": {
                "Expression": "[DataCorePlugin.CurrentGame]='IRacing'"}}})
        return {
            "$type": "SimHub.Models.Dashboard, SimHub",
            "BaseWidth": 800, "BaseHeight": 480,
            "BackgroundColor": "#FF101010",
            "Metadata": {"Title": "Test SimHub", "Author": "Reda",
                         "Description": "Sample"},
            "SelectedScreen": {"$ref": "s1"},
            "Images": [{"Name": "logo", "Extension": ".png", "Data": PNG}],
            "Screens": {"$values": [screen([
                item("RectangleItem", "Panel", Left=80, Top=48, Width=400,
                     Height=240, BackgroundColor="#FF112233",
                     BorderStyle={"AllBorders": 2, "AllCornerRadius": 6,
                                  "BorderColor": "#FFFFFFFF"}),
                item("TextItem", "Speed", Left=80, Top=48, Width=320,
                     Height=96, Text="0", FontSize=40, Font="Droid Sans",
                     TextColor="#FF00FF00",
                     Bindings={"Text": {"Formula": {
                         "Expression":
                         "[DataCorePlugin.GameData.NewData.SpeedKmh]"}}}),
                item("ImageItem", "Logo", Left=0, Top=0, Width=80,
                     Height=80, Image="logo"),
                item("WidgetItem", "Child", Left=400, Top=240, Width=240,
                     Height=96, FileName="child.djson"),
                hidden,
            ])]},
        }

    def child(self):
        return {
            "BaseWidth": 240, "BaseHeight": 96,
            "SelectedScreen": {"$ref": "s1"},
            "Screens": {"$values": [screen([
                item("TextItem", "Child Text", Left=0, Top=0, Width=240,
                     Height=96, Text="CHILD", FontSize=30,
                     TextColor="#FFFFFFFF"),
            ], name="Child")]},
        }

    def test_import_zip_flattens_and_copies_assets(self):
        data = archive({
            "Test SimHub/Test SimHub.djson": self.dashboard(),
            "Test SimHub/child.djson": self.child(),
        })
        layout, report = simhub.import_dashboard(data, "Test SimHub.zip")
        self.assertEqual("Test SimHub", layout["name"])
        self.assertEqual("#101010", layout["background"])
        self.assertEqual("Dashboard", report["screen"])
        self.assertEqual(4, len(layout["widgets"]))
        self.assertEqual(1, report["assets"])
        panel = next(w for w in layout["widgets"] if w["id"] == "panel")
        self.assertEqual(102.4, panel["x"])
        self.assertEqual(60, panel["y"])
        self.assertEqual(512, panel["w"])
        self.assertEqual(300, panel["h"])
        self.assertEqual("#112233", panel["fill"])
        self.assertEqual(6, panel["radius"])
        speed = next(w for w in layout["widgets"] if w["id"] == "speed")
        self.assertEqual("value", speed["type"])
        self.assertEqual("v", speed["field"])
        self.assertEqual("auto", speed["unit"])
        logo = next(w for w in layout["widgets"] if w["id"] == "logo")
        self.assertRegex(logo["src"], r"^/custom/imports/[a-z0-9-]+/logo\.png$")
        token, filename = logo["src"].split("/")[3:5]
        self.assertIsNotNone(studio.import_asset_path(token, filename))
        self.assertFalse(any(w["id"] == "ignition"
                             for w in layout["widgets"]))
        self.assertIn("CHILD", [w.get("text") for w in layout["widgets"]])
        self.assertEqual([], [w for w in report["warnings"]
                              if "introuvable" in w])
        self.assertEqual(["Droid Sans"], report["fonts"])

    def test_direct_djson_warns_about_missing_components(self):
        blob = json.dumps(self.dashboard()).encode()
        data = base64.b64encode(blob).decode()
        layout, report = simhub.import_dashboard(data, "Test SimHub.djson")
        self.assertTrue(layout["widgets"])
        self.assertEqual(1, report["missing"])
        self.assertIn("composant introuvable: child.djson",
                      report["warnings"])

    def test_formula_mapping(self):
        rpm = simhub._formula_field(
            "[DataCorePlugin.GameData.NewData.FilteredRpms] / 1000")
        self.assertEqual(("r", "int", "none", .001, 0), rpm)
        clutch = simhub._formula_field(
            "100-[DataCorePlugin.GameData.NewData.Clutch]")
        self.assertEqual(("clu", "int", "percent", -1, 100), clutch)
        oil = simhub._formula_field(
            "if(isnull([DataCorePlugin.CurrentGame],'AssettoCorsa')="
            "'AssettoCorsa',90,[DataCorePlugin.GameData.NewData."
            "OilTemperature])")
        self.assertEqual("ot", oil[0])
        fuel = simhub._formula_field(
            "[DataCorePlugin.GameData.NewData.FuelPercent]")
        self.assertEqual("fp", fuel[0])
        self.assertIsNone(simhub._formula_field(
            "if([DataCorePlugin.Computed.Fuel_RemainingLaps]<2,"
            "[DataCorePlugin.GameData.NewData.Fuel],0)"))

    def test_faithful_import_preserves_tree_and_bindings(self):
        data = archive({
            "Test SimHub/Test SimHub.djson": self.dashboard(),
            "Test SimHub/child.djson": self.child(),
        })
        layout, report = simhub_faithful.import_faithful(
            data, "Test SimHub.zip")
        self.assertEqual("simhub", layout["kind"])
        self.assertEqual("Test SimHub", layout["name"])
        self.assertEqual([], layout["widgets"])
        self.assertIn("simhub", layout)
        items = layout["simhub"]["items"]
        self.assertEqual(4, len(items))
        speed = next(i for i in items if i["name"] == "Speed")
        self.assertEqual("v", speed["bind"]["field"])
        logo = next(i for i in items if i["name"] == "Logo")
        self.assertRegex(logo["src"], r"^/custom/imports/")
        self.assertFalse(any(i["name"] == "Ignition" for i in items))
        self.assertEqual("Dashboard", report["screen"])

    def test_route_advisor_map_is_preserved(self):
        path = (Path(__file__).resolve().parent.parent / "dashboards" /
                "course" / "SimHub - Truck Route Advisor.simhubdash")
        if not path.is_file():
            self.skipTest("route advisor absent")
        data = base64.b64encode(path.read_bytes()).decode()
        layout, report = simhub_faithful.import_faithful(
            data, path.name)
        self.assertEqual("simhub", layout["kind"])
        self.assertTrue(layout["simhub"].get("map_url"))
        found = []

        def walk(items):
            for item in items:
                if item.get("type") == "ETSMap":
                    found.append(item)
                walk(item.get("children") or [])
                walk((item.get("child") or {}).get("items") or [])

        walk(layout["simhub"]["items"])
        self.assertEqual(1, len(found))
        self.assertGreater(found[0]["width"], 1000)

    def test_speed_unit_visibility_keeps_kmh(self):
        kmh = item("TextItem", "KMH", Left=0, Top=0, Width=80, Height=40,
                   Text="mph", Visible=True,
                   Bindings={"Visible": {"Formula": {
                       "Expression": "isnull([DataCorePlugin.GameData."
                       "NewData.SpeedLocalUnit],0)='KMH'"}}})
        mph = item("TextItem", "MPH", Left=0, Top=0, Width=80, Height=40,
                   Text="mph", Visible=True,
                   Bindings={"Visible": {"Formula": {
                       "Expression": "isnull([DataCorePlugin.GameData."
                       "NewData.SpeedLocalUnit],0)='MPH'"}}})
        dashboard = self.dashboard()
        dashboard["Screens"]["$values"][0]["Items"]["$values"] = [kmh, mph]
        data = archive({"Test SimHub/Test SimHub.djson": dashboard})
        layout, _ = simhub.import_dashboard(data, "Test SimHub.zip")
        self.assertEqual([], layout["widgets"])


if __name__ == "__main__":
    unittest.main()
