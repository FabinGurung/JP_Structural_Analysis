import math
import unittest

import openseespy.opensees as ops

from jp_structural.solvers.opensees.elastic_frame import (
    assign_lumped_node_masses,
    build_elastic_frame_model,
    eigen_periods,
)


MODEL={
 "qa":{"status":"PASS_REFERENCE_INTEGRITY"},
 "materials":[{"name":"M","E":25000.0,"poisson":0.2}],
 "frame_sections":[{"name":"C","material":"M","shape":"Concrete Rectangular",
                    "width":300.0,"depth":300.0,"i2_modifier":1.0,"i3_modifier":1.0}],
 "nodes":[
   {"id":"Base::1","x":0.0,"y":0.0,"z":0.0,"restraint":"UX UY UZ RX RY RZ"},
   {"id":"Story1::1","x":0.0,"y":0.0,"z":3000.0,"restraint":None}
 ],
 "frames":[
   {"id":"Story1::C1","type":"COLUMN","section":"C",
    "i_node":"Story1::1","j_node":"Base::1"}
 ]
}

class OpenSeesTranslatorTest(unittest.TestCase):
    def test_build_and_eigen(self):
        b=build_elastic_frame_model(MODEL)
        self.assertEqual(len(b.node_tags),2)
        self.assertEqual(len(b.element_tags),1)
        # Add equal translational masses to make the cantilever dynamically solvable.
        assign_lumped_node_masses(b,{"Story1::1":(1.0,1.0,1.0)})
        periods=eigen_periods(2)
        self.assertEqual(len(periods),2)
        self.assertTrue(all(math.isfinite(x) and x>0 for x in periods))
        self.assertGreater(periods[0],0.0)
        ops.wipe()

if __name__=="__main__":
    unittest.main()
