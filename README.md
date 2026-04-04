# GeoStructPy

**Geotechnical Engineering Toolkit for Structural Engineers**

[![PyPI version](https://img.shields.io/pypi/v/geostructpy?color=blue&label=PyPI)](https://pypi.org/project/geostructpy/)
[![License](https://img.shields.io/github/license/albertp16/geostructpy)](https://github.com/albertp16/geostructpy/blob/main/LICENSE)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/albertp16/geostructpy/issues)

GeoStructPy is an open-source Python web application and library for geotechnical engineering calculations, built for the APEC Consultancy team. It provides 10 interactive modules covering bearing capacity, earth pressure, pile design, slope analysis, and borehole data processing.

---

## Modules

| Module | Category | Description |
|--------|----------|-------------|
| **Terzaghi** | Foundation | Bearing capacity for strip, square, and circular footings |
| **Meyerhof** | Foundation | Bearing capacity with shape, depth, and inclination factors |
| **Mononobe-Okabe** | Earth Pressure | Seismic active/passive earth pressure for retaining walls |
| **Wall Stability** | Earth Pressure | Retaining wall sliding, overturning, and eccentricity checks |
| **Micropile** | Deep Foundation | Micropile design per NSCP 2015, AISC 14th Ed., ACI 318-14/19 |
| **Bored Pile** | Deep Foundation | Bored pile capacity from rock UCS, RQD, and structural checks |
| **Slope Stability** | Slope | Midas GTS NX material parameters derived from borehole data |
| **SPT & UCS Charts** | Borehole | SPT N-value, N60, and UCS vs. Depth graph maker with JSON import |
| **Borehole Log** | Borehole | AI-powered borehole log digitizer with soil profiles and charts |
| **Theory & Notes** | Reference | Technical background and equations |

For detailed theory, equations, and step-by-step tutorials for each module, see the [Wiki](https://github.com/albertp16/geostructpy/wiki).

---

## Running the App

### Local Development

```sh
cd webapp
pip install -r requirements.txt
python app.py
```

Open [http://localhost:8080](http://localhost:8080).

### Production (Railway)

The `webapp/` directory is Railway-ready with `Procfile`, `requirements.txt`, and `runtime.txt`.

1. Push to GitHub
2. Connect to [Railway](https://railway.app)
3. Set root directory to `webapp/`
4. Railway auto-detects the Procfile and deploys with Gunicorn

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | Enables AI-powered borehole log extraction. Without it, use the free copy-paste method. |
| `PORT` | Auto | Set by Railway/Heroku. Defaults to 8080 locally. |

---

## Project Structure

```
webapp/
  app.py                # Flask routes and form processing
  requirements.txt      # Flask, Gunicorn, Anthropic SDK, python-dotenv
  Procfile              # Railway/Heroku entry point
  runtime.txt           # Python 3.12.8
  calculators/
    terzaghi.py         # Terzaghi bearing capacity
    meyerhof.py         # Meyerhof bearing capacity
    mononobe_okabe.py   # Seismic earth pressure
    stability.py        # Retaining wall stability
    micropile.py        # Micropile design
    bored_pile.py       # Bored pile capacity
    slope_stability.py  # Slope parameters and charts
    spt_depth.py        # SPT/N60/UCS chart generator
    borehole_log.py     # Borehole log processing and AI extraction
  templates/
    base.html           # Shared layout, navbar, APEC disclaimer, print CSS
    index.html          # Dashboard with module cards
    terzaghi.html       # Terzaghi calculator
    meyerhof.html       # Meyerhof calculator
    mononobe_okabe.html # Mononobe-Okabe calculator
    stability.html      # Wall stability analysis
    micropile.html      # Micropile design
    bored_pile.html     # Bored pile design
    slope_stability.html # Slope stability analysis
    spt_ucs.html        # SPT & UCS chart maker
    borehole_log.html   # Borehole log digitizer
    theory.html         # Technical notes
    changelog.html      # Version history
```

## Python Library

Install the core library for use in scripts:

```sh
pip install geostructpy
```

See the [PyPI page](https://pypi.org/project/geostructpy/) for API documentation.

---

## References

- Terzaghi, K. (1943). *Theoretical Soil Mechanics*. Wiley.
- Meyerhof, G.G. (1963). Some recent research on the bearing capacity of foundations. *Canadian Geotechnical Journal*, 1(1), 16-26.
- Das, B., Sivakugan, N. (2017). *Principles of Foundation Engineering* (9th ed.). Cengage.
- Poulos, H. (2017). *Tall Building Foundation Design*. CRC Press.
- Bowles, J.E. (1987). Elastic foundation settlements on sand deposits. *J. Geotech. Eng.*, ASCE.
- Vesic, A.S. (1973). Analysis of ultimate loads of shallow foundations. *J. Soil Mech. Found. Div.*, ASCE.
- Chao, G. (2019). CE75.05 Geotechnical Engineering for Tall Buildings Lecture Notes, AIT, Thailand.

## About the Developer

**Albert Pamonag, M.Eng** | APEC Consultancy
- Professional Master of Structural Design in Tall Buildings (PMTB), Asian Institute of Technology (AIT), Thailand
- Master of Engineering in Civil Engineering (Structural Engineering), De La Salle University - Manila
- Contact: [albertpamonag@gmail.com](mailto:albertpamonag@gmail.com)

## Disclaimer

This tool is intended for use by the APEC Consultancy team for preliminary geotechnical calculations only. The developers assume no liability for design decisions made based on the output of this application. All results must be verified by a qualified geotechnical or structural engineer before use in any project.

## License

See [LICENSE](LICENSE) for details. Contributions and feedback are welcome.
