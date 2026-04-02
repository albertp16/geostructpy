"""Meyerhof (1963) bearing capacity calculation."""
import math

DEG = math.pi / 180

M_NC = [5.14,5.38,5.63,5.90,6.19,6.49,6.81,7.16,7.53,7.92,8.35,8.80,9.28,9.81,10.37,10.98,11.63,12.34,13.10,13.93,14.83,15.82,16.88,18.05,19.32,20.72,22.25,23.94,25.80,27.86,30.14,32.67,35.49,38.64,42.16,46.12,50.59,55.63,61.35,67.87,75.31,83.86,93.71,105.11,118.37,133.88,152.10,173.64,199.26,229.93,266.89]
M_NQ = [1.00,1.09,1.20,1.31,1.43,1.57,1.72,1.88,2.06,2.25,2.47,2.71,2.97,3.26,3.59,3.94,4.34,4.77,5.26,5.80,6.40,7.07,7.82,8.66,9.60,10.66,11.85,13.20,14.72,16.44,18.40,20.63,23.18,26.09,29.44,33.30,37.75,42.92,48.93,55.96,64.20,73.90,85.38,99.02,115.31,134.88,158.51,187.21,222.32,265.51,319.07]
M_NY = [0.00,0.07,0.15,0.24,0.34,0.45,0.57,0.71,0.86,1.03,1.22,1.44,1.69,1.97,2.29,2.65,3.06,3.53,4.07,4.68,5.39,6.20,7.13,8.20,9.44,10.88,12.54,14.47,16.72,19.34,22.40,25.99,30.22,35.19,41.06,48.03,56.31,66.19,78.03,92.25,109.41,130.22,155.55,186.54,224.64,271.76,330.35,403.67,496.01,613.16,762.89]


def _interp(arr, phi):
    i = int(math.floor(phi))
    if i < 0:
        return arr[0]
    if i >= 50:
        return arr[50]
    frac = phi - i
    return arr[i] * (1 - frac) + arr[i + 1] * frac


def _f(v, d=3):
    return f"{v:.{d}f}"


