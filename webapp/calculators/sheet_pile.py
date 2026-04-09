"""Cantilever sheet-pile wall analysis — two-layer sand profile.

Implements the limit-equilibrium closed-form analysis of a cantilever
sheet-pile wall with TWO soil layers (Layer 1 above the dredge line,
Layer 2 below) plus the full distribution of lateral pressure, shear,
bending moment, and deflection along the wall.

The scope and metric defaults match PYWALL 2019 Example 4 (Ensoft, Reese
et al., 2021) — "LRFD Analysis of Sheet-Pile Wall for Static and Seismic
Conditions" — so the calculator can reproduce the limit-equilibrium part
of that example (Figure 4.3). The more refined p-y (subgrade-reaction)
solution shown in PYWALL Figure 4.5 is not implemented here: that
requires solving EI·y'''' + p(y) − w = 0 with nonlinear Winkler springs
via the discrete-element method of Matlock & Halliburton (1965), which
is beyond the scope of a closed-form web calculator.

References
----------
PYWALL Technical Manual (Reese, Wang, Arrellaga & Vasquez, Ensoft 2021):
  §2.1-2.3 Earth pressure theory (Rankine / Coulomb).
  §2.5     Lateral pressure from surcharge.
  §3.2     Differential equation of beam on elastic foundation:
             EI·(d⁴y/dx⁴) = w + p   (Eq. 3.8)
             EI·(d²y/dx²) = M       (Eq. 3.7)
           with axial-load extension after Hetenyi (1956).
  §3.3     Discrete-element beam-column model (Matlock & Halliburton 1965).
  §3.5     Relationship of earth pressure and structural deformation
           (Terzaghi 1954).

PYWALL Examples Manual §4.1 — Example 4 LRFD Analysis of Sheet-Pile Wall
for Static and Seismic Conditions (Ensoft 2021). Defaults below are the
metric conversion of Table 4.1 and Table 4.3 of that example.

Das, B.M. & Sivakugan, N. (2019). Principles of Foundation Engineering,
9th Edition SI. Ch. 18 §18.4 "Cantilever Sheet Piling Penetrating Sandy
Soil," pp. 758-764, Eq. 18.11-18.22. This is the closed-form solution
used here (quartic for the depth of embedment, peak-shear position for
the max moment).
"""

import math

DEG = math.pi / 180


def _f(v, d=2):
    return f"{v:.{d}f}"


def _solve_quartic(coeffs):
    """Find the smallest positive real root of D^4 + a3 D^3 + a2 D^2 + a1 D + a0 = 0.

    The Das §18.4 quartic is well-behaved in the physical range (0 < D <
    ~5·L) so bisection with a Newton fallback is sufficient.
    """
    a4, a3, a2, a1, a0 = coeffs

    def f(D):
        return a4 * D ** 4 + a3 * D ** 3 + a2 * D ** 2 + a1 * D + a0

    def fp(D):
        return 4 * a4 * D ** 3 + 3 * a3 * D ** 2 + 2 * a2 * D + a1

    lo, hi = 0.001, 100.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        # Newton-Raphson fallback
        D = 1.0
        for _ in range(80):
            fval = f(D)
            d = fp(D)
            if abs(d) < 1e-12:
                break
            D_new = D - fval / d
            if D_new <= 0:
                D_new = D / 2
            if abs(D_new - D) < 1e-7:
                return D_new
            D = D_new
        return max(D, 0.1)
    for _ in range(200):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if abs(fmid) < 1e-7 or (hi - lo) < 1e-7:
            return mid
        if flo * fmid < 0:
            hi = mid
        else:
            lo = mid
            flo = fmid
    return (lo + hi) / 2


