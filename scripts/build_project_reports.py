#!/usr/bin/env python3
"""Assemble project reports and the standalone hand-calculation sheet for Pages."""
from html import escape
import json
from pathlib import Path
import re
from string import Template

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PROJECTS = ROOT / "registry/project-reports.json"
SHEET = ROOT / "templates/hand-calculation.html"
NAV = '<nav class="navigation" aria-label="Primary navigation">'


def calculation(**fields):
    values = {name: escape(value) for name, value in fields.items() if name != "working"}
    values["working"] = "".join(f"<li>{escape(line)}</li>" for line in fields["working"])
    return Template(SHEET.read_text()).substitute(values)


def plot(floors):
    """Horizontal bars and printed values for the source-applied floor loads."""
    maximum = max(500, 500 * -(-max(value for _, value in floors) // 500))
    if not floors or any(not 0 <= value <= maximum for _, value in floors):
        raise ValueError("Floor load values exceed the labelled plot scale")
    rows = []
    for index, (label, value) in enumerate(floors):
        y = 23 + index * 48
        rows.append(f'<text x="0" y="{y + 15}">{escape(label)}</text>'
                    f'<rect x="48" y="{y}" width="{value / maximum * 370:.2f}" height="21" rx="3" fill="#227175"/>'
                    f'<text x="432" y="{y + 15}">{value:,.2f}</text>')
    axis_y = 23 + len(floors) * 48
    for tick in range(0, int(maximum) + 1, 500):
        x = 48 + tick / maximum * 370
        rows.append(f'<path d="M{x:.2f} {axis_y - 6}v6" stroke="currentColor"/>'
                    f'<text x="{x:.2f}" y="{axis_y + 16}" text-anchor="middle">{tick:,}</text>')
    return (f'<svg viewBox="0 0 560 {axis_y + 26}" role="img" aria-labelledby="floor-plot-title" '
            f'fill="currentColor" font-size="15"><title id="floor-plot-title">Applied loads by floor in kilonewtons</title>'
            f'<path d="M48 {axis_y}h370" stroke="currentColor"/>{"".join(rows)}</svg>')


def page(title, content):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<base href="../"><title>{escape(title)} | JP Structural Analysis</title>
<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="project-report.css"></head>
<body><header class="site-header"><div class="wrap nav-row">
<a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">JP</span><strong>Structural Analysis</strong></a>
{NAV}<a href="index.html">Home</a><a href="projects/index.html">Projects</a><a href="templates/index.html">Calculation template</a><a href="more.html">Methods &amp; archive</a></nav>
</div></header><main class="wrap project-index">{content}</main></body></html>
"""


def project_tools(project):
    data = json.loads((SITE / project["source_catalogue"]).read_text())
    beam = next(member for member in data["members"] if member["key"] == project["worked_beam"])
    section = data["frame_sections"][beam["section"]]
    width, depth = section["width_mm"], section["depth_mm"]
    length = beam["length_mm"]
    wall = next(load for load in beam["applied_loads"] if load["pattern"] == "WALL LOAD")
    rate = wall["working"]["w_N_per_mm"]
    wall_force = rate * length / 1000
    volume = width * depth * length / 1e9
    storeys = [(name, data["level_summary"][name]["source_mass_eligible_applied_gravity_kN"])
               for name in ("GF", "FF", "TF")]
    total = sum(weight for _, weight in storeys)
    floor_working = []
    for name, weight in storeys:
        loads = data["level_summary"][name]["source_pattern_load_kN"]
        wall_kN = loads.get("WALL LOAD", 0)
        finish_kN = loads.get("FLOOR FINISH", 0)
        live_share_kN = loads.get("Live", 0)
        if abs(wall_kN + finish_kN + live_share_kN - weight) > 0.00001:
            raise ValueError(f"{name}: floor load components do not add up")
        floor_working.append(
            f"{name} = {wall_kN:,.3f} + {finish_kN:,.3f} + "
            f"(0.30 × {live_share_kN / 0.30:,.3f}) ≈ {weight:,.3f} kN."
        )
    sheets = calculation(
        number="01 / Beam loading", title=f"Wall load and concrete volume for {beam['key'].replace(':', ' ')}",
        reference="Reference · ETABS 21 beam dimensions and wall load assignment",
        find="Find the wall load carried along the beam and the gross volume of concrete.",
        given=f"Width = {width:g} mm. Depth = {depth:g} mm. Centreline length = {length:,.0f} mm. Wall load = {rate:g} N/mm.",
        assumptions="The wall load is uniform along the full beam. Use the centreline length for the gross concrete volume.",
        working=[
            f"Section area = width × depth = {width:g} × {depth:g} = {width * depth:,.0f} mm².",
            f"Gross concrete = area × length = {width * depth:,.0f} × {length:,.0f} = {width * depth * length:,.0f} mm³.",
            f"Divide by 10⁹ to convert to cubic metres. Gross concrete = {volume:.5f} m³.",
            f"Wall force = load per metre × length = {rate:g} kN/m × {length / 1000:g} m = {wall_force:.5f} kN.",
        ],
        answer=f"{volume:.5f} m³ of gross concrete and {wall_force:.5f} kN of downward wall force.",
        check="The wall force excludes the beam’s own weight and loads from the floor. Joint deductions are needed for a net concrete take-off.",
    )
    sheets += calculation(
        number="02 / Floor loads", title="Add the loads used in the floor comparison",
        reference="Reference · ETABS 21 wall, floor-finish and live load assignments",
        find="Compare the assigned loads on the ground, first and top floors.",
        given="Take the full assigned wall and floor-finish loads and 30% of the live load on each floor.",
        assumptions="The comparison covers assigned loads only. Structural self-weight is calculated separately.",
        working=[
            "For each floor, add wall load + floor finish + (0.30 × live load).",
            *floor_working,
            "Total = " + " + ".join(f"{weight:,.3f}" for _, weight in storeys) + f" ≈ {total:,.3f} kN.",
        ],
        answer=f"Combined assigned load for the three floors = {total:,.3f} kN.",
        check="The total is a subtotal for the stated loads. A seismic weight check also needs the structure’s own weight and the rest of the applicable mass contributions.",
    )
    trial = json.loads((SITE / project["casebook"]).read_text())
    finish = trial["role_results"]["ULS"]["independently_run_research_patterns"]["FLOOR FINISH"]
    applied = finish["applied_gravity"]["total_applied_downward_N"]
    reaction = finish["sum_native_fixed_base_reactions_N"][2]
    residual = finish["vertical_equilibrium_residual_N"]
    sheets += calculation(
        number="03 / Support reactions", title="Balance the floor-finish load",
        reference="Reference · R6.10 floor-finish run with ultimate-limit-state stiffness",
        find="Check that the upward support reactions balance the downward floor-finish load.",
        given=f"Applied floor-finish load = {applied / 1000:,.6f} kN downward. Sum of vertical reactions = {reaction / 1000:,.6f} kN upward.",
        assumptions="Use the trial with 103 connected shells. Take upward as positive. The other 12 shells require a separate support check.",
        working=[
            "Add the vertical forces. The sum should be zero.",
            f"ΣFz = +{reaction / 1000:,.6f} − {applied / 1000:,.6f} kN.",
            f"Using the unrounded forces, the difference is {residual:.6f} N.",
        ],
        answer="The vertical reactions balance the floor-finish load within the numerical tolerance.",
        check="This check applies to the load and supports included in this run. It leaves the missing shell support paths open.",
    )
    viewer = escape(project["viewer"], quote=True)
    return f"""<section class="rb-card project-tools" id="project-figures" aria-labelledby="project-figure-heading">
<h2 id="project-figure-heading">Figures and linked model views</h2>
<figure class="project-figure">{plot(storeys)}
<figcaption>Figure 1. Assigned wall load, floor finish and 30% of live load by floor. Values in kN. Structural self-weight is excluded.</figcaption></figure>
<figure class="project-figure"><iframe class="project-model" loading="lazy" src="{viewer}?view=report#r610-mesh" title="Linked 2D plan and 3D shell views for {escape(project['name'], quote=True)}"></iframe>
<figcaption>Figure 2. Select a shell in either view to locate it in both. Orange identifies shells whose vertical support path still needs checking.</figcaption></figure>
<p class="project-links"><a href="{viewer}#r610-mesh">Open full shell views</a><a href="etabs21-member-book.html">Open linked beam and column views</a><a href="{viewer}#r610-solver">Read the R6.10 case results</a></p>
</section>
<section class="rb-card project-tools" id="project-hand-calculations" aria-labelledby="project-hand-heading">
<h2 id="project-hand-heading">Hand calculations</h2>
<p>Work through the dimensions and loads in order. <a href="templates/index.html">Open the blank calculation sheet</a>.</p>
{sheets}
<p><a href="worked-calculations.html">Read the extended calculation book</a></p></section>"""


def build():
    projects = json.loads(PROJECTS.read_text())
    entries = []
    for project in projects:
        slug = project["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Invalid project slug: {slug}")
        route = f"projects/{slug}/report.html"
        original = (SITE / project["report"]).read_text()
        html = original.replace("<head>", '<head><base href="../../"><link rel="stylesheet" href="project-report.css">', 1)
        cover = '<div class="rb-guidance" role="note">'
        if html.count(cover) != 1:
            raise ValueError(f"{slug}: report cover boundary changed")
        html = html.replace(cover, project_tools(project) + "\n" + cover)
        html = html.replace('<nav id="rb-chapter-nav">', '<nav id="rb-chapter-nav"><a href="#project-figures">Figures and model</a><a href="#project-hand-calculations">Hand calculations</a>')
        html = html.replace('href="#report-contents">Read report ↓</a>', 'href="#report-contents">Read report ↓</a><a class="btn secondary" href="#project-hand-calculations">Hand calculations</a><a class="btn secondary" href="#project-figures">Figures and model</a>')
        html = html.replace('aria-current="page" href="report.html"', f'aria-current="page" href="{route}"')
        html = html.replace('href="report.html#', f'href="{route}#')
        html = html.replace('href="#', f'href="{route}#')
        destination = SITE / route
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html)
        entries.append(f'<article class="panel"><p class="eyebrow">Structural report · Review edition</p><h2>{escape(project["name"])}</h2>'
                       f'<p>{escape(project["description"])}</p><div class="project-links"><a class="btn primary" href="{route}">Open report</a>'
                       f'<a href="{route}#project-hand-calculations">Hand calculations</a><a href="{route}#project-figures">Figures and linked views</a></div></article>')
    (SITE / "projects/index.html").write_text(page("Projects", "<h1>Project reports</h1><p>Read a building’s report, check its working and inspect the model.</p>" + "".join(entries)))
    blank = calculation(
        number="Calculation sheet", title="Member or check name", reference="Drawing, report section or site measurement",
        find="State the quantity or check you are working out.",
        given="List dimensions, loads and material properties with units.",
        assumptions="State the support conditions, load shape and any values you have assumed.",
        working=["Write the equation and explain its symbols.", "Put the known values into the equation, keeping the units visible.", "Show the intermediate steps and any unit conversions."],
        answer="Write the result with its unit and the rounding used.",
        check="Check units, signs and balance where applicable. Record anything still to be confirmed.",
    )
    (SITE / "templates").mkdir(exist_ok=True)
    (SITE / "templates/index.html").write_text(page("Hand-calculation template", "<h1>Hand-calculation template</h1><p>Use one sheet per member or check. Put the supporting sketch or plot next to the working and refer to it by number.</p>" + blank + '<p><a href="projects/index.html">See completed examples in the project reports</a></p>'))


if __name__ == "__main__":
    build()
