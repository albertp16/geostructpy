"""
GeoStructPy Web Application
Lightweight Flask app for geotechnical engineering calculations.
Intended for APEC Consultancy team use.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# Load .env from project root (one level up from webapp/)
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

from calculators import terzaghi, meyerhof, mononobe_okabe, stability, micropile
from calculators import slope_stability, spt_depth, borehole_log, bored_pile
from calculators import sheet_pile, anchor

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
    defaults = dict(
        cohesion=10, gamma=18, phi=30, ftype='square', B=2.0, Df=1.5, FS=3.0,
        gamma_sat=20.0, water_table=-1.0,
    )
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
            gamma_sat=_float('gamma_sat', 20.0),
            water_table=_float('water_table', -1.0),
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
        beta=90, delta=20, kh=0.30, kv=0.0, cohesion=0.0,
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
            kh=_float('kh', 0.30),
            kv=_float('kv', 0.0),
            cohesion=_float('cohesion', 0.0),
        )
        results = mononobe_okabe.calculate(**params)
    return render_template("mononobe_okabe.html", params=params, results=results)


@app.route("/stability", methods=["GET", "POST"])
def stability_view():
    defaults = dict(
        h1=1.0, h2=1.0, t_stem=0.20, t_base=0.30, b_base=1.00, b_heel=0.80,
        gamma_s=18, phi=35.2, mu=0.35, q_bearing=125, gamma_c=23.56, q=0,
        y_front=0.0, include_passive=False, b_toe=0.0,
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
            y_front=_float('y_front', 0.0),
            include_passive=bool(request.form.get('include_passive')),
            b_toe=_float('b_toe', 0.0),
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

    # Prepare JSON for Handsontable
    combos_json = [[lc['label'], lc['Pu'], lc['Vu'], lc['Mu']] for lc in load_combos]

    return render_template("micropile.html",
                           params=params, results=results,
                           load_combos=load_combos, combos_json=combos_json,
                           bar_sizes=bar_sizes)


@app.route("/slope-stability", methods=["GET", "POST"])
def slope_stability_view():
    default_layers = [
        dict(name='LAYER 1', thickness=3.0, description='Sandy SILT', spt=7, phi=21, cohesion=0, E=11000, nu=0.2, gamma=13.27, moisture_content=22.64, Gs=2.65),
        dict(name='LAYER 2', thickness=3.0, description='Sandy lean CLAY', spt=10, phi=0, cohesion=30, E=11500, nu=0.2, gamma=14.63, moisture_content=45.26, Gs=2.65),
        dict(name='LAYER 3', thickness=7.0, description='Sandy SILT', spt=12, phi=0, cohesion=37, E=7500, nu=0.2, gamma=17.19, moisture_content=46.37, Gs=2.65),
    ]
    results = None
    computed = None
    layers = default_layers

    if request.method == "POST":
        lc = int(_float('layer_count', 0))
        layers = []
        for i in range(lc):
            layers.append(dict(
                name=request.form.get(f'ly_name_{i}', f'LAYER {i+1}'),
                thickness=_float(f'ly_thickness_{i}', 3.0),
                description=request.form.get(f'ly_desc_{i}', ''),
                spt=_float(f'ly_spt_{i}', 0),
                phi=_float(f'ly_phi_{i}', 30),
                cohesion=_float(f'ly_c_{i}', 0),
                E=_float(f'ly_E_{i}', 10000),
                nu=_float(f'ly_nu_{i}', 0.3),
                gamma=_float(f'ly_gamma_{i}', 18),
                moisture_content=_float(f'ly_mc_{i}', 0),
                Gs=_float(f'ly_Gs_{i}', 2.65),
                data_source=request.form.get(f'ly_src_{i}', '') or None,
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
            'thickness': ly['thickness'],
            'description': ly['description'],
            'spt': ly['spt'],
            'phi': ly['phi'],
            'cohesion': ly['cohesion'],
            'E': ly['E'],
            'nu': ly['nu'],
            'gamma': ly['gamma'],
            'moisture_content': ly['moisture_content'],
            'Gs': ly['Gs'],
            'data_source': ly.get('data_source') or '',
        })

    # Build soil profile chart, software table, parameters table, and borehole charts
    profile_chart = None
    software_table = None
    params_table = None
    bh_charts = {}
    if computed:
        profile_chart = slope_stability.build_soil_profile(computed)
        software_table = slope_stability.build_software_table(computed)
        params_table = slope_stability.build_parameters_table(computed)
        bh_charts = slope_stability.build_borehole_charts(computed)

    return render_template("slope_stability.html", layers=layers,
                           layers_json=layers_json, results=results,
                           profile_chart=profile_chart,
                           software_table=software_table,
                           params_table=params_table,
                           bh_charts=bh_charts)


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


@app.route("/borehole-log", methods=["GET", "POST"])
def borehole_log_view():
    has_api_key = bool(os.environ.get('ANTHROPIC_API_KEY'))
    results = None
    samples_json = []
    metadata = {'borehole_id': '', 'location': '', 'water_table_depth': ''}

    if request.method == "POST":
        sc = int(_float('sample_count', 0))
        samples = []
        for i in range(sc):
            samples.append({
                'sample_id': request.form.get(f's_id_{i}', ''),
                'depth': _float(f's_depth_{i}', 0),
                'sample_type': request.form.get(f's_type_{i}', 'SPT'),
                'spt_n': _float(f's_spt_{i}', 0) or None,
                'recovery_pct': _float(f's_rec_{i}', 0) or None,
                'rqd_pct': _float(f's_rqd_{i}', 0) or None,
                'description': request.form.get(f's_desc_{i}', ''),
                'classification': request.form.get(f's_cls_{i}', ''),
                'water_content': _float(f's_wc_{i}', 0) or None,
                'liquid_limit': _float(f's_wl_{i}', 0) or None,
                'plastic_limit': _float(f's_wp_{i}', 0) or None,
                'plasticity_index': _float(f's_pi_{i}', 0) or None,
                'ucs': _float(f's_ucs_{i}', 0) or None,
                'specific_gravity': _float(f's_sg_{i}', 0) or None,
            })

        wt = _float('water_table_depth', 0) or None
        metadata = {
            'borehole_id': request.form.get('borehole_id', ''),
            'location': request.form.get('location', ''),
            'water_table_depth': request.form.get('water_table_depth', ''),
        }

        if samples:
            results = borehole_log.build_charts(samples, wt)
            results['layer_table'] = borehole_log.build_layer_table(samples)

        samples_json = [
            [s['sample_id'], s['depth'], s['sample_type'],
             s['spt_n'], s['recovery_pct'], s['rqd_pct'],
             s['description'], s['classification'],
             s['water_content'], s['liquid_limit'], s['plastic_limit'],
             s['plasticity_index'], s['ucs'], s['specific_gravity']]
            for s in samples
        ]

    # Pass samples as dicts for the data table in results
    samples_data = []
    if request.method == "POST" and samples:
        for s in samples:
            n60 = round(s['spt_n'] * 72 / 60, 1) if s.get('spt_n') is not None else None
            ucs_kpa = None
            if s.get('ucs') is not None:
                ucs_kpa = round(s['ucs'] * 98.07, 1)
            elif n60 is not None:
                ucs_kpa = round(n60 * 12.5, 1)
            samples_data.append({**s, 'n60': n60, 'ucs_kpa': ucs_kpa})

    return render_template("borehole_log.html",
                           has_api_key=has_api_key,
                           results=results,
                           samples_json=samples_json,
                           samples_data=samples_data,
                           metadata=metadata)


@app.route("/api/borehole-extract", methods=["POST"])
def borehole_extract_api():
    try:
        data = request.get_json()
        if not data or 'image_base64' not in data:
            return jsonify({'error': 'Missing image_base64 in request body.'}), 400

        image_b64 = data['image_base64']
        mime = data.get('mime_type', 'image/png')

        result = borehole_log.extract_from_image(image_b64, mime)
        if 'error' in result:
            return jsonify(result), 500

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/slope-from-borehole", methods=["POST"])
def slope_from_borehole_api():
    """Convert borehole JSON to slope stability layers using Polish Code tables."""
    try:
        data = request.get_json()
        if not data or 'samples' not in data:
            return jsonify({'error': 'Missing samples in request body.'}), 400
        layers = slope_stability.derive_layers_from_borehole(data['samples'])
        return jsonify({'layers': layers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/bored-pile", methods=["GET", "POST"])
def bored_pile_view():
    defaults = dict(
        D=254, Lp=10.5, Wt=2.5, FS=3.5,
        fc=27.58, Yc=23.6, Cc=50,
        Fy=275.79, db=25, nbar=6,
        rock_type='Limestone', Co=7400, Nms=0.28, RQD='75-90',
        Vu=0, s_tie=150, db_tie=10,
    )
    results = None
    params = defaults
    borehole_json_str = ''

    if request.method == "POST":
        params = dict(
            D=_float('D', 254), Lp=_float('Lp', 10.5),
            Wt=_float('Wt', 2.5), FS=_float('FS', 3.5),
            fc=_float('fc', 27.58), Yc=_float('Yc', 23.6), Cc=_float('Cc', 50),
            Fy=_float('Fy', 275.79), db=_float('db', 25), nbar=int(_float('nbar', 6)),
            rock_type=request.form.get('rock_type', 'Limestone'),
            Co=_float('Co', 7400), Nms=_float('Nms', 0.28),
            RQD=request.form.get('RQD', '75-90'),
            Vu=_float('Vu', 0),
            s_tie=_float('s_tie', 150),
            db_tie=_float('db_tie', 10),
        )
        borehole_json_str = request.form.get('borehole_json', '')
        try:
            bh_data = json.loads(borehole_json_str)
            samples = bh_data.get('samples', [])
        except (json.JSONDecodeError, AttributeError):
            samples = []

        if samples:
            pile_params = dict(D=params['D'], Lp=params['Lp'], Wt=params['Wt'], FS=params['FS'])
            concrete_params = dict(fc=params['fc'], Yc=params['Yc'], Cc=params['Cc'])
            rebar_params = dict(Fy=params['Fy'], db=params['db'], nbar=params['nbar'])
            rock_params = dict(rock_type=params['rock_type'], Co=params['Co'],
                               Nms=params['Nms'], RQD=params['RQD'])
            shear_params = dict(Vu=params['Vu'], s=params['s_tie'], db_tie=params['db_tie'])
            results = bored_pile.calculate(samples, pile_params, concrete_params,
                                           rebar_params, rock_params, shear=shear_params)

    return render_template("bored_pile.html", params=params, results=results,
                           borehole_json_str=borehole_json_str)


@app.route("/sheet-pile", methods=["GET", "POST"])
def sheet_pile_view():
    defaults = dict(
        L=6.0, gamma=17.0, gamma_sat=20.0, phi=32.0,
        L1=2.0, q=10.0, sigma_allow=170000.0,
    )
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            L=_float('L', 6.0),
            gamma=_float('gamma', 17.0),
            gamma_sat=_float('gamma_sat', 20.0),
            phi=_float('phi', 32.0),
            L1=_float('L1', 2.0),
            q=_float('q', 10.0),
            sigma_allow=_float('sigma_allow', 170000.0),
        )
        try:
            results = sheet_pile.calculate(**params)
        except (ValueError, ZeroDivisionError) as e:
            results = {
                'report': f'<p style="color:#c0392b;"><strong>Calculation error:</strong> {e}</p>',
                'Ka': 0, 'Kp': 0, 'L3': 0, 'D_theoretical': 0, 'D_design': 0,
                'M_max': 0, 'S_req': 0, 'S_req_cm3_per_m': 0,
                'chart_traces': [], 'chart_layout': {},
            }
    return render_template("sheet_pile.html", params=params, results=results)


@app.route("/anchor", methods=["GET", "POST"])
def anchor_view():
    defaults = dict(
        B=1.5, h=1.5, H=3.0, soil_type='sand',
        gamma=18.0, phi=32.0, cu=50.0, FS=2.0,
    )
    results = None
    params = defaults
    if request.method == "POST":
        params = dict(
            B=_float('B', 1.5),
            h=_float('h', 1.5),
            H=_float('H', 3.0),
            soil_type=request.form.get('soil_type', 'sand'),
            gamma=_float('gamma', 18.0),
            phi=_float('phi', 32.0),
            cu=_float('cu', 50.0),
            FS=_float('FS', 2.0),
        )
        try:
            results = anchor.calculate(**params)
        except (ValueError, ZeroDivisionError) as e:
            results = {
                'report': f'<p style="color:#c0392b;"><strong>Calculation error:</strong> {e}</p>',
                'Pu': 0, 'Pa': 0, 'Rf': 0,
                'chart_traces': [], 'chart_layout': {},
            }
    return render_template("anchor.html", params=params, results=results)


@app.route("/changelog")
def changelog():
    return render_template("changelog.html")


@app.route("/theory")
def theory():
    return render_template("theory.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
