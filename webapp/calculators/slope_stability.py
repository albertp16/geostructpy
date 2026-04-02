"""Slope stability parameters calculator for Midas GTS NX material input."""
import math


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(layers):
    """
    Each layer dict:
        name, depth, description, spt, phi, cohesion, E, nu, gamma,
        moisture_content, gamma_sat (optional), void_ratio (optional),
        permeability (optional)

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
        # Void ratio: e = Gs * w / Sr (assume Sr=1 for saturated)
        w = mc / 100.0 if mc > 0 else 0.3
        e0 = Gs * w if mc > 0 else 0.5

        # Dry unit weight: gamma_d = gamma / (1 + w)
        gamma_d = gamma / (1 + w) if w > 0 else gamma

        # Saturated unit weight: gamma_sat = (Gs + e) / (1 + e) * gamma_w
        gamma_w = 9.81
        gamma_sat = (Gs + e0) / (1 + e0) * gamma_w

        # Effective unit weight
        gamma_eff = gamma_sat - gamma_w

        # Ko = 1 - sin(phi) (Jaky's formula)
        Ko = 1 - math.sin(math.radians(phi)) if phi > 0 else 0.5

        # Dilatancy angle (approximate: psi = phi - 30 for phi > 30, else 0)
        psi = max(0, phi - 30)

        # Default permeability based on soil type
        perm = layer.get('permeability', 1e-5)

        # Specific storativity Ss = gamma_w * (1/E + e0/(1+e0) * 1/E_water)
        # Simplified: Ss = gamma_w / E * (1 + e0) for compressible soils
        E_pa = E * 1000  # kPa to Pa for Ss calc
        Ss = gamma_w / (E if E > 0 else 10000)

        result = {
            'name': name,
            'depth': depth,
            'description': desc,
            'spt': spt,
            # General tab
            'E': E,
            'nu': nu,
            'gamma': gamma,
            'Ko': Ko,
            'cohesion': c,
            'phi': phi,
            'damping_ratio': 0.05,
            # Porous tab
            'gamma_sat': gamma_sat,
            'e0': e0,
            'perm_kx': perm,
            'perm_ky': perm,
            'perm_kz': perm,
            'Ss': Ss,
            # Non-Linear tab
            'psi': psi,
            # Derived
            'gamma_d': gamma_d,
            'gamma_eff': gamma_eff,
            'moisture_content': mc,
            'Gs': Gs,
        }
        results.append(result)

    return results


def build_report(layer):
    """Build HTML report for a single layer in Midas GTS NX format."""
    r = f'<h3>{layer["name"]} — {layer["description"]}</h3>'
    r += f'<p style="color:var(--muted);font-size:0.9em;">Depth: {layer["depth"]}'
    if layer['spt']:
        r += f' | SPT N = {layer["spt"]}'
    r += '</p>'

    # General tab
    r += '<h4>General (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Elastic Modulus, E</td><td>{_f(layer["E"], 0)} kN/m\u00b2</td></tr>'
    r += f'<tr><td style="text-align:left">Poisson\'s Ratio, \u03bd</td><td>{_f(layer["nu"], 2)}</td></tr>'
    r += f'<tr><td style="text-align:left">Unit Weight, \u03b3</td><td>{_f(layer["gamma"], 2)} kN/m\u00b3</td></tr>'
    r += f'<tr><td style="text-align:left">Ko (1 \u2212 sin\u03c6)</td><td>{_f(layer["Ko"], 9)}</td></tr>'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m\u00b2</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, \u03c6</td><td>{_f(layer["phi"], 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Damping Ratio</td><td>{_f(layer["damping_ratio"], 2)}</td></tr>'
    r += '</table>'

    # Porous tab
    r += '<h4>Porous</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Unit Weight (Saturated)</td><td>{_f(layer["gamma_sat"], 2)} kN/m\u00b3</td></tr>'
    r += f'<tr><td style="text-align:left">Initial Void Ratio, e\u2080</td><td>{_f(layer["e0"], 4)}</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kx</td><td>{layer["perm_kx"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability ky</td><td>{layer["perm_ky"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Permeability kz</td><td>{layer["perm_kz"]:.2e} m/sec</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Storativity, Ss</td><td>{layer["Ss"]:.6e} 1/m</td></tr>'
    r += '</table>'

    # Non-Linear tab
    r += '<h4>Non-Linear (Mohr-Coulomb)</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Cohesion, C</td><td>{_f(layer["cohesion"], 0)} kN/m\u00b2</td></tr>'
    r += f'<tr><td style="text-align:left">Frictional Angle, \u03c6</td><td>{_f(layer["phi"], 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Dilatancy Angle, \u03c8</td><td>{_f(layer["psi"], 0)} [deg]</td></tr>'
    r += f'<tr><td style="text-align:left">Tensile Strength</td><td>0 kN/m\u00b2</td></tr>'
    r += '</table>'

    # Derived
    r += '<h4>Derived Properties</h4>'
    r += '<table class="data-table" style="max-width:500px;">'
    r += f'<tr><td style="text-align:left">Dry Unit Weight, \u03b3<sub>d</sub></td><td>{_f(layer["gamma_d"], 2)} kN/m\u00b3</td></tr>'
    r += f'<tr><td style="text-align:left">Effective Unit Weight, \u03b3\'</td><td>{_f(layer["gamma_eff"], 2)} kN/m\u00b3</td></tr>'
    r += f'<tr><td style="text-align:left">Moisture Content</td><td>{_f(layer["moisture_content"], 2)}%</td></tr>'
    r += f'<tr><td style="text-align:left">Specific Gravity, Gs</td><td>{_f(layer["Gs"], 2)}</td></tr>'
    r += '</table>'

    return r
