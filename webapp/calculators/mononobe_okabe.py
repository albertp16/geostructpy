"""Mononobe-Okabe seismic earth pressure calculation.

References
----------
- Das, B.M. & Sivakugan, N. (2019). Principles of Foundation Engineering,
  9th Edition SI. §16.3 Rankine active (p. 644), §16.7 Coulomb active (p. 658),
  §16.8 Lateral earth pressure due to surcharge (p. 665), §16.9 Active earth
  pressure for earthquake conditions — granular backfill (p. 668), §16.10
  Active earth pressure for earthquake condition, vertical back / c'-φ'
  backfill (p. 672), §16.17 Passive force under earthquake conditions.
- Mononobe, N. & Matsuo, H. (1929). Proc. World Engineering Conference, Tokyo.
- Okabe, S. (1926). J. Japan Society of Civil Engineers, 12(1).
- Seed, H.B. & Whitman, R.V. (1970). ASCE Specialty Conf., 103-147.
- Kramer, S.L. (1996). Geotechnical Earthquake Engineering, Ch. 11
  (Eqs. 11.6-11.10: M-O coefficients and Zarrabi-Kashani critical wedge angle).
- Zarrabi-Kashani, K. (1979). Sliding of gravity retaining wall during
  earthquakes. M.S. thesis, MIT. (Closed-form critical failure-surface angle.)
- AASHTO (2020). LRFD Bridge Design Specifications, §11.6.5.
- EN 1998-5:2004 (Eurocode 8 Part 5), Annex E.

Angle conventions (Das sin-form)
--------------------------------
alpha : backfill slope from horizontal (deg)
beta  : wall back face from horizontal (deg); 90 = vertical back
delta : wall-soil friction angle (deg)
theta : seismic inertia angle, arctan(kh / (1 - kv)) (deg)

The Kramer/Zarrabi cos-form quantities map as: wall batter from vertical
theta_w = 90 - beta; backfill slope beta_K = alpha; inertia angle psi = theta.
"""
import math

DEG = math.pi / 180

# ---------------------------------------------------------------------------
# Chart chrome — dataviz reference palette (validated, light surface)
# ---------------------------------------------------------------------------
COL = {
    "static": "#2a78d6",      # series 1 blue  — static active
    "seismic": "#e34948",     # series 6 red   — seismic total
    "increment": "#eb6834",   # series 8 orange — dynamic increment
    "approx": "#1baf7a",      # series 2 aqua  — Seed-Whitman approximation
    "ord_lo": "#86b6ef",      # ordinal blue ramp (phi - 5)
    "ord_mid": "#2a78d6",     # ordinal blue ramp (phi)
    "ord_hi": "#104281",      # ordinal blue ramp (phi + 5)
    "ink": "#0b0b0b",
    "ink2": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "soil_fill": "rgba(194,178,128,0.30)",
    "soil_line": "rgba(150,134,86,0.85)",
    "wall_fill": "rgba(173,178,184,0.55)",
    "wall_line": "#52514e",
    "wedge_line": "#8b6914",
    "good": "#0ca30c",
    "critical": "#d03b3b",
    "W": "#008300",           # weight vector (series 4 green)
    "R": "#4a3aa7",           # reaction vector (series 5 violet)
}
FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _f(v, d=3):
    return f"{v:.{d}f}"


def _base_layout(height=460):
    """Shared Plotly chrome: recessive hairline grid, system sans, light surface."""
    return {
        "font": {"family": FONT_FAMILY, "size": 12, "color": COL["ink2"]},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "height": height,
        "margin": {"l": 56, "r": 16, "t": 24, "b": 48},
        "hoverlabel": {
            "font": {"family": FONT_FAMILY, "size": 12},
            "bgcolor": "#ffffff", "bordercolor": COL["grid"],
        },
    }


def _axis(title=None, visible=True):
    ax = {
        "visible": visible,
        "gridcolor": COL["grid"], "gridwidth": 1,
        "zeroline": False,
        "linecolor": COL["axis"], "linewidth": 1,
        "ticks": "outside", "tickcolor": COL["axis"],
        "tickfont": {"size": 11, "color": COL["muted"]},
    }
    if title:
        ax["title"] = {"text": title, "font": {"size": 12, "color": COL["ink2"]}}
    return ax


# ---------------------------------------------------------------------------
# Earth pressure coefficients (Das sin-form; angles in degrees)
# ---------------------------------------------------------------------------

def coulomb_ka(phi, delta, alpha, beta):
    """Static Coulomb (Müller-Breslau) active coefficient.
    Das §16.7 Eq. 16.26, p. 658. Note the sin²β term (= cos²θw of the
    cos-form); verified against direct wedge equilibrium."""
    s_bd = math.sin((beta - delta) * DEG)
    s_ba = math.sin((beta + alpha) * DEG)
    if s_bd <= 1e-12 or s_ba <= 1e-12:
        return None
    num = math.sin((beta + phi) * DEG) ** 2
    root_arg = (math.sin((phi + delta) * DEG) * math.sin((phi - alpha) * DEG) /
                (s_bd * s_ba))
    if root_arg < 0:
        return None
    den = math.sin(beta * DEG) ** 2 * s_bd * (1 + math.sqrt(root_arg)) ** 2
    if den <= 1e-12:
        return None
    return num / den


def coulomb_kp(phi, delta, alpha, beta):
    """Static Coulomb (Müller-Breslau) passive coefficient. Das §16.13.

    Obtained from the active form by phi -> -phi, delta -> -delta; note the
    geometry term is sin(beta + alpha), same as the active case.
    """
    s_bd = math.sin((beta + delta) * DEG)
    s_ba = math.sin((beta + alpha) * DEG)
    if s_bd <= 1e-12 or s_ba <= 1e-12:
        return None
    num = math.sin((beta - phi) * DEG) ** 2
    root_arg = (math.sin((phi + delta) * DEG) * math.sin((phi + alpha) * DEG) /
                (s_bd * s_ba))
    if root_arg < 0:
        return None
    inner = 1 - math.sqrt(root_arg)
    if inner <= 1e-9:
        return None
    den = math.sin(beta * DEG) ** 2 * s_bd * inner ** 2
    return num / den


def mo_kae(phi, delta, alpha, beta, theta):
    """Mononobe-Okabe seismic active coefficient. Das §16.9 Eq. 16.38, p. 668.

    Returns None when the sqrt argument is negative, i.e. outside the M-O
    validity domain phi - alpha - theta >= 0.
    """
    if phi - alpha - theta < 0:
        return None
    s_bdt = math.sin((beta - delta - theta) * DEG)
    s_ba = math.sin((beta + alpha) * DEG)
    if s_bdt <= 1e-12 or s_ba <= 1e-12:
        return None
    num = math.sin((beta + phi - theta) * DEG) ** 2
    root_arg = (math.sin((phi + delta) * DEG) * math.sin((phi - alpha - theta) * DEG) /
                (s_bdt * s_ba))
    if root_arg < 0:
        return None
    den = (math.cos(theta * DEG) * math.sin(beta * DEG) ** 2 * s_bdt *
           (1 + math.sqrt(root_arg)) ** 2)
    if den <= 1e-12:
        return None
    return num / den


def mo_kpe(phi, delta, alpha, beta, theta):
    """M-O seismic passive coefficient. Kramer (1996) Eq. 11.10 (cos-form);
    Das §16.17. Mapped via wall batter theta_w = 90 - beta, slope = alpha."""
    tw = 90.0 - beta        # wall batter from vertical
    a = alpha
    ps = theta
    c_dtp = math.cos((delta - tw + ps) * DEG)
    c_atw = math.cos((a - tw) * DEG)
    if c_dtp <= 1e-12 or c_atw <= 1e-12:
        return None
    root_arg = (math.sin((phi + delta) * DEG) * math.sin((phi + a - ps) * DEG) /
                (c_dtp * c_atw))
    if root_arg < 0:
        return None
    inner = 1 - math.sqrt(root_arg)
    if inner <= 1e-9:
        return None
    num = math.cos((phi + tw - ps) * DEG) ** 2
    den = (math.cos(ps * DEG) * math.cos(tw * DEG) ** 2 * c_dtp * inner ** 2)
    if den <= 1e-12:
        return None
    return num / den


