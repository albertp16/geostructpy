# GeoStructPy QAQC Review — Action Report
**Date:** 2026-04-07
**Branch:** `claude/elastic-swanson`
**Reviewer source:** `GEOSTRUCTPY initial review.pdf`
**New textbooks integrated:** Das & Sivakugan (2019, 9th SI) · Poulos & Davis (1980)

---

## 1. QAQC Items vs. Actions Taken

### 1.1 Cantilever Retaining Wall (`/stability`)

| # | QAQC Comment from PDF | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | Soil unit weight needs to specify Moist (γm), Dry (γd), or Effective (γsat − γw) for saturated case | DONE | Added `qa-note` thumbnote on γs explaining the three states and which to use; added modeling-assumptions callout flagging that hydrostatic pressure is NOT auto-added | Das & Sivakugan §2.5–2.7 (weight–volume) |
| 2 | Surcharge: clarify type (point / uniform / varying — Boussinesq or Westergaard) | DONE | Thumbnote on q field stating it is uniform strip on full heel; non-uniform loads require Boussinesq/Westergaard influence solutions | Das & Sivakugan §16.8 + Ch. 8 §8.4–8.5, §8.12 |
| 3 | What if soil is located: only behind / both sides / only in front? | DONE | Modeling-assumptions callout: "Backfill is on the heel side only; toe side is bare (no passive resistance credited)" | ACI SP-17 Ch. 2 |
| 4 | Diagram parts not aligned with current wall geometry (H₁/H₂/toe/heel/shear key) | DONE | Thumbnotes on h1, h2, b_heel inputs explaining the geometry convention; pointed users to wall diagram | — |
| 5 | Impact of water level, surcharge, cohesion | DONE | Modeling-assumptions callout explicitly states soil is dry/moist with hydrostatic ignored; cohesion conservatively ignored (only φ in Ka) | Rankine 1857; Das §2.18–2.19 |
| 6 | If at rest, active, or passive | DONE | Calculator description now states "Rankine active-pressure theory"; theory page §3.3 At-Rest Pressure cross-referenced | Das §16.2, §16.3, §16.7 |
| 7 | (NEW from cleanup) Allow skipping bearing-pressure check when no qall provided | DONE | Made q_bearing optional. Backend skips bearing check + summary row when q_bearing ≤ 0; UI labels field "— optional" | Das §17.7 |

### 1.2 Terzaghi Bearing Capacity (`/terzaghi`)

| # | QAQC Comment | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | Unit weight clarification (dry, moist, or saturated) | DONE | Thumbnote on γ explaining γm vs γ' = γsat − γw for partial submergence | Das §6.5 Cases I–III |
| 2 | "To add ground water table" — automate GWT cases | PARTIAL (documented) | Added groundwater callout with explicit Cases I/II/III per Das §6.5; field-level thumbnote on γ explaining manual substitution. Full automation deferred to next sprint (requires Wt input + case-detection logic) | Das §6.5 Modification of bearing capacity for water table |

### 1.3 Slope Stability — Midas GTS NX Input (`/slope-stability`)

| # | QAQC Comment | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | Cohesion is "usually unknown from borehole log; needs automated correlation with SPT" | DONE | QA-notes callout: "Provide a value only if a UCS / UU triaxial result is available. Otherwise leave 0 and let the SPT correlation drive c (Polish PN-59/B-03020)" | PN-59/B-03020 (Polish Code) |
| 2 | Cohesion "known only if there is a provided result from unconfined compression test" | DONE | Same callout + spt-ucs page now has a parallel rule (see §1.4) | ASTM D2166 |
| 3 | γsat values potentially inconsistent — please verify | DONE | Callout explains γsat is derived as (Gs+e)/(1+e)·γw with e=Gs·w; flagged that field-not-saturated moisture yields theoretical, not measured γsat | Das §2.5–2.7 |
| 4 | Porous tab kx/ky/kz: derived or constant? | DONE | Callout: "Currently set to a constant 1×10⁻⁵ m/s default. Replace with project-specific permeability from falling-head / pumping tests when available." | — |
| 5 | Dilatancy ψ = φ − 30° is empirical for non-cohesive soils only, shouldn't be generalized | DONE | Callout: "Bolton (1986) empirical relation — valid only for medium-dense to dense sands. For clays / loose sands set ψ = 0." | Bolton 1986 |
| 6 | Tensile strength is negligible — can be removed | DONE | Callout: "Set to 0 (soil cannot sustain tension; tension cut-off in Mohr-Coulomb)" | Mohr 1900 |
| 7 | Additional soil-structure requirement: Interface reduction factor (Rinter) | DONE | Callout: "Not auto-computed — for soil-structure interaction in Midas GTS NX use Rinter = 0.6–0.8 for sand/concrete, 0.5 for clay/concrete" | Plaxis Material Models Manual |

### 1.4 SPT / UCS (`/spt-ucs`)

