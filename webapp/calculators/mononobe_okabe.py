"""Mononobe-Okabe seismic earth pressure calculation.

References
----------
- Das, B.M. & Sivakugan, N. (2019). Principles of Foundation Engineering,
  9th Edition SI. §16.3 Rankine active (p. 644), §16.7 Coulomb active (p. 658),
  §16.8 Lateral earth pressure due to surcharge (p. 665), §16.9 Active earth
  pressure for earthquake conditions — granular backfill (p. 668), §16.10
  Active earth pressure for earthquake condition, vertical back / c'-φ'
  backfill (p. 672).
- Mononobe, N. & Matsuo, H. (1929). Proc. World Engineering Conference, Tokyo.
- Okabe, S. (1926). J. Japan Society of Civil Engineers, 12(1).
- Seed, H.B. & Whitman, R.V. (1970). ASCE Specialty Conf., 103-147.
- Kramer, S.L. (1996). Geotechnical Earthquake Engineering, Ch. 11. Prentice-Hall.
"""
import math

DEG = math.pi / 180


def _f(v, d=3):
    return f"{v:.{d}f}"


def calculate(soil_weight, h_wall, alpha, phi, beta, delta, kh, kv, cohesion=0.0):
    """Compute Mononobe-Okabe seismic earth pressure on a retaining wall.

    Parameters
    ----------
    soil_weight : float
        Unit weight of backfill soil γ (kN/m³).
    h_wall : float
        Wall height H (m).
    alpha : float
        Angle of backfill slope from horizontal (degrees).
    phi : float
        Soil friction angle φ (degrees).
    beta : float
        Angle of wall back face from horizontal (degrees). 90 = vertical back.
    delta : float
        Wall-soil friction angle δ (degrees).
    kh, kv : float
        Effective horizontal / vertical seismic coefficients (already include
        any PGA reduction factor). Ref: AASHTO §11.6.5.2.
    cohesion : float, optional
        Effective cohesion c' of backfill (kPa). Applies the Das §16.10
        c'-φ' correction when α = 0 and β = 90°. Ignored otherwise (with
        a disclaimer in the report) because the seismic c'-φ' closed-form
        is only valid for the simple vertical-back / horizontal-surface case.

    Returns
    -------
    dict with 'results' (list of HTML strings), 'cross_section' (textbook
    wall + pressure diagram), 'force_polygon' (failure wedge with force
    vectors), and back-compat aliases 'chart_traces' / 'chart_layout'
    pointing to the cross section for existing templates that still use
    the single-chart pattern.
    """
    g = soil_weight
    H = h_wall
    a = alpha
    ph = phi
    b = beta
    d = delta
    c_prime = cohesion or 0.0

    results = []

    # Effective seismic coefficients (already include any reduction factor on PGA)
    kh_val = kh
    kv_val = kv
    results.append(
        f"<h4>Seismic Parameters</h4>"
        f'<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        f'Ref: Das &amp; Sivakugan &sect;16.9, <strong>p.&nbsp;668</strong> '
        f'(earthquake active pressure &mdash; granular backfill); AASHTO LRFD &sect;11.6.5.2.</p>'
        f"\\[ k_h = {_f(kh_val)} \\quad k_v = {_f(kv_val)} \\]"
    )

    # Inclination angle theta = arctan(kh / (1 - kv))
    theta_rad = math.atan(kh_val / (1 - kv_val))
    theta = math.degrees(theta_rad)
    results.append(
        f"<h4>Inclination Angle</h4>"
        f"\\[ \\theta = \\arctan\\left(\\frac{{k_h}}{{1-k_v}}\\right) = "
        f"\\arctan\\left(\\frac{{{_f(kh_val)}}}{{{_f(1-kv_val)}}}\\right) = {_f(theta)}^\\circ \\]"
    )

    # Ko
    ko = 1 - math.sin(ph * DEG)
    results.append(
        f"<h4>At-Rest Earth Pressure Coefficient</h4>"
        f'<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        f'Ref: Jaky (1944); Das &amp; Sivakugan &sect;16.2 Eq.&nbsp;16.3, '
        f'<strong>p.&nbsp;640</strong>.</p>'
        f"\\[ K_0 = 1 - \\sin\\phi = 1 - \\sin({ph}^\\circ) = {_f(ko, 4)} \\]"
    )

    # Ka (static active - Coulomb)
    ka_num = math.sin((b + ph) * DEG) ** 2
    ka_den = (math.sin(b * DEG) * math.sin((b - d) * DEG) *
              (1 + math.sqrt(math.sin((ph + d) * DEG) * math.sin((ph - a) * DEG) /
                             (math.sin((b - d) * DEG) * math.sin((b + a) * DEG)))) ** 2)
    ka = ka_num / ka_den
    results.append(
        f"<h4>Static Active Pressure Coefficient (Coulomb)</h4>"
        f'<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        f'Ref: Coulomb (1776); Das &amp; Sivakugan &sect;16.7 Eq.&nbsp;16.26, '
        f'<strong>p.&nbsp;658</strong>.</p>'
        f"\\[ K_a = \\frac{{\\sin^2(\\beta+\\phi)}}{{\\sin\\beta\\sin(\\beta-\\delta)"
        f"\\left[1+\\sqrt{{\\frac{{\\sin(\\phi+\\delta)\\sin(\\phi-\\alpha)}}"
        f"{{\\sin(\\beta-\\delta)\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(ka, 5)} \\]"
    )

    # Kp (static passive - Coulomb)
    kp_num = math.sin((b - ph) * DEG) ** 2
    kp_inner = 1 - math.sqrt(math.sin((ph + d) * DEG) * math.sin((ph + a) * DEG) /
                              (math.sin((b + d) * DEG) * math.sin((b - a) * DEG)))
    kp_den = math.sin(b * DEG) * math.sin((b + d) * DEG) * kp_inner ** 2
    kp = kp_num / kp_den
    results.append(
        f"<h4>Static Passive Pressure Coefficient (Coulomb)</h4>"
        f"\\[ K_p = \\frac{{\\sin^2(\\beta-\\phi)}}{{\\sin\\beta\\sin(\\beta+\\delta)"
        f"\\left[1-\\sqrt{{\\frac{{\\sin(\\phi+\\delta)\\sin(\\phi+\\alpha)}}"
        f"{{\\sin(\\beta+\\delta)\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(kp, 5)} \\]"
    )

    # Kae (seismic active - Mononobe-Okabe)
    kae_num = math.sin((b + ph - theta) * DEG) ** 2
    kae_den = (math.cos(theta * DEG) * math.sin(b * DEG) * math.sin((b - d - theta) * DEG) *
               (1 + math.sqrt(math.sin((ph + d) * DEG) * math.sin((ph - a - theta) * DEG) /
                              (math.sin((b - d - theta) * DEG) * math.sin((b + a) * DEG)))) ** 2)
    kae = kae_num / kae_den
    results.append(
        f"<h4>Seismic Active Pressure Coefficient (Mononobe-Okabe)</h4>"
        f'<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        f'Ref: Mononobe &amp; Matsuo (1929); Okabe (1926); Das &amp; Sivakugan '
        f'&sect;16.9 Eq.&nbsp;16.38, <strong>p.&nbsp;668</strong>; Kramer (1996) Ch.&nbsp;11.</p>'
        f"\\[ K_{{ae}} = \\frac{{\\sin^2(\\beta+\\phi-\\theta)}}{{\\cos\\theta\\sin\\beta"
        f"\\sin(\\beta-\\delta-\\theta)\\left[1+\\sqrt{{\\frac{{\\sin(\\phi+\\delta)"
        f"\\sin(\\phi-\\alpha-\\theta)}}{{\\sin(\\beta-\\delta-\\theta)"
        f"\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(kae, 5)} \\]"
    )

    # Delta Ka
    dKa = kae * (1 - kv_val) - ka
    results.append(
        f"<h4>Dynamic Increment</h4>"
        f"\\[ \\Delta K_a = K_{{ae}}(1-k_v) - K_a = {_f(dKa, 5)} \\]"
    )

    # Total static and seismic lateral force (granular default, c'=0)
    Pa_static = 0.5 * g * H * H * ka
    Pa_seismic = 0.5 * g * H * H * kae

    # c'-φ' correction per Das §16.10, p. 672.
    # Only applicable when wall back is vertical (β = 90°) and surface is
    # horizontal (α = 0). Apply the seismic generalization of the classical
    # cohesive-soil closed-form (Rankine-type).
    c_applicable = (c_prime > 0 and abs(a) < 1e-6 and abs(b - 90) < 1e-6)
    if c_prime > 0:
        if c_applicable:
            sqrt_kae = math.sqrt(kae)
            z_crack = 2 * c_prime / (g * sqrt_kae) if g > 0 else 0.0
            z_crack = min(max(z_crack, 0.0), H)
            # Das Eq. 16.44 analog (generalized from 16.24 static case):
            Pae_cphi = 0.5 * g * H * H * kae - 2 * c_prime * H * sqrt_kae + (2 * c_prime ** 2) / g
            Pae_cphi = max(Pae_cphi, 0.0)
            results.append(
                f"<h4>Cohesion Correction (Das &sect;16.10, p.&nbsp;672)</h4>"
                f'<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
                f'Applying the c\'-&phi;\' seismic extension from Das &sect;16.10, '
                f'<strong>p.&nbsp;672</strong>. Valid for vertical wall back '
                f'(&beta;&nbsp;=&nbsp;90&deg;) and horizontal surface (&alpha;&nbsp;=&nbsp;0).</p>'
                f"\\[ \\sigma_{{ae}}(z) = K_{{ae}} \\gamma z - 2 c' \\sqrt{{K_{{ae}}}} \\]"
                f"\\[ z_{{crack}} = \\frac{{2 c'}}{{\\gamma \\sqrt{{K_{{ae}}}}}} = "
                f"\\frac{{2 \\times {_f(c_prime, 2)}}}{{{_f(g, 2)} \\times \\sqrt{{{_f(kae, 4)}}}}} "
                f"= {_f(z_crack, 3)} \\text{{ m}} \\]"
                f"\\[ P_{{ae,c'\\phi'}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_{{ae}} "
                f"- 2 c' H \\sqrt{{K_{{ae}}}} + \\frac{{2 {{c'}}^2}}{{\\gamma}} "
                f"= {_f(Pae_cphi, 2)} \\text{{ kN/m}} \\]"
            )
            Pa_seismic_reported = Pae_cphi
        else:
            results.append(
                '<h4>Cohesion Correction (Das &sect;16.10, p.&nbsp;672)</h4>'
                '<p style="color:#b7791f;font-size:0.9em;"><em>c\'-&phi;\' seismic correction '
                'from Das &sect;16.10 is only valid for vertical wall back '
                '(&beta;&nbsp;=&nbsp;90&deg;) and horizontal backfill (&alpha;&nbsp;=&nbsp;0). '
                f'Current inputs: &alpha; = {_f(a,1)}&deg;, &beta; = {_f(b,1)}&deg;. '
                'Falling back to granular formulation (c\' ignored).</em></p>'
            )
            z_crack = 0.0
            Pa_seismic_reported = Pa_seismic
    else:
        z_crack = 0.0
        Pa_seismic_reported = Pa_seismic

    results.append(
        f"<h4>Earth Pressure Forces (per unit length)</h4>"
        f"\\[ P_{{a,static}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_a = {_f(Pa_static, 2)} \\text{{ kN/m}} \\]"
        f"\\[ P_{{a,seismic}} = {_f(Pa_seismic_reported, 2)} \\text{{ kN/m}} \\]"
    )

    # Build textbook-style cross section and force polygon
    cross_section = _build_cross_section(
        H, g, ka, kae, a, b, theta, Pa_static, Pa_seismic_reported,
        c_prime if c_applicable else 0.0, z_crack
    )
    force_polygon = _build_force_polygon(
        H, g, a, b, ph, theta, kh_val, kv_val, Pa_seismic_reported
    )

    return {
        "results": results,
        "cross_section": cross_section,
        "force_polygon": force_polygon,
        # Back-compat aliases for any template still using the old single-chart API
        "chart_traces": cross_section["traces"],
        "chart_layout": cross_section["layout"],
    }


