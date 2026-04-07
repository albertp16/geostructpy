"""Bored pile static capacity calculator.

Computes skin resistance (Beta/Alpha methods) and base resistance
per layer from borehole SPT data. References:
  - Beta method (Burland, 1973) for granular soils
  - Alpha method (Tomlinson, 1971) for cohesive soils
  - Bearing capacity factors from Meyerhof (1976)
"""

import math


def _f(v, d=2):
    return f"{v:.{d}f}"


# ---------------------------------------------------------------------------
# Soil classification helpers
# ---------------------------------------------------------------------------

_GRANULAR = {'GM', 'GW', 'GP', 'GC', 'SM', 'SW', 'SP', 'SC'}
_COHESIVE = {'CL', 'CH', 'ML', 'MH', 'OL', 'OH', 'PT'}


def _is_granular(cls):
    return (cls or '').upper() in _GRANULAR


def _is_cohesive(cls):
    return (cls or '').upper() in _COHESIVE


def _is_rock(cls):
    return (cls or '').upper() in ('RK', 'ROCK')


# ---------------------------------------------------------------------------
# SPT correlations
# ---------------------------------------------------------------------------

def _phi_from_spt(n):
    """Friction angle from SPT (Peck, Hanson & Thornburn, 1974)."""
    if n is None or n <= 0:
        return 28
    phi = 27.1 + 0.3 * n - 0.00054 * n * n
    return min(max(phi, 26), 45)


def _cu_from_spt(n):
    """Undrained shear strength Cu (kPa) from SPT (Stroud, 1974)."""
    if n is None or n <= 0:
        return 12.5
    return 6.25 * n


def _gamma_from_spt(n, is_granular=True):
    """Estimate unit weight (kN/m3) from SPT N-value."""
    if n is None or n <= 0:
        return 16.0
    if is_granular:
        return min(14 + 0.15 * n, 22)
    else:
        return min(15 + 0.1 * n, 21)


def _alpha_factor(cu):
    """Adhesion factor alpha for Alpha method (Tomlinson, 1971).

    alpha = 1.0 for Cu <= 25 kPa, linearly decreasing to 0.5 for Cu >= 100 kPa.
    """
    if cu <= 25:
        return 1.0
    elif cu >= 100:
        return 0.5
    else:
        return 1.0 - 0.5 * (cu - 25) / 75


# Bearing capacity factor Nq (Meyerhof, 1976) for driven/bored piles
_NQ_TABLE = {
    26: 10, 28: 15, 30: 21, 32: 29, 34: 40, 36: 55, 38: 77, 40: 109,
    42: 155, 44: 220, 45: 260,
}


