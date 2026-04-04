"""Slope stability parameters calculator for Midas GTS NX material input."""
import math


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(layers):
    """
    Each layer dict:
        name, thickness, description, spt, phi, cohesion, E, nu, gamma,
        moisture_content, Gs

    Returns computed Midas GTS NX material parameters per layer.
    """
    results = []
    cumulative_depth = 0

    for layer in layers:
        name = layer['name']
        thickness = layer.get('thickness', 3.0)
        desc = layer['description']
        spt = layer.get('spt', 0)
        phi = layer.get('phi', 0)
        c = layer.get('cohesion', 0)
        E = layer.get('E', 10000)
        nu = layer.get('nu', 0.3)
        gamma = layer.get('gamma', 18)
        mc = layer.get('moisture_content', 0)
        Gs = layer.get('Gs', 2.65)

        top = cumulative_depth
        cumulative_depth += thickness
        bottom = cumulative_depth

        # Derived parameters
        w = mc / 100.0 if mc > 0 else 0.3
        e0 = Gs * w if mc > 0 else 0.5
        gamma_d = gamma / (1 + w) if w > 0 else gamma
        gamma_w = 9.81
        gamma_sat = (Gs + e0) / (1 + e0) * gamma_w
        gamma_eff = gamma_sat - gamma_w
        Ko = 1 - math.sin(math.radians(phi)) if phi > 0 else 0.5
        psi = max(0, phi - 30)
        perm = layer.get('permeability', 1e-5)
        Ss = gamma_w / (E if E > 0 else 10000)

        result = {
            'name': name,
            'thickness': thickness,
            'depth_top': top,
            'depth_bottom': bottom,
            'depth_range': f"{_f(top)}-{_f(bottom)}",
            'description': desc,
            'spt': spt,
            'E': E, 'nu': nu, 'gamma': gamma,
            'Ko': Ko, 'cohesion': c, 'phi': phi,
            'damping_ratio': 0.05,
            'gamma_sat': gamma_sat, 'e0': e0,
            'perm_kx': perm, 'perm_ky': perm, 'perm_kz': perm,
            'Ss': Ss,
            'psi': psi,
            'gamma_d': gamma_d, 'gamma_eff': gamma_eff,
            'moisture_content': mc, 'Gs': Gs,
            'w': w, 'gamma_w': gamma_w,
        }
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# SPT Correlation Tables (Polish Code PN-59/B-03020, Wilun & Starzewski)
# ---------------------------------------------------------------------------

# Table 5: Unit weight from N-value
_GAMMA_TABLE = [
    # (N_min, N_max, gamma_above_wt, gamma_below_wt)
    (2, 4, 14, 8),
    (5, 10, 16, 9),
    (11, 20, 17, 10),
    (21, 30, 18, 10),
    (31, 40, 19, 11),
    (41, 50, 20, 12),
    (51, 999, 21, 13),
]


def _gamma_from_n(n):
    """Unit weight (kN/m3) from SPT N (Table 5, above water table)."""
    if n is None or n < 2:
        return 14
    for nmin, nmax, g_above, _ in _GAMMA_TABLE:
        if nmin <= n <= nmax:
            return g_above
    return 21


# Table 1: Sandy Clay and Silty Clay (CL, CH with sand description)
_SANDY_CLAY = [
    # (N_min, N_max, c_mid, phi_mid)
    (0, 3, 25, 1),
    (4, 8, 45, 3.5),
    (8, 15, 55, 6.5),
    (15, 30, 70, 9),
    (31, 999, 85, 10),
]

# Table 2: Clayey Sand and Clayey Silts (SC, GC)
_CLAYEY_SAND = [
    (0, 3, 11.5, 6),
    (4, 8, 24.5, 9.5),
    (8, 15, 34, 14),
    (15, 30, 44, 18),
    (31, 999, 50, 20),
]

