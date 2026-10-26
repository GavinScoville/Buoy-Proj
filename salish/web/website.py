import math
import os
from datetime import datetime

from salish.core.config import place
from salish.core.geodesy import distance
from salish.paths import PLOTS, SIMULATIONS, SITE

# Renders artifacts/site/Salish-Surf-Report.md. Sections follow the model
# order: WAVEWATCH III forecast, ray tracing (Pacific, Strait, Islands),
# spectral (mild-slope) model, finite-difference model, then buoy reports.

REPORT = SITE / "Salish-Surf-Report.md"


def _image(path, alt):
    if not os.path.exists(path):
        return "_No output yet._"
    return f"![{alt}]({os.path.relpath(path, SITE)})"


def _stage_note(stage):
    """One-line note when a section's figures are not from this run."""
    if stage is None or stage.status == "ok":
        return ""
    if stage.status == "disabled":
        return "_Disabled in config; any figures below are from an earlier run._\n\n"
    return f"_Not updated this run ({stage.status}: {stage.note}); any figures below are from an earlier run._\n\n"


def _wavewatch(stages):
    return f"""## Swell Forecast (WAVEWATCH III)

{_stage_note(stages.get("wavewatch"))}NOAA's GFS-Wave (WAVEWATCH III) forecast at the Neah Bay buoy. Each panel shows
the swell partitions as arrows pointing the way the waves travel; length is height
and colour is period.

{_image(PLOTS / "swell_forecast.png", "Daily swell forecast")}

<details>
<summary><strong>Hourly forecast, next 48 hours</strong></summary>

{_image(PLOTS / "swell_forecast_hourly.png", "Hourly swell forecast")}

</details>
"""


def _ray_tracing(stages):
    return f"""## Ray Tracing

### Across the Pacific
{_stage_note(stages.get("pacific_rays"))}{_image(PLOTS / "maps" / "pacific.png", "Pacific wave propagation")}

1,600 km off the coast, the Ocean Papa buoy collects wave data.
Using this information, we can infer the trajectory of waves as they travel across the Pacific.
This map uses spherical trigonometry to calculate the azimuth and great-circle path of each wave.
It does not yet include the Coriolis effect — coming soon.

### Strait of Juan de Fuca
{_stage_note(stages.get("ray_tracing"))}{_image(PLOTS / "maps" / "Strait.png", "Strait refraction")}

At the entrance of the Salish Sea, the Neah Bay buoy provides us basic wave data.
No other surf models currently incorporate how these waves refract across the Strait.
This ray-tracing diagram illustrates how the coastline bends and redirects incoming wave energy.
A simple algorithm currently predicts wave height by holding energy flux constant.

### Islands Region
{_image(PLOTS / "maps" / "Island.png", "Islands refraction")}

The rays linearly interpolate between the Port Angeles Buoy and the New Dungeness Buoy.
Waves pass over many underwater features but only experience friction and thus
refraction when the depth is less than half the wavelength.
"""


def _spectral(stages):
    stage = stages.get("spectral")
    stats = ""
    if stage is not None and stage.status == "ok":
        r = stage.output
        stats = (f"- **Offshore:** {r['offshore_Hs']:.2f} m at {r['T']:.0f} s from {r['mwd']:.0f}°\n"
                 f"- **Largest wave height in the domain:** {r['max_Hs']:.2f} m "
                 f"({r['max_Hs'] / r['offshore_Hs']:.2f}× offshore)\n"
                 f"- **95th percentile:** {r['p95_Hs']:.2f} m\n"
                 f"- **Cells limited by breaking:** {r['breaking_pct']:.2f}%\n\n")
    return f"""## Spectral Model (Parabolic Mild-Slope)

{_stage_note(stage)}A directionally spread sea state from the Neah Bay buoy is marched shoreward across
10 m bathymetry, capturing refraction, shoaling, diffraction and depth-limited breaking.
The right panel shows the Iribarren number along the shore: whether waves there
spill, plunge or surge, from the local seabed slope and the modelled wave height.

{stats}{_image(PLOTS / "mild_slope_simulation.png", "Mild-slope wave height and Iribarren number")}
"""


