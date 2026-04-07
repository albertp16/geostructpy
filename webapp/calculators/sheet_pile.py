"""Cantilever sheet-pile wall in homogeneous sand.

Implements the closed-form analysis for a cantilever sheet pile penetrating
sandy soil per Das, B.M. & Sivakugan, N. (2019) *Principles of Foundation
Engineering*, 9th Edition SI, §18.4 "Cantilever Sheet Piling Penetrating
Sandy Soil," pp. 758-764, Eq. 18.11-18.17.

The calculator solves the classical quartic (Das Eq. 18.17) for the required
embedment depth D given the wall height L above the dredge line, water-table
depth L1, soil unit weights γ and γ', friction angle φ, and any surcharge q on
the backfill surface. It then computes the maximum bending moment and the
required section modulus for the steel sheet pile.

References
----------
- Das, B.M. & Sivakugan, N. (2019). Principles of Foundation Engineering,
  9th Edition SI. Cengage Learning. Ch. 18 §18.3-18.4, pp. 757-764.
- Teng, W.C. (1962). Foundation Design. Prentice-Hall.
- USS Steel (1975). Sheet Pile Design Manual. United States Steel Corp.
- Poulos, H.G. & Davis, E.H. (1980). Pile Foundation Analysis and Design.
  Wiley. Ch. 7 — lateral loading of single piles (context only).
"""

import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def _solve_quartic(coeffs):
    """Solve a quartic polynomial D^4 + a3 D^3 + a2 D^2 + a1 D + a0 = 0 for
    the smallest positive real root. Uses a simple bisection on a sensible
    interval because the Das §18.4 quartic is well-behaved in the physical
    range (0 < D < 5·L).

    Parameters
    ----------
    coeffs : tuple of 5
        (a4, a3, a2, a1, a0) — a4 is the coefficient of D^4 (always 1
        after normalisation for Das Eq. 18.17).
    """
    a4, a3, a2, a1, a0 = coeffs

    def f(D):
        return a4 * D ** 4 + a3 * D ** 3 + a2 * D ** 2 + a1 * D + a0

    # Quartic is monotonic on (0, large D) for the Das coefficients when the
    # problem is physically feasible. Bisection from 0 to 100 m should cover
    # any realistic wall.
    lo, hi = 0.01, 100.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        # No sign change — fall back to Newton's method starting from a guess
        D = 1.0
        for _ in range(60):
            fval = f(D)
            fder = 4 * a4 * D ** 3 + 3 * a3 * D ** 2 + 2 * a2 * D + a1
            if abs(fder) < 1e-12:
                break
            D_new = D - fval / fder
            if D_new <= 0:
                D_new = D / 2
            if abs(D_new - D) < 1e-6:
                return D_new
            D = D_new
        return max(D, 0.1)
    for _ in range(200):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if abs(fmid) < 1e-6 or (hi - lo) < 1e-6:
            return mid
        if flo * fmid < 0:
            hi = fmid and mid
        else:
            lo = mid
            flo = fmid
        # Recompute due to the and-short-circuit above
        hi = (lo + hi) / 2 + (hi - (lo + hi) / 2)
    return (lo + hi) / 2


