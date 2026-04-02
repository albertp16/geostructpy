const { createApp } = Vue;
const DEG = Math.PI / 180;

// Meyerhof bearing capacity factors (phi = 0 to 50)
const M_NC = [5.14,5.38,5.63,5.90,6.19,6.49,6.81,7.16,7.53,7.92,8.35,8.80,9.28,9.81,10.37,10.98,11.63,12.34,13.10,13.93,14.83,15.82,16.88,18.05,19.32,20.72,22.25,23.94,25.80,27.86,30.14,32.67,35.49,38.64,42.16,46.12,50.59,55.63,61.35,67.87,75.31,83.86,93.71,105.11,118.37,133.88,152.10,173.64,199.26,229.93,266.89];
const M_NQ = [1.00,1.09,1.20,1.31,1.43,1.57,1.72,1.88,2.06,2.25,2.47,2.71,2.97,3.26,3.59,3.94,4.34,4.77,5.26,5.80,6.40,7.07,7.82,8.66,9.60,10.66,11.85,13.20,14.72,16.44,18.40,20.63,23.18,26.09,29.44,33.30,37.75,42.92,48.93,55.96,64.20,73.90,85.38,99.02,115.31,134.88,158.51,187.21,222.32,265.51,319.07];
const M_NY = [0.00,0.07,0.15,0.24,0.34,0.45,0.57,0.71,0.86,1.03,1.22,1.44,1.69,1.97,2.29,2.65,3.06,3.53,4.07,4.68,5.39,6.20,7.13,8.20,9.44,10.88,12.54,14.47,16.72,19.34,22.40,25.99,30.22,35.19,41.06,48.03,56.31,66.19,78.03,92.25,109.41,130.22,155.55,186.54,224.64,271.76,330.35,403.67,496.01,613.16,762.89];

function interp(arr, phi) {
    const i = Math.floor(phi);
    if (i < 0) return arr[0];
    if (i >= 50) return arr[50];
    return arr[i] * (1 - (phi - i)) + arr[i + 1] * (phi - i);
}

