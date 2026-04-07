"""Braced-cut excavation analysis (basic / first build).

Implements the Peck (1969) apparent earth-pressure envelope method for a
braced excavation in homogeneous sand or soft-to-medium clay, plus the
strut-load distribution to a single horizontal level of struts and the
bottom heave (Bjerrum & Eide, 1956 / Terzaghi 1943) check for clay.

This is the textbook method covered in:

- Das, B.M. & Sivakugan, N. (2019). *Principles of Foundation Engineering*,
  9th Edition SI. Cengage. Ch. 19 "Braced Cuts" (pp. 814-846):
    §19.2 Braced-cut analysis based on general wedge theory
    §19.3 Pressure envelope for braced-cut design
    §19.4 Pressure envelope for cuts in layered soil
    §19.5 Design of various components of a braced cut
    §19.7 Bottom heave of a cut in clay
    §19.8 Stability of the bottom of a cut in sand
- Bowles, J.E. (1996). *Foundation Analysis and Design*, 5th Edition.
  McGraw-Hill. Ch. 14 "Walls for Excavations":
    §14.1 Construction excavations
    §14.2 Soil pressures on braced excavation walls
    §14.3 Conventional design of braced excavation walls
    §14.6 Instability due to heave of bottom of excavation
- Peck, R.B. (1969). Deep excavations and tunneling in soft ground.
  *Proc. 7th Int. Conf. Soil Mechanics and Foundation Engineering*,
  State-of-the-Art volume, pp. 225-290.
- Bjerrum, L. & Eide, O. (1956). Stability of strutted excavations in
  clay. *Géotechnique*, 6(1), 32-47.
- Terzaghi, K. (1943). *Theoretical Soil Mechanics*. Wiley. (Bottom heave.)

Scope of this first build: single excavation depth H, homogeneous soil
(sand OR clay), uniform strut spacing along the wall, no surcharge, no
groundwater pressure differential. The intent is to give the engineer
a quick textbook-style estimate for preliminary sizing — full design
should use the layered-soil case (Das §19.4) and a more rigorous
analysis (e.g., LPILE or PLAXIS) for final values.
"""

