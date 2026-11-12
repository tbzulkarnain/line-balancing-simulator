import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Simulator", layout="wide")

st.title("🏭 Production Line Balancing & WIP Bottleneck Simulator")
st.caption("Simulasi lini riil: Waktu proses utuh per operator dengan load sharing paralel, serta visualisasi antrean WIP berjejer rapi di konveyor saat terjadi bottleneck.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES & ACTUAL MP ---
st.subheader("1. Data Input Proses & Actual MP")
st.write("Masukkan CT Base dan Allowance. Jika proses tertentu lambat atau memiliki MP sedikit, antrean sepatu akan terlihat menumpuk berjejer di konveyor.")

default_data = pd.DataFrame({
    "Nama Proses": ["st collar lining", "st tip", "st counter", "hotmelt", "st margin", "punching", "insert lace"],
    "Cycle Time Base (s)": [10.0, 45.0, 12.0, 18.0, 17.0, 15.0, 15.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 2, 1, 1, 1, 1, 1]  # st tip diset 2 MP agar terlihat pembagian kerjanya
})

edited_df = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nama Proses": st.column_config.TextColumn("Nama Proses", required=True),
        "Cycle Time Base (s)": st.column_config.NumberColumn("CT Base (s)", min_value=0.1, format="%.2f"),
        "Allowance (%)": st.column_config.NumberColumn("Allowance (%)", min_value=0.0, max_value=100.0, format="%.1f"),
        "Actual MP": st.column_config.NumberColumn("Actual MP", min_value=1, step=1, required=True)
    }
)