def critical_wedge_angle(phi, delta, alpha, beta, theta):
    """Critical (thrust-maximizing) failure-surface angle from horizontal.

    Zarrabi-Kashani (1979) closed form; Kramer (1996) Eq. 11.6 notation:
      alpha_AE = phi - psi + arctan[(-tan(phi-psi-b) + C1E) / C2E]
    with b = backfill slope, theta_w = wall batter from vertical, psi = theta.
    Static Coulomb limit (psi=0, vertical wall, level fill): 45 + phi/2.
    Returns None outside the validity domain.
    """
    tw = 90.0 - beta
    b = alpha
    ps = theta
    A = (phi - ps - b) * DEG      # tan argument
    B = (phi - ps - tw) * DEG     # cot argument
    if A < 0 or math.sin(B) <= 0:
        return None
    tanA = math.tan(A)
    cotB = math.cos(B) / math.sin(B)
    tanD = math.tan((delta + ps + tw) * DEG)
    arg = tanA * (tanA + cotB) * (1 + tanD * cotB)
    if arg < 0:
        return None
    c1e = math.sqrt(arg)
    c2e = 1 + tanD * (tanA + cotB)
    return phi - ps + math.degrees(math.atan((-tanA + c1e) / c2e))


# ---------------------------------------------------------------------------
# Critical-wedge geometry and force equilibrium (exact, per unit length)
# ---------------------------------------------------------------------------

def _wedge_geometry(H, alpha, beta, rho):
    """Vertices of the trial wedge for failure plane at angle rho (deg, from
    horizontal), heel at origin, backfill on +x. Returns (crest, apex, area)
    or None if the plane never intersects the ground surface.

    Das convention: beta is measured at the heel from the horizontal in front
    of the wall, so the crest sits at x_t = -H/tan(beta) — for beta < 90 the
    soil rests on the inclined back face (crest away from the backfill).
    """
    a_r = alpha * DEG
    r_r = rho * DEG
    x_t = -H / math.tan(beta * DEG) if abs(beta - 90) > 1e-9 else 0.0
    denom = math.sin(r_r) - math.cos(r_r) * math.tan(a_r)
    if denom <= 1e-12:
        return None
    t = (H - x_t * math.tan(a_r)) / denom
    if t <= 0:
        return None
    xi, yi = t * math.cos(r_r), t * math.sin(r_r)
    # Shoelace for triangle (0,0), (xi,yi), (x_t,H)
    area = 0.5 * abs(xi * H - x_t * yi)
    return (x_t, H), (xi, yi), area


