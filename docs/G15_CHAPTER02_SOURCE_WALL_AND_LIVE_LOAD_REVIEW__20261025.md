# Chapter 2.5/2.6 source-quantity validation without invented wall objects (2026-10-25)

Original §2.5 names plans Fig 3–4 but does not give our engine accepted slab, openings, wall segment, frame object IDs and load assignments. Original §2.6.2 has 2 kN/m² rooms, 1.5 terrace, 3 corridor/stair; original residential classification conflicts with other source use labels. Source geometry/occupancy admission remains open.

Original §2.6.3 uses H3.05m, γ19.2kN/m³, beam depth0.40m, t=.23/.11m, 21%/20% openings and H1=.95m/parapet t=.12m. Native function wall_line_dead_load independently recomputes gross/net main/partition and parapet: [11.7024,9.244896,5.5968,4.47744,2.1888] kN/m. Original printed [11.69,9.24,5.59,4.47,2.10]; gross main and parapet differ by >0.01 kN/m. Do not rewrite original. A 3.05 vs 3.048m storey number discrepancy is highlighted. No source wall segment ID, target beam ID, slab polygon, original pattern, or load assignment invented.

Publish machine JSON at site/data/g15-chapter02-load-review.v0.1.json. Keep source physical claims and F3 one-way shear hold. Source-gate accepted=0, original Gate20 15 unaccepted. Computational review does not imply source-to-physical acceptance.