# Table 3: Cohesionless Soils - Sand (SM, SW, SP, GM, GW, GP) c=0
_SAND = [
    (0, 3, 0, 26),
    (4, 10, 0, 30),
    (10, 30, 0, 33.5),
    (30, 50, 0, 36),
    (51, 999, 0, 38),
]

# Table 4: Sandy Silts (ML, MH)
_SANDY_SILT = [
    (0, 3, 8.5, 6),
    (4, 8, 17.5, 13),
    (8, 15, 24.5, 18),
    (15, 30, 34, 22.5),
    (31, 999, 40, 25),
]


def _lookup_table(table, n):
    """Interpolate cohesion and phi from a correlation table."""
    if n is None or n <= 0:
        return table[0][2], table[0][3]
    for nmin, nmax, c, phi in table:
        if nmin <= n <= nmax:
            return c, phi
    return table[-1][2], table[-1][3]


def _get_soil_table(classification):
    """Select the right Polish Code table based on USCS classification."""
    cls = (classification or '').upper()
    # Cohesionless sands/gravels (no clay component)
    if cls in ('SM', 'SW', 'SP', 'GM', 'GW', 'GP'):
        return _SAND
    # Clayey sand/gravel
    if cls in ('SC', 'GC'):
        return _CLAYEY_SAND
    # Sandy silts
    if cls in ('ML', 'MH'):
        return _SANDY_SILT
    # Sandy clay, silty clay, lean/fat clay
    if cls in ('CL', 'CH'):
        return _SANDY_CLAY
    # Default to sandy clay for unknown
    return _SANDY_CLAY


def _estimate_E(n, classification):
    """Estimate Young's modulus E (kPa) from SPT N-value.

    Uses E = 500*(N+15) to match the Excel template.
    """
    cls = (classification or '').upper()
    if cls in ('SM', 'SW', 'SP', 'GM', 'GW', 'GP', 'SC', 'GC'):
        return round(500 * ((n or 5) + 15))
    else:
        # Cohesive: also use E = 500*(N+15) for consistency with Excel
        return round(500 * ((n or 5) + 15))


def build_parameters_table(layers):
    """Build Slope Stability Parameters table matching the Excel format.

    Computes: Dry Unit Weight, Saturated Unit Weight from the Excel formulas:
      gamma_d = gamma / (1 + mc/100)
      gamma_sat = gamma_d + 9.81 - gamma_d/Gs  (or Gs=2.7 if not provided)
    """
    if not layers:
        return ''

    r = '<h3>Slope Stability Parameters</h3>'
    r += '<div style="overflow-x:auto;">'
    r += '<table class="data-table" style="font-size:0.82em;white-space:nowrap;">'
    r += '<thead><tr>'
    r += '<th>Layer</th><th>Depth (m)</th>'
    r += '<th>Soil/Rock Description</th><th>SPT N</th>'
    r += '<th>&phi; (&deg;)</th><th>c (kPa)</th>'
    r += '<th>E (kPa)</th><th>&nu;</th>'
    r += '<th>&gamma; (kN/m&sup3;)</th><th>MC (%)</th>'
    r += '<th>&gamma;<sub>d</sub> (kN/m&sup3;)</th>'
    r += '<th>&gamma;<sub>sat</sub> (kN/m&sup3;)</th>'
    r += '</tr></thead><tbody>'

    for i, ly in enumerate(layers):
        gamma = ly['gamma']
        mc = ly.get('moisture_content', 0)
        Gs = ly.get('Gs', 2.65) or 2.65
        w = mc / 100.0 if mc > 0 else 0

        # Dry unit weight: gamma_d = gamma / (1 + w)
        gamma_d = gamma / (1 + w) if w > 0 else gamma

        # Saturated unit weight matching Excel:
        # IF(Gs=0, gamma_d + 9.81 - gamma_d/2.7, gamma_d + 9.81 - gamma_d/Gs)
        if Gs == 0 or Gs is None:
            gamma_sat = gamma_d + 9.81 - gamma_d / 2.7
        else:
            gamma_sat = gamma_d + 9.81 - gamma_d / Gs

        r += '<tr>'
        r += f'<td><span class="layer-link" onclick="openModal({i})">{ly["name"]}</span></td>'
        r += f'<td>{ly["depth_range"]}</td>'
        r += f'<td>{ly["description"]}</td>'
        r += f'<td>{ly["spt"]}</td>'
        r += f'<td>{_f(ly["phi"], 0)}</td>'
        r += f'<td>{_f(ly["cohesion"], 0)}</td>'
        r += f'<td>{_f(ly["E"], 0)}</td>'
        r += f'<td>{_f(ly["nu"])}</td>'
        r += f'<td>{_f(gamma)}</td>'
        r += f'<td>{_f(mc)}</td>'
        r += f'<td>{_f(gamma_d)}</td>'
        r += f'<td>{_f(gamma_sat)}</td>'
        r += '</tr>'

    r += '</tbody></table></div>'
    return r