def _get_nq(phi):
    """Interpolate Nq from bearing capacity table."""
    keys = sorted(_NQ_TABLE.keys())
    if phi <= keys[0]:
        return _NQ_TABLE[keys[0]]
    if phi >= keys[-1]:
        return _NQ_TABLE[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= phi <= keys[i + 1]:
            ratio = (phi - keys[i]) / (keys[i + 1] - keys[i])
            return _NQ_TABLE[keys[i]] + ratio * (_NQ_TABLE[keys[i + 1]] - _NQ_TABLE[keys[i]])
    return _NQ_TABLE[keys[-1]]


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate(samples, pile, concrete, rebar, rock, shear=None):
    """Compute bored pile static capacity.

    Parameters
    ----------
    samples : list of dict
        Borehole samples with keys: depth, spt_n, classification, description
    pile : dict
        D (mm), Lp (m), Wt (m), FS (float)
    concrete : dict
        fc (MPa), Yc (kN/m3), Cc (mm)
    rebar : dict
        Fy (MPa), db (mm), nbar (int)
    rock : dict
        rock_type (str), Co (kPa), Nms (float), RQD (str)
    shear : dict, optional
        Vu (kN) — factored lateral shear demand at pile head
        s (mm)  — transverse reinforcement spacing / spiral pitch
        db_tie (mm) — diameter of tie bar (used to compute Av of one leg)
        When omitted or Vu <= 0, the shear check is skipped with a note
        in the report.

    Returns dict with HTML reports, tables, and Plotly chart data.
    """
    D_mm = pile['D']
    D_m = D_mm / 1000
    Lp = pile['Lp']
    Wt = pile['Wt']
    FS = pile['FS']

    perimeter = math.pi * D_m
    Ap = math.pi * D_m ** 2 / 4  # m2

    fc = concrete['fc']
    Yc = concrete['Yc']
    Ec = round(4700 * math.sqrt(fc), 0)

    # Sort samples by depth
    samples = sorted(samples, key=lambda s: s['depth'])

    # Filter samples within pile length
    pile_samples = [s for s in samples if s['depth'] <= Lp]
    if not pile_samples:
        pile_samples = samples[:1]  # at least use first sample

    # ---------------------------------------------------------------------------
    # Step 1: Build layer table
    # ---------------------------------------------------------------------------
    layers = []
    for i, s in enumerate(pile_samples):
        depth = s['depth']
        n = s.get('spt_n')
        cls = (s.get('classification') or '').upper()
        desc = s.get('description', '')

        granular = _is_granular(cls)
        cohesive = _is_cohesive(cls)
        is_rock = _is_rock(cls)

        # Layer thickness (half distance to neighbours)
        if i == 0:
            top = 0
        else:
            top = (pile_samples[i - 1]['depth'] + depth) / 2
        if i < len(pile_samples) - 1:
            bot = (depth + pile_samples[i + 1]['depth']) / 2
        else:
            bot = min(depth + 1, Lp)
        thickness = bot - top
        mid_depth = (top + bot) / 2

        # Soil properties from SPT
        if is_rock:
            gamma = 24.0
            phi = 0
            cu = 0
        elif granular:
            gamma = _gamma_from_spt(n, True)
            phi = _phi_from_spt(n)
            cu = 0
        else:
            gamma = _gamma_from_spt(n, False)
            phi = 0
            cu = _cu_from_spt(n)

        # Effective vertical stress at midpoint
        if mid_depth <= Wt:
            q0 = gamma * mid_depth
        else:
            q0 = gamma * Wt + (gamma - 9.81) * (mid_depth - Wt)
        q0 = max(q0, 0)

        # Skin friction
        if is_rock:
            # Rock skin: use rock adhesion (simplified)
            alpha = 0
            beta = 0
            K0 = 0
            delta = 0
            fs = 0  # Rock skin usually ignored for bored piles, capacity from base
        elif granular:
            K0 = round(1 - math.sin(math.radians(phi)), 4)
            delta = round(0.75 * phi, 2)
            beta = round(K0 * math.tan(math.radians(delta)), 4)
            alpha = 0
            fs = round(beta * q0, 2)
        else:  # cohesive
            alpha = round(_alpha_factor(cu), 3)
            K0 = 0
            delta = 0
            beta = 0
            fs = round(alpha * cu, 2)

        As = round(perimeter * thickness, 3)
        Qs = round(fs * As, 2)

        layers.append({
            'num': i + 1,
            'sample_id': s.get('sample_id', f'L{i+1}'),
            'depth_top': round(top, 2),
            'depth_bot': round(bot, 2),
            'mid_depth': round(mid_depth, 2),
            'thickness': round(thickness, 2),
            'classification': cls,
            'description': desc,
            'soil_type': 'Rock' if is_rock else ('Granular' if granular else 'Cohesive'),
            'spt_n': n,
            'gamma': round(gamma, 2),
            'phi': round(phi, 1) if phi else '-',
            'cu': round(cu, 1) if cu else '-',
            'K0': round(K0, 4) if K0 else '-',
            'delta': round(delta, 1) if delta else '-',
            'beta': round(beta, 4) if beta else '-',
            'alpha': round(alpha, 3) if alpha else '-',
            'q0': round(q0, 2),
            'fs': round(fs, 2),
            'As': round(As, 3),
            'Qs': round(Qs, 2),
        })

    # ---------------------------------------------------------------------------
    # Step 2: Total skin resistance
    # ---------------------------------------------------------------------------
    Qs_total = round(sum(ly['Qs'] for ly in layers), 2)

    # ---------------------------------------------------------------------------
    # Step 3: Base resistance
    # ---------------------------------------------------------------------------
    # Determine tip layer
    tip_sample = pile_samples[-1] if pile_samples else samples[-1]
    tip_cls = (tip_sample.get('classification') or '').upper()
    tip_n = tip_sample.get('spt_n')

    # Effective stress at pile tip
    if Lp <= Wt:
        q0_tip = sum(ly['gamma'] for ly in layers) / len(layers) * Lp if layers else 0
    else:
        avg_gamma = sum(ly['gamma'] for ly in layers) / len(layers) if layers else 18
        q0_tip = avg_gamma * Wt + (avg_gamma - 9.81) * (Lp - Wt)
    q0_tip = max(round(q0_tip, 2), 0)

    base_method = ''
    if _is_rock(tip_cls):
        # Rock bearing
        Co = rock.get('Co', 5000)
        Nms = rock.get('Nms', 0.28)
        qb = round(Nms * Co, 2)
        Qb = round(qb * Ap, 2)
        base_method = f'Rock: q_b = N_{{ms}} \\times C_o = {Nms} \\times {_f(Co,0)} = {_f(qb,1)} \\text{{ kPa}}'
    elif _is_granular(tip_cls):
        phi_tip = _phi_from_spt(tip_n)
        Nq = round(_get_nq(phi_tip), 1)
        qb = round(Nq * q0_tip, 2)
        # Limit: qb <= 50*Nq (kPa) for bored piles
        qb_limit = 50 * Nq
        qb = min(qb, qb_limit)
        Qb = round(qb * Ap, 2)
        base_method = (f'Granular: N_q = {_f(Nq,1)}, '
                       f'q_b = N_q \\times q_0 = {_f(Nq,1)} \\times {_f(q0_tip,1)} = {_f(qb,1)} \\text{{ kPa}}')
    else:
        cu_tip = _cu_from_spt(tip_n)
        Nc = 9.0
        qb = round(Nc * cu_tip, 2)
        Qb = round(qb * Ap, 2)
        base_method = (f'Cohesive: N_c = {Nc}, C_u = {_f(cu_tip,1)}, '
                       f'q_b = N_c \\times C_u = {Nc} \\times {_f(cu_tip,1)} = {_f(qb,1)} \\text{{ kPa}}')

    # ---------------------------------------------------------------------------
    # Step 4: Total and allowable capacity
    # ---------------------------------------------------------------------------
    Qu = round(Qs_total + Qb, 2)
    Wp = round(Yc * Ap * Lp, 2)
    Qu_net = round(Qu - Wp, 2)
    Qa = round(Qu / FS, 2)

    # ---------------------------------------------------------------------------
    # Step 5: Build skin resistance HTML table
    # ---------------------------------------------------------------------------
    skin_table = _build_skin_table(layers)

    # ---------------------------------------------------------------------------
    # Step 6: Build capacity chart
    # ---------------------------------------------------------------------------
    chart = _build_capacity_chart(layers, Qb, Lp)

    # ---------------------------------------------------------------------------
    # Step 7: Build reports
    # ---------------------------------------------------------------------------
    base_report = _build_base_report(base_method, qb, Ap, Qb)

    capacity_summary = _build_capacity_summary(Qs_total, Qb, Qu, Wp, Qu_net, FS, Qa)

    input_summary = _build_input_summary(pile, concrete, rebar, rock, D_m, perimeter, Ap, Ec)

    # Step 8: Transverse shear check (ACI 318-19 §22.5, §25.7.3)
    shear_report = _build_shear_report(
        fc=fc, Fy=rebar['Fy'], D_mm=D_mm, Cc=concrete['Cc'],
        db_long=rebar['db'], shear=(shear or {}),
    )

    return {
        'input_summary': input_summary,
        'skin_table': skin_table,
        'base_report': base_report,
        'capacity_summary': capacity_summary,
        'shear_report': shear_report,
        'Qs': Qs_total,
        'Qb': Qb,
        'Qu': Qu,
        'Qa': Qa,
        'chart_traces': chart['traces'],
        'chart_layout': chart['layout'],
    }


def _build_shear_report(fc, Fy, D_mm, Cc, db_long, shear):
    """Transverse shear capacity per ACI 318-19 §22.5 (one-way shear) and
    §25.7.3 (spirals). For a circular section the calculator uses the ACI
    R10.7.1 equivalent rectangular strip: bw = 0.9·D, with an approximate
    effective depth d ≈ D/2 + (D/2 - cover - db_long/2)·(2/π).

    Returns an HTML block (string). Skips the check with an informational
    message when Vu <= 0 or inputs are missing.
    """
    Vu = shear.get('Vu', 0) if shear else 0
    if not Vu or Vu <= 0:
        return (
            '<p><em>No lateral shear demand supplied (V<sub>u</sub> = 0) &mdash; '
            'transverse shear check skipped. Provide V<sub>u</sub>, tie pitch s, '
            'and tie bar diameter to run the ACI 318-19 &sect;22.5 check.</em></p>'
            '<p style="font-size:0.82em;color:#6c757d;">Reference: ACI 318-19 '
            '&sect;22.5 (one-way shear strength), &sect;25.7.3 (spirals), '
            'R10.7.1 (circular section equivalent width). See also '
            'Poulos &amp; Davis (1980) Ch.&nbsp;7 for lateral loading of single piles.</p>'
        )

    s = shear.get('s', 150.0)       # mm
    db_tie = shear.get('db_tie', 10.0)  # mm
    # Area of ONE leg of a tie / one turn of spiral, in mm^2
    Av = math.pi * db_tie ** 2 / 4.0
    b_w = 0.9 * D_mm                # mm, ACI R10.7.1 equivalent width
    # Effective depth for a circular section with cover Cc and longitudinal bar db_long
    # Use the classical approximation d = D/2 + (2/π)·R_bar where R_bar is the centroid-to-center distance of the longitudinal cage.
    R_bar = D_mm / 2 - Cc - db_long / 2
    d_eff = D_mm / 2 + (2.0 / math.pi) * R_bar  # mm
    # ACI 318-19 §22.5.5.1 simplified Vc for normal-weight concrete (no axial load benefit):
    #   Vc = 0.17·λ·√f'c·bw·d    (SI units: MPa, mm, N)
    lam = 1.0  # normal-weight concrete
    Vc_N = 0.17 * lam * math.sqrt(fc) * b_w * d_eff   # Newtons
    Vc = Vc_N / 1000.0                                # kN
    # ACI §22.5.10.5.3 stirrup/spiral shear contribution: Vs = Av·fyt·d / s
    Vs_N = Av * Fy * d_eff / s                         # Newtons (Av mm², Fy MPa, d mm, s mm)
    Vs = Vs_N / 1000.0                                 # kN
    phi_red = 0.75                                     # ACI 318-19 §21.2 strength-reduction for shear
    phi_Vn = phi_red * (Vc + Vs)
    passed = phi_Vn >= Vu
    ratio = Vu / phi_Vn if phi_Vn > 0 else float('inf')

    r = (
        '<p style="font-size:0.85em;color:#6c757d;margin:0 0 6px;">'
        'Reference: ACI 318-19 <strong>&sect;22.5.5.1</strong> (V<sub>c</sub> for non-prestressed '
        'members), <strong>&sect;22.5.10.5.3</strong> (V<sub>s</sub> from transverse reinforcement), '
        '<strong>&sect;21.2</strong> (&phi; = 0.75), <strong>R10.7.1</strong> (circular-section '
        'equivalent width b<sub>w</sub> = 0.9D). Context for V<sub>u</sub>: '
        'Poulos &amp; Davis (1980) Ch.&nbsp;7 &mdash; lateral loading of single piles.</p>'
    )
    r += f'<h4>Geometry &amp; Reinforcement</h4>'
    r += (
        f'\\[ b_w = 0.9 D = 0.9 \\times {D_mm:.0f} = {b_w:.0f} \\text{{ mm}} \\]'
        f'\\[ d_{{\\text{{eff}}}} \\approx \\tfrac{{D}}{{2}} + \\tfrac{{2}}{{\\pi}}(R_{{bar}}) = '
        f'{d_eff:.1f} \\text{{ mm}} \\]'
        f'\\[ A_v = \\tfrac{{\\pi d_b^2}}{{4}} = \\tfrac{{\\pi \\times {db_tie:.0f}^2}}{{4}} = '
        f'{Av:.1f} \\text{{ mm}}^2 \\text{{ (one tie leg, }}d_{{b,tie}}={db_tie:.0f}\\text{{ mm)}} \\]'
    )
    r += '<h4>Concrete and Steel Shear Capacity</h4>'
    r += (
        f'\\[ V_c = 0.17 \\lambda \\sqrt{{f_c\'}} \\, b_w \\, d = '
        f'0.17 \\times 1.0 \\times \\sqrt{{{fc}}} \\times {b_w:.0f} \\times {d_eff:.0f} '
        f'/ 1000 = {Vc:.1f} \\text{{ kN}} \\]'
        f'\\[ V_s = \\frac{{A_v f_{{yt}} d}}{{s}} = '
        f'\\frac{{{Av:.1f} \\times {Fy} \\times {d_eff:.0f}}}{{{s:.0f}}} / 1000 = '
        f'{Vs:.1f} \\text{{ kN}} \\quad (\\text{{tie pitch }} s = {s:.0f} \\text{{ mm}}) \\]'
    )
    r += '<h4>Design Strength and Demand/Capacity Ratio</h4>'
    r += (
        f'\\[ \\phi V_n = \\phi (V_c + V_s) = 0.75 \\times ({Vc:.1f} + {Vs:.1f}) = '
        f'{phi_Vn:.1f} \\text{{ kN}} \\]'
        f'\\[ V_u = {Vu:.1f} \\text{{ kN}}, \\quad \\frac{{V_u}}{{\\phi V_n}} = {ratio:.2f} \\]'
    )
    color = '#27ae60' if passed else '#e74c3c'
    verdict = 'PASS' if passed else 'FAIL'
    r += (
        f'<p style="font-size:1.0em;"><strong>Result:</strong> '
        f'<span style="color:{color};font-weight:bold;">{verdict}</span> '
        f'({phi_Vn:.1f} kN '
        + ('&ge;' if passed else '&lt;') +
        f' {Vu:.1f} kN)</p>'
    )
    return r


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def _build_skin_table(layers):
    """Build tabulated skin resistance table (like Excel Table 2)."""
    r = '<table class="data-table" style="font-size:0.82em;white-space:nowrap;">'
    r += '<thead><tr>'
    r += '<th>Layer</th><th>Depth (m)</th><th>Type</th><th>SPT N</th>'
    r += '<th>&gamma;<sub>eff</sub><br>(kN/m&sup3;)</th>'
    r += '<th>K<sub>0</sub></th>'
    r += '<th>&delta; (&deg;)</th>'
    r += '<th>&beta;</th>'
    r += '<th>&alpha;</th>'
    r += '<th>q<sub>0</sub><br>(kPa)</th>'
    r += '<th>f<sub>s</sub><br>(kPa)</th>'
    r += '<th>A<sub>s</sub><br>(m&sup2;)</th>'
    r += '<th>Q<sub>s</sub><br>(kN)</th>'
    r += '</tr></thead><tbody>'

    running_qs = 0
    for ly in layers:
        running_qs += ly['Qs']
        r += '<tr>'
        r += f'<td>{ly["num"]}</td>'
        r += f'<td>{_f(ly["depth_top"],1)}-{_f(ly["depth_bot"],1)}</td>'
        r += f'<td>{ly["soil_type"]}</td>'
        r += f'<td>{ly["spt_n"] if ly["spt_n"] is not None else "-"}</td>'
        r += f'<td>{_f(ly["gamma"])}</td>'
        r += f'<td>{ly["K0"]}</td>'
        r += f'<td>{ly["delta"]}</td>'
        r += f'<td>{ly["beta"]}</td>'
        r += f'<td>{ly["alpha"]}</td>'
        r += f'<td>{_f(ly["q0"])}</td>'
        r += f'<td>{_f(ly["fs"])}</td>'
        r += f'<td>{_f(ly["As"],3)}</td>'
        r += f'<td><strong>{_f(ly["Qs"])}</strong></td>'
        r += '</tr>'

    # Total row
    total_qs = sum(ly['Qs'] for ly in layers)
    r += f'<tr style="background:#eaf4fb;font-weight:bold;">'
    r += f'<td colspan="12" style="text-align:right;">Total Skin Resistance, Q<sub>s</sub> =</td>'
    r += f'<td>{_f(total_qs)} kN</td></tr>'
    r += '</tbody></table>'
    return r


def _build_base_report(method_latex, qb, Ap, Qb):
    """Build base resistance report with equations."""
    r = f'\\[ {method_latex} \\]'
    r += f'\\[ Q_b = q_b \\times A_p = {_f(qb, 1)} \\times {_f(Ap, 4)} = \\boxed{{{_f(Qb, 2)} \\text{{ kN}}}} \\]'
    return r


def _build_capacity_summary(Qs, Qb, Qu, Wp, Qu_net, FS, Qa):
    """Build capacity summary table."""
    r = '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Skin Resistance, Q<sub>s</sub></td><td><strong>{_f(Qs)} kN</strong></td></tr>'
    r += f'<tr><td style="text-align:left">Base Resistance, Q<sub>b</sub></td><td><strong>{_f(Qb)} kN</strong></td></tr>'
    r += f'<tr style="background:#eaf4fb;"><td style="text-align:left"><strong>Ultimate Capacity, Q<sub>u</sub> = Q<sub>s</sub> + Q<sub>b</sub></strong></td><td><strong>{_f(Qu)} kN</strong></td></tr>'
    r += f'<tr><td style="text-align:left">Pile Self-Weight, W<sub>p</sub></td><td>{_f(Wp)} kN</td></tr>'
    r += f'<tr><td style="text-align:left">Net Capacity, Q<sub>u,net</sub> = Q<sub>u</sub> - W<sub>p</sub></td><td>{_f(Qu_net)} kN</td></tr>'
    r += f'<tr><td style="text-align:left">Factor of Safety, FS</td><td>{_f(FS, 1)}</td></tr>'
    r += f'<tr style="background:#d5f5e3;"><td style="text-align:left"><strong>Allowable Capacity, Q<sub>a</sub> = Q<sub>u</sub> / FS</strong></td><td><strong>{_f(Qa)} kN</strong></td></tr>'
    r += '</table>'
    return r


def _build_input_summary(pile, concrete, rebar, rock, D_m, perimeter, Ap, Ec):
    """Build input parameter summary."""
    r = '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">'

    # Pile properties
    r += '<table class="data-table" style="font-size:0.85em;">'
    r += '<thead><tr><th colspan="2">Pile Properties</th></tr></thead><tbody>'
    r += f'<tr><td>Diameter, D</td><td>{pile["D"]} mm ({_f(D_m, 3)} m)</td></tr>'
    r += f'<tr><td>Length, L<sub>p</sub></td><td>{_f(pile["Lp"])} m</td></tr>'
    r += f'<tr><td>Perimeter, P</td><td>{_f(perimeter, 3)} m</td></tr>'
    r += f'<tr><td>Area, A<sub>p</sub></td><td>{_f(Ap, 4)} m&sup2;</td></tr>'
    r += f'<tr><td>Water Table, W<sub>t</sub></td><td>{_f(pile["Wt"])} m</td></tr>'
    r += f'<tr><td>Factor of Safety, FS</td><td>{_f(pile["FS"], 1)}</td></tr>'
    r += '</tbody></table>'

    # Concrete + rebar
    r += '<table class="data-table" style="font-size:0.85em;">'
    r += '<thead><tr><th colspan="2">Concrete &amp; Reinforcement</th></tr></thead><tbody>'
    r += f'<tr><td>f\'<sub>c</sub></td><td>{_f(concrete["fc"])} MPa</td></tr>'
    r += f'<tr><td>E<sub>c</sub></td><td>{_f(Ec, 0)} MPa</td></tr>'
    r += f'<tr><td>&gamma;<sub>c</sub></td><td>{_f(concrete["Yc"])} kN/m&sup3;</td></tr>'
    r += f'<tr><td>Cover, C<sub>c</sub></td><td>{concrete["Cc"]} mm</td></tr>'
    r += f'<tr><td>F<sub>y</sub></td><td>{_f(rebar["Fy"])} MPa</td></tr>'
    r += f'<tr><td>Bars</td><td>{rebar["nbar"]}-&Phi;{rebar["db"]}mm</td></tr>'
    r += '</tbody></table>'

    r += '</div>'
    return r


def _build_capacity_chart(layers, Qb, Lp):
    """Build Plotly chart: cumulative pile capacity vs depth."""
    depths = [0]
    cum_qs = [0]
    running = 0

    for ly in layers:
        running += ly['Qs']
        depths.append(ly['depth_bot'])
        cum_qs.append(round(running, 2))

    # Add Qb at pile tip
    depths_total = depths.copy()
    cum_total = [q + Qb for q in cum_qs]

    traces = [
        {
            "x": cum_qs,
            "y": [-d for d in depths],
            "mode": "lines+markers",
            "name": "Skin (Qs)",
            "line": {"color": "#2980b9", "width": 2},
            "marker": {"size": 6},
        },
        {
            "x": cum_total,
            "y": [-d for d in depths_total],
            "mode": "lines+markers",
            "name": "Total (Qs+Qb)",
            "line": {"color": "#27ae60", "width": 2.5},
            "marker": {"size": 6},
        },
    ]

    max_val = max(cum_total) * 1.15 if cum_total else 500
    y_min = -(Lp + 1)

    layout = {
        "title": "",
        "xaxis": {
            "title": "Pile Capacity [kN]",
            "side": "top",
            "range": [0, max_val],
            "gridcolor": "#ddd",
        },
        "yaxis": {
            "title": "Depth [m]",
            "range": [y_min, 1],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": 550,
        "margin": {"t": 60, "r": 30, "b": 30, "l": 60},
        "legend": {"x": 0.6, "y": 0.95},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
    }

    return {'traces': traces, 'layout': layout}