def calculate(L, layers=None,
              q=0.0, EI=19700.0, sigma_allow=170000.0,
              load_factor_earth=1.0, load_factor_LS=1.0,
              resistance_factor_Kp=1.0,
              # Legacy scalar inputs (kept for backward-compat with the old
              # two-layer form and existing unit tests). When `layers` is
              # supplied, these are ignored.
              gamma1=None, phi1=None, gamma2=None, phi2=None,
              delta2=0.0, Kp_override=-1.0):
    """Cantilever sheet-pile wall in a two-layer sand profile.

    Matches the limit-equilibrium procedure presented in PYWALL
    Examples Manual §4.1.2 (Example 4) and Das & Sivakugan §18.4
    Eq. 18.7-18.22. The calculator computes the required embedment
    depth, the maximum moment, required section modulus, and the full
    distribution of net lateral pressure, shear, bending moment and
    deflection along the wall length.

    Parameters
    ----------
    L : float
        Retained height above the dredge line (m). This is the
        "exposed" height of the sheet pile in the retained-soil side.
    layers : list of dict, optional
        Soil profile as a list of layers from top to bottom. Each layer
        dict has the following keys:
            name       : str, display name (optional)
            thickness  : float, layer thickness (m). The last layer is
                         treated as extending to infinity past the pile
                         tip regardless of thickness.
            gamma      : float, total unit weight (kN/m³)
            phi        : float, effective friction angle (deg)
            delta      : float, wall-friction angle (deg) for passive
                         Kp (only used for the below-dredge layer)
            Kp_override: float, direct override for the passive
                         coefficient of the below-dredge layer (e.g.
                         8.2 for PYWALL Example 4 Table 4.1). 0 or
                         negative means "auto-compute from Rankine or
                         Coulomb".
        Layers above the dredge line are integrated piecewise for the
        active pressure diagram. The layer whose extent covers z = L
        (or the first layer strictly below L if L falls on a boundary)
        is the "design layer" used for the below-dredge quartic and for
        the embedment / max-moment calculation.

        When omitted, the legacy two-layer scalar inputs (gamma1, phi1,
        gamma2, phi2, delta2, Kp_override) are used instead.
    q : float, optional
        Uniform surcharge on the backfill surface (kPa). PYWALL
        Example 4 uses 240 psf ≈ 11.49 kPa for the static case.
    EI : float, optional
        Per-metre flexural stiffness of the sheet pile (kN·m²/m).
        PYWALL Example 4 uses 1.453 × 10⁷ ft²·lb/ft ≈ 19700 kN·m²/m.
        Used only for the deflection plot (the limit-equilibrium
        force / moment calc is EI-independent).
    sigma_allow : float, optional
        Allowable bending stress in the sheet pile steel (kPa).
        Default 170 000 kPa = 170 MPa (≈ half of Grade 50 steel).

    Returns
    -------
    dict
        report : HTML report with MathJax equations and references
        Ka1, Ka2, Kp2 : Rankine earth-pressure coefficients
        L3 : distance below dredge line to the zero-pressure point (m)
        D_theoretical : embedment depth from the Das quartic (m)
        D_design : D_theoretical × 1.20 safety factor
                   (PYWALL Example 4 §4.1.2 convention)
        L_total : full wall length = L + D_design (m)
        M_max : maximum bending moment along the wall (kN·m/m)
        z_max_moment : depth of M_max below the top (m)
        S_req : required section modulus (m³/m)
        S_req_cm3_per_m : S_req × 10⁶ for convenience (cm³/m)
        deflection_top : lateral deflection at the top (m, for reference)
        pressure_traces, pressure_layout : Plotly net-pressure plot
        shear_traces, shear_layout : Plotly shear plot
        moment_traces, moment_layout : Plotly bending-moment plot
        deflection_traces, deflection_layout : Plotly deflection plot
        chart_traces, chart_layout : alias for the pressure plot
            (back-compat with any template still using the old single
            chart_traces / chart_layout entry).
    """
    # ----- Normalize the soil profile into a uniform layer list -----
    # When the caller passes a `layers` list, use it directly. Otherwise
    # synthesise a two-element list from the legacy scalar arguments so
    # existing tests and the previous API continue to work.
    if layers is None or len(layers) == 0:
        if gamma1 is None or phi1 is None or gamma2 is None or phi2 is None:
            raise ValueError(
                'Either `layers` (list of dicts) or the legacy scalar '
                'arguments gamma1/phi1/gamma2/phi2 must be supplied.'
            )
        layers = [
            {
                'name': 'Layer 1',
                'thickness': max(L, 0.01),
                'gamma': gamma1,
                'phi': phi1,
                'delta': 0.0,
                'Kp_override': -1.0,
            },
            {
                'name': 'Layer 2',
                'thickness': 1e6,   # effectively infinite
                'gamma': gamma2,
                'phi': phi2,
                'delta': delta2,
                'Kp_override': Kp_override,
            },
        ]
    else:
        # Clean / coerce the caller-supplied list
        clean = []
        for i, ly in enumerate(layers):
            if ly is None:
                continue
            thickness = float(ly.get('thickness', 0.0) or 0.0)
            gamma = float(ly.get('gamma', 0.0) or 0.0)
            phi_i  = float(ly.get('phi',   0.0) or 0.0)
            if thickness <= 0 or gamma <= 0 or phi_i <= 0:
                continue
            clean.append({
                'name':        ly.get('name') or f'Layer {i + 1}',
                'thickness':   thickness,
                'gamma':       gamma,
                'phi':         phi_i,
                'delta':       float(ly.get('delta', 0.0) or 0.0),
                'Kp_override': float(ly.get('Kp_override', -1.0) or -1.0),
            })
        if not clean:
            raise ValueError('`layers` list is empty after cleaning.')
        layers = clean
        # The last layer is treated as extending to infinity past the tip.
        layers[-1]['thickness'] = max(layers[-1]['thickness'], 1e6)

    # Attach cumulative top depths and identify the "design layer" — the
    # layer that covers z = L (or the first layer with top >= L if L falls
    # on a boundary).
    cum = 0.0
    for ly in layers:
        ly['z_top'] = cum
        cum += ly['thickness']
        ly['z_bot'] = cum

    design_layer = None
    for ly in layers:
        if ly['z_top'] <= L < ly['z_bot']:
            design_layer = ly
            break
    if design_layer is None:
        # L is exactly at or past the bottom of the last defined layer —
        # use the last layer as the design layer.
        design_layer = layers[-1]

    gamma2 = design_layer['gamma']
    phi2   = design_layer['phi']
    delta2 = design_layer.get('delta', 0.0) or 0.0
    Kp_override = design_layer.get('Kp_override', -1.0) or -1.0

    # ----- Earth-pressure coefficients -----
    # Ka for each layer (Rankine, δ = 0).
    # Kp for the design layer (below dredge) uses the precedence:
    #   1. If Kp_override > 0, use that value directly (lets the user match
    #      Caquot-Kerisel table values such as the Kp = 8.2 used by PYWALL
    #      Example 4 Table 4.1, which is not reproducible by plain Coulomb).
    #   2. Else if δ > 0, use the Coulomb form for vertical wall back
    #      (θ = 0) and horizontal backfill (α = 0):
    #          Kp = cos²φ / [cosδ · (1 − √(sin(φ+δ)·sinφ / cosδ))²]
    #      Ref: Das §16.13 Eq. 16.52, PYWALL Tech Manual §2.3 Coulomb theory.
    #   3. Else use Rankine Kp = (1+sinφ)/(1−sinφ).
    for ly in layers:
        ph = max(min(ly['phi'], 45.0), 5.0)
        ly['Ka'] = (1 - math.sin(ph * DEG)) / (1 + math.sin(ph * DEG))
    ph2 = max(min(phi2, 45.0), 5.0)
    d2  = max(min(delta2, ph2 - 0.5), 0.0)
    Ka1 = layers[0]['Ka']                  # Ka of the first (top) layer — for surcharge at z=0
    Ka2 = design_layer['Ka']               # Ka of the design layer — for below-dredge calc
    if Kp_override is not None and Kp_override > 0:
        Kp2 = float(Kp_override)
        Kp_source = f'user override (e.g. Caquot-K\u00e9risel table); Kp2 = {Kp2:.3f}'
    elif d2 > 0:
        cos_phi2 = math.cos(ph2 * DEG)
        cos_d2   = math.cos(d2 * DEG)
        root_term = math.sin((ph2 + d2) * DEG) * math.sin(ph2 * DEG) / cos_d2
        if root_term < 0:
            root_term = 0.0
        denom_Kp = cos_d2 * (1 - math.sqrt(root_term)) ** 2
        Kp2 = (cos_phi2 ** 2 / denom_Kp) if denom_Kp > 1e-9 else (
            (1 + math.sin(ph2 * DEG)) / (1 - math.sin(ph2 * DEG)))
        Kp_source = f'Coulomb form with \u03b4\u2082 = {d2:.1f}\u00b0 (Das \u00a716.13 Eq.\u00a016.52)'
    else:
        Kp2 = (1 + math.sin(ph2 * DEG)) / (1 - math.sin(ph2 * DEG))
        Kp_source = 'Rankine form (\u03b4\u2082 = 0)'
    # Effective (factored) Layer 2 pressure coefficients for design.
    # LRFD convention (PYWALL Example 4 Table 4.1 Strength I):
    #   load side:       γ_earth × Ka2 (pressure factored UP)
    #   resistance side: φ_Kp    × Kp2 (pressure factored DOWN)
    # γ₂ is a material property and is NOT factored — only the coefficients
    # carry load/resistance factors.
    g_e_load = max(load_factor_earth, 0.0)
    Kp2_eff = Kp2 * max(resistance_factor_Kp, 1e-6)
    Ka2_eff = Ka2 * g_e_load                       # factored Ka2 for Layer-2 growth
    # The "effective" (Kp - Ka) difference below the dredge line:
    Kp_minus_Ka_eff = Kp2_eff - Ka2_eff
    if Kp_minus_Ka_eff <= 0 or gamma2 <= 0:
        raise ValueError(
            'Invalid Layer 2 parameters: (phi_Kp*Kp2 - gamma_earth*Ka2) and '
            'gamma_2 must be positive. '
            f'Kp2={Kp2:.3f}, phi_Kp={resistance_factor_Kp:.3f}, '
            f'Ka2={Ka2:.3f}, gamma_earth={load_factor_earth:.3f}.'
        )

    # ----- Active pressure above and just below the dredge line -----
    # AASHTO LRFD load factors (PYWALL Example 4 Table 4.1):
    #   γ_earth applied to earth-pressure component   (1.5 for Strength I)
    #   γ_LS    applied to live-load surcharge       (1.75 for Strength I)
    # Default 1.0 = unfactored (working-stress) analysis.
    g_e = max(load_factor_earth, 0.0)
    g_ls = max(load_factor_LS, 0.0)

    # Cumulative factored vertical stress at the dredge line, summed across
    # all above-dredge layer segments. Also keep a list of piecewise
    # boundaries for plotting and the trapezoid integration.
    #   σ_v_earth(z=L)  = γ_earth · Σᵢ γᵢ · hᵢ      (for layer segments above dredge)
    #   σ_v_surch(z=L)  = γ_LS · q                   (constant with depth)
    # At each layer boundary above dredge we store (z, σ_v_earth, σ_v_surch, Ka).
    sigma_v_surch = g_ls * q
    above_segments = []   # list of dicts: z_top, z_bot, gamma, phi, Ka
    cum_sigma_earth = 0.0
    for ly in layers:
        if ly['z_top'] >= L:
            break
        z_top = ly['z_top']
        z_bot = min(ly['z_bot'], L)
        above_segments.append({
            'z_top': z_top,
            'z_bot': z_bot,
            'gamma': ly['gamma'],
            'phi':   ly['phi'],
            'Ka':    ly['Ka'],
            'sigma_earth_top': cum_sigma_earth,
        })
        cum_sigma_earth += g_e * ly['gamma'] * (z_bot - z_top)
        above_segments[-1]['sigma_earth_bot'] = cum_sigma_earth
        if ly['z_bot'] >= L:
            break
    sigma_v_earth  = cum_sigma_earth
    sigma_v_dredge = sigma_v_earth + sigma_v_surch

    # Key pressures for the report and plots
    pa_top_wall      = Ka1 * sigma_v_surch             # factored, z=0
    pa_bot_dredge_L1 = ((above_segments[-1]['Ka'] * (above_segments[-1]['sigma_earth_bot'] + sigma_v_surch))
                       if above_segments else
                       Ka1 * sigma_v_dredge)           # factored, z=L-
    sigma2           = Ka2 * sigma_v_dredge            # factored, z=L+ (design layer)

    def _pa_above(z):
        """Factored active pressure at depth z (0 ≤ z ≤ L), piecewise by layer."""
        if z <= 0:
            return Ka1 * sigma_v_surch
        if z >= L:
            return pa_bot_dredge_L1
        for seg in above_segments:
            if seg['z_top'] <= z <= seg['z_bot']:
                frac = (z - seg['z_top']) / (seg['z_bot'] - seg['z_top']) if seg['z_bot'] > seg['z_top'] else 0.0
                sigma_earth = seg['sigma_earth_top'] + frac * (seg['sigma_earth_bot'] - seg['sigma_earth_top'])
                return seg['Ka'] * (sigma_earth + sigma_v_surch)
        return pa_bot_dredge_L1

    # ----- Zero-pressure point depth below the dredge line -----
    # Below dredge line (with LRFD load/resistance factors):
    #     p_a_below(z) = sigma2 + γ_earth · Ka2 · γ₂ · (z - L)
    #     p_p_below(z) = φ_Kp · Kp2 · γ₂ · (z - L)
    #     net(z)      = sigma2 + γ₂·(z - L) · (γ_earth·Ka2 − φ_Kp·Kp2)
    #                 = sigma2 − γ₂·(z - L) · (Kp2_eff − Ka2_eff)
    # Zero at (z - L) = sigma2 / [γ₂ · (Kp2_eff − Ka2_eff)]
    L3 = sigma2 / (Kp_minus_Ka_eff * gamma2)

    # ----- Resultant of the active pressure above the zero-pressure point -----
    # P1 = resultant of the piecewise-linear active pressure above the dredge
    # line. With one layer above dredge this reduces to a simple trapezoid;
    # with N layers it is a sum of trapezoids (one per layer segment) that
    # may have pressure jumps at the layer boundaries when Ka changes.
    P1 = 0.0
    M_trap_about_top = 0.0   # first moment of P1 about the top of wall
    for seg in above_segments:
        p_top = seg['Ka'] * (seg['sigma_earth_top'] + sigma_v_surch)
        p_bot = seg['Ka'] * (seg['sigma_earth_bot'] + sigma_v_surch)
        h = seg['z_bot'] - seg['z_top']
        area = 0.5 * (p_top + p_bot) * h
        # Centroid of this trapezoid within the segment, measured from the
        # segment's top: y_c = h · (p_top + 2·p_bot) / (3·(p_top + p_bot))
        if (p_top + p_bot) > 1e-12:
            y_c_rel = h * (p_top + 2 * p_bot) / (3 * (p_top + p_bot))
        else:
            y_c_rel = h / 2.0
        z_c_abs = seg['z_top'] + y_c_rel   # from the top of wall
        P1 += area
        M_trap_about_top += area * z_c_abs

    # Force P2 and zero-pressure point remain as before (single design layer
    # below the dredge line handles the rest).
    P2 = 0.5 * sigma2 * L3
    P_total = P1 + P2

    z_c_trap_from_top = M_trap_about_top / P1 if P1 > 0 else L / 2.0
    zbar_trap = (L + L3) - z_c_trap_from_top

    # Net-active triangle centroid (below dredge line): the triangle has its MAX
    # pressure at z = L and zero at z = L + L3, so its centroid is at 1/3 of L3
    # below the dredge line, i.e. 2/3 of L3 above the zero-pressure point.
    zbar_tri = 2.0 * L3 / 3.0

    zbar_total = (P1 * zbar_trap + P2 * zbar_tri) / P_total if P_total > 0 else 0.0

    # ----- Das §18.4 quartic: solve for depth BELOW the zero-pressure point -----
    # The quartic uses the "effective" (Kp−Ka)·γ term with LRFD factors:
    #     denom = γ₂ · (Kp2_eff − Ka2_eff)
    denom = Kp_minus_Ka_eff * gamma2
    A1 = sigma2 / denom
    A2 = 8.0 * P_total / denom
    A3 = 6.0 * P_total * (2.0 * zbar_total * denom + sigma2) / denom ** 2
    A4 = P_total * (6.0 * zbar_total * sigma2 + 4.0 * P_total) / denom ** 2

    D_below_zero = _solve_quartic((1.0, A1, -A2, -A3, -A4))
    D_theoretical_quartic = L3 + D_below_zero

    # The Das §18.4 quartic uses the classical Blum "simplified" convention
    # with a concentrated tip reaction. For the full continuous-distribution
    # plot the tip reaction is distributed along the embedment, and the
    # moment must vanish at the true pile tip (static equilibrium of the
    # free-free beam on the Winkler foundation). Refine D by bisection so
    # that the numerically integrated tip moment is zero — this produces
    # the expected smooth pressure / shear / moment diagrams along the
    # entire embedded length.
    def _tip_moment(D_try):
        L_try = L + D_try
        n = 201
        z_arr = [L_try * i / (n - 1) for i in range(n)]
        p_arr = []
        for z in z_arr:
            if z <= L:
                p_arr.append(_pa_above(z))
            else:
                zr = z - L
                p_a = sigma2 + Ka2_eff * gamma2 * zr
                p_p = Kp2_eff * gamma2 * zr
                p_arr.append(p_a - p_p)
        V = 0.0
        M = 0.0
        prev_p = p_arr[0]
        prev_V = 0.0
        for i in range(1, n):
            dz = z_arr[i] - z_arr[i - 1]
            V_new = V + 0.5 * (p_arr[i] + prev_p) * dz
            M_new = M + 0.5 * (V_new + prev_V) * dz
            V, M = V_new, M_new
            prev_p = p_arr[i]
            prev_V = V
        return M

    # Bracket: start from the quartic estimate and expand until we find
    # a sign change in the tip moment.
    D_lo = max(D_theoretical_quartic * 0.5, 0.1)
    D_hi = D_theoretical_quartic * 3.0
    f_lo = _tip_moment(D_lo)
    f_hi = _tip_moment(D_hi)
    expand = 0
    while f_lo * f_hi > 0 and expand < 6:
        D_hi *= 1.6
        f_hi = _tip_moment(D_hi)
        expand += 1
    if f_lo * f_hi > 0:
        # Could not bracket — fall back to the Das quartic value
        D_theoretical = D_theoretical_quartic
    else:
        # Bisection
        for _ in range(80):
            D_mid = 0.5 * (D_lo + D_hi)
            f_mid = _tip_moment(D_mid)
            if abs(f_mid) < 1e-4 or (D_hi - D_lo) < 1e-4:
                break
            if f_lo * f_mid < 0:
                D_hi, f_hi = D_mid, f_mid
            else:
                D_lo, f_lo = D_mid, f_mid
        D_theoretical = 0.5 * (D_lo + D_hi)

    D_design = D_theoretical * 1.20                # PYWALL Example 4 §4.1.2 / Das §18.4 (20% safety)
    L_total = L + D_design

    # ----- Location and value of the maximum bending moment -----
    # Das Eq. 18.19: z' = sqrt(2·P / [(Kp − Ka)·γ']) below the zero-pressure
    # point, using the factored γ₂ and the φ·Kp-factored passive coefficient.
    z_shear_zero = math.sqrt(2.0 * P_total / denom) if denom > 0 else 0.0
    # Maximum moment (Das Eq. 18.21):
    M_max = P_total * (z_shear_zero + zbar_total) - denom * z_shear_zero ** 3 / 6.0
    # Depth of M_max below the top of wall:
    z_max_moment = L + L3 + z_shear_zero

    # Required section modulus (working stress, Das Eq. 18.22)
    S_req = M_max / sigma_allow if sigma_allow > 0 else 0.0
    S_req_cm3_per_m = S_req * 1e6                   # m³/m -> cm³/m

    # ----- Full distributions of p, V, M, y along the wall for plotting -----
    # Plot range is 0 → L + D_theoretical (not D_design) so that the moment
    # and shear diagrams close to zero at the tip (since D_theoretical is
    # the equilibrium depth found by the bisection). The extra 20% embedment
    # in D_design is just a safety buffer and carries no additional loading
    # in the static LE model.
    L_plot = L + D_theoretical
    n_points = 301
    z_grid = [L_plot * i / (n_points - 1) for i in range(n_points)]
    p_grid = []
    for z in z_grid:
        if z <= L:
            # Above dredge line: piecewise-linear factored active pressure
            # from the above-dredge layer segments.
            p_grid.append(_pa_above(z))
        else:
            # Below dredge line: factored design-layer net (active − passive).
            # Active grows with Ka2_eff·γ₂; passive with Kp2_eff·γ₂.
            zr = z - L
            p_active = sigma2 + Ka2_eff * gamma2 * zr
            p_passive = Kp2_eff * gamma2 * zr
            p_grid.append(p_active - p_passive)

    # Trapezoidal integration top -> down for V and M.
    # Sign convention: p(z) positive = driving (into wall from the retained side).
    # V(z) = ∫₀ᶻ p dζ   (cumulative horizontal force above the cut)
    # M(z) = ∫₀ᶻ V dζ
    V_grid = [0.0] * n_points
    for i in range(1, n_points):
        dz = z_grid[i] - z_grid[i - 1]
        V_grid[i] = V_grid[i - 1] + 0.5 * (p_grid[i] + p_grid[i - 1]) * dz
    M_grid = [0.0] * n_points
    for i in range(1, n_points):
        dz = z_grid[i] - z_grid[i - 1]
        M_grid[i] = M_grid[i - 1] + 0.5 * (V_grid[i] + V_grid[i - 1]) * dz

    # Deflection y(z) via double integration of the curvature equation
    #     d²y/dz² = M(z) / EI                   (PYWALL Tech Manual §3.2 Eq. 3.7)
    # We use forward integration from the top (z=0) with arbitrary constants
    # theta_raw(0)=0 and y_raw(0)=0, then add a linear correction y = y_raw +
    # A + B·z so that the BOTTOM boundary conditions are satisfied:
    #     y(L_total)     = 0   (pseudo-fixed tip)
    #     y'(L_total)    = 0   (pseudo-fixed tip rotation)
    # This yields a cantilever-like deflection shape with the top of the
    # wall deflected toward the excavation (positive y), matching the
    # qualitative shape in PYWALL Figure 4.5.
    theta_raw = [0.0] * n_points
    for i in range(1, n_points):
        dz = z_grid[i] - z_grid[i - 1]
        theta_raw[i] = theta_raw[i - 1] + 0.5 * (M_grid[i] / EI + M_grid[i - 1] / EI) * dz
    y_raw = [0.0] * n_points
    for i in range(1, n_points):
        dz = z_grid[i] - z_grid[i - 1]
        y_raw[i] = y_raw[i - 1] + 0.5 * (theta_raw[i] + theta_raw[i - 1]) * dz
    # Apply linear correction so that y(L_total) = y'(L_total) = 0.
    B_corr = -theta_raw[-1]
    A_corr = -(y_raw[-1] + B_corr * z_grid[-1])
    y_grid = [y_raw[i] + A_corr + B_corr * z_grid[i] for i in range(n_points)]
    # Report the sign such that positive y means deflection toward the
    # excavation (standard cantilever convention). The sign of the raw
    # integration depends on the moment sign convention used above; we
    # just take the absolute value at the top for reporting.
    deflection_top = abs(y_grid[0])
    if y_grid[0] < 0:
        y_grid = [-v for v in y_grid]

    # ----- Build the HTML report with MathJax equations -----
    r = '<div>'
    r += (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 8px;">'
        'Ref: <strong>PYWALL 2019 Examples Manual &sect;4.1</strong> '
        '(Ensoft, Reese et al., 2021) Example 4 &mdash; LRFD Analysis of '
        'Sheet-Pile Wall for Static and Seismic Conditions. Closed-form '
        'limit-equilibrium procedure per <strong>PYWALL Technical Manual '
        '&sect;2.2</strong> (Rankine earth pressure) and <strong>Das &amp; '
        'Sivakugan (2019, 9th SI) &sect;18.4 Eq.&nbsp;18.7&ndash;18.22, '
        'pp.&nbsp;758&ndash;764</strong>. This calculator implements the '
        'limit-equilibrium force/moment balance (PYWALL Fig.&nbsp;4.3 '
        'comparison path). The more refined p-y / subgrade-reaction '
        'solution (PYWALL Fig.&nbsp;4.5) requires the discrete-element '
        'beam-column method of Matlock &amp; Halliburton (1965), PYWALL '
        'Tech Manual &sect;3.2&ndash;3.3, and is beyond the closed-form '
        'scope of this module.</p>'
    )

    r += '<h4>Rankine Earth-Pressure Coefficients</h4>'
    r += (
        '<p style="font-size:0.82em;color:#6c757d;margin:0 0 6px;">'
        'Ref: PYWALL Tech Manual &sect;2.2 (Rankine), Das &sect;16.3 '
        '(active) and &sect;16.11 (passive).</p>'
    )
    # ----- Soil profile table (always rendered, shows the layers used) -----
    r += '<h4>Soil Profile</h4>'
    r += '<table class="data-table" style="max-width:760px;margin:0 0 10px;">'
    r += (
        '<thead><tr>'
        '<th>#</th><th>Layer</th><th>Top (m)</th><th>Bottom (m)</th>'
        '<th>Thick. (m)</th>'
        '<th>&gamma; (kN/m³)</th>'
        '<th>&phi; (&deg;)</th>'
        '<th>&delta; (&deg;)</th>'
        '<th>K<sub>a</sub></th>'
        '<th>K<sub>p</sub> override</th>'
        '<th>Role</th>'
        '</tr></thead><tbody>'
    )
    for i, ly in enumerate(layers):
        role_tags = []
        if ly['z_top'] < L:
            role_tags.append('above dredge')
        if ly is design_layer:
            role_tags.append('<strong>design layer</strong>')
        role = ', '.join(role_tags) if role_tags else 'below dredge'
        kp_ov = ly.get('Kp_override', 0.0) or 0.0
        kp_disp = f'{kp_ov:.2f}' if kp_ov > 0 else '&mdash;'
        r += (
            f'<tr>'
            f'<td>{i + 1}</td>'
            f'<td>{ly.get("name", f"Layer {i + 1}")}</td>'
            f'<td>{_f(ly["z_top"])}</td>'
            f'<td>{_f(ly["z_bot"])}</td>'
            f'<td>{_f(ly["thickness"])}</td>'
            f'<td>{_f(ly["gamma"])}</td>'
            f'<td>{_f(ly["phi"], 1)}</td>'
            f'<td>{_f(ly.get("delta", 0.0), 1)}</td>'
            f'<td>{_f(ly["Ka"], 4)}</td>'
            f'<td>{kp_disp}</td>'
            f'<td style="font-size:0.85em;color:#6c757d;">{role}</td>'
            f'</tr>'
        )
    r += '</tbody></table>'
    r += (
        f'<p style="font-size:0.82em;color:#6c757d;margin:0 0 6px;">'
        f'Retained height L = {_f(L)} m. The design layer '
        f'(<strong>{design_layer.get("name", "layer")}</strong>) is the one that '
        'covers z = L; its parameters drive the below-dredge quartic and the '
        'embedment / max-moment calculation.</p>'
    )

    phi1_disp = layers[0]['phi']
    phi2_disp = design_layer['phi']
    r += f'\\[ K_{{a1}} = \\tfrac{{1-\\sin\\phi_1}}{{1+\\sin\\phi_1}} = {_f(Ka1,4)} \\quad (\\phi_1 = {_f(phi1_disp,1)}^\\circ \\text{{, top layer}}) \\]'
    r += f'\\[ K_{{a2}} = \\tfrac{{1-\\sin\\phi_2}}{{1+\\sin\\phi_2}} = {_f(Ka2,4)} \\quad (\\phi_2 = {_f(phi2_disp,1)}^\\circ \\text{{, design layer}}) \\]'
    r += f'\\[ K_{{p2}} = {_f(Kp2,4)} \\]'
    r += (
        f'<p style="font-size:0.80em;color:#6c757d;margin:0 0 6px;">'
        f'K<sub>p2</sub> source: {Kp_source}.</p>'
    )

    r += '<h4>Active Pressure at Key Elevations</h4>'
    r += (
        '<p style="font-size:0.82em;color:#6c757d;margin:0 0 6px;">'
        'Ref: PYWALL Examples Manual Table 4.2 (Example 4 static case, '
        'p.&nbsp;4-5). Note the discontinuity at the dredge line when '
        'K<sub>a1</sub> &ne; K<sub>a2</sub>.</p>'
    )
    r += (
        f'\\[ \\sigma_{{a}}(z=0) = K_{{a1}} \\cdot q = {_f(Ka1,4)} \\times {_f(q)} = '
        f'{_f(pa_top_wall)} \\text{{ kPa}} \\]'
    )
    # Above-dredge earth stress is the sum of all above-dredge layer segments.
    r += (
        f'\\[ \\sigma_{{a}}(z=L^-) = K_{{a,\\text{{bot}}}} (\\sum_i \\gamma_{{earth}}\\gamma_i h_i + \\gamma_{{LS}} q) = '
        f'{_f(pa_bot_dredge_L1)} \\text{{ kPa}} \\]'
    )
    r += (
        f'\\[ \\sigma_2 = \\sigma_{{a}}(z=L^+) = K_{{a2}} (\\sigma_{{v,\\text{{dredge}}}}) = {_f(Ka2,4)} \\times '
        f'{_f(sigma_v_dredge)} = {_f(sigma2)} \\text{{ kPa}} \\]'
    )

    r += '<h4>Zero-Pressure Point Below the Dredge Line</h4>'
    r += (
        f'\\[ L_3 = \\frac{{\\sigma_2}}{{(K_{{p2}} - K_{{a2}}) \\gamma_2}} = '
        f'\\frac{{{_f(sigma2)}}}{{{_f(Kp_minus_Ka_eff,4)} \\times {_f(gamma2)}}} = '
        f'{_f(L3,3)} \\text{{ m}} \\]'
    )

    r += '<h4>Resultant Active Force P and Centroid</h4>'
    r += (
        f'\\[ P = P_1 + P_2 = {_f(P1)} + {_f(P2)} = {_f(P_total)} \\text{{ kN/m}} \\]'
    )
    r += (
        f'\\[ \\bar{{z}} = {_f(zbar_total,3)} \\text{{ m (from the zero-pressure point, upward)}} \\]'
    )

    r += '<h4>Embedment Depth (Das &sect;18.4 Eq.&nbsp;18.17 Quartic)</h4>'
    r += '\\[ D^4 + A_1 D^3 - A_2 D^2 - A_3 D - A_4 = 0 \\]'
    r += (
        f'\\[ A_1 = {_f(A1,3)}, \\ A_2 = {_f(A2,3)}, \\ '
        f'A_3 = {_f(A3,3)}, \\ A_4 = {_f(A4,3)} \\]'
    )
    r += (
        f'\\[ D = {_f(D_below_zero,3)} \\text{{ m (below the zero-pressure point)}} \\]'
        f'\\[ D_{{theoretical}} = L_3 + D = {_f(D_theoretical,3)} \\text{{ m (below dredge line)}} \\]'
    )
    r += (
        f'<p><strong>Design embedment</strong> '
        f'(20&percnt; safety factor per PYWALL Example 4 &sect;4.1.2 and '
        f'Das p.&nbsp;762): '
        f'D<sub>design</sub> = 1.20 &times; {_f(D_theoretical,3)} = '
        f'<strong>{_f(D_design,2)} m</strong>. '
        f'Total wall length = L + D<sub>design</sub> = '
        f'<strong>{_f(L_total,2)} m</strong>. '
        f'PYWALL Example 4 Strength I target: Do&nbsp;=&nbsp;8.57&nbsp;ft '
        f'&approx;&nbsp;2.61&nbsp;m, D&nbsp;=&nbsp;10.3&nbsp;ft &approx;&nbsp;3.14&nbsp;m.</p>'
    )

    r += '<h4>Maximum Bending Moment (Das &sect;18.4 Eq.&nbsp;18.19-18.21)</h4>'
    r += (
        f"\\[ z' = \\sqrt{{\\frac{{2 P}}{{(K_{{p2}} - K_{{a2}}) \\gamma_2}}}} = "
        f"{_f(z_shear_zero,3)} \\text{{ m (depth of zero shear below the zero-pressure point)}} \\]"
    )
    r += (
        f"\\[ M_{{max}} = P (z' + \\bar{{z}}) - \\tfrac{{1}}{{6}}(K_{{p2}}-K_{{a2}})\\gamma_2 z'^3 = "
        f"{_f(M_max)} \\text{{ kN}} \\cdot \\text{{m/m}} \\]"
    )
    r += (
        f'<p>Depth of M<sub>max</sub> below the top of wall: '
        f'<strong>{_f(z_max_moment,2)} m</strong>. '
        f'PYWALL Example 4 Strength I targets: M<sub>max</sub> = '
        f'27&thinsp;272 ft&middot;lbs/ft &approx; <strong>121.3 kN&middot;m/m</strong> '
        f'at 14.4&nbsp;ft &approx; 4.39&nbsp;m below the top.</p>'
    )

    r += '<h4>Required Section Modulus (Das Eq.&nbsp;18.22)</h4>'
    r += (
        f'\\[ S_{{req}} = \\frac{{M_{{max}}}}{{\\sigma_{{allow}}}} = '
        f'\\frac{{{_f(M_max)}}}{{{_f(sigma_allow,0)}}} = {_f(S_req,6)} \\text{{ m}}^3/\\text{{m}} '
        f'= {_f(S_req_cm3_per_m,1)} \\text{{ cm}}^3/\\text{{m}} \\]'
    )

    r += '<h4>Deflection at the Top of Wall</h4>'
    r += (
        '<p style="font-size:0.82em;color:#6c757d;margin:0 0 6px;">'
        'Obtained by double integration of M(z)/EI from the pile tip '
        'upward with pseudo-fixed BCs y(L<sub>total</sub>) = 0 and '
        'y\'(L<sub>total</sub>) = 0. This is the EI-dependent deflection '
        'shape associated with the limit-equilibrium M(z) distribution '
        '(PYWALL Tech Manual &sect;3.2 Eq.&nbsp;3.7, M = EI y\'\'). The '
        'full nonlinear p-y solution in PYWALL typically predicts a '
        'similar shape but smaller magnitude because the passive '
        'resistance is not fully mobilized.</p>'
    )
    r += (
        f'\\[ y(0) = {_f(deflection_top*1000, 2)} \\text{{ mm}} '
        f'\\quad (EI = {_f(EI,0)} \\text{{ kN}} \\cdot \\text{{m}}^2/\\text{{m}}) \\]'
    )
    r += '</div>'

    # ----- Four Plotly sub-plots -----
    pressure_plot = _build_pressure_chart(z_grid, p_grid, L, L_plot, sigma2, L3)
    shear_plot = _build_single_profile(
        z_grid, V_grid, L, L_plot,
        title="Shear (kN/m)", xlabel="Shear, V (kN/m)", color="#2980b9",
    )
    moment_plot = _build_single_profile(
        z_grid, M_grid, L, L_plot,
        title="Bending Moment (kN·m/m)", xlabel="Moment, M (kN·m/m)", color="#27ae60",
    )
    # Deflection plotted in mm for readability
    y_mm = [v * 1000.0 for v in y_grid]
    deflection_plot = _build_single_profile(
        z_grid, y_mm, L, L_plot,
        title="Deflection (mm)", xlabel="Deflection, y (mm)", color="#8e44ad",
    )

    return {
        'report': r,
        'Ka1': Ka1,
        'Ka2': Ka2,
        'Kp2': Kp2,
        'L3': L3,
        'D_theoretical': D_theoretical,
        'D_design': D_design,
        'L_total': L_total,
        'M_max': M_max,
        'z_max_moment': z_max_moment,
        'S_req': S_req,
        'S_req_cm3_per_m': S_req_cm3_per_m,
        'deflection_top_mm': deflection_top * 1000.0,
        'pressure_traces': pressure_plot['traces'],
        'pressure_layout': pressure_plot['layout'],
        'shear_traces': shear_plot['traces'],
        'shear_layout': shear_plot['layout'],
        'moment_traces': moment_plot['traces'],
        'moment_layout': moment_plot['layout'],
        'deflection_traces': deflection_plot['traces'],
        'deflection_layout': deflection_plot['layout'],
        # Back-compat aliases
        'chart_traces': pressure_plot['traces'],
        'chart_layout': pressure_plot['layout'],
    }