def derive_layers_from_borehole(samples):
    """Convert borehole JSON samples into slope stability layer format.

    Uses Polish Code PN-59/B-03020 correlation tables to derive
    phi, cohesion, gamma, and E from SPT N-values and classification.

    Returns list of layer dicts compatible with the Handsontable format.
    """
    if not samples:
        return []

    # Sort by depth
    samples = sorted(samples, key=lambda s: s['depth'])

    # Group consecutive samples with same classification into layers
    groups = []
    current = {'cls': (samples[0].get('classification') or '').upper(),
               'samples': [samples[0]]}
    for s in samples[1:]:
        cls = (s.get('classification') or '').upper()
        if cls == current['cls']:
            current['samples'].append(s)
        else:
            groups.append(current)
            current = {'cls': cls, 'samples': [s]}
    groups.append(current)

    layers = []
    for i, g in enumerate(groups):
        slist = g['samples']
        cls = g['cls']
        n_values = [s.get('spt_n') for s in slist if s.get('spt_n') is not None]
        avg_n = round(sum(n_values) / len(n_values)) if n_values else 0

        # Depth range
        min_depth = min(s['depth'] for s in slist)
        max_depth = max(s['depth'] for s in slist)
        if i == 0:
            top = 0
        else:
            prev_max = max(s['depth'] for s in groups[i - 1]['samples'])
            top = round((prev_max + min_depth) / 2, 2)
        if i < len(groups) - 1:
            next_min = min(s['depth'] for s in groups[i + 1]['samples'])
            bot = round((max_depth + next_min) / 2, 2)
        else:
            bot = round(max_depth + 1, 2)
        thickness = round(bot - top, 2)

        # Description from first sample
        desc = slist[0].get('description', cls)

        # Derive parameters from Polish Code tables
        table = _get_soil_table(cls)
        cohesion, phi = _lookup_table(table, avg_n)
        gamma = _gamma_from_n(avg_n)
        E = _estimate_E(avg_n, cls)

        # Rock layers
        if cls in ('RK', 'ROCK'):
            cohesion = 100
            phi = 35
            gamma = 24
            E = 50000

        layers.append({
            'row_num': i + 1,
            'name': f'LAYER {i + 1}',
            'thickness': thickness,
            'description': desc,
            'spt': avg_n,
            'phi': round(phi, 1),
            'cohesion': round(cohesion, 0),
            'E': E,
            'nu': 0.3 if cls not in ('RK', 'ROCK') else 0.2,
            'gamma': round(gamma, 2),
            'moisture_content': 0,
            'Gs': 2.65,
        })

    return layers


