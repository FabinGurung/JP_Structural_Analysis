# Gate21 working OpenSees Structural Report — execution and limits

Run: python -m pip install -e ".[test,opensees]"
Run: python scripts/build_g15_gate21_report.py --output-dir build/g15-gate21/report

Generated from actual OpenSees 3D elastic 6DOF beam-column code, five individually solved signed load cases, 165 provisional frame members. Exports HTML (Print/Save PDF), Markdown, JSON, CSV with 825 complete 12-component member-end action records, SHA256 manifest. GitHub Actions and Pages run the same code.

Original private structural PDF Drive ID 1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM SHA256 f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52; DOCX ID 19q3h_rBHMP14fbkVcZ424iNJpomR7Wyz. Layout source physical pp9–11, p42; original seismic weight p25; original story mass table p34; unsafe F3 p61.

Conditional source Wi uses source mass values Story1 270076.47, Story2 274062.74, Story3 152521.81, units assumed kg (unprinted), multiplied by standard gravity 9.80665/1000. The model's total 6831.910791783 kN agrees arithmetically with source 6831.9109kN. It is NOT a verified original ETABS mass-source assignment.

All other defaults are cited as working inputs, not fabricated source data: G15 23-column and 165-member source-derived assumed grid, 2 unsupported connectors, E=22360.6798MPa, cracked ULS EI modifiers, T=.493s, Cd=.131, fixed bases and seismic-W surrogate for GRAVITY.

Open equations: W=sum Wi; V=Cd W; Fi=V Wi hi^k/sum(Wj hj^k); story elastic chord ratio computed same node over adjacent floors. Source numerical implementation uses NBC105:2025 6.2/6.3. Each OpenSees solve passes global force and moment equilibrium tolerance <0.001.

Custom bounded input: --request-json /private/my_case.json with exact keys solver_request and provenance. Provenance must cover every physical input with class ASSUMED, CONDITIONAL_SOURCE or SOURCE_REPORTED_UNVERIFIED plus citation and uncertainty. The original native ETABS model, gravity component loads, true floor areas, wall paths, modal spectra, accidental torsion, P-Delta, accepted NBC drift and reinforcement schedules remain unavailable/not completed.

Original footing F3 remains NOT SAFE IN ONE WAY SHEAR. No structural design, construction approval or seal. Do not expose private original sources on GitHub.
