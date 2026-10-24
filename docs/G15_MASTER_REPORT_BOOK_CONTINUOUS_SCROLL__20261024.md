# G15 master report reader v1 — continuous scroll

The primary `site/report.html` now presents the original revised source report's contents in the correct reader order:

- Cover and report status
- Table of contents with anchored chapters and sticky navigation
- Chapter 01 Introduction/executive/structural modelling
- Chapter 02 Materials, cover, sections, architectural layout
- Chapter 03 Loads, wall/finish/live, conditional seismic actions, ULS/SLS status
- Chapter 04 OpenSees modelling, five signed solved cases, force and moment equilibrium
- Chapter 05 Displacements, same-grid elastic chord ratios, and unverified modal/irregularity checks
- Chapter 06 Columns, beams, slabs, foundations (F3 NOT SAFE), staircase design readiness
- Chapter 07 QA, unresolved proof obligations, source citations and download/print exports.

The whole document remains in one continuous scrolling page. It does not change or remove Project Lab/3D Studio/calculation modules and preserves the previous M09, D2, Gate05, Gate06 and Gate21 report evidence sections, relocated into relevant chapters inside native HTML <details> panels. The original revised PDF remains in private Drive (file ID 1TpWUmOdrcQqOpkN6qvmhZ12KrYaNABBM); the public page cites it without republishing its source drawings.

`site/report-book.js` reads the generated `site/reports/g15-gate21-report.v0.1.json` file and fills provenance inputs, ESM floor weights and forces, five actual OpenSees case displacement/reactions/equilibrium, elastic story chords and hard engineering HOLD state. It explicitly rejects any unexpected schema or approval state. Site JavaScript never initiates a solver or claims that scrolling executes OpenSees.

GitHub Actions uses the pinned tested OpenSees source to run, validate and regenerate report JSON and HTML before deploying Pages. The user may independently run scenario workflows for fresh artifact outputs; these do not automatically replace the master public report. Print gives a readable browser PDF. Source code, tests and original Gate21 reports remain intact.

The chapter headings are **presentation organization**, not claims of completed design. Source-reported seismic coefficients and period remain unverified for the native model; original F3 source finding is unsafe. No missing RC design, source mass components, soil investigation, modal spectrum or reinforcement checks have been invented.
