import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Simulator", layout="wide")

st.title("🏭 Production Line One-Piece Flow Simulator")
st.caption("Simulasi konveyor riil: Produk berjalan di konveyor tengah, ditarik operator berhadapan (atas-bawah), dikerjakan sesuai Effective CT (Standard Time / MP), lalu dilanjutkan.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES & ACTUAL MP ---
st.subheader("1. Data Input Proses & Actual MP")
st.write("Isi proses, CT Base, Allowance, dan Actual MP. Effective CT adalah waktu siklus per unit setelah dibagi jumlah MP.")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting", "Stitching", "Assembly", "Outsole", "Packing"],
    "Cycle Time Base (s)": [10.0, 20.0, 15.0, 12.0, 8.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 2, 1, 1, 1]
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
    col2.metric("🚨 Bottleneck", f"{bottleneck_process}", delta=f"{max_ct:.1f} s", delta_color="inverse")
    col3.metric("👥 Total MP", f"{df['Actual MP'].sum()} Orang")
    col4.metric("⏱️ Takt Time", f"{takt_time_sec:.1f} s")

    # --- STEP 2: ANIMASI KANVAS LAYOUT BERHADAPAN & KONVEYOR BERGERAK ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Layout Berhadapan & Konveyor Berjalan")
    st.caption("Meja operator berpasangan di sisi atas dan bawah konveyor tengah. Produk berjalan di konveyor, ditarik ke meja saat tiba di stasiun, dikerjakan, lalu dikembalikan ke konveyor.")

    stations_list = []
    for idx, row in df.iterrows():
        mp_count = int(row["Actual MP"])
        std_time = row["Standard Time (s)"]
        eff_ct = row["Effective CT (s)"]
        is_bn = (row["Nama Proses"] == bottleneck_process)
        
        for m in range(mp_count):
            stations_list.append({
                "process_name": row["Nama Proses"],
                "display_name": row["Nama Proses"] + (f" ({m+1})" if mp_count > 1 else ""),
                "std_time": float(std_time),
                "eff_ct": float(eff_ct),
                "mp": mp_count,
                "is_bottleneck": is_bn
            })

    stations_json = json.dumps(stations_list)
    takt_val = float(takt_time_sec)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #eef2f7;
                margin: 0;
                padding: 10px;
                text-align: center;
            }}
            #canvas-container {{
                background: #ffffff;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                padding: 15px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 1100px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #f8fafc;
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
            <canvas id="simCanvas" width="1050" height="480"></canvas>
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
            const spacing = canvas.width / (nStations + 1);

            let products = [];
            let finishedCount = 0;
            let lastTimestamp = null;
            let spawnTimer = 0;

            function changeSpeed() {{
                speedMultiplier = parseFloat(speedSelect.value);
            }}

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Gambar Konveyor Tengah Memanjang
                ctx.fillStyle = "#e2e8f0";
                ctx.strokeStyle = "#475569";
                ctx.lineWidth = 3;
                ctx.fillRect(40, 205, canvas.width - 80, 70);
                ctx.strokeRect(40, 205, canvas.width - 80, 70);

                ctx.strokeStyle = "#94a3b8";
                ctx.setLineDash([10, 10]);
                ctx.beginPath();
                ctx.moveTo(40, 240);
                ctx.lineTo(canvas.width - 40, 240);
                ctx.stroke();
                ctx.setLineDash([]);

                // 2. Gambar Stasiun Atas dan Bawah Berhadapan
                stations.forEach(function(stn, i) {{
                    let x = spacing * (i + 1);
                    let isTop = (i % 2 === 0);
                    let tableY = isTop ? 90 : 390;
                    let operatorY = isTop ? 28 : 442;

                    ctx.fillStyle = stn.is_bottleneck ? "#ef4444" : "#3b82f6";
                    ctx.fillRect(x - 45, tableY - 25, 90, 50);
                    ctx.strokeStyle = "#0f172a";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 45, tableY - 25, 90, 50);

                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 10px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(stn.display_name, x, tableY - 8);
                    ctx.font = "10px Arial";
                    ctx.fillText("CT: " + stn.eff_ct.toFixed(1) + "s", x, tableY + 10);

                    ctx.fillStyle = "#0f172a";
                    ctx.font = "bold 13px Arial";
                    ctx.fillText("(● 👤)", x, operatorY);
                }});

                // 3. Gambar Produk (👟) di Konveyor atau Meja Operator
                products.forEach(function(prod) {{
                    if (prod.status === 'conveyor') {{
                        ctx.fillStyle = "#10b981";
                        ctx.beginPath();
                        ctx.arc(prod.x, 240, 14, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.strokeStyle = "#047857";
                        ctx.lineWidth = 2;
                        ctx.stroke();

                        ctx.fillStyle = "#ffffff";
                        ctx.font = "11px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", prod.x, 244);
                    }} else if (prod.status === 'working') {{
                        let stn = stations[prod.stationIdx];
                        let isTop = (prod.stationIdx % 2 === 0);
                        let tableY = isTop ? 90 : 390;
                        let stnX = spacing * (prod.stationIdx + 1);

                        ctx.fillStyle = "#f59e0b";
                        ctx.beginPath();
                        ctx.arc(stnX, tableY, 14, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.strokeStyle = "#b45309";
                        ctx.lineWidth = 2;
                        ctx.stroke();

                        ctx.fillStyle = "#ffffff";
                        ctx.font = "11px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", stnX, tableY + 4);

                        let prog = Math.min(100, (prod.workElapsed / stn.eff_ct) * 100);
                        ctx.fillStyle = "#cbd5e1";
                        ctx.fillRect(stnX - 40, tableY + 30, 80, 5);
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(stnX - 40, tableY + 30, (80 * (prog / 100)), 5);
                    }}
                }});

                ctx.fillStyle = "#0f172a";
                ctx.font = "bold 13px Arial";
                ctx.textAlign = "left";
                ctx.fillText("📦 Total Sepatu Selesai: " + finishedCount + " Pcs", 50, 470);
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
                        x: 50,
                        status: 'conveyor',
                        stationIdx: 0,
                        workElapsed: 0
                    }});
                }}

                products.forEach(function(prod) {{
                    if (prod.status === 'conveyor') {{
                        prod.x += 80 * adjustedDelta;

                        let targetStnIdx = prod.stationIdx;
                        let targetX = spacing * (targetStnIdx + 1);

                        if (prod.x >= targetX) {{
                            prod.x = targetX;
                            prod.status = 'working';
                            prod.workElapsed = 0;
                        }}
                    }} else if (prod.status === 'working') {{
                        let stn = stations[prod.stationIdx];
                        prod.workElapsed += adjustedDelta;

                        if (prod.workElapsed >= stn.eff_ct) {{
                            prod.stationIdx++;
                            if (prod.stationIdx >= stations.length) {{
                                finishedCount++;
                                prod.status = 'finished';
                            }} else {{
                                prod.status = 'conveyor';
                            }}
                        }}
                    }}
                }});

                products = products.filter(function(p) {{
                    return p.status !== 'finished';
                }});

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

    st.components.v1.html(html_code, height=540, scrolling=False)

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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_correct_ct")
