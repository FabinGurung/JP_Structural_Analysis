#!/usr/bin/env python3
"""Generate and validate the same R6.10 site additions in CI and Pages."""
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_project_reports import PROJECTS, SITE, build as build_projects
from scripts.build_r6p10_gravity_casebook import OUT as CASEBOOK, export as export_cases
from scripts.build_r6p10_source_shell_mesh import OUT as SHELLS, export as export_shells

import json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    _, shells = export_shells()
    cases, receipt = export_cases()
    require(sha256(SHELLS.read_bytes()).hexdigest() == shells["source_QA_file_sha256"], "Shell audit checksum mismatch")
    require(sha256(CASEBOOK.read_bytes()).hexdigest() == receipt["casebook_SHA256"], "Casebook checksum mismatch")
    require(shells["source_sha256"] == receipt["source_governing_E2K_SHA256"], "Model revisions differ")
    require((shells["total_shell_objects"], shells["source_connected_shells"],
             shells["source_unrestrained_shells"], shells["original_diaphragm_point_assignments"])
            == (115, 103, 12, 201), "Shell and diaphragm scope changed")
    require((cases["replayed_source_gravity_pattern_cases"], cases["replayed_source_conditional_seismic_pattern_cases"],
             cases["recombined_original_source_linear_add_expressions"]) == (8, 4, 22), "Case coverage changed")
    require(not shells["engineering_approval"] and not cases["engineering_approval"]
            and not cases["all_source_gravity_and_seismic_combination_envelopes_reproduced"]
            and cases["F3_one_way_shear_unsafe"], "Engineering status changed")
    build_projects()
    for project in json.loads(PROJECTS.read_text()):
        route = f"projects/{project['slug']}/report.html"
        report = (SITE / route).read_text()
        require(all(marker in report for marker in ('id="project-hand-calculations"', 'id="project-figures"',
                '<svg ', '<iframe ', f'href="{route}#project-hand-calculations"')),
                f"{route} is missing hand calculations, figures, or linked model views")
        require((SITE / project["viewer"]).is_file(), f"Missing model viewer for {route}")
    print("R6.10 verified: 115 shell records, 8 gravity trials, 4 lateral trials, 22 trial combinations and project report links")


if __name__ == "__main__":
    main()
