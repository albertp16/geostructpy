"""
GeoStructPy Web Application
Lightweight Flask app for geotechnical engineering calculations.
Intended for APEC Consultancy team use.
"""

from flask import Flask, render_template, request

from calculators import terzaghi, meyerhof, mononobe_okabe, stability, micropile
from calculators import slope_stability, spt_depth

app = Flask(__name__)


def _float(key, default=0.0):
    try:
        return float(request.form.get(key, default))
    except (ValueError, TypeError):
        return default


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/terzaghi", methods=["GET", "POST"])
def terzaghi_view():
    defaults = dict(cohesion=10, gamma=18, phi=30, ftype='square', B=2.0, Df=1.5, FS=3.0)
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            cohesion=_float('cohesion', 10),
            gamma=_float('gamma', 18),
            phi=_float('phi', 30),
            ftype=request.form.get('ftype', 'square'),
            B=_float('B', 2.0),
            Df=_float('Df', 1.5),
            FS=_float('FS', 3.0),
        )
        results = terzaghi.calculate(**params)
    return render_template("terzaghi.html", params=params, results=results)


@app.route("/meyerhof", methods=["GET", "POST"])
def meyerhof_view():
    defaults = dict(c=0, gamma=18, phi=30, theta=0, shape='square', B=2.0, L=3.0, Df=1.5, FS=3.0)
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            c=_float('c', 0),
            gamma=_float('gamma', 18),
            phi=_float('phi', 30),
            theta=_float('theta', 0),
            shape=request.form.get('shape', 'square'),
            B=_float('B', 2.0),
            L=_float('L', 3.0),
            Df=_float('Df', 1.5),
            FS=_float('FS', 3.0),
        )
        results = meyerhof.calculate(**params)
    return render_template("meyerhof.html", params=params, results=results)


@app.route("/mononobe-okabe", methods=["GET", "POST"])
def mononobe_okabe_view():
    defaults = dict(
        soil_weight=7.2, h_wall=1.35, alpha=0, phi=40,
        beta=90, delta=20, pga=0.60, kh=0.50, kv=0.0,
    )
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            soil_weight=_float('soil_weight', 7.2),
            h_wall=_float('h_wall', 1.35),
            alpha=_float('alpha', 0),
            phi=_float('phi', 40),
            beta=_float('beta', 90),
            delta=_float('delta', 20),
            pga=_float('pga', 0.60),
            kh=_float('kh', 0.50),
            kv=_float('kv', 0.0),
        )
        results = mononobe_okabe.calculate(**params)
    return render_template("mononobe_okabe.html", params=params, results=results)


@app.route("/stability", methods=["GET", "POST"])
def stability_view():
    defaults = dict(
        h1=1.0, h2=1.0, t_stem=0.20, t_base=0.30, b_base=1.00, b_heel=0.80,
        gamma_s=18, phi=35.2, mu=0.35, q_bearing=125, gamma_c=23.56, q=0,
    )
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            h1=_float('h1', 1.0),
            h2=_float('h2', 1.0),
            t_stem=_float('t_stem', 0.20),
            t_base=_float('t_base', 0.30),
            b_base=_float('b_base', 1.00),
            b_heel=_float('b_heel', 0.80),
            gamma_s=_float('gamma_s', 18),
            phi=_float('phi', 35.2),
            mu=_float('mu', 0.35),
            q_bearing=_float('q_bearing', 125),
            gamma_c=_float('gamma_c', 23.56),
            q=_float('q', 0),
        )
        results = stability.calculate(**params)
    return render_template("stability.html", params=params, results=results)


@app.route("/micropile", methods=["GET", "POST"])
def micropile_view():
    bar_sizes = [10, 12, 16, 20, 25, 28, 32, 36, 40]
    default_combos = [
        {'label': '1.2D + 1.6L', 'Pu': 535, 'Vu': 1, 'Mu': 0},
        {'label': '1.2D + 1.0L + 1.0E', 'Pu': 480, 'Vu': 5, 'Mu': 2},
        {'label': '0.9D + 1.0E', 'Pu': 320, 'Vu': 5, 'Mu': 2},
        {'label': '1.2D + 1.6L + 0.5S', 'Pu': 535, 'Vu': 1, 'Mu': 0},
    ]
    defaults = dict(
        D=200, db=25, nbar=1, fy=415, fc=30, cc=45,
        restrained=0, Qa=7000, Fa=24, Pp=17, H=0.91, d=9.14,
    )
    results = None
    params = defaults
    load_combos = default_combos

    if request.method == "POST":
        params = dict(
            D=_float('D', 200),
            db=_float('db', 25),
            nbar=int(_float('nbar', 1)),
            fy=_float('fy', 415),
            fc=_float('fc', 30),
            cc=_float('cc', 45),
            restrained=int(_float('restrained', 0)),
            Qa=_float('Qa', 7000),
            Fa=_float('Fa', 24),
            Pp=_float('Pp', 17),
            H=_float('H', 0.91),
            d=_float('d', 9.14),
        )

        # Parse load combinations
        lc_count = int(_float('lc_count', 0))
        load_combos = []
        for i in range(lc_count):
            load_combos.append({
                'label': request.form.get(f'lc_label_{i}', 'Combination'),
                'Pu': _float(f'lc_Pu_{i}', 0),
                'Vu': _float(f'lc_Vu_{i}', 0),
                'Mu': _float(f'lc_Mu_{i}', 0),
            })
        if not load_combos:
            load_combos = default_combos

        results = micropile.calculate(
            D=params['D'], db=params['db'], nbar=params['nbar'],
            fy=params['fy'], fc=params['fc'], cc=params['cc'],
            restrained=params['restrained'],
            Qa=params['Qa'], Fa=params['Fa'], Pp=params['Pp'],
            H=params['H'], d=params['d'],
            load_combos=load_combos,
        )

    return render_template("micropile.html",
                           params=params, results=results,
                           load_combos=load_combos, bar_sizes=bar_sizes)


