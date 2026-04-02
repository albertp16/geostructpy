"""Mononobe-Okabe seismic earth pressure calculation."""
import math

DEG = math.pi / 180


def _f(v, d=3):
    return f"{v:.{d}f}"


def calculate(soil_weight, h_wall, alpha, phi, beta, delta, pga, kh, kv):
    g = soil_weight
    H = h_wall
    a = alpha
    ph = phi
    b = beta
    d = delta

    results = []

    # Seismic coefficients
    kh_val = kh * pga
    kv_val = kv * pga
    results.append(
        f"<h4>Seismic Parameters</h4>"
        f"\\[ k_h = {_f(kh_val)} \\quad k_v = {_f(kv_val)} \\]"
    )

    # Inclination angle theta
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

    # Total forces
    Pa_static = 0.5 * g * H * H * ka
    Pa_seismic = 0.5 * g * H * H * kae
    results.append(
        f"<h4>Earth Pressure Forces (per unit length)</h4>"
        f"\\[ P_{{a,static}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_a = {_f(Pa_static, 2)} \\text{{ kN/m}} \\]"
        f"\\[ P_{{a,seismic}} = \\tfrac{{1}}{{2}}\\gamma H^2 K_{{ae}} = {_f(Pa_seismic, 2)} \\text{{ kN/m}} \\]"
    )

    # Pressure chart data
    y_vals = []
    ps = []
    pe = []
    for i in range(21):
        z = (H / 20) * i
        y_vals.append(z)
        ps.append(g * z * ka)
        pe.append(g * z * kae)

    chart_traces = [
        {"x": ps, "y": y_vals, "mode": "lines", "name": "Static (Ka)", "line": {"color": "#3498db", "width": 2}},
        {"x": pe, "y": y_vals, "mode": "lines", "name": "Seismic (Kae)", "line": {"color": "#e74c3c", "width": 2}},
    ]

    chart_layout = {
        "title": "Lateral Pressure Distribution",
        "xaxis": {"title": "Pressure (kPa)"},
        "yaxis": {"title": "Depth (m)", "autorange": "reversed"},
        "height": 400,
        "margin": {"t": 40, "r": 30, "b": 50, "l": 60},
    }

    return {"results": results, "chart_traces": chart_traces, "chart_layout": chart_layout}