import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(soil_type, H, gamma, phi, cu, h_strut_spacing, n_strut_levels,
              FS_heave=1.5):
    """Compute apparent-earth-pressure design loads on a braced cut.

    Parameters
    ----------
    soil_type : {'sand', 'soft_medium_clay', 'stiff_clay'}
        Selects the Peck (1969) apparent-pressure envelope shape.
    H : float
        Excavation depth (m).
    gamma : float
        Total (moist) unit weight of soil (kN/m³).
    phi : float
        Effective friction angle (deg). Used only for the sand case.
    cu : float
        Undrained shear strength (kPa). Used only for clay cases.
    h_strut_spacing : float
        Vertical spacing between strut levels (m). Used to compute the
        per-strut force from the apparent-pressure envelope.
    n_strut_levels : int
        Number of horizontal strut levels along the wall height.
    FS_heave : float, optional
        Required factor of safety against bottom heave for clay
        (Bjerrum & Eide). Default 1.5 per Bowles §14.6.

    Returns
    -------
    dict
        report : HTML report with MathJax + reference citations
        sigma_max : peak apparent earth pressure (kPa)
        Pa : total horizontal load on the wall per unit run (kN/m)
        F_strut : design force per strut level per unit run of wall (kN/m)
        N_s : Bjerrum stability number for clay (dimensionless)
        FS_heave_actual : computed FS against bottom heave (clay only)
        chart_traces, chart_layout : Plotly cross-section + apparent
            pressure envelope figure
    """
    GAMMA_W = 9.81

    # ---- Apparent earth-pressure envelope (Peck 1969) ----
    # Das & Sivakugan §19.3 Fig. 19.4 (pp. 820-823); Bowles §14.2 Fig. 14-1
    if soil_type == 'sand':
        # Sand: rectangular envelope, sigma_a = 0.65 · gamma · H · Ka
        ph = max(min(phi, 45.0), 5.0)
        Ka = (1 - math.sin(ph * DEG)) / (1 + math.sin(ph * DEG))
        sigma_max = 0.65 * gamma * H * Ka
        envelope_shape = 'rectangular (uniform with depth)'
        Ns = None
        FS_heave_actual = None

    elif soil_type == 'soft_medium_clay':
        # Bjerrum stability number Ns = gamma·H / cu  (Das Eq. 19.13)
        Ns = gamma * H / cu if cu > 0 else float('inf')
        # Soft-medium clay: use the larger of (i) trapezoidal envelope
        # 0.3·gamma·H or (ii) the m·gamma·H − 4·cu envelope per Peck
        # (Das Eq. 19.4-19.5).
        sigma_a_1 = 0.3 * gamma * H
        # Peck's reduction factor m: 1.0 normally, 0.4 for very soft clays
        m_peck = 1.0
        if Ns > 6:
            m_peck = 0.4
        sigma_a_2 = gamma * H * (1 - (4 * cu) / (gamma * H)) * m_peck if gamma * H > 0 else 0
        sigma_max = max(sigma_a_1, sigma_a_2)
        envelope_shape = 'trapezoidal (Peck 1969 soft-medium clay)'
        # Bjerrum & Eide bottom-heave check (Das Eq. 19.18, p. 836)
        # FS = Nc · cu / (gamma · H + q)   with q = 0 here
        Nc_bj = 5.7  # for square / strip cut, Bjerrum & Eide chart at L/B large
        FS_heave_actual = Nc_bj * cu / (gamma * H) if gamma * H > 0 else float('inf')

    elif soil_type == 'stiff_clay':
        # Stiff clay (Ns = gamma·H/cu < 4): trapezoidal envelope
        # sigma_a = 0.2·gamma·H to 0.4·gamma·H, use 0.3 as midpoint per Peck
        Ns = gamma * H / cu if cu > 0 else float('inf')
        sigma_max = 0.3 * gamma * H
        envelope_shape = 'trapezoidal (Peck 1969 stiff fissured clay)'
        Nc_bj = 5.7
        FS_heave_actual = Nc_bj * cu / (gamma * H) if gamma * H > 0 else float('inf')

    else:
        raise ValueError(
            f"Unknown soil_type '{soil_type}'. Use 'sand', "
            f"'soft_medium_clay', or 'stiff_clay'.")

    # Total horizontal load (per unit run of wall)
    if soil_type == 'sand':
        Pa_total = sigma_max * H                    # rectangle area
    else:
        # Trapezoid: top 0.25·H and bottom 0.25·H taper to 0; middle 0.5·H is full
        Pa_total = sigma_max * (0.25 * H * 0.5 + 0.5 * H + 0.25 * H * 0.5)
        # Equivalent area: sigma_max * 0.75 * H
        Pa_total = sigma_max * 0.75 * H

    # Design strut force per level (tributary area = h_strut_spacing × 1 m)
    F_strut = sigma_max * h_strut_spacing

    # ---- Build HTML report ----
    r = '<div>'
    r += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 8px;">'
        'Refs: Peck (1969) apparent earth-pressure envelopes; '
        '<strong>Das &amp; Sivakugan (2019, 9th SI) Ch.&nbsp;19 Braced Cuts</strong>: '
        '&sect;19.3 Pressure envelope for braced-cut design (pp.&nbsp;820&ndash;823, '
        'Fig.&nbsp;19.4); &sect;19.5 Design of various components of a braced cut '
        '(p.&nbsp;823); &sect;19.7 Bottom heave of a cut in clay (p.&nbsp;835); '
        'Bjerrum &amp; Eide (1956). '
        '<strong>Bowles (1996, 5e) Ch.&nbsp;14 Walls for Excavations</strong>: '
        '&sect;14.1&ndash;14.3 (pp.&nbsp;785&ndash;803); &sect;14.6 Heave of bottom of '
        'excavation. <em>Scope:</em> homogeneous single-soil profile, no GWT differential, '
        'no surcharge &mdash; this is a preliminary sizing tool, not a final design '
        'calculator.</p>'
    )

    r += '<h4>Apparent Earth-Pressure Envelope (Peck 1969)</h4>'
    if soil_type == 'sand':
        r += (
            f'\\[ K_a = \\tfrac{{1-\\sin\\phi\'}}{{1+\\sin\\phi\'}} = {_f(Ka, 4)} \\]'
            f'\\[ \\sigma_a = 0.65 \\cdot \\gamma \\cdot H \\cdot K_a = '
            f'0.65 \\times {_f(gamma)} \\times {_f(H)} \\times {_f(Ka, 4)} = '
            f'{_f(sigma_max)} \\text{{ kPa}} \\]'
            f'<p>Envelope shape: <strong>{envelope_shape}</strong></p>'
        )
    elif soil_type == 'soft_medium_clay':
        r += (
            f'<p>Bjerrum stability number: '
            f'\\[ N_s = \\frac{{\\gamma H}}{{c_u}} = '
            f'\\frac{{{_f(gamma)} \\times {_f(H)}}}{{{_f(cu)}}} = {_f(Ns, 2)} \\]</p>'
        )
        if Ns > 6:
            r += (
                '<p style="color:#b7791f;"><em>N<sub>s</sub> &gt; 6 &mdash; very soft '
                'clay, applying Peck\'s reduction factor m = 0.4 to the second '
                'envelope expression.</em></p>'
            )
        r += (
            f'\\[ \\sigma_{{a,1}} = 0.3 \\gamma H = {_f(sigma_a_1)} \\text{{ kPa}} \\]'
            f'\\[ \\sigma_{{a,2}} = m \\gamma H \\left(1 - \\frac{{4c_u}}{{\\gamma H}}\\right) = '
            f'{_f(sigma_a_2)} \\text{{ kPa}} \\quad (m = {_f(m_peck, 2)}) \\]'
            f'\\[ \\sigma_a = \\max(\\sigma_{{a,1}}, \\sigma_{{a,2}}) = {_f(sigma_max)} \\text{{ kPa}} \\]'
            f'<p>Envelope shape: <strong>{envelope_shape}</strong></p>'
        )
    else:  # stiff clay
        r += (
            f'<p>Bjerrum stability number: '
            f'\\[ N_s = \\frac{{\\gamma H}}{{c_u}} = {_f(Ns, 2)} \\]</p>'
            f'\\[ \\sigma_a = 0.3 \\cdot \\gamma \\cdot H = {_f(sigma_max)} \\text{{ kPa}} \\]'
            f'<p>Envelope shape: <strong>{envelope_shape}</strong></p>'
        )
        if Ns >= 4:
            r += (
                '<p style="color:#b7791f;"><em>Warning: N<sub>s</sub> &ge; 4 indicates '
                'this clay should be modeled as soft-medium, not stiff fissured.</em></p>'
            )

    r += '<h4>Total Horizontal Load on Wall</h4>'
    if soil_type == 'sand':
        r += (
            f'\\[ P_a = \\sigma_a \\cdot H = {_f(sigma_max)} \\times {_f(H)} = '
            f'{_f(Pa_total)} \\text{{ kN/m}} \\quad \\text{{(rectangular envelope area)}} \\]'
        )
    else:
        r += (
            f'\\[ P_a = \\sigma_a \\cdot 0.75 H = {_f(sigma_max)} \\times 0.75 \\times {_f(H)} = '
            f'{_f(Pa_total)} \\text{{ kN/m}} \\quad \\text{{(trapezoidal envelope area)}} \\]'
        )

    r += '<h4>Design Strut Force (per Strut Level, per m Run of Wall)</h4>'
    r += (
        f'\\[ F_{{strut}} = \\sigma_a \\cdot h_{{strut}} = '
        f'{_f(sigma_max)} \\times {_f(h_strut_spacing)} = '
        f'{_f(F_strut)} \\text{{ kN/m}} \\]'
    )
    r += (
        f'<p>With <strong>{n_strut_levels}</strong> strut level(s) at vertical spacing '
        f'{_f(h_strut_spacing)} m, each strut level (per metre run of wall) carries '
        f'<strong>{_f(F_strut)} kN/m</strong>. Per Das &amp; Sivakugan &sect;19.5 '
        f'(p.&nbsp;823) and Bowles &sect;14.3 the actual horizontal load distribution to '
        f'individual struts depends on the strut horizontal spacing along the wall and on '
        f'whether the wall is treated as a continuous beam supported at strut levels '
        f'(simply supported between adjacent struts).</p>'
    )

    if soil_type in ('soft_medium_clay', 'stiff_clay'):
        r += '<h4>Bottom-Heave Stability (Bjerrum &amp; Eide 1956)</h4>'
        r += (
            f'\\[ FS_{{heave}} = \\frac{{N_c \\cdot c_u}}{{\\gamma H + q}} = '
            f'\\frac{{{_f(Nc_bj)} \\times {_f(cu)}}}{{{_f(gamma * H)} + 0}} = '
            f'{_f(FS_heave_actual, 2)} \\]'
        )
        passed = FS_heave_actual >= FS_heave
        color = '#27ae60' if passed else '#e74c3c'
        verdict = 'PASS' if passed else 'FAIL'
        r += (
            f'<p>Required FS = {_f(FS_heave, 2)}. Computed FS = {_f(FS_heave_actual, 2)} '
            f'&rarr; <span style="color:{color};font-weight:bold;">{verdict}</span></p>'
            '<p style="font-size:0.82em;color:#6c757d;">Ref: Das &amp; Sivakugan '
            '&sect;19.7 Eq.&nbsp;19.18, <strong>p.&nbsp;835</strong>; '
            'Bjerrum &amp; Eide (1956) <em>G&eacute;otechnique</em> 6(1), 32&ndash;47; '
            'Bowles (1996, 5e) &sect;14.6 (Eq.&nbsp;14-9). N<sub>c</sub> = 5.7 used here '
            'for a strip / square cut at large L/B; for shallow cuts read N<sub>c</sub> '
            'from Bjerrum &amp; Eide chart (Das Fig.&nbsp;19.18, p.&nbsp;836).</p>'
        )

    r += '</div>'

    chart = _build_envelope_chart(soil_type, H, sigma_max, Pa_total, h_strut_spacing,
                                  n_strut_levels)

    return {
        'report': r,
        'sigma_max': sigma_max,
        'Pa': Pa_total,
        'F_strut': F_strut,
        'Ns': Ns,
        'FS_heave_actual': FS_heave_actual,
        'chart_traces': chart['traces'],
        'chart_layout': chart['layout'],
    }