def calculate(L, gamma, gamma_sat, phi, L1, q, sigma_allow=170000.0):
    """Design a cantilever sheet-pile wall in homogeneous sand.

    Parameters
    ----------
    L : float
        Height of wall above the dredge line (m). Total "unsupported height"
        on the backfill side.
    gamma : float
        Moist unit weight of backfill above the water table (kN/m³).
    gamma_sat : float
        Saturated unit weight of soil below the water table (kN/m³). Used to
        compute γ' = γ_sat − γ_w.
    phi : float
        Effective friction angle of sand (degrees). Assumed uniform above
        and below the dredge line for this first build.
    L1 : float
        Depth from top of wall to water table (m). Set L1 = L (or greater)
        if no water table exists within the retained height.
    q : float
        Uniform surcharge on backfill surface (kPa).
    sigma_allow : float, optional
        Allowable bending stress in the steel sheet pile (kPa). Default
        170000 kPa = 170 MPa, typical for structural sheet pile steel.

    Returns
    -------
    dict
        report : HTML report with MathJax equations and references
        Ka, Kp : Rankine coefficients
        D_req : required embedment depth below dredge line (m)
        D_design : D_req × 1.30 safety factor per Das p. 762
        M_max : maximum bending moment (kN·m/m)
        S_req : required section modulus (m³/m)
        chart_traces, chart_layout : Plotly pressure diagram
    """
    GAMMA_W = 9.81

    ph = max(min(phi, 45.0), 5.0)  # clamp
    Ka = (1 - math.sin(ph * DEG)) / (1 + math.sin(ph * DEG))
    Kp = (1 + math.sin(ph * DEG)) / (1 - math.sin(ph * DEG))
    Kp_Ka = Kp - Ka
    gamma_eff = gamma_sat - GAMMA_W

    # Apply surcharge by treating it as an equivalent additional soil height
    # above the top of wall: h_q = q / gamma (Das Fig. 18.11 / §18.3).
    h_q_equiv = q / gamma if gamma > 0 else 0.0

    # L2 = penetration of wall below the water table, above the dredge line
    # (= L - L1 when L1 < L; else 0).
    L2 = max(L - L1, 0.0)
    L1_used = min(L1, L)

    # Effective lateral pressure at the water table (depth L1 from top of wall)
    sigma1 = Ka * gamma * (L1_used + h_q_equiv)
    # Effective lateral pressure at the dredge line (depth L from top of wall)
    sigma2 = sigma1 + Ka * gamma_eff * L2
    # Note: below the water table, the driving effective stress uses γ'; water
    # pressure is assumed balanced on both sides of the wall (free-standing
    # dredge line is the classical simplification).

    # L3 = distance below dredge line to the point of zero net pressure
    #   L3 = sigma2 / [(Kp - Ka) · γ']    (Das Eq. 18.11)
    if gamma_eff <= 0 or Kp_Ka <= 0:
        raise ValueError('Invalid soil parameters: γ_eff and (Kp−Ka) must be positive.')
    L3 = sigma2 / (Kp_Ka * gamma_eff)

    # P = resultant of the active pressure diagram above (dredge line + L3)
    # = area of the combined trapezoid from z=0 to z=L1, trapezoid from L1 to
    # L, plus the little triangle from the dredge line down to the zero-pressure point.
    # (Das Eq. 18.12 / Fig. 18.11.)
    P1_area = 0.5 * sigma1 * L1_used                      # triangle above WT
    P2_area = sigma1 * L2                                  # rectangle below WT
    P3_area = 0.5 * (sigma2 - sigma1) * L2                 # triangle below WT
    P4_area = 0.5 * sigma2 * L3                            # triangle below dredge line
    P_total = P1_area + P2_area + P3_area + P4_area

    # z_bar = distance from the point of zero pressure UP to the resultant P.
    # Compute centroid in a reference frame where z=0 at the zero-pressure
    # point and z increases upward.
    # Levels (heights above the zero-pressure point):
    #   zero-pressure point: z = 0
    #   dredge line:         z = L3
    #   water table:         z = L3 + L2
    #   top of wall:         z = L3 + L2 + L1_used
    z_P4 = L3 / 3.0                                        # triangle in sand below dredge
    z_P3 = L3 + L2 / 3.0                                   # triangle below WT (upper third)
    z_P2 = L3 + L2 / 2.0                                   # rectangle below WT
    z_P1 = L3 + L2 + L1_used / 3.0                         # triangle above WT
    M_sum = P1_area * z_P1 + P2_area * z_P2 + P3_area * z_P3 + P4_area * z_P4
    z_bar = M_sum / P_total if P_total > 0 else 0.0

    # Das Eq. 18.16 / 18.17: D^4 + A1 D^3 − A2 D^2 − A3 D − A4 = 0
    # where D is measured from the zero-pressure point DOWN to the pile tip.
    # Coefficients (per Das §18.4, eqs 18.13-18.17):
    term_denom = Kp_Ka * gamma_eff
    A1 = sigma2 / term_denom
    A2 = 8 * P_total / term_denom
    A3 = 6 * P_total * (2 * z_bar * term_denom + sigma2) / (term_denom ** 2)
    A4 = (P_total * (6 * z_bar * sigma2 + 4 * P_total)) / (term_denom ** 2)

    # Solve D^4 + A1 D^3 − A2 D^2 − A3 D − A4 = 0
    D_below_zero = _solve_quartic((1.0, A1, -A2, -A3, -A4))
    # Total required embedment below the dredge line:
    D_theoretical = L3 + D_below_zero
    # Das recommends 20-30% additional safety on D (p. 762). Use 1.30.
    D_design = D_theoretical * 1.30

    # Maximum moment occurs at the depth of zero shear inside the wall.
    # Below the dredge line, the net pressure at depth z from the dredge line is:
    #   sigma_net(z) = (Kp - Ka) · γ' · z - sigma2     (positive = passive net resisting)
    # Zero shear is where the area of the positive passive diagram (from dredge to z)
    # equals the total active force P above. Solve:
    #   P = 0.5 · (Kp-Ka)·γ' · z^2                (after subtracting the balancing active triangle)
    # In the standard Das formulation (Eq. 18.19), z' = sqrt(2·P / [(Kp-Ka)·γ']).
    z_shear_zero = math.sqrt(2 * P_total / term_denom) if term_denom > 0 else 0.0
    # Maximum moment (Das Eq. 18.21):
    #   M_max = P · (z' + z_bar) − 0.5 · (Kp-Ka) · γ' · z'^3 / 3
    M_max = P_total * (z_shear_zero + z_bar) - (Kp_Ka * gamma_eff * z_shear_zero ** 3) / 6.0

    # Required section modulus per unit run of wall (Das Eq. 18.22):
    #   S = M_max / σ_allow
    # Result units: kN·m/m ÷ kPa = m³/m.
    S_req = M_max / sigma_allow if sigma_allow > 0 else 0.0
    # Convert to cm³/m for easier comparison against PZ / AZ catalog sections
    S_req_cm3_per_m = S_req * 1e6

    # Build HTML report
    r = '<div>'
    r += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 8px;">'
        'Ref: Das &amp; Sivakugan (2019, 9th SI) <strong>&sect;18.4 Cantilever Sheet '
        'Piling Penetrating Sandy Soil</strong>, <strong>pp.&nbsp;758&ndash;764</strong>, '
        'Eq.&nbsp;18.11&ndash;18.22. This build models a homogeneous sand profile only; '
        'clay and layered cases (Das &sect;18.6, &sect;18.10) are deferred. Poulos &amp; '
        'Davis (1980) Ch.&nbsp;7 is the authoritative reference for laterally loaded '
        'single piles and provides the theoretical backdrop for the earth-pressure '
        'assumptions used here.</p>'
    )
    r += '<h4>Rankine Coefficients</h4>'
    r += f'\\[ K_a = \\tfrac{{1-\\sin\\phi}}{{1+\\sin\\phi}} = {_f(Ka,4)} \\]'
    r += f'\\[ K_p = \\tfrac{{1+\\sin\\phi}}{{1-\\sin\\phi}} = {_f(Kp,4)} \\]'
    r += f'\\[ K_p - K_a = {_f(Kp_Ka,4)} \\]'

    r += '<h4>Effective Unit Weight (below water table)</h4>'
    r += (
        f'\\[ \\gamma\' = \\gamma_{{sat}} - \\gamma_w = {_f(gamma_sat,2)} - {GAMMA_W} '
        f'= {_f(gamma_eff,2)} \\text{{ kN/m}}^3 \\]'
    )

    r += '<h4>Active Pressure at Key Levels (Das Eq. 18.7-18.10, pp. 758-760)</h4>'
    r += (
        f'\\[ \\sigma_1\' = K_a \\gamma (L_1 + h_q) = {_f(Ka,4)} \\times {_f(gamma,2)} '
        f'\\times ({_f(L1_used,2)} + {_f(h_q_equiv,2)}) = {_f(sigma1,2)} \\text{{ kPa}} \\]'
    )
    r += (
        f'\\[ \\sigma_2\' = \\sigma_1\' + K_a \\gamma\' L_2 = {_f(sigma1,2)} + {_f(Ka,4)} '
        f'\\times {_f(gamma_eff,2)} \\times {_f(L2,2)} = {_f(sigma2,2)} \\text{{ kPa}} \\]'
    )

    r += '<h4>Depth L3 Below Dredge Line to Point of Zero Net Pressure</h4>'
    r += (
        f'\\[ L_3 = \\frac{{\\sigma_2\'}}{{(K_p - K_a)\\gamma\'}} = '
        f'\\frac{{{_f(sigma2,2)}}}{{{_f(Kp_Ka,4)} \\times {_f(gamma_eff,2)}}} = '
        f'{_f(L3,3)} \\text{{ m}} \\]'
    )

    r += '<h4>Resultant Active Force P and Centroid z-bar</h4>'
    r += f'\\[ P = P_1 + P_2 + P_3 + P_4 = {_f(P_total,2)} \\text{{ kN/m}} \\]'
    r += f'\\[ \\bar{{z}} = {_f(z_bar,3)} \\text{{ m (from the zero-pressure point)}} \\]'

    r += '<h4>Embedment Depth (Das Eq. 18.17)</h4>'
    r += (
        '\\[ D^4 + A_1 D^3 - A_2 D^2 - A_3 D - A_4 = 0 \\]'
        f'\\[ A_1 = {_f(A1,3)}, \\quad A_2 = {_f(A2,3)}, \\quad A_3 = {_f(A3,3)}, '
        f'\\quad A_4 = {_f(A4,3)} \\]'
        f'\\[ D = {_f(D_below_zero,3)} \\text{{ m (below zero-pressure point)}} \\]'
        f'\\[ D_{{theoretical}} = L_3 + D = {_f(D_theoretical,3)} \\text{{ m (below dredge line)}} \\]'
    )
    r += (
        f'<p><strong>Design embedment</strong> (30% safety per Das p.&nbsp;762): '
        f'D<sub>design</sub> = 1.30 &times; D<sub>theoretical</sub> = '
        f'<strong>{_f(D_design,2)} m</strong></p>'
    )

    r += '<h4>Maximum Bending Moment (Das Eq. 18.19-18.21, p. 763)</h4>'
    r += (
        f'\\[ z\' = \\sqrt{{\\frac{{2P}}{{(K_p - K_a)\\gamma\'}}}} = '
        f'{_f(z_shear_zero,3)} \\text{{ m (depth of zero shear below dredge line)}} \\]'
    )
    r += (
        f'\\[ M_{{max}} = P(z\' + \\bar{{z}}) - \\tfrac{{1}}{{6}}(K_p-K_a)\\gamma\' z\'^3 = '
        f'{_f(M_max,2)} \\text{{ kN}}\\cdot\\text{{m/m}} \\]'
    )

    r += '<h4>Required Section Modulus (Das Eq. 18.22, p. 764)</h4>'
    r += (
        f'\\[ S_{{req}} = \\frac{{M_{{max}}}}{{\\sigma_{{allow}}}} = '
        f'\\frac{{{_f(M_max,2)}}}{{{_f(sigma_allow,0)}}} = {_f(S_req,6)} \\text{{ m}}^3/\\text{{m}} '
        f'= {_f(S_req_cm3_per_m,1)} \\text{{ cm}}^3/\\text{{m}} \\]'
    )

    r += '</div>'

    # Plotly pressure diagram
    chart = _build_pressure_chart(
        L, L1_used, L2, L3, D_design,
        sigma1, sigma2,
        Kp_Ka, gamma_eff,
    )

    return {
        'report': r,
        'Ka': Ka,
        'Kp': Kp,
        'L3': L3,
        'D_theoretical': D_theoretical,
        'D_design': D_design,
        'M_max': M_max,
        'S_req': S_req,
        'S_req_cm3_per_m': S_req_cm3_per_m,
        'chart_traces': chart['traces'],
        'chart_layout': chart['layout'],
    }