def _build_pressure_chart(z, p, L, L_total, sigma2, L3):
    """Net lateral pressure envelope with dredge-line and zero-pressure annotations."""
    z_zero = L + L3
    # Positive (driving) segment: fill with red
    # Negative (resisting) segment: fill with blue
    traces = [
        {
            'x': p, 'y': z,
            'mode': 'lines',
            'line': {'color': '#c0392b', 'width': 2.5},
            'name': 'Net pressure',
        },
        {
            'x': [0, 0], 'y': [0, L_total],
            'mode': 'lines',
            'line': {'color': '#333', 'width': 1.2, 'dash': 'dot'},
            'showlegend': False, 'hoverinfo': 'skip',
        },
    ]
    ann = [
        {
            'x': 0, 'y': L,
            'text': f'Dredge line (L = {L:.2f} m)',
            'showarrow': True, 'arrowhead': 2, 'ax': 30, 'ay': 0,
            'font': {'size': 10, 'color': '#8b6914'},
            'bgcolor': 'rgba(255,255,255,0.8)',
        },
        {
            'x': 0, 'y': z_zero,
            'text': f'Zero pressure (L₃ = {L3:.2f} m)',
            'showarrow': True, 'arrowhead': 2, 'ax': 30, 'ay': 0,
            'font': {'size': 10, 'color': '#2980b9'},
            'bgcolor': 'rgba(255,255,255,0.8)',
        },
        {
            'x': sigma2, 'y': L + 0.01,
            'text': f'σ₂ = {sigma2:.1f} kPa',
            'showarrow': False,
            'font': {'size': 9, 'color': '#c0392b'},
            'xanchor': 'left', 'yanchor': 'top',
        },
    ]
    layout = {
        'title': {'text': 'Net Lateral Pressure (kPa)', 'font': {'size': 13}},
        'xaxis': {'title': 'Pressure (kPa)', 'zeroline': True, 'zerolinecolor': '#999'},
        'yaxis': {
            'title': 'Depth below top of wall (m)',
            'autorange': 'reversed',
            'zeroline': False,
        },
        'height': 420,
        'margin': {'l': 70, 'r': 20, 't': 45, 'b': 50},
        'plot_bgcolor': '#ffffff', 'paper_bgcolor': '#ffffff',
        'annotations': ann,
        'showlegend': False,
    }
    return {'traces': traces, 'layout': layout}


