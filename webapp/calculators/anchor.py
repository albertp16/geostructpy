"""Deadman anchor / anchor-plate holding capacity.

Implements the ultimate holding capacity of a rigid rectangular anchor plate
embedded in soil, following:

- Das, B.M. & Sivakugan, N. (2019). *Principles of Foundation Engineering*,
  9th Edition SI, §18.18 "Holding Capacity of Deadman Anchors," p. 804-811.
- §18.19 Holding Capacity of Anchor Plates in Sand (Ovesen-Stromann, p. 804)
- §18.20 Holding Capacity of Anchor Plates in Clay (p. 811)
- Bowles, J.E. (1996). Foundation Analysis and Design, 5th Ed., Ch. 14.
- Poulos, H.G. & Davis, E.H. (1980). Pile Foundation Analysis and Design,
  Ch. 7 — lateral soil-structure interaction (context only).

Sand case (Ovesen-Stromann / simplified Rankine-difference):
    Pu = B · h · γ · H · (Kp - Ka) · Rf
where Rf is a shape/overburden factor from Das Fig. 18.29 (p. 805), here
approximated as a smooth function of H/h in the range [1, 5].

Clay case (Mackenzie 1955 / Tschebotarioff 1973):
    Pu = B · h · 9 · cu · Rf
with Rf → 1 for deep anchors and a simple linear taper near the surface.
"""

