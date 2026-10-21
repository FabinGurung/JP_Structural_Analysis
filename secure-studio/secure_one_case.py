"""Executes the source-governed private Gate08 working-frame scenario."""
import contextlib
import io
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/"scripts"))
import run_gate08_mass_calibrated as model

def main():
    payload=json.loads(sys.stdin.read())
    with contextlib.redirect_stdout(io.StringIO()):
        result=model.build(
            bridges=payload["bridges"],
            beam_width=payload["beam_width_mm"],
            E_MPa=payload["concrete_E_MPa"],
            stiffness_state=payload["stiffness_state"],
            eccentricity_cases=True,
            tributary_proxy=True,
            diaphragm=payload["diaphragm"],
            wall_proxy=payload["wall_proxy"],
            mass_basis="RECONSTRUCTED_COMPONENTS",
            footprint_proxy=payload["footprint_proxy"])
    assert result["model_counts"]["members"]==165
    assert len(result["case_results"])==51
    assert len(result["element_actions"])==8415
    assert max(x["max_global_equilibrium_residual"] for x in result["case_results"])<0.002
    governing=max(result["case_results"],key=lambda x:x["max_roof_lateral_displacement_mm"])
    actions=[a for a in result["element_actions"] if a["case"]==governing["case"]]
    assert len(actions)==165
    output={
        "schema":"jp.private.g15.working3d.v1",
        "model_counts":result["model_counts"],
        "variant":result["variant"],
        "case_count":len(result["case_results"]),
        "case_results":result["case_results"],
        "governing_case":governing["case"],
        "signed_member_actions":actions,
        "report_mass_kN":result["source_ETABS_seismic_weight_kN"],
        "modeled_mass_kN":result["trial_ESM_seismic_weight_kN"],
        "F3_source_failure":"NOT SAFE IN ONE WAY SHEAR",
        "engineering_approval":False,
        "actual_as_built_verified":False,
        "status":"WORKING_HYPOTHESIS_NUMERICALLY_SOLVED"}
    print(json.dumps(output,allow_nan=False))
if __name__=="__main__":
    main()
