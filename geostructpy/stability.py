"""Cantilever retaining wall stability analysis."""
import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(h1, h2, t_stem, t_base, b_base, b_heel, gamma_s, phi, mu, q_bearing, gamma_c, q):
    gs = gamma_s
    gc = gamma_c
    totalHeight = h1 + h2

    # Vertical loads (restoring)
    P1 = gc * t_stem * (totalHeight - t_base)
    P2 = gc * t_base * b_base
    P3 = gs * (totalHeight - t_base) * (b_base - t_stem)

    m1 = P1 * (t_stem / 2)
    m2 = P2 * (b_base / 2)
    m3 = P3 * (b_base - b_heel / 2)

    Wt = P1 + P2 + P3
    Mr = m1 + m2 + m3

    # Surcharge on heel
    P_sur = q * b_heel
    m_sur = P_sur * (b_base - b_heel / 2)
    Wt += P_sur
    Mr += m_sur

    # Lateral loads
    Ka = (1 - math.sin(phi * DEG)) / (1 + math.sin(phi * DEG))
    maxHP = Ka * gs * totalHeight
    Pa_soil = 0.5 * Ka * gs * totalHeight * totalHeight
    Pa_sur = q * Ka * totalHeight
    Pa_total = Pa_soil + Pa_sur

    Mo_soil = Pa_soil * (totalHeight / 3)
    Mo_sur = Pa_sur * (totalHeight / 2)
    Mo = Mo_soil + Mo_sur

    # Eccentricity & contact pressure
    netMoment = Mr - Mo
    ecc = netMoment / Wt
    e_abs = abs(b_base / 2 - ecc)
    qAvg = Wt / b_base

    if e_abs >= b_base / 2:
        contactCase = 'Unstable \u2013 resultant outside base'
        qmax = float('inf')
        qmin = 0
    elif e_abs <= b_base / 6:
        if e_abs < 0.0001:
            contactCase = 'Full Contact: Uniform'
            qmax = qmin = qAvg
        elif abs(e_abs - b_base / 6) < 0.0001:
            contactCase = 'Full Contact: Triangular'
            qmax = 2 * qAvg
            qmin = 0
        else:
            contactCase = 'Full Contact: Trapezoidal'
            qmax = qAvg * (1 + 6 * e_abs / b_base)
            qmin = qAvg * (1 - 6 * e_abs / b_base)
    else:
        contactCase = 'Partial Contact (tension side lifts)'
        qmin = 0
        x_bar = b_base / 2 - e_abs
        qmax = 2 * Wt / (3 * x_bar)

    # Factors of safety
    FS_slide = (mu * Wt) / Pa_total
    FS_over = Mr / Mo

    # Build report
    r = '<h4>Rankine Active Earth Pressure Coefficient</h4>'
    r += f'\\[ K_a = \\frac{{1 - \\sin\\phi}}{{1 + \\sin\\phi}} = {_f(Ka, 4)} \\]'

    r += '<h4>Lateral Loads</h4>'
    r += f'\\[ \\sigma_{{a,max}} = K_a \\gamma_s H = {_f(maxHP)} \\text{{ kPa}} \\]'
    r += f'\\[ P_{{a,soil}} = \\tfrac{{1}}{{2}} K_a \\gamma_s H^2 = {_f(Pa_soil)} \\text{{ kN/m}} \\]'
    if q > 0:
        r += f'\\[ P_{{a,surcharge}} = q \\cdot K_a \\cdot H = {_f(Pa_sur)} \\text{{ kN/m}} \\]'
    r += f'\\[ P_{{a,total}} = {_f(Pa_total)} \\text{{ kN/m}} \\]'

    r += '<h4>Vertical Loads &amp; Restoring Moment</h4>'
    r += '<table class="data-table"><thead><tr><th>Component</th><th>W (kN/m)</th><th>Arm (m)</th><th>M<sub>R</sub> (kN\u00b7m/m)</th></tr></thead><tbody>'
    parts = [
        {'name': 'P1 \u2013 Stem', 'W': P1, 'x': t_stem / 2, 'M': m1},
        {'name': 'P2 \u2013 Base slab', 'W': P2, 'x': b_base / 2, 'M': m2},
        {'name': 'P3 \u2013 Backfill', 'W': P3, 'x': b_base - b_heel / 2, 'M': m3},
    ]
    if q > 0:
        parts.append({'name': 'Surcharge', 'W': P_sur, 'x': b_base - b_heel / 2, 'M': m_sur})
    for p in parts:
        r += f'<tr><td>{p["name"]}</td><td>{_f(p["W"])}</td><td>{_f(p["x"])}</td><td>{_f(p["M"])}</td></tr>'
    r += f'<tr style="font-weight:bold"><td>Total</td><td>{_f(Wt)}</td><td></td><td>{_f(Mr)}</td></tr>'
    r += '</tbody></table>'

    r += '<h4>Overturning Moment about Toe</h4>'
    r += f'\\[ M_o = P_{{a,soil}} \\times \\frac{{H}}{{3}}'
    if q > 0:
        r += f' + P_{{a,sur}} \\times \\frac{{H}}{{2}}'
    r += f' = {_f(Mo)} \\text{{ kN\u00b7m/m}} \\]'

    r += '<h4>Sliding Check</h4>'
    r += f'\\[ FS_{{sliding}} = \\frac{{\\mu \\cdot W}}{{P_a}} = \\frac{{{_f(mu * Wt)}}}{{{_f(Pa_total)}}} = {_f(FS_slide)} \\]'

    r += '<h4>Overturning Check</h4>'
    r += f'\\[ FS_{{overturning}} = \\frac{{M_R}}{{M_o}} = \\frac{{{_f(Mr)}}}{{{_f(Mo)}}} = {_f(FS_over)} \\]'

    r += '<h4>Eccentricity &amp; Base Pressure</h4>'
    r += f'\\[ \\bar{{x}} = \\frac{{M_R - M_o}}{{W}} = {_f(ecc)} \\text{{ m}} \\]'
    r += f'\\[ e = \\frac{{B}}{{2}} - \\bar{{x}} = {_f(e_abs)} \\text{{ m}} \\quad (B/6 = {_f(b_base / 6)}) \\]'
    r += f'<p><strong>Contact case:</strong> {contactCase}</p>'

    qmax_display = _f(qmax) if math.isfinite(qmax) else '\u221e'
    r += f'\\[ q_{{max}} = {qmax_display} \\text{{ kPa}}, \\quad q_{{min}} = {_f(qmin)} \\text{{ kPa}} \\]'

    bearingOK = qmax <= q_bearing
    r += f'<p><strong>Bearing check:</strong> q<sub>max</sub> = {qmax_display} kPa '
    r += '\u2264' if bearingOK else '>'
    r += f' q<sub>all</sub> = {_f(q_bearing)} kPa \u2192 '
    r += f'<span style="color:{"#27ae60" if bearingOK else "#e74c3c"};font-weight:bold">{"PASS" if bearingOK else "FAIL"}</span></p>'

    # Summary table
    summary = [
        {
            'name': 'Sliding',
            'driving': _f(Pa_total) + ' kN/m',
            'resisting': _f(mu * Wt) + ' kN/m',
            'fs': _f(FS_slide),
            'req': '\u2265 1.5',
            'pass': FS_slide >= 1.5,
        },
        {
            'name': 'Overturning',
            'driving': _f(Mo) + ' kN\u00b7m/m',
            'resisting': _f(Mr) + ' kN\u00b7m/m',
            'fs': _f(FS_over),
            'req': '\u2265 2.0',
            'pass': FS_over >= 2.0,
        },
        {
            'name': 'Eccentricity',
            'driving': 'e = ' + _f(e_abs) + ' m',
            'resisting': 'B/6 = ' + _f(b_base / 6) + ' m',
            'fs': _f(999 if e_abs < 0.001 else (b_base / 6) / e_abs),
            'req': 'e \u2264 B/6',
            'pass': e_abs <= b_base / 6 + 0.001,
        },
        {
            'name': 'Bearing Pressure',
            'driving': qmax_display + ' kPa',
            'resisting': _f(q_bearing) + ' kPa',
            'fs': _f(q_bearing / (qmax if qmax else 1)),
            'req': 'q_max \u2264 q_all',
            'pass': bearingOK,
        },
    ]
    allPass = all(s['pass'] for s in summary)

    # Wall plot data
    y_top = h1
    y_gl = 0
    y_iface = -(h2 - t_base)
    y_bot = -h2
    span = totalHeight

    wallX = [0, t_stem, t_stem, b_base, b_base, 0, 0, 0]
    wallY = [y_top, y_top, y_iface, y_iface, y_bot, y_bot, y_gl, y_top]

    ifaceX = [0, t_stem]
    ifaceY = [y_iface, y_iface]

    margin_val = 0.12 * b_base
    dark = '#006400'

    wall_traces = [
        {"x": wallX, "y": wallY, "mode": "lines", "line": {"color": "#333", "width": 2.5}, "showlegend": False, "hoverinfo": "skip"},
        {"x": ifaceX, "y": ifaceY, "mode": "lines", "line": {"color": "#333", "width": 2}, "showlegend": False, "hoverinfo": "skip"},
    ]
    # Dashed ground-level & top lines
    for yv in [y_top, y_gl]:
        wall_traces.append({
            "x": [-margin_val, b_base + margin_val], "y": [yv, yv], "mode": "lines",
            "line": {"color": "#888", "width": 1, "dash": "dash"},
            "showlegend": False, "hoverinfo": "skip"
        })
    # Backfill
    wall_traces.append({
        "x": [t_stem, b_base, b_base, t_stem], "y": [y_top, y_top, y_iface, y_iface],
        "fill": "toself", "fillcolor": "rgba(194,178,128,0.25)",
        "line": {"color": "rgba(194,178,128,0.5)", "width": 1},
        "showlegend": False, "hoverinfo": "skip"
    })
    # Concrete fills
    wall_traces.append({
        "x": [0, t_stem, t_stem, 0], "y": [y_top, y_top, y_iface, y_iface],
        "fill": "toself", "fillcolor": "rgba(180,180,180,0.3)", "line": {"width": 0},
        "showlegend": False, "hoverinfo": "skip"
    })
    wall_traces.append({
        "x": [0, b_base, b_base, 0], "y": [y_iface, y_iface, y_bot, y_bot],
        "fill": "toself", "fillcolor": "rgba(180,180,180,0.3)", "line": {"width": 0},
        "showlegend": False, "hoverinfo": "skip"
    })

    # Pressure triangle
    triBaseW = 0.35 * span
    triX0 = b_base + margin_val * 1.5
    wall_traces.append({
        "x": [triX0, triX0, triX0 + triBaseW], "y": [y_top, y_bot, y_bot],
        "mode": "lines", "fill": "toself", "fillcolor": "rgba(0,100,0,0.08)",
        "line": {"color": dark, "width": 1.5}, "showlegend": False, "hoverinfo": "skip"
    })
    for frac in [0.2, 0.4, 0.6, 0.8, 1.0]:
        yi = y_top - frac * span
        xi = triBaseW * frac
        wall_traces.append({
            "x": [triX0 + xi, triX0], "y": [yi, yi], "mode": "lines",
            "line": {"color": dark, "width": 2.5 if frac == 1.0 else 1},
            "showlegend": False, "hoverinfo": "skip"
        })

    # Annotations
    ann = []
    ann.append({"x": -margin_val * 0.6, "y": (y_top + y_gl) / 2, "text": f"h\u2081 = {h1:.2f} m", "showarrow": False, "font": {"size": 11, "color": "#333"}, "xanchor": "right"})
    ann.append({"x": -margin_val * 0.6, "y": (y_gl + y_bot) / 2, "text": f"h\u2082 = {h2:.2f} m", "showarrow": False, "font": {"size": 11, "color": "#333"}, "xanchor": "right"})
    ann.append({"x": t_stem / 2, "y": y_top + 0.06 * span, "text": f"t<sub>stem</sub> = {t_stem:.2f} m", "showarrow": False, "font": {"size": 10, "color": "#333"}})
    ann.append({"x": b_base / 2, "y": y_bot - 0.08 * span, "text": f"b<sub>base</sub> = {b_base:.2f} m", "showarrow": False, "font": {"size": 11, "color": "#333"}})
    ann.append({"x": b_base + margin_val * 0.5, "y": (y_iface + y_bot) / 2, "text": f"t<sub>base</sub> = {t_base:.2f} m", "showarrow": False, "font": {"size": 10, "color": "#333"}, "xanchor": "left"})

    arrowLen = 0.22 * span
    loads = [
        {"label": "P1", "val": P1, "x": t_stem / 2, "y": (y_top + y_bot) / 2},
        {"label": "P2", "val": P2, "x": b_base / 2, "y": (y_iface + y_bot) / 2},
        {"label": "P3", "val": P3, "x": (t_stem + b_base) / 2, "y": (y_top + y_iface) / 2},
    ]
    for ld in loads:
        ann.append({
            "x": ld["x"], "y": ld["y"], "ax": ld["x"], "ay": ld["y"] + arrowLen,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 2, "arrowsize": 1.2, "arrowwidth": 2.5, "arrowcolor": dark
        })
        ann.append({
            "x": ld["x"], "y": ld["y"] + arrowLen + 0.03 * span,
            "text": f"<b>{ld['label']} = {ld['val']:.2f}</b>", "showarrow": False,
            "font": {"size": 10, "color": dark}
        })

    # Active force arrow
    yH3 = y_bot + span / 3
    xH3 = triBaseW * (1 - 1 / 3)
    ann.append({
        "x": triX0, "y": yH3, "ax": triX0 + xH3, "ay": yH3,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.5, "arrowwidth": 3, "arrowcolor": dark
    })
    ann.append({
        "x": triX0 + xH3 + 0.02 * span, "y": yH3 + 0.03 * span,
        "text": f"<b>Pa = {Pa_soil:.2f}</b>", "showarrow": False,
        "font": {"size": 10, "color": dark}, "xanchor": "left"
    })
    ann.append({
        "x": triX0 + triBaseW / 2, "y": y_bot - 0.06 * span,
        "text": f"K<sub>a</sub>\u03B3<sub>s</sub>H = {maxHP:.2f} kPa", "showarrow": False,
        "font": {"size": 10, "color": dark}
    })
    ann.append({
        "x": triX0 + triBaseW + 0.08 * span, "y": (y_bot + yH3) / 2,
        "text": f"H/3 = {span / 3:.2f} m", "showarrow": False,
        "font": {"size": 10, "color": "#333"}, "xanchor": "left"
    })

    wall_layout = {
        "xaxis": {"visible": False, "scaleanchor": "y"},
        "yaxis": {"visible": False},
        "margin": {"l": 10, "r": 10, "t": 30, "b": 30},
        "height": 420,
        "plot_bgcolor": "white", "paper_bgcolor": "white",
        "annotations": ann,
        "title": {"text": "Wall Cross-Section & Lateral Pressure", "font": {"size": 14}},
    }

    # Pressure distribution plot
    pressure_traces = []
    pressure_traces.append({"x": [0, b_base], "y": [0, 0], "mode": "lines", "line": {"color": "#333", "width": 2}, "showlegend": False, "hoverinfo": "skip"})

    if qmin >= 0 and math.isfinite(qmax):
        pressure_traces.append({
            "x": [0, b_base, b_base, 0], "y": [0, 0, -qmax, -qmin],
            "fill": "toself", "fillcolor": "rgba(41,128,185,0.2)",
            "line": {"color": "#2980b9", "width": 2}, "name": "Base pressure", "showlegend": False
        })
        pressure_traces.append({
            "x": [0], "y": [-qmin], "mode": "markers+text",
            "marker": {"size": 6, "color": "#2980b9"},
            "text": [f"q<sub>min</sub> = {qmin:.1f} kPa"],
            "textposition": "bottom left", "showlegend": False
        })
        pressure_traces.append({
            "x": [b_base], "y": [-qmax], "mode": "markers+text",
            "marker": {"size": 6, "color": "#e74c3c"},
            "text": [f"q<sub>max</sub> = {qmax:.1f} kPa"],
            "textposition": "bottom right", "showlegend": False
        })

    if math.isfinite(q_bearing):
        pressure_traces.append({
            "x": [-0.05 * b_base, b_base * 1.05], "y": [-q_bearing, -q_bearing],
            "mode": "lines", "line": {"color": "#e74c3c", "width": 1.5, "dash": "dash"},
            "name": "q_all", "showlegend": False
        })

    pressure_ann = [
        {"x": b_base * 1.06, "y": -q_bearing, "text": f"q<sub>all</sub> = {q_bearing:.0f} kPa", "showarrow": False, "font": {"size": 10, "color": "#e74c3c"}, "xanchor": "left"},
        {"x": b_base / 2, "y": min(-qmax * 1.1 if math.isfinite(qmax) else -q_bearing * 1.1, -q_bearing * 1.1) - 5, "text": f"<i>{contactCase}</i>", "showarrow": False, "font": {"size": 10, "color": "#555"}},
    ]

    pressure_layout = {
        "xaxis": {"title": "Base width (m)", "zeroline": False},
        "yaxis": {"title": "Pressure (kPa, downward negative)", "zeroline": True},
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
        "height": 420,
        "plot_bgcolor": "white", "paper_bgcolor": "white",
        "annotations": pressure_ann,
        "title": {"text": "Base Pressure Distribution", "font": {"size": 14}},
    }

    return {
        "report": r,
        "summary": summary,
        "allPass": allPass,
        "wall_traces": wall_traces,
        "wall_layout": wall_layout,
        "pressure_traces": pressure_traces,
        "pressure_layout": pressure_layout,
    }