import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def _shape_factor_sand(H_h_ratio):
    """Approximate Das Fig. 18.29 (p. 805) for sand.

    Values read from Das's design chart for strip (B/h large) anchors:
        H/h  = 1   -> Rf ~ 1.00
        H/h  = 2   -> Rf ~ 1.40
        H/h  = 3   -> Rf ~ 1.75
        H/h  = 4   -> Rf ~ 2.00
        H/h >= 5   -> Rf ~ 2.20
    Interpolate linearly and clamp. This is the reduction-plus-shape factor
    applied to the raw Rankine-difference formula.
    """
    knots = [(1.0, 1.00), (2.0, 1.40), (3.0, 1.75), (4.0, 2.00), (5.0, 2.20)]
    if H_h_ratio <= knots[0][0]:
        return knots[0][1]
    if H_h_ratio >= knots[-1][0]:
        return knots[-1][1]
    for i in range(len(knots) - 1):
        x1, y1 = knots[i]
        x2, y2 = knots[i + 1]
        if x1 <= H_h_ratio <= x2:
            t = (H_h_ratio - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return knots[-1][1]


def calculate(B, h, H, soil_type, gamma, phi, cu, FS=2.0):
    """Compute ultimate and allowable holding capacity of a deadman anchor.

    Parameters
    ----------
    B : float
        Plate width (m) — dimension perpendicular to the pull direction.
    h : float
        Plate height (m) — dimension in the vertical plane.
    H : float
        Depth to the plate CENTER from ground surface (m).
    soil_type : {'sand', 'clay'}
        Soil type. 'sand' uses Ovesen-Stromann (Das §18.19); 'clay' uses
        the Mackenzie/Tschebotarioff formulation (Das §18.20).
    gamma : float
        Soil unit weight (kN/m³).
    phi : float
        Effective friction angle (degrees). Used for sand case.
    cu : float
        Undrained shear strength (kPa). Used for clay case.
    FS : float, optional
        Factor of safety. Default 2.0 per Das p. 804.

    Returns
    -------
    dict
        report, Pu, Pa, Rf, Ka, Kp, chart_traces, chart_layout.
    """
    if h <= 0 or B <= 0 or H <= 0:
        raise ValueError('B, h, and H must all be positive.')
    H_h_ratio = H / h

    report = '<div>'
    report += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 8px;">'
        'Ref: Das &amp; Sivakugan (2019, 9th SI) <strong>&sect;18.18 Holding Capacity '
        'of Deadman Anchors</strong>, <strong>p.&nbsp;804</strong>; '
        '<strong>&sect;18.19 Holding Capacity of Anchor Plates in Sand</strong> (p.&nbsp;804); '
        '<strong>&sect;18.20 Holding Capacity of Anchor Plates in Clay</strong> (p.&nbsp;811); '
        'Bowles (1996) Ch.&nbsp;14; Poulos &amp; Davis (1980) Ch.&nbsp;7 for '
        'lateral soil-structure interaction background.</p>'
    )

    if soil_type == 'sand':
        ph = max(min(phi, 45.0), 5.0)
        Ka = (1 - math.sin(ph * DEG)) / (1 + math.sin(ph * DEG))
        Kp = (1 + math.sin(ph * DEG)) / (1 - math.sin(ph * DEG))
        Kp_Ka = Kp - Ka
        # Shape/overburden factor from Das Fig. 18.29 (p. 805)
        Rf = _shape_factor_sand(H_h_ratio)
        # Raw (unfactored) Rankine-difference capacity per unit width of plate
        #   q_p = γ · H · (Kp - Ka)                (avg passive-minus-active stress on plate)
        # Total ultimate holding force (Das §18.19):
        #   Pu = B · h · q_p · Rf
        q_p = gamma * H * Kp_Ka
        Pu = B * h * q_p * Rf
        Pa = Pu / FS

        report += '<h4>Sand &mdash; Ovesen-Stromann (Das &sect;18.19, p.&nbsp;804)</h4>'
        report += (
            f'\\[ K_a = \\tfrac{{1-\\sin\\phi}}{{1+\\sin\\phi}} = {_f(Ka,4)}, \\quad '
            f'K_p = \\tfrac{{1+\\sin\\phi}}{{1-\\sin\\phi}} = {_f(Kp,4)} \\]'
        )
        report += f'\\[ q_p = \\gamma H (K_p - K_a) = {_f(gamma,2)} \\times {_f(H,2)} \\times {_f(Kp_Ka,4)} = {_f(q_p,2)} \\text{{ kPa}} \\]'
        report += (
            f'<p><strong>H/h ratio</strong> = {_f(H_h_ratio,2)} &rarr; shape/overburden factor '
            f'R<sub>f</sub> = <strong>{_f(Rf,3)}</strong> '
            '(interpolated from Das Fig. 18.29, p.&nbsp;805)</p>'
        )
        report += (
            f'\\[ P_u = B \\cdot h \\cdot q_p \\cdot R_f = {_f(B,2)} \\times {_f(h,2)} '
            f'\\times {_f(q_p,2)} \\times {_f(Rf,3)} = {_f(Pu,2)} \\text{{ kN}} \\]'
        )
        report += (
            f'\\[ P_a = \\frac{{P_u}}{{FS}} = \\frac{{{_f(Pu,2)}}}{{{_f(FS,1)}}} = '
            f'{_f(Pa,2)} \\text{{ kN}} \\]'
        )

    elif soil_type == 'clay':
        # Mackenzie 1955 / Tschebotarioff 1973 (Das §18.20, p. 811)
        #   Pu = B · h · 9 · cu · Rf
        # Rf transitions from about 0.5 at H/h = 1 to 1.0 at H/h ≥ 3 (deep)
        if H_h_ratio <= 1:
            Rf = 0.5
        elif H_h_ratio >= 3:
            Rf = 1.0
        else:
            Rf = 0.5 + 0.25 * (H_h_ratio - 1)
        Nc = 9.0
        Pu = B * h * Nc * cu * Rf
        Pa = Pu / FS
        Ka = Kp = Kp_Ka = 0.0

        report += '<h4>Clay &mdash; Mackenzie (1955) / Tschebotarioff (1973) (Das &sect;18.20, p.&nbsp;811)</h4>'
        report += (
            f'\\[ P_u = B \\cdot h \\cdot N_c \\cdot c_u \\cdot R_f \\]'
        )
        report += (
            f'<p><strong>H/h ratio</strong> = {_f(H_h_ratio,2)} &rarr; depth factor '
            f'R<sub>f</sub> = <strong>{_f(Rf,3)}</strong> (deep-anchor limit = 1.0 at H/h &ge; 3)</p>'
        )
        report += (
            f'\\[ P_u = {_f(B,2)} \\times {_f(h,2)} \\times 9 \\times {_f(cu,2)} \\times '
            f'{_f(Rf,3)} = {_f(Pu,2)} \\text{{ kN}} \\]'
        )
        report += (
            f'\\[ P_a = \\frac{{P_u}}{{FS}} = \\frac{{{_f(Pu,2)}}}{{{_f(FS,1)}}} = '
            f'{_f(Pa,2)} \\text{{ kN}} \\]'
        )
    else:
        raise ValueError(f"Unknown soil_type '{soil_type}' — use 'sand' or 'clay'.")

    report += '</div>'

    chart = _build_anchor_chart(B, h, H, soil_type, Pu, Pa)

    return {
        'report': report,
        'Pu': Pu,
        'Pa': Pa,
        'Rf': Rf,
        'Ka': Ka,
        'Kp': Kp,
        'H_h_ratio': H_h_ratio,
        'chart_traces': chart['traces'],
        'chart_layout': chart['layout'],
    }


