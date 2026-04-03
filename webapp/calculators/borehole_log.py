"""Borehole log image digitizer using Claude Vision API."""

import json
import os


def _f(v, d=2):
    return f"{v:.{d}f}"


# ---------------------------------------------------------------------------
# AI Vision extraction
# ---------------------------------------------------------------------------

def _get_extraction_prompt():
    """Return the structured prompt for Claude Vision extraction."""
    return """You are a geotechnical data extraction specialist. Analyze this borehole log image and extract ALL visible data into the exact JSON structure below.

Return ONLY valid JSON — no markdown fencing, no commentary, no explanation.

{
  "borehole_id": "string or null",
  "location": "string or null",
  "elevation": "number in meters or null",
  "water_table_depth": "number in meters or null (look for inverted triangle symbol)",
  "end_of_log_depth": "number in meters or null",
  "samples": [
    {
      "sample_id": "string e.g. SS-1, CS-1",
      "depth": "number — midpoint depth in meters",
      "sample_type": "SPT or CORE",
      "spt_n": "integer blows/30cm or null for core samples",
      "recovery_pct": "number 0-100 or null",
      "rqd_pct": "number 0-100 or null",
      "description": "full soil/rock description text",
      "classification": "USCS code e.g. GM, SC, CL, SM, RK or null",
      "water_content": "number percent or null",
      "liquid_limit": "number or null",
      "plastic_limit": "number or null",
      "plasticity_index": "number or null",
      "ucs": "number in kg/cm2 or null",
      "specific_gravity": "number or null"
    }
  ]
}

Rules:
- Use null for any value NOT clearly visible — NEVER guess
- Distinguish SPT samples (SS-#) from core samples (CS-#) via sample_type
- Depths in meters
- SPT N-value in blows per 30cm
- UCS (qu) in kg/cm2 as shown
- For soil descriptions include ALL text: type, color, consistency, density, classification
- Look for water table triangle/inverted-triangle symbol and report its depth
- Order samples by depth (shallowest first)
- If recovery is shown as a percentage, record it
- If RQD is shown, record it (typically only for core samples)"""


