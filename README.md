# GeoStructPy

**Geotechnical Engineering Toolkit for Structural Engineers**

[![PyPI version](https://img.shields.io/pypi/v/geostructpy?color=blue&label=PyPI)](https://pypi.org/project/geostructpy/)
[![License](https://img.shields.io/github/license/albertpamonag/geostructpy)](https://github.com/albertpamonag/geostructpy/blob/main/LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/albertpamonag/geostructpy/issues)

GeoStructPy is an open-source Python library and web application for geotechnical engineering calculations, designed for practicing structural and geotechnical engineers. It provides interactive tools for bearing capacity analysis, seismic earth pressure calculations, and retaining wall stability checks.

## Web Application

A lightweight Flask-based web app with interactive calculators, step-by-step equation rendering (MathJax), and printable reports.

### Modules

| Module | Description | Method |
|--------|-------------|--------|
| **Terzaghi** | Ultimate bearing capacity for strip, square, and circular footings | Terzaghi (1943) |
| **Meyerhof** | Bearing capacity with shape, depth, and load inclination factors | Meyerhof (1963) |
| **Mononobe-Okabe** | Seismic active/passive earth pressure coefficients | Mononobe-Okabe (1929) |
| **Wall Stability** | Retaining wall sliding, overturning, and eccentricity checks | Rankine earth pressure |
| **Micropile** | Micropile design with slenderness, soil capacity, lateral, flexural/axial, and shear checks | NSCP 2015, AISC 14th Ed., ACI 318-14/19 |
| **Theory & Notes** | Technical background on all implemented methods | AIT CE75.05 lecture notes |

### How to Run the App

**Option 1 - Run locally (development):**

```sh
cd webapp
pip install -r requirements.txt
python app.py
```

Then open [http://localhost:8080](http://localhost:8080) in your browser. All calculators are client-side (Vue.js + MathJax + Plotly), so Flask only serves the pages.

**Option 2 - Deploy to Railway (production):**

The `webapp/` directory is Railway-ready with `Procfile`, `requirements.txt`, and `runtime.txt`.

1. Push your code to GitHub
2. Connect the repository to [Railway](https://railway.app)
3. Set the **root directory** to `webapp/`
4. Railway auto-detects the `Procfile` and deploys with Gunicorn

**Option 3 - Deploy with Docker (optional):**

```sh
cd webapp
pip install gunicorn
gunicorn app:app --bind 0.0.0.0:8080
```

### Project Structure

```
webapp/
  app.py              # Flask routes (lightweight, serves templates only)
  requirements.txt    # Flask + Gunicorn
  Procfile            # Railway/Heroku entry point
  runtime.txt         # Python version for Railway
  templates/
    base.html         # Shared layout, nav, disclaimer, print CSS
    index.html        # Landing page with module cards
    terzaghi.html     # Terzaghi bearing capacity calculator
    meyerhof.html     # Meyerhof bearing capacity calculator
    mononobe_okabe.html  # Seismic earth pressure calculator
    stability.html    # Retaining wall stability analysis
    micropile.html    # Micropile design (NSCP/AISC/ACI)
    theory.html       # Technical notes & equations
    changelog.html    # Version history
  static/js/
    terzaghi.js       # Terzaghi calculation engine
    meyerhof.js       # Meyerhof calculation engine
    mononobe_okabe.js # Mononobe-Okabe calculation engine
    stability.js      # Retaining wall stability engine
    micropile.js      # Micropile design engine
```

## Python Library

Install the core library:

```sh
pip install geostructpy
```

### Features

**Shallow Foundation Design**
- Terzaghi (1943) bearing capacity equation with shape factors
- Meyerhof (1963) bearing capacity equation with shape, depth, and inclination factors
- Bearing capacity factor tables and interpolation (phi = 0-50 deg)
- Support for strip, square, rectangular, and circular footings
- Drained and undrained analysis

**Seismic Earth Pressure**
- Mononobe-Okabe method for seismic active earth pressure
- Coulomb static active and passive pressure coefficients
- At-rest earth pressure coefficient (K0)
- Seismic inclination angle computation

**Retaining Wall Stability**
- Rankine active and passive earth pressure
- Sliding safety factor (FS >= 1.5)
- Overturning safety factor (FS >= 2.0)
- Eccentricity and base pressure distribution

**Serviceability Limit State** *(Under Development)*
- Immediate settlement (Bowles, 1987)
- Primary consolidation settlement
- Secondary consolidation settlement

**Micropile Design**
- Slenderness check per AISC 14th Ed. E2/D1 (KL/r < 200)
- Soil compression and tension capacity per ACI 318-14/19
- Lateral soil capacity and required embedment depth per NSCP 2015
- Concrete flexural and axial capacity with P-M interaction diagram (ACI 318-14 Sec. 21.2)
- Concrete shear capacity per ACI 318-14/19 Sec. 22.5
- Metric rebar library (10 mm through 40 mm) with LRFD load combinations

**Deep Foundations** *(Under Development)*
- Pile foundation design
- Pile raft foundation

## Technical Background

The calculations are aligned with:

- **Terzaghi (1943)**: General shear failure theory for shallow foundations assuming homogeneous isotropic soil with horizontal ground surface. Applicable to strip, square, and circular footings with shape factors.

- **Meyerhof (1963)**: Extended bearing capacity theory incorporating shape factors (De Beer, 1970), depth factors (Hansen, 1970), and load inclination factors for rectangular foundations and inclined loads.

- **Mononobe-Okabe (1929)**: Pseudo-static extension of Coulomb's earth pressure theory for seismic conditions using horizontal (kh) and vertical (kv) seismic coefficients.

- **Limit State Design**: Both Ultimate Limit State (bearing capacity failure, sliding, overturning) and Serviceability Limit State (settlement, angular distortion) approaches following LRFD methodology.

## References

- Terzaghi, K. (1943). *Theoretical Soil Mechanics*. Wiley.
- Meyerhof, G.G. (1963). Some recent research on the bearing capacity of foundations. *Canadian Geotechnical Journal*, 1(1), 16-26.
- Das, B., Sivakugan, N. (2017). *Principles of Foundation Engineering* (9th ed.). Cengage.
- Poulos, H. (2017). *Tall Building Foundation Design*. CRC Press.
- Bowles, J.E. (1987). Elastic foundation settlements on sand deposits. *J. Geotech. Eng.*, ASCE.
- Vesic, A.S. (1973). Analysis of ultimate loads of shallow foundations. *J. Soil Mech. Found. Div.*, ASCE.
- Chao, G. (2019). CE75.05 Geotechnical Engineering for Tall Buildings Lecture Notes, AIT, Thailand.

## About the Developer

**Albert Pamonag, M.Eng**
- Professional Master of Structural Design in Tall Buildings (PMTB), Asian Institute of Technology (AIT), Thailand
- Master of Engineering in Civil Engineering (Structural Engineering), De La Salle University - Manila
- Contact: [albertpamonag@gmail.com](mailto:albertpamonag@gmail.com)

## Disclaimer

This tool is intended for use by the APEC Consultancy team for preliminary geotechnical calculations only. The developers assume no liability for design decisions made based on the output of this application. All results must be verified by a qualified geotechnical or structural engineer before use in any project.

## License

See [LICENSE](LICENSE) for details. Contributions and feedback are welcome.
