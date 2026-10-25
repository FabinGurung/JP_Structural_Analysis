# G15 Chapter 1 source evidence audit — 25 October 2026

This release begins sequential review of the original 68-page private report, covering original §1.1 Executive Summary, §1.2 Structural Modelling and §1.3 Structural System. It does not assert the user's G+1.5 model matches ETABS numerically; the requirement is to follow an engineering process with OpenSees, transparent mathematics, source-cited inputs and defensible code checks.

Original private authority: Google Drive ID 1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM; original title `new nbc2025 report REVISED(1).pdf`; SHA-256 `f122904444a2e2f75230d9d4e41da0093d050da25c6e8140c86d466b7e37cc52`. Source was read from connected Drive on 2026-10-25, preserving original statements and conflicts without rewriting the original.

§1.1 original source states Pokhara/Lekhnath, G+1.5, 3.048m per level, 9.144m total, residential, RC SMRF, M20, Fe500, three footing types, soil class D and source allowable 160kN/m2 at 1.5m. Conflicts held: commercial ground-floor use and closing-office occupancy descriptions; source 'Kathmandu' seismic zone despite reported Pokhara location; NBC105:2020 vs NBC105:2025 source references; source 14x14in column versus later 400x400mm columns. None is silently normalized into a physical truth.

§1.2 source describes ETABS v20.0.0 model and SAFE foundation, centreline geometry, rectangular members, two horizontal seismic directions and claimed static + response spectrum. Current independent OpenSees solves FIVE static cases of a provisional frame only; do not mislabel as authentic ETABS or completed response spectrum. §1.3 RC SMRF and frame load path described as desired system, not confirmed code compliance.

20 de-identified observation entries from the source and current code are in `site/data/g15-chapter01-source-review.v0.1.json`, with 7 explicit unaccepted Chapter1 engineering evidence gates. 0 accepted, 7 OPEN; not a permit/approved design. F3 from original §6.4 remains explicitly NOT SAFE IN ONE WAY SHEAR.

The client-designer identity, phone, email and private drawing content were not copied to public GitHub. Script `scripts/check_g15_chapter01_source.py` independently validates source labels, open gates and public HTML. Next original chapter is Chapter 2 (material grades, reinforcement, cover, reference codes, plans, gravity and seismic actions).
