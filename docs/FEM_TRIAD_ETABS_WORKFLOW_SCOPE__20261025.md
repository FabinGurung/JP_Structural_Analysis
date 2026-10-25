# FEM learning lab and ETABS-inspired workflow (2026-10-25)

The ETABS taxonomy (official User Guide) comprises File, Edit, View, Define, Draw, Select, Assign, Analyze, Display, Design, Detailing, Options, Tools/Plugins, Help. This does not mean its interface is necessarily a ribbon; the official UI describes menus, toolbars, explorer and multi-view windows. We reproduce **workflow concepts**, never copyrighted CSS/images/UX artwork or claim ETABS numerical compatibility.

The user's practical boundary-conditions question has no automatic site-independent answer. Restraint degrees of freedom must be deduced from drawings, foundation/soil interaction, structural continuity and deliberate model assumptions and independently checked. Loads must be deduced from authentic occupancy, slabs/material mass, walls, code actions, geometry and their locations. Never infer from total seismic mass alone.

The instructional 2D cantilever is explicitly a MADE-UP example, fixed base at (0,0), tip at (0,3m), horizontal tip load 5/10/15/20 kN, E 25,000MPa, b=h=0.3m. OpenSeesPy elasticBeamColumn solves the actual static linear FE problem. Independent manual formulas M=FL, V=F, u=FL^3/(3EI), theta=FL^2/(2EI) verify it. Source report numbers do not participate.

The workflow-schema registry lists 14 menu delegations and 16 proposed normalized entity tables; these are a *design plan* only, not a new deployed SQL DB or guaranteed 6NF. Each entity joins by its PK/FK and has durable provenance. Data records may be JSON/CSV in GitHub Actions today; eventual normalized SQLite/PostgreSQL should follow verified requirement. Existing repo NBC105:2025 verified inventory has 14 scoped clause groups; not the entirety of NBC or fully validated RC bar selection. NBC205:2024 RUD must pass applicability and 2020->2025 reconciliation.

The FEM lesson's Three.js/SVG/tables/manual solving are to be integrated into More and original Chapter 2 gets input-location and boundary proof requirements. No engineering acceptance or F3 redesign in this lesson.