def extract_from_image(image_base64, mime_type):
    """Send borehole log image to Claude Vision API and extract structured data.

    Returns dict with borehole metadata and samples list, or error dict.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {'error': 'ANTHROPIC_API_KEY environment variable not set.'}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": _get_extraction_prompt(),
                },
            ],
        }],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith('```'):
        lines = raw.split('\n')
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        raw = '\n'.join(lines)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {'error': 'Failed to parse AI response as JSON.', 'raw_response': raw}

    return data


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

_COLORS = ['#e6a817', '#2c3e50', '#2980b9', '#27ae60', '#8e44ad',
           '#e67e22', '#1abc9c', '#c0392b', '#d35400', '#7f8c8d']

_SOIL_COLORS = {
    'GM': '#c4a66a', 'GW': '#b8a050', 'GP': '#c9b97a', 'GC': '#a89060',
    'SM': '#d4b896', 'SW': '#c8a878', 'SP': '#d8c8a8', 'SC': '#d4a060',
    'CL': '#8fbc8f', 'CH': '#6b8e6b', 'ML': '#a8d8a8', 'MH': '#78a878',
    'OL': '#808060', 'OH': '#606040', 'PT': '#404020',
    'RK': '#a0a0a0', 'ROCK': '#a0a0a0',
}
_SOIL_COLORS_DEFAULT = '#d5dbdb'


def _base_layout(title, x_title, y_min, y_max, x_max, height=550):
    """Common layout for depth-based charts (X on top, Y inverted)."""
    return {
        "title": title,
        "xaxis": {
            "title": x_title,
            "side": "top",
            "range": [0, x_max],
            "gridcolor": "#ddd",
        },
        "yaxis": {
            "title": "Depth [m]",
            "range": [y_min, y_max],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": height,
        "margin": {"t": 80, "r": 40, "b": 40, "l": 70},
        "legend": {"x": 1.02, "y": 0.5, "xanchor": "left",
                   "bordercolor": "#333", "borderwidth": 1},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
    }


def _depth_range(samples, key):
    """Compute Y-axis range from samples that have a non-None value for key."""
    depths = [-s['depth'] for s in samples if s.get(key) is not None]
    if not depths:
        return -12, 1
    return min(min(depths) - 1, -12), 1


def _build_spt_chart(samples):
    """SPT N-value vs Depth."""
    pts = [(s['depth'], s['spt_n']) for s in samples if s.get('spt_n') is not None]
    if not pts:
        return None
    depths = [-d for d, _ in pts]
    values = [v for _, v in pts]
    x_max = max(values) * 1.15 if values else 60
    y_min, y_max = min(min(depths) - 1, -12), 1
    traces = [{
        "x": values, "y": depths,
        "mode": "lines+markers", "name": "SPT N",
        "marker": {"size": 9, "color": "#2c3e50", "symbol": "circle"},
        "line": {"color": "#2c3e50", "width": 1.5},
    }]
    layout = _base_layout("SPT N-value vs. Depth",
                          "SPT N-value, N [b/0.3m]", y_min, y_max, x_max)
    layout["xaxis"]["dtick"] = 10
    return {'traces': traces, 'layout': layout}


def _build_n60_chart(samples):
    """Corrected N₆₀ vs Depth."""
    pts = [(s['depth'], s['spt_n']) for s in samples if s.get('spt_n') is not None]
    if not pts:
        return None
    depths = [-d for d, _ in pts]
    values = [round(v * 72 / 60, 1) for _, v in pts]
    x_max = max(values) * 1.15 if values else 60
    y_min, y_max = min(min(depths) - 1, -12), 1
    traces = [{
        "x": values, "y": depths,
        "mode": "lines+markers", "name": "N\u2086\u2080",
        "marker": {"size": 9, "color": "#2980b9", "symbol": "square"},
        "line": {"color": "#2980b9", "width": 1.5},
    }]
    layout = _base_layout("Corrected SPT N\u2086\u2080 vs. Depth",
                          "SPT N\u2086\u2080 [b/0.3m]", y_min, y_max, x_max)
    layout["xaxis"]["dtick"] = 10
    return {'traces': traces, 'layout': layout}


def _build_ucs_chart(samples):
    """UCS vs Depth — uses extracted UCS if available, else empirical from N60."""
    pts = []
    for s in samples:
        if s.get('ucs') is not None:
            # Convert kg/cm2 to kPa (1 kg/cm2 ≈ 98.07 kPa)
            pts.append((s['depth'], round(s['ucs'] * 98.07, 1)))
        elif s.get('spt_n') is not None:
            n60 = s['spt_n'] * 72 / 60
            pts.append((s['depth'], round(n60 * 12.5, 1)))
    if not pts:
        return None
    depths = [-d for d, _ in pts]
    values = [v for _, v in pts]
    x_max = max(values) * 1.15 if values else 500
    y_min, y_max = min(min(depths) - 1, -12), 1
    traces = [{
        "x": values, "y": depths,
        "mode": "lines+markers", "name": "UCS",
        "marker": {"size": 9, "color": "#27ae60", "symbol": "diamond"},
        "line": {"color": "#27ae60", "width": 1.5},
    }]
    # Median line
    sorted_v = sorted(values)
    n = len(sorted_v)
    med = sorted_v[n // 2] if n % 2 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
    traces.append({
        "x": [med, med], "y": [min(depths) - 1, max(depths) + 1],
        "mode": "lines", "name": f"Median = {_f(med, 1)} kPa",
        "line": {"color": "#c0392b", "width": 2, "dash": "dash"},
    })
    layout = _base_layout("UCS (q\u1D64) vs. Depth",
                          "UCS, q\u1D64 [kPa]", y_min, y_max, x_max)
    return {'traces': traces, 'layout': layout}


def _build_water_content_chart(samples):
    """Water content, liquid limit, plastic limit vs Depth."""
    wc = [(s['depth'], s['water_content']) for s in samples if s.get('water_content') is not None]
    wl = [(s['depth'], s['liquid_limit']) for s in samples if s.get('liquid_limit') is not None]
    wp = [(s['depth'], s['plastic_limit']) for s in samples if s.get('plastic_limit') is not None]
    if not wc and not wl and not wp:
        return None
    traces = []
    all_vals = []
    all_depths = []
    if wc:
        depths_wc = [-d for d, _ in wc]
        vals_wc = [v for _, v in wc]
        all_vals.extend(vals_wc)
        all_depths.extend(depths_wc)
        traces.append({
            "x": vals_wc, "y": depths_wc,
            "mode": "lines+markers", "name": "w (natural)",
            "marker": {"size": 8, "color": "#2c3e50", "symbol": "circle"},
            "line": {"color": "#2c3e50", "width": 1.5},
        })
    if wl:
        depths_wl = [-d for d, _ in wl]
        vals_wl = [v for _, v in wl]
        all_vals.extend(vals_wl)
        all_depths.extend(depths_wl)
        traces.append({
            "x": vals_wl, "y": depths_wl,
            "mode": "lines+markers", "name": "w\u2097 (liquid limit)",
            "marker": {"size": 8, "color": "#2980b9", "symbol": "square"},
            "line": {"color": "#2980b9", "width": 1.5},
        })
    if wp:
        depths_wp = [-d for d, _ in wp]
        vals_wp = [v for _, v in wp]
        all_vals.extend(vals_wp)
        all_depths.extend(depths_wp)
        traces.append({
            "x": vals_wp, "y": depths_wp,
            "mode": "lines+markers", "name": "w\u209A (plastic limit)",
            "marker": {"size": 8, "color": "#e67e22", "symbol": "triangle-up"},
            "line": {"color": "#e67e22", "width": 1.5},
        })
    x_max = max(all_vals) * 1.3 if all_vals else 100
    y_min = min(all_depths) - 1 if all_depths else -12
    y_max = 1
    layout = _base_layout("Water Content vs. Depth", "Water Content [%]",
                          min(y_min, -12), y_max, x_max)
    return {'traces': traces, 'layout': layout}


def _build_rqd_chart(samples):
    """RQD% vs Depth for core samples."""
    pts = [(s['depth'], s['rqd_pct']) for s in samples if s.get('rqd_pct') is not None]
    if not pts:
        return None
    depths = [-d for d, _ in pts]
    values = [v for _, v in pts]
    y_min, y_max = min(min(depths) - 1, -12), 1
    traces = [{
        "x": values, "y": depths,
        "mode": "lines+markers", "name": "RQD",
        "marker": {"size": 9, "color": "#8e44ad", "symbol": "hexagon"},
        "line": {"color": "#8e44ad", "width": 1.5},
    }]
    layout = _base_layout("RQD vs. Depth", "RQD [%]", y_min, y_max, 110)
    return {'traces': traces, 'layout': layout}


def _build_recovery_chart(samples):
    """Recovery% vs Depth."""
    pts = [(s['depth'], s['recovery_pct']) for s in samples if s.get('recovery_pct') is not None]
    if not pts:
        return None
    depths = [-d for d, _ in pts]
    values = [v for _, v in pts]
    y_min, y_max = min(min(depths) - 1, -12), 1
    traces = [{
        "x": values, "y": depths,
        "mode": "lines+markers", "name": "Recovery",
        "marker": {"size": 9, "color": "#e67e22", "symbol": "pentagon"},
        "line": {"color": "#e67e22", "width": 1.5},
    }]
    layout = _base_layout("Recovery vs. Depth", "Recovery [%]", y_min, y_max, 110)
    return {'traces': traces, 'layout': layout}


def _group_into_layers(samples):
    """Group consecutive samples with the same classification into layers."""
    if not samples:
        return []
    layers = []
    current = {
        'name': samples[0].get('classification') or 'Unknown',
        'description': samples[0].get('description') or '',
        'samples': [samples[0]],
    }
    for s in samples[1:]:
        cls = s.get('classification') or 'Unknown'
        if cls == current['name']:
            current['samples'].append(s)
        else:
            layers.append(current)
            current = {'name': cls, 'description': s.get('description') or '', 'samples': [s]}
    layers.append(current)

    # Compute layer properties
    result = []
    depth_top = 0
    for i, ly in enumerate(layers):
        spt_vals = [s['spt_n'] for s in ly['samples'] if s.get('spt_n') is not None]
        avg_spt = round(sum(spt_vals) / len(spt_vals), 1) if spt_vals else None

        min_depth = min(s['depth'] for s in ly['samples'])
        max_depth = max(s['depth'] for s in ly['samples'])

        # Estimate thickness
        if i == 0:
            top = 0
        else:
            prev_max = max(s['depth'] for s in layers[i - 1]['samples'])
            top = round((prev_max + min_depth) / 2, 2)
        if i < len(layers) - 1:
            next_min = min(s['depth'] for s in layers[i + 1]['samples'])
            bot = round((max_depth + next_min) / 2, 2)
        else:
            bot = round(max_depth + 1, 2)

        thickness = round(bot - top, 2)

        result.append({
            'num': i + 1,
            'name': f'LAYER {i + 1}',
            'classification': ly['name'],
            'description': ly['description'],
            'depth_top': top,
            'depth_bottom': bot,
            'thickness': thickness,
            'avg_spt': avg_spt,
            'sample_count': len(ly['samples']),
        })
        depth_top = bot

    return result


def _build_soil_profile(samples):
    """Build coloured soil profile from grouped layers."""
    layers = _group_into_layers(samples)
    if not layers:
        return None

    layer_colors = ['#aed6f1', '#a9dfbf', '#f9e79f', '#d2b4de', '#f5cba7',
                    '#a3e4d7', '#fadbd8', '#d5dbdb', '#abebc6', '#f5b7b1']
    traces = []
    annotations = []

    for i, ly in enumerate(layers):
        cls = ly['classification']
        col = _SOIL_COLORS.get(cls.upper(), layer_colors[i % len(layer_colors)])
        top = -ly['depth_top']
        bot = -ly['depth_bottom']
        mid = (top + bot) / 2

        spt_text = f" | SPT={ly['avg_spt']}" if ly['avg_spt'] is not None else ''
        desc = ly['description']
        if len(desc) > 35:
            desc = desc[:32] + '...'

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
            "text": f"{ly['name']}: {ly['description']}<br>"
                    f"{_f(ly['depth_top'])}-{_f(ly['depth_bottom'])} m<br>"
                    f"t = {_f(ly['thickness'])} m{spt_text}",
        })

        annotations.append({
            "x": 0.5, "y": mid,
            "text": f"<b>{ly['name']}</b><br>{desc}<br>"
                    f"t={_f(ly['thickness'])}m{spt_text}",
            "showarrow": False,
            "font": {"size": 11},
            "xanchor": "center",
        })

    max_depth = max(ly['depth_bottom'] for ly in layers) + 1
    layout = {
        "title": "Soil Profile",
        "xaxis": {"visible": False, "range": [-0.2, 1.2]},
        "yaxis": {
            "title": "Depth [m]",
            "range": [-(max_depth), 1],
            "dtick": 1,
            "gridcolor": "#ddd",
        },
        "height": max(450, int(max_depth * 40)),
        "width": 350,
        "margin": {"t": 40, "r": 20, "b": 30, "l": 60},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "annotations": annotations,
    }
    return {'traces': traces, 'layout': layout}


def build_layer_table(samples):
    """Build an HTML layer summary table similar to slope stability output."""
    layers = _group_into_layers(samples)
    if not layers:
        return ''

    r = '<table class="data-table" style="font-size:0.85em;">'
    r += '<thead><tr>'
    r += '<th>#</th><th>Layer Name</th><th>Thickness (m)</th>'
    r += '<th>Description</th><th>SPT N</th><th>Classification</th>'
    r += '<th>Depth Range (m)</th><th>Samples</th>'
    r += '</tr></thead><tbody>'

    for ly in layers:
        spt_str = _f(ly['avg_spt'], 1) if ly['avg_spt'] is not None else '-'
        r += f'<tr>'
        r += f'<td>{ly["num"]}</td>'
        r += f'<td>{ly["name"]}</td>'
        r += f'<td>{_f(ly["thickness"])}</td>'
        r += f'<td>{ly["description"]}</td>'
        r += f'<td>{spt_str}</td>'
        r += f'<td><strong>{ly["classification"]}</strong></td>'
        r += f'<td>{_f(ly["depth_top"])}-{_f(ly["depth_bottom"])}</td>'
        r += f'<td>{ly["sample_count"]}</td>'
        r += f'</tr>'

    r += '</tbody></table>'
    return r


def build_charts(samples, water_table_depth=None):
    """Build all applicable charts from validated sample data.

    Returns dict of chart_name -> {traces, layout}. Skips charts with no data.
    """
    builders = {
        'spt': _build_spt_chart,
        'n60': _build_n60_chart,
        'ucs': _build_ucs_chart,
        'water_content': _build_water_content_chart,
        'rqd': _build_rqd_chart,
        'recovery': _build_recovery_chart,
        'soil_profile': _build_soil_profile,
    }

    charts = {}
    for name, builder in builders.items():
        result = builder(samples)
        if result is not None:
            # Add water table annotation if available
            if water_table_depth is not None and name != 'soil_profile':
                wt_y = -water_table_depth
                result['layout'].setdefault('shapes', []).append({
                    "type": "line",
                    "x0": 0, "x1": 1, "xref": "paper",
                    "y0": wt_y, "y1": wt_y,
                    "line": {"color": "#2980b9", "width": 2, "dash": "dash"},
                })
                result['layout'].setdefault('annotations', []).append({
                    "x": 1, "xref": "paper", "y": wt_y,
                    "text": f"WT = {_f(water_table_depth)} m",
                    "showarrow": False,
                    "font": {"size": 10, "color": "#2980b9"},
                    "xanchor": "left",
                })
            charts[name] = result

    # Summary statistics
    summaries = []
    spt_vals = [s['spt_n'] for s in samples if s.get('spt_n') is not None]
    if spt_vals:
        summaries.append({
            'label': 'SPT N-value',
            'count': len(spt_vals),
            'min': _f(min(spt_vals), 0),
            'max': _f(max(spt_vals), 0),
            'avg': _f(sum(spt_vals) / len(spt_vals), 1),
        })

    return {'charts': charts, 'summaries': summaries}
