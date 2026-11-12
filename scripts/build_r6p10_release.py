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
from scripts.build_r6p15_incomplete_edge_audit import export as export_incomplete
from scripts.build_r6p16_reproducibility_gate import export as export_reproducibility
from scripts.build_r6p17_canonical_source_graph import export as export_canonical

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
            and trib["no_source_gravity_load_case_modified"]
            and trib["no_original_design_member_actions_modified"]
            and trib["F3_one_way_shear_unsafe"]
            and not trib["engineering_approval"],
            "R6.14 source slab edge and engineering HOLD changed")
    require(trib_receipt["source_governing_pair"] == cases["source_model_fingerprints"],
            "R6.14 ULS/SLS source pair mismatch")
    r615, r615_receipt = export_incomplete(base=trib)
    require(r615["coverage"]["slabs_examined"] == 77
            and r615["coverage"]["source_edges_examined"] == 308
            and sum(r615["coverage"]["review_group_counts"].values()) == 77
            and sum(r615["coverage"]["frame_edge_class_counts"].values()) == 308
            and r615["baseline"]["r614_complete_four_edge_shells"] == 25
            and r615["baseline"]["source_graph_unanchored"] == 12
            and not r615["original_source_gravity_actions_modified"]
            and not r615["original_R614_45deg_allocations_modified"]
            and not r615["member_design_loads_modified"]
            and not r615["shell_contact_gate_promoted"]
            and r615["F3_one_way_shear_unsafe"]
            and not r615["engineering_approval"], "R6.15 source classification/HOLD failed")
    require(r615_receipt["governing_ULS_SLS_SHA256"] == cases["source_model_fingerprints"],
            "R6.15 source model fingerprint mismatch")

    reproduction, reproduction_receipt = export_reproducibility(r615=r615)
    require(reproduction["module_count"] == 18
            and reproduction["module_coverage_status_counts"] == {
               "DRAFT_UNVALIDATED":1,"IMPLEMENTED_BOUNDED":2,"MISSING":4,"PARTIAL":11}
            and reproduction["reproduction"]["Gate21_assumption_frame_solved_cases"] == 5
            and reproduction["reproduction"]["R615_original_edges_inspected"] == 308
            and not reproduction["reproduction"]["full_governing_ETABS21_model_equivalent"]
            and not reproduction["reproduction"]["all_historical_report_results_recomputed"]
            and not reproduction["engineering_approval"]
            and reproduction["twelve_unsupported_shells_excluded"]
            and reproduction["F3_one_way_shear_unsafe"],
            "R6.16 source-to-report acceptance gate failed")
    require(reproduction["source_scope"]["governing_ULS_SLS_SHA256"]
           == cases["source_model_fingerprints"],
           "R6.16 source pair not governing")
    require(not reproduction_receipt["engineering_approval"]
           and reproduction_receipt["F3_one_way_shear_unsafe"],
           "R6.16 evidence receipt invalid")

    canonical, canonical_receipt = export_canonical(mesh=source_mesh,casebook=cases)
    require(canonical["counts"]["source_frame_objects"] == 165
            and canonical["counts"]["source_shell_objects"] == 115
            and canonical["counts"]["source_components"] == 5
            and canonical["counts"]["original_source_fixed_base_point_ids"] == 27
            and canonical["counts"]["used_in_current_coarse_FE_fixed_base_nodes"] == 21
            and canonical["counts"]["source_graph_connected_shells"] == 103
            and canonical["counts"]["original_unanchored_shells_excluded"] == 12
            and canonical["counts"]["independently_solved_bounded_gravity_cases"] == 8
            and canonical["counts"]["signed_individual_base_reactions"] == 168
            and canonical["equilibrium_of_research_gravity_cases_verified"]
            and not canonical["native_ETABS21_generated_joints_or_releases_verified"]
            and not canonical["full_ETABS21_3D_model_reconstructed_and_validated"]
            and canonical["no_new_fixed_restraints_or_beam_shell_ties_created"]
            and canonical["no_source_unsupported_shell_was_added_to_solver"]
            and canonical["F3_one_way_shear_unsafe"]
            and not canonical["engineering_approval"],
            "R6.17 source graph, signed equilibrium or safety gate failed")
    require(canonical["governing_ULS_SLS_input_SHA256"]
            == cases["source_model_fingerprints"],
            "R6.17 governing model revision mismatch")
    require(canonical_receipt["F3_one_way_shear_unsafe"]
            and not canonical_receipt["engineering_approval"],
            "R6.17 receipt failed safety gate")

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


    original = project_report.read_text(encoding="utf-8")
    review_block = ('<section class="rb-card project-tools" id="project-r6p15-incomplete">'
        '<h2>R6.15 · Individual review of 77 unresolved slab perimeters</h2>'
        '<p>Source beam-segment gaps, overlaps, adjacent FLOOR objects and '
        'non-sectioned LINE proximity; strictly hypothetical one-way and '
        'cantilever studies only. No accepted support path or design loads.</p>'
        '<p><a href="projects/pokhara-g15/incomplete-edges.html">'
        'Inspect all 77 withheld slabs and source edges</a></p></section>\n')
    if 'id="project-r6p15-incomplete"' not in original:
        if target not in original:
            raise ValueError("R6.15 report original hand-calculation anchor disappeared")
        project_report.write_text(original.replace(target,review_block+target,1),encoding="utf-8")

    original = project_report.read_text(encoding="utf-8")
    readiness_block = ('<section class="rb-card project-tools" id="project-r6p16-reproducibility">'
        '<h2>R6.16 · Can our engine reproduce the complete structural report?</h2>'
        '<p>Executed OpenSees research vs historic ETABS21 source equivalence, '
        'all 18 implementation modules, remaining acceptance gaps and safety holds. '
        'Source report fully verified: NO. Numerically reproducible bounded reports: YES.</p>'
        '<p><a href="projects/pokhara-g15/reproducibility.html">'
        'Open first-party engine and report reproducibility review</a></p></section>\n')
    if 'id="project-r6p16-reproducibility"' not in original:
        if target not in original:
            raise ValueError("Original project hand-calculation anchor disappeared")
        project_report.write_text(original.replace(target,readiness_block+target,1),encoding="utf-8")

    original = project_report.read_text(encoding="utf-8")
    canonical_block = ('<section class="rb-card project-tools" id="project-r6p17-canonical">'
        '<h2>R6.17 · Canonical original-source 3D model and research gravity equilibrium</h2>'
        '<p>Original source node/frame/shell graph, individually reviewed 12 source-unanchored '
        'shells and 21 signed base-reaction records for each of eight bounded research gravity cases. '
        'No native ETABS21 joint or reaction equivalence or RCC design acceptance.</p>'
        '<p><a href="projects/pokhara-g15/canonical-model.html">'
        'Open 3D source model, twelve shell holds and gravity reaction QA</a></p></section>\n')
    if 'id="project-r6p17-canonical"' not in original:
        if target not in original:
            raise ValueError("R6.17 original hand-calculation anchor disappeared")
        project_report.write_text(original.replace(target,canonical_block+target,1),encoding="utf-8")

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
            require('id="project-r6p17-canonical"' in report,
                    "R6.17 canonical source 3D audit link missing")
            require((SITE/"projects/pokhara-g15/canonical-model.html").is_file(),
                    "R6.17 canonical source model browser page missing")
            require('id="project-r6p16-reproducibility"' in report,
                    "R6.16 engine/report readiness link missing")
            require((SITE/"projects/pokhara-g15/reproducibility.html").is_file(),
                    "R6.16 reproducibility page missing")
            require('id="project-r6p15-incomplete"' in report,
                    "R6.15 unresolved perimeter audit link missing")
            require((SITE/"projects/pokhara-g15/incomplete-edges.html").is_file(),
                    "R6.15 77-case browser report missing")
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
