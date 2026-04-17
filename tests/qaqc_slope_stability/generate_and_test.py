"""Internal QAQC test: generate 10 random borehole datasets, run them through
slope_stability.derive_layers_from_borehole + .calculate, and assert that the
QAQC fixes hold on every dataset.

Run:  py tests/qaqc_slope_stability/generate_and_test.py

Writes:
  tests/qaqc_slope_stability/dataset_01.json ... dataset_10.json
  tests/qaqc_slope_stability/report.md
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')

from webapp.calculators import slope_stability  # noqa: E402


# ---------------------------------------------------------------------------
# Random borehole generator
# ---------------------------------------------------------------------------

SOIL_POOL = [
    # (classification, description)
    ('CL',    'Gray, sandy CLAY, medium plastic, traces fine gravel'),
    ('CH',    'Brown, fat CLAY, high plasticity'),
    ('ML',    'Gray, sandy SILT, low plasticity'),
    ('MH',    'Brown, elastic SILT, high plasticity'),
    ('SM',    'Gray, silty SAND, non-plastic, with shell fragments'),
    ('SP',    'Gray, poorly graded fine SAND'),
    ('SW',    'Gray, well-graded SAND'),
    ('SP-SM', 'Gray, poorly graded SAND with silt'),
    ('SC-SM', 'Gray, silty-clayey SAND'),
    ('SC',    'Brown, clayey SAND'),
    ('GW',    'Gray, well-graded GRAVEL'),
    ('GW-SW', 'Gray, SAND and GRAVEL mixture'),
    ('GM',    'Gray, silty GRAVEL'),
    ('GC',    'Brown, clayey GRAVEL'),
]


def _random_spt(cls):
    if cls.startswith('C'):
        return random.randint(2, 30)
    if cls.startswith('M'):
        return random.randint(3, 35)
    return random.randint(5, 55)


def _maybe(p):
    return random.random() < p


def make_borehole(seed):
    """Generate a randomized borehole JSON payload."""
    rng = random.Random(seed)
    n_spt = rng.randint(12, 24)
    n_core = rng.choice([0, 0, 3, 5, 6])          # ~60% of boreholes hit rock
    include_nr = rng.random() < 0.6               # ~60% have No Recovery events

    samples = []
    depth = 1.5
    # ---- SPT run ---------------------------------------------------------
    segments = rng.randint(3, 5)
    picks = rng.sample(SOIL_POOL, k=min(segments, len(SOIL_POOL)))
    i = 1
    depth_cursor = depth
    for seg_idx, (cls, desc) in enumerate(picks):
        seg_len = rng.randint(2, 5)
        for _ in range(seg_len):
            if i > n_spt:
                break
            spt_n = _random_spt(cls)
            samples.append({
                'sample_id': f'SS-{i}',
                'depth': round(depth_cursor, 3),
                'sample_type': 'SPT',
                'spt_n': spt_n,
                'recovery_pct': round(rng.uniform(20, 95), 2),
                'rqd_pct': None,
                'description': desc,
                'classification': cls,
                'water_content': round(rng.uniform(10, 45), 2) if _maybe(0.8) else None,
                'liquid_limit': round(rng.uniform(25, 60), 1) if cls.startswith(('C', 'M')) and _maybe(0.5) else None,
                'plastic_limit': round(rng.uniform(15, 30), 1) if cls.startswith(('C', 'M')) and _maybe(0.5) else None,
                'plasticity_index': None,
                'ucs': None,
                'specific_gravity': round(rng.uniform(2.60, 2.85), 2) if _maybe(0.5) else None,
            })
            depth_cursor += rng.uniform(1.0, 1.8)
            i += 1

    # ---- No Recovery event(s) -------------------------------------------
    if include_nr:
        for _ in range(rng.randint(1, 3)):
            samples.append({
                'sample_id': f'SS-{i}',
                'depth': round(depth_cursor, 3),
                'sample_type': 'SPT',
                'spt_n': None,
                'recovery_pct': 0,
                'rqd_pct': None,
                'description': 'No Recovery',
                'classification': None,
                'water_content': None,
                'liquid_limit': None,
                'plastic_limit': None,
                'plasticity_index': None,
                'ucs': None,
                'specific_gravity': None,
            })
            depth_cursor += rng.uniform(0.8, 1.6)
            i += 1

    # ---- CORE run --------------------------------------------------------
    j = 1
    for _ in range(n_core):
        has_ucs = _maybe(0.75)
        samples.append({
            'sample_id': f'CS-{j}',
            'depth': round(depth_cursor, 3),
            'sample_type': 'CORE',
            'spt_n': None,
            'recovery_pct': round(rng.uniform(40, 100), 2),
            'rqd_pct': round(rng.uniform(20, 95), 1),
            'description': 'Gray, weathered fine-grained SANDSTONE',
            'classification': rng.choice([None, 'RK']),
            'water_content': round(rng.uniform(5, 25), 2) if _maybe(0.5) else None,
            'liquid_limit': None,
            'plastic_limit': None,
            'plasticity_index': None,
            'ucs': round(rng.uniform(10, 160), 2) if has_ucs else None,   # kg/cm²
            'specific_gravity': round(rng.uniform(2.60, 2.80), 2) if _maybe(0.4) else None,
        })
        depth_cursor += rng.uniform(0.8, 1.6)
        j += 1

    return {
        'borehole_id': f'BH-RANDOM-{seed:02d}',
        'location': 'Random QAQC test',
        'water_table_depth': round(rng.uniform(1.5, 6.0), 2),
        'samples': samples,
    }


# ---------------------------------------------------------------------------
# Assertions that encode the QAQC fixes
# ---------------------------------------------------------------------------

SAND_FAMILY = ('SM', 'SW', 'SP', 'GM', 'GW', 'GP')


def assert_qaqc(dataset, computed, layers_in):
    failures = []

    # 1) No CORE sample is swallowed by a No-Recovery layer
    core_samples = [s for s in dataset['samples'] if (s.get('sample_type') or '').upper() == 'CORE']
    core_layers = [ly for ly in computed if ly.get('is_core')]
    if len(core_samples) != sum(1 for ly in core_layers):
        failures.append(
            f'CORE sample count ({len(core_samples)}) != CORE layer count '
            f'({len(core_layers)}); QAQC #1 regression (CORE swallowed by NR)'
        )

    # 2) Sand-family layers: phi >= 26, cohesion == 0
    for ly in computed:
        cls0 = (ly.get('classification') or '').upper().split('-')[0]
        if ly.get('is_core') or ly.get('is_no_recovery'):
            continue
        if cls0 in SAND_FAMILY:
            if ly['cohesion'] > 1:
                failures.append(
                    f"{ly['name']} classified {ly.get('classification')} is sand-family "
                    f"but c={ly['cohesion']} kPa (expected 0) — QAQC consistency regression"
                )
            if ly['phi'] < 25:
                failures.append(
                    f"{ly['name']} sand-family has phi={ly['phi']}° (expected >=25°)"
                )

    # 3) Priority list: if any sample in a layer has water_content, the
    #    layer's moisture_content should match the mean (not a defaulted 0).
    for ly_in, ly_out in zip(layers_in, computed):
        # find raw samples that fed this layer: identify by description match
        if ly_out.get('is_no_recovery') or ly_out.get('is_core'):
            continue
        # moisture_content should never silently be 0 for a real layer
        if ly_out['moisture_content'] == 0:
            failures.append(
                f"{ly_out['name']}: moisture_content == 0 (fallback didn't fire)"
            )

    # 4) Per-layer permeability varies (not all 1e-5)
    perms = {ly['perm_kx'] for ly in computed}
    if len(perms) < 2 and len(computed) > 2:
        failures.append(
            f'All {len(computed)} layers share permeability={perms} — QAQC regression '
            '(porous defaults are not layer-specific)'
        )

    # 5) CORE layers should use ROCK physics
    for ly in core_layers:
        if ly['phi'] != 35 or ly['gamma'] != 24 or ly['E'] < 40000:
            failures.append(
                f"{ly['name']}: CORE layer but phi={ly['phi']}, gamma={ly['gamma']}, "
                f"E={ly['E']} — expected rock defaults"
            )

    # 6) Measured-UCS precedence for rock cohesion.
    # After the fix each CORE sample becomes its own layer, so we can pair
    # CORE samples and CORE layers 1:1 in input order and check precedence.
    core_sample_list = [
        s for s in sorted(dataset['samples'], key=lambda x: x.get('depth', 0))
        if (s.get('sample_type') or '').upper() == 'CORE'
    ]
    if len(core_sample_list) == len(core_layers):
        for s, ly in zip(core_sample_list, core_layers):
            if s.get('ucs') is not None and ly['cohesion'] == 100:
                failures.append(
                    f"{ly['name']}: sample {s.get('sample_id')} has measured UCS="
                    f"{s.get('ucs')} kg/cm² but cohesion stuck at 100 kPa default"
                )

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    HERE.mkdir(parents=True, exist_ok=True)
    report_lines = [
        '# Slope Stability QAQC — Internal Test Report',
        '',
        'Ten randomized borehole datasets were generated, piped through',
        '`slope_stability.derive_layers_from_borehole` + `.calculate`, and checked',
        'against the QAQC acceptance rules:',
        '',
        '1. Every CORE sample survives as its own layer (not swallowed by No-Recovery).',
        '2. All sand-family layers (SM/SW/SP/GM/GW/GP) use `c=0`, `phi >= 25°`.',
        '3. Layer moisture content is never silently left at 0 (priority list / fallback fires).',
        '4. At least two distinct per-layer permeabilities appear (porous tab is not a column of defaults).',
        '5. CORE layers use rock physics (`phi=35, gamma=24, E>=40000`).',
        '6. Measured UCS overrides the 100 kPa rock-cohesion default.',
        '',
        '| # | Borehole     | Samples | Layers | CORE | NR | Failures |',
        '|---|--------------|--------:|-------:|-----:|---:|:--------:|',
    ]

    total_failures = 0
    for seed in range(1, 11):
        data = make_borehole(seed)
        path = HERE / f'dataset_{seed:02d}.json'
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

        layers_in = slope_stability.derive_layers_from_borehole(data['samples'])
        computed = slope_stability.calculate(layers_in)

        n_core = sum(1 for ly in computed if ly.get('is_core'))
        n_nr = sum(1 for ly in computed if ly.get('is_no_recovery'))
        failures = assert_qaqc(data, computed, layers_in)
        total_failures += len(failures)

        status = '✅ 0' if not failures else f'❌ {len(failures)}'
        report_lines.append(
            f"| {seed:2d} | {data['borehole_id']} | {len(data['samples'])} | "
            f"{len(computed)} | {n_core} | {n_nr} | {status} |"
        )
        if failures:
            for f in failures:
                report_lines.append(f'  - {f}')

    report_lines.append('')
    report_lines.append(
        f"**Overall:** {'PASS — all 10 datasets satisfy the QAQC acceptance rules.' if total_failures == 0 else f'FAIL — {total_failures} rule violation(s) across 10 datasets.'}"
    )
    report_lines.append('')
    report_lines.append('## Per-dataset layer fingerprint')
    for seed in range(1, 11):
        data = json.loads((HERE / f'dataset_{seed:02d}.json').read_text(encoding='utf-8'))
        layers_in = slope_stability.derive_layers_from_borehole(data['samples'])
        computed = slope_stability.calculate(layers_in)
        report_lines.append('')
        report_lines.append(f"### `{data['borehole_id']}` — {len(data['samples'])} samples → {len(computed)} layers")
        report_lines.append('')
        report_lines.append('| Layer | Depth (m) | Class | N | φ (°) | c (kPa) | γ | MC% | Gs | k (m/s) | Flags |')
        report_lines.append('|-------|-----------|-------|--:|------:|--------:|--:|----:|---:|---------|-------|')
        for ly in computed:
            flags = []
            if ly.get('is_core'): flags.append('CORE')
            if ly.get('is_no_recovery'): flags.append('NR')
            report_lines.append(
                f"| {ly['name']} | {ly['depth_range']} | {ly.get('classification','')} | "
                f"{ly['spt']} | {ly['phi']} | {int(ly['cohesion'])} | {ly['gamma']} | "
                f"{ly['moisture_content']} | {ly['Gs']} | {ly['perm_kx']:.0e} | {' '.join(flags)} |"
            )

    (HERE / 'report.md').write_text('\n'.join(report_lines), encoding='utf-8')
    print('\n'.join(report_lines[:35]))
    print('...')
    print(f'\nReport written to {HERE / "report.md"}')
    print(f'Total failures across 10 datasets: {total_failures}')
    return 0 if total_failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