def _build_envelope_chart(soil_type, H, sigma_max, Pa_total, h_strut, n_strut):
    """Plotly cross-section: excavation wall on the left + apparent
    earth-pressure envelope on the right (Das Fig. 19.4 / Bowles Fig. 14-1)."""
    # Wall as a thick black vertical line at x = 0; envelope to the right.
    # y axis: depth from ground surface, positive downward (autorange reversed).
    is_sand = (soil_type == 'sand')

    traces = []

    # Ground surface
    traces.append({
        'x': [-0.4 * sigma_max, sigma_max * 1.4],
        'y': [0, 0],
        'mode': 'lines',
        'line': {'color': '#333', 'width': 1.5},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Excavation bottom line
    traces.append({
        'x': [-0.4 * sigma_max, sigma_max * 1.4],
        'y': [H, H],
        'mode': 'lines',
        'line': {'color': '#8b6914', 'width': 1.5, 'dash': 'dash'},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Wall (thick black vertical)
    traces.append({
        'x': [0, 0], 'y': [0, H],
        'mode': 'lines',
        'line': {'color': '#222', 'width': 5},
        'showlegend': False, 'hoverinfo': 'skip',
    })

    # Apparent-pressure envelope polygon
    if is_sand:
        # Rectangle from y=0 to y=H, x=0 to x=sigma_max
        env_x = [0, sigma_max, sigma_max, 0, 0]
        env_y = [0, 0, H, H, 0]
    else:
        # Trapezoid: 0 at top, sigma_max at 0.25H, sigma_max at 0.75H, 0 at H
        env_x = [0, sigma_max, sigma_max, 0, 0, 0]
        env_y = [0, 0.25 * H, 0.75 * H, H, H, 0]
    traces.append({
        'x': env_x, 'y': env_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(231,76,60,0.30)',
        'line': {'color': '#c0392b', 'width': 2},
        'name': f'σ_a (max {sigma_max:.1f} kPa)',
    })

    # Strut markers along the wall
    if n_strut > 0:
        strut_y = [(i + 0.5) * (H / n_strut) for i in range(n_strut)]
        strut_x = [-0.05 * sigma_max] * n_strut
        traces.append({
            'x': strut_x, 'y': strut_y,
            'mode': 'markers+text',
            'marker': {'symbol': 'square', 'size': 14, 'color': '#1f6391'},
            'text': [f'S{i+1}' for i in range(n_strut)],
            'textposition': 'middle left',
            'name': 'Strut level',
        })

    ann = [
        {'x': sigma_max * 0.5, 'y': H * 0.5,
         'text': f'<b>σ_a = {sigma_max:.1f} kPa</b><br>P_a = {Pa_total:.1f} kN/m',
         'showarrow': False, 'font': {'size': 11, 'color': '#7f1d1d'},
         'bgcolor': 'rgba(255,255,255,0.7)'},
        {'x': -0.20 * sigma_max, 'y': H * 0.5,
         'text': f'<b>H = {H:.2f} m</b>',
         'showarrow': False, 'font': {'size': 12, 'color': '#333'},
         'xanchor': 'right'},
        {'x': sigma_max * 0.7, 'y': 0,
         'text': 'ground surface', 'showarrow': False,
         'font': {'size': 9, 'color': '#666'}, 'yanchor': 'bottom'},
        {'x': sigma_max * 0.7, 'y': H,
         'text': 'excavation level', 'showarrow': False,
         'font': {'size': 9, 'color': '#8b6914'}, 'yanchor': 'top'},
    ]

    layout = {
        'title': {'text': 'Apparent Earth-Pressure Envelope (Peck 1969)',
                  'font': {'size': 14}, 'x': 0.5},
        'xaxis': {'title': 'Lateral pressure (kPa)',
                  'range': [-0.4 * sigma_max, sigma_max * 1.4],
                  'zeroline': True, 'zerolinecolor': '#999'},
        'yaxis': {'title': 'Depth below ground surface (m)',
                  'autorange': 'reversed', 'zeroline': False},
        'height': 520,
        'margin': {'l': 70, 'r': 20, 't': 50, 'b': 60},
        'plot_bgcolor': '#ffffff', 'paper_bgcolor': '#ffffff',
        'annotations': ann,
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.15, 'xanchor': 'center'},
    }
    return {'traces': traces, 'layout': layout}
