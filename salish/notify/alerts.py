"""Compose surf alert emails from a spot's config and its latest buoy reading."""

import math
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from salish.core.config import place
from salish.core.geodesy import angle_diff, bearing, distance
from salish.processing.alerts import travel_bearing
from salish.processing.conditions import current_at, tide_trend, wind_state

G = 9.81


def _label(name):
    return name.replace("_", " ").title()


def _travel_speed(T, depth_m=None, current_cm_s=0.0):
    """Wave speed in m/s: deep-water if depth_m is None, else at that depth."""
    if depth_m is None:
        return G * T / (2 * math.pi)
    L = G * T**2 / (2 * math.pi)
    c = math.sqrt(G * L / (2 * math.pi) * math.tanh(2 * math.pi * depth_m / L))
    return c + current_cm_s / 100


def compose(cfg, spot, obs, tides, currents, tz):
    rules = spot["alert"]
    origin = place(cfg, spot["buoy"])
    when = obs["datetime"]
    fmt = lambda t: t.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z")
    travel = travel_bearing(obs)
    current = current_at(currents, when)

    lines = [
        f"Summary from the {spot['name']} buoy at {fmt(when)}:",
        "",
        f"  - Wave height: {obs['WVHT']} m",
        f"  - Dominant period: {obs['DPD']} s",
    ]
    if obs.get("APD") == obs.get("APD"):  # not NaN
        lines.append(f"  - Average period: {obs['APD']} s")
    lines += [
        f"  - Estimated wave energy: {obs['wave_energy']:.2f} kJ/m²",
        f"  - Waves travelling toward: {travel:.0f}°",
    ]

    if "aimed_at" in rules:
        target = rules["aimed_at"]["place"]
        az = bearing(origin, place(cfg, target))
        lines.append(f"  - Bearing to {_label(target)}: {az:.0f}° (waves are {angle_diff(travel, az):+.1f}° off it)")

    if "bearing_needed" in rules:
        need = rules["bearing_needed"]
        b = (bearing(place(cfg, need["at"]), place(cfg, need["from"])) + 180) % 360
        lines.append(f"  - Waves reach {_label(need['at'])} travelling toward about {b:.0f}°")

    if "travel_to" in rules:
        dest = rules["travel_to"]["place"]
        dist = distance(origin, place(cfg, dest))
        speed = _travel_speed(obs["DPD"], rules["travel_to"].get("depth_m"),
                              current[0] if current and "depth_m" in rules["travel_to"] else 0.0)
        hours = dist / (speed * 3600)
        landfall = when + timedelta(hours=hours)
        lines.append(f"  - First waves reach {_label(dest)} ({dist/1000:.0f} km) in {hours:.1f} h, around {fmt(landfall)}")

    lines.append("")
    tide = tide_trend(tides, when)
    if tide:
        height, change, status = tide
        lines.append(f"  - Tide is {height:.2f} m and {status}, changing {change:+.2f} m in the next hour")
    if current:
        velocity, status = current
        lines.append(f"  - Current is {status}, moving at {velocity:.1f} cm/s")
    if rules.get("report_wind"):
        lines.append(f"  - Wind is {wind_state(obs)} at {obs['WSPD']} m/s, from {obs['WDIR']}°")

    lines += ["", f"  Photos: https://www.ndbc.noaa.gov/station_page.php?station={spot['buoy']}"]

    message = MIMEMultipart("alternative")
    message["Subject"] = rules["subject"]
    message.attach(MIMEText("\n".join(lines) + "\n", "plain"))
    return message
