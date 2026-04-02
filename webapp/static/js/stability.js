/* ============================================================
   Cantilever Retaining Wall Stability Analysis
   Aligned with retaining_wall.ipynb (cantilever_retaining_wall)
   ============================================================ */
const { createApp } = Vue;
const DEG = Math.PI / 180;

createApp({
    data() {
        return {
            p: {
                h1: 1.0,        // height above ground (m)
                h2: 1.0,        // height below ground (m)
                t_stem: 0.20,   // stem thickness (m)
                t_base: 0.30,   // base thickness (m)
                b_base: 1.00,   // total base width (m)
                b_heel: 0.80,   // heel width (m)
                gamma_s: 18,    // soil unit weight (kN/m³)
                phi: 35.2,      // soil friction angle (deg)
                mu: 0.35,       // soil-concrete friction coeff
                q_bearing: 125, // allowable soil bearing (kPa)
                gamma_c: 23.56, // concrete unit weight (kN/m³)
                q: 0            // surcharge (kPa)
            },
            computed: false,
            report: '',
            summary: [],
            allPass: false
        };
    },
    methods: {
        f: (v, d = 2) => v.toFixed(d),

        calculate() {
            const { h1, h2, t_stem, t_base, b_base, b_heel,
                    gamma_s: gs, phi, mu, q_bearing, gamma_c: gc, q } = this.p;

            const totalHeight = h1 + h2;

            // ── Vertical loads (restoring) ──
            const P1 = gc * t_stem * (totalHeight - t_base);           // stem
            const P2 = gc * t_base * b_base;                           // base slab
            const P3 = gs * (totalHeight - t_base) * (b_base - t_stem); // backfill
            let Wt = P1 + P2 + P3;

            const m1 = P1 * (t_stem / 2);
            const m2 = P2 * (b_base / 2);
            const m3 = P3 * (b_base - b_heel / 2);
            let Mr = m1 + m2 + m3;

            // Surcharge on heel
            const P_sur = q * b_heel;
            const m_sur = P_sur * (b_base - b_heel / 2);
            Wt += P_sur;
            Mr += m_sur;

            // ── Lateral loads ──
            const Ka = (1 - Math.sin(phi * DEG)) / (1 + Math.sin(phi * DEG));
            const maxHP = Ka * gs * totalHeight;
            const Pa_soil = 0.5 * Ka * gs * totalHeight * totalHeight;
            const Pa_sur = q * Ka * totalHeight;
            const Pa_total = Pa_soil + Pa_sur;

            const Mo_soil = Pa_soil * (totalHeight / 3);
            const Mo_sur = Pa_sur * (totalHeight / 2);
            const Mo = Mo_soil + Mo_sur;

            // ── Eccentricity & contact pressure ──
            const netMoment = Mr - Mo;
            const ecc = netMoment / Wt;           // distance from toe
            const e_abs = Math.abs(b_base / 2 - ecc); // eccentricity from centre
            const qAvg = Wt / b_base;

            let qmin, qmax, contactCase;
            if (e_abs >= b_base / 2) {
                contactCase = 'Unstable – resultant outside base';
                qmax = Infinity; qmin = 0;
            } else if (e_abs <= b_base / 6) {
                if (e_abs < 0.0001) {
                    contactCase = 'Full Contact: Uniform';
                    qmax = qmin = qAvg;
                } else if (Math.abs(e_abs - b_base / 6) < 0.0001) {
                    contactCase = 'Full Contact: Triangular';
                    qmax = 2 * qAvg; qmin = 0;
                } else {
                    contactCase = 'Full Contact: Trapezoidal';
                    qmax = qAvg * (1 + 6 * e_abs / b_base);
                    qmin = qAvg * (1 - 6 * e_abs / b_base);
                }
            } else {
                contactCase = 'Partial Contact (tension side lifts)';
                qmin = 0;
                const x_bar = b_base / 2 - e_abs;
                qmax = 2 * Wt / (3 * x_bar);
            }

            // ── Factors of safety ──
            const FS_slide = (mu * Wt) / Pa_total;
            const FS_over = Mr / Mo;

            // ── Build report ──
            let r = '';
            r += `<h4>Rankine Active Earth Pressure Coefficient</h4>`;
            r += `\\[ K_a = \\frac{1 - \\sin\\phi}{1 + \\sin\\phi} = ${this.f(Ka, 4)} \\]`;

            r += `<h4>Lateral Loads</h4>`;
            r += `\\[ \\sigma_{a,max} = K_a \\gamma_s H = ${this.f(maxHP)} \\text{ kPa} \\]`;
            r += `\\[ P_{a,soil} = \\tfrac{1}{2} K_a \\gamma_s H^2 = ${this.f(Pa_soil)} \\text{ kN/m} \\]`;
            if (q > 0) r += `\\[ P_{a,surcharge} = q \\cdot K_a \\cdot H = ${this.f(Pa_sur)} \\text{ kN/m} \\]`;
            r += `\\[ P_{a,total} = ${this.f(Pa_total)} \\text{ kN/m} \\]`;

            r += `<h4>Vertical Loads &amp; Restoring Moment</h4>`;
            r += `<table class="data-table"><thead><tr><th>Component</th><th>W (kN/m)</th><th>Arm (m)</th><th>M<sub>R</sub> (kN·m/m)</th></tr></thead><tbody>`;
            const parts = [
                { name: 'P1 – Stem', W: P1, x: t_stem / 2, M: m1 },
                { name: 'P2 – Base slab', W: P2, x: b_base / 2, M: m2 },
                { name: 'P3 – Backfill', W: P3, x: b_base - b_heel / 2, M: m3 }
            ];
            if (q > 0) parts.push({ name: 'Surcharge', W: P_sur, x: b_base - b_heel / 2, M: m_sur });
            for (const p of parts) {
                r += `<tr><td>${p.name}</td><td>${this.f(p.W)}</td><td>${this.f(p.x)}</td><td>${this.f(p.M)}</td></tr>`;
            }
            r += `<tr style="font-weight:bold"><td>Total</td><td>${this.f(Wt)}</td><td></td><td>${this.f(Mr)}</td></tr>`;
            r += `</tbody></table>`;

            r += `<h4>Overturning Moment about Toe</h4>`;
            r += `\\[ M_o = P_{a,soil} \\times \\frac{H}{3}`;
            if (q > 0) r += ` + P_{a,sur} \\times \\frac{H}{2}`;
            r += ` = ${this.f(Mo)} \\text{ kN·m/m} \\]`;

            r += `<h4>Sliding Check</h4>`;
            r += `\\[ FS_{sliding} = \\frac{\\mu \\cdot W}{P_a} = \\frac{${this.f(mu * Wt)}}{${this.f(Pa_total)}} = ${this.f(FS_slide)} \\]`;

            r += `<h4>Overturning Check</h4>`;
            r += `\\[ FS_{overturning} = \\frac{M_R}{M_o} = \\frac{${this.f(Mr)}}{${this.f(Mo)}} = ${this.f(FS_over)} \\]`;

            r += `<h4>Eccentricity &amp; Base Pressure</h4>`;
            r += `\\[ \\bar{x} = \\frac{M_R - M_o}{W} = ${this.f(ecc)} \\text{ m} \\]`;
            r += `\\[ e = \\frac{B}{2} - \\bar{x} = ${this.f(e_abs)} \\text{ m} \\quad (B/6 = ${this.f(b_base / 6)}) \\]`;
            r += `<p><strong>Contact case:</strong> ${contactCase}</p>`;
            r += `\\[ q_{max} = ${this.f(qmax)} \\text{ kPa}, \\quad q_{min} = ${this.f(qmin)} \\text{ kPa} \\]`;

            const bearingOK = qmax <= q_bearing;
            r += `<p><strong>Bearing check:</strong> q<sub>max</sub> = ${this.f(qmax)} kPa `;
            r += bearingOK ? `≤` : `>`;
            r += ` q<sub>all</sub> = ${this.f(q_bearing)} kPa → <span style="color:${bearingOK ? '#27ae60' : '#e74c3c'};font-weight:bold">${bearingOK ? 'PASS' : 'FAIL'}</span></p>`;

            this.report = r;

            // ── Summary table ──
            this.summary = [
                {
                    name: 'Sliding', driving: this.f(Pa_total) + ' kN/m',
                    resisting: this.f(mu * Wt) + ' kN/m',
                    fs: this.f(FS_slide), req: '≥ 1.5', pass: FS_slide >= 1.5
                },
                {
                    name: 'Overturning', driving: this.f(Mo) + ' kN·m/m',
                    resisting: this.f(Mr) + ' kN·m/m',
                    fs: this.f(FS_over), req: '≥ 2.0', pass: FS_over >= 2.0
                },
                {
                    name: 'Eccentricity', driving: 'e = ' + this.f(e_abs) + ' m',
                    resisting: 'B/6 = ' + this.f(b_base / 6) + ' m',
                    fs: this.f(e_abs < 0.001 ? 999 : (b_base / 6) / e_abs),
                    req: 'e ≤ B/6', pass: e_abs <= b_base / 6 + 0.001
                },
                {
                    name: 'Bearing Pressure', driving: this.f(qmax) + ' kPa',
                    resisting: this.f(q_bearing) + ' kPa',
                    fs: this.f(q_bearing / (qmax || 1)),
                    req: 'q_max ≤ q_all', pass: bearingOK
                }
            ];
            this.allPass = this.summary.every(s => s.pass);
            this.computed = true;

            this.$nextTick(() => {
                if (window.MathJax) MathJax.typeset();
                this.plotWall(h1, h2, t_stem, t_base, b_base, P1, P2, P3, Pa_soil, maxHP, totalHeight);
                this.plotPressure(b_base, qmin, qmax, q_bearing, contactCase);
            });
        },

        // ── Plotly: Wall cross-section with dimensions & loads ──
        plotWall(h1, h2, t_stem, t_base, b_base, P1, P2, P3, activeForce, maxHP, H) {
            const y_top = h1;
            const y_gl = 0;
            const y_iface = -(h2 - t_base);
            const y_bot = -h2;
            const span = H;

            // Wall outline (cantilever – no toe extension)
            const wallX = [0, t_stem, t_stem, b_base, b_base, 0, 0, 0];
            const wallY = [y_top, y_top, y_iface, y_iface, y_bot, y_bot, y_gl, y_top];

            // Stem-base interface line
            const ifaceX = [0, t_stem];
            const ifaceY = [y_iface, y_iface];

            const traces = [];

            // Wall outline
            traces.push({
                x: wallX, y: wallY, mode: 'lines',
                line: { color: '#333', width: 2.5 },
                showlegend: false, hoverinfo: 'skip'
            });
            // Interface line
            traces.push({
                x: ifaceX, y: ifaceY, mode: 'lines',
                line: { color: '#333', width: 2 },
                showlegend: false, hoverinfo: 'skip'
            });

            // Dashed ground-level & top lines
            const margin = 0.12 * b_base;
            for (const [yv, label] of [[y_top, 'Upper Level'], [y_gl, 'Ground Level']]) {
                traces.push({
                    x: [-margin, b_base + margin], y: [yv, yv], mode: 'lines',
                    line: { color: '#888', width: 1, dash: 'dash' },
                    showlegend: false, hoverinfo: 'skip'
                });
            }

            // Backfill hatching (light fill)
            traces.push({
                x: [t_stem, b_base, b_base, t_stem],
                y: [y_top, y_top, y_iface, y_iface],
                fill: 'toself', fillcolor: 'rgba(194,178,128,0.25)',
                line: { color: 'rgba(194,178,128,0.5)', width: 1 },
                showlegend: false, hoverinfo: 'skip'
            });

            // Concrete fill
            traces.push({
                x: [0, t_stem, t_stem, 0],
                y: [y_top, y_top, y_iface, y_iface],
                fill: 'toself', fillcolor: 'rgba(180,180,180,0.3)',
                line: { width: 0 },
                showlegend: false, hoverinfo: 'skip'
            });
            traces.push({
                x: [0, b_base, b_base, 0],
                y: [y_iface, y_iface, y_bot, y_bot],
                fill: 'toself', fillcolor: 'rgba(180,180,180,0.3)',
                line: { width: 0 },
                showlegend: false, hoverinfo: 'skip'
            });

            // Annotations for dimensions and loads
            const ann = [];
            const dark = '#006400';

            // h1 dimension
            ann.push({
                x: -margin * 0.6, y: (y_top + y_gl) / 2,
                text: `h₁ = ${h1.toFixed(2)} m`, showarrow: false,
                font: { size: 11, color: '#333' }, xanchor: 'right'
            });
            // h2 dimension
            ann.push({
                x: -margin * 0.6, y: (y_gl + y_bot) / 2,
                text: `h₂ = ${h2.toFixed(2)} m`, showarrow: false,
                font: { size: 11, color: '#333' }, xanchor: 'right'
            });
            // t_stem
            ann.push({
                x: t_stem / 2, y: y_top + 0.06 * span,
                text: `t<sub>stem</sub> = ${t_stem.toFixed(2)} m`, showarrow: false,
                font: { size: 10, color: '#333' }
            });
            // b_base
            ann.push({
                x: b_base / 2, y: y_bot - 0.08 * span,
                text: `b<sub>base</sub> = ${b_base.toFixed(2)} m`, showarrow: false,
                font: { size: 11, color: '#333' }
            });
            // t_base
            ann.push({
                x: b_base + margin * 0.5, y: (y_iface + y_bot) / 2,
                text: `t<sub>base</sub> = ${t_base.toFixed(2)} m`, showarrow: false,
                font: { size: 10, color: '#333' }, xanchor: 'left'
            });

            // P1, P2, P3 load arrows
            const arrowLen = 0.22 * span;
            const loads = [
                { label: 'P1', val: P1, x: t_stem / 2, y: (y_top + y_bot) / 2 },
                { label: 'P2', val: P2, x: b_base / 2, y: (y_iface + y_bot) / 2 },
                { label: 'P3', val: P3, x: (t_stem + b_base) / 2, y: (y_top + y_iface) / 2 }
            ];
            for (const ld of loads) {
                ann.push({
                    x: ld.x, y: ld.y,
                    ax: ld.x, ay: ld.y + arrowLen,
                    xref: 'x', yref: 'y', axref: 'x', ayref: 'y',
                    showarrow: true,
                    arrowhead: 2, arrowsize: 1.2, arrowwidth: 2.5, arrowcolor: dark
                });
                ann.push({
                    x: ld.x, y: ld.y + arrowLen + 0.03 * span,
                    text: `<b>${ld.label} = ${ld.val.toFixed(2)}</b>`, showarrow: false,
                    font: { size: 10, color: dark }
                });
            }

            // Pressure triangle on the right side
            const triBaseW = 0.35 * span;
            const triX0 = b_base + margin * 1.5;

            // Triangle outline
            traces.push({
                x: [triX0, triX0, triX0 + triBaseW],
                y: [y_top, y_bot, y_bot],
                mode: 'lines', fill: 'toself',
                fillcolor: 'rgba(0,100,0,0.08)',
                line: { color: dark, width: 1.5 },
                showlegend: false, hoverinfo: 'skip'
            });

            // Pressure arrows at fractions
            for (const frac of [0.2, 0.4, 0.6, 0.8, 1.0]) {
                const yi = y_top - frac * span;
                const xi = triBaseW * frac;
                traces.push({
                    x: [triX0 + xi, triX0], y: [yi, yi], mode: 'lines',
                    line: { color: dark, width: frac === 1.0 ? 2.5 : 1 },
                    showlegend: false, hoverinfo: 'skip'
                });
            }

            // Active force arrow at H/3
            const yH3 = y_bot + span / 3;
            const xH3 = triBaseW * (1 - 1 / 3);
            ann.push({
                x: triX0, y: yH3,
                ax: triX0 + xH3, ay: yH3,
                xref: 'x', yref: 'y', axref: 'x', ayref: 'y',
                showarrow: true,
                arrowhead: 2, arrowsize: 1.5, arrowwidth: 3, arrowcolor: dark
            });
            ann.push({
                x: triX0 + xH3 + 0.02 * span, y: yH3 + 0.03 * span,
                text: `<b>Pa = ${activeForce.toFixed(2)}</b>`, showarrow: false,
                font: { size: 10, color: dark }, xanchor: 'left'
            });
            // Max horizontal pressure label
            ann.push({
                x: triX0 + triBaseW / 2, y: y_bot - 0.06 * span,
                text: `K<sub>a</sub>γ<sub>s</sub>H = ${maxHP.toFixed(2)} kPa`, showarrow: false,
                font: { size: 10, color: dark }
            });
            // h/3 label
            ann.push({
                x: triX0 + triBaseW + 0.08 * span, y: (y_bot + yH3) / 2,
                text: `H/3 = ${(span / 3).toFixed(2)} m`, showarrow: false,
                font: { size: 10, color: '#333' }, xanchor: 'left'
            });

            const layout = {
                xaxis: { visible: false, scaleanchor: 'y' },
                yaxis: { visible: false },
                margin: { l: 10, r: 10, t: 30, b: 30 },
                height: 420,
                plot_bgcolor: 'white', paper_bgcolor: 'white',
                annotations: ann,
                title: { text: 'Wall Cross-Section & Lateral Pressure', font: { size: 14 } }
            };

            Plotly.newPlot('wall-plot', traces, layout, { responsive: true, displayModeBar: false });
        },

        // ── Plotly: Base pressure distribution ──
        plotPressure(B, qmin, qmax, qall, contactCase) {
            const traces = [];

            // Base line
            traces.push({
                x: [0, B], y: [0, 0], mode: 'lines',
                line: { color: '#333', width: 2 },
                showlegend: false, hoverinfo: 'skip'
            });

            if (qmin >= 0 && isFinite(qmax)) {
                // Trapezoidal / uniform / triangular
                traces.push({
                    x: [0, B, B, 0],
                    y: [0, 0, -qmax, -qmin],
                    fill: 'toself', fillcolor: 'rgba(41,128,185,0.2)',
                    line: { color: '#2980b9', width: 2 },
                    name: 'Base pressure', showlegend: false
                });

                // Labels
                traces.push({
                    x: [0], y: [-qmin], mode: 'markers+text',
                    marker: { size: 6, color: '#2980b9' },
                    text: [`q<sub>min</sub> = ${qmin.toFixed(1)} kPa`],
                    textposition: 'bottom left', showlegend: false
                });
                traces.push({
                    x: [B], y: [-qmax], mode: 'markers+text',
                    marker: { size: 6, color: '#e74c3c' },
                    text: [`q<sub>max</sub> = ${qmax.toFixed(1)} kPa`],
                    textposition: 'bottom right', showlegend: false
                });
            }

            // Allowable bearing line
            if (isFinite(qall)) {
                traces.push({
                    x: [-0.05 * B, B * 1.05], y: [-qall, -qall], mode: 'lines',
                    line: { color: '#e74c3c', width: 1.5, dash: 'dash' },
                    name: 'q_all', showlegend: false
                });
            }

            const ann = [
                {
                    x: B * 1.06, y: -qall,
                    text: `q<sub>all</sub> = ${qall.toFixed(0)} kPa`,
                    showarrow: false, font: { size: 10, color: '#e74c3c' }, xanchor: 'left'
                },
                {
                    x: B / 2, y: Math.min(-qmax * 1.1, -qall * 1.1) - 5,
                    text: `<i>${contactCase}</i>`,
                    showarrow: false, font: { size: 10, color: '#555' }
                }
            ];

            const layout = {
                xaxis: { title: 'Base width (m)', zeroline: false },
                yaxis: { title: 'Pressure (kPa, downward negative)', zeroline: true },
                margin: { l: 60, r: 20, t: 30, b: 50 },
                height: 420,
                plot_bgcolor: 'white', paper_bgcolor: 'white',
                annotations: ann,
                title: { text: 'Base Pressure Distribution', font: { size: 14 } }
            };

            Plotly.newPlot('pressure-plot', traces, layout, { responsive: true, displayModeBar: false });
        }
    }
}).mount('#app');
