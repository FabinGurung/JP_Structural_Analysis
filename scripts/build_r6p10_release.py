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
from scripts.build_r6p12_manual_report_audit import export as export_manual
from scripts.build_r6p13_member_gravity_research import export as export_members
from scripts.build_r6p14_tributary_reconciliation import export as export_tributary

import json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    source_mesh, shells = export_shells()
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
    manual = export_manual()
    require(len(manual['checks']) >= 40 and manual['F3_one_way_shear_unsafe']
            and not manual['engineering_approval'], 'R6.12 manual report evidence failed')
    members, member_receipt = export_members(cases=cases, mesh=source_mesh)
    require(members["count"]["actual_structural_frame_members"] == 165
            and members["count"]["source_shell_objects"] == 115
            and members["count"]["research_shells_included"] == 103
            and members["count"]["research_shells_excluded"] == 12
            and members["F3_one_way_shear_unsafe"]
            and not members["engineering_approval"]
            and not members["research_member_strength_or_capacity_accepted"],
            "R6.13 member ledger scope or engineering boundary changed")
    require(member_receipt["governing_model_SHA256"] == cases["source_model_fingerprints"],
            "R6.13 member data diverges from governing ULS/SLS source")
    trib, trib_receipt = export_tributary(mesh=source_mesh)
    require(trib["coverage"]["original_shells"] == 115
            and trib["coverage"]["source_graph_shells_connected"] == 103
            and trib["coverage"]["source_graph_shells_without_base_path"] == 12
            and trib["twelve_unsupported_shells_excluded"]
            and not trib["physical_vertical_force_transfer_verified"]
            and not trib["no_source_gravity_load_case_modified"] is False
            and trib["F3_one_way_shear_unsafe"]
            and not trib["engineering_approval"],
            "R6.14 source slab edge and engineering HOLD changed")
    require(trib_receipt["source_governing_pair"] == cases["source_model_fingerprints"],
            "R6.14 ULS/SLS source pair mismatch")
    project_report = SITE / "projects/pokhara-g15/report.html"
    original = project_report.read_text(encoding="utf-8")
    target = '<section class="rb-card project-tools" id="project-hand-calculations"'
    block = ('<section class="rb-card project-tools" id="project-r6p13-members">'
        '<h2>R6.13 · Source member gravity and research actions</h2>'
        '<p>Member-by-member source geometry, assigned wall loads, independent bounded '
        'gravity-pattern end actions and explicitly unverified strength checks for '
        '165 structural members and 115 shells. No ETABS21 design approval.</p>'
        '<p><a href="projects/pokhara-g15/member-gravity.html">'
        'Open source member gravity and research ledger</a></p></section>\n')
    if target not in original:
        raise ValueError("Original project hand-calculation section disappeared")
    target = '<section class="rb-card project-tools" id="project-hand-calculations"'
    tributary_block = ('<section class="rb-card project-tools" id="project-r6p14-tributary">'
        '<h2>R6.14 · Slab-to-beam geometry and conditional tributary areas</h2>'
        '<p>Original source slab edges, candidate same-floor beam boundaries, '
        '45-degree geometric load shares only for complete four-edge rectangular candidates, '
        'and explicit withheld structural load paths. No verified force transfer or design loads.</p>'
        '<p><a href="projects/pokhara-g15/tributary-audit.html">'
        'Open slab-to-beam source reconciliation</a></p></section>\n')
    if 'id="project-r6p14-tributary"' not in original:
        original = original.replace(target,tributary_block+target,1)
        project_report.write_text(original,encoding="utf-8")
    if 'id="project-r6p13-members"' not in original:
        project_report.write_text(original.replace(target,block+target,1),encoding="utf-8")

    for project in json.loads(PROJECTS.read_text()):
        route = f"projects/{project['slug']}/report.html"
        report = (SITE / route).read_text()
        require(all(marker in report for marker in ('id="project-hand-calculations"', 'id="project-figures"',
                '<svg ', '<iframe ', f'href="{route}#project-hand-calculations"')),
                f"{route} is missing hand calculations, figures, or linked model views")
        require((SITE / project["viewer"]).is_file(), f"Missing model viewer for {route}")
        if project["slug"] == "pokhara-g15":
            require('id="project-r6p12-manual"' in report, "R6.12 manual audit link missing")
            require((SITE/"projects/pokhara-g15/manual-verification.html").is_file(),
                    "R6.12 manual audit page missing")
            require('id="project-r6p14-tributary"' in report,
                    "R6.14 tributary audit project link missing")
            require((SITE/"projects/pokhara-g15/tributary-audit.html").is_file(),
                    "R6.14 tributary page missing")
            require('id="project-r6p13-members"' in report,
                    "R6.13 member ledger link missing from original project report")
            require((SITE/"projects/pokhara-g15/member-gravity.html").is_file(),
                    "R6.13 member gravity page missing")

    print("R6.10 verified: 115 shell records, 8 gravity trials, 4 lateral trials, 22 trial combinations and project report links")


if __name__ == "__main__":
    main()
