"""Cantilever retaining wall stability analysis."""
import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(h1, h2, t_stem, t_base, b_base, b_heel, gamma_s, phi, mu, q_bearing, gamma_c, q,
              y_front=0.0, include_passive=False, b_toe=0.0):
    """Cantilever retaining-wall stability analysis.

    Geometry convention (per Das & Sivakugan 2019, 9th SI, §17.2 Proportioning
    Retaining Walls, p. 697; Fig. 17.4):

        x = 0          : front (toe-side) edge of base slab
        x = b_toe      : front face of stem
        x = b_toe+t_stem: back face of stem
        x = b_base     : back (heel-side) edge of base slab

    where b_base = b_toe + t_stem + b_heel.

    The b_toe parameter is optional. When b_toe > 0 it is taken as the
    explicit toe projection and b_base is auto-recomputed as
    b_toe + t_stem + b_heel. When b_toe == 0 (legacy default), the calculator
    derives b_toe = max(b_base - t_stem - b_heel, 0) so the existing form
    inputs continue to work without modification.

    Refs: Das & Sivakugan (2019) §17.2 (proportioning, p. 697), §17.4
    (stability checks, p. 699), §17.5-17.7 (overturning, sliding, bearing,
    pp. 701-706); Bowles (1996) §12.4 (proportioning gravity walls);
    Poulos & Davis (1980) Ch. 2 (effective-stress concepts behind γ').
    """
    gs = gamma_s
    gc = gamma_c
    totalHeight = h1 + h2

    # Resolve b_toe vs. b_base. If user supplies b_toe explicitly (> 0), it
    # overrides b_base. Otherwise we derive b_toe from the existing inputs
    # to preserve regression on the legacy default geometry.
    if b_toe and b_toe > 0:
        b_base = b_toe + t_stem + b_heel
    else:
        b_toe = max(b_base - t_stem - b_heel, 0.0)

    # Stem position (x of front face)
    x_stem_front = b_toe
    x_stem_back = b_toe + t_stem

    # Vertical loads (restoring), moments taken about the toe at x = 0
    # P1 = stem self-weight; centroid at x = b_toe + t_stem/2 per the
    #      geometry convention above (Das §17.4 p. 699).
    P1 = gc * t_stem * (totalHeight - t_base)
    # P2 = base slab self-weight; centroid at x = b_base/2.
    P2 = gc * t_base * b_base
    # P3 = backfill weight ABOVE THE HEEL only (width = b_heel, not the entire
    #      base minus stem). When b_toe = 0 this reduces to the legacy
    #      formula (b_base - t_stem) so existing baselines are preserved.
    P3 = gs * (totalHeight - t_base) * b_heel

    m1 = P1 * (x_stem_front + t_stem / 2)
    m2 = P2 * (b_base / 2)
    m3 = P3 * (b_base - b_heel / 2)

    Wt = P1 + P2 + P3
    Mr = m1 + m2 + m3

    # Surcharge on heel (vertical bearing component)
    P_sur = q * b_heel
    m_sur = P_sur * (b_base - b_heel / 2)
    Wt += P_sur
    Mr += m_sur

    # Toe-side soil weight on top of the toe slab. Front soil exists from
    # the base top (y = -h2 + t_base) up to the soil surface (y = -h2 + y_front).
    # Only the portion ABOVE the base contributes a vertical load on the toe.
    # Ref: Das §17.4 p. 699 - the soil above the toe is conventionally
    # added to the resisting moment when the front cover is reliably present.
    if y_front > t_base and b_toe > 0:
        h_toe_soil = y_front - t_base
        P_toe_soil = gs * h_toe_soil * b_toe
        m_toe_soil = P_toe_soil * (b_toe / 2.0)
        Wt += P_toe_soil
        Mr += m_toe_soil
    else:
        h_toe_soil = 0.0
        P_toe_soil = 0.0
        m_toe_soil = 0.0

    # Lateral loads (active, back side)
    Ka = (1 - math.sin(phi * DEG)) / (1 + math.sin(phi * DEG))
    maxHP = Ka * gs * totalHeight
    Pa_soil = 0.5 * Ka * gs * totalHeight * totalHeight
    Pa_sur = q * Ka * totalHeight
    Pa_total = Pa_soil + Pa_sur

    Mo_soil = Pa_soil * (totalHeight / 3)
    Mo_sur = Pa_sur * (totalHeight / 2)
    Mo = Mo_soil + Mo_sur

    # Passive resistance from front (toe-side) soil per Rankine
    # Ref: Das & Sivakugan (2019, 9th SI) §16.11 Eq. 16.47, p. 676; §17.4 Stability checks, p. 699.
    Kp = (1 + math.sin(phi * DEG)) / (1 - math.sin(phi * DEG))
    if y_front > 0:
        Pp_soil = 0.5 * Kp * gs * y_front * y_front   # kN/m
        Mp_resist = Pp_soil * (y_front / 3.0)         # moment about base bottom
        maxPP = Kp * gs * y_front                     # peak passive pressure at base
    else:
        Pp_soil = 0.0
        Mp_resist = 0.0
        maxPP = 0.0

    # Credit passive resistance in the overturning/eccentricity checks only when requested.
    # Default behavior (include_passive=False) leaves Mr and Mo untouched, preserving the
    # regression against the pre-change numeric output.
    if include_passive and y_front > 0:
        Mr_total = Mr + Mp_resist
    else:
        Mr_total = Mr

    # Eccentricity & contact pressure
    netMoment = Mr_total - Mo
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
    if include_passive and y_front > 0:
        FS_slide = (mu * Wt + Pp_soil) / Pa_total
        FS_over = Mr_total / Mo
    else:
        FS_slide = (mu * Wt) / Pa_total
        FS_over = Mr / Mo

    # Build report
    r = '<h4>Wall Geometry (with Explicit Toe)</h4>'
    r += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        'Ref: Das &amp; Sivakugan (2019, 9th SI) <strong>&sect;17.2 Proportioning Retaining '
        'Walls, p.&nbsp;697</strong>, Fig.&nbsp;17.4. The toe is the projection of the base '
        'slab in front of the stem; the heel is the projection behind. Typical toe width is '
        '~1/3 to 1/4 of the base width for cantilever walls. &sect;17.4 stability checks, '
        '<strong>p.&nbsp;699</strong>; Bowles (1996) &sect;12.4 proportioning gravity walls.</p>'
    )
    r += '<table class="data-table" style="max-width:560px;margin:0 0 8px;">'
    r += '<thead><tr><th>Component</th><th>Width (m)</th><th>x-range (m)</th></tr></thead><tbody>'
    r += f'<tr><td>Toe slab</td><td>{_f(b_toe)}</td><td>0.00 &ndash; {_f(x_stem_front)}</td></tr>'
    r += f'<tr><td>Stem</td><td>{_f(t_stem)}</td><td>{_f(x_stem_front)} &ndash; {_f(x_stem_back)}</td></tr>'
    r += f'<tr><td>Heel slab</td><td>{_f(b_heel)}</td><td>{_f(x_stem_back)} &ndash; {_f(b_base)}</td></tr>'
    r += f'<tr style="font-weight:bold"><td>Total base, b</td><td>{_f(b_base)}</td><td></td></tr>'
    r += '</tbody></table>'

    r += '<h4>Rankine Active Earth Pressure Coefficient</h4>'
    r += f'\\[ K_a = \\frac{{1 - \\sin\\phi}}{{1 + \\sin\\phi}} = {_f(Ka, 4)} \\]'

    r += '<h4>Lateral Loads</h4>'
    r += f'\\[ \\sigma_{{a,max}} = K_a \\gamma_s H = {_f(maxHP)} \\text{{ kPa}} \\]'
    r += f'\\[ P_{{a,soil}} = \\tfrac{{1}}{{2}} K_a \\gamma_s H^2 = {_f(Pa_soil)} \\text{{ kN/m}} \\]'
    if q > 0:
        r += f'\\[ P_{{a,surcharge}} = q \\cdot K_a \\cdot H = {_f(Pa_sur)} \\text{{ kN/m}} \\]'
    r += f'\\[ P_{{a,total}} = {_f(Pa_total)} \\text{{ kN/m}} \\]'

    # Passive resistance (Rankine) — front / toe-side soil
    # Ref: Das & Sivakugan (2019, 9th SI) §16.11 Rankine passive earth pressure, Eq. 16.47, p. 676.
    #      §17.4 Stability of retaining walls, p. 699 — discussion of crediting passive force.
    r += '<h4>Passive Resistance (Front Soil)</h4>'
    r += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        'Ref: Das &amp; Sivakugan (2019, 9th SI) &sect;16.11 Rankine passive pressure, '
        '<strong>p.&nbsp;676</strong>; &sect;17.4 &mdash; stability of retaining walls, '
        '<strong>p.&nbsp;699</strong>.</p>'
    )
    r += f'\\[ K_p = \\frac{{1 + \\sin\\phi}}{{1 - \\sin\\phi}} = {_f(Kp, 4)} \\]'
    if y_front > 0:
        r += f'\\[ \\sigma_{{p,max}} = K_p \\gamma_s y = {_f(maxPP)} \\text{{ kPa}} \\]'
        r += f'\\[ P_p = \\tfrac{{1}}{{2}} K_p \\gamma_s y^2 = {_f(Pp_soil)} \\text{{ kN/m}} \\quad (\\text{{at }} y/3 = {_f(y_front/3)} \\text{{ m from base}}) \\]'
        if include_passive:
            r += (
                f'<p><strong>Credited</strong> in sliding and overturning checks '
                f'(M<sub>p</sub> = {_f(Mp_resist)} kN&middot;m/m added to restoring moment).</p>'
            )
        else:
            r += (
                '<p><em>Computed but NOT credited</em> in sliding / overturning '
                '(checkbox unticked, per ACI SP-17 Ch.&nbsp;2 conservative guidance).</p>'
            )
    else:
        r += '<p><em>Front soil depth y = 0 &mdash; no passive resistance available.</em></p>'

    r += '<h4>Vertical Loads &amp; Restoring Moment</h4>'
    r += '<table class="data-table"><thead><tr><th>Component</th><th>W (kN/m)</th><th>Arm (m)</th><th>M<sub>R</sub> (kN\u00b7m/m)</th></tr></thead><tbody>'
    parts = [
        {'name': 'P1 \u2013 Stem', 'W': P1, 'x': t_stem / 2, 'M': m1},
        {'name': 'P2 \u2013 Base slab', 'W': P2, 'x': b_base / 2, 'M': m2},
        {'name': 'P3 \u2013 Backfill', 'W': P3, 'x': b_base - b_heel / 2, 'M': m3},
    ]
    if q > 0:
        parts.append({'name': 'Surcharge', 'W': P_sur, 'x': b_base - b_heel / 2, 'M': m_sur})
    if P_toe_soil > 0:
        parts.append({'name': 'P4 \u2013 Toe-side soil', 'W': P_toe_soil, 'x': b_toe / 2, 'M': m_toe_soil})
    for p in parts:
        r += f'<tr><td>{p["name"]}</td><td>{_f(p["W"])}</td><td>{_f(p["x"])}</td><td>{_f(p["M"])}</td></tr>'
    r += f'<tr style="font-weight:bold"><td>Total</td><td>{_f(Wt)}</td><td></td><td>{_f(Mr)}</td></tr>'
    r += '</tbody></table>'
    if P_toe_soil > 0:
        r += (
            '<p style="font-size:0.82em;color:#6c757d;margin:0;">'
            f'P4 = &gamma;<sub>s</sub> &times; (y &minus; t<sub>base</sub>) &times; b<sub>toe</sub> = '
            f'{_f(gs)} &times; ({_f(y_front)} &minus; {_f(t_base)}) &times; {_f(b_toe)} = '
            f'{_f(P_toe_soil)} kN/m, applied at the toe-slab centroid (x = b<sub>toe</sub>/2). '
            'Ref: Das &amp; Sivakugan &sect;17.4 (p.&nbsp;699) &mdash; soil cover above the toe '
            'is added to the resisting weight when the front cover is permanent.</p>'
        )

    r += '<h4>Overturning Moment about Toe</h4>'
    r += f'\\[ M_o = P_{{a,soil}} \\times \\frac{{H}}{{3}}'
    if q > 0:
        r += f' + P_{{a,sur}} \\times \\frac{{H}}{{2}}'
    r += f' = {_f(Mo)} \\text{{ kN\u00b7m/m}} \\]'

    r += '<h4>Sliding Check</h4>'
    if include_passive and y_front > 0:
        r += (
            f'\\[ FS_{{sliding}} = \\frac{{\\mu \\cdot W + P_p}}{{P_a}} = '
            f'\\frac{{{_f(mu * Wt)} + {_f(Pp_soil)}}}{{{_f(Pa_total)}}} = {_f(FS_slide)} \\]'
        )
    else:
        r += (
            f'\\[ FS_{{sliding}} = \\frac{{\\mu \\cdot W}}{{P_a}} = '
            f'\\frac{{{_f(mu * Wt)}}}{{{_f(Pa_total)}}} = {_f(FS_slide)} \\]'
        )

    r += '<h4>Overturning Check</h4>'
    if include_passive and y_front > 0:
        r += (
            f'\\[ FS_{{overturning}} = \\frac{{M_R + M_p}}{{M_o}} = '
            f'\\frac{{{_f(Mr)} + {_f(Mp_resist)}}}{{{_f(Mo)}}} = {_f(FS_over)} \\]'
        )
    else:
        r += (
            f'\\[ FS_{{overturning}} = \\frac{{M_R}}{{M_o}} = '
            f'\\frac{{{_f(Mr)}}}{{{_f(Mo)}}} = {_f(FS_over)} \\]'
        )

    r += '<h4>Eccentricity &amp; Base Pressure</h4>'
    r += f'\\[ \\bar{{x}} = \\frac{{M_R - M_o}}{{W}} = {_f(ecc)} \\text{{ m}} \\]'
    r += f'\\[ e = \\frac{{B}}{{2}} - \\bar{{x}} = {_f(e_abs)} \\text{{ m}} \\quad (B/6 = {_f(b_base / 6)}) \\]'
    r += f'<p><strong>Contact case:</strong> {contactCase}</p>'

    qmax_display = _f(qmax) if math.isfinite(qmax) else '\u221e'
    r += f'\\[ q_{{max}} = {qmax_display} \\text{{ kPa}}, \\quad q_{{min}} = {_f(qmin)} \\text{{ kPa}} \\]'

    do_bearing_check = q_bearing > 0
    if do_bearing_check:
        bearingOK = qmax <= q_bearing
        r += f'<p><strong>Bearing check:</strong> q<sub>max</sub> = {qmax_display} kPa '
        r += '\u2264' if bearingOK else '>'
        r += f' q<sub>all</sub> = {_f(q_bearing)} kPa \u2192 '
        r += f'<span style="color:{"#27ae60" if bearingOK else "#e74c3c"};font-weight:bold">{"PASS" if bearingOK else "FAIL"}</span></p>'
    else:
        bearingOK = True
        r += '<p><strong>Bearing check:</strong> <em>skipped &mdash; q<sub>all</sub> not provided</em></p>'

    # Summary table
    _slide_resisting = (
        f'{_f(mu * Wt + Pp_soil)} kN/m (incl. P<sub>p</sub>)'
        if include_passive and y_front > 0
        else f'{_f(mu * Wt)} kN/m'
    )
    _over_resisting = (
        f'{_f(Mr + Mp_resist)} kN&middot;m/m (incl. M<sub>p</sub>)'
        if include_passive and y_front > 0
        else f'{_f(Mr)} kN&middot;m/m'
    )
    summary = [
        {
            'name': 'Sliding',
            'driving': _f(Pa_total) + ' kN/m',
            'resisting': _slide_resisting,
            'fs': _f(FS_slide),
            'req': '\u2265 1.5',
            'pass': FS_slide >= 1.5,
        },
        {
            'name': 'Overturning',
            'driving': _f(Mo) + ' kN\u00b7m/m',
            'resisting': _over_resisting,
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
    ]
    if do_bearing_check:
        summary.append({
            'name': 'Bearing Pressure',
            'driving': qmax_display + ' kPa',
            'resisting': _f(q_bearing) + ' kPa',
            'fs': _f(q_bearing / (qmax if qmax else 1)),
            'req': 'q_max \u2264 q_all',
            'pass': bearingOK,
        })
    allPass = all(s['pass'] for s in summary)

    # Wall plot data
    y_top = h1
    y_gl = 0
    y_iface = -(h2 - t_base)
    y_bot = -h2
    span = totalHeight

    # Stem positioned with explicit toe in front (per Das §17.2 Fig. 17.4 convention).
    # Outer wall outline traces: top -> stem outer -> base outer -> close.
    wallX = [
        x_stem_front, x_stem_back, x_stem_back, b_base, b_base,
        0, 0, x_stem_front, x_stem_front,
    ]
    wallY = [
        y_top, y_top, y_iface, y_iface, y_bot,
        y_bot, y_iface, y_iface, y_top,
    ]

    margin_val = 0.12 * b_base
    dark = '#006400'

    wall_traces = [
        {"x": wallX, "y": wallY, "mode": "lines", "line": {"color": "#333", "width": 2.5},
         "showlegend": False, "hoverinfo": "skip"},
    ]
    # Dashed ground-level & top lines
    for yv in [y_top, y_gl]:
        wall_traces.append({
            "x": [-margin_val * 4 - b_toe, b_base + margin_val * 4], "y": [yv, yv],
            "mode": "lines", "line": {"color": "#888", "width": 1, "dash": "dash"},
            "showlegend": False, "hoverinfo": "skip"
        })
    # Backfill (heel side, above the heel slab)
    wall_traces.append({
        "x": [x_stem_back, b_base, b_base, x_stem_back],
        "y": [y_top, y_top, y_iface, y_iface],
        "fill": "toself", "fillcolor": "rgba(194,178,128,0.30)",
        "line": {"color": "rgba(160,145,95,0.7)", "width": 1},
        "showlegend": False, "hoverinfo": "skip"
    })
    # Front soil ON TOP of the toe slab (positive x, between x=0 and stem face)
    # Only when y_front exceeds the base thickness (i.e., soil reaches above the toe top).
    if y_front > t_base and b_toe > 0:
        soil_top_y = min(y_iface + (y_front - t_base), y_gl)
        wall_traces.append({
            "x": [0, x_stem_front, x_stem_front, 0],
            "y": [y_iface, y_iface, soil_top_y, soil_top_y],
            "fill": "toself", "fillcolor": "rgba(194,178,128,0.30)",
            "line": {"color": "rgba(160,145,95,0.7)", "width": 1},
            "showlegend": False, "hoverinfo": "skip"
        })
    # Lateral cover soil to the LEFT of the toe (provides passive resistance).
    # Drawn only if y_front > 0; uses a fictitious lateral extent for the visual.
    if y_front > 0:
        lat_cover_extent = max(0.5 * span, 0.5 * b_base)
        soil_top_lat = min(y_bot + y_front, y_gl)
        wall_traces.append({
            "x": [-lat_cover_extent, 0, 0, -lat_cover_extent],
            "y": [y_bot, y_bot, soil_top_lat, soil_top_lat],
            "fill": "toself", "fillcolor": "rgba(194,178,128,0.20)",
            "line": {"color": "rgba(160,145,95,0.5)", "width": 1, "dash": "dot"},
            "showlegend": False, "hoverinfo": "skip"
        })
    # Concrete fill (stem)
    wall_traces.append({
        "x": [x_stem_front, x_stem_back, x_stem_back, x_stem_front],
        "y": [y_top, y_top, y_iface, y_iface],
        "fill": "toself", "fillcolor": "rgba(160,160,160,0.55)", "line": {"width": 0},
        "showlegend": False, "hoverinfo": "skip"
    })
    # Concrete fill (base slab — full width including toe)
    wall_traces.append({
        "x": [0, b_base, b_base, 0], "y": [y_iface, y_iface, y_bot, y_bot],
        "fill": "toself", "fillcolor": "rgba(160,160,160,0.55)", "line": {"width": 0},
        "showlegend": False, "hoverinfo": "skip"
    })

    # Active pressure triangle (right side of wall, behind the heel)
    triBaseW = 0.35 * span
    triX0 = b_base + margin_val * 1.5
    wall_traces.append({
        "x": [triX0, triX0, triX0 + triBaseW], "y": [y_top, y_bot, y_bot],
        "mode": "lines", "fill": "toself", "fillcolor": "rgba(0,100,0,0.10)",
        "line": {"color": dark, "width": 1.8}, "showlegend": False, "hoverinfo": "skip"
    })
    for frac in [0.2, 0.4, 0.6, 0.8, 1.0]:
        yi = y_top - frac * span
        xi = triBaseW * frac
        wall_traces.append({
            "x": [triX0 + xi, triX0], "y": [yi, yi], "mode": "lines",
            "line": {"color": dark, "width": 2.5 if frac == 1.0 else 1},
            "showlegend": False, "hoverinfo": "skip"
        })

    # Surcharge lateral pressure rectangle (Pa_sur = q·Ka, depth-independent)
    # Drawn ON TOP of the active triangle as a separate orange band behind it.
    if q > 0:
        sur_rect_W = (q * Ka) / (gs * Ka * totalHeight) * triBaseW if totalHeight > 0 else 0
        sur_rect_W = min(sur_rect_W, 0.25 * span)
        wall_traces.append({
            "x": [triX0, triX0 + sur_rect_W, triX0 + sur_rect_W, triX0],
            "y": [y_top, y_top, y_bot, y_bot],
            "mode": "lines", "fill": "toself", "fillcolor": "rgba(230,126,34,0.18)",
            "line": {"color": "#e67e22", "width": 1.5, "dash": "dash"},
            "showlegend": False, "hoverinfo": "skip"
        })

    # Passive pressure triangle (left side of stem, on toe side) — only if y_front > 0
    passive_color = '#2980b9'   # blue, distinct from active green
    if y_front > 0:
        pTriBaseW = 0.22 * span
        # Position the passive triangle just to the LEFT of x=0 (left edge of base)
        pTriX0 = -margin_val * 1.5
        wall_traces.append({
            "x": [pTriX0, pTriX0 - pTriBaseW, pTriX0],
            "y": [y_bot + y_front, y_bot, y_bot],
            "mode": "lines", "fill": "toself", "fillcolor": "rgba(41,128,185,0.12)",
            "line": {"color": passive_color, "width": 1.8}, "showlegend": False, "hoverinfo": "skip"
        })
        for frac in [0.2, 0.4, 0.6, 0.8, 1.0]:
            yi = (y_bot + y_front) - frac * y_front
            xi = pTriBaseW * frac
            wall_traces.append({
                "x": [pTriX0 - xi, pTriX0], "y": [yi, yi], "mode": "lines",
                "line": {"color": passive_color, "width": 2.5 if frac == 1.0 else 1},
                "showlegend": False, "hoverinfo": "skip"
            })

    # Annotations
    ann = []
    h_label_x = -margin_val * 0.6 - (lat_cover_extent if y_front > 0 else 0)
    ann.append({"x": h_label_x, "y": (y_top + y_gl) / 2,
                "text": f"H\u2081 = {h1:.2f} m", "showarrow": False,
                "font": {"size": 13, "color": "#333"}, "xanchor": "right"})
    ann.append({"x": h_label_x, "y": (y_gl + y_bot) / 2,
                "text": f"H\u2082 = {h2:.2f} m", "showarrow": False,
                "font": {"size": 13, "color": "#333"}, "xanchor": "right"})
    ann.append({"x": x_stem_front + t_stem / 2, "y": y_top + 0.07 * span,
                "text": f"t<sub>stem</sub> = {t_stem:.2f} m", "showarrow": False,
                "font": {"size": 11, "color": "#333"}})
    ann.append({"x": b_base / 2, "y": y_bot - 0.10 * span,
                "text": f"b = {b_base:.2f} m  (toe {b_toe:.2f} | stem {t_stem:.2f} | heel {b_heel:.2f})",
                "showarrow": False, "font": {"size": 12, "color": "#333"}})
    ann.append({"x": b_base + margin_val * 0.5, "y": (y_iface + y_bot) / 2,
                "text": f"t<sub>base</sub> = {t_base:.2f} m", "showarrow": False,
                "font": {"size": 11, "color": "#333"}, "xanchor": "left"})
    # Toe / heel labels with arrows pointing to the slab projections
    if b_toe > 0:
        ann.append({
            "x": b_toe / 2, "y": y_iface + 0.02 * span,
            "ax": b_toe / 2, "ay": y_iface + 0.18 * span,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 3, "arrowsize": 1.0, "arrowwidth": 1.5,
            "arrowcolor": "#7f1d1d",
        })
        ann.append({
            "x": b_toe / 2, "y": y_iface + 0.20 * span,
            "text": "<b>toe</b>", "showarrow": False,
            "font": {"size": 12, "color": "#7f1d1d"},
        })
    ann.append({
        "x": x_stem_back + b_heel / 2, "y": y_iface + 0.02 * span,
        "ax": x_stem_back + b_heel / 2, "ay": y_iface + 0.18 * span,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 3, "arrowsize": 1.0, "arrowwidth": 1.5,
        "arrowcolor": "#7f1d1d",
    })
    ann.append({
        "x": x_stem_back + b_heel / 2, "y": y_iface + 0.20 * span,
        "text": "<b>heel</b>", "showarrow": False,
        "font": {"size": 12, "color": "#7f1d1d"},
    })

    arrowLen = 0.22 * span
    loads = [
        {"label": "P1", "val": P1, "x": x_stem_front + t_stem / 2, "y": (y_top + y_iface) / 2},
        {"label": "P2", "val": P2, "x": b_base / 2, "y": (y_iface + y_bot) / 2},
        {"label": "P3", "val": P3, "x": x_stem_back + b_heel / 2, "y": (y_top + y_iface) / 2},
    ]
    if P_toe_soil > 0:
        loads.append({
            "label": "P4", "val": P_toe_soil,
            "x": b_toe / 2,
            "y": (y_iface + min(y_iface + (y_front - t_base), y_gl)) / 2,
        })
    for ld in loads:
        ann.append({
            "x": ld["x"], "y": ld["y"], "ax": ld["x"], "ay": ld["y"] + arrowLen,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 2, "arrowsize": 1.2, "arrowwidth": 2.5,
            "arrowcolor": dark,
        })
        ann.append({
            "x": ld["x"], "y": ld["y"] + arrowLen + 0.04 * span,
            "text": f"<b>{ld['label']} = {ld['val']:.2f}</b>", "showarrow": False,
            "font": {"size": 11, "color": dark},
        })

    # Surcharge load arrows on top of the heel + label
    if q > 0:
        n_sur_arrows = 5
        x_a = x_stem_back + 0.05 * b_heel
        x_b = b_base - 0.05 * b_heel
        for i in range(n_sur_arrows):
            xa = x_a + i * (x_b - x_a) / max(n_sur_arrows - 1, 1)
            ann.append({
                "x": xa, "y": y_top + 0.01 * span,
                "ax": xa, "ay": y_top + 0.20 * span,
                "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
                "showarrow": True, "arrowhead": 2, "arrowsize": 1.0, "arrowwidth": 2,
                "arrowcolor": "#e67e22",
            })
        ann.append({
            "x": (x_stem_back + b_base) / 2, "y": y_top + 0.27 * span,
            "text": f"<b>q = {q:.1f} kPa</b>", "showarrow": False,
            "font": {"size": 12, "color": "#e67e22"},
        })

    # Active soil force arrow at H/3
    yH3 = y_bot + span / 3
    xH3 = triBaseW * (1 - 1 / 3)
    ann.append({
        "x": triX0, "y": yH3, "ax": triX0 + xH3, "ay": yH3,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.5, "arrowwidth": 3, "arrowcolor": dark
    })
    ann.append({
        "x": triX0 + xH3 + 0.02 * span, "y": yH3 + 0.04 * span,
        "text": f"<b>Pa = {Pa_soil:.2f}</b>", "showarrow": False,
        "font": {"size": 11, "color": dark}, "xanchor": "left"
    })
    ann.append({
        "x": triX0 + triBaseW / 2, "y": y_bot - 0.07 * span,
        "text": f"K<sub>a</sub>\u03B3<sub>s</sub>H = {maxHP:.2f} kPa", "showarrow": False,
        "font": {"size": 11, "color": dark}
    })
    ann.append({
        "x": triX0 + triBaseW + 0.08 * span, "y": (y_bot + yH3) / 2,
        "text": f"H/3 = {span / 3:.2f} m", "showarrow": False,
        "font": {"size": 11, "color": "#333"}, "xanchor": "left"
    })

    # Active surcharge force arrow at H/2 (depth-independent rectangle)
    if q > 0:
        sur_rect_W = (q * Ka) / (gs * Ka * totalHeight) * triBaseW if totalHeight > 0 else 0
        sur_rect_W = min(sur_rect_W, 0.25 * span)
        yH2 = y_bot + span / 2
        ann.append({
            "x": triX0, "y": yH2, "ax": triX0 + sur_rect_W * 0.7, "ay": yH2,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 2, "arrowsize": 1.3, "arrowwidth": 2.5,
            "arrowcolor": "#e67e22",
        })
        ann.append({
            "x": triX0 + sur_rect_W + 0.02 * span, "y": yH2 - 0.04 * span,
            "text": f"<b>Pa<sub>sur</sub> = {Pa_sur:.2f}</b>", "showarrow": False,
            "font": {"size": 10, "color": "#e67e22"}, "xanchor": "left"
        })
        ann.append({
            "x": triX0 + sur_rect_W * 1.05, "y": y_top + 0.04 * span,
            "text": f"K<sub>a</sub>q = {q*Ka:.2f} kPa", "showarrow": False,
            "font": {"size": 10, "color": "#e67e22"}, "xanchor": "left"
        })

    # Passive force arrow and annotations (only when y_front > 0)
    if y_front > 0:
        yp3 = y_bot + y_front / 3.0                    # Pp acts at y/3 from base
        pTriBaseW_local = 0.22 * span
        pTriX0_local = -margin_val * 1.5
        # Arrow from the max-pressure edge (left) toward the wall (right, +x direction)
        ann.append({
            "x": pTriX0_local, "y": yp3,
            "ax": pTriX0_local - pTriBaseW_local, "ay": yp3,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 2, "arrowsize": 1.5, "arrowwidth": 3,
            "arrowcolor": passive_color
        })
        pp_label = (
            f"<b>Pp = {Pp_soil:.2f}</b>" if include_passive
            else f"<b>Pp = {Pp_soil:.2f}</b> (not credited)"
        )
        ann.append({
            "x": pTriX0_local - pTriBaseW_local - 0.02 * span, "y": yp3 + 0.03 * span,
            "text": pp_label, "showarrow": False,
            "font": {"size": 10, "color": passive_color}, "xanchor": "right"
        })
        ann.append({
            "x": pTriX0_local - pTriBaseW_local / 2, "y": y_bot - 0.06 * span,
            "text": f"K<sub>p</sub>\u03B3<sub>s</sub>y = {maxPP:.2f} kPa", "showarrow": False,
            "font": {"size": 10, "color": passive_color}
        })
        # y_front dimension
        ann.append({
            "x": pTriX0_local + margin_val * 0.3, "y": y_bot + y_front / 2,
            "text": f"y = {y_front:.2f} m", "showarrow": False,
            "font": {"size": 10, "color": "#333"}, "xanchor": "left"
        })

    # Left extent of the plot x-axis: when y_front > 0 the passive triangle and lateral
    # cover soil live to the left of x = 0, so widen the range to include them.
    if y_front > 0:
        x_left = -lat_cover_extent - margin_val * 1.5
    else:
        x_left = -margin_val * 1.5

    wall_layout = {
        "xaxis": {"visible": False, "scaleanchor": "y", "scaleratio": 1,
                  "range": [x_left, b_base + margin_val + triBaseW + 0.30 * span]},
        "yaxis": {"visible": False, "range": [y_bot - 0.22 * span, y_top + 0.40 * span]},
        "margin": {"l": 20, "r": 20, "t": 50, "b": 30},
        "height": 680,
        "plot_bgcolor": "white", "paper_bgcolor": "white",
        "annotations": ann,
        "title": {"text": "Wall Cross-Section &amp; Lateral Pressure (Das &sect;17.4 / Fig. 17.4)",
                  "font": {"size": 16}, "x": 0.5},
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
