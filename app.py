import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Simulator", layout="wide")

st.title("🏭 Production Line Balancing & Bottleneck Simulator")
st.caption("Simulasi konveyor: Operator mengambil 1 sepatu ke meja kerja. Jika stasiun lambat (bottleneck), sepatu berikutnya berjejer mundur di konveyor tanpa saling menimpa.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES & ACTUAL MP ---
st.subheader("1. Data Input Proses & Actual MP")
st.write("Naikkan CT Base salah satu proses (misal Assembly jadi 35s) untuk melihat antrean sepatu berjejer di konveyor depan stasiun tersebut.")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting", "Stitching", "Assembly", "Outsole", "Packing"],
    "Cycle Time Base (s)": [8.0, 18.0, 28.0, 10.0, 7.0],
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

    # --- STEP 2: ANIMASI KANVAS DENGAN ANTREAN WIP TANPA TUMPUK ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Layout Berhadapan & Visualisasi Antrean Bottleneck")
    st.caption("Setiap operator hanya memegang 1 sepatu di meja. Sepatu berlebih akan berjejer rapi mundur di rel konveyor lengkap dengan penghitung jumlah WIP.")

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
                background-color: #e8f5e9;
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
                max-width: 1120px;
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
            <canvas id="simCanvas" width="1080" height="500"></canvas>
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
            const cols = Math.ceil(nStations / 2);
            const colSpacing = (canvas.width - 140) / Math.max(1, cols);

            let products = [];
            let finishedCount = 0;
            let lastTimestamp = null;
            let spawnTimer = 0;

            function changeSpeed() {{
                speedMultiplier = parseFloat(speedSelect.value);
            }}

            function getStationCoords(i) {{
                let isTop = (i % 2 === 0);
                let colIdx = Math.floor(i / 2);
                let x = 130 + colIdx * colSpacing;
                let tableY = isTop ? 120 : 380;
                return {{ x: x, tableY: tableY, isTop: isTop }};
            }}

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Konveyor Tengah Memanjang (Persis Referensi Gambar)
                ctx.fillStyle = "#f1f8e9";
                ctx.strokeStyle = "#1f2937";
                ctx.lineWidth = 2.5;
                ctx.fillRect(40, 215, canvas.width - 80, 70);
                ctx.strokeRect(40, 215, canvas.width - 80, 70);

                // Garis arah aliran konveyor
                ctx.strokeStyle = "#94a3b8";
                ctx.setLineDash([10, 10]);
                ctx.beginPath();
                ctx.moveTo(40, 250);
                ctx.lineTo(canvas.width - 40, 250);
                ctx.stroke();
                ctx.setLineDash([]);

                // 2. Gambar Meja & Operator Sisi Atas dan Bawah (Layout Sesuai Gambar Referensi)
                stations.forEach(function(stn, i) {{
                    let pos = getStationCoords(i);
                    let x = pos.x;
                    let tableY = pos.tableY;
                    let isTop = pos.isTop;

                    // Label Nama Proses di atas meja (untuk baris atas) atau di bawah meja (untuk baris bawah)
                    ctx.fillStyle = "#111827";
                    ctx.font = "bold 12px Arial";
                    ctx.textAlign = "center";
                    let labelY = isTop ? (tableY - 52) : (tableY + 62);
                    ctx.fillText(stn.display_name, x, labelY);
                    ctx.font = "11px Arial";
                    ctx.fillStyle = "#374151";
                    ctx.fillText("CT: " + stn.eff_ct.toFixed(1) + "s", x, labelY + (isTop ? 14 : -14));

                    // Meja Kerja (Biru / Merah jika Bottleneck) - Vertikal seperti gambar referensi
                    ctx.fillStyle = stn.is_bottleneck ? "#dc2626" : "#3b66b8";
                    ctx.fillRect(x - 32, tableY - 32, 64, 64);
                    ctx.strokeStyle = "#ffffff";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 32, tableY - 32, 64, 64);

                    // Kursi & Operator di sebelah KIRI meja (persis gambar referensi)
                    let opX = x - 48;
                    ctx.fillStyle = "#000000";
                    ctx.beginPath();
                    ctx.arc(opX, tableY, 11, 0, Math.PI * 2);
                    ctx.fill();

                    // Sandaran kursi melengkung di kiri lingkaran operator
                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.arc(opX, tableY, 16, Math.PI * 0.72, Math.PI * 1.28);
                    ctx.stroke();

                    // Hitung total WIP yang menunggu/dikerjakan di stasiun ini
                    let waitingCount = products.filter(p => p.stationIdx === i && p.status === 'queued').length;
                    let workingCount = products.filter(p => p.stationIdx === i && p.status === 'working').length;
                    let totalHold = waitingCount + workingCount;

                    // Badge Indikator Jumlah Sepatu yang Dipegang/Antre di Stasiun Ini
                    if (totalHold > 0) {{
                        ctx.fillStyle = waitingCount > 0 ? "#b91c1c" : "#047857";
                        ctx.beginPath();
                        ctx.roundRect(x + 14, tableY - 42, 38, 18, 6);
                        ctx.fill();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 10px Arial";
                        ctx.fillText("👟 " + totalHold, x + 33, tableY - 30);
                    }}
                }});

                // 3. Gambar Produk (👟) — Tidak Saling Menimpa!
                products.forEach(function(prod) {{
                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        // Sepatu berjalan atau antre berjejer rapi di atas rel konveyor
                        ctx.fillStyle = prod.status === 'queued' ? "#fee2e2" : "#ffffff";
                        ctx.strokeStyle = prod.status === 'queued' ? "#dc2626" : "#1f2937";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.roundRect(prod.x - 16, 234, 32, 32, 6);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "18px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", prod.x, 256);
                    }} else if (prod.status === 'working') {{
                        // Hanya 1 sepatu yang sedang dikerjakan berada di atas meja operator
                        let pos = getStationCoords(prod.stationIdx);
                        let stn = stations[prod.stationIdx];

                        ctx.fillStyle = "#fef3c7";
                        ctx.strokeStyle = "#d97706";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.roundRect(pos.x - 16, pos.tableY - 18, 32, 32, 6);
                        ctx.fill();
                        ctx.stroke();

                        ctx.font = "18px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟", pos.x, pos.tableY + 4);

                        // Progress Bar Pengerjaan di dalam meja
                        let prog = Math.min(100, (prod.workElapsed / stn.eff_ct) * 100);
                        ctx.fillStyle = "#1e293b";
                        ctx.fillRect(pos.x - 24, pos.tableY + 20, 48, 6);
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(pos.x - 24, pos.tableY + 20, 48 * (prog / 100), 6);
                    }}
                }});

                // Info Total Output Selesai & Total WIP di Lini
                let totalWipInLine = products.length;
                ctx.fillStyle = "#111827";
                ctx.font = "bold 13px Arial";
                ctx.textAlign = "left";
                ctx.fillText("📦 Total Output Selesai: " + finishedCount + " Pcs   |   🔄 Total WIP di Lini: " + totalWipInLine + " Pcs", 45, 485);
            }}

            function update(timestamp) {{
                if (!isRunning) return;

                if (!lastTimestamp) lastTimestamp = timestamp;
                let deltaTime = (timestamp - lastTimestamp) / 1000;
                lastTimestamp = timestamp;

                let adjustedDelta = deltaTime * speedMultiplier;
                timeElapsed += adjustedDelta;
                spawnTimer += adjustedDelta;

                // Produk baru masuk ke awal konveyor setiap Takt Time
                if (spawnTimer >= Math.max(1.0, taktTime)) {{
                    spawnTimer = 0;
                    products.push({{
                        id: Math.random(),
                        x: 55,
                        status: 'conveyor',
                        stationIdx: 0,
                        workElapsed: 0
                    }});
                }}

                // Proses setiap stasiun: Cek apakah meja kosong untuk menarik sepatu dari konveyor
                stations.forEach(function(stn, idx) {{
                    let isStationBusy = products.some(p => p.stationIdx === idx && p.status === 'working');
                    if (!isStationBusy) {{
                        // Cari sepatu terdepan yang sedang menunggu/tiba di stasiun ini
                        let candidate = products.find(p => p.stationIdx === idx && p.status === 'queued');
                        if (candidate) {{
                            candidate.status = 'working';
                            candidate.workElapsed = 0;
                        }}
                    }}
                }});

                // Update posisi setiap sepatu agar berjejer rapi tanpa menimpa satu sama lain
                for (let i = 0; i < products.length; i++) {{
                    let prod = products[i];

                    if (prod.status === 'conveyor' || prod.status === 'queued') {{
                        let targetPos = getStationCoords(prod.stationIdx);
                        let targetX = targetPos.x;

                        // Hitung posisi antrean jika sudah ada sepatu lain yang antre di stasiun yang sama
                        let aheadInSameStation = 0;
                        for (let j = 0; j < i; j++) {{
                            if (products[j].stationIdx === prod.stationIdx && (products[j].status === 'queued' || products[j].status === 'conveyor')) {{
                                aheadInSameStation++;
                            }}
                        }}

                        // Beri jarak 36px per sepatu agar berjejer mundur ke kiri dan TIDAK saling menimpa
                        let stopX = targetX - (aheadInSameStation * 36);

                        if (prod.x < stopX) {{
                            prod.x += 110 * adjustedDelta;
                            if (prod.x >= stopX) {{
                                prod.x = stopX;
                                prod.status = 'queued';
                            }} else {{
                                prod.status = 'conveyor';
                            }}
                        }} else {{
                            prod.x = stopX;
                            prod.status = 'queued';
                        }}
                    }} else if (prod.status === 'working') {{
                        let stn = stations[prod.stationIdx];
                        prod.workElapsed += adjustedDelta;

                        // Selesai dikerjakan di meja, kembalikan ke rel konveyor untuk menuju stasiun berikutnya
                        if (prod.workElapsed >= stn.eff_ct) {{
                            let currentPos = getStationCoords(prod.stationIdx);
                            prod.stationIdx++;

                            if (prod.stationIdx >= stations.length) {{
                                finishedCount++;
                                prod.status = 'finished';
                            }} else {{
                                prod.x = currentPos.x;
                                prod.status = 'conveyor';
                                prod.workElapsed = 0;
                            }}
                        }}
                    }}
                }}

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

    st.components.v1.html(html_code, height=560, scrolling=False)

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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_no_overlap")
