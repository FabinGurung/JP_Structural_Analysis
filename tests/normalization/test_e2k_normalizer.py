import tempfile
from pathlib import Path
import unittest
from jp_structural.normalization.e2k_normalizer import normalize

FIXTURE = '''$ File C:\\tmp\\pilot.e2k saved 1/1/2026
$ STORIES - IN SEQUENCE FROM TOP
  STORY "Story1" HEIGHT 3000
  STORY "Base" ELEV 0
$ POINT COORDINATES
  POINT "1" 0 0
  POINT "2" 4000 0
$ LINE CONNECTIVITIES
  LINE "C1" COLUMN "1" "1" 1
  LINE "B1" BEAM "1" "2" 0
$ AREA CONNECTIVITIES
  AREA "F1" FLOOR 4 "1" "2" "2" "1" 0 0 0 0
$ POINT ASSIGNS
  POINTASSIGN "1" "Base" RESTRAINT "UX UY UZ RX RY RZ"
  POINTASSIGN "1" "Story1" DIAPH "D1"
  POINTASSIGN "2" "Story1" DIAPH "D1"
$ LINE ASSIGNS
  LINEASSIGN "C1" "Story1" SECTION "C"
  LINEASSIGN "B1" "Story1" SECTION "B"
$ AREA ASSIGNS
  AREAASSIGN "F1" "Story1" SECTION "S"
$ FRAME OBJECT LOADS
  LINELOAD "B1" "Story1" TYPE "UNIFF" DIR "GRAV" LC "Wall" FVAL 5
$ SHELL OBJECT LOADS
  AREALOAD "F1" "Story1" TYPE "UNIFF" DIR "GRAV" LC "Live" FVAL 0.002
$ MASS SOURCE
  MASSSOURCE "MsSrc1" INCLUDELOADS "Yes"
  MASSSOURCELOAD "MsSrc1" "Dead" 1
$ LOAD CASES
  LOADCASE "Dead" TYPE "Linear Static"
$ LOAD COMBINATIONS
  COMBO "1.2D" TYPE "Linear Add"
$ END OF MODEL FILE
'''

class NormalizeTest(unittest.TestCase):
    def test_story_expansion_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pilot.e2k"; p.write_text(FIXTURE,encoding="utf-8")
            x=normalize(p)
            self.assertEqual(x["qa"]["status"],"PASS_REFERENCE_INTEGRITY")
            self.assertEqual(x["qa"]["counts"]["nodes"],3)
            self.assertEqual(x["qa"]["counts"]["frames"],2)
            self.assertEqual(x["qa"]["counts"]["columns"],1)
            self.assertEqual(x["qa"]["counts"]["beams"],1)
            col=next(f for f in x["frames"] if f["type"]=="COLUMN")
            self.assertEqual(col["i_node"],"Story1::1")
            self.assertEqual(col["j_node"],"Base::1")
            self.assertEqual(x["stories"][-1]["elevation"],3000.0)

if __name__=="__main__": unittest.main()