def _build_pressure_chart(L, L1, L2, L3, D_design, sigma1, sigma2, Kp_Ka, gamma_eff):
    """Pressure diagram: active on the left (above and below the dredge line)
    and passive-net on the right from the dredge line down to the pile tip.
    """
    # y = 0 at top of wall, positive downward (Plotly y-axis is reversed below)
    # We plot with y measured from the top of wall; "depth below dredge line"
    # is y - L.
    top = 0.0
    wt_y = L1
    dredge_y = L
    zero_press_y = L + L3
    tip_y = L + D_design

    # Active pressure polygon
    active_x = [0, -0]  # placeholder; we build a closed polygon below
    # Build the active profile: 0 at top, sigma1 at WT, sigma2 at dredge line,
    # then linear to zero at zero-pressure point, then linearly INCREASING
    # into "net active" region (which becomes negative in Das sign convention).
    active_poly_x = [0, 0, -sigma1, -sigma2, -(sigma2 + Kp_Ka * gamma_eff * (D_design - L3) * 0.4), 0]
    # Simpler: draw a cleaner trapezoid and triangle set that matches Das Fig. 18.11
    active_above_x = [0, -sigma1, -sigma2, 0]
    active_above_y = [top, wt_y, dredge_y, dredge_y]

    # From dredge line down to the zero-pressure point, net active stays positive (leftward)
    active_below_x = [0, -sigma2, 0, 0]
    active_below_y = [dredge_y, dredge_y, zero_press_y, dredge_y]

    # Passive net pressure diagram: from the zero-pressure point down to the pile tip,
    # the net pressure (Kp - Ka)·γ'·z - sigma2 grows linearly; the max at D_design below dredge
    sigma_passive_max = Kp_Ka * gamma_eff * (D_design - L3)
    passive_x = [0, sigma_passive_max, 0, 0]
    passive_y = [zero_press_y, tip_y, tip_y, zero_press_y]

    traces = []
    # Wall line (solid vertical)
    traces.append({
        'x': [0, 0], 'y': [top, tip_y],
        'mode': 'lines', 'line': {'color': '#333', 'width': 3},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Dredge line (horizontal dashed)
    scale = max(sigma2, sigma_passive_max, 1.0)
    traces.append({
        'x': [-1.2 * scale, 1.2 * scale], 'y': [dredge_y, dredge_y],
        'mode': 'lines', 'line': {'color': '#8b6914', 'width': 1.5, 'dash': 'dash'},
        'showlegend': False, 'hoverinfo': 'skip',
    })
    # Water table (horizontal dotted blue) if within wall
    if L1 > 0 and L1 < L:
        traces.append({
            'x': [-1.2 * scale, 1.2 * scale], 'y': [wt_y, wt_y],
            'mode': 'lines', 'line': {'color': '#3498db', 'width': 1.2, 'dash': 'dot'},
            'showlegend': False, 'hoverinfo': 'skip',
        })
    # Active pressure above dredge
    traces.append({
        'x': active_above_x, 'y': active_above_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(231,76,60,0.25)',
        'line': {'color': '#c0392b', 'width': 2},
        'name': 'Active (above dredge)',
    })
    # Active net below dredge down to L3
    traces.append({
        'x': active_below_x, 'y': active_below_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(231,76,60,0.15)',
        'line': {'color': '#c0392b', 'width': 2, 'dash': 'dot'},
        'name': 'Net active (below dredge)',
    })
    # Passive net below the zero-pressure point
    traces.append({
        'x': passive_x, 'y': passive_y,
        'mode': 'lines', 'fill': 'toself',
        'fillcolor': 'rgba(52,152,219,0.30)',
        'line': {'color': '#2980b9', 'width': 2},
        'name': 'Net passive',
    })

    ann = [
        {'x': -0.02 * scale, 'y': top, 'text': 'Top of wall',
         'showarrow': False, 'font': {'size': 10, 'color': '#333'}, 'xanchor': 'right'},
        {'x': -0.02 * scale, 'y': dredge_y, 'text': f'Dredge line (L = {L:.2f} m)',
         'showarrow': False, 'font': {'size': 10, 'color': '#8b6914'}, 'xanchor': 'right'},
        {'x': 0.02 * scale, 'y': zero_press_y, 'text': f'Zero net pressure (L3 = {L3:.2f} m)',
         'showarrow': False, 'font': {'size': 9, 'color': '#2980b9'}, 'xanchor': 'left'},
        {'x': 0.02 * scale, 'y': tip_y, 'text': f'Tip (D = {D_design:.2f} m)',
         'showarrow': False, 'font': {'size': 10, 'color': '#2980b9'}, 'xanchor': 'left'},
    ]
    if L1 > 0 and L1 < L:
        ann.append({
            'x': -0.02 * scale, 'y': wt_y, 'text': f'Water table (L1 = {L1:.2f} m)',
            'showarrow': False, 'font': {'size': 9, 'color': '#3498db'}, 'xanchor': 'right',
        })

    layout = {
        'title': {'text': 'Cantilever Sheet-Pile Pressure Diagram (Das Fig. 18.11)', 'font': {'size': 13}},
        'xaxis': {'title': 'Net lateral pressure (kPa)', 'zeroline': True,
                  'range': [-1.3 * scale, 1.3 * scale]},
        'yaxis': {'title': 'Depth below top of wall (m)', 'autorange': 'reversed'},
        'height': 500,
        'margin': {'l': 70, 'r': 20, 't': 50, 'b': 60},
        'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'annotations': ann,
        'legend': {'orientation': 'h', 'x': 0.5, 'y': -0.15, 'xanchor': 'center'},
    }
    return {'traces': traces, 'layout': layout}
