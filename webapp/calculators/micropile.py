"""Micropile design calculator (Metric) - NSCP 2015, AISC 14th, ACI 318-14/19."""
import math


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(D, db, nbar, fy, fc, cc, restrained, Qa, Fa, Pp, H, d, load_combos):
    D_m = D / 1000
    R = D / 2
    Ab = math.pi * db * db / 4 * nbar
    Ag = math.pi * D * D / 4
    Es = 200000
    ecu = 0.003
    ey = fy / Es

    tie = 10 if db <= 32 else 12
    dprime = cc + tie + db / 2
    deff = D - dprime

    if fc <= 28:
        beta1 = 0.85
    else:
        beta1 = max(0.85 - 0.05 * (fc - 28) / 7, 0.65)

    Ec = 4700 * math.sqrt(fc)

    # Governing loads
    Pu = max(load_combos, key=lambda lc: abs(lc['Pu']))['Pu']
    Vu = max(load_combos, key=lambda lc: abs(lc['Vu']))['Vu']
    Mu = max(load_combos, key=lambda lc: abs(lc['Mu']))['Mu']

    # SUMMARY
    sumr = '<table class="data-table" style="max-width:550px;">'
    sumr += f'<tr><td style="text-align:left">Section Diameter, D</td><td>{D} mm</td></tr>'
    sumr += f'<tr><td style="text-align:left">Center Bar</td><td>{nbar} - {db} mm (A<sub>s</sub> = {_f(Ab,0)} mm&sup2;)</td></tr>'
    sumr += f'<tr><td style="text-align:left">f<sub>y</sub></td><td>{fy} MPa</td></tr>'
    sumr += f'<tr><td style="text-align:left">f\'<sub>c</sub></td><td>{fc} MPa</td></tr>'
    sumr += f'<tr><td style="text-align:left">&beta;<sub>1</sub></td><td>{_f(beta1,4)}</td></tr>'
    sumr += f'<tr><td style="text-align:left">E<sub>c</sub></td><td>{_f(Ec,0)} MPa</td></tr>'
    sumr += f'<tr><td style="text-align:left">d<sub>eff</sub></td><td>{_f(deff,1)} mm</td></tr>'
    sumr += f'<tr><td style="text-align:left">d\'</td><td>{_f(dprime,1)} mm</td></tr>'
    sumr += f'<tr><td style="text-align:left">Height Above Grade, H</td><td>{H} m</td></tr>'
    sumr += f'<tr><td style="text-align:left">Total Embedment, d</td><td>{d} m</td></tr>'
    sumr += f'<tr style="font-weight:bold"><td style="text-align:left">Governing P<sub>u</sub></td><td>{_f(Pu,1)} kN</td></tr>'
    sumr += f'<tr style="font-weight:bold"><td style="text-align:left">Governing V<sub>u</sub></td><td>{_f(Vu,1)} kN</td></tr>'
    sumr += f'<tr style="font-weight:bold"><td style="text-align:left">Governing M<sub>u</sub></td><td>{_f(Mu,1)} kN-m</td></tr>'
    sumr += '</table>'

    # 1. SLENDERNESS
    K = 1
    r_mm = D / 4
    L_mm = (H if restrained else (H + d)) * 1000
    KLr = (K * L_mm) / r_mm
    slenderOK = KLr < 200

    sl = f'\\[ \\frac{{KL}}{{r}} = \\frac{{{K} \\times {_f(L_mm,0)}}}{{{_f(r_mm,1)}}} = {_f(KLr)} \\]'
    sl += f'\\[ {_f(KLr)} \\quad {"<" if slenderOK else "\\geq"} \\quad 200 \\quad \\textbf{{[{"Satisfactory" if slenderOK else "FAIL"}]}} \\]'
    sl += f'<p>where K = {K}, L = {_f(L_mm/1000,2)} m = {_f(L_mm,0)} mm, r = D/4 = {_f(r_mm,1)} mm</p>'

    # 2. SOIL COMPRESSION / TENSION
    Ag_m2 = math.pi * D_m * D_m / 4
    perim_m = math.pi * D_m
    skin_total = perim_m * Fa * d
    endBearing = Qa * Ag_m2
    Pc_capacity = skin_total + endBearing

    Wpile = 24 * Ag_m2 * (H + d)
    P_demand_comp = Pu + Wpile

    T_demand = max(0, -Pu)
    T_capacity = skin_total

    soilCompOK = P_demand_comp <= Pc_capacity
    soilTensOK = T_demand <= T_capacity

    so = '<h4>Compression Check</h4>'
    so += f'\\[ P_u + W_{{pile}} = {_f(Pu,1)} + {_f(Wpile,1)} = {_f(P_demand_comp,1)} \\text{{ kN}} \\]'
    so += f'\\[ \\pi D \\cdot d \\cdot F_a + \\frac{{\\pi D^2}}{{4}} Q_a = {_f(skin_total,1)} + {_f(endBearing,1)} = {_f(Pc_capacity,1)} \\text{{ kN}} \\]'
    so += f'\\[ {_f(P_demand_comp,1)} \\quad {"<" if soilCompOK else "\\geq"} \\quad {_f(Pc_capacity,1)} \\quad \\textbf{{[{"Satisfactory" if soilCompOK else "FAIL"}]}} \\]'
    so += '<h4>Tension Check</h4>'
    so += f'\\[ T = {_f(T_demand,1)} \\text{{ kN}} \\quad {"<" if soilTensOK else "\\geq"} \\quad \\pi D \\cdot d \\cdot F_a = {_f(T_capacity,1)} \\text{{ kN}} \\quad \\textbf{{[{"Satisfactory" if soilTensOK else "FAIL"}]}} \\]'

    # 3. LATERAL CAPACITY
    d_third = d / 3
    S3 = 2 * Pp * min(d, 3.66)
    S1 = 2 * Pp * min(d_third, 3.66)

    if restrained:
        d_req = math.sqrt(4.25 * Vu * H / (D_m * S3 + 0.001))
    else:
        A_nc = 2.34 * Vu / (D_m * S1 + 0.001)
        d_req = (A_nc / 2) * (1 + math.sqrt(1 + 4.36 * H / (A_nc + 0.001)))
    lateralOK = d_req <= d

    la = f'\\[ S_3 = 2 P_p \\min(d,\\, 3.66\\text{{m}}) = {_f(S3)} \\text{{ kPa}} \\]'
    la += f'\\[ S_1 = 2 P_p \\min(d/3,\\, 3.66\\text{{m}}) = {_f(S1)} \\text{{ kPa}} \\]'
    la += '<h4>Required Embedment Depth</h4>'
    la += f'\\[ d_{{req}} = {_f(d_req)} \\text{{ m}} \\quad {"<" if lateralOK else "\\geq"} \\quad d = {d} \\text{{ m}} \\quad \\textbf{{[{"Satisfactory" if lateralOK else "FAIL"}]}} \\]'

    # 4. P-M INTERACTION DIAGRAM
    Ast = Ab
    nom_P, nom_M, ult_P, ult_M, phi_list = [], [], [], [], []

    c_val = D * 1.5
    while c_val >= D * 0.05:
        a = beta1 * c_val

        es = ecu * (deff - c_val) / c_val
        es_prime = ecu * (c_val - dprime) / c_val
        fs = min(fy, max(-fy, es * Es))
        fs_prime = min(fy, max(-fy, es_prime * Es))

        if a >= D:
            Ac_seg = Ag
        elif a <= 0:
            Ac_seg = 0
        else:
            val = max(-1, min(1, (R - a) / R))
            Ac_seg = R * R * math.acos(val) - (R - a) * math.sqrt(max(0, 2 * R * a - a * a))

        Cc_circ = 0.85 * fc * Ac_seg / 1000
        T = Ast * min(fy, abs(fs)) * (1 if fs >= 0 else -1) / 1000
        Cs = Ast * (min(fy, abs(fs_prime)) * (1 if fs_prime >= 0 else -1) - 0.85 * fc) / 1000

        Pn = Cc_circ + Cs - T

        if Ac_seg > 1:
            yc = min(a, D) / 2
        else:
            yc = 0
        arm_cc = R - yc
        arm_cs = R - dprime
        arm_t = deff - R

        Mn = (Cc_circ * arm_cc + Cs * arm_cs + T * arm_t) / 1000

        if es >= 0.005:
            phi_val = 0.90
        elif es <= ey:
            phi_val = 0.65
        else:
            phi_val = 0.65 + 0.25 * (es - ey) / (0.005 - ey)
            phi_val = max(0.65, min(0.90, phi_val))

        ecc_val = abs(Mn / Pn * 1000) if Pn != 0 else 9999
        if ecc_val <= 1.5 * D:
            nom_P.append(Pn)
            nom_M.append(abs(Mn))
            ult_P.append(phi_val * Pn)
            ult_M.append(phi_val * abs(Mn))
            phi_list.append(phi_val)

        c_val -= D * 0.01

    # Pure compression cap
    Pn_max = (0.85 * fc * (Ag - Ab) + fy * Ab) / 1000
    Pn_max_capped = 0.80 * Pn_max

    for i in range(len(ult_P)):
        if ult_P[i] > 0.65 * Pn_max_capped:
            ult_P[i] = min(ult_P[i], 0.65 * Pn_max_capped)

    # Find phiMn at Pu
    phiMn_at_Pu = 0
    for i in range(len(ult_P) - 1):
        p1, p2 = ult_P[i], ult_P[i + 1]
        m1, m2 = ult_M[i], ult_M[i + 1]
        if (p1 >= Pu and p2 <= Pu) or (p1 <= Pu and p2 >= Pu):
            t = (Pu - p1) / (p2 - p1 + 0.0001)
            phiMn_at_Pu = m1 + t * (m2 - m1)
            break
    flexOK = phiMn_at_Pu >= Mu

    fl = '<h4>Material Properties</h4>'
    fl += f"\\[ E_c = 4700\\sqrt{{f'_c}} = 4700\\sqrt{{{fc}}} = {_f(Ec,0)} \\text{{ MPa}} \\]"
    fl += f'\\[ E_s = {Es} \\text{{ MPa}}, \\quad \\beta_1 = {_f(beta1,4)}, \\quad \\varepsilon_{{cu}} = {ecu} \\]'
    fl += f'\\[ A_g = \\frac{{\\pi D^2}}{{4}} = {_f(Ag,0)} \\text{{ mm}}^2, \\quad A_s = {_f(Ab,0)} \\text{{ mm}}^2 \\]'
    fl += '<h4>Interaction Diagram Check</h4>'
    fl += f'\\[ \\phi M_n \\text{{ @ }} P_u = {_f(Pu,1)} \\text{{ kN}} \\Rightarrow \\phi M_n = {_f(phiMn_at_Pu,1)} \\text{{ kN-m}} \\]'
    fl += f'\\[ \\phi M_n = {_f(phiMn_at_Pu,1)} \\quad {">" if flexOK else "<"} \\quad M_u = {_f(Mu,1)} \\quad \\textbf{{[{"Satisfactory" if flexOK else "FAIL"}]}} \\]'

    # 5. SHEAR
    Vc = (1 / 6) * math.sqrt(fc) * Ag / 1000
    phi_v = 0.75
    phiVn = phi_v * Vc
    shearOK = phiVn >= abs(Vu)

    sh = f"\\[ V_c = \\frac{{1}}{{6}}\\sqrt{{f'_c}} \\cdot A_g = \\frac{{1}}{{6}}\\sqrt{{{fc}}} \\times {_f(Ag,0)} = {_f(Vc,1)} \\text{{ kN}} \\]"
    sh += f'\\[ \\phi V_n = {phi_v} \\times {_f(Vc,1)} = {_f(phiVn,1)} \\text{{ kN}} \\]'
    sh += f'\\[ V_u = {_f(abs(Vu),1)} \\text{{ kN}} \\quad {"<" if shearOK else "\\geq"} \\quad \\phi V_n = {_f(phiVn,1)} \\text{{ kN}} \\quad \\textbf{{[{"Satisfactory" if shearOK else "FAIL"}]}} \\]'

    # SUMMARY TABLE
    summaryTable = [
        {'check': 'Slenderness (KL/r < 200)', 'demand': _f(KLr), 'capacity': '200', 'pass': slenderOK},
        {'check': 'Soil Compression', 'demand': _f(P_demand_comp, 1) + ' kN', 'capacity': _f(Pc_capacity, 1) + ' kN', 'pass': soilCompOK},
        {'check': 'Soil Tension', 'demand': _f(T_demand, 1) + ' kN', 'capacity': _f(T_capacity, 1) + ' kN', 'pass': soilTensOK},
        {'check': 'Lateral Embedment', 'demand': _f(d_req, 2) + ' m', 'capacity': str(d) + ' m', 'pass': lateralOK},
        {'check': 'Flexural (P-M)', 'demand': _f(Mu, 1) + ' kN-m', 'capacity': _f(phiMn_at_Pu, 1) + ' kN-m', 'pass': flexOK},
        {'check': 'Shear', 'demand': _f(abs(Vu), 1) + ' kN', 'capacity': _f(phiVn, 1) + ' kN', 'pass': shearOK},
    ]
    allPass = all(row['pass'] for row in summaryTable)

    # Interaction diagram chart
    comp_M, comp_P, trans_M, trans_P, tens_M, tens_P = [], [], [], [], [], []
    for i in range(len(ult_P)):
        if phi_list[i] <= 0.65:
            comp_M.append(ult_M[i]); comp_P.append(ult_P[i])
        elif phi_list[i] >= 0.90:
            tens_M.append(ult_M[i]); tens_P.append(ult_P[i])
        else:
            trans_M.append(ult_M[i]); trans_P.append(ult_P[i])

    if comp_M and trans_M:
        trans_M.insert(0, comp_M[-1]); trans_P.insert(0, comp_P[-1])
    if trans_M and tens_M:
        tens_M.insert(0, trans_M[-1]); tens_P.insert(0, trans_P[-1])

    chart_traces = [
        {"x": nom_M, "y": nom_P, "mode": "lines", "name": "Nominal (Pn, Mn)", "line": {"color": "#bdc3c7", "width": 1.5, "dash": "dot"}, "hoverinfo": "skip"},
        {"x": comp_M, "y": comp_P, "mode": "lines", "name": "Compression Controlled", "line": {"color": "#2c3e50", "width": 2.5, "dash": "dash"}, "fill": "none"},
        {"x": trans_M, "y": trans_P, "mode": "lines", "name": "Transition", "line": {"color": "#e74c3c", "width": 2.5}, "fill": "none"},
        {"x": tens_M, "y": tens_P, "mode": "lines", "name": "Tension Controlled", "line": {"color": "#2c3e50", "width": 2.5}, "fill": "none"},
    ]

    lcPts_x, lcPts_y, lcLabels = [], [], []
    for lc in load_combos:
        lcPts_x.append(abs(lc['Mu']))
        lcPts_y.append(lc['Pu'])
        lcLabels.append(lc['label'])
    chart_traces.append({
        "x": lcPts_x, "y": lcPts_y, "mode": "markers+text",
        "name": "Load Combinations", "text": lcLabels,
        "textposition": "top right", "textfont": {"size": 9, "color": "#7f8c8d"},
        "marker": {"size": 8, "color": "#e74c3c", "symbol": "square"}
    })
    chart_traces.append({
        "x": [abs(Mu)], "y": [Pu], "mode": "markers",
        "name": f"Governing (Pu={_f(Pu,0)}, Mu={_f(Mu,1)})",
        "marker": {"size": 12, "color": "#e74c3c", "symbol": "diamond", "line": {"width": 2, "color": "#c0392b"}}
    })

    all_m = ult_M + nom_M + [abs(Mu)]
    all_p = ult_P + nom_P + [Pu]
    maxM = max(all_m) * 1.15 if all_m else 10
    maxP = max(all_p) * 1.15 if all_p else 10
    minP = min(min(all_p), 0, Pu) * 1.15 if all_p else -10

    chart_layout = {
        "title": {"text": "P-M Interaction Diagram", "font": {"size": 15, "color": "#2c3e50"}},
        "xaxis": {"title": "\u03D5 Mn (kN-m)", "range": [0, maxM], "gridcolor": "#ecf0f1", "zeroline": True, "zerolinecolor": "#bdc3c7"},
        "yaxis": {"title": "\u03D5 Pn (kN)", "range": [minP, maxP], "gridcolor": "#ecf0f1", "zeroline": True, "zerolinecolor": "#bdc3c7", "zerolinewidth": 2},
        "height": 500,
        "margin": {"t": 50, "r": 40, "b": 60, "l": 70},
        "legend": {"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center", "font": {"size": 10}},
        "plot_bgcolor": "#fafbfc", "paper_bgcolor": "#fff",
        "annotations": [
            {"x": abs(Mu), "y": Pu, "xref": "x", "yref": "y", "text": "Design Point", "showarrow": True,
             "arrowhead": 2, "ax": 40, "ay": -30, "font": {"size": 11, "color": "#e74c3c"}}
        ],
    }

    # Governing loads info for template
    gov = {'Pu': Pu, 'Vu': Vu, 'Mu': Mu}

    return {
        'summaryReport': sumr,
        'slendernessReport': sl,
        'soilReport': so,
        'lateralReport': la,
        'flexuralReport': fl,
        'shearReport': sh,
        'summaryTable': summaryTable,
        'allPass': allPass,
        'chart_traces': chart_traces,
        'chart_layout': chart_layout,
        'gov': gov,
    }
