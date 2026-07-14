"""QAQC for the Mononobe-Okabe calculator.

Independent verification strategy: the closed-form coefficients are checked
against a brute-force trial-wedge search (maximize thrust P over the failure
plane angle rho) that shares no code with the closed forms. Also checks
static limits, polygon closure, and end-to-end report generation.

Run:  python tests/qaqc_mononobe_okabe/qaqc_mononobe_okabe.py
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "webapp"))

from calculators.mononobe_okabe import (  # noqa: E402
    calculate, coulomb_ka, coulomb_kp, mo_kae, mo_kpe,
    critical_wedge_angle, _wedge_equilibrium,
)

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))


def numeric_max_thrust(H, g, alpha, beta, phi, delta, kh, kv):
    """Brute-force trial-wedge search: independent of all closed forms."""
    best_p, best_rho = -1e30, None
    rho = alpha + 0.2
    while rho < 89.8:
        eq = _wedge_equilibrium(H, g, alpha, beta, phi, delta, rho, kh, kv)
        if eq and eq[0] > best_p:
            best_p, best_rho = eq[0], rho
        rho += 0.01
    return best_p, best_rho


# ---------------------------------------------------------------------------
print("=== 1. Static limits ===")
for phi, delta, alpha, beta in [(30, 15, 0, 90), (35, 20, 10, 85), (40, 20, 0, 90),
                                (28, 14, 5, 95), (33, 0, 0, 90)]:
    ka = coulomb_ka(phi, delta, alpha, beta)
    kae0 = mo_kae(phi, delta, alpha, beta, 0.0)
    check(f"Kae(theta=0)==Ka  phi={phi} d={delta} a={alpha} b={beta}",
          abs(kae0 - ka) < 1e-12, f"{kae0:.6f} vs {ka:.6f}")
    kp = coulomb_kp(phi, delta, alpha, beta)
    kpe0 = mo_kpe(phi, delta, alpha, beta, 0.0)
    if kp is not None and kpe0 is not None:
        check(f"Kpe(theta=0)==Kp  phi={phi} d={delta} a={alpha} b={beta}",
              abs(kpe0 - kp) / kp < 1e-9, f"{kpe0:.6f} vs {kp:.6f}")

print("=== 2. Critical angle: closed form vs Coulomb classic ===")
# delta=0, vertical wall, level fill -> 45 + phi/2 exactly
for phi in (25, 30, 35, 40):
    rho_cf = critical_wedge_angle(phi, 0, 0, 90, 0.0)
    check(f"alpha_A(static, d=0) == 45+phi/2  phi={phi}",
          abs(rho_cf - (45 + phi / 2)) < 1e-6, f"{rho_cf:.4f}")

print("=== 3. Critical angle & thrust: closed form vs numeric wedge search ===")
CASES = [
    # H, g, alpha, beta, phi, delta, kh, kv
    (1.35, 7.2, 0, 90, 40, 20, 0.30, 0.0),   # app defaults
    (5.0, 18.0, 0, 90, 35, 17.5, 0.20, 0.0),
    (5.0, 18.0, 10, 90, 35, 17.5, 0.15, 0.10),
    (4.0, 19.0, 5, 80, 33, 16, 0.25, 0.0),
    (6.0, 20.0, 0, 95, 38, 19, 0.18, -0.09),
    (3.0, 18.5, 0, 90, 30, 0, 0.10, 0.0),
]
for (H, g, a, b, ph, d, kh, kv) in CASES:
    th = math.degrees(math.atan2(kh, 1 - kv))
    kae = mo_kae(ph, d, a, b, th)
    rho_cf = critical_wedge_angle(ph, d, a, b, th)
    P_formula = 0.5 * g * H * H * kae * (1 - kv)
    P_num, rho_num = numeric_max_thrust(H, g, a, b, ph, d, kh, kv)
    check(f"rho closed-form vs numeric  case {(H, a, b, ph, d, kh, kv)}",
          abs(rho_cf - rho_num) < 0.05, f"{rho_cf:.3f} vs {rho_num:.3f}")
    check(f"P_ae formula vs numeric max thrust",
          abs(P_formula - P_num) / P_formula < 1e-4,
          f"{P_formula:.4f} vs {P_num:.4f}")
    eq = _wedge_equilibrium(H, g, a, b, ph, d, rho_cf, kh, kv)
    check(f"polygon closure at critical angle",
          eq is not None and abs(eq[0] - P_formula) / P_formula < 1e-6,
          f"{eq[0]:.6f} vs {P_formula:.6f}")

print("=== 4. Validity guard ===")
check("Kae None past limit", mo_kae(30, 15, 0, 90, 31.0) is None)
check("Kae defined at limit", mo_kae(30, 15, 0, 90, 29.99) is not None)

print("=== 5. End-to-end report generation ===")
SCEN = [
    dict(soil_weight=7.2, h_wall=1.35, alpha=0, phi=40, beta=90, delta=20,
         kh=0.30, kv=0.0, cohesion=0.0),
    dict(soil_weight=18, h_wall=5, alpha=10, phi=35, beta=85, delta=17.5,
         kh=0.20, kv=0.10, cohesion=0.0),
    dict(soil_weight=18, h_wall=4, alpha=0, phi=32, beta=90, delta=16,
         kh=0.15, kv=0.0, cohesion=10.0),          # cohesion path
    dict(soil_weight=18, h_wall=4, alpha=5, phi=32, beta=85, delta=16,
         kh=0.15, kv=0.0, cohesion=10.0),          # cohesion not applicable
    dict(soil_weight=19, h_wall=6, alpha=15, phi=30, beta=90, delta=15,
         kh=0.35, kv=0.0, cohesion=0.0),           # past M-O limit -> warning
    dict(soil_weight=18, h_wall=5, alpha=0, phi=35, beta=90, delta=0,
         kh=0.0, kv=0.0, cohesion=0.0),            # no seismic, no friction
]
for i, sc in enumerate(SCEN):
    try:
        out = calculate(**sc)
        json.dumps(out)  # must be JSON-serializable for the template
        s = out["summary"]
        ok = (s["kae"] > 0 and s["Pae"] >= 0 and
              all(k in out["figures"] for k in
                  ("cross_section", "force_polygon", "sensitivity", "pressure_dist")))
        check(f"scenario {i} report ok", ok,
              f"Kae={s['kae']:.4f} Pae={s['Pae']:.2f} valid={s['mo_valid']}")
        if s["closure"] is not None:
            check(f"scenario {i} QA closure < 0.01%", s["closure"] < 0.01,
                  f"{s['closure']:.5f}%")
        if not s["mo_valid"]:
            check(f"scenario {i} warning emitted", len(s["warnings"]) > 0)
    except Exception as e:  # noqa: BLE001
        check(f"scenario {i} report ok", False, f"{type(e).__name__}: {e}")

print("=== 6. z_bar sanity: between H/3 and 0.6H ===")
out = calculate(soil_weight=18, h_wall=5, alpha=0, phi=35, beta=90, delta=17.5,
                kh=0.20, kv=0.0, cohesion=0.0)
s = out["summary"]
check("H/3 <= z_bar <= 0.6H",
      5 / 3 - 1e-9 <= s["z_bar"] <= 3.0 + 1e-9, f"z_bar={s['z_bar']:.3f}")
check("kh=0 -> z_bar == H/3",
      abs(calculate(soil_weight=18, h_wall=5, alpha=0, phi=35, beta=90,
                    delta=17.5, kh=0.0, kv=0.0)["summary"]["z_bar"] - 5 / 3) < 1e-6)

print("=== 7. Review-finding regressions ===")


def expect_value_error(name, **kw):
    try:
        calculate(**kw)
        check(name, False, "no exception raised")
    except ValueError:
        check(name, True)
    except Exception as e:  # noqa: BLE001
        check(name, False, f"wrong exception {type(e).__name__}: {e}")


# 7a. c'-phi' with kv != 0: closed form must equal the numeric integral of
# the reported sigma_ae(z), and z_crack must be its zero-crossing.
out = calculate(soil_weight=18, h_wall=4, alpha=0, phi=32, beta=90, delta=16,
                kh=0.15, kv=0.10, cohesion=10.0)
s = out["summary"]
kae, zc = s["kae"], s["z_crack"]
g_, H_, kv_, c_ = 18.0, 4.0, 0.10, 10.0
sig = lambda z: max(kae * (1 - kv_) * g_ * z - 2 * c_ * math.sqrt(kae), 0.0)
n = 200000
integral = sum(sig(H_ * (i + 0.5) / n) for i in range(n)) * H_ / n
check("cohesion+kv: Pae == integral of sigma_ae", abs(s["Pae"] - integral) < 1e-3,
      f"{s['Pae']:.4f} vs {integral:.4f}")
check("cohesion+kv: sigma_ae(z_crack) == 0", abs(sig(zc)) < 1e-9, f"sig={sig(zc):.2e}")
check("cohesion+kv: z_bar within [z_a, 0.6H]",
      s["z_a"] - 1e-9 <= s["z_bar"] <= 0.6 * H_ + 1e-9,
      f"z_bar={s['z_bar']:.3f} z_a={s['z_a']:.3f}")

# 7b. Full-height tension crack -> zero thrust, z_bar bounded
out = calculate(soil_weight=7.2, h_wall=1.35, alpha=0, phi=40, beta=90, delta=20,
                kh=0.30, kv=0.0, cohesion=5.0)
s = out["summary"]
check("full-height crack -> Pae == 0", s["Pae"] == 0.0, f"Pae={s['Pae']}")
check("full-height crack -> z_bar <= H", s["z_bar"] <= 1.35 + 1e-9,
      f"z_bar={s['z_bar']:.3f}")

# 7c. z_bar bounded when Pae < Pa (large kv)
out = calculate(soil_weight=18, h_wall=1.35, alpha=-10, phi=15, beta=45, delta=0,
                kh=0.0, kv=0.99, cohesion=0.0)
s = out["summary"]
check("large kv -> z_bar bounded", s["z_bar"] <= 0.6 * 1.35 + 1e-9,
      f"z_bar={s['z_bar']:.3f}")

# 7d. Crash classes -> clean ValueError (route renders these as banners)
expect_value_error("phi <= alpha -> ValueError", soil_weight=18, h_wall=1.35,
                   alpha=25, phi=15, beta=45, delta=0, kh=0, kv=0, cohesion=0)
expect_value_error("delta == beta -> ValueError", soil_weight=18, h_wall=1.35,
                   alpha=-10, phi=40, beta=45, delta=45, kh=0, kv=-0.2, cohesion=0)
expect_value_error("beta-delta-theta <= 0 -> ValueError", soil_weight=18,
                   h_wall=1.35, alpha=-10, phi=20, beta=45, delta=20, kh=0.5,
                   kv=0, cohesion=0)
expect_value_error("beta-delta-theta == 0 at clamp -> ValueError", soil_weight=18,
                   h_wall=1.35, alpha=-10, phi=15, beta=45, delta=20, kh=0.5,
                   kv=0, cohesion=0)
expect_value_error("kv >= 1 -> ValueError", soil_weight=18, h_wall=5, alpha=0,
                   phi=35, beta=90, delta=17, kh=0.30, kv=1.2, cohesion=0)
expect_value_error("negative-Kae corner -> ValueError", soil_weight=18,
                   h_wall=1.35, alpha=0, phi=45, beta=60, delta=22.5, kh=0.5,
                   kv=0.5, cohesion=0)
expect_value_error("alpha+beta >= 180 -> ValueError", soil_weight=18, h_wall=3,
                   alpha=50, phi=10, beta=135, delta=0, kh=0.2, kv=0, cohesion=0)

# 7e. Silent None paths that must NOT crash
out = calculate(soil_weight=18, h_wall=1.35, alpha=-10, phi=40, beta=110,
                delta=40, kh=0.0, kv=-0.2, cohesion=0.0)  # Kp root_arg == 1
check("Kp degenerate -> report ok, kp None", out["summary"]["kp"] is None)
out = calculate(soil_weight=18, h_wall=1.35, alpha=0, phi=20, beta=135, delta=25,
                kh=0.1, kv=0.5, cohesion=0.0)  # Kpe root_arg == 1
check("Kpe degenerate -> report ok, kpe None", out["summary"]["kpe"] is None)

# 7f. Kpe evaluated at the TRUE theta past the active limit
out = calculate(soil_weight=19, h_wall=6, alpha=15, phi=30, beta=90, delta=15,
                kh=0.35, kv=0.0, cohesion=0.0)
th_true = math.degrees(math.atan2(0.35, 1.0))
kpe_true = mo_kpe(30, 15, 15, 90, th_true)
check("Kpe uses true theta past active limit",
      out["summary"]["kpe"] is not None and abs(out["summary"]["kpe"] - kpe_true) < 1e-12,
      f"{out['summary']['kpe']} vs {kpe_true}")

# 7g. Mini fuzz: no exception other than ValueError; finite JSON output
import itertools
import random
random.seed(7)
n_run = n_ve = 0
bad = []
for _ in range(4000):
    kwargs = dict(
        soil_weight=random.choice([1, 7.2, 18, 24]),
        h_wall=random.choice([0.01, 0.5, 1.35, 5, 15, 30]),
        alpha=random.choice([-10, 0, 5, 15, 25, 34.9]),
        phi=random.choice([15, 20, 30, 40, 45]),
        beta=random.choice([45, 60, 80, 90, 95, 110, 135]),
        delta=random.choice([0, 10, 20, 30, 45, 50]),
        kh=random.choice([0, 0.1, 0.3, 0.5, 0.9]),
        kv=random.choice([-0.2, 0, 0.1, 0.5, 0.99, 1.0, 1.5]),
        cohesion=random.choice([0, 5, 50]),
    )
    n_run += 1
    try:
        out = calculate(**kwargs)
        json.dumps(out)
        s = out["summary"]
        vals = [s["kae"], s["Pae"], s["z_bar"], s["Ph"], s["M_ot"]]
        if any(v is not None and (math.isnan(v) or math.isinf(v)) for v in vals):
            bad.append(("nan/inf", kwargs))
        elif s["kae"] <= 0 or s["Pae"] < 0:
            bad.append(("nonpositive", kwargs))
        elif s["z_bar"] > kwargs["h_wall"] + 1e-9:
            bad.append(("z_bar>H", kwargs))
    except ValueError:
        n_ve += 1
    except Exception as e:  # noqa: BLE001
        bad.append((f"{type(e).__name__}: {e}", kwargs))
check(f"fuzz 4000 cases: no crash/NaN/negative ({n_ve} clean ValueErrors)",
      not bad, str(bad[:3]))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