if not edited_df.empty and takt_time_sec > 0:
    df = edited_df.copy()
    df["Standard Time (s)"] = df["Cycle Time Base (s)"] * (1 + df["Allowance (%)"] / 100)
    df["Effective CT (s)"] = df["Standard Time (s)"] / df["Actual MP"]
    
    max_ct = df["Effective CT (s)"].max()
    bottleneck_idx = df["Effective CT (s)"].idxmax()
    bottleneck_process = df.loc[bottleneck_idx, "Nama Proses"]
    
    total_effective_ct = df["Effective CT (s)"].sum()
    num_stations = len(df)
    balancing_rate = (total_effective_ct / (max_ct * num_stations)) * 100

    # METRICS SUMMARY
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Balancing Rate", f"{balancing_rate:.2f}%")
    col2.metric("🚨 Bottleneck", f"{bottleneck_process}", delta=f"{max_ct:.1f} s/pcs (Effective)", delta_color="inverse")
    col3.metric("👥 Total MP", f"{df['Actual MP'].sum()} Orang")
    col4.metric("⏱️ Takt Time", f"{takt_time_sec:.1f} s")

    # --- STEP 2: ANIMASI KANVAS DENGAN ANTREAN WIP BERJEJER & PARALLEL LOAD SHARING ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Lini Produksi & Visualisasi Bottleneck")
    st.caption("Sepatu yang menumpuk akibat antrean proses akan berjejer rapi di konveyor depan stasiun tanpa saling menimpa.")

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

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #e8f5e9;
                margin: 0;
                padding: 10px;
                text-align: center;
            }}
            #canvas-container {{
                background: #ffffff;
                border: 2px solid #a5d6a7;
                border-radius: 12px;
                padding: 15px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 1150px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #dcedc8;
                border-radius: 8px;
                width: 100%;
                height: auto;
            }}
            .panel {{
                margin-top: 15px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 20px;
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
                padding: 10px 18px;
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
            .speed-selector {{
                font-size: 14px;
                font-weight: bold;
                color: #1e293b;
            }}
            select {{
                padding: 6px 12px;
                font-size: 14px;
                border-radius: 6px;
                border: 1px solid #cbd5e1;
                background-color: white;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div id="canvas-container">
            <h3 id="timer-display" style="margin: 0 0 10px 0; color: #1e293b; font-size: 18px;">⏱️ Waktu Aktual: 0.0 Detik | Takt Time: {takt_val:.1f}s</h3>
            <canvas id="simCanvas" width="1100" height="520"></canvas>
            <div class="panel">
                <div class="controls">
                    <button onclick="startSimulation()">▶ Play</button>
                    <button onclick="pauseSimulation()">⏸ Pause</button>
                    <button class="reset" onclick="resetSimulation()">🔄 Reset</button>
                </div>
                <div class="speed-selector">
                    ⚡ Kecepatan: 
                    <select id="speedSelect" onchange="changeSpeed()">
                        <option value="1">1x (Normal)</option>
                        <option value="2">2x</option>
                        <option value="5" selected>5x</option>
                        <option value="10">10x</option>
                    </select>
                </div>
            </div>
        </div>

        <script>
            const stations = {stations_json};
            const taktTime = {takt_val};
            const canvas = document.getElementById("simCanvas");
            const ctx = canvas.getContext("2d");
            const timerDisplay = document.getElementById("timer-display");
            const speedSelect = document.getElementById("speedSelect");

            let animationId = null;
            let timeElapsed = 0;
            let isRunning = false;
            let speedMultiplier = 5;

            const nStations = stations.length;
            const colSpacing = (canvas.width - 120) / Math.max(1, nStations);

            let products = [];
            let finishedCount = 0;
            let lastTimestamp = null;
            let spawnTimer = 0;

            function changeSpeed() {{
                speedMultiplier = parseFloat(speedSelect.value);
            }}

            function getStationCoords(i) {{
                let isTop = (i % 2 === 0);
                let x = 80 + i * colSpacing + (colSpacing / 2);
                let tableY = isTop ? 120 : 400;
                return {{ x: x, tableY: tableY, isTop: isTop }};
            }}

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Konveyor Tengah Memanjang
                ctx.fillStyle = "#f1f8e9";
                ctx.strokeStyle = "#1f2937";
                ctx.lineWidth = 2.5;
                ctx.fillRect(30, 230, canvas.width - 60, 65);
                ctx.strokeRect(30, 230, canvas.width - 60, 65);

                ctx.strokeStyle = "#94a3b8";
                ctx.setLineDash([10, 10]);
                ctx.beginPath();
                ctx.moveTo(30, 262.5);
                ctx.lineTo(canvas.width - 30, 262.5);
                ctx.stroke();
                ctx.setLineDash([]);

                // 2. Gambar Meja & Operator Sisi Atas dan Bawah
                stations.forEach(function(stn, i) {{
                    let pos = getStationCoords(i);
                    let x = pos.x;
                    let tableY = pos.tableY;
                    let isTop = pos.isTop;

                    ctx.fillStyle = "#111827";
                    ctx.font = "bold 10px Arial";
                    ctx.textAlign = "center";
                    let labelY = isTop ? (tableY - 52) : (tableY + 62);
                    ctx.fillText(stn.process_name, x, labelY);
                    ctx.font = "10px Arial";
                    ctx.fillStyle = "#374151";
                    ctx.fillText("CT: " + stn.std_time.toFixed(1) + "s", x, labelY + (isTop ? 13 : -13));
                    ctx.fillText(stn.display_name, x, labelY + (isTop ? 26 : -26));

                    ctx.fillStyle = stn.is_bottleneck ? "#dc2626" : "#3b66b8";
                    ctx.fillRect(x - 28, tableY - 28, 56, 56);
                    ctx.strokeStyle = "#ffffff";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 28, tableY - 28, 56, 56);

                    let opX = x - 42;
                    ctx.fillStyle = "#000000";
                    ctx.beginPath();
                    ctx.arc(opX, tableY, 10, 0, Math.PI * 2);
                    ctx.fill();

                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 2.5;
                    ctx.beginPath();
                    ctx.arc(opX, tableY, 14, Math.PI * 0.72, Math.PI * 1.28);
                    ctx.stroke();

                    // Hitung WIP tertahan di stasiun ini (yang antre di konveyor)
                    let waitingCount = products.filter(p => p.currentStationIdx === i && p.status === 'queued').length;
                    let workingCount = products.filter(p => p.currentStationIdx === i && p.status === 'working').length;
                    let totalHold = waitingCount + workingCount;

                    if (totalHold > 0) {{
                        ctx.fillStyle = waitingCount > 0 ? "#b91c1c" : "#047857";
                        ctx.beginPath();
                        ctx.roundRect(x + 10, tableY - 38, 34, 16, 5);
                        ctx.fill();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 9px Arial";
                        ctx.fillText("👟 " + totalHold, x + 27, tableY - 27);
                    }}
                }});

                // 3. Gambar Produk (👟) — Berjejer mundur di konveyor tanpa saling menimpa!
                products.forEach(function(prod) {{
                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        ctx.fillStyle = prod.status === 'queued' ? "#fee2e2" : "#ffffff";
                        ctx.strokeStyle = prod.status === 'queued' ? "#dc2626" : "#1f2937";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.roundRect(prod.x - 14, 248, 28, 28, 5);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "15px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", prod.x, 269);
                    }} else if (prod.status === 'working') {{
                        let pos = getStationCoords(prod.currentStationIdx);
                        let stn = stations[prod.currentStationIdx];

                        ctx.fillStyle = "#fef3c7";
                        ctx.strokeStyle = "#d97706";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.roundRect(pos.x - 14, pos.tableY - 14, 28, 28, 5);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "15px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", pos.x, pos.tableY + 5);

                        let prog = Math.min(100, (prod.workElapsed / stn.std_time) * 100);
                        ctx.fillStyle = "#1e293b";
                        ctx.fillRect(pos.x - 20, pos.tableY + 18, 40, 5);
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(pos.x - 20, pos.tableY + 18, 40 * (prog / 100), 5);
                    }}
                }});

                let totalWipInLine = products.length;
                ctx.fillStyle = "#111827";
                ctx.font = "bold 13px Arial";
                ctx.textAlign = "left";
                ctx.fillText("📦 Total Output Selesai: " + finishedCount + " Pcs   |   🔄 Total WIP di Lini: " + totalWipInLine + " Pcs", 35, 505);
            }}

            function update(timestamp) {{
                if (!isRunning) return;

                if (!lastTimestamp) lastTimestamp = timestamp;
                let deltaTime = (timestamp - lastTimestamp) / 1000;
                lastTimestamp = timestamp;

                let adjustedDelta = deltaTime * speedMultiplier;
                timeElapsed += adjustedDelta;
                spawnTimer += adjustedDelta;

                if (spawnTimer >= Math.max(1.0, taktTime)) {{
                    spawnTimer = 0;
                    products.push({{
                        id: Math.random(),
                        x: 45,
                        status: 'conveyor',
                        currentProcessStep: 0,
                        currentStationIdx: -1,
                        workElapsed: 0
                    }});
                }}

                let uniqueProcesses = [...new Set(stations.map(s => s.process_name))];

                // Update posisi setiap produk dengan sistem antrean berjejer mundur di konveyor
                products.forEach(function(prod, idx) {{
                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        let targetProcName = uniqueProcesses[prod.currentProcessStep];
                        let candidateStations = stations.map((s, i) => Object.assign({{}}, s, {{ idx: i }})).filter(s => s.process_name === targetProcName);
                        
                        // Cari operator paralel yang meja kerjanya kosong
                        let availableStation = candidateStations.find(cs => !products.some(p => p.currentStationIdx === cs.idx && p.status === 'working'));

                        if (availableStation) {{
                            prod.currentStationIdx = availableStation.idx;
                            let targetPos = getStationCoords(availableStation.idx);
                            
                            if (Math.abs(prod.x - targetPos.x) <= 5) {{
                                prod.x = targetPos.x;
                                prod.status = 'working';
                                prod.workElapsed = 0;
                            }} else {{
                                prod.x += 100 * adjustedDelta;
                                if (prod.x > targetPos.x) prod.x = targetPos.x;
                                prod.status = 'conveyor';
                            }}
                        }} else {{
                            // Jika semua operator di proses ini sibuk, produk antre dan berjejer rapi mundur di konveyor
                            let firstStationOfProc = candidateStations[0];
                            let targetPos = getStationCoords(firstStationOfProc.idx);
                            
                            // Hitung berapa produk lain yang sudah antre di depan produk ini pada proses yang sama
                            let aheadCount = 0;
                            for (let j = 0; j < idx; j++) {{
                                if (products[j].currentProcessStep === prod.currentProcessStep && (products[j].status === 'queued' || products[j].status === 'conveyor')) {{
                                    aheadCount++;
                                }}
                            }}

                            let stopX = targetPos.x - (aheadCount * 32) - 40;
                            if (stopX < 45) stopX = 45;

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

                timerDisplay.innerText = "⏱️ Waktu Aktual: " + timeElapsed.toFixed(1) + " Detik | Takt Time: " + taktTime.toFixed(1) + "s (Kecepatan: " + speedMultiplier + "x)";
                
                drawScene();
                animationId = requestAnimationFrame(update);
            }}

            function startSimulation() {{
                if (!isRunning) {{
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
                lastTimestamp = null;
                timerDisplay.innerText = "⏱️ Waktu Aktual: 0.0 Detik | Takt Time: " + taktTime.toFixed(1) + "s";
                drawScene();
            }}

            drawScene();
        </script>
    </body>
    </html>
    """

    st.components.v1.html(html_code, height=580, scrolling=False)

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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_wip_queue")