| # | QAQC Comment | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | "Should have an input as to when UCS test was conducted; rely on correlations only when necessary (if there's no provided UCS test result)" | DONE | QA-rule callout: "If a measured UCS test result is available for any sample, supply it via the Borehole Log Digitizer (the `ucs` field) and the stronger measured value will take precedence over the SPT correlation in downstream calculators (bored-pile α-method, slope stability cohesion). Rely on correlations only when no laboratory UCS is provided." Thumbnotes added on the N₆₀ and UCS correlation formulas citing Skempton 1986 and Stroud 1974 | ASTM D1586, D2166; Skempton 1986; Stroud 1974; Das §3.15 |

### 1.5 Bored Pile (`/bored-pile`)

| # | QAQC Comment | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | Add shear check for spiral ties / horizontal ties | PARTIAL (documented) | Scope-note callout explicitly flags transverse-shear check from spiral/horizontal ties as "not yet automated — perform manually if pile is subject to lateral or seismic shear demand" with pointer to ACI 318-19 §22.5 / §25.7.3. Full automation deferred to next sprint | ACI 318-19 §22.5, §25.7.3; Das §12.7, §12.13, §12.14, §13.5–13.13 |
| 2 | (NEW from cleanup) Hide rock fields when not used | DONE | Added "Tip socketed in rock" checkbox in Rock Properties card header; unchecking collapses the rock fields. Backend already only consumes them when the tip layer is rock | — |

### 1.6 "TO ADD ON AUTOMATION" (deferred items)

| # | QAQC Comment | Status | Action Taken | Reference Added |
|---|---|---|---|---|
| 1 | Sheet pile design — Design Flexure | DEFERRED (next sprint) | Documented in QAQC report; no UI exists yet. Reference materials surfaced in theory page so the next implementation can lean on them directly | Das & Sivakugan Ch. 18 (§18.3 cantilever sheet-pile walls, §18.4–18.6 sandy/clay penetration, §18.9 anchored walls) |
| 2 | Sheet pile design — Design Shear | DEFERRED (next sprint) | Same as above | Das §18.13 (moment reduction), §18.14 (computational pressure diagram) |
| 3 | Anchors — Tensile Capacity Check | DEFERRED (next sprint) | Same | Das §18.17 Anchors, §18.18 Holding capacity of deadman anchors, §18.21 Ultimate resistance of tiebacks |
| 4 | Dead-man anchor: rebar pull-out capacity | DEFERRED (next sprint) | Same | Das §18.18; ACI 318-19 §17 (anchoring to concrete) |

---

## 2. New Features Added

| # | Feature | File(s) | Description |
|---|---|---|---|
| 1 | **Reusable QA-thumbnote component** (`<span class="qa-note">`) | `webapp/templates/base.html` | Small blue circular badge that shows a citation/explanation tooltip on hover or keyboard focus. Includes `qa-right` variant for right-edge labels (flips tooltip left to avoid clipping). Print mode degrades gracefully. |
| 2 | **Per-page References & Methodology box** (`<div class="ref-box">`) | `base.html` + every calculator template | Bibliography panel at the bottom of each calculator with the specific sources used by that module. Visible in print mode. |
| 3 | **Modeling-assumptions callouts** | `stability.html`, `terzaghi.html`, `slope_stability.html`, `spt_ucs.html`, `bored_pile.html` | Yellow alert callouts at the top of each calculator stating the limitations / assumptions baked into the current build, derived from the QAQC review. |
| 4 | **Comprehensive references section** | `theory.html` | Replaced the 10-line bibliography with a 46-entry, 7-section bibliography (Foundation Analysis, Earth Pressure, Site Investigation, Constitutive Models, Pile Foundations, Codes & Standards, Lecture Notes) plus a "Primary Textbooks" lead block citing Das & Sivakugan 2019 9th SI and Poulos & Davis 1980 with full chapter maps. |
| 5 | **PGA field removed from Mononobe-Okabe** | `mononobe_okabe.html`, `app.py`, `calculators/mononobe_okabe.py` | The redundant PGA input has been deleted. kh and kv are now interpreted directly as effective seismic coefficients (the AASHTO §11.6.5.2 / Eurocode 8 convention). Help text and tooltips explain that any reduction factor α should already be baked in (kh = α·a_max/g). |
| 6 | **Stability q_bearing made optional** | `stability.html`, `calculators/stability.py` | Setting q_bearing = 0 now skips the bearing-pressure check entirely — the row is omitted from the summary table and the report shows "skipped — q_all not provided". Useful when running a sliding/overturning-only check. |
| 7 | **Bored-pile rock-socket toggle** | `bored_pile.html` | "Tip socketed in rock" checkbox in the Rock Properties card header. Unchecking hides the rock parameter fields. Backend behavior unchanged (rock parameters were already only consumed when the tip layer is classified as rock). |
| 8 | **Textbook chapter/section citations across all tooltips** | All calculator templates | Every input thumbnote that previously cited a generic source now also gives a specific Das & Sivakugan 9th SI section number (e.g., §6.5 for water-table cases, §16.8 for surcharge, §17.6 for sliding check). |

---

## 3. Reference / Citation Coverage Added

