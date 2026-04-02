"""SPT N-value, N60, and UCS vs Depth chart generator."""


def _f(v, d=2):
    return f"{v:.{d}f}"


def calculate(boreholes, chart_type='spt'):
    """
    boreholes: list of dicts, each:
        {
            'name': 'BH-01',
            'data': [
                {'depth': 1.5, 'value': 38},
                ...
            ]
        }
    chart_type: 'spt' | 'n60' | 'ucs'
    Returns chart traces/layout and summary table.
    """
    colors = ['#e6a817', '#2c3e50', '#2980b9', '#27ae60', '#8e44ad',
              '#e67e22', '#1abc9c', '#c0392b', '#d35400', '#7f8c8d']
    symbols = ['triangle-up', 'square', 'circle', 'diamond',
               'triangle-down', 'pentagon', 'hexagon', 'star',
               'cross', 'x']

    titles = {
        'spt': 'SPT N-value, N [b/0.3m]',
        'n60': 'SPT N-value, N\u2086\u2080 [b/0.3m]',
        'ucs': 'Unconfined Compressive Strength, UCS or q\u1D64 [kPa]',
    }
    chart_titles = {
        'spt': 'Measured SPT N values (N) vs. Depth',
        'n60': 'Corrected SPT N values (N\u2086\u2080) vs. Depth',
        'ucs': 'Unconfined Compressive Strength (UCS or q\u1D64) vs. Depth',
    }

    traces = []
    all_depths = []
    all_values = []

    for i, bh in enumerate(boreholes):
        col = colors[i % len(colors)]
        sym = symbols[i % len(symbols)]
        depths = [-pt['depth'] for pt in bh['data'] if pt.get('value') is not None]
        values = [pt['value'] for pt in bh['data'] if pt.get('value') is not None]

        all_depths.extend(depths)
        all_values.extend(values)

        traces.append({
            "x": values, "y": depths,
            "mode": "markers", "name": bh['name'],
            "marker": {"size": 10, "color": col, "symbol": sym},
        })

    # Add median line for UCS
    if chart_type == 'ucs' and all_values:
        sorted_vals = sorted(all_values)
        n = len(sorted_vals)
        median_val = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        if all_depths:
            min_d = min(all_depths)
            max_d = max(all_depths)
            traces.append({
                "x": [median_val, median_val], "y": [max_d + 1, min_d - 1],
                "mode": "lines", "name": "Median Line",
                "line": {"color": "#27ae60", "width": 2.5},
            })

    # Y-axis range
    if all_depths:
        y_min = min(min(all_depths) - 1, -30)
        y_max = 1
    else:
        y_min = -30
        y_max = 1

    # X-axis range
    if all_values:
        x_max = max(all_values) * 1.1
    else:
        x_max = 100

    layout = {
        "title": chart_titles.get(chart_type, ''),
        "xaxis": {
            "title": titles.get(chart_type, ''),
            "side": "top",
            "range": [0, x_max],
            "dtick": 10 if chart_type != 'ucs' else None,
            "gridcolor": "#ddd",
        },
        "yaxis": {
            "title": "Depth [m]",
            "range": [y_min, y_max],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": 650,
        "margin": {"t": 80, "r": 40, "b": 40, "l": 70},
        "legend": {"x": 1.02, "y": 0.5, "xanchor": "left",
                   "bordercolor": "#333", "borderwidth": 1},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
    }

    # Summary stats
    summaries = []
    for bh in boreholes:
        vals = [pt['value'] for pt in bh['data'] if pt.get('value') is not None]
        depths = [pt['depth'] for pt in bh['data'] if pt.get('value') is not None]
        if vals:
            summaries.append({
                'name': bh['name'],
                'num_points': len(vals),
                'max_depth': _f(max(depths)),
                'min_val': _f(min(vals), 0),
                'max_val': _f(max(vals), 0),
                'avg_val': _f(sum(vals) / len(vals), 1),
            })

    return {
        'chart_traces': traces,
        'chart_layout': layout,
        'summaries': summaries,
        'chart_type': chart_type,
    }
