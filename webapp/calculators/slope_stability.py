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

        traces.append({
            "x": [0, 1, 1, 0],
            "y": [top, top, bot, bot],
            "fill": "toself",
            "fillcolor": col,
            "line": {"color": "#333", "width": 1},
            "mode": "lines",
            "name": ly['name'],
            "showlegend": False,
            "hoverinfo": "text",
            "text": f"{ly['name']}: {ly['description']}<br>{_f(ly['depth_top'])}–{_f(ly['depth_bottom'])} m<br>t = {_f(ly['thickness'])} m",
        })

        annotations.append({
            "x": 0.5, "y": mid,
            "text": f"<b>{ly['name']}</b><br>{ly['description']}<br>t={_f(ly['thickness'])}m | SPT={ly['spt']}",
            "showarrow": False,
            "font": {"size": 11},
            "xanchor": "center",
        })

    max_depth = max(ly['depth_bottom'] for ly in layers) if layers else 10

    layout = {
        "title": "Soil Profile",
        "xaxis": {"visible": False, "range": [-0.2, 1.2]},
        "yaxis": {
            "title": "Depth [m]",
            "range": [-(max_depth + 1), 1],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": 450,
        "width": 350,
        "margin": {"t": 40, "r": 20, "b": 30, "l": 60},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "annotations": annotations,
    }

    return {'traces': traces, 'layout': layout}


def build_software_table(layers):
    """Build consolidated Midas GTS NX software input HTML table."""
    r = '<h3>Midas GTS NX &mdash; Software Input Summary</h3>'

    # General tab table
    r += '<h4>General (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="font-size:0.85em;">'
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
    r += '<table class="data-table" style="font-size:0.85em;">'
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
    r += '<table class="data-table" style="font-size:0.85em;">'
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
    r += '<table class="data-table" style="max-width:700px;text-align:left;">'
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
    r += '<table class="data-table" style="max-width:500px;">'
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
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Unit Weight (Saturated)</td><td>{_f(gamma_sat)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Initial Void Ratio, e₀</td><td>{_f(e0, 4)}</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kx</td><td>{layer["perm_kx"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability ky</td><td>{layer["perm_ky"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kz</td><td>{layer["perm_kz"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Storativity, Ss</td><td>{Ss:.6e} 1/m</td></tr>'
    r += '</table>'

    # Non-Linear tab
    r += '<h4>Non-Linear (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m&sup2;</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, &phi;</td><td>{_f(phi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Dilatancy Angle, &psi;</td><td>{_f(psi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Tensile Strength</td><td>0 kN/m&sup2;</td></tr>'
    r += '</table>'

    # Derived
    r += '<h4>Derived Properties</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Dry Unit Weight, &gamma;<sub>d</sub></td><td>{_f(gamma_d)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Effective Unit Weight, &gamma;\'</td><td>{_f(gamma_eff)} kN/m&sup3;</td></tr>'
    r += f'<tr><td style="text-align:left">Moisture Content</td><td>{_f(mc)}%</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Gravity, Gs</td><td>{_f(Gs)}</td></tr>'
    r += '</table>'

    return r