def _wedge_equilibrium(H, gamma, alpha, beta, phi, delta, rho, kh, kv):
    """Solve pseudo-static equilibrium of the trial wedge for (P, R, W).

    Force directions (x into backfill, y up):
      W_eff = (0, -(1-kv) W);  inertia = (-kh W, 0)
      R (from soil below plane) along (-sin(rho-phi), cos(rho-phi))
      P (from wall on wedge)   along (sin(b-d), cos(b-d)):
        face up-vector u = (-cos b, sin b), soil-side normal n_w = (sin b, cos b),
        p_dir = n_w cos d + u sin d.
    Returns (P, R, W) or None.
    """
    geom = _wedge_geometry(H, alpha, beta, rho)
    if geom is None:
        return None
    _, _, area = geom
    W = gamma * area
    r_dir = (-math.sin((rho - phi) * DEG), math.cos((rho - phi) * DEG))
    p_dir = (math.sin((beta - delta) * DEG), math.cos((beta - delta) * DEG))
    # R*r + P*p = (kh W, (1-kv) W)
    rhs = (kh * W, (1 - kv) * W)
    det = r_dir[0] * p_dir[1] - r_dir[1] * p_dir[0]
    if abs(det) < 1e-12:
        return None
    R = (rhs[0] * p_dir[1] - rhs[1] * p_dir[0]) / det
    P = (r_dir[0] * rhs[1] - r_dir[1] * rhs[0]) / det
    return P, R, W


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def calculate(soil_weight, h_wall, alpha, phi, beta, delta, kh, kv, cohesion=0.0):
    """Compute the Mononobe-Okabe seismic earth pressure report.

    Parameters
    ----------
    soil_weight : float   Unit weight of backfill γ (kN/m³).
    h_wall : float        Wall height H (m).
    alpha : float         Backfill slope from horizontal (deg).
    phi : float           Soil friction angle φ' (deg).
    beta : float          Wall back face from horizontal (deg); 90 = vertical.
    delta : float         Wall-soil friction angle δ (deg).
    kh, kv : float        Effective pseudo-static coefficients (PGA reduction
                          already applied). Ref: AASHTO §11.6.5.2.
    cohesion : float      Effective cohesion c' (kPa); Das §16.10 correction
                          applied only for α = 0, β = 90°.

    Returns
    -------
    dict with 'results' (list of HTML report sections), 'summary' (key values
    for the UI cards), 'figures' (cross_section / force_polygon / sensitivity
    / pressure_dist Plotly dicts), and back-compat aliases 'cross_section',
    'force_polygon', 'chart_traces', 'chart_layout'.
    """
    g = float(soil_weight)
    H = float(h_wall)
    a = float(alpha)
    ph = float(phi)
    b = float(beta)
    d = float(delta)
    kh_val = float(kh)
    kv_val = float(kv)
    c_prime = float(cohesion or 0.0)

    results = []
    warnings = []

    # -- 0. Input validation --------------------------------------------------
    if kv_val >= 1:
        raise ValueError(
            f"k_v = {kv_val:g} >= 1 means the upward inertia exceeds gravity; "
            f"the pseudo-static M-O formulation is undefined. Use k_v < 1 "
            f"(typically 0 to 2/3 of k_h).")
    if H <= 0 or g <= 0:
        raise ValueError("Wall height H and unit weight gamma must be positive.")

    # -- 1. Seismic coefficients, inertia angle, validity ------------------
    theta_rad = math.atan2(kh_val, 1 - kv_val)
    theta = math.degrees(theta_rad)
    kh_limit = (1 - kv_val) * math.tan((ph - a) * DEG) if ph > a else 0.0
    mo_valid = (ph - a - theta) >= -1e-9
    theta_used = theta
    if not mo_valid:
        # Fluidized-backfill limit: clamp theta to (phi - alpha) so the report
        # still produces the limiting equilibrium value, with a hard warning.
        theta_used = ph - a
        warnings.append(
            f"M-O validity limit exceeded: &phi; &minus; &alpha; &minus; &theta; = "
            f"{_f(ph - a - theta, 2)}&deg; &lt; 0. The M-O square root is undefined "
            f"(backfill is at the pseudo-static fluidization limit). Coefficients are "
            f"reported at the limiting inertia angle &theta;<sub>lim</sub> = "
            f"{_f(theta_used, 2)}&deg;, i.e. k<sub>h,lim</sub> = {_f(kh_limit, 3)}. "
            f"Reduce k<sub>h</sub>, flatten the backfill slope, or use a "
            f"displacement-based method (e.g. Richards-Elms / Newmark)."
        )
    if d > ph:
        warnings.append(
            f"&delta; = {_f(d, 1)}&deg; exceeds &phi; = {_f(ph, 1)}&deg;; "
            f"wall friction cannot exceed soil friction. Typical range "
            f"&delta; = &phi;/2 to 2&phi;/3."
        )
    if b - d - theta_used <= 1e-9:
        raise ValueError(
            f"M-O undefined: beta - delta - theta = {b - d - theta_used:.2f} deg <= 0 "
            f"(the thrust diverges as the wall-friction resultant becomes parallel "
            f"to the back face). Reduce k_h or delta, or steepen the wall (larger beta).")

    validity_html = (
        f'<span style="color:{COL["good"]};font-weight:600;">&#10003; valid</span>'
        if mo_valid else
        f'<span style="color:{COL["critical"]};font-weight:600;">&#10007; exceeded '
        f'&mdash; limiting state reported</span>'
    )
    results.append(
        f"<h4>1&nbsp;&middot;&nbsp;Seismic Coefficients &amp; Inertia Angle</h4>"
        f'<p class="ref-line">Ref: Das &amp; Sivakugan &sect;16.9, <strong>p.&nbsp;668</strong>; '
        f'AASHTO LRFD &sect;11.6.5.2; Kramer (1996) &sect;11.6.1. '
        f'k<sub>h</sub>, k<sub>v</sub> are <em>effective</em> coefficients '
        f'(PGA wave-scattering / displacement reduction already applied).</p>'
        f"\\[ k_h = {_f(kh_val)} \\qquad k_v = {_f(kv_val)} \\]"
        f"\\[ \\theta = \\arctan\\!\\left(\\frac{{k_h}}{{1-k_v}}\\right) = "
        f"\\arctan\\!\\left(\\frac{{{_f(kh_val)}}}{{{_f(1 - kv_val)}}}\\right) = {_f(theta, 2)}^\\circ \\]"
        f"<p><strong>M-O validity check</strong> (square-root argument requires "
        f"\\( \\phi - \\alpha - \\theta \\ge 0 \\)):</p>"
        f"\\[ \\phi - \\alpha - \\theta = {_f(ph, 1)} - {_f(a, 1)} - {_f(theta, 2)} "
        f"= {_f(ph - a - theta, 2)}^\\circ \\]"
        f"\\[ k_{{h,\\lim}} = (1-k_v)\\tan(\\phi-\\alpha) = {_f(kh_limit, 3)} \\]"
        f"<p>Status: {validity_html}</p>"
    )

    # -- 2. Static coefficients --------------------------------------------
    ko = 1 - math.sin(ph * DEG)
    ka = coulomb_ka(ph, d, a, b)
    kp = coulomb_kp(ph, d, a, b)
    if ka is None:
        # Static Coulomb itself is invalid — nothing sensible to report.
        raise ValueError(
            "Coulomb active coefficient undefined for these inputs: requires "
            "phi >= alpha (backfill slope no steeper than its friction angle), "
            "beta > delta, and alpha + beta < 180 deg.")
    results.append(
        f"<h4>2&nbsp;&middot;&nbsp;Static Earth Pressure Coefficients</h4>"
        f'<p class="ref-line">Ref: Jaky (1944); Coulomb (1776); Das &amp; Sivakugan '
        f'&sect;16.2 Eq.&nbsp;16.3 <strong>p.&nbsp;640</strong>, '
        f'&sect;16.7 Eq.&nbsp;16.26 <strong>p.&nbsp;658</strong>.</p>'
        f"\\[ K_0 = 1 - \\sin\\phi = 1 - \\sin {_f(ph, 1)}^\\circ = {_f(ko, 4)} \\]"
        f"\\[ K_a = \\frac{{\\sin^2(\\beta+\\phi)}}{{\\sin^2\\!\\beta\\,\\sin(\\beta-\\delta)"
        f"\\left[1+\\sqrt{{\\dfrac{{\\sin(\\phi+\\delta)\\sin(\\phi-\\alpha)}}"
        f"{{\\sin(\\beta-\\delta)\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(ka, 5)} \\]"
        + (f"\\[ K_p = \\frac{{\\sin^2(\\beta-\\phi)}}{{\\sin^2\\!\\beta\\,\\sin(\\beta+\\delta)"
           f"\\left[1-\\sqrt{{\\dfrac{{\\sin(\\phi+\\delta)\\sin(\\phi+\\alpha)}}"
           f"{{\\sin(\\beta+\\delta)\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(kp, 5)} \\]"
           if kp is not None else
           "<p><em>Coulomb K<sub>p</sub> undefined for these inputs.</em></p>")
    )

    # -- 3. Seismic active coefficient (M-O) --------------------------------
    kae = mo_kae(ph, d, a, b, theta_used)
    if kae is None or kae <= 0:
        raise ValueError(
            "Mononobe-Okabe coefficient undefined for these inputs (even at the "
            "limiting inertia angle). Check that beta - delta - theta > 0 and "
            "alpha + beta < 180 deg.")
    dKae = kae * (1 - kv_val) - ka
    results.append(
        f"<h4>3&nbsp;&middot;&nbsp;Seismic Active Coefficient &mdash; Mononobe-Okabe</h4>"
        f'<p class="ref-line">Ref: Okabe (1926); Mononobe &amp; Matsuo (1929); '
        f'Das &amp; Sivakugan &sect;16.9 Eq.&nbsp;16.38, <strong>p.&nbsp;668</strong>; '
        f'Kramer (1996) Eq.&nbsp;11.6.</p>'
        f"\\[ K_{{ae}} = \\frac{{\\sin^2(\\beta+\\phi-\\theta)}}{{\\cos\\theta\\,\\sin^2\\!\\beta\\,"
        f"\\sin(\\beta-\\delta-\\theta)\\left[1+\\sqrt{{\\dfrac{{\\sin(\\phi+\\delta)\\,"
        f"\\sin(\\phi-\\alpha-\\theta)}}{{\\sin(\\beta-\\delta-\\theta)\\,"
        f"\\sin(\\beta+\\alpha)}}}}\\right]^2}} = {_f(kae, 5)} \\]"
        f"\\[ \\Delta K_{{ae}} = K_{{ae}}(1-k_v) - K_a = {_f(kae, 5)} \\times {_f(1 - kv_val, 3)} "
        f"- {_f(ka, 5)} = {_f(dKae, 5)} \\]"
    )

    # -- 4. Seismic passive coefficient -------------------------------------
    # Evaluated at the TRUE inertia angle: the passive root's validity domain
    # (phi + alpha - theta >= 0) differs from the active one, and clamping
    # theta down would overstate the resistance-side quantity.
    kpe = mo_kpe(ph, d, a, b, theta)
    Ppe = 0.5 * g * H * H * kpe * (1 - kv_val) if kpe is not None else None
    if kpe is not None:
        results.append(
            f"<h4>4&nbsp;&middot;&nbsp;Seismic Passive Coefficient &mdash; Mononobe-Okabe</h4>"
            f'<p class="ref-line">Ref: Kramer (1996) Eq.&nbsp;11.10; Das &amp; Sivakugan '
            f'&sect;16.17. Cos-form with wall batter '
            f'\\( \\theta_w = 90^\\circ - \\beta = {_f(90 - b, 1)}^\\circ \\). '
            f'<em>Note:</em> M-O passive assumes a planar failure surface and '
            f'<strong>overestimates</strong> resistance for &delta; &gt; &phi;/2 '
            f'(log-spiral solutions are lower); use with caution as resistance.</p>'
            f"\\[ K_{{pe}} = \\frac{{\\cos^2(\\phi+\\theta_w-\\theta)}}{{\\cos\\theta\\,"
            f"\\cos^2\\theta_w\\,\\cos(\\delta-\\theta_w+\\theta)\\left[1-\\sqrt{{"
            f"\\dfrac{{\\sin(\\phi+\\delta)\\,\\sin(\\phi+\\alpha-\\theta)}}"
            f"{{\\cos(\\delta-\\theta_w+\\theta)\\,\\cos(\\alpha-\\theta_w)}}}}\\right]^2}} "
            f"= {_f(kpe, 5)} \\]"
            f"\\[ P_{{pe}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_{{pe}}(1-k_v) = {_f(Ppe, 2)} "
            f"\\text{{ kN/m}} \\]"
        )
    else:
        results.append(
            f"<h4>4&nbsp;&middot;&nbsp;Seismic Passive Coefficient &mdash; Mononobe-Okabe</h4>"
            f"<p><em>K<sub>pe</sub> undefined for these inputs (square-root argument "
            f"negative).</em></p>"
        )

    # -- 5. Lateral thrusts --------------------------------------------------
    Pa_static = 0.5 * g * H * H * ka
    Pae_granular = 0.5 * g * H * H * kae * (1 - kv_val)
    results.append(
        f"<h4>5&nbsp;&middot;&nbsp;Lateral Thrusts (per unit length of wall)</h4>"
        f'<p class="ref-line">Ref: Das &amp; Sivakugan &sect;16.9 Eq.&nbsp;16.37, '
        f'<strong>p.&nbsp;668</strong>; Kramer (1996) Eq.&nbsp;11.7. Note the '
        f'\\( (1-k_v) \\) factor on the seismic thrust.</p>'
        f"\\[ P_a = \\tfrac{{1}}{{2}}\\gamma H^2 K_a = "
        f"\\tfrac{{1}}{{2}} \\times {_f(g, 2)} \\times {_f(H, 2)}^2 \\times {_f(ka, 4)} "
        f"= {_f(Pa_static, 2)} \\text{{ kN/m}} \\]"
        f"\\[ P_{{ae}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_{{ae}}(1-k_v) = "
        f"\\tfrac{{1}}{{2}} \\times {_f(g, 2)} \\times {_f(H, 2)}^2 \\times {_f(kae, 4)} "
        f"\\times {_f(1 - kv_val, 3)} = {_f(Pae_granular, 2)} \\text{{ kN/m}} \\]"
        f"\\[ \\Delta P_{{ae}} = P_{{ae}} - P_a = {_f(Pae_granular - Pa_static, 2)} "
        f"\\text{{ kN/m}} \\]"
    )

    # -- 5b. Cohesion correction (Das §16.10) --------------------------------
    # Both the static and seismic thrusts get the same tension-crack treatment
    # so the dynamic increment and resultant height compare like with like.
    # The (1-kv) factor is carried through z_crack and the closure term so the
    # closed form is the exact integral of the displayed sigma_ae(z).
    c_applicable = (c_prime > 0 and abs(a) < 1e-6 and abs(b - 90) < 1e-6)
    z_crack = 0.0
    zc_a = 0.0
    Pa_ref = Pa_static
    if c_prime > 0:
        if c_applicable:
            sqrt_kae = math.sqrt(kae)
            sqrt_ka = math.sqrt(ka)
            one_kv = 1 - kv_val
            z_crack = 2 * c_prime / (g * sqrt_kae * one_kv)
            zc_a = 2 * c_prime / (g * sqrt_ka)
            crack_warn = ""
            if z_crack >= H:
                z_crack = H
                Pae_cphi = 0.0
                crack_warn = (
                    '<p style="color:#b7791f;font-size:0.9em;"><em>The tension crack '
                    'reaches the full wall height: the seismic pressure is negative '
                    'over the entire back face and the resultant is taken as zero. '
                    'The closed form does not apply beyond z<sub>crack</sub> = H.</em></p>')
            else:
                Pae_cphi = (0.5 * g * H * H * kae * one_kv
                            - 2 * c_prime * H * sqrt_kae
                            + (2 * c_prime ** 2) / (g * one_kv))
                Pae_cphi = max(Pae_cphi, 0.0)
            if zc_a >= H:
                zc_a = H
                Pa_ref = 0.0
            else:
                Pa_ref = max(0.5 * g * H * H * ka
                             - 2 * c_prime * H * sqrt_ka
                             + (2 * c_prime ** 2) / g, 0.0)
            results.append(
                f"<h4>5b&nbsp;&middot;&nbsp;Cohesion Correction (c&prime;-&phi;&prime; backfill)</h4>"
                f'<p class="ref-line">Ref: Das &amp; Sivakugan &sect;16.10, '
                f'<strong>p.&nbsp;672</strong>. Valid for vertical back '
                f'(&beta;&nbsp;=&nbsp;90&deg;) and level surface (&alpha;&nbsp;=&nbsp;0). '
                f'The tension-cracked depth carries no pressure; the closed forms below '
                f'are the exact integrals of the corrected pressure profiles. The same '
                f'correction is applied to the static thrust so &Delta;P<sub>ae</sub> '
                f'compares like with like.</p>'
                f"\\[ \\sigma_{{ae}}(z) = K_{{ae}}(1-k_v)\\,\\gamma z - 2c'\\sqrt{{K_{{ae}}}} "
                f"\\qquad \\sigma_a(z) = K_a\\,\\gamma z - 2c'\\sqrt{{K_a}} \\]"
                f"\\[ z_{{crack}} = \\frac{{2c'}}{{\\gamma(1-k_v)\\sqrt{{K_{{ae}}}}}} "
                f"= {_f(z_crack, 3)} \\text{{ m}} \\qquad "
                f"z_{{crack,a}} = \\frac{{2c'}}{{\\gamma\\sqrt{{K_a}}}} = {_f(zc_a, 3)} \\text{{ m}} \\]"
                f"\\[ P_{{ae,c'\\phi'}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_{{ae}}(1-k_v) "
                f"- 2c'H\\sqrt{{K_{{ae}}}} + \\frac{{2c'^2}}{{\\gamma(1-k_v)}} "
                f"= {_f(Pae_cphi, 2)} \\text{{ kN/m}} \\]"
                f"\\[ P_{{a,c'\\phi'}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_a "
                f"- 2c'H\\sqrt{{K_a}} + \\frac{{2c'^2}}{{\\gamma}} "
                f"= {_f(Pa_ref, 2)} \\text{{ kN/m}} \\]"
                + crack_warn
            )
            Pae = Pae_cphi
        else:
            results.append(
                f"<h4>5b&nbsp;&middot;&nbsp;Cohesion Correction (c&prime;-&phi;&prime; backfill)</h4>"
                f'<p style="color:#b7791f;font-size:0.9em;"><em>The Das &sect;16.10 seismic '
                f'c&prime;-&phi;&prime; closed form is only valid for a vertical wall back '
                f'(&beta; = 90&deg;) and level backfill (&alpha; = 0). Current inputs: '
                f'&alpha; = {_f(a, 1)}&deg;, &beta; = {_f(b, 1)}&deg;. Falling back to the '
                f'granular formulation (c&prime; ignored).</em></p>'
            )
            Pae = Pae_granular
    else:
        Pae = Pae_granular

    dPae = max(Pae - Pa_ref, 0.0)

    # Pressure ordinates at fifth points (table twin of Figure 4)
    def _sigma_ae(z):
        s_val = kae * (1 - kv_val) * g * z
        if c_applicable:
            s_val -= 2 * c_prime * math.sqrt(kae)
        return max(s_val, 0.0)

    def _sigma_a(z):
        s_val = ka * g * z
        if c_applicable:
            s_val -= 2 * c_prime * math.sqrt(ka)
        return max(s_val, 0.0)

    press_rows = []
    for i in range(6):
        z = H * i / 5
        s_a = _sigma_a(z)
        s_ae = _sigma_ae(z)
        press_rows.append(
            f"<tr><td>{_f(z, 2)}</td><td>{_f(s_a, 2)}</td>"
            f"<td>{_f(s_ae, 2)}</td><td>{_f(s_ae - s_a, 2)}</td></tr>")
    results.append(
        f"<h4>5c&nbsp;&middot;&nbsp;Pressure Ordinates (table twin of Figure&nbsp;4)</h4>"
        f"<table class='data-table'><thead><tr><th>z (m)</th>"
        f"<th>&sigma;<sub>a</sub> (kPa)</th><th>&sigma;<sub>ae</sub> (kPa)</th>"
        f"<th>&Delta;&sigma; (kPa)</th></tr></thead><tbody>"
        + "".join(press_rows) + "</tbody></table>"
    )

    # -- 6. Point of application, components, overturning --------------------
    # Seed & Whitman (1970): static part at its distribution centroid (H/3 for
    # the granular triangle; (H - z_crack,a)/3 for the c'-corrected profile),
    # dynamic increment at 0.6H. Since Pae = Pa_ref + dPae whenever dPae > 0,
    # z_bar is a convex combination and stays within [z_a, 0.6H].
    z_a = (H - zc_a) / 3
    if Pae > 1e-12 and Pae > Pa_ref:
        z_bar = (Pa_ref * z_a + dPae * 0.6 * H) / Pae
    else:
        z_bar = z_a
    # Thrust acts at delta from the wall-back normal; with beta from horizontal
    # this gives Ph = Pae sin(beta - delta), Pv = Pae cos(beta - delta) downward.
    Ph = Pae * math.sin((b - d) * DEG)
    Pv = Pae * math.cos((b - d) * DEG)   # positive downward on the wall
    M_ot = Ph * z_bar
    z_a_label = ("(H - z_{crack,a})/3" if c_applicable else "H/3")
    results.append(
        f"<h4>6&nbsp;&middot;&nbsp;Point of Application &amp; Force Components</h4>"
        f'<p class="ref-line">Ref: Seed &amp; Whitman (1970); Das &amp; Sivakugan '
        f'&sect;17.10; AASHTO &sect;11.6.5. The theoretical M-O distribution is '
        f'triangular (resultant at H/3); test data show the <em>dynamic increment</em> '
        f'acts higher &mdash; the S&amp;W convention (0.6H) is the design standard.</p>'
        f"\\[ z_a = {z_a_label} = {_f(z_a, 3)} \\text{{ m}} \\]"
        f"\\[ \\bar{{z}} = \\frac{{P_a\\,z_a + \\Delta P_{{ae}}\\,(0.6H)}}{{P_{{ae}}}} = "
        f"\\frac{{{_f(Pa_ref, 2)} \\times {_f(z_a, 3)} + {_f(dPae, 2)} \\times "
        f"{_f(0.6 * H, 3)}}}{{{_f(Pae, 2)}}} = {_f(z_bar, 3)} \\text{{ m above heel}} "
        f"\\;\\; (\\bar{{z}}/H = {_f(z_bar / H, 3)}) \\]"
        f"\\[ P_h = P_{{ae}}\\sin(\\beta-\\delta) = {_f(Ph, 2)} \\text{{ kN/m}} \\qquad "
        f"P_v = P_{{ae}}\\cos(\\beta-\\delta) = {_f(Pv, 2)} \\text{{ kN/m (down)}} \\]"
        f"\\[ M_{{ot}} = P_h\\,\\bar{{z}} = {_f(Ph, 2)} \\times {_f(z_bar, 3)} "
        f"= {_f(M_ot, 2)} \\text{{ kN\\!\\cdot\\!m/m}} \\]"
    )

    # -- 7. Critical failure surface ------------------------------------------
    psi_ae = critical_wedge_angle(ph, d, a, b, theta_used)
    psi_a = critical_wedge_angle(ph, d, a, b, 0.0)
    wedge = _wedge_geometry(H, a, b, psi_ae) if psi_ae else None
    x_t = -H / math.tan(b * DEG) if abs(b - 90) > 1e-9 else 0.0
    x_extent = (wedge[1][0] - x_t) if wedge else None
    if psi_ae is not None:
        ext_html = (f"\\[ x_{{wedge}} = {_f(x_extent, 2)} \\text{{ m behind the wall crest}} \\]"
                    if x_extent is not None else "")
        results.append(
            f"<h4>7&nbsp;&middot;&nbsp;Critical Failure Surface</h4>"
            f'<p class="ref-line">Ref: Zarrabi-Kashani (1979); Kramer (1996) '
            f'Eq.&nbsp;11.6 notation. Exact closed form for the thrust-maximizing '
            f'planar wedge; reduces to the Coulomb result in the static limit. '
            f'Seismic shaking <em>flattens</em> the failure plane, enlarging the '
            f'active wedge.</p>'
            f"\\[ \\alpha_{{AE}} = \\phi - \\theta + \\arctan\\!\\left["
            f"\\frac{{-\\tan(\\phi-\\theta-\\alpha) + C_{{1E}}}}{{C_{{2E}}}}\\right] "
            f"= {_f(psi_ae, 2)}^\\circ \\]"
            + (f"\\[ \\alpha_A^{{static}} = {_f(psi_a, 2)}^\\circ "
               f"\\qquad \\Delta = {_f(psi_a - psi_ae, 2)}^\\circ \\text{{ flatter under shaking}} \\]"
               if psi_a is not None else "")
            + ext_html
        )

    # -- 8. Seed-Whitman approximation check ---------------------------------
    sw_applicable = abs(a) < 1e-6 and abs(b - 90) < 1e-6
    kae_sw = ka + 0.75 * kh_val
    sw_err = (kae_sw - kae) / kae * 100 if kae > 0 else 0.0
    results.append(
        f"<h4>8&nbsp;&middot;&nbsp;Seed&ndash;Whitman Approximation Check</h4>"
        f'<p class="ref-line">Ref: Seed &amp; Whitman (1970): '
        f'\\( \\Delta K_{{ae}} \\approx \\tfrac{{3}}{{4}}k_h \\) for vertical walls '
        f'with level granular backfill (&phi; &asymp; 35&deg;).'
        + ("" if sw_applicable else
           " <strong>Outside its geometry range here</strong> "
           f"(&alpha; = {_f(a, 1)}&deg;, &beta; = {_f(b, 1)}&deg;) &mdash; shown for reference only.")
        + '</p>'
        f"\\[ K_{{ae}}^{{SW}} \\approx K_a + 0.75\\,k_h = {_f(ka, 4)} + 0.75 \\times "
        f"{_f(kh_val, 3)} = {_f(kae_sw, 4)} \\quad "
        f"\\left(\\text{{vs. exact }} {_f(kae, 4)},\\; {'+' if sw_err >= 0 else ''}{_f(sw_err, 1)}\\%\\right) \\]"
    )

    # -- 9. Wedge equilibrium QA check ---------------------------------------
    poly = None
    if psi_ae is not None and c_prime <= 0:
        eq = _wedge_equilibrium(H, g, a, b, ph, d, psi_ae, kh_val, kv_val)
        if eq:
            P_poly, R_poly, W_wedge = eq
            closure = abs(P_poly - Pae_granular) / Pae_granular * 100 if Pae_granular > 0 else 0.0
            poly = {"P": P_poly, "R": R_poly, "W": W_wedge, "closure": closure}
            results.append(
                f"<h4>9&nbsp;&middot;&nbsp;Independent QA &mdash; Wedge Equilibrium</h4>"
                f'<p class="ref-line">Force equilibrium of the critical wedge '
                f'(Fig.&nbsp;2) solved independently of the K<sub>ae</sub> formula: '
                f'the closed-form coefficient and the vector polygon must agree.</p>'
                f"\\[ W = {_f(W_wedge, 2)} \\text{{ kN/m}} \\qquad "
                f"k_h W = {_f(kh_val * W_wedge, 2)} \\qquad "
                f"k_v W = {_f(kv_val * W_wedge, 2)} \\]"
                f"\\[ P_{{ae}}^{{polygon}} = {_f(P_poly, 2)} \\text{{ kN/m vs. }} "
                f"P_{{ae}}^{{M\\text{{-}}O}} = {_f(Pae_granular, 2)} \\text{{ kN/m}} "
                f"\\quad (\\Delta = {_f(closure, 3)}\\%) \\]"
            )
    if poly is None:
        results.append(
            f"<h4>9&nbsp;&middot;&nbsp;Independent QA &mdash; Wedge Equilibrium</h4>"
            f'<p class="ref-line">The wedge-equilibrium cross-check applies to the '
            f'granular formulation only; it is not evaluated '
            + ("for c&prime; &gt; 0 (the closed-form check would need a cohesive "
               "force along the failure plane)." if c_prime > 0 else
               "at the limiting state (the critical wedge degenerates).")
            + '</p>'
        )

    # -- 10. Design summary table ---------------------------------------------
    def _row(sym, desc, val, unit):
        return (f"<tr><td style='text-align:left'>\\( {sym} \\)</td>"
                f"<td style='text-align:left'>{desc}</td>"
                f"<td><strong>{val}</strong></td><td>{unit}</td></tr>")

    summary_rows = [
        _row("\\theta", "Seismic inertia angle", _f(theta, 2), "&deg;"),
        _row("K_0", "At-rest coefficient (Jaky)", _f(ko, 4), "&ndash;"),
        _row("K_a", "Static active (Coulomb)", _f(ka, 4), "&ndash;"),
        _row("K_{ae}", "Seismic active (M-O)", _f(kae, 4), "&ndash;"),
        _row("\\Delta K_{ae}", "Dynamic coefficient increment", _f(dKae, 4), "&ndash;"),
    ]
    if kp is not None:
        summary_rows.insert(3, _row("K_p", "Static passive (Coulomb)", _f(kp, 4), "&ndash;"))
    if kpe is not None:
        summary_rows.append(_row("K_{pe}", "Seismic passive (M-O)", _f(kpe, 4), "&ndash;"))
    summary_rows += [
        _row("P_a", "Static active thrust" +
             (" (c&prime;-corrected)" if c_applicable else ""),
             _f(Pa_ref, 2), "kN/m"),
        _row("P_{ae}", "Seismic active thrust", _f(Pae, 2), "kN/m"),
        _row("\\Delta P_{ae}", "Dynamic thrust increment", _f(dPae, 2), "kN/m"),
        _row("\\bar{z}", "Resultant height above heel (S&amp;W)", _f(z_bar, 3), "m"),
        _row("P_h", "Horizontal component", _f(Ph, 2), "kN/m"),
        _row("P_v", "Vertical component (down)", _f(Pv, 2), "kN/m"),
        _row("M_{ot}", "Overturning moment about heel", _f(M_ot, 2), "kN&middot;m/m"),
    ]
    if psi_ae is not None:
        summary_rows.append(_row("\\alpha_{AE}", "Critical failure-plane angle", _f(psi_ae, 2), "&deg;"))
    results.append(
        f"<h4>10&nbsp;&middot;&nbsp;Design Summary</h4>"
        f"<table class='data-table'><thead><tr><th>Symbol</th><th>Quantity</th>"
        f"<th>Value</th><th>Unit</th></tr></thead><tbody>"
        + "".join(summary_rows) + "</tbody></table>"
    )

    # -- Figures ---------------------------------------------------------------
    fig_cross = _fig_cross_section(
        H, g, ka, kae, a, b, theta, Pa_ref, Pae, psi_ae,
        c_prime if c_applicable else 0.0, z_crack, z_bar, kv_val, zc_a)
    fig_poly = _fig_force_polygon(H, g, a, b, ph, d, psi_ae, kh_val, kv_val,
                                  poly, Pae_granular)
    fig_sens = _fig_sensitivity(ph, d, a, b, kh_val, kv_val, ka, kae, kh_limit,
                                mo_valid)
    fig_press = _fig_pressure(H, g, ka, kae, kv_val,
                              c_prime if c_applicable else 0.0, z_crack, zc_a)

    summary = {
        "kae": kae, "ka": ka, "kp": kp, "kpe": kpe, "ko": ko,
        "theta": theta, "kh_limit": kh_limit, "mo_valid": mo_valid,
        "Pa": Pa_static, "Pa_ref": Pa_ref, "Pae": Pae, "dPae": dPae, "Ppe": Ppe,
        "z_bar": z_bar, "z_bar_ratio": z_bar / H if H > 0 else 0.0, "z_a": z_a,
        "Ph": Ph, "Pv": Pv, "M_ot": M_ot,
        "psi_ae": psi_ae, "psi_a": psi_a, "x_extent": x_extent,
        "closure": poly["closure"] if poly else None,
        "c_applicable": c_applicable, "z_crack": z_crack,
        "warnings": warnings,
    }

    figures = {
        "cross_section": fig_cross,
        "force_polygon": fig_poly,
        "sensitivity": fig_sens,
        "pressure_dist": fig_press,
    }

    return {
        "results": results,
        "summary": summary,
        "figures": figures,
        # Back-compat aliases
        "cross_section": fig_cross,
        "force_polygon": fig_poly,
        "chart_traces": fig_cross["traces"],
        "chart_layout": fig_cross["layout"],
    }