def _build_anchor_chart(B, h, H, soil_type, Pu, Pa):
    """Cross-section schematic of the anchor plate with wedge diagram and
    force arrow. Styled as a textbook figure (Das Fig. 18.27 / 18.29)."""
    # Plate is drawn vertically (viewed in elevation), centered at depth H.
    top_plate = H - h / 2
    bot_plate = H + h / 2
    plate_x = [0, 0.10 * h, 0.10 * h, 0, 0]
    plate_y = [top_plate, top_plate, bot_plate, bot_plate, top_plate]

    # Ground surface
    surf_x = [-2 * h, 5 * h]
    surf_y = [0, 0]

    # Active wedge (behind plate, the pull side) — simplified as a triangle
    active_wedge_x = [0, -2 * h, 0, 0]
    active_wedge_y = [top_plate, 0, 0, top_plate]
    # Passive wedge (in front of plate, the resisting side)
    passive_wedge_x = [0.10 * h, 0.10 * h + 2.5 * h, 0.10 * h, 0.10 * h]
    passive_wedge_y = [bot_plate, 0, 0, bot_plate]

    traces = []
    # Soil mass tinted background
    traces.append({
        'x': [-2.5 * h, 5 * h, 5 * h, -2.5 * h],
        'y': [0, 0, 1.5 * H, 1.5 * H],
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(194,178,128,0.25)',
        'line': {'color': 'rgba(160,145,95,0.4)', 'width': 1},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Ground surface
    traces.append({
        'x': surf_x, 'y': surf_y,
        'mode': 'lines', 'line': {'color': '#333', 'width': 2},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Active wedge (red-tinted, dashed outline)
    traces.append({
        'x': active_wedge_x, 'y': active_wedge_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(231,76,60,0.20)',
        'line': {'color': '#c0392b', 'width': 1.5, 'dash': 'dash'},
        'name': 'Active wedge', 'hoverinfo': 'skip',
    })
    # Passive wedge (blue-tinted, solid outline)
    traces.append({
        'x': passive_wedge_x, 'y': passive_wedge_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(52,152,219,0.25)',
        'line': {'color': '#2980b9', 'width': 2},
        'name': 'Passive wedge', 'hoverinfo': 'skip',
    })
    # Plate (concrete gray)
    traces.append({
        'x': plate_x, 'y': plate_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(80,80,80,0.8)',
        'line': {'color': '#222', 'width': 2},
        'showlegend': False, 'hoverinfo': 'skip',
    })

    ann = [
        {'x': 0, 'y': H, 'text': f'<b>H = {H:.2f} m</b>',
         'showarrow': False, 'font': {'size': 10, 'color': '#333'},
         'xanchor': 'left', 'bgcolor': 'rgba(255,255,255,0.8)'},
        {'x': -0.05 * h, 'y': top_plate - 0.05 * h,
         'text': f'h = {h:.2f} m', 'showarrow': False,
         'font': {'size': 10, 'color': '#333'}, 'xanchor': 'right'},
        {'x': 2 * h, 'y': H + 0.1 * h, 'text': f'<b>P<sub>u</sub> = {Pu:.1f} kN</b>',
         'showarrow': False, 'font': {'size': 11, 'color': '#2980b9'}},
        {'x': 2 * h, 'y': H + 0.3 * h, 'text': f'P<sub>a</sub> = {Pa:.1f} kN (FS-reduced)',
         'showarrow': False, 'font': {'size': 10, 'color': '#2980b9'}},
        # Pull force arrow on plate, pointing LEFT (the tie-rod direction)
        {
            'x': -1.5 * h, 'y': H, 'ax': 0.10 * h, 'ay': H,
            'xref': 'x', 'yref': 'y', 'axref': 'x', 'ayref': 'y',
            'showarrow': True, 'arrowhead': 2, 'arrowsize': 1.5,
            'arrowwidth': 3, 'arrowcolor': '#c0392b',
        },
    ]

    layout = {
        'title': {'text': f'Deadman Anchor in {soil_type.capitalize()} &mdash; Cross Section',
                  'font': {'size': 13}, 'x': 0.5},
        'xaxis': {'visible': False, 'scaleanchor': 'y', 'scaleratio': 1,
                  'range': [-2.5 * h, 5 * h]},
        'yaxis': {'visible': False, 'autorange': 'reversed',
                  'range': [1.5 * H, -0.2 * h]},
        'margin': {'l': 10, 'r': 10, 't': 40, 'b': 20},
        'height': 500,
        'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'annotations': ann,
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.02, 'xanchor': 'center'},
    }
    return {'traces': traces, 'layout': layout}
