"""SVG rendering of C12 benchmark plots."""

from __future__ import annotations

import math
from dataclasses import dataclass

def _map_to_svg(
    x: float, y: float, x_min: float, x_max: float, y_min: float, y_max: float,
    width: float = 600, height: float = 400, margin: float = 40
) -> tuple[float, float]:
    plot_width = width - 2 * margin
    plot_height = height - 2 * margin

    x_range = max(x_max - x_min, 1e-12)
    y_range = max(y_max - y_min, 1e-12)

    x_svg = margin + ((x - x_min) / x_range) * plot_width
    y_svg = height - margin - ((y - y_min) / y_range) * plot_height
    return x_svg, y_svg

def render_task_a_svg(history: list[tuple[float, list[float], list[float]]]) -> str:
    """Render Task A1 distances y1, y2, y3 over time as SVG."""
    width = 800
    height = 500
    margin = 50

    t_min = min(point[0] for point in history)
    t_max = max(point[0] for point in history)
    y_min = 0.0
    y_max = max(max(point[1]) for point in history)

    lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">',
        '  <style>',
        '    .axis { stroke: black; stroke-width: 1; }',
        '    .grid { stroke: #e0e0e0; stroke-width: 1; stroke-dasharray: 4; }',
        '    .label { font-family: sans-serif; font-size: 14px; fill: black; text-anchor: middle; }',
        '    .legend { font-family: sans-serif; font-size: 14px; }',
        '  </style>',
        f'  <text x="{width/2}" y="{margin - 20}" class="label" style="font-size: 16px; font-weight: bold;">Task A1: Relative Distances y1, y2, y3 over time (e=0.2)</text>'
    ]

    # Axes
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>')
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" class="axis"/>')

    # Grid & Labels
    x_ticks = 10
    for i in range(x_ticks + 1):
        x = t_min + (t_max - t_min) * i / x_ticks
        svg_x, svg_y = _map_to_svg(x, y_min, t_min, t_max, y_min, y_max, width, height, margin)
        lines.append(f'  <line x1="{svg_x}" y1="{height-margin}" x2="{svg_x}" y2="{margin}" class="grid"/>')
        lines.append(f'  <text x="{svg_x}" y="{height-margin+20}" class="label">{x:.1f}</text>')

    y_ticks = 5
    for i in range(y_ticks + 1):
        y = y_min + (y_max - y_min) * i / y_ticks
        svg_x, svg_y = _map_to_svg(t_min, y, t_min, t_max, y_min, y_max, width, height, margin)
        lines.append(f'  <line x1="{margin}" y1="{svg_y}" x2="{width-margin}" y2="{svg_y}" class="grid"/>')
        lines.append(f'  <text x="{margin-10}" y="{svg_y+5}" class="label" style="text-anchor: end;">{y:.1f}</text>')

    lines.append(f'  <text x="{width/2}" y="{height-margin+40}" class="label">Time t</text>')
    lines.append(f'  <text x="{margin-40}" y="{height/2}" transform="rotate(-90 {margin-40} {height/2})" class="label">Relative Distance</text>')

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    labels = ['y1', 'y2', 'y3']

    for i in range(3):
        path_data = []
        for point in history:
            t = point[0]
            y = point[1][i]
            svg_x, svg_y = _map_to_svg(t, y, t_min, t_max, y_min, y_max, width, height, margin)
            cmd = "M" if not path_data else "L"
            path_data.append(f"{cmd} {svg_x:.2f},{svg_y:.2f}")

        lines.append(f'  <path d="{" ".join(path_data)}" fill="none" stroke="{colors[i]}" stroke-width="2" />')

        # Legend
        leg_y = margin + 20 * i
        lines.append(f'  <line x1="{width-margin-80}" y1="{leg_y}" x2="{width-margin-50}" y2="{leg_y}" stroke="{colors[i]}" stroke-width="2"/>')
        lines.append(f'  <text x="{width-margin-40}" y="{leg_y+5}" class="legend">{labels[i]}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def render_task_b2_svg(sweep: dict[float, dict[str, object]]) -> str:
    """Render Task B2 final velocities x1, x2, x3, x4 vs e as SVG."""
    width = 800
    height = 500
    margin = 50

    e_vals = sorted(sweep.keys())
    e_min = 0.0
    e_max = 1.0

    v_min = 0.0
    v_max = 1.0

    lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">',
        '  <style>',
        '    .axis { stroke: black; stroke-width: 1; }',
        '    .grid { stroke: #e0e0e0; stroke-width: 1; stroke-dasharray: 4; }',
        '    .label { font-family: sans-serif; font-size: 14px; fill: black; text-anchor: middle; }',
        '    .legend { font-family: sans-serif; font-size: 14px; }',
        '  </style>',
        f'  <text x="{width/2}" y="{margin - 20}" class="label" style="font-size: 16px; font-weight: bold;">Task B2: Final Velocities vs Restitution Coefficient (e)</text>'
    ]

    # Axes
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>')
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" class="axis"/>')

    # Grid & Labels
    x_ticks = 10
    for i in range(x_ticks + 1):
        x = e_min + (e_max - e_min) * i / x_ticks
        svg_x, svg_y = _map_to_svg(x, v_min, e_min, e_max, v_min, v_max, width, height, margin)
        lines.append(f'  <line x1="{svg_x}" y1="{height-margin}" x2="{svg_x}" y2="{margin}" class="grid"/>')
        lines.append(f'  <text x="{svg_x}" y="{height-margin+20}" class="label">{x:.1f}</text>')

    y_ticks = 5
    for i in range(y_ticks + 1):
        y = v_min + (v_max - v_min) * i / y_ticks
        svg_x, svg_y = _map_to_svg(e_min, y, e_min, e_max, v_min, v_max, width, height, margin)
        lines.append(f'  <line x1="{margin}" y1="{svg_y}" x2="{width-margin}" y2="{svg_y}" class="grid"/>')
        lines.append(f'  <text x="{margin-10}" y="{svg_y+5}" class="label" style="text-anchor: end;">{y:.2f}</text>')

    lines.append(f'  <text x="{width/2}" y="{height-margin+40}" class="label">Restitution Coefficient e</text>')
    lines.append(f'  <text x="{margin-40}" y="{height/2}" transform="rotate(-90 {margin-40} {height/2})" class="label">Final Velocity</text>')

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    labels = ['v1', 'v2', 'v3', 'v4']

    for i in range(4):
        path_data = []
        for e in e_vals:
            v = sweep[e]["velocities"][i]
            svg_x, svg_y = _map_to_svg(e, v, e_min, e_max, v_min, v_max, width, height, margin)
            cmd = "M" if not path_data else "L"
            path_data.append(f"{cmd} {svg_x:.2f},{svg_y:.2f}")

        lines.append(f'  <path d="{" ".join(path_data)}" fill="none" stroke="{colors[i]}" stroke-width="2" />')

        # Legend
        leg_y = margin + 20 * i
        lines.append(f'  <line x1="{width-margin-80}" y1="{leg_y}" x2="{width-margin-50}" y2="{leg_y}" stroke="{colors[i]}" stroke-width="2"/>')
        lines.append(f'  <text x="{width-margin-40}" y="{leg_y+5}" class="legend">{labels[i]}</text>')

    lines.append('</svg>')
    return "\n".join(lines)