def calculate(c, gamma, phi, theta, shape, B, L, Df, FS):
    g = gamma
    if shape == 'strip':
        L = 1000
    elif shape in ('square', 'circular'):
        L = B

    Nc = _interp(M_NC, phi)
    Nq = _interp(M_NQ, phi)
    Ny = _interp(M_NY, phi)
    q = g * Df

    # Shape factors
    Fcs = 1 + (B / L) * (Nq / Nc)
    Fqs = 1 + (B / L) * math.tan(phi * DEG)
    Fys = 1 - 0.4 * (B / L)

    # Depth factors
    ratio = Df / B
    if ratio <= 1:
        Fqd = 1 + 2 * math.tan(phi * DEG) * (1 - math.sin(phi * DEG)) ** 2 * ratio
        Fcd = Fqd - (1 - Fqd) / (Nq * math.tan(phi * DEG) + 0.001)
        Fyd = 1.0
    else:
        Fqd = 1 + 2 * math.tan(phi * DEG) * (1 - math.sin(phi * DEG)) ** 2 * math.atan(ratio)
        Fcd = Fqd - (1 - Fqd) / (Nq * math.tan(phi * DEG) + 0.001)
        Fyd = 1.0

    if phi == 0:
        Fcd = 1 + 0.4 * (ratio if ratio <= 1 else math.atan(ratio))

    # Inclination factors
    Fci = (1 - theta / 90) ** 2
    Fqi = Fci
    Fyi = (1 - theta / phi) ** 2 if theta > 0 and phi > 0 else 1.0

    # Ultimate bearing capacity
    term1 = c * Nc * Fcs * Fcd * Fci
    term2 = q * Nq * Fqs * Fqd * Fqi
    term3 = 0.5 * g * B * Ny * Fys * Fyd * Fyi
    qu = term1 + term2 + term3
    qall = qu / FS

    r = f"<h4>Bearing Capacity Factors (\\(\\phi' = {phi}^\\circ\\), Meyerhof)</h4>"
    r += f"\\[ N_c = {_f(Nc,2)}, \\quad N_q = {_f(Nq,2)}, \\quad N_\\gamma = {_f(Ny,2)} \\]"
    r += f"<h4>Shape Factors</h4>"
    r += f"\\[ F_{{cs}} = 1 + \\frac{{B}}{{L}}\\frac{{N_q}}{{N_c}} = {_f(Fcs,4)} \\]"
    r += f"\\[ F_{{qs}} = 1 + \\frac{{B}}{{L}}\\tan\\phi' = {_f(Fqs,4)} \\]"
    r += f"\\[ F_{{\\gamma s}} = 1 - 0.4\\frac{{B}}{{L}} = {_f(Fys,4)} \\]"
    r += f"<h4>Depth Factors (D<sub>f</sub>/B = {_f(ratio,2)})</h4>"
    r += f"\\[ F_{{cd}} = {_f(Fcd,4)}, \\quad F_{{qd}} = {_f(Fqd,4)}, \\quad F_{{\\gamma d}} = {_f(Fyd,4)} \\]"
    r += f"<h4>Inclination Factors (\\(\\theta = {theta}^\\circ\\))</h4>"
    r += f"\\[ F_{{ci}} = {_f(Fci,4)}, \\quad F_{{qi}} = {_f(Fqi,4)}, \\quad F_{{\\gamma i}} = {_f(Fyi,4)} \\]"
    r += f"<h4>Surcharge</h4>"
    r += f"\\[ q = \\gamma \\cdot D_f = {g} \\times {Df} = {_f(q,2)} \\text{{ kPa}} \\]"
    r += f"<h4>Ultimate Bearing Capacity (Meyerhof, 1963)</h4>"
    r += f"\\[ q_u = c'N_cF_{{cs}}F_{{cd}}F_{{ci}} + qN_qF_{{qs}}F_{{qd}}F_{{qi}} + \\tfrac{{1}}{{2}}\\gamma BN_\\gamma F_{{\\gamma s}}F_{{\\gamma d}}F_{{\\gamma i}} \\]"
    r += f"\\[ q_u = {_f(term1,2)} + {_f(term2,2)} + {_f(term3,2)} \\]"
    r += f"\\[ \\boxed{{q_u = {_f(qu,2)} \\text{{ kPa}}}} \\]"
    r += f"<h4>Allowable Bearing Capacity</h4>"
    r += f"\\[ q_{{all}} = \\frac{{q_u}}{{FS}} = \\frac{{{_f(qu,2)}}}{{{FS}}} = \\boxed{{{_f(qall,2)} \\text{{ kPa}}}} \\]"

    # Chart data
    angles = list(range(51))
    nc_val = _interp(M_NC, phi)
    nq_val = _interp(M_NQ, phi)
    ny_val = _interp(M_NY, phi)
    xmin = 0.1

    proj_lines = []
    for val, col in [(nc_val, '#2980b9'), (nq_val, '#e67e22'), (ny_val, '#27ae60')]:
        if val > 0:
            proj_lines.append({"x": [xmin, val], "y": [phi, phi], "mode": "lines",
                               "line": {"color": col, "width": 1, "dash": "dash"},
                               "showlegend": False, "hoverinfo": "skip"})
            proj_lines.append({"x": [val, val], "y": [phi, 0], "mode": "lines",
                               "line": {"color": col, "width": 1, "dash": "dash"},
                               "showlegend": False, "hoverinfo": "skip"})

    chart_traces = [
        {"x": list(M_NC), "y": angles, "mode": "lines", "name": "Nc", "line": {"color": "#2980b9", "width": 2}},
        {"x": list(M_NQ), "y": angles, "mode": "lines", "name": "Nq", "line": {"color": "#e67e22", "width": 2}},
        {"x": list(M_NY), "y": angles, "mode": "lines", "name": "N\u03B3", "line": {"color": "#27ae60", "width": 2}},
        *proj_lines,
        {"x": [nc_val], "y": [phi], "mode": "markers", "name": f"Nc={_f(nc_val,1)}", "marker": {"size": 10, "color": "#2980b9", "symbol": "diamond"}},
        {"x": [nq_val], "y": [phi], "mode": "markers", "name": f"Nq={_f(nq_val,1)}", "marker": {"size": 10, "color": "#e67e22", "symbol": "diamond"}},
        {"x": [ny_val], "y": [phi], "mode": "markers", "name": f"N\u03B3={_f(ny_val,1)}", "marker": {"size": 10, "color": "#27ae60", "symbol": "diamond"}},
    ]

    chart_layout = {
        "title": "Meyerhof Bearing Capacity Factors",
        "xaxis": {"title": "Bearing Capacity Factor", "type": "log", "range": [-1, 3.2]},
        "yaxis": {"title": "Friction Angle \u03C6\u2032 (deg)", "range": [0, 50]},
        "height": 420,
        "margin": {"t": 40, "r": 30, "b": 50, "l": 60},
        "legend": {"orientation": "h", "y": -0.18},
    }

    return {"report": r, "chart_traces": chart_traces, "chart_layout": chart_layout}