def build_soil_profile(layers):
    """Build Plotly soil profile chart from computed layers."""
    colors = ['#aed6f1', '#a9dfbf', '#f9e79f', '#d2b4de', '#f5cba7',
              '#a3e4d7', '#fadbd8', '#d5dbdb', '#abebc6', '#f5b7b1']
    traces = []
    annotations = []

    for i, ly in enumerate(layers):
        col = colors[i % len(colors)]
        top = -ly['depth_top']
        bot = -ly['depth_bottom']
        mid = (top + bot) / 2
        thickness = ly['thickness']

        traces.append({
            "x": [0, 1, 1, 0],
            "y": [top, top, bot, bot],
            "fill": "toself",
            "fillcolor": col,
            "line": {"color": "#555", "width": 1.5},
            "mode": "lines",
            "name": ly['name'],
            "showlegend": False,
            "hoverinfo": "text",
            "text": f"{ly['name']}: {ly['description']}<br>{_f(ly['depth_top'])}-{_f(ly['depth_bottom'])} m<br>t = {_f(thickness)} m | SPT={ly['spt']}",
        })

        # Adapt label to layer thickness
        desc = ly['description']
        if thickness >= 3:
            if len(desc) > 45:
                desc = desc[:42] + '...'
            label = f"<b>{ly['name']}</b><br>{desc}<br>t={_f(thickness)}m | SPT={ly['spt']}"
            font_size = 11
        elif thickness >= 1.5:
            if len(desc) > 30:
                desc = desc[:27] + '...'
            label = f"<b>{ly['name']}</b>  {desc}  t={_f(thickness)}m | SPT={ly['spt']}"
            font_size = 10
        else:
            label = f"<b>{ly['name']}</b> t={_f(thickness)}m | SPT={ly['spt']}"
            font_size = 9

        annotations.append({
            "x": 0.5, "y": mid,
            "text": label,
            "showarrow": False,
            "font": {"size": font_size, "color": "#333"},
            "xanchor": "center",
        })

    max_depth = max(ly['depth_bottom'] for ly in layers) if layers else 10
    chart_height = max(500, int(max_depth * 45))

    layout = {
        "title": "",
        "xaxis": {"visible": False, "range": [-0.1, 1.1]},
        "yaxis": {
            "title": "Depth [m]",
            "range": [-(max_depth + 1), 1],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": chart_height,
        "width": 400,
        "margin": {"t": 20, "r": 20, "b": 30, "l": 60},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "annotations": annotations,
    }

    return {'traces': traces, 'layout': layout}


def build_borehole_charts(layers, samples=None):
    """Build SPT N, RQD, Water Content, and Plasticity Index charts from input data.

    Uses samples (raw borehole data) if available, otherwise derives from layers.
    """
    charts = {}

    # Use samples if provided, otherwise build from layers
    if samples:
        pts_n = [(s['depth'], s['spt_n']) for s in samples if s.get('spt_n') is not None]
        pts_rqd = [(s['depth'], s['rqd_pct']) for s in samples if s.get('rqd_pct') is not None]
        pts_wc = [(s['depth'], s['water_content']) for s in samples if s.get('water_content') is not None]
        pts_pi = []
        for s in samples:
            pi = s.get('plasticity_index')
            if pi is not None:
                pts_pi.append((s['depth'], pi))
            elif s.get('description') and 'NP' in s.get('description', '').upper():
                pts_pi.append((s['depth'], 0))
    else:
        pts_n = [((ly['depth_top'] + ly['depth_bottom']) / 2, ly['spt'])
                 for ly in layers if ly.get('spt')]
        pts_rqd = []
        pts_wc = [((ly['depth_top'] + ly['depth_bottom']) / 2, ly['moisture_content'])
                  for ly in layers if ly.get('moisture_content')]
        pts_pi = []

    # Publication-quality chart style
    _font = {"family": "Arial, Helvetica, sans-serif", "color": "#333"}
    _axis_font = {**_font, "size": 12}
    _title_font = {**_font, "size": 13}
    _tick_font = {**_font, "size": 11}

    def _make_chart(pts, title, x_title, x_unit, color, symbol, x_dtick=None):
        if not pts:
            return None
        depths = [-d for d, _ in pts]
        values = [v for _, v in pts]
        x_max = max(values) * 1.2 if values else 50
        y_min = min(depths) - 1
        x_cfg = {
            "title": {"text": x_title, "font": _title_font, "standoff": 8},
            "side": "top",
            "range": [0, x_max],
            "gridcolor": "rgba(0,0,0,0.08)",
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": "rgba(0,0,0,0.15)",
            "zerolinewidth": 1,
            "tickfont": _tick_font,
            "ticks": "outside",
            "ticklen": 5,
            "tickcolor": "#999",
            "linecolor": "#333",
            "linewidth": 1.5,
            "mirror": True,
        }
        if x_dtick:
            x_cfg["dtick"] = x_dtick
        return {
            'traces': [{
                "x": values, "y": depths,
                "mode": "lines+markers",
                "name": title,
                "marker": {"size": 7, "color": color, "symbol": symbol,
                           "line": {"width": 1.2, "color": "#fff"}},
                "line": {"color": color, "width": 2, "shape": "linear"},
                "hovertemplate": f"{x_title}: %{{x}}{x_unit}<br>Depth: %{{y:.1f}} m<extra></extra>",
            }],
            'layout': {
                "title": "",
                "xaxis": x_cfg,
                "yaxis": {
                    "title": {"text": "Depth [m]", "font": _title_font, "standoff": 8},
                    "range": [min(y_min, -12), 1],
                    "dtick": 1,
                    "gridcolor": "rgba(0,0,0,0.08)",
                    "gridwidth": 1,
                    "tickfont": _tick_font,
                    "ticks": "outside",
                    "ticklen": 5,
                    "tickcolor": "#999",
                    "linecolor": "#333",
                    "linewidth": 1.5,
                    "mirror": True,
                },
                "height": 480,
                "margin": {"t": 55, "r": 25, "b": 25, "l": 65},
                "plot_bgcolor": "#fff",
                "paper_bgcolor": "#fff",
                "font": _font,
                "showlegend": False,
            }
        }

    charts['spt'] = _make_chart(pts_n, 'SPT N-value', 'N [blows/0.3m]', '', '#2c3e50', 'circle', 10)
    charts['rqd'] = _make_chart(pts_rqd, 'RQD', 'RQD [%]', '%', '#8e44ad', 'diamond')
    charts['wc'] = _make_chart(pts_wc, 'Water Content', 'w [%]', '%', '#2980b9', 'square')
    charts['pi'] = _make_chart(pts_pi, 'Plasticity Index', 'PI', '', '#e67e22', 'triangle-up')

    # Remove None entries
    return {k: v for k, v in charts.items() if v is not None}


def build_software_table(layers):
    """Build consolidated Midas GTS NX software input HTML table."""
    r = '<h3>Midas GTS NX &mdash; Software Input Summary</h3>'

    # General tab table
    r += '<h4>General (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="font-size:0.85em;width:100%;">'
    r += '<thead><tr><th>Layer</th><th>Depth (m)</th><th>E (kN/m&sup2;)</th><th>&nu;</th>'
    r += '<th>&gamma; (kN/m&sup3;)</th><th>K₀</th><th>C (kN/m&sup2;)</th><th>&phi; (&deg;)</th><th>Damping</th></tr></thead>'
    r += '<tbody>'
    for ly in layers:
        r += f'<tr><td>{ly["name"]}</td><td>{ly["depth_range"]}</td>'
        r += f'<td>{_f(ly["E"], 0)}</td><td>{_f(ly["nu"])}</td>'
        r += f'<td>{_f(ly["gamma"])}</td><td>{_f(ly["Ko"], 4)}</td>'
        r += f'<td>{_f(ly["cohesion"], 0)}</td><td>{_f(ly["phi"], 0)}</td>'
        r += f'<td>{_f(ly["damping_ratio"])}</td></tr>'
    r += '</tbody></table>'

    # Porous tab table
    r += '<h4>Porous</h4>'
    r += '<table class="data-table" style="font-size:0.85em;width:100%;">'
    r += '<thead><tr><th>Layer</th><th>&gamma;<sub>sat</sub> (kN/m&sup3;)</th><th>e₀</th>'
    r += '<th>kx (m/s)</th><th>ky (m/s)</th><th>kz (m/s)</th><th>Ss (1/m)</th></tr></thead>'
    r += '<tbody>'
    for ly in layers:
        r += f'<tr><td>{ly["name"]}</td>'
        r += f'<td>{_f(ly["gamma_sat"])}</td><td>{_f(ly["e0"], 4)}</td>'
        r += f'<td>{ly["perm_kx"]:.2e}</td><td>{ly["perm_ky"]:.2e}</td>'
        r += f'<td>{ly["perm_kz"]:.2e}</td><td>{ly["Ss"]:.4e}</td></tr>'
    r += '</tbody></table>'

    # Non-Linear tab table
    r += '<h4>Non-Linear (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="font-size:0.85em;width:100%;">'
    r += '<thead><tr><th>Layer</th><th>C (kN/m&sup2;)</th><th>&phi; (&deg;)</th>'
    r += '<th>&psi; (&deg;)</th><th>Tensile (kN/m&sup2;)</th></tr></thead>'
    r += '<tbody>'
    for ly in layers:
        r += f'<tr><td>{ly["name"]}</td>'
        r += f'<td>{_f(ly["cohesion"], 0)}</td><td>{_f(ly["phi"], 0)}</td>'
        r += f'<td>{_f(ly["psi"], 0)}</td><td>0</td></tr>'
    r += '</tbody></table>'

    return r


def build_report(layer):
    """Build HTML report for a single layer with manual computation."""
    r = f'<h3>{layer["name"]} &mdash; {layer["description"]}</h3>'
    r += f'<p style="color:var(--muted);font-size:0.9em;">Depth: {layer["depth_range"]} m (thickness = {_f(layer["thickness"])} m)'
    if layer['spt']:
        r += f' | SPT N = {layer["spt"]}'
    r += '</p>'

    w = layer['w']
    Gs = layer['Gs']
    e0 = layer['e0']
    gamma = layer['gamma']
    gamma_w = layer['gamma_w']
    gamma_d = layer['gamma_d']
    gamma_sat = layer['gamma_sat']
    gamma_eff = layer['gamma_eff']
    phi = layer['phi']
    Ko = layer['Ko']
    psi = layer['psi']
    E = layer['E']
    Ss = layer['Ss']
    mc = layer['moisture_content']

    r += '<h4>Manual Computation</h4>'
    r += '<table class="data-table" style="max-width:700px;text-align:left;margin:0 auto;">'
    r += '<thead><tr><th style="width:40%;">Parameter</th><th style="width:35%;">Formula / Method</th><th style="width:25%;">Result</th></tr></thead>'
    r += '<tbody>'

    r += f'<tr><td>Moisture content, w</td><td>w = MC / 100</td><td>{_f(w, 4)}</td></tr>'

    if mc > 0:
        r += f'<tr><td>Void ratio, e₀</td><td>e₀ = Gs &times; w = {_f(Gs)} &times; {_f(w, 4)}</td><td>{_f(e0, 4)}</td></tr>'
    else:
        r += f'<tr><td>Void ratio, e₀</td><td>Assumed (no MC data)</td><td>{_f(e0, 4)}</td></tr>'

    r += f'<tr><td>Dry unit weight, &gamma;<sub>d</sub></td>'
    r += f'<td>&gamma;<sub>d</sub> = &gamma; / (1 + w) = {_f(gamma)} / (1 + {_f(w, 4)})</td>'
    r += f'<td>{_f(gamma_d)} kN/m&sup3;</td></tr>'

    r += f'<tr><td>Saturated unit weight, &gamma;<sub>sat</sub></td>'
    r += f'<td>&gamma;<sub>sat</sub> = (Gs + e₀) / (1 + e₀) &times; &gamma;<sub>w</sub><br>'
    r += f'= ({_f(Gs)} + {_f(e0, 4)}) / (1 + {_f(e0, 4)}) &times; {_f(gamma_w)}</td>'
    r += f'<td>{_f(gamma_sat)} kN/m&sup3;</td></tr>'

    r += f'<tr><td>Effective unit weight, &gamma;\'</td>'
    r += f'<td>&gamma;\' = &gamma;<sub>sat</sub> &minus; &gamma;<sub>w</sub> = {_f(gamma_sat)} &minus; {_f(gamma_w)}</td>'
    r += f'<td>{_f(gamma_eff)} kN/m&sup3;</td></tr>'

    if phi > 0:
        r += f'<tr><td>At-rest earth pressure, K₀</td>'
        r += f'<td>K₀ = 1 &minus; sin(&phi;) = 1 &minus; sin({_f(phi, 0)}&deg;)</td>'
        r += f'<td>{_f(Ko, 9)}</td></tr>'
    else:
        r += f'<tr><td>At-rest earth pressure, K₀</td><td>Assumed (&phi; = 0)</td><td>{_f(Ko, 4)}</td></tr>'

    if phi > 30:
        r += f'<tr><td>Dilatancy angle, &psi;</td>'
        r += f'<td>&psi; = &phi; &minus; 30&deg; = {_f(phi, 0)}&deg; &minus; 30&deg;</td>'
        r += f'<td>{_f(psi, 0)}&deg;</td></tr>'
    else:
        r += f'<tr><td>Dilatancy angle, &psi;</td>'
        r += f'<td>&psi; = max(0, &phi; &minus; 30&deg;) &rarr; &phi; &le; 30&deg;</td>'
        r += f'<td>{_f(psi, 0)}&deg;</td></tr>'

    r += f'<tr><td>Specific storativity, Ss</td>'
    r += f'<td>Ss = &gamma;<sub>w</sub> / E = {_f(gamma_w)} / {_f(E, 0)}</td>'
    r += f'<td>{Ss:.6e} 1/m</td></tr>'

    r += '</tbody></table>'

    # General tab
    r += '<h4>General (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;margin:0 auto;">'
    r += f'<tr><td style="text-align:left">Elastic Modulus, E</td><td>{_f(E, 0)} kN/m&sup2;</td></tr>'
    r += f'<tr><td style="text-align:left">Poisson\'s Ratio, &nu;</td><td>{_f(layer["nu"], 2)}</td></tr>'
    r += f'<tr><td style="text-align:left">Unit Weight, &gamma;</td><td>{_f(gamma)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Ko (1 &minus; sin&phi;)</td><td>{_f(Ko, 9)}</td></tr>'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m&sup2;</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, &phi;</td><td>{_f(phi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Damping Ratio</td><td>{_f(layer["damping_ratio"], 2)}</td></tr>'
    r += '</table>'

    # Porous tab
    r += '<h4>Porous</h4>'
    r += '<table class="data-table" style="max-width:500px;margin:0 auto;">'
    r += f'<tr><td style="text-align:left">Unit Weight (Saturated)</td><td>{_f(gamma_sat)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Initial Void Ratio, e₀</td><td>{_f(e0, 4)}</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kx</td><td>{layer["perm_kx"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability ky</td><td>{layer["perm_ky"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kz</td><td>{layer["perm_kz"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Storativity, Ss</td><td>{Ss:.6e} 1/m</td></tr>'
    r += '</table>'

    # Non-Linear tab
    r += '<h4>Non-Linear (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;margin:0 auto;">'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m&sup2;</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, &phi;</td><td>{_f(phi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Dilatancy Angle, &psi;</td><td>{_f(psi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Tensile Strength</td><td>0 kN/m&sup2;</td></tr>'
    r += '</table>'

    # Derived
    r += '<h4>Derived Properties</h4>'
    r += '<table class="data-table" style="max-width:500px;margin:0 auto;">'
    r += f'<tr><td style="text-align:left">Dry Unit Weight, &gamma;<sub>d</sub></td><td>{_f(gamma_d)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Effective Unit Weight, &gamma;\'</td><td>{_f(gamma_eff)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Moisture Content</td><td>{_f(mc)}%</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Gravity, Gs</td><td>{_f(Gs)}</td></tr>'
    r += '</table>'

    return r