def render_task_b1_svg(sweep: dict[float, dict[str, object]]) -> str:
    """Render Task B1 number of collisions vs e as SVG."""
    width = 800
    height = 500
    margin = 50

    e_vals = sorted(sweep.keys())
    e_min = 0.0
    e_max = 1.0

    c_min = 0
    c_max = max(sweep[e]["collisions"] for e in e_vals)
    c_max = max(c_max, 10)

    lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">',
        '  <style>',
        '    .axis { stroke: black; stroke-width: 1; }',
        '    .grid { stroke: #e0e0e0; stroke-width: 1; stroke-dasharray: 4; }',
        '    .label { font-family: sans-serif; font-size: 14px; fill: black; text-anchor: middle; }',
        '  </style>',
        f'  <text x="{width/2}" y="{margin - 20}" class="label" style="font-size: 16px; font-weight: bold;">Task B1: Number of Collisions vs Restitution Coefficient (e)</text>'
    ]

    # Axes
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>')
    lines.append(f'  <line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" class="axis"/>')

    # Grid & Labels
    x_ticks = 10
    for i in range(x_ticks + 1):
        x = e_min + (e_max - e_min) * i / x_ticks
        svg_x, svg_y = _map_to_svg(x, c_min, e_min, e_max, c_min, c_max, width, height, margin)
        lines.append(f'  <line x1="{svg_x}" y1="{height-margin}" x2="{svg_x}" y2="{margin}" class="grid"/>')
        lines.append(f'  <text x="{svg_x}" y="{height-margin+20}" class="label">{x:.1f}</text>')

    y_ticks = 5
    for i in range(y_ticks + 1):
        y = c_min + (c_max - c_min) * i / y_ticks
        svg_x, svg_y = _map_to_svg(e_min, y, e_min, e_max, c_min, c_max, width, height, margin)
        lines.append(f'  <line x1="{margin}" y1="{svg_y}" x2="{width-margin}" y2="{svg_y}" class="grid"/>')
        lines.append(f'  <text x="{margin-10}" y="{svg_y+5}" class="label" style="text-anchor: end;">{int(y)}</text>')

    lines.append(f'  <text x="{width/2}" y="{height-margin+40}" class="label">Restitution Coefficient e</text>')
    lines.append(f'  <text x="{margin-40}" y="{height/2}" transform="rotate(-90 {margin-40} {height/2})" class="label">Number of Collisions</text>')

    path_data = []
    for e in e_vals:
        c = sweep[e]["collisions"]
        svg_x, svg_y = _map_to_svg(e, c, e_min, e_max, c_min, c_max, width, height, margin)
        cmd = "M" if not path_data else "L"
        path_data.append(f"{cmd} {svg_x:.2f},{svg_y:.2f}")

    lines.append(f'  <path d="{" ".join(path_data)}" fill="none" stroke="#1f77b4" stroke-width="2" />')

    lines.append('</svg>')
    return "\n".join(lines)
