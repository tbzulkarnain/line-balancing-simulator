import streamlit as st
import pandas as pd
import json
import math

st.set_page_config(page_title="Line Balancing Simulator", layout="wide")

st.title("🏭 Production Line Balancing & WIP Bottleneck Simulator")
st.caption("Simulasi lini riil: Target Pasang/Jam, Auto-Stop 1 Jam, Actual MP Otomatis, & Analisis IE.")

# --- KONTROL PARAMETER DI ATAS (TARGET PASANG/JAM) ---
st.markdown("### ⚙️ Parameter Lini Produksi")
col_p1, col_p2 = st.columns(2)
with col_p1:
    target_demand_per_hour = st.number_input("Target Production (Pasang/Jam)", value=50, step=5, key="input_demand_hour")

takt_time_sec = 3600 / target_demand_per_hour if target_demand_per_hour > 0 else 0
st.info(f"⏱️ **Takt Time Target Lini**: {takt_time_sec:.2f} detik/pasang (Simulasi berjalan untuk durasi 1 Jam / 3600 Detik)")

# --- STEP 1: TABEL INPUT TUNGGAL ---
st.markdown("---")
st.subheader("1. Data Input Proses & Pengaturan Actual MP")
st.write("Masukkan Nama Proses, CT Base, dan Allowance. Kolom **Actual MP** terisi otomatis (pembulatan ke atas) dan dapat disesuaikan langsung.")

