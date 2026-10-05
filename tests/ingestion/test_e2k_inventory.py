import tempfile
from pathlib import Path
import unittest
from jp_structural.ingestion.e2k_inventory import inventory

FIXTURE='''$ File C:\\tmp\\Pilot.e2k saved 1/1/2026 1:00:00 PM
$ PROGRAM INFORMATION
  PROGRAM  "ETABS"  VERSION "21.0.0"
$ CONTROLS
  UNITS  "N"  "MM"  "C"
  TITLE2  "Pilot"
$ STORIES - IN SEQUENCE FROM TOP
  STORY "Story1" HEIGHT 3000
  STORY "Base" ELEV 0
$ DIAPHRAGM NAMES
  DIAPHRAGM "D1" TYPE RIGID
$ MATERIAL PROPERTIES
  MATERIAL "M20" TYPE "Concrete" GRADE "M20"
$ FRAME SECTIONS
  FRAMESECTION "B1" MATERIAL "M20" SHAPE "Concrete Rectangular" D 400 B 230
$ SLAB PROPERTIES
  SHELLPROP "S1" PROPTYPE "Slab" MATERIAL "M20" MODELINGTYPE "ShellThin" SLABTYPE "Slab" SLABTHICKNESS 125
$ POINT COORDINATES
  POINT "1" 0 0
$ LINE CONNECTIVITIES
  LINE "C1" COLUMN "1" "1" 1
$ AREA CONNECTIVITIES
$ LOAD PATTERNS
  LOADPATTERN "Dead" TYPE "Dead" SELFWEIGHT 1
$ ANALYSIS OPTIONS
  PDELTA METHOD "NONE"
$ MASS SOURCE
  MASSSOURCE "MsSrc1" INCLUDEELEMENTS "No"
$ FUNCTIONS
$ LOAD CASES
  LOADCASE "Dead" TYPE "Linear Static" INITCOND "PRESET"
$ LOAD COMBINATIONS
  COMBO "1.2D" TYPE "Linear Add"
$ PROJECT INFORMATION
  PROJECTINFO COMPANYNAME "Test" MODELNAME "Pilot"
$ END OF MODEL FILE
'''

class InventoryTest(unittest.TestCase):
    def test_core_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"Pilot.e2k"; p.write_text(FIXTURE,encoding="utf-8")
            x=inventory(p)
            self.assertEqual(x["program"]["version"],"21.0.0")
            self.assertEqual(x["program"]["units"],["N","MM","C"])
            self.assertEqual(x["counts"]["stories"],2)
            self.assertEqual(x["counts"]["load_cases"],1)
            self.assertEqual(x["counts"]["load_combinations"],1)
            self.assertEqual(x["frame_sections"][0]["depth"],400.0)
            self.assertTrue(any(w["code"]=="PDELTA_DISABLED_IN_SOURCE" for w in x["warnings"]))

if __name__=="__main__": unittest.main()