@app.route("/slope-stability", methods=["GET", "POST"])
def slope_stability_view():
    default_layers = [
        dict(name='LAYER 1', depth='0.00-3.00', description='Sandy SILT', spt=7, phi=21, cohesion=0, E=11000, nu=0.2, gamma=13.27, moisture_content=22.64, Gs=2.65),
        dict(name='LAYER 2', depth='3.00-6.00', description='Sandy lean CLAY', spt=10, phi=0, cohesion=30, E=11500, nu=0.2, gamma=14.63, moisture_content=45.26, Gs=2.65),
        dict(name='LAYER 3', depth='6.00-13.00', description='Sandy SILT', spt=12, phi=0, cohesion=37, E=7500, nu=0.2, gamma=17.19, moisture_content=46.37, Gs=2.65),
    ]
    results = None
    layers = default_layers

    if request.method == "POST":
        lc = int(_float('layer_count', 0))
        layers = []
        for i in range(lc):
            layers.append(dict(
                name=request.form.get(f'ly_name_{i}', f'LAYER {i+1}'),
                depth=request.form.get(f'ly_depth_{i}', ''),
                description=request.form.get(f'ly_desc_{i}', ''),
                spt=_float(f'ly_spt_{i}', 0),
                phi=_float(f'ly_phi_{i}', 30),
                cohesion=_float(f'ly_c_{i}', 0),
                E=_float(f'ly_E_{i}', 10000),
                nu=_float(f'ly_nu_{i}', 0.3),
                gamma=_float(f'ly_gamma_{i}', 18),
                moisture_content=_float(f'ly_mc_{i}', 0),
                Gs=_float(f'ly_Gs_{i}', 2.65),
            ))
        if not layers:
            layers = default_layers

        computed = slope_stability.calculate(layers)
        results = [slope_stability.build_report(ly) for ly in computed]

    # Prepare JSON for Handsontable
    layers_json = []
    for i, ly in enumerate(layers):
        layers_json.append({
            'row_num': i + 1,
            'name': ly['name'],
            'depth': ly['depth'],
            'description': ly['description'],
            'spt': ly['spt'],
            'phi': ly['phi'],
            'cohesion': ly['cohesion'],
            'E': ly['E'],
            'nu': ly['nu'],
            'gamma': ly['gamma'],
            'moisture_content': ly['moisture_content'],
            'Gs': ly['Gs'],
        })

    return render_template("slope_stability.html", layers=layers,
                           layers_json=layers_json, results=results)


@app.route("/spt-ucs", methods=["GET", "POST"])
def spt_ucs_view():
    default_boreholes = [
        {'name': 'BH-01', 'data': [
            {'depth': 1.5, 'value': 38}, {'depth': 3, 'value': 13},
            {'depth': 4.5, 'value': 17}, {'depth': 6, 'value': 14},
            {'depth': 7.5, 'value': 25}, {'depth': 9, 'value': 21},
        ]},
        {'name': 'BH-02', 'data': [
            {'depth': 1.5, 'value': 63}, {'depth': 3, 'value': 46},
            {'depth': 4.5, 'value': 20}, {'depth': 6, 'value': 11},
            {'depth': 7.5, 'value': 12}, {'depth': 9, 'value': 25},
        ]},
    ]
    results = None
    boreholes = default_boreholes

    if request.method == "POST":
        bh_count = int(_float('bh_count', 0))
        boreholes = []
        for b in range(bh_count):
            name = request.form.get(f'bh_name_{b}', f'BH-{b+1}')
            pt_count = int(_float(f'bh_pt_count_{b}', 0))
            data = []
            for p in range(pt_count):
                d = _float(f'bh_{b}_depth_{p}', 0)
                v = _float(f'bh_{b}_val_{p}', 0)
                data.append({'depth': d, 'value': v})
            boreholes.append({'name': name, 'data': data})
        if not boreholes:
            boreholes = default_boreholes

        results = spt_depth.calculate(boreholes)

    # Prepare JSON for Handsontable
    boreholes_json = []
    for bh in boreholes:
        boreholes_json.append({
            'name': bh['name'],
            'data': [[pt['depth'], pt['value']] for pt in bh['data']],
        })

    return render_template("spt_ucs.html",
                           boreholes=boreholes, boreholes_json=boreholes_json,
                           results=results)


@app.route("/changelog")
def changelog():
    return render_template("changelog.html")


@app.route("/theory")
def theory():
    return render_template("theory.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