if "line_data" not in st.session_state:
    st.session_state.line_data = pd.DataFrame({
        "Nama Proses": ["st collar lining", "st tip", "st counter", "hotmelt", "st margin", "punching", "insert lace"],
        "Cycle Time Base (s)": [10.0, 35.0, 12.0, 18.0, 17.0, 15.0, 15.0],
        "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    })

temp_df = st.session_state.line_data.copy()
temp_df["Standard Time (s)"] = temp_df["Cycle Time Base (s)"] * (1 + temp_df["Allowance (%)"] / 100)

# Auto MP dihitung ulang otomatis berdasarkan Takt Time terbaru
temp_df["Auto MP"] = temp_df["Standard Time (s)"].apply(lambda st_val: max(1, math.ceil(st_val / takt_time_sec)) if takt_time_sec > 0 else 1)
temp_df["Actual MP"] = temp_df["Auto MP"]

edited_df = st.data_editor(
    temp_df[["Nama Proses", "Cycle Time Base (s)", "Allowance (%)", "Standard Time (s)", "Actual MP"]],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nama Proses": st.column_config.TextColumn("Nama Proses", required=True),
        "Cycle Time Base (s)": st.column_config.NumberColumn("CT Base (s)", min_value=0.1, format="%.2f"),
        "Allowance (%)": st.column_config.NumberColumn("Allowance (%)", min_value=0.0, max_value=100.0, format="%.1f"),
        "Standard Time (s)": st.column_config.NumberColumn("Standard Time (s)", format="%.2f", disabled=True),
        "Actual MP": st.column_config.NumberColumn("Actual MP (Adjustable)", min_value=1, step=1, required=True)
    },
    key="single_input_table"
)

st.session_state.line_data = edited_df[["Nama Proses", "Cycle Time Base (s)", "Allowance (%)", "Actual MP"]]

if not edited_df.empty and takt_time_sec > 0:
    df = edited_df.copy()
    df["Effective CT (s)"] = df["Standard Time (s)"] / df["Actual MP"]
    
    max_ct = df["Effective CT (s)"].max()
    bottleneck_idx = df["Effective CT (s)"].idxmax()
    bottleneck_process = df.loc[bottleneck_idx, "Nama Proses"]
    
    total_effective_ct = df["Effective CT (s)"].sum()
    num_stations = len(df)
    balancing_rate = (total_effective_ct / (max_ct * num_stations)) * 100

    # METRICS SUMMARY
    st.markdown("---")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("🎯 Balancing Rate", f"{balancing_rate:.2f}%")
    col_m2.metric("🚨 Bottleneck", f"{bottleneck_process}", delta=f"{max_ct:.1f} s/pasang", delta_color="inverse")
    col_m3.metric("👥 Total MP", f"{df['Actual MP'].sum()} Orang")
    col_m4.metric("⏱️ Takt Time", f"{takt_time_sec:.1f} s")

    # --- STEP 2: ANIMASI KANVAS DENGAN AUTO-STOP 1 JAM (3600s) ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Lini Produksi Sepatu (One-Piece Flow)")
    st.caption("Simulasi berjalan selama 1 Jam (3600 Detik) dan berhenti otomatis (Auto-Stop).")

    line_stations = []
    global_station_index = 0

    for idx, row in df.iterrows():
        p_name = row["Nama Proses"]
        mp_count = int(row["Actual MP"])
        std_time = float(row["Standard Time (s)"])
        eff_ct = float(row["Effective CT (s)"])
        is_bn = (p_name == bottleneck_process)

        sub_stations = []
        for m in range(mp_count):
            sub_stations.append({
                "station_id": global_station_index,
                "process_name": p_name,
                "display_name": f"{p_name} ({m+1})" if mp_count > 1 else p_name,
                "std_time": std_time,
                "eff_ct": eff_ct,
                "is_bottleneck": is_bn
            })
            global_station_index += 1
        
        line_stations.append({
            "process_name": p_name,
            "sub_stations": sub_stations
        })

    flat_stations = []
    for group in line_stations:
        for sub in group["sub_stations"]:
            flat_stations.append(sub)

    stations_json = json.dumps(flat_stations)
    takt_val = float(takt_time_sec)

    speed_multiplier = st.slider("⚡ Kecepatan Simulasi (Multiplier)", min_value=1.0, max_value=50.0, value=20.0, step=1.0, key="speed_slider_bottom")
    current_speed = float(speed_multiplier)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #e8f5e9;
                margin: 0;
                padding: 4px;
                text-align: center;
            }}
            #canvas-container {{
                background: #ffffff;
                border: 2px solid #a5d6a7;
                border-radius: 8px;
                padding: 10px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 1060px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #dcedc8;
                border-radius: 6px;
                width: 100%;
                height: auto;
            }}
            .panel {{
                margin-top: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .controls {{
                display: flex;
                gap: 10px;
            }}
            button {{
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 8px 18px;
                font-size: 14px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            button:hover {{
                background-color: #1d4ed8;
            }}
            button.reset {{
                background-color: #dc2626;
            }}
            button.reset:hover {{
                background-color: #b91c1c;
            }}
        </style>
    </head>
    <body>
        <div id="canvas-container">
            <h4 id="timer-display" style="margin: 0 0 6px 0; color: #1e293b; font-size: 14px;">⏱️ Waktu Simulasi: 0.0s / 3600.0s (1 Jam)</h4>
            <canvas id="simCanvas" width="1040" height="260"></canvas>
            <div class="panel">
                <div class="controls">
                    <button onclick="startSimulation()">▶ Play</button>
                    <button onclick="pauseSimulation()">⏸ Pause</button>
                    <button class="reset" onclick="resetSimulation()">🔄 Reset</button>
                </div>
            </div>
        </div>

        <script>
            const stations = {stations_json};
            const taktTime = {takt_val};
            let speedMultiplier = {current_speed};
            const MAX_TIME = 3600.0;

            const canvas = document.getElementById("simCanvas");
            const ctx = canvas.getContext("2d");
            const timerDisplay = document.getElementById("timer-display");

            let animationId = null;
            let timeElapsed = 0;
            let isRunning = false;
            let isFinished = false;

            const nStations = stations.length;
            const colSpacing = (canvas.width - 30) / Math.max(1, nStations);
            const tableWidth = Math.max(13, Math.min(32, colSpacing * 0.7));
            const tableHeight = Math.max(26, Math.min(42, tableWidth * 1.3));
            const fontSize = Math.max(9, Math.min(12, Math.floor(11 * (10 / Math.max(8, nStations)))));

            let products = [];
            let finishedCount = 0;
            let lastTimestamp = null;
            let spawnTimer = 0;

            function getStationCoords(i) {{
                let isTop = (i % 2 === 0);
                let x = 15 + i * colSpacing + (colSpacing / 2);
                let tableY = isTop ? 68 : 192;
                return {{ x: x, tableY: tableY, isTop: isTop }};
            }}

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                ctx.fillStyle = "#f1f8e9";
                ctx.strokeStyle = "#1f2937";
                ctx.lineWidth = 1.5;
                ctx.fillRect(8, 105, canvas.width - 16, 50);
                ctx.strokeRect(8, 105, canvas.width - 16, 50);

                ctx.strokeStyle = "#94a3b8";
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(8, 130);
                ctx.lineTo(canvas.width - 8, 130);
                ctx.stroke();
                ctx.setLineDash([]);

                stations.forEach(function(stn, i) {{
                    let pos = getStationCoords(i);
                    let x = pos.x;
                    let tableY = pos.tableY;
                    let isTop = pos.isTop;

                    ctx.fillStyle = stn.is_bottleneck ? "#dc2626" : "#2563eb";
                    ctx.fillRect(x - tableWidth/2, tableY - tableHeight/2, tableWidth, tableHeight);
                    ctx.strokeStyle = "#ffffff";
                    ctx.lineWidth = 1;
                    ctx.strokeRect(x - tableWidth/2, tableY - tableHeight/2, tableWidth, tableHeight);

                    ctx.textAlign = "center";
                    if (isTop) {{
                        ctx.fillStyle = "#0f172a";
                        ctx.font = "bold " + fontSize + "px Arial";
                        ctx.fillText(stn.display_name, x, tableY - tableHeight/2 - 14);

                        ctx.fillStyle = "#334155";
                        ctx.font = "bold " + (fontSize - 1) + "px Arial";
                        ctx.fillText("CT:" + stn.std_time.toFixed(1) + "s", x, tableY - tableHeight/2 - 4);
                    }} else {{
                        ctx.fillStyle = "#334155";
                        ctx.font = "bold " + (fontSize - 1) + "px Arial";
                        ctx.fillText("CT:" + stn.std_time.toFixed(1) + "s", x, tableY + tableHeight/2 + 10);

                        ctx.fillStyle = "#0f172a";
                        ctx.font = "bold " + fontSize + "px Arial";
                        ctx.fillText(stn.display_name, x, tableY + tableHeight/2 + 21);
                    }}

                    let opX = x - (tableWidth/2 + 6);
                    ctx.fillStyle = "#000000";
                    ctx.beginPath();
                    ctx.arc(opX, tableY, Math.max(3.5, tableWidth/4), 0, Math.PI * 2);
                    ctx.fill();

                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 1.2;
                    ctx.beginPath();
                    ctx.arc(opX, tableY, Math.max(6, tableWidth/2.8), Math.PI * 0.72, Math.PI * 1.28);
                    ctx.stroke();

                    let waitingCount = products.filter(p => p.currentStationIdx === i && p.status === 'queued').length;
                    let workingCount = products.filter(p => p.currentStationIdx === i && p.status === 'working').length;
                    let totalHold = waitingCount + workingCount;

                    if (totalHold > 0) {{
                        ctx.fillStyle = waitingCount > 0 ? "#b91c1c" : "#047857";
                        ctx.beginPath();
                        ctx.roundRect(x + (tableWidth/2 + 2), tableY - 9, 22, 11, 2);
                        ctx.fill();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 8px Arial";
                        ctx.fillText("👟" + totalHold, x + (tableWidth/2 + 13), tableY - 1);
                    }}
                }});

                products.forEach(function(prod) {{
                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        ctx.fillStyle = prod.status === 'queued' ? "#fee2e2" : "#ffffff";
                        ctx.strokeStyle = prod.status === 'queued' ? "#dc2626" : "#1f2937";
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.roundRect(prod.x - 8, 118, 16, 16, 2);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "10px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", prod.x, 131);
                    }} else if (prod.status === 'working') {{
                        let pos = getStationCoords(prod.currentStationIdx);
                        let stn = stations[prod.currentStationIdx];

                        ctx.fillStyle = "#fef3c7";
                        ctx.strokeStyle = "#d97706";
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.roundRect(pos.x - 8, pos.tableY - 8, 16, 16, 2);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "10px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", pos.x, pos.tableY + 4);

                        let prog = Math.min(100, (prod.workElapsed / stn.std_time) * 100);
                        ctx.fillStyle = "#1e293b";
                        ctx.fillRect(pos.x - 9, pos.tableY + 9, 18, 2.5);
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(pos.x - 9, pos.tableY + 9, 18 * (prog / 100), 2.5);
                    }}
                }});

                let totalWipInLine = products.length;
                ctx.fillStyle = "#111827";
                ctx.font = "bold 11px Arial";
                ctx.textAlign = "left";
                ctx.fillText("📦 Total Output 1 Jam: " + finishedCount + " Pasang   |   🔄 Total WIP di Lini: " + totalWipInLine + " Pasang" + (isFinished ? " — ✅ SELESAI (1 JAM)" : ""), 10, 252);
            }}

            function update(timestamp) {{
                if (!isRunning) return;

                if (!lastTimestamp) lastTimestamp = timestamp;
                let deltaTime = (timestamp - lastTimestamp) / 1000;
                lastTimestamp = timestamp;

                let adjustedDelta = deltaTime * speedMultiplier;
                timeElapsed += adjustedDelta;

                if (timeElapsed >= MAX_TIME) {{
                    timeElapsed = MAX_TIME;
                    isRunning = false;
                    isFinished = true;
                    drawScene();
                    timerDisplay.innerText = "⏱️ Waktu Simulasi: 3600.0s / 3600.0s (1 Jam Selesai!) 🎉";
                    return;
                }}

                spawnTimer += adjustedDelta;

                if (spawnTimer >= Math.max(1.0, taktTime)) {{
                    spawnTimer = 0;
                    products.push({{
                        id: Math.random(),
                        x: 12,
                        status: 'conveyor',
                        currentProcessStep: 0,
                        currentStationIdx: -1,
                        workElapsed: 0
                    }});
                }}

                let uniqueProcesses = [...new Set(stations.map(s => s.process_name))];

                products.forEach(function(prod, idx) {{
                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        let targetProcName = uniqueProcesses[prod.currentProcessStep];
                        let candidateStations = stations.map((s, i) => Object.assign({{}}, s, {{ idx: i }})).filter(s => s.process_name === targetProcName);
                        
                        let availableStation = candidateStations.find(cs => !products.some(p => p.currentStationIdx === cs.idx && p.status === 'working'));

                        if (availableStation) {{
                            prod.currentStationIdx = availableStation.idx;
                            let targetPos = getStationCoords(availableStation.idx);
                            
                            if (Math.abs(prod.x - targetPos.x) <= 3) {{
                                prod.x = targetPos.x;
                                prod.status = 'working';
                                prod.workElapsed = 0;
                            }} else {{
                                prod.x += 100 * adjustedDelta;
                                if (prod.x > targetPos.x) prod.x = targetPos.x;
                                prod.status = 'conveyor';
                            }}
                        }} else {{
                            let firstStationOfProc = candidateStations[0];
                            let targetPos = getStationCoords(firstStationOfProc.idx);
                            
                            let aheadCount = 0;
                            for (let j = 0; j < idx; j++) {{
                                if (products[j].currentProcessStep === prod.currentProcessStep && (products[j].status === 'queued' || products[j].status === 'conveyor')) {{
                                    aheadCount++;
                                }}
                            }}

                            let stopX = targetPos.x - (aheadCount * 18) - 12;
                            if (stopX < 12) stopX = 12;

                            if (prod.x < stopX) {{
                                prod.x += 100 * adjustedDelta;
                                if (prod.x >= stopX) {{
                                    prod.x = stopX;
                                    prod.status = 'queued';
                                    prod.currentStationIdx = firstStationOfProc.idx;
                                }} else {{
                                    prod.status = 'conveyor';
                                }}
                            }} else {{
                                prod.x = stopX;
                                prod.status = 'queued';
                                prod.currentStationIdx = firstStationOfProc.idx;
                            }}
                        }}
                    }} else if (prod.status === 'working') {{
                        let stn = stations[prod.currentStationIdx];
                        prod.workElapsed += adjustedDelta;

                        if (prod.workElapsed >= stn.std_time) {{
                            prod.currentProcessStep++;
                            if (prod.currentProcessStep >= uniqueProcesses.length) {{
                                finishedCount++;
                                prod.status = 'finished';
                            }} else {{
                                let currentPos = getStationCoords(prod.currentStationIdx);
                                prod.x = currentPos.x;
                                prod.status = 'conveyor';
                                prod.workElapsed = 0;
                            }}
                        }}
                    }}
                }});

                products = products.filter(p => p.status !== 'finished');

                timerDisplay.innerText = "⏱️ Waktu Simulasi: " + timeElapsed.toFixed(1) + "s / 3600.0s (Kecepatan: " + speedMultiplier + "x)";
                
                drawScene();
                animationId = requestAnimationFrame(update);
            }}

            function startSimulation() {{
                if (!isRunning && !isFinished) {{
                    isRunning = true;
                    lastTimestamp = null;
                    animationId = requestAnimationFrame(update);
                }}
            }}

            function pauseSimulation() {{
                isRunning = false;
                lastTimestamp = null;
                cancelAnimationFrame(animationId);
            }}

            function resetSimulation() {{
                pauseSimulation();
                timeElapsed = 0;
                finishedCount = 0;
                spawnTimer = 0;
                products = [];
                isFinished = false;
                lastTimestamp = null;
                timerDisplay.innerText = "⏱️ Waktu Simulasi: 0.0s / 3600.0s (1 Jam)";
                drawScene();
            }}

            drawScene();
        </script>
    </body>
    </html>
    """

    st.components.v1.html(html_code, height=410, scrolling=False)

    # --- STEP 3: YAMAZUMI CHART ---
    st.markdown("---")
    st.subheader("3. Yamazumi Chart (Analisis Effective CT vs Takt Time)")
    
    import plotly.graph_objects as go
    fig_bar = go.Figure()
    colors = ['#EF4444' if i == bottleneck_idx else '#3B82F6' for i in range(len(df))]

    fig_bar.add_trace(go.Bar(
        x=df["Nama Proses"],
        y=df["Effective CT (s)"],
        text=[f"{ct:.1f}s (MP:{mp})" for ct, mp in zip(df["Effective CT (s)"], df["Actual MP"])],
        textposition='auto',
        marker_color=colors
    ))

    fig_bar.add_hline(
        y=takt_time_sec, 
        line_dash="dash", 
        line_color="red", 
        annotation_text=f"Takt Time Target ({takt_time_sec:.1f}s)"
    )

    fig_bar.update_layout(height=380, template="plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_autostop_hour")

    # --- STEP 4: ANALISIS TEKNIK INDUSTRI (IE) OTOMATIS ---
    st.markdown("---")
    st.subheader("📋 4. Analisis & Evaluasi Teknik Industri (Industrial Engineering)")
    
    total_mp_used = df['Actual MP'].sum()
    labor_productivity = target_demand_per_hour / total_mp_used if total_mp_used > 0 else 0
    
    st.markdown(f"""
    Berdasarkan konfigurasi lini dan hasil simulasi berdurasi 1 jam, berikut adalah evaluasi performa lini produksi sepatu Anda:
    
    1. **Evaluasi Target vs Kapasitas Aktual**:
       * **Target Demand**: `{target_demand_per_hour} Pasang/Jam` (Takt Time: `{takt_time_sec:.2f} detik`).
       * **Analisis Kesenjangan**: Selisih antara target teoretis dan output nyata di lantai produksi disebabkan oleh **Line Balancing Loss**, waktu muat awal lini (*filling time*), serta fenomena *blocking* dan *starving* antar stasiun estafet murni (*One-Piece Flow*). Produk yang masih tertahan sebagai WIP di akhir jam ke-1 membuktikan adanya hambatan aliran mikro.
    
    2. **Identifikasi Proses Kritis (Bottleneck)**:
       * Proses **`{bottleneck_process}`** bertindak sebagai pembatas utama laju produksi dengan *Effective Cycle Time* sebesar **`{max_ct:.2f} detik`**. 
       * *Rekomendasi IE*: Jika Anda ingin mendongkrak output mendekati target penuh, pertimbangkan untuk menambah operator (*Actual MP*) atau memperbaiki metode kerja (*method study*) khusus pada proses `{bottleneck_process}` ini.
    
    3. **Indikator Ketenagakerjaan & Produktivitas**:
       * **Total Manpower (MP)**: `{total_mp_used} Orang`
       * **Produktivitas Tenaga Kerja**: `{labor_productivity:.2f} Pasang/Orang/Jam`
       * **Tingkat Keseimbangan Lini (Balancing Rate)**: `{balancing_rate:.2f}%` (Semakin mendekati 100%, semakin merata beban kerja antar operator).
    """)