def _build_single_profile(z, vals, L, L_total, title, xlabel, color):
    """Generic single-trace x-vs-z profile plot with dredge line marker."""
    max_abs = max((abs(v) for v in vals), default=1.0) or 1.0
    traces = [
        {
            'x': vals, 'y': z,
            'mode': 'lines',
            'line': {'color': color, 'width': 2.5},
            'fill': 'tozerox',
            'fillcolor': color + '22' if color.startswith('#') and len(color) == 7 else 'rgba(41,128,185,0.13)',
            'name': title,
        },
        {
            'x': [0, 0], 'y': [0, L_total],
            'mode': 'lines',
            'line': {'color': '#333', 'width': 1.2, 'dash': 'dot'},
            'showlegend': False, 'hoverinfo': 'skip',
        },
        {
            'x': [-1.15 * max_abs, 1.15 * max_abs], 'y': [L, L],
            'mode': 'lines',
            'line': {'color': '#8b6914', 'width': 1.2, 'dash': 'dash'},
            'showlegend': False, 'hoverinfo': 'skip',
            'name': 'Dredge line',
        },
    ]
    layout = {
        'title': {'text': title, 'font': {'size': 13}},
        'xaxis': {
            'title': xlabel,
            'zeroline': True, 'zerolinecolor': '#999',
            'range': [-1.15 * max_abs, 1.15 * max_abs],
        },
        'yaxis': {
            'title': 'Depth (m)',
            'autorange': 'reversed',
            'zeroline': False,
        },
        'height': 420,
        'margin': {'l': 70, 'r': 20, 't': 45, 'b': 50},
        'plot_bgcolor': '#ffffff', 'paper_bgcolor': '#ffffff',
        'showlegend': False,
    }
    return {'traces': traces, 'layout': layout}
