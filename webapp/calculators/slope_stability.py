"""Slope stability parameters calculator for Midas GTS NX material input."""
import math


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(layers):
    """
    Each layer dict:
        name, depth, description, spt, phi, cohesion, E, nu, gamma,
        moisture_content, Gs

    Returns computed Midas GTS NX material parameters per layer.
    """
    results = []

    for layer in layers:
        name = layer['name']
        depth = layer['depth']
        desc = layer['description']
        spt = layer.get('spt', 0)
        phi = layer.get('phi', 0)
        c = layer.get('cohesion', 0)
        E = layer.get('E', 10000)  # kPa
        nu = layer.get('nu', 0.3)
        gamma = layer.get('gamma', 18)  # kN/m3
        mc = layer.get('moisture_content', 0)  # %
        Gs = layer.get('Gs', 2.65)

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
            'depth': depth,
            'description': desc,
            'spt': spt,
            # Input
            'E': E,
            'nu': nu,
            'gamma': gamma,
            'Ko': Ko,
            'cohesion': c,
            'phi': phi,
            'damping_ratio': 0.05,
            # Porous
            'gamma_sat': gamma_sat,
            'e0': e0,
            'perm_kx': perm,
            'perm_ky': perm,
            'perm_kz': perm,
            'Ss': Ss,
            # Non-Linear
            'psi': psi,
            # Derived
            'gamma_d': gamma_d,
            'gamma_eff': gamma_eff,
            'moisture_content': mc,
            'Gs': Gs,
            'w': w,
            'gamma_w': gamma_w,
        }
        results.append(result)

    return results


def build_report(layer):
    """Build HTML report for a single layer in Midas GTS NX format with manual computation."""
    r = f'<h3>{layer["name"]} &mdash; {layer["description"]}</h3>'
    r += f'<p style="color:var(--muted);font-size:0.9em;">Depth: {layer["depth"]}'
    if layer['spt']:
        r += f' | SPT N = {layer["spt"]}'
    r += '</p>'

    # --- Manual Computation ---
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

    # Moisture content
    r += f'<tr><td>Moisture content, w</td><td>w = MC / 100</td><td>{_f(w, 4)}</td></tr>'

    # Void ratio
    if mc > 0:
        r += f'<tr><td>Void ratio, e₀</td><td>e₀ = Gs × w = {_f(Gs)} × {_f(w, 4)}</td><td>{_f(e0, 4)}</td></tr>'
    else:
        r += f'<tr><td>Void ratio, e₀</td><td>Assumed (no MC data)</td><td>{_f(e0, 4)}</td></tr>'

    # Dry unit weight
    r += f'<tr><td>Dry unit weight, γ<sub>d</sub></td>'
    r += f'<td>γ<sub>d</sub> = γ / (1 + w) = {_f(gamma)} / (1 + {_f(w, 4)})</td>'
    r += f'<td>{_f(gamma_d)} kN/m³</td></tr>'

    # Saturated unit weight
    r += f'<tr><td>Saturated unit weight, γ<sub>sat</sub></td>'
    r += f'<td>γ<sub>sat</sub> = (Gs + e₀) / (1 + e₀) × γ<sub>w</sub><br>'
    r += f'= ({_f(Gs)} + {_f(e0, 4)}) / (1 + {_f(e0, 4)}) × {_f(gamma_w)}</td>'
    r += f'<td>{_f(gamma_sat)} kN/m³</td></tr>'

    # Effective unit weight
    r += f'<tr><td>Effective unit weight, γ\'</td>'
    r += f'<td>γ\' = γ<sub>sat</sub> − γ<sub>w</sub> = {_f(gamma_sat)} − {_f(gamma_w)}</td>'
    r += f'<td>{_f(gamma_eff)} kN/m³</td></tr>'

    # Ko
    if phi > 0:
        r += f'<tr><td>At-rest earth pressure, K₀</td>'
        r += f'<td>K₀ = 1 − sin(φ) = 1 − sin({_f(phi, 0)}°)</td>'
        r += f'<td>{_f(Ko, 9)}</td></tr>'
    else:
        r += f'<tr><td>At-rest earth pressure, K₀</td><td>Assumed (φ = 0)</td><td>{_f(Ko, 4)}</td></tr>'

    # Dilatancy angle
    if phi > 30:
        r += f'<tr><td>Dilatancy angle, ψ</td>'
        r += f'<td>ψ = φ − 30° = {_f(phi, 0)}° − 30°</td>'
        r += f'<td>{_f(psi, 0)}°</td></tr>'
    else:
        r += f'<tr><td>Dilatancy angle, ψ</td>'
        r += f'<td>ψ = max(0, φ − 30°) → φ ≤ 30°</td>'
        r += f'<td>{_f(psi, 0)}°</td></tr>'

    # Specific storativity
    r += f'<tr><td>Specific storativity, Ss</td>'
    r += f'<td>Ss = γ<sub>w</sub> / E = {_f(gamma_w)} / {_f(E, 0)}</td>'
    r += f'<td>{Ss:.6e} 1/m</td></tr>'

    r += '</tbody></table>'

    # --- General tab ---
    r += '<h4>General (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Elastic Modulus, E</td><td>{_f(E, 0)} kN/m²</td></tr>'
    r += f'<tr><td style="text-align:left">Poisson\'s Ratio, ν</td><td>{_f(layer["nu"], 2)}</td></tr>'
    r += f'<tr><td style="text-align:left">Unit Weight, γ</td><td>{_f(gamma)} kN/m³</td></tr>'
    r += f'<tr><td style="text-align:left">Ko (1 − sinφ)</td><td>{_f(Ko, 9)}</td></tr>'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m²</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, φ</td><td>{_f(phi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Damping Ratio</td><td>{_f(layer["damping_ratio"], 2)}</td></tr>'
    r += '</table>'

    # --- Porous tab ---
    r += '<h4>Porous</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Unit Weight (Saturated)</td><td>{_f(gamma_sat)} kN/m³</td></tr>'
    r += f'<tr><td style="text-align:left">Initial Void Ratio, e₀</td><td>{_f(e0, 4)}</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kx</td><td>{layer["perm_kx"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability ky</td><td>{layer["perm_ky"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kz</td><td>{layer["perm_kz"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Storativity, Ss</td><td>{Ss:.6e} 1/m</td></tr>'
    r += '</table>'

    # --- Non-Linear tab ---
    r += '<h4>Non-Linear (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m²</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, φ</td><td>{_f(phi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Dilatancy Angle, ψ</td><td>{_f(psi, 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Tensile Strength</td><td>0 kN/m²</td></tr>'
    r += '</table>'

    # --- Derived ---
    r += '<h4>Derived Properties</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Dry Unit Weight, γ<sub>d</sub></td><td>{_f(gamma_d)} kN/m³</td></tr>'
    r += f'<tr><td style="text-align:left">Effective Unit Weight, γ\'</td><td>{_f(gamma_eff)} kN/m³</td></tr>'
    r += f'<tr><td style="text-align:left">Moisture Content</td><td>{_f(mc)}%</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Gravity, Gs</td><td>{_f(Gs)}</td></tr>'
    r += '</table>'

    return r