# ---------------------------------------------------------------------------
# Figure 1 — wall cross-section with critical wedge and pressure overlay
# ---------------------------------------------------------------------------

def _fig_cross_section(H, g, ka, kae, alpha, beta, theta, Pa_static, Pae,
                       psi_ae, c_prime, z_crack, z_bar, kv, zc_a=0.0):
    beta_rad = beta * DEG
    alpha_rad = alpha * DEG
    x_t = -H / math.tan(beta_rad) if abs(beta - 90) > 1e-9 else 0.0
    t_stem = max(0.10 * H, 0.05)

    # Wall polygon (heel at origin, stem to the left of the back face)
    wall_x = [0, -t_stem + min(0.0, x_t), -t_stem + min(0.0, x_t), x_t, 0]
    wall_y = [0, 0, H, H, 0]

    # Size the drawn soil to contain the critical wedge (capped at 4H; the
    # wedge flattens without bound near the M-O limit, so clip and say so).
    geom = _wedge_geometry(H, alpha, beta, psi_ae) if psi_ae is not None else None
    cap_x = 4.0 * H
    wedge_clipped = False
    if geom:
        (_, _), (apex_x, apex_y), _ = geom
        if apex_x <= cap_x:
            bf_len = max(1.6 * H, 1.15 * apex_x)
        else:
            bf_len = cap_x
            wedge_clipped = True
    else:
        bf_len = 1.6 * H
    bf_top_end = H + (bf_len - x_t) * math.tan(alpha_rad)
    bf_x = [0, bf_len, bf_len, x_t, 0]
    bf_y = [0, 0, bf_top_end, H, 0]

    sigma_a_max = max(g * H * ka - (2 * c_prime * math.sqrt(ka) if c_prime > 0 else 0.0), 0.0)
    sigma_ae_max = g * H * kae * (1 - kv)
    p_scale = 0.42 * H / max(sigma_ae_max, sigma_a_max, 1e-9)
    off = -t_stem + min(0.0, x_t) - 0.06 * H

    # Static pressure triangle (corrected profile starts at zc_a when c' > 0)
    stat_x = [off, off - sigma_a_max * p_scale, off]
    stat_y = [H - min(zc_a, H), 0, 0]
    if c_prime > 0 and z_crack > 0:
        sig_base = max(sigma_ae_max - 2 * c_prime * math.sqrt(kae), 0.0)
        seis_x = [off, off - sig_base * p_scale, off]
        seis_y = [H - min(z_crack, H), 0, 0]
    else:
        seis_x = [off, off - sigma_ae_max * p_scale, off]
        seis_y = [H, 0, 0]

    traces = []
    # Backfill
    traces.append({
        "x": bf_x, "y": bf_y, "mode": "lines", "fill": "toself",
        "fillcolor": COL["soil_fill"],
        "line": {"color": COL["soil_line"], "width": 1},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Critical failure wedge (clipped at the drawn soil edge if needed)
    wedge_drawn = None
    if geom:
        (cx, cy), (xi, yi), _ = geom
        if wedge_clipped:
            xi_d = bf_len
            yi_plane = xi_d * math.tan(psi_ae * DEG)
            yi_surf = H + (xi_d - x_t) * math.tan(alpha_rad)
            traces.append({
                "x": [0, xi_d, xi_d, cx, 0],
                "y": [0, yi_plane, yi_surf, cy, 0],
                "mode": "lines", "fill": "toself",
                "fillcolor": "rgba(194,178,128,0.45)",
                "line": {"color": COL["wedge_line"], "width": 2, "dash": "dash"},
                "hoverinfo": "skip", "showlegend": False,
            })
            wedge_drawn = (xi_d, yi_plane)
        else:
            traces.append({
                "x": [0, xi, cx, 0], "y": [0, yi, cy, 0],
                "mode": "lines", "fill": "toself",
                "fillcolor": "rgba(194,178,128,0.45)",
                "line": {"color": COL["wedge_line"], "width": 2, "dash": "dash"},
                "hoverinfo": "skip", "showlegend": False,
            })
            wedge_drawn = (xi, yi)
    # Wall
    traces.append({
        "x": wall_x, "y": wall_y, "mode": "lines", "fill": "toself",
        "fillcolor": COL["wall_fill"],
        "line": {"color": COL["wall_line"], "width": 2},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Ground line
    traces.append({
        "x": [off - 0.55 * H, bf_len], "y": [0, 0],
        "mode": "lines", "line": {"color": COL["axis"], "width": 1.5},
        "hoverinfo": "skip", "showlegend": False,
    })
    # Static pressure triangle
    traces.append({
        "x": stat_x, "y": stat_y, "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(42,120,214,0.12)",
        "line": {"color": COL["static"], "width": 2, "dash": "dash"},
        "hoverinfo": "skip",
        "name": f"Static  Pₐ = {Pa_static:.1f} kN/m",
    })
    # Seismic pressure
    traces.append({
        "x": seis_x, "y": seis_y, "mode": "lines", "fill": "toself",
        "fillcolor": "rgba(227,73,72,0.12)",
        "line": {"color": COL["seismic"], "width": 2},
        "hoverinfo": "skip",
        "name": f"Seismic  Pₐₑ = {Pae:.1f} kN/m",
    })
    if c_prime > 0 and z_crack > 0:
        traces.append({
            "x": [off - 0.12 * H, x_t + 0.08 * H], "y": [H - z_crack, H - z_crack],
            "mode": "lines",
            "line": {"color": "#7f1d1d", "width": 1.5, "dash": "dot"},
            "hoverinfo": "skip", "showlegend": False,
        })

    ann = []
    # H dimension line with arrowheads (drawn as two annotations)
    xd = off - 0.50 * H
    ann.append({"x": xd, "y": 0, "ax": xd, "ay": H / 2, "xref": "x", "yref": "y",
                "axref": "x", "ayref": "y", "showarrow": True, "arrowhead": 2,
                "arrowsize": 1, "arrowwidth": 1, "arrowcolor": COL["muted"]})
    ann.append({"x": xd, "y": H, "ax": xd, "ay": H / 2, "xref": "x", "yref": "y",
                "axref": "x", "ayref": "y", "showarrow": True, "arrowhead": 2,
                "arrowsize": 1, "arrowwidth": 1, "arrowcolor": COL["muted"]})
    ann.append({"x": xd, "y": H / 2, "text": f"H = {H:.2f} m", "showarrow": False,
                "font": {"size": 11, "color": COL["ink2"]}, "xanchor": "right",
                "xshift": -4})
    # Angle labels
    ann.append({"x": x_t + 0.55 * bf_len, "y": bf_top_end + 0.10 * H,
                "text": f"α = {alpha:.1f}°", "showarrow": False,
                "font": {"size": 11, "color": COL["ink2"]}})
    ann.append({"x": 0.03 * H, "y": 0.10 * H,
                "text": f"β = {beta:.1f}°", "showarrow": False,
                "font": {"size": 11, "color": COL["ink2"]}, "xanchor": "left"})
    if wedge_drawn is not None:
        # Label placed midway along the drawn failure plane, nudged below it
        wx, wy = wedge_drawn
        ann.append({"x": 0.55 * wx, "y": max(0.55 * wy - 0.10 * H, 0.06 * H),
                    "text": f"α<sub>AE</sub> = {psi_ae:.1f}°",
                    "showarrow": False,
                    "font": {"size": 11, "color": COL["wedge_line"]}})
        if wedge_clipped:
            ann.append({"x": bf_len * 0.98, "y": wy + 0.10 * H,
                        "text": "wedge extends beyond view →",
                        "showarrow": False, "xanchor": "right",
                        "font": {"size": 10, "color": COL["muted"]}})
    ann.append({"x": x_t + 0.02 * H, "y": H * 1.10,
                "text": f"θ = {theta:.2f}°", "showarrow": False,
                "font": {"size": 11, "color": COL["seismic"]}, "xanchor": "left"})

    # Static resultant arrow at H/3
    y_s = H / 3
    ann.append({"x": -t_stem - 0.01 * H, "y": y_s, "ax": off - 0.26 * H, "ay": y_s,
                "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
                "showarrow": True, "arrowhead": 2, "arrowsize": 1.2,
                "arrowwidth": 2, "arrowcolor": COL["static"]})
    ann.append({"x": off - 0.27 * H, "y": y_s + 0.05 * H,
                "text": f"P<sub>a</sub> @ H/3", "showarrow": False,
                "font": {"size": 10, "color": COL["ink2"]}, "xanchor": "right"})
    # Combined seismic resultant at z_bar
    ann.append({"x": -t_stem - 0.01 * H, "y": z_bar, "ax": off - 0.34 * H, "ay": z_bar,
                "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
                "showarrow": True, "arrowhead": 2, "arrowsize": 1.2,
                "arrowwidth": 2.5, "arrowcolor": COL["seismic"]})
    ann.append({"x": off - 0.35 * H, "y": z_bar + 0.05 * H,
                "text": f"P<sub>ae</sub> @ z̄ = {z_bar:.2f} m",
                "showarrow": False,
                "font": {"size": 10, "color": COL["ink2"]}, "xanchor": "right"})
    if c_prime > 0 and z_crack > 0:
        ann.append({"x": x_t + 0.10 * H, "y": H - z_crack,
                    "text": f"z<sub>crack</sub> = {z_crack:.2f} m",
                    "showarrow": False, "font": {"size": 10, "color": "#7f1d1d"},
                    "xanchor": "left", "yshift": 8})

    y_top = max(H * 1.30, bf_top_end + 0.25 * H)
    if wedge_drawn is not None:
        y_top = max(y_top, wedge_drawn[1] + 0.20 * H)
    layout = _base_layout(height=440)
    layout.update({
        "xaxis": {"visible": False, "scaleanchor": "y", "scaleratio": 1,
                  "range": [off - 0.75 * H, bf_len + 0.05 * H]},
        "yaxis": {"visible": False,
                  "range": [-0.15 * H, y_top]},
        "margin": {"l": 8, "r": 8, "t": 8, "b": 8},
        "annotations": ann,
        "showlegend": True,
        "legend": {"orientation": "h", "x": 0.5, "y": -0.04, "xanchor": "center",
                   "font": {"size": 11, "color": COL["ink2"]}},
    })
    return {"traces": traces, "layout": layout}


# ---------------------------------------------------------------------------
# Figure 2 — closed force polygon of the critical wedge
# ---------------------------------------------------------------------------

def _fig_force_polygon(H, g, alpha, beta, phi, delta, psi_ae, kh, kv,
                       poly, Pae_granular):
    """True head-to-tail vector polygon in force space (kN/m). When the exact
    equilibrium solution is available the polygon closes by construction."""
    if psi_ae is None or poly is None:
        # Fallback: nothing meaningful to draw
        layout = _base_layout(height=440)
        layout.update({
            "xaxis": {"visible": False}, "yaxis": {"visible": False},
            "annotations": [{
                "x": 0.5, "y": 0.5, "xref": "paper", "yref": "paper",
                "text": "Force polygon not drawn: the wedge-equilibrium check is<br>"
                        "granular-only (c′ = 0) and needs a defined critical wedge<br>"
                        "(not available at the M-O limiting state).",
                "showarrow": False,
                "font": {"size": 12, "color": COL["muted"]},
            }],
        })
        return {"traces": [], "layout": layout}

    W = poly["W"]
    P = poly["P"]
    R = poly["R"]
    rho = psi_ae
    r_dir = (-math.sin((rho - phi) * DEG), math.cos((rho - phi) * DEG))
    p_dir = (math.sin((beta - delta) * DEG), math.cos((beta - delta) * DEG))

    # Head-to-tail chain: W down, kvW up, khW toward wall, R, P closes.
    pts = [(0.0, 0.0)]
    vecs = [
        ("W", (0.0, -W), COL["W"]),
    ]
    if abs(kv) > 1e-9:
        vecs.append((f"kᵥW", (0.0, kv * W), COL["increment"]))
    vecs.append(("kₕW", (-kh * W, 0.0), COL["seismic"]))
    vecs.append(("R", (R * r_dir[0], R * r_dir[1]), COL["R"]))
    vecs.append(("Pₐₑ", (P * p_dir[0], P * p_dir[1]), COL["static"]))

    labels = {"W": W, "kᵥW": abs(kv * W), "kₕW": kh * W, "R": R,
              "Pₐₑ": P}

    ann = []
    for name, (vx, vy), color in vecs:
        x0, y0 = pts[-1]
        x1, y1 = x0 + vx, y0 + vy
        pts.append((x1, y1))
        ann.append({
            "x": x1, "y": y1, "ax": x0, "ay": y0,
            "xref": "x", "yref": "y", "axref": "x", "ayref": "y",
            "showarrow": True, "arrowhead": 3, "arrowsize": 1.1,
            "arrowwidth": 2.5, "arrowcolor": color,
        })
        # Label at midpoint, offset perpendicular to the vector
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        vlen = math.hypot(vx, vy) or 1.0
        # perpendicular offset (to the left of travel)
        ox, oy = -vy / vlen, vx / vlen
        ann.append({
            "x": mx, "y": my, "showarrow": False,
            "text": f"<b>{name}</b> = {labels[name]:.1f}",
            "font": {"size": 11, "color": COL["ink"]},
            "xshift": ox * 30, "yshift": oy * 16,
            "bgcolor": "rgba(255,255,255,0.85)",
        })

    closure_err = math.hypot(*pts[-1]) / W * 100 if W > 0 else 0.0
    ann.append({
        "x": 0.02, "y": 0.02, "xref": "paper", "yref": "paper",
        "xanchor": "left", "yanchor": "bottom", "showarrow": False,
        "text": (f"Closure: {closure_err:.2f}% of W &nbsp;|&nbsp; "
                 f"Pₐₑ polygon = {P:.2f} vs M-O = {Pae_granular:.2f} kN/m "
                 f"(Δ {poly['closure']:.2f}%)"),
        "font": {"size": 11, "color": COL["good"] if poly["closure"] < 0.5 else COL["critical"]},
    })

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = 0.18 * max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)

    # Invisible scatter to establish axes ranges & hover values at vertices
    traces = [{
        "x": xs, "y": ys, "mode": "markers",
        "marker": {"size": 7, "color": COL["ink2"],
                   "line": {"color": "#ffffff", "width": 2}},
        "hovertemplate": "(%{x:.1f}, %{y:.1f}) kN/m<extra></extra>",
        "showlegend": False,
    }]

    layout = _base_layout(height=440)
    layout.update({
        "xaxis": {**_axis("Horizontal force (kN/m)"),
                  "scaleanchor": "y", "scaleratio": 1,
                  "range": [min(xs) - pad, max(xs) + pad]},
        "yaxis": {**_axis("Vertical force (kN/m)"),
                  "range": [min(ys) - pad, max(ys) + pad]},
        "annotations": ann,
        "showlegend": False,
    })
    return {"traces": traces, "layout": layout}


# ---------------------------------------------------------------------------
# Figure 3 — Kae sensitivity to kh (family over phi) + design point
# ---------------------------------------------------------------------------

def _fig_sensitivity(phi, delta, alpha, beta, kh, kv, ka_design, kae_design,
                     kh_limit, mo_valid=True):
    phis = [max(phi - 5, alpha + 1), phi, phi + 5]
    colors = [COL["ord_lo"], COL["ord_mid"], COL["ord_hi"]]
    kh_max_plot = min(max(kh * 1.6, kh_limit * 1.05, 0.35), 0.9)

    traces = []
    for p_i, color in zip(phis, colors):
        xs, ys = [], []
        n = 80
        for i in range(n + 1):
            k = kh_max_plot * i / n
            th = math.degrees(math.atan2(k, 1 - kv))
            val = mo_kae(p_i, delta, alpha, beta, th)
            if val is None:
                break
            xs.append(round(k, 4))
            ys.append(val)
        traces.append({
            "x": xs, "y": ys, "mode": "lines",
            "line": {"color": color, "width": 2, "shape": "spline"},
            "name": f"φ = {p_i:.0f}°",
            "hovertemplate": "kₕ = %{x:.3f}<br>Kₐₑ = %{y:.4f}<extra>φ = "
                             + f"{p_i:.0f}°</extra>",
        })

    # Seed-Whitman approximation for the design phi (dashed = approximation)
    ka0 = coulomb_ka(phi, delta, alpha, beta)
    if ka0 is not None:
        xs = [round(kh_max_plot * i / 40, 4) for i in range(41)]
        traces.append({
            "x": xs, "y": [ka0 + 0.75 * x for x in xs], "mode": "lines",
            "line": {"color": COL["approx"], "width": 2, "dash": "dash"},
            "name": "Seed–Whitman  Kₐ + 0.75kₕ",
            "hovertemplate": "kₕ = %{x:.3f}<br>Kₐₑ ≈ %{y:.4f}"
                             "<extra>Seed–Whitman</extra>",
        })

    # Design point. When the M-O limit is exceeded, Kae is a clamped
    # limiting-state value — plot it AT the limit with an open marker so the
    # figure never asserts that Kae is defined at the raw kh.
    pt_x = kh if mo_valid else min(kh_limit, kh)
    traces.append({
        "x": [pt_x], "y": [kae_design], "mode": "markers",
        "marker": ({"size": 11, "color": COL["ink"],
                    "line": {"color": "#ffffff", "width": 2}}
                   if mo_valid else
                   {"size": 12, "color": "rgba(0,0,0,0)", "symbol": "circle-open",
                    "line": {"color": COL["critical"], "width": 2.5}}),
        "name": "Design point" if mo_valid else "Limiting state (kₕ > kₕ,lim)",
        "hovertemplate": ("kₕ = %{x:.3f}<br>Kₐₑ = %{y:.4f}<extra>"
                          + ("Design point" if mo_valid else "Limiting state")
                          + "</extra>"),
    })

    shapes = []
    ann = []
    if 0 < kh_limit <= kh_max_plot:
        shapes.append({
            "type": "line", "x0": kh_limit, "x1": kh_limit, "y0": 0, "y1": 1,
            "yref": "paper",
            "line": {"color": COL["critical"], "width": 1},
        })
        ann.append({
            "x": kh_limit, "y": 1.0, "yref": "paper", "showarrow": False,
            "text": f"kₕ,lim = {kh_limit:.3f}",
            "font": {"size": 10, "color": COL["critical"]},
            "xanchor": "left", "xshift": 4, "yanchor": "top",
        })
    ann.append({
        "x": pt_x, "y": kae_design, "showarrow": False,
        "text": (f"Kₐₑ = {kae_design:.3f}" if mo_valid
                 else f"Kₐₑ,lim = {kae_design:.3f}"),
        "font": {"size": 11,
                 "color": COL["ink"] if mo_valid else COL["critical"]},
        "yshift": 16, "xanchor": "center",
    })

    layout = _base_layout(height=440)
    layout.update({
        "xaxis": {**_axis("Horizontal seismic coefficient kₕ"),
                  "range": [0, kh_max_plot * 1.02]},
        "yaxis": _axis("Seismic active coefficient Kₐₑ"),
        "legend": {"orientation": "h", "x": 0, "y": 1.14, "xanchor": "left",
                   "font": {"size": 11, "color": COL["ink2"]}},
        "annotations": ann,
        "shapes": shapes,
        "hovermode": "closest",
    })
    return {"traces": traces, "layout": layout}


# ---------------------------------------------------------------------------
# Figure 4 — lateral pressure distribution with depth
# ---------------------------------------------------------------------------

def _fig_pressure(H, g, ka, kae, kv, c_prime, z_crack, zc_a=0.0):
    n = 40
    zs = [H * i / n for i in range(n + 1)]
    if c_prime > 0:
        sqrt_kae = math.sqrt(kae)
        sqrt_ka = math.sqrt(ka)
        stat = [max(g * z * ka - 2 * c_prime * sqrt_ka, 0.0) for z in zs]
        seis = [max(kae * (1 - kv) * g * z - 2 * c_prime * sqrt_kae, 0.0) for z in zs]
    else:
        stat = [g * z * ka for z in zs]
        seis = [kae * (1 - kv) * g * z for z in zs]

    traces = [
        {
            "x": stat, "y": zs, "mode": "lines",
            "line": {"color": COL["static"], "width": 2},
            "name": "Static  σₐ = Kₐγz",
            "hovertemplate": "z = %{y:.2f} m<br>σ = %{x:.2f} kPa<extra>Static</extra>",
        },
        {
            "x": seis, "y": zs, "mode": "lines",
            "line": {"color": COL["seismic"], "width": 2},
            "fill": "tonextx", "fillcolor": "rgba(235,104,52,0.12)",
            "name": "Seismic  σₐₑ (M-O)",
            "hovertemplate": "z = %{y:.2f} m<br>σ = %{x:.2f} kPa<extra>Seismic</extra>",
        },
    ]

    ann = [{
        "x": (stat[-1] + seis[-1]) / 2, "y": H * 0.97, "showarrow": False,
        "text": "Δσ (dynamic increment)",
        "font": {"size": 10, "color": COL["increment"]},
        "xanchor": "center", "yshift": 10,
    }]
    if c_prime > 0 and 0 < z_crack < H:
        ann.append({
            "x": max(seis) * 0.55, "y": z_crack, "showarrow": False,
            "text": f"tension crack z = {z_crack:.2f} m",
            "font": {"size": 10, "color": "#7f1d1d"}, "yshift": -8,
        })

    layout = _base_layout(height=440)
    layout.update({
        "xaxis": _axis("Lateral pressure σ (kPa)"),
        "yaxis": {**_axis("Depth below crest z (m)"), "autorange": "reversed"},
        "legend": {"orientation": "h", "x": 0, "y": 1.14, "xanchor": "left",
                   "font": {"size": 11, "color": COL["ink2"]}},
        "annotations": ann,
        "hovermode": "y unified",
    })
    return {"traces": traces, "layout": layout}