# ---------------------------------------------------------------------------
# Textbook-style plot builders
# ---------------------------------------------------------------------------

def _build_cross_section(H, g, ka, kae, alpha, beta, theta, Pa_static, Pa_seismic,
                         c_prime, z_crack):
    """Wall cross-section with static and seismic pressure triangles.

    Styled after Das Fig. 16.23 / Kramer Fig. 11.1: wall polygon (concrete
    gray), backfill (tan), static active pressure (dashed blue), seismic
    active pressure (solid red), resultant force arrows and annotations
    for H, α, β, θ, Pa, Pae.
    """
    # Wall geometry: place the wall back face at x=0, vertical for β=90.
    # The backfill extends to the right of the wall.
    # For visual consistency we draw the wall with a fixed stem thickness.
    t_stem = 0.08 * H
    beta_rad = beta * DEG
    alpha_rad = alpha * DEG

    # Wall back (top-right corner) and bottom
    # If β=90, back face is vertical. Otherwise we skew slightly.
    dx_top = H / math.tan(beta_rad) if abs(beta - 90) > 0.5 else 0.0
    x_back_top = dx_top
    x_back_bot = 0.0
    x_front_top = dx_top + t_stem
    x_front_bot = t_stem

    # Wall polygon (concrete)
    wall_x = [x_back_bot, x_front_bot, x_front_top, x_back_top, x_back_bot]
    wall_y = [0, 0, H, H, 0]

    # Backfill polygon: right of wall back face, sloping up at angle α
    # Extend the backfill about 1.2H to the right
    bf_len = 1.4 * H
    bf_x = [
        x_back_bot, x_back_bot + bf_len,
        x_back_bot + bf_len, x_back_top,
    ]
    bf_y = [
        0, 0,
        bf_len * math.tan(alpha_rad) + 0.0, H,
    ]

    # Static active pressure triangle (dashed blue), drawn as a sub-figure to the
    # LEFT of the wall (negative x), oriented horizontally. Max pressure at base.
    sigma_static_max = g * H * ka
    sigma_seismic_max = g * H * kae
    # If cohesion applicable, subtract the 2c'√Kae offset at all depths
    sigma_seismic_top = -2 * c_prime * math.sqrt(kae) if c_prime > 0 else 0.0
    # But we only draw the pressure where σ > 0 (below z_crack)
    p_scale_x = 0.40 * H / max(sigma_seismic_max, sigma_static_max, 1.0)
    offset_x = -0.05 * H  # push the pressure diagrams slightly left of the wall
    # Static triangle vertices (in "plot" coords)
    stat_tri_x = [offset_x, offset_x - sigma_static_max * p_scale_x, offset_x]
    stat_tri_y = [H, 0, 0]
    # Seismic triangle vertices — for granular, a triangle; for c'-φ', a trapezoid
    # starting at z_crack.
    if c_prime > 0 and z_crack > 0:
        z_c_from_top = min(z_crack, H)
        # Pressure at base = σ_seismic_max + σ_seismic_top (top is negative)
        sig_base = sigma_seismic_max + sigma_seismic_top
        sig_base = max(sig_base, 0.0)
        seis_x = [
            offset_x, offset_x - sig_base * p_scale_x,
            offset_x, offset_x,
        ]
        seis_y = [
            H - z_c_from_top, 0,
            0, H - z_c_from_top,
        ]
    else:
        seis_x = [offset_x, offset_x - sigma_seismic_max * p_scale_x, offset_x]
        seis_y = [H, 0, 0]

    traces = []

    # Backfill soil (tan) — draw first so wall covers the interior
    traces.append({
        "x": bf_x, "y": bf_y,
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(194,178,128,0.35)",
        "line": {"color": "rgba(160,145,95,0.7)", "width": 1},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Add diagonal hatch lines inside the backfill for a textbook feel
    for i in range(6):
        y0 = H * (i + 1) / 6
        xstart = x_back_bot + bf_len * (i + 1) / 7
        xend = xstart + 0.10 * H
        traces.append({
            "x": [xstart, xend], "y": [y0 - 0.06 * H, y0],
            "mode": "lines",
            "line": {"color": "rgba(160,145,95,0.6)", "width": 1},
            "hoverinfo": "skip", "showlegend": False,
        })
    # Wall (concrete gray)
    traces.append({
        "x": wall_x, "y": wall_y,
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(176,176,176,0.7)",
        "line": {"color": "#333", "width": 2},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Ground line under wall
    traces.append({
        "x": [offset_x - 0.5 * H, x_front_bot + bf_len], "y": [0, 0],
        "mode": "lines", "line": {"color": "#333", "width": 1.5},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Static pressure triangle (dashed blue)
    traces.append({
        "x": stat_tri_x, "y": stat_tri_y,
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(52,152,219,0.22)",
        "line": {"color": "#2980b9", "width": 2, "dash": "dash"},
        "hoverinfo": "skip",
        "name": f"Static Pa = {Pa_static:.1f} kN/m",
    })
    # Seismic pressure (solid red)
    traces.append({
        "x": seis_x, "y": seis_y,
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(231,76,60,0.30)",
        "line": {"color": "#c0392b", "width": 2},
        "hoverinfo": "skip",
        "name": f"Seismic Pae = {Pa_seismic:.1f} kN/m",
    })

    # Tension crack line (if c'-φ')
    if c_prime > 0 and z_crack > 0:
        traces.append({
            "x": [offset_x - 0.10 * H, x_back_top + 0.05 * H],
            "y": [H - z_crack, H - z_crack],
            "mode": "lines",
            "line": {"color": "#7f1d1d", "width": 1.5, "dash": "dot"},
            "hoverinfo": "skip", "showlegend": False,
        })

    # Annotations
    ann = []
    # H dimension (left of pressure)
    ann.append({
        "x": offset_x - 0.45 * H, "y": H / 2,
        "text": f"H = {H:.2f} m", "showarrow": False,
        "font": {"size": 11, "color": "#333"}, "xanchor": "right",
    })
    # α (slope) near top of backfill
    ann.append({
        "x": x_back_top + 0.35 * bf_len, "y": H + 0.12 * H,
        "text": f"&alpha; = {alpha:.1f}&deg;", "showarrow": False,
        "font": {"size": 11, "color": "#555"},
    })
    # β (wall back angle) near wall top
    ann.append({
        "x": x_back_top + 0.01 * H, "y": H * 0.08,
        "text": f"&beta; = {beta:.1f}&deg;", "showarrow": False,
        "font": {"size": 11, "color": "#555"}, "xanchor": "left",
    })
    # θ (seismic inclination)
    ann.append({
        "x": x_front_top + 0.08 * H, "y": H * 0.92,
        "text": f"&theta; = {theta:.2f}&deg;", "showarrow": False,
        "font": {"size": 11, "color": "#c0392b"}, "xanchor": "left",
    })
    # Static resultant arrow at H/3
    y_static_resultant = H / 3
    static_arrow_start = offset_x - 0.28 * H
    ann.append({
        "x": x_back_bot - 0.02 * H, "y": y_static_resultant,
        "ax": static_arrow_start, "ay": y_static_resultant,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.5,
        "arrowwidth": 2.5, "arrowcolor": "#2980b9",
    })
    ann.append({
        "x": static_arrow_start - 0.02 * H, "y": y_static_resultant + 0.04 * H,
        "text": f"<b>P<sub>a</sub> = {Pa_static:.1f}</b>", "showarrow": False,
        "font": {"size": 10, "color": "#2980b9"}, "xanchor": "right",
    })
    # Seismic resultant arrow at ~0.6H per Seed & Whitman 1970
    y_seismic_resultant = 0.6 * H
    seismic_arrow_start = offset_x - 0.32 * H
    ann.append({
        "x": x_back_bot - 0.02 * H, "y": y_seismic_resultant,
        "ax": seismic_arrow_start, "ay": y_seismic_resultant,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.5,
        "arrowwidth": 3, "arrowcolor": "#c0392b",
    })
    ann.append({
        "x": seismic_arrow_start - 0.02 * H, "y": y_seismic_resultant + 0.04 * H,
        "text": f"<b>P<sub>ae</sub> = {Pa_seismic:.1f}</b>", "showarrow": False,
        "font": {"size": 10, "color": "#c0392b"}, "xanchor": "right",
    })
    # Tension crack label
    if c_prime > 0 and z_crack > 0:
        ann.append({
            "x": offset_x - 0.02 * H, "y": H - z_crack,
            "text": f"z<sub>crack</sub> = {z_crack:.2f} m", "showarrow": False,
            "font": {"size": 9, "color": "#7f1d1d"}, "xanchor": "right",
        })

    # H/3 label for static
    ann.append({
        "x": static_arrow_start - 0.03 * H, "y": y_static_resultant - 0.08 * H,
        "text": "H/3", "showarrow": False,
        "font": {"size": 9, "color": "#2980b9"}, "xanchor": "right",
    })
    # 0.6H label for seismic
    ann.append({
        "x": seismic_arrow_start - 0.03 * H, "y": y_seismic_resultant + 0.1 * H,
        "text": "0.6H (Seed &amp; Whitman 1970)", "showarrow": False,
        "font": {"size": 9, "color": "#c0392b"}, "xanchor": "right",
    })

    layout = {
        "xaxis": {
            "visible": False, "scaleanchor": "y", "scaleratio": 1,
            "range": [offset_x - 0.95 * H, x_back_bot + bf_len + 0.1 * H],
        },
        "yaxis": {"visible": False, "range": [-0.12 * H, H * 1.35]},
        "margin": {"l": 10, "r": 10, "t": 40, "b": 20},
        "height": 520,
        "plot_bgcolor": "white", "paper_bgcolor": "white",
        "annotations": ann,
        "legend": {"orientation": "h", "x": 0.5, "y": -0.02, "xanchor": "center",
                   "font": {"size": 10}},
        "title": {"text": "Wall Cross-Section &mdash; Static vs. Seismic Active Pressure",
                  "font": {"size": 13}, "x": 0.5},
    }
    return {"traces": traces, "layout": layout}


def _build_force_polygon(H, g, alpha, beta, phi, theta, kh, kv, Pae):
    """Failure-wedge diagram with force polygon (Das Fig. 16.23 / Kramer Fig 11.1).

    Shows the trial wedge inside the backfill at a critical failure angle
    ψa (approximated as 45 - φ/2 + θ/2 for the generalized M-O case),
    together with vectors for W, khW, kvW, Pae, R.
    """
    alpha_rad = alpha * DEG
    phi_rad = phi * DEG
    theta_rad = theta * DEG

    # Critical failure plane angle from horizontal — Das §16.9 gives a closed-form
    # for the static Coulomb case (45 - φ/2). For the M-O generalization we use
    # the simple Seed & Whitman (1970) approximation:
    psi_a = max(45.0 - phi / 2.0 + theta / 2.0, 10.0)
    psi_rad = psi_a * DEG

    # Place wall back face at x=0, from (0,0) to (0,H)
    # Failure plane from (0,0) out at angle psi_a above horizontal to the backfill surface.
    # Intersection of failure plane with backfill top: y = H, so
    # x_fail = H / tan(psi_rad)
    if math.tan(psi_rad) > 1e-6:
        x_fail = H / math.tan(psi_rad)
    else:
        x_fail = 2 * H
    # But the backfill surface slopes at angle α; for small α we ignore that detail
    # and use a horizontal surface at y=H for the polygon diagram.

    wedge_x = [0, x_fail, 0, 0]
    wedge_y = [0, H, H, 0]

    traces = []
    # Backfill reference (light tan)
    traces.append({
        "x": [0, x_fail * 1.4, x_fail * 1.4, 0],
        "y": [0, 0, H, H],
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(194,178,128,0.15)",
        "line": {"color": "rgba(160,145,95,0.4)", "width": 1},
        "showlegend": False, "hoverinfo": "skip",
    })
    # Trial failure wedge (hatched by convention — we use a solid tint)
    traces.append({
        "x": wedge_x, "y": wedge_y,
        "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(194,178,128,0.50)",
        "line": {"color": "#8b6914", "width": 2, "dash": "dash"},
        "showlegend": False, "hoverinfo": "skip",
    })
    # Wall back face (vertical line)
    traces.append({
        "x": [0, 0], "y": [0, H],
        "mode": "lines", "line": {"color": "#333", "width": 3},
        "showlegend": False, "hoverinfo": "skip",
    })
    # Ground
    traces.append({
        "x": [-0.15 * H, x_fail * 1.5], "y": [0, 0],
        "mode": "lines", "line": {"color": "#333", "width": 1.5},
        "showlegend": False, "hoverinfo": "skip",
    })

    # Compute wedge weight
    # Wedge area = 0.5 · x_fail · H
    W_wedge = 0.5 * x_fail * H * g  # kN per m
    # Inertia forces
    khW = kh * W_wedge
    kvW = kv * W_wedge

    # Annotations
    ann = []
    # Failure plane angle label
    ann.append({
        "x": x_fail / 2, "y": H / 2 * 0.3,
        "text": f"&psi;<sub>a</sub> = {psi_a:.1f}&deg;",
        "showarrow": False,
        "font": {"size": 11, "color": "#8b6914"},
    })
    # W (weight) arrow at wedge centroid
    cg_x = x_fail / 3
    cg_y = H / 3
    arrow_len = 0.25 * H
    ann.append({
        "x": cg_x, "y": cg_y - arrow_len,
        "ax": cg_x, "ay": cg_y,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.3,
        "arrowwidth": 2.5, "arrowcolor": "#006400",
    })
    ann.append({
        "x": cg_x, "y": cg_y - arrow_len - 0.06 * H,
        "text": f"<b>W = {W_wedge:.1f}</b>", "showarrow": False,
        "font": {"size": 10, "color": "#006400"},
    })
    # khW (horizontal seismic inertia) — away from wall
    ann.append({
        "x": cg_x + arrow_len, "y": cg_y + 0.08 * H,
        "ax": cg_x, "ay": cg_y + 0.08 * H,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.3,
        "arrowwidth": 2.5, "arrowcolor": "#c0392b",
    })
    ann.append({
        "x": cg_x + arrow_len + 0.04 * H, "y": cg_y + 0.13 * H,
        "text": f"<b>k<sub>h</sub>W = {khW:.1f}</b>", "showarrow": False,
        "font": {"size": 10, "color": "#c0392b"}, "xanchor": "left",
    })
    # Pae acting on the wall (from wedge into wall) at H/3
    ann.append({
        "x": -arrow_len * 0.8, "y": H / 3,
        "ax": 0, "ay": H / 3,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.5,
        "arrowwidth": 3, "arrowcolor": "#2c3e50",
    })
    ann.append({
        "x": -arrow_len * 0.85, "y": H / 3 + 0.05 * H,
        "text": f"<b>P<sub>ae</sub> = {Pae:.1f}</b>", "showarrow": False,
        "font": {"size": 10, "color": "#2c3e50"}, "xanchor": "right",
    })
    # R (reaction on failure plane, at angle φ from normal to plane)
    # For the diagram we just show its direction out of the plane.
    rx0 = x_fail * 0.55
    ry0 = H * 0.55
    # Normal to failure plane is at angle (psi_a - 90) below the plane,
    # and R is at angle φ from that normal toward the soil
    normal_angle = (psi_a - 90) * DEG
    r_angle = normal_angle - phi_rad
    r_len = 0.25 * H
    ann.append({
        "x": rx0 + r_len * math.cos(r_angle),
        "y": ry0 + r_len * math.sin(r_angle),
        "ax": rx0, "ay": ry0,
        "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
        "showarrow": True, "arrowhead": 2, "arrowsize": 1.3,
        "arrowwidth": 2.5, "arrowcolor": "#1f6391",
    })
    ann.append({
        "x": rx0 + (r_len + 0.02 * H) * math.cos(r_angle),
        "y": ry0 + (r_len + 0.02 * H) * math.sin(r_angle),
        "text": "<b>R</b>", "showarrow": False,
        "font": {"size": 10, "color": "#1f6391"},
    })

    layout = {
        "xaxis": {
            "visible": False, "scaleanchor": "y", "scaleratio": 1,
            "range": [-0.6 * H, x_fail * 1.55],
        },
        "yaxis": {"visible": False, "range": [-0.12 * H, H * 1.25]},
        "margin": {"l": 10, "r": 10, "t": 40, "b": 20},
        "height": 520,
        "plot_bgcolor": "white", "paper_bgcolor": "white",
        "annotations": ann,
        "title": {"text": "Trial Failure Wedge &mdash; Pseudo-Static Forces",
                  "font": {"size": 13}, "x": 0.5},
    }
    return {"traces": traces, "layout": layout}
