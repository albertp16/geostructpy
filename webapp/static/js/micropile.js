const { createApp } = Vue;

createApp({
    data() {
        return {
            barSizes: [10, 12, 16, 20, 25, 28, 32, 36, 40],
            p: {
                D: 200, db: 25, nbar: 1, fy: 415, fc: 30, cc: 45,
                restrained: 0, Qa: 7000, Fa: 24, Pp: 17, H: 0.91, d: 9.14
            },
            loadCombos: [
                { label: '1.2D + 1.6L',             Pu: 535, Vu: 1, Mu: 0 },
                { label: '1.2D + 1.0L + 1.0E',      Pu: 480, Vu: 5, Mu: 2 },
                { label: '0.9D + 1.0E',             Pu: 320, Vu: 5, Mu: 2 },
                { label: '1.2D + 1.6L + 0.5S',      Pu: 535, Vu: 1, Mu: 0 }
            ],
            computed: false,
            summaryReport: '', slendernessReport: '', soilReport: '',
            lateralReport: '', flexuralReport: '', shearReport: '',
            summaryTable: [], allPass: false
        };
    },
    computed: {
        gov() {
            let Pu = 0, Vu = 0, Mu = 0;
            for (const lc of this.loadCombos) {
                if (Math.abs(lc.Pu) > Math.abs(Pu)) Pu = lc.Pu;
                if (Math.abs(lc.Vu) > Math.abs(Vu)) Vu = lc.Vu;
                if (Math.abs(lc.Mu) > Math.abs(Mu)) Mu = lc.Mu;
            }
            return { Pu, Vu, Mu };
        },
        govIdx() {
            let max = 0, idx = 0;
            this.loadCombos.forEach((lc, i) => {
                const v = Math.abs(lc.Pu) + Math.abs(lc.Vu)*10 + Math.abs(lc.Mu)*10;
                if (v > max) { max = v; idx = i; }
            });
            return idx;
        }
    },
    methods: {
        f(v, d=2) { return Number(v).toFixed(d); },
        addLc() { this.loadCombos.push({ label: 'New Combination', Pu: 0, Vu: 0, Mu: 0 }); },
        removeLc(i) { if (this.loadCombos.length > 1) this.loadCombos.splice(i, 1); },

        calculate() {
            const p = this.p;
            const D = p.D;           // mm
            const D_m = D / 1000;    // m
            const R = D / 2;         // mm
            const db = p.db;         // mm
            const Ab = Math.PI * db * db / 4 * p.nbar; // mm²
            const Ag = Math.PI * D * D / 4;  // mm²
            const cc = p.cc;
            const fc = p.fc;         // MPa
            const fy = p.fy;         // MPa
            const Es = 200000;       // MPa
            const ecu = 0.003;
            const ey = fy / Es;

            // Tie diameter
            const tie = db <= 32 ? 10 : 12;
            const dprime = cc + tie + db / 2;  // mm (from compression face to bar center)
            const deff = D - dprime;            // mm (effective depth)

            // Beta1 per ACI 318-14/19
            let beta1;
            if (fc <= 28) beta1 = 0.85;
            else beta1 = Math.max(0.85 - 0.05 * (fc - 28) / 7, 0.65);

            // Ec
            const Ec = 4700 * Math.sqrt(fc); // MPa

            // Governing loads from LRFD table
            const Pu = this.gov.Pu;  // kN
            const Vu = this.gov.Vu;  // kN
            const Mu = this.gov.Mu;  // kN-m

            // ===== SUMMARY =====
            let sum = `<table class="data-table" style="max-width:550px;">`;
            sum += `<tr><td style="text-align:left">Section Diameter, D</td><td>${D} mm</td></tr>`;
            sum += `<tr><td style="text-align:left">Center Bar</td><td>${p.nbar} - ${db} mm (A<sub>s</sub> = ${this.f(Ab,0)} mm&sup2;)</td></tr>`;
            sum += `<tr><td style="text-align:left">f<sub>y</sub></td><td>${fy} MPa</td></tr>`;
            sum += `<tr><td style="text-align:left">f'<sub>c</sub></td><td>${fc} MPa</td></tr>`;
            sum += `<tr><td style="text-align:left">&beta;<sub>1</sub></td><td>${this.f(beta1,4)}</td></tr>`;
            sum += `<tr><td style="text-align:left">E<sub>c</sub></td><td>${this.f(Ec,0)} MPa</td></tr>`;
            sum += `<tr><td style="text-align:left">d<sub>eff</sub></td><td>${this.f(deff,1)} mm</td></tr>`;
            sum += `<tr><td style="text-align:left">d'</td><td>${this.f(dprime,1)} mm</td></tr>`;
            sum += `<tr><td style="text-align:left">Height Above Grade, H</td><td>${p.H} m</td></tr>`;
            sum += `<tr><td style="text-align:left">Total Embedment, d</td><td>${p.d} m</td></tr>`;
            sum += `<tr style="font-weight:bold"><td style="text-align:left">Governing P<sub>u</sub></td><td>${this.f(Pu,1)} kN</td></tr>`;
            sum += `<tr style="font-weight:bold"><td style="text-align:left">Governing V<sub>u</sub></td><td>${this.f(Vu,1)} kN</td></tr>`;
            sum += `<tr style="font-weight:bold"><td style="text-align:left">Governing M<sub>u</sub></td><td>${this.f(Mu,1)} kN-m</td></tr>`;
            sum += `</table>`;
            this.summaryReport = sum;

            // ===== 1. SLENDERNESS (AISC 14th E2/D1) =====
            const K = 1;
            const r_mm = D / 4;  // radius of gyration for circular
            const L_mm = (p.restrained ? p.H : (p.H + p.d)) * 1000;
            const KLr = (K * L_mm) / r_mm;
            const slenderOK = KLr < 200;

            let sl = `\\[ \\frac{KL}{r} = \\frac{${K} \\times ${this.f(L_mm,0)}}{${this.f(r_mm,1)}} = ${this.f(KLr)} \\]`;
            sl += `\\[ ${this.f(KLr)} \\quad ${slenderOK ? '<' : '\\geq'} \\quad 200 \\quad \\textbf{[${slenderOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            sl += `<p>where K = ${K}, L = ${this.f(L_mm/1000,2)} m = ${this.f(L_mm,0)} mm, r = D/4 = ${this.f(r_mm,1)} mm</p>`;
            this.slendernessReport = sl;

            // ===== 2. SOIL COMPRESSION / TENSION =====
            const Ag_m2 = Math.PI * D_m * D_m / 4;
            const perim_m = Math.PI * D_m;
            const skin_total = perim_m * p.Fa * p.d;  // kN (Fa in kPa * d in m * perimeter)
            const endBearing = p.Qa * Ag_m2;           // kN (Qa in kPa * area m²)
            const Pc_capacity = skin_total + endBearing;

            // Pile self-weight (approx 24 kN/m³ concrete)
            const Wpile = 24 * Ag_m2 * (p.H + p.d);
            const P_demand_comp = Pu + Wpile;

            const T_demand = Math.max(0, -Pu);
            const T_capacity = skin_total;

            const soilCompOK = P_demand_comp <= Pc_capacity;
            const soilTensOK = T_demand <= T_capacity;

            let so = `<h4>Compression Check</h4>`;
            so += `\\[ P_u + W_{pile} = ${this.f(Pu,1)} + ${this.f(Wpile,1)} = ${this.f(P_demand_comp,1)} \\text{ kN} \\]`;
            so += `\\[ \\pi D \\cdot d \\cdot F_a + \\frac{\\pi D^2}{4} Q_a = ${this.f(skin_total,1)} + ${this.f(endBearing,1)} = ${this.f(Pc_capacity,1)} \\text{ kN} \\]`;
            so += `\\[ ${this.f(P_demand_comp,1)} \\quad ${soilCompOK ? '<' : '\\geq'} \\quad ${this.f(Pc_capacity,1)} \\quad \\textbf{[${soilCompOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            so += `<h4>Tension Check</h4>`;
            so += `\\[ T = ${this.f(T_demand,1)} \\text{ kN} \\quad ${soilTensOK ? '<' : '\\geq'} \\quad \\pi D \\cdot d \\cdot F_a = ${this.f(T_capacity,1)} \\text{ kN} \\quad \\textbf{[${soilTensOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            this.soilReport = so;

            // ===== 3. LATERAL CAPACITY (NSCP 2015) =====
            const d_third = p.d / 3;
            const S3 = 2 * p.Pp * Math.min(p.d, 3.66);
            const S1 = 2 * p.Pp * Math.min(d_third, 3.66);

            let d_req;
            if (p.restrained) {
                d_req = Math.sqrt(4.25 * (Vu) * p.H / (D_m * S3 + 0.001));
            } else {
                const A_nc = 2.34 * (Vu) / (D_m * S1 + 0.001);
                d_req = (A_nc / 2) * (1 + Math.sqrt(1 + 4.36 * p.H / (A_nc + 0.001)));
            }
            const lateralOK = d_req <= p.d;

            let la = `\\[ S_3 = 2 P_p \\min(d,\\, 3.66\\text{m}) = ${this.f(S3)} \\text{ kPa} \\]`;
            la += `\\[ S_1 = 2 P_p \\min(d/3,\\, 3.66\\text{m}) = ${this.f(S1)} \\text{ kPa} \\]`;
            la += `<h4>Required Embedment Depth</h4>`;
            la += `\\[ d_{req} = ${this.f(d_req)} \\text{ m} \\quad ${lateralOK ? '<' : '\\geq'} \\quad d = ${p.d} \\text{ m} \\quad \\textbf{[${lateralOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            this.lateralReport = la;

            // ===== 4. P-M INTERACTION DIAGRAM (ACI 318-14/19) =====
            // Based on the notebook approach: vary neutral axis depth c
            const nom_P = [], nom_M = [], ult_P = [], ult_M = [], phi_list = [];
            const Ast = Ab;  // single bar or bar group at center
            const Asc = Ast;

            // c varies from large (pure compression) down to small (pure tension region)
            const c_vals = [];
            for (let c = D * 1.5; c >= D * 0.05; c -= D * 0.01) c_vals.push(c);

            for (const c of c_vals) {
                const a = beta1 * c;

                // Strains
                const es = ecu * (deff - c) / c;      // tension bar strain
                const es_prime = ecu * (c - dprime) / c; // compression bar strain
                const fs = Math.min(fy, Math.max(-fy, es * Es));
                const fs_prime = Math.min(fy, Math.max(-fy, es_prime * Es));

                // Forces (in N, then /1000 = kN)
                const Cc = 0.85 * fc * Math.min(a, D) * D / 1000;  // simplified rectangular for circular
                // For circular section: approximate with equivalent rectangle (conservative)
                // Better: use circular segment area
                let Ac_seg;
                if (a >= D) {
                    Ac_seg = Ag;
                } else if (a <= 0) {
                    Ac_seg = 0;
                } else {
                    const val = Math.max(-1, Math.min(1, (R - a) / R));
                    Ac_seg = R * R * Math.acos(val) - (R - a) * Math.sqrt(Math.max(0, 2 * R * a - a * a));
                }
                const Cc_circ = 0.85 * fc * Ac_seg / 1000;  // kN

                const T = Ast * Math.min(fy, Math.abs(fs)) * Math.sign(fs) / 1000;    // kN
                const Cs = Asc * (Math.min(fy, Math.abs(fs_prime)) * Math.sign(fs_prime) - 0.85 * fc) / 1000;

                const Pn = Cc_circ + Cs - T;  // kN

                // Moment about center of section
                // Centroid of circular segment from top
                let yc;
                if (Ac_seg > 1) {
                    const chord = Math.sqrt(Math.max(0, 2 * R * Math.min(a, D) - Math.min(a, D) ** 2));
                    yc = (2 * chord ** 3) / (3 * Ac_seg);
                    yc = Math.min(a, D) / 2;  // simplified
                } else { yc = 0; }
                const arm_cc = R - yc;                    // mm from center
                const arm_cs = R - dprime;               // mm from center (compression bar)
                const arm_t = deff - R;                  // mm from center (tension bar)

                const Mn = (Cc_circ * arm_cc + Cs * arm_cs + T * arm_t) / 1000; // kN-m (mm -> m /1000)

                // Phi factor per ACI 318-14 Sec. 21.2
                let phi;
                if (es >= 0.005) {
                    phi = 0.90;  // tension controlled
                } else if (es <= ey) {
                    phi = 0.65;  // compression controlled
                } else {
                    phi = 0.65 + 0.25 * (es - ey) / (0.005 - ey);  // transition
                    phi = Math.max(0.65, Math.min(0.90, phi));
                }

                const ecc = Pn !== 0 ? Math.abs(Mn / Pn * 1000) : 9999; // mm
                if (ecc > 1.5 * D) continue;

                nom_P.push(Pn);
                nom_M.push(Math.abs(Mn));
                ult_P.push(phi * Pn);
                ult_M.push(phi * Math.abs(Mn));
                phi_list.push(phi);
            }

            // Pure compression cap (0.80 factor per ACI)
            const Pn_max = (0.85 * fc * (Ag - Ab) + fy * Ab) / 1000; // kN
            const Pn_max_capped = 0.80 * Pn_max;

            // Cap all points at Pn_max
            for (let i = 0; i < ult_P.length; i++) {
                if (ult_P[i] > 0.65 * Pn_max_capped) {
                    ult_P[i] = Math.min(ult_P[i], 0.65 * Pn_max_capped);
                }
            }

            // Find phiMn at Pu by interpolating
            let phiMn_at_Pu = 0;
            for (let i = 0; i < ult_P.length - 1; i++) {
                const p1 = ult_P[i], p2 = ult_P[i + 1];
                const m1 = ult_M[i], m2 = ult_M[i + 1];
                if ((p1 >= Pu && p2 <= Pu) || (p1 <= Pu && p2 >= Pu)) {
                    const t = (Pu - p1) / (p2 - p1 + 0.0001);
                    phiMn_at_Pu = m1 + t * (m2 - m1);
                    break;
                }
            }
            const flexOK = phiMn_at_Pu >= Mu;

            let fl = `<h4>Material Properties</h4>`;
            fl += `\\[ E_c = 4700\\sqrt{f'_c} = 4700\\sqrt{${fc}} = ${this.f(Ec,0)} \\text{ MPa} \\]`;
            fl += `\\[ E_s = ${Es} \\text{ MPa}, \\quad \\beta_1 = ${this.f(beta1,4)}, \\quad \\varepsilon_{cu} = ${ecu} \\]`;
            fl += `\\[ A_g = \\frac{\\pi D^2}{4} = ${this.f(Ag,0)} \\text{ mm}^2, \\quad A_s = ${this.f(Ab,0)} \\text{ mm}^2 \\]`;
            fl += `<h4>Interaction Diagram Check</h4>`;
            fl += `\\[ \\phi M_n \\text{ @ } P_u = ${this.f(Pu,1)} \\text{ kN} \\Rightarrow \\phi M_n = ${this.f(phiMn_at_Pu,1)} \\text{ kN-m} \\]`;
            fl += `\\[ \\phi M_n = ${this.f(phiMn_at_Pu,1)} \\quad ${flexOK ? '>' : '<'} \\quad M_u = ${this.f(Mu,1)} \\quad \\textbf{[${flexOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            this.flexuralReport = fl;

            // ===== 5. SHEAR (ACI 318-14/19 Sec. 22.5) =====
            // Vc = (1/6)*sqrt(f'c)*Ag (metric, N)
            const Vc = (1 / 6) * Math.sqrt(fc) * Ag / 1000;  // kN
            const phi_v = 0.75;
            const phiVn = phi_v * Vc;
            const shearOK = phiVn >= Math.abs(Vu);

            let sh = `\\[ V_c = \\frac{1}{6}\\sqrt{f'_c} \\cdot A_g = \\frac{1}{6}\\sqrt{${fc}} \\times ${this.f(Ag,0)} = ${this.f(Vc,1)} \\text{ kN} \\]`;
            sh += `\\[ \\phi V_n = ${phi_v} \\times ${this.f(Vc,1)} = ${this.f(phiVn,1)} \\text{ kN} \\]`;
            sh += `\\[ V_u = ${this.f(Math.abs(Vu),1)} \\text{ kN} \\quad ${shearOK ? '<' : '\\geq'} \\quad \\phi V_n = ${this.f(phiVn,1)} \\text{ kN} \\quad \\textbf{[${shearOK ? 'Satisfactory' : 'FAIL'}]} \\]`;
            this.shearReport = sh;

            // ===== SUMMARY TABLE =====
            this.summaryTable = [
                { check: 'Slenderness (KL/r < 200)', demand: this.f(KLr), capacity: '200', pass: slenderOK },
                { check: 'Soil Compression', demand: this.f(P_demand_comp,1) + ' kN', capacity: this.f(Pc_capacity,1) + ' kN', pass: soilCompOK },
                { check: 'Soil Tension', demand: this.f(T_demand,1) + ' kN', capacity: this.f(T_capacity,1) + ' kN', pass: soilTensOK },
                { check: 'Lateral Embedment', demand: this.f(d_req,2) + ' m', capacity: p.d + ' m', pass: lateralOK },
                { check: 'Flexural (P-M)', demand: this.f(Mu,1) + ' kN-m', capacity: this.f(phiMn_at_Pu,1) + ' kN-m', pass: flexOK },
                { check: 'Shear', demand: this.f(Math.abs(Vu),1) + ' kN', capacity: this.f(phiVn,1) + ' kN', pass: shearOK }
            ];
            this.allPass = this.summaryTable.every(r => r.pass);
            this.computed = true;

            this.$nextTick(() => {
                if (window.MathJax) MathJax.typeset();
                this.plotInteraction(nom_M, nom_P, ult_M, ult_P, phi_list, Mu, Pu);
            });
        },

        plotInteraction(nomM, nomP, ultM, ultP, phis, Mu, Pu) {
            // Split ultimate curve into compression-controlled, transition, and tension-controlled
            const comp_M = [], comp_P = [], trans_M = [], trans_P = [], tens_M = [], tens_P = [];
            for (let i = 0; i < ultP.length; i++) {
                if (phis[i] <= 0.65) {
                    comp_M.push(ultM[i]); comp_P.push(ultP[i]);
                } else if (phis[i] >= 0.90) {
                    tens_M.push(ultM[i]); tens_P.push(ultP[i]);
                } else {
                    trans_M.push(ultM[i]); trans_P.push(ultP[i]);
                }
            }

            // Make sure zones connect
            if (comp_M.length && trans_M.length) {
                trans_M.unshift(comp_M[comp_M.length-1]); trans_P.unshift(comp_P[comp_P.length-1]);
            }
            if (trans_M.length && tens_M.length) {
                tens_M.unshift(trans_M[trans_M.length-1]); tens_P.unshift(trans_P[trans_P.length-1]);
            }

            const traces = [
                // Nominal (dashed, lighter)
                {x: nomM, y: nomP, mode:'lines', name:'Nominal (Pn, Mn)', line:{color:'#bdc3c7',width:1.5,dash:'dot'}, hoverinfo:'skip'},
                // Ultimate - compression controlled
                {x: comp_M, y: comp_P, mode:'lines', name:'Compression Controlled', line:{color:'#2c3e50',width:2.5,dash:'dash'}, fill:'none'},
                // Ultimate - transition
                {x: trans_M, y: trans_P, mode:'lines', name:'Transition', line:{color:'#e74c3c',width:2.5}, fill:'none'},
                // Ultimate - tension controlled
                {x: tens_M, y: tens_P, mode:'lines', name:'Tension Controlled', line:{color:'#2c3e50',width:2.5}, fill:'none'},
            ];

            // All load combination points
            const lcPts_x = [], lcPts_y = [], lcLabels = [];
            for (const lc of this.loadCombos) {
                lcPts_x.push(Math.abs(lc.Mu));
                lcPts_y.push(lc.Pu);
                lcLabels.push(lc.label);
            }
            traces.push({
                x: lcPts_x, y: lcPts_y, mode:'markers+text',
                name:'Load Combinations',
                text: lcLabels,
                textposition: 'top right',
                textfont: {size:9, color:'#7f8c8d'},
                marker:{size:8, color:'#e74c3c', symbol:'square'}
            });

            // Governing point (larger)
            traces.push({
                x: [Math.abs(Mu)], y: [Pu], mode:'markers',
                name:'Governing (Pu=' + this.f(Pu,0) + ', Mu=' + this.f(Mu,1) + ')',
                marker:{size:12, color:'#e74c3c', symbol:'diamond', line:{width:2, color:'#c0392b'}}
            });

            const maxM = Math.max(...ultM, ...nomM, Math.abs(Mu)) * 1.15;
            const maxP = Math.max(...ultP, ...nomP, Pu) * 1.15;
            const minP = Math.min(...ultP, ...nomP, 0, Pu) * 1.15;

            Plotly.newPlot('interaction-plot', traces, {
                title: {text:'P-M Interaction Diagram', font:{size:15,color:'#2c3e50'}},
                xaxis: {title:'\u03D5 Mn (kN-m)', range:[0, maxM], gridcolor:'#ecf0f1', zeroline:true, zerolinecolor:'#bdc3c7'},
                yaxis: {title:'\u03D5 Pn (kN)', range:[minP, maxP], gridcolor:'#ecf0f1', zeroline:true, zerolinecolor:'#bdc3c7', zerolinewidth:2},
                height: 500,
                margin: {t:50, r:40, b:60, l:70},
                legend: {orientation:'h', y:-0.2, x:0.5, xanchor:'center', font:{size:10}},
                plot_bgcolor: '#fafbfc',
                paper_bgcolor: '#fff',
                annotations: [
                    {x: Math.abs(Mu), y: Pu, xref:'x', yref:'y', text:'Design Point', showarrow:true,
                     arrowhead:2, ax:40, ay:-30, font:{size:11, color:'#e74c3c'}}
                ]
            }, {responsive: true});
        }
    }
}).mount('#app');
