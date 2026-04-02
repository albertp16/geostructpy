"""Terzaghi (1943) bearing capacity calculation."""
import math

# Bearing capacity factors (phi = 0 to 50)
T_NC = [5.70,6.00,6.30,6.62,6.97,7.34,7.73,8.15,8.60,9.09,9.61,10.16,10.76,11.41,12.11,12.86,13.68,14.60,15.12,16.56,17.69,18.92,20.27,21.75,23.36,25.13,27.09,29.24,31.61,34.24,37.16,40.41,44.04,48.09,52.64,57.75,63.53,70.01,77.50,85.97,95.66,106.81,119.67,134.58,151.95,172.28,196.22,224.55,258.28,298.71,347.50]
T_NQ = [1.00,1.10,1.22,1.35,1.49,1.64,1.81,2.00,2.21,2.44,2.69,2.98,3.29,3.63,4.02,4.45,4.92,5.45,6.04,6.70,7.44,8.26,9.19,10.23,11.40,12.72,14.21,15.90,17.81,19.98,22.46,25.28,28.52,32.23,36.50,41.44,47.16,53.80,61.55,70.61,81.27,93.85,108.75,126.50,147.74,173.28,204.19,241.80,287.85,344.64,415.14]
T_NY = [0.00,0.01,0.04,0.06,0.10,0.14,0.20,0.27,0.35,0.44,0.56,0.69,0.85,1.04,1.26,1.52,1.82,2.18,2.59,3.07,3.64,4.31,5.09,6.00,7.08,8.34,9.84,11.60,13.70,16.18,19.13,22.65,26.87,31.94,38.04,45.41,54.36,65.27,78.61,95.03,115.31,140.51,171.99,211.56,261.60,325.34,407.11,512.84,650.67,831.99,1072.80]


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


def calculate(cohesion, gamma, phi, ftype, B, Df, FS):
    c = cohesion
    g = gamma

    Nc = _interp(T_NC, phi)
    Nq = _interp(T_NQ, phi)
    Ny = _interp(T_NY, phi)

    if ftype == 'strip':
        Sc, Sr = 1.0, 1.0
    elif ftype == 'square':
        Sc, Sr = 1.3, 0.8
    else:
        Sc, Sr = 1.3, 0.6

    q = g * Df
    qu = c * Nc * Sc + q * Nq + 0.5 * g * B * Ny * Sr
    qall = qu / FS
    if ftype == 'circular':
        Qall = qall * B * math.pi * B / 4
    else:
        Qall = qall * B * B

    r = f"<h4>Bearing Capacity Factors (\\(\\phi' = {phi}^\\circ\\))</h4>"
    r += f"\\[ N_c = {_f(Nc,2)}, \\quad N_q = {_f(Nq,2)}, \\quad N_\\gamma = {_f(Ny,2)} \\]"
    r += f"<h4>Shape Factors ({ftype} footing)</h4>"
    r += f"\\[ S_c = {Sc}, \\quad S_\\gamma = {Sr} \\]"
    r += f"<h4>Surcharge</h4>"
    r += f"\\[ q = \\gamma \\cdot D_f = {g} \\times {Df} = {_f(q,2)} \\text{{ kPa}} \\]"
    r += f"<h4>Ultimate Bearing Capacity (Terzaghi, 1943)</h4>"
    r += f"\\[ q_u = c'N_cS_c + qN_q + \\tfrac{{1}}{{2}}\\gamma B N_\\gamma S_\\gamma \\]"
    r += f"\\[ q_u = ({c})({_f(Nc,2)})({Sc}) + ({_f(q,2)})({_f(Nq,2)}) + (0.5)({g})({B})({_f(Ny,2)})({Sr}) \\]"
    r += f"\\[ q_u = {_f(qu,2)} \\text{{ kPa}} \\]"
    r += f"<h4>Allowable Bearing Capacity</h4>"
    r += f"\\[ q_{{all}} = \\frac{{q_u}}{{FS}} = \\frac{{{_f(qu,2)}}}{{{FS}}} = {_f(qall,2)} \\text{{ kPa}} \\]"

    if ftype == 'circular':
        r += f"\\[ Q_{{all}} = q_{{all}} \\times \\frac{{\\pi B^2}}{{4}} = {_f(Qall,2)} \\text{{ kN}} \\]"
    else:
        r += f"\\[ Q_{{all}} = q_{{all}} \\times B^2 = {_f(Qall,2)} \\text{{ kN (for square area)}} \\]"

    # Chart data
    angles = list(range(51))
    nc_val = _interp(T_NC, phi)
    nq_val = _interp(T_NQ, phi)
    ny_val = _interp(T_NY, phi)
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
        {"x": list(T_NC), "y": angles, "mode": "lines", "name": "Nc", "line": {"color": "#2980b9", "width": 2}},
        {"x": list(T_NQ), "y": angles, "mode": "lines", "name": "Nq", "line": {"color": "#e67e22", "width": 2}},
        {"x": list(T_NY), "y": angles, "mode": "lines", "name": "N\u03B3", "line": {"color": "#27ae60", "width": 2}},
        *proj_lines,
        {"x": [nc_val], "y": [phi], "mode": "markers", "name": f"Nc={_f(nc_val,1)}", "marker": {"size": 10, "color": "#2980b9", "symbol": "diamond"}},
        {"x": [nq_val], "y": [phi], "mode": "markers", "name": f"Nq={_f(nq_val,1)}", "marker": {"size": 10, "color": "#e67e22", "symbol": "diamond"}},
        {"x": [ny_val], "y": [phi], "mode": "markers", "name": f"N\u03B3={_f(ny_val,1)}", "marker": {"size": 10, "color": "#27ae60", "symbol": "diamond"}},
    ]

    chart_layout = {
        "title": "Terzaghi Bearing Capacity Factors",
        "xaxis": {"title": "Bearing Capacity Factor", "type": "log", "range": [-1, 3.2]},
        "yaxis": {"title": "Friction Angle \u03C6\u2032 (deg)", "range": [0, 50]},
        "height": 420,
        "margin": {"t": 40, "r": 30, "b": 50, "l": 60},
        "legend": {"orientation": "h", "y": -0.18},
    }

    return {"report": r, "chart_traces": chart_traces, "chart_layout": chart_layout}
