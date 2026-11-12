import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Conveyor & WIP Simulator", layout="wide")

st.title("🏭 Real-Time Production Line Conveyor & WIP Bottleneck Simulator")
st.caption("Simulasi nyata: Aliran konveyor tengah, operator berhadapan di kanan-kiri, penumpukan WIP akibat Bottleneck, dan kontrol kecepatan.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES & ACTUAL MP ---
st.subheader("1. Data Input Proses & Alokasi Actual MP")
st.write("Ubah jumlah Actual MP di tabel bawah untuk melihat bagaimana penyesuaian tenaga kerja memengaruhi Bottleneck dan Balancing Rate.")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting", "Stitching 1", "Stitching 2", "Assembly", "Outsole", "Packing"],
    "Cycle Time Base (s)": [6.0, 18.0, 15.0, 12.0, 10.0, 5.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 3, 2, 2, 2, 1]  # Stitching diberi MP lebih banyak karena CT tinggi
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
    col2.metric("🚨 Bottleneck", f"{bottleneck_process}", delta=f"{max_ct:.1f} s/pcs", delta_color="inverse")
    col3.metric("👥 Total MP", f"{df['Actual MP'].sum()} Orang")
    col4.metric("⏱️ Takt Time", f"{takt_time_sec:.1f} s")

    # --- STEP 2: ANIMASI KANVAS KONVEYOR TENGAH & WIP BUFFER ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Layout Konveyor Riil, MP, & Penumpukan WIP (Bottleneck)")
    st.caption("Rel konveyor di tengah mengalirkan produk. Operator di atas dan bawah mengambil produk sesuai kapasitas MP & Cycle Time. Perhatikan penumpukan produk (WIP) di stasiun Bottleneck.")

    stations_data = []
    for idx, row in df.iterrows():
        stations_data.append({
            "name": row["Nama Proses"],
            "ct": float(row["Effective CT (s)"]),
            "mp": int(row["Actual MP"]),
            "is_bottleneck": (row["Nama Proses"] == bottleneck_process)
        })

    stations_json = json.dumps(stations_data)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f8fafc;
                margin: 0;
                padding: 10px;
                text-align: center;
            }}
            #canvas-container {{
                background: #f1f5f9;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                padding: 15px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 1050px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #ffffff;
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
            <h3 id="timer-display" style="margin: 0 0 10px 0; color: #1e293b; font-size: 18px;">⏱️ Waktu Aktual: 0.0 Detik</h3>
            <canvas id="simCanvas" width="1000" height="480"></canvas>
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
                        <option value="5">5x</option>
                        <option value="10">10x</option>
                    </select>
                </div>
            </div>
        </div>

        <script>
            const stations = {stations_json};
            const canvas = document.getElementById("simCanvas");
            const ctx = canvas.getContext("2d");
            const timerDisplay = document.getElementById("timer-display");
            const speedSelect = document.getElementById("speedSelect");

            let animationId = null;
            let timeElapsed = 0;
            let isRunning = false;
            let speedMultiplier = 1;

            const nStations = stations.length;
            const spacing = canvas.width / (nStations + 1);

            // Status stasiun: wipBuffer (jumlah antrean produk menumpuk di konveyor stasiun tersebut)
            let stationState = stations.map(function(stn) {{
                return {{ wipBuffer: 0, elapsedWork: 0, isWorking: false }};
            }});

            let finishedCount = 0;
            let lastTimestamp = null;
            let spawnTimer = 0;

            function changeSpeed() {{
                speedMultiplier = parseFloat(speedSelect.value);
            }}

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Gambar Rel Konveyor Utama di Tengah (Memanjang)
                ctx.fillStyle = "#e2e8f0";
                ctx.strokeStyle = "#475569";
                ctx.lineWidth = 3;
                ctx.fillRect(40, 210, canvas.width - 80, 70);
                ctx.strokeRect(40, 210, canvas.width - 80, 70);

                // Rel Rol Konveyor Tengah (garis putus-putus)
                ctx.strokeStyle = "#94a3b8";
                ctx.setLineDash([10, 10]);
                ctx.beginPath();
                ctx.moveTo(40, 245);
                ctx.lineTo(canvas.width - 40, 245);
                ctx.stroke();
                ctx.setLineDash([]);

                // 2. Gambar Stasiun Kerja (Operator Atas & Bawah berhadapan dengan rel tengah)
                stations.forEach(function(stn, i) {{
                    let x = spacing * (i + 1);
                    let state = stationState[i];

                    // Posisi Meja & Operator ATAS (Genap) atau BAWAH (Ganjil) disebar berhadap-hadapan
                    let isTop = (i % 2 === 0);
                    let tableY = isTop ? 80 : 360;
                    let operatorY = isTop ? 30 : 430;

                    // Kotak Meja Kerja Operator
                    ctx.fillStyle = stn.is_bottleneck ? "#ef4444" : "#3b82f6";
                    ctx.fillRect(x - 50, tableY - 25, 100, 50);
                    ctx.strokeStyle = "#0f172a";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 50, tableY - 25, 100, 50);

                    // Teks Informasi Stasiun & MP
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 11px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(stn.name, x, tableY - 8);
                    ctx.font = "10px Arial";
                    ctx.fillText("MP: " + stn.mp + " | CT: " + stn.ct.toFixed(1) + "s", x, tableY + 10);

                    // Ikon Manpower (👤 x MP)
                    ctx.fillStyle = "#0f172a";
                    ctx.font = "14px Arial";
                    let mpIcons = "";
                    for(let m=0; m < Math.min(stn.mp, 3); m++) mpIcons += "👤";
                    if(stn.mp > 3) mpIcons += "+";
                    ctx.fillText(mpIcons, x, operatorY);

                    // Progress bar pengerjaan stasiun
                    let progressPercent = Math.min(100, (state.elapsedWork / stn.ct) * 100);
                    ctx.fillStyle = "#cbd5e1";
                    ctx.fillRect(x - 45, tableY + 32, 90, 6);
                    if (state.isWorking) {{
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(x - 45, tableY + 32, (90 * (progressPercent / 100)), 6);
                    }}

                    // 3. Visualisasi Penumpukan WIP (Bottleneck Buffer) di Konveyor Depan Stasiun
                    if (state.wipBuffer > 0) {{
                        ctx.fillStyle = "#f59e0b";
                        let bufferDisplay = Math.min(state.wipBuffer, 5); // Maksimal visual 5 kotak
                        for(let b = 0; b < bufferDisplay; b++) {{
                            let bx = isTop ? (x - 20 + (b * 8)) : (x - 20 - (b * 8));
                            let by = 245;
                            ctx.fillRect(bx - 6, by - 6, 12, 12);
                            ctx.strokeStyle = "#78350f";
                            ctx.strokeRect(bx - 6, by - 6, 12, 12);
                        }}
                        // Angka jumlah tumpukan WIP
                        ctx.fillStyle = "#b91c1c";
                        ctx.font = "bold 11px Arial";
                        ctx.fillText("WIP: " + state.wipBuffer, x, isTop ? 170 : 315);
                    }}
                }});

                // Info Output Produk Selesai di Ujung Konveyor
                ctx.fillStyle = "#0f172a";
                ctx.font = "bold 13px Arial";
                ctx.textAlign = "left";
                ctx.fillText("📦 Total Output Selesai: " + finishedCount + " Pcs", 50, 470);
            }}

            function update(timestamp) {{
                if (!isRunning) return;

                if (!lastTimestamp) lastTimestamp = timestamp;
                let deltaTime = (timestamp - lastTimestamp) / 1000;
                lastTimestamp = timestamp;

                let adjustedDelta = deltaTime * speedMultiplier;
                timeElapsed += adjustedDelta;
                spawnTimer += adjustedDelta;

                // Masuknya material baru ke stasiun pertama setiap 2 detik (atau sesuai takt time)
                if (spawnTimer >= 2.0) {{
                    spawnTimer = 0;
                    stationState[0].wipBuffer++;
                }}

                // Simulasi Aliran WIP antar Stasiun Berdasarkan Kapasitas CT & MP
                stations.forEach(function(stn, idx) {{
                    let state = stationState[idx];

                    // Jika stasiun sedang tidak bekerja tapi ada WIP di buffernya, ambil untuk dikerjakan
                    if (!state.isWorking && state.wipBuffer > 0) {{
                        state.isWorking = true;
                        state.elapsedWork = 0;
                        state.wipBuffer--; // Ambil 1 dari antrean konveyor
                    }}

                    // Jika sedang bekerja, hitung waktu pengerjaan sesuai Effective CT
                    if (state.isWorking) {{
                        state.elapsedWork += adjustedDelta;

                        if (state.elapsedWork >= stn.ct) {{
                            state.isWorking = false;
                            state.elapsedWork = 0;

                            // Teruskan ke stasiun berikutnya, atau jika stasiun terakhir hitung selesai
                            if (idx === stations.length - 1) {{
                                finishedCount++;
                            }} else {{
                                stationState[idx + 1].wipBuffer++;
                            }}
                        }}
                    }}
                }});

                timerDisplay.innerText = "⏱️ Waktu Aktual: " + timeElapsed.toFixed(1) + " Detik (Kecepatan: " + speedMultiplier + "x)";
                
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
                lastTimestamp = null;
                stationState = stations.map(function() {{
                    return {{ wipBuffer: 0, elapsedWork: 0, isWorking: false }};
                }});
                timerDisplay.innerText = "⏱️ Waktu Aktual: 0.0 Detik";
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
    st.subheader("3. Yamazumi Chart (Analisis Efisiensi & Kapasitas MP)")
    
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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_mp_wip")