createApp({
    data() {
        return {
            p: { c: 0, gamma: 18, phi: 30, theta: 0, shape: 'square', B: 2.0, L: 3.0, Df: 1.5, FS: 3.0 },
            computed: false,
            report: ''
        };
    },
    methods: {
        f: (v, d=3) => v.toFixed(d),
        calculate() {
            const {c, gamma:g, phi, theta, shape, B, Df, FS} = this.p;
            let L = this.p.L;
            if (shape === 'strip') L = 1000;
            else if (shape === 'square' || shape === 'circular') L = B;

            const Nc = interp(M_NC, phi);
            const Nq = interp(M_NQ, phi);
            const Ny = interp(M_NY, phi);
            const q = g * Df;

            // Shape factors (Meyerhof/De Beer)
            const Fcs = 1 + (B / L) * (Nq / Nc);
            const Fqs = 1 + (B / L) * Math.tan(phi * DEG);
            const Fys = 1 - 0.4 * (B / L);

            // Depth factors
            let Fcd, Fqd, Fyd;
            const ratio = Df / B;
            if (ratio <= 1) {
                Fqd = 1 + 2 * Math.tan(phi * DEG) * Math.pow(1 - Math.sin(phi * DEG), 2) * ratio;
                Fcd = Fqd - (1 - Fqd) / (Nq * Math.tan(phi * DEG) + 0.001);
                Fyd = 1.0;
            } else {
                Fqd = 1 + 2 * Math.tan(phi * DEG) * Math.pow(1 - Math.sin(phi * DEG), 2) * Math.atan(ratio);
                Fcd = Fqd - (1 - Fqd) / (Nq * Math.tan(phi * DEG) + 0.001);
                Fyd = 1.0;
            }
            // Fix Fcd for phi=0
            if (phi === 0) { Fcd = 1 + 0.4 * (ratio <= 1 ? ratio : Math.atan(ratio)); }

            // Inclination factors
            const Fci = Math.pow(1 - theta / 90, 2);
            const Fqi = Fci;
            const Fyi = theta > 0 ? Math.pow(1 - theta / phi, 2) : 1.0;

            // Ultimate bearing capacity
            const term1 = c * Nc * Fcs * Fcd * Fci;
            const term2 = q * Nq * Fqs * Fqd * Fqi;
            const term3 = 0.5 * g * B * Ny * Fys * Fyd * Fyi;
            const qu = term1 + term2 + term3;
            const qall = qu / FS;

            let r = `<h4>Bearing Capacity Factors (\\(\\phi' = ${phi}^\\circ\\), Meyerhof)</h4>`;
            r += `\\[ N_c = ${this.f(Nc,2)}, \\quad N_q = ${this.f(Nq,2)}, \\quad N_\\gamma = ${this.f(Ny,2)} \\]`;

            r += `<h4>Shape Factors</h4>`;
            r += `\\[ F_{cs} = 1 + \\frac{B}{L}\\frac{N_q}{N_c} = ${this.f(Fcs,4)} \\]`;
            r += `\\[ F_{qs} = 1 + \\frac{B}{L}\\tan\\phi' = ${this.f(Fqs,4)} \\]`;
            r += `\\[ F_{\\gamma s} = 1 - 0.4\\frac{B}{L} = ${this.f(Fys,4)} \\]`;

            r += `<h4>Depth Factors (D<sub>f</sub>/B = ${this.f(ratio,2)})</h4>`;
            r += `\\[ F_{cd} = ${this.f(Fcd,4)}, \\quad F_{qd} = ${this.f(Fqd,4)}, \\quad F_{\\gamma d} = ${this.f(Fyd,4)} \\]`;

            r += `<h4>Inclination Factors (\\(\\theta = ${theta}^\\circ\\))</h4>`;
            r += `\\[ F_{ci} = ${this.f(Fci,4)}, \\quad F_{qi} = ${this.f(Fqi,4)}, \\quad F_{\\gamma i} = ${this.f(Fyi,4)} \\]`;

            r += `<h4>Surcharge</h4>`;
            r += `\\[ q = \\gamma \\cdot D_f = ${g} \\times ${Df} = ${this.f(q,2)} \\text{ kPa} \\]`;

            r += `<h4>Ultimate Bearing Capacity (Meyerhof, 1963)</h4>`;
            r += `\\[ q_u = c'N_cF_{cs}F_{cd}F_{ci} + qN_qF_{qs}F_{qd}F_{qi} + \\tfrac{1}{2}\\gamma BN_\\gamma F_{\\gamma s}F_{\\gamma d}F_{\\gamma i} \\]`;
            r += `\\[ q_u = ${this.f(term1,2)} + ${this.f(term2,2)} + ${this.f(term3,2)} \\]`;
            r += `\\[ \\boxed{q_u = ${this.f(qu,2)} \\text{ kPa}} \\]`;

            r += `<h4>Allowable Bearing Capacity</h4>`;
            r += `\\[ q_{all} = \\frac{q_u}{FS} = \\frac{${this.f(qu,2)}}{${FS}} = \\boxed{${this.f(qall,2)} \\text{ kPa}} \\]`;

            this.report = r;
            this.computed = true;
            this.$nextTick(() => {
                if (window.MathJax) MathJax.typeset();
                this.plotFactors();
            });
        },
        plotFactors() {
            const angles = Array.from({length:51}, (_,i) => i);
            const phi = this.p.phi;
            const nc = interp(M_NC, phi), nq = interp(M_NQ, phi), ny = interp(M_NY, phi);
            const xmin = 0.1;

            const projLines = [];
            [[nc,'#2980b9'],[nq,'#e67e22'],[ny,'#27ae60']].forEach(([val,col]) => {
                if (val > 0) {
                    projLines.push({x:[xmin,val], y:[phi,phi], mode:'lines', line:{color:col,width:1,dash:'dash'}, showlegend:false, hoverinfo:'skip'});
                    projLines.push({x:[val,val], y:[phi,0], mode:'lines', line:{color:col,width:1,dash:'dash'}, showlegend:false, hoverinfo:'skip'});
                }
            });

            Plotly.newPlot('mey-plot', [
                {x: M_NC, y: angles, mode:'lines', name:'Nc', line:{color:'#2980b9',width:2}},
                {x: M_NQ, y: angles, mode:'lines', name:'Nq', line:{color:'#e67e22',width:2}},
                {x: M_NY, y: angles, mode:'lines', name:'N\u03B3', line:{color:'#27ae60',width:2}},
                ...projLines,
                {x: [nc], y: [phi], mode:'markers', name:'Nc='+nc.toFixed(1), marker:{size:10,color:'#2980b9',symbol:'diamond'}},
                {x: [nq], y: [phi], mode:'markers', name:'Nq='+nq.toFixed(1), marker:{size:10,color:'#e67e22',symbol:'diamond'}},
                {x: [ny], y: [phi], mode:'markers', name:'N\u03B3='+ny.toFixed(1), marker:{size:10,color:'#27ae60',symbol:'diamond'}}
            ], {
                title:'Meyerhof Bearing Capacity Factors',
                xaxis:{title:'Bearing Capacity Factor', type:'log', range:[-1,3.2]},
                yaxis:{title:'Friction Angle \u03C6\u2032 (deg)', range:[0,50]},
                height:420,
                margin:{t:40,r:30,b:50,l:60},
                legend:{orientation:'h', y:-0.18}
            }, {responsive:true});
        }
    }
}).mount('#app');