def _view_3d(name):
    """Collapsible 3D panel: the still render, plus a link to the interactive
    scene. Markdown cannot render the PyVista HTML inline, so the still is what
    actually shows in the report and the HTML is one click away."""
    png = SIMULATIONS / name / "wave_3d.png"
    html = SIMULATIONS / name / "wave_3d.html"
    if not os.path.exists(png) and not os.path.exists(html):
        return "_No 3D view yet._"
    lines = ["<details>",
             f"<summary><strong>3D view of {name.replace('_', ' ')}, last frame</strong></summary>",
             "",
             _image(png, f"{name} 3D wave surface"),
             ""]
    if os.path.exists(html):
        lines += [f"[Open the interactive version →]({os.path.relpath(html, SITE)})", ""]
    lines.append("</details>")
    return "\n".join(lines)


def _finite_difference(cfg, stages):
    stage = stages.get("finite_difference")
    results = {}
    if stage is not None and stage.status == "ok":
        results = {r["location"]: r for r in stage.output}
    blocks = []
    for loc in cfg["models"]["finite_difference"]["locations"]:
        block = f"### {loc['name'].replace('_', ' ')}\n{loc['description']}\n\n"
        r = results.get(loc["name"])
        if r is not None and r.get("status") in ("success", "completed_with_warning"):
            p = r["buoy_params"]
            block += (f"- **Forcing:** {p['h']:.2f} m, {p['T']:.0f} s, from {p['direction']:.0f}°\n"
                      f"- **Grid:** {r['grid_shape'][0]}×{r['grid_shape'][1]} points\n\n")
        elif r is not None:
            block += f"_Not updated this run: {r.get('error', r.get('status'))}._\n\n"
        block += _image(SIMULATIONS / loc["name"] / "wave_simulation.gif", f"{loc['name']} simulation")
        block += "\n\n" + _view_3d(loc["name"])
        blocks.append(block)
    return (f"## Finite-Difference Model (Airy Waves)\n\n{_stage_note(stage)}"
            "Time-stepped linear wave simulations on 10-30 m bathymetry grids.\n\n"
            + "\n\n".join(blocks) + "\n")


def _spot_report(cfg, spot, obs, alert):
    name = spot["name"]
    if obs is None:
        return f"## {name}\n\n_No data from buoy {spot['buoy']} this run._\n"
    km = distance(place(cfg, spot["buoy"]), place(cfg, "fort_ebey")) / 1000
    lines = [
        f"## {name} Wave Report",
        f"Distance: {km:.0f} km to Fort Ebey",
        "",
        f"- **Wave height:** {obs['WVHT'] * 3.28084:.1f} ft",
        f"- **Dominant period:** {obs['DPD']} s",
        f"- **Wave energy:** {obs['wave_energy']:.0f} kJ/m of crest",
        f"- **Waves travelling toward:** {obs['wave_bearing']:.0f}°",
    ]
    if obs.get("WSPD") == obs.get("WSPD"):  # not NaN
        lines.append(f"- **Wind:** {obs['WSPD']} m/s from {obs.get('WDIR', 'N/A')}°")
    if alert is not None:
        status, reason = alert
        lines.append(f"- **Alert status:** {'WATCH' if status else 'normal'} ({reason})")
    lines += [
        "",
        "A meter of wave crest has the kinetic energy of a Prius traveling",
        f"**{math.sqrt(obs['wave_energy'] * 2 / 1350) * 2.23694:.1f} mph.**",
        "",
        "<details>",
        f"<summary><strong>Click to show {name} plots</strong></summary>",
        "",
    ]
    for kind in spot.get("plots", []):
        lines.append(_image(PLOTS / kind / f"{plot_name(spot)}.png", f"{name} {kind}") + "  ")
    lines += [
        "",
        "</details>",
        "",
        f"- [Station Page →](https://www.ndbc.noaa.gov/station_page.php?station={spot['buoy']})",
    ]
    return "\n".join(lines) + "\n"


def plot_name(spot):
    """File stem the plotting functions use for this spot."""
    return spot["name"].replace(" ", "_")


def render_site(cfg, obs, alerts, stages, tz):
    """
    obs: buoy id -> latest observation (or None); alerts: spot key ->
    (status, reason); stages: stage name -> StageResult.
    """
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")
    sections = [
        f"# Salish Sea Surf Report\n**Updated:** {timestamp}\n",
        _wavewatch(stages),
        _ray_tracing(stages),
        _spectral(stages),
        _finite_difference(cfg, stages),
        "# Wave Reports\n",
    ]
    sections += [_spot_report(cfg, s, obs.get(s["buoy"]), alerts.get(s["key"])) for s in cfg["spots"]]
    sections.append("*Report auto-generated from live NOAA buoy data and wave models.*\n")

    SITE.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n---\n\n".join(sections))
    print(f"Markdown report updated: {REPORT}")
    return REPORT