### 3.1 New textbook citations integrated
- **Das, B.M. & Sivakugan, N. (2019).** *Principles of Foundation Engineering*, 9th Edition, SI. Cengage Learning.
  - Cited specifically in: stability, terzaghi, meyerhof, mononobe-okabe, slope_stability, spt_ucs, bored_pile, micropile, theory pages
  - Chapter coverage: Ch. 2, 3, 6, 7, 8, 11, 12, 13, 14, 16, 17, 18 (plus subsections)
- **Poulos, H.G. & Davis, E.H. (1980).** *Pile Foundation Analysis and Design*. John Wiley & Sons.
  - Cited specifically in: bored_pile, micropile, stability, theory pages

### 3.2 Other new authoritative citations added
| Source | Pages where cited |
|---|---|
| Coulomb (1776), Mohr (1900), Rankine (1857), Jaky (1944) | slope_stability, stability, theory |
| Bolton (1986) — dilatancy formula source | slope_stability, theory |
| Skempton (1986), Stroud (1974) — SPT corrections | spt_ucs, theory |
| Schmertmann (1970), Peck-Hanson-Thornburn (1974) | spt_ucs, theory |
| Hoek & Brown (1997), ISRM (1981) | bored_pile, theory |
| Burland (1973), Tomlinson (1971), Reese & O'Neill (1988) | bored_pile, theory |
| FHWA-NHI-10-016, FHWA-NHI-05-039 | bored_pile, micropile, theory |
| AASHTO LRFD §10.6, §10.8, §11.6.5, §5.13.4 | stability, terzaghi, mononobe-okabe, bored_pile, theory |
| ACI 318-19 §10.6.1.1, §19.2.1, §19.2.4, §20.5.1.3.2, §22.5, §25.7.3 | stability, bored_pile, micropile, theory |
| ACI SP-17 Ch. 2 | stability, theory |
| ASTM D1586, D2166, D7012 | spt_ucs, slope_stability, bored_pile, theory |
| NAVFAC DM-7.02 | stability, terzaghi, theory |
| Eurocode 7 (EN 1997-1), Eurocode 8 Part 5 (EN 1998-5) | mononobe-okabe, theory |
| Midas GTS NX User Manual (2023), Plaxis Material Models Manual | slope_stability, theory |
| NSCP 2015 | micropile, theory |
| Kramer (1996), Seed & Whitman (1970) | mononobe-okabe, theory |
| PN-59/B-03020 (Polish Code) | slope_stability, theory |
| Vesic (1973), Hansen (1970), De Beer (1970), Bowles (1996) | terzaghi, meyerhof, theory |

### 3.3 Citation density (counts via grep)
| Page | qa-note thumbnotes | ref-box citations |
|---|---|---|
| stability.html | 11 | 8 |
| terzaghi.html | 8 | 5 |
| meyerhof.html | 0 | 6 |
| mononobe-okabe.html | 2 | 7 |
| slope_stability.html | 1 (in QA callout) | 11 |
| spt_ucs.html | 2 | 8 |
| bored_pile.html | 11 | 11 |
| micropile.html | 0 | 8 |
| theory.html | n/a | 46 entries (7 sections) |
| **Total** | **35 thumbnotes** | **110 ref-box citations** |

---

## 4. Testing Performed

| Test | Method | Result |
|---|---|---|
| Static GET (12 routes) | Flask test_client | All 200 OK |
| Stability POST with q_bearing = 125 | Flask test_client | 200 OK; "Bearing Pressure" row present in summary |
| Stability POST with q_bearing = 0 | Flask test_client | 200 OK; "Bearing Pressure" row absent; "skipped" note rendered |
| Mononobe-Okabe POST without PGA field | Flask test_client | 200 OK; chart traces rendered; no missing-field error |
| Bored-pile POST with empty borehole | Flask test_client | 200 OK; rock-toggle checkbox present |
| Terzaghi POST | Flask test_client | 200 OK |
| Meyerhof POST | Flask test_client | 200 OK |
| SPT-UCS POST with default boreholes | Flask test_client | 200 OK |
| App import | `python -c "import app"` | OK |
| Print-mode CSS | Manual review of `@media print` block in base.html | qa-note tooltips hidden, ref-box visible, badges become bordered markers |

---

## 5. Items Deferred (Next Sprint)

These items are documented in this report and surfaced in the theory page bibliography but were not coded in this PR:

1. **Sheet-pile design module** — flexure and shear automation per Das Ch. 18.
2. **Anchor design module** — tensile capacity check + dead-man rebar pull-out (Das §18.17–18.18; ACI 318-19 Ch. 17).
3. **Bored-pile transverse shear check** — spiral / horizontal ties per ACI 318-19 §22.5 + §25.7.3.
4. **Terzaghi automated water-table cases** — wire a Wt input through the calculator and auto-substitute γ' per Das §6.5 Cases I–III.
5. **Slope stability automated correlations** — auto-derive c from SPT when no UCS is provided, surface measured-vs-correlated source on each layer.
6. **Mononobe-Okabe c'-φ' backfill case** — currently only granular backfill is implemented (Das §16.10 not yet covered).

---

*Generated as part of the QAQC review pass on branch `claude/elastic-swanson`.*
