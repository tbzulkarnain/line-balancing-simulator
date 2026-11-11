import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Video Simulator", layout="wide")

st.title("🏭 Production Line Video Simulator & Line Balancing")
st.caption("Simulasi konveyor interaktif dengan animasi halus, timer detik, dan progres kerja independen per stasiun berdasarkan Cycle Time.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES ---
st.subheader("1. Data Input Proses & Cycle Time")
st.write("Isi proses produksi. Setiap operator akan bekerja dengan durasi sesuai Cycle Time masing-masing.")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting", "Stitching 1", "Stitching 2", "Assembly 1", "Assembly 2", "Outsole", "QC", "Packing"],
    "Cycle Time Base (s)": [12.0, 22.0, 18.0, 28.0, 15.0, 20.0, 14.0, 10.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 1, 1, 1, 1, 1, 1, 1]
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

    # --- STEP 2: ANIMASI HTML5 CANVAS (DIPERBESAR & TOMBOL PASTI KELIHATAN) ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Video Aliran Konveyor & Progres Kerja Stasiun")
    st.caption("Perhatikan bar progress di setiap meja operator: operator merampungkan pekerjaannya sesuai besar Cycle Time masing-masing.")

    stations_data = []
    for idx, row in df.iterrows():
        stations_data.append({
            "name": row["Nama Proses"],
            "ct": float(row["Effective CT (s)"]),
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
                background-color: #f9fafb;
                margin: 0;
                padding: 10px;
                text-align: center;
            }}
            #canvas-container {{
                background: #e6f4ea;
                border: 2px solid #d1d5db;
                border-radius: 10px;
                padding: 15px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 1000px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #ffffff;
                border-radius: 6px;
                width: 100%;
                height: auto;
            }}
            .controls {{
                margin-top: 15px;
                display: flex;
                justify-content: center;
                gap: 15px;
            }}
            button {{
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
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
            <h3 id="timer-display" style="margin: 0 0 15px 0; color: #1f2937; font-size: 20px;">⏱️ Timer: 0.0 Detik</h3>
            <canvas id="simCanvas" width="960" height="460"></canvas>
            <div class="controls">
                <button onclick="startSimulation()">▶ Play Simulasi</button>
                <button onclick="pauseSimulation()">⏸ Pause</button>
                <button class="reset" onclick="resetSimulation()">🔄 Reset</button>
            </div>
        </div>

        <script>
            const stations = {stations_json};
            const canvas = document.getElementById("simCanvas");
            const ctx = canvas.getContext("2d");
            const timerDisplay = document.getElementById("timer-display");

            let animationId = null;
            let timeElapsed = 0;
            let isRunning = false;
            let shoePos = 0;

            const mid = Math.ceil(stations.length / 2);
            const topStations = stations.slice(0, mid);
            const bottomStations = stations.slice(mid);
            const maxCols = Math.max(topStations.length, bottomStations.length);
            const colWidth = canvas.width / (maxCols + 0.5);

            let stationProgress = stations.map(() => 0);

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Jalur Konveyor Tengah yang Luas
                ctx.fillStyle = "#f3f4f6";
                ctx.strokeStyle = "#374151";
                ctx.lineWidth = 3;
                ctx.fillRect(40, 175, canvas.width - 80, 110);
                ctx.strokeRect(40, 175, canvas.width - 80, 110);

                // Garis Konveyor Putus-putus
                ctx.strokeStyle = "#9ca3af";
                ctx.setLineDash([12, 12]);
                ctx.beginPath();
                ctx.moveTo(40, 230);
                ctx.lineTo(canvas.width - 40, 230);
                ctx.stroke();
                ctx.setLineDash([]);

                let globalIndex = 0;

                // 2. Stasiun Sisi ATAS
                topStations.forEach((stn, i) => {{
                    let x = 90 + i * colWidth;
                    let y = 75;
                    let prog = stationProgress[globalIndex];

                    // Kotak Meja Operator
                    ctx.fillStyle = stn.is_bottleneck ? "#ef4444" : "#3b82f6";
                    ctx.fillRect(x - 48, y - 35, 96, 70);
                    ctx.strokeStyle = "#000";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 48, y - 35, 96, 70);

                    // Teks Nama & CT
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 12px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(stn.name, x, y - 12);
                    ctx.font = "11px Arial";
                    ctx.fillText("CT: " + stn.ct.toFixed(1) + "s", x, y + 5);

                    // Progress Bar Kerja
                    ctx.fillStyle = "#111827";
                    ctx.fillRect(x - 40, y + 15, 80, 10);
                    ctx.fillStyle = prog >= 100 ? "#10b981" : "#f59e0b";
                    ctx.fillRect(x - 40, y + 15, (80 * (prog / 100)), 10);

                    // Ikon Operator 👤
                    ctx.fillStyle = "#1f2937";
                    ctx.font = "16px Arial";
                    ctx.fillText("👤", x, y - 45);

                    globalIndex++;
                }});

                // 3. Stasiun Sisi BAWAH
                bottomStations.forEach((stn, i) => {{
                    let x = 90 + i * colWidth;
                    let y = 375;
                    let prog = stationProgress[globalIndex];

                    // Kotak Meja Operator
                    ctx.fillStyle = stn.is_bottleneck ? "#ef4444" : "#3b82f6";
                    ctx.fillRect(x - 48, y - 35, 96, 70);
                    ctx.strokeStyle = "#000";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 48, y - 35, 96, 70);

                    // Teks Nama & CT
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 12px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(stn.name, x, y - 12);
                    ctx.font = "11px Arial";
                    ctx.fillText("CT: " + stn.ct.toFixed(1) + "s", x, y + 5);

                    // Progress Bar Kerja
                    ctx.fillStyle = "#111827";
                    ctx.fillRect(x - 40, y + 15, 80, 10);
                    ctx.fillStyle = prog >= 100 ? "#10b981" : "#f59e0b";
                    ctx.fillRect(x - 40, y + 15, (80 * (prog / 100)), 10);

                    // Ikon Operator 👤
                    ctx.fillStyle = "#1f2937";
                    ctx.font = "16px Arial";
                    ctx.fillText("👤", x, y + 52);

                    globalIndex++;
                }});

                // 4. Sepatu (👟) Berjalan di Konveyor Tengah
                let currentShoeX = 70 + (shoePos % (canvas.width - 140));
                ctx.fillStyle = "#10b981";
                ctx.beginPath();
                ctx.arc(currentShoeX, 230, 20, 0, Math.PI * 2);
                ctx.fill();
                ctx.strokeStyle = "#047857";
                ctx.lineWidth = 3;
                ctx.stroke();

                ctx.fillStyle = "#ffffff";
                ctx.font = "15px Arial";
                ctx.textAlign = "center";
                ctx.fillText("👟", currentShoeX, 235);
            }}

            function update() {{
                if (!isRunning) return;
                
                timeElapsed += 0.1;
                shoePos += 1.5;

                stations.forEach((stn, idx) => {{
                    let speedIncrement = (0.1 / stn.ct) * 100;
                    stationProgress[idx] += speedIncrement;
                    
                    if (stationProgress[idx] >= 100) {{
                        stationProgress[idx] = 0; 
                    }}
                }});

                timerDisplay.innerText = "⏱️ Timer Berjalan: " + timeElapsed.toFixed(1) + " Detik";
                
                drawScene();
                animationId = requestAnimationFrame(update);
            }}

            function startSimulation() {{
                if (!isRunning) {{
                    isRunning = true;
                    update();
                }}
            }}

            function pauseSimulation() {{
                isRunning = false;
                cancelAnimationFrame(animationId);
            }}

            function resetSimulation() {{
                pauseSimulation();
                timeElapsed = 0;
                shoePos = 0;
                stationProgress = stations.map(() => 0);
                timerDisplay.innerText = "⏱️ Timer: 0.0 Detik";
                drawScene();
            }}

            drawScene();
        </script>
    </body>
    </html>
    """

    # Mengatur tinggi Streamlit component iframe agar lebih luas (540px) sehingga tombol play tidak terpotong
    st.components.v1.html(html_code, height=540, scrolling=False)

    # --- STEP 3: YAMAZUMI CHART ---
    st.markdown("---")
    st.subheader("3. Yamazumi Chart (Analisis Cycle Time vs Takt Time)")
    
    import plotly.graph_objects as go
    fig_bar = go.Figure()
    colors = ['#EF4444' if i == bottleneck_idx else '#3B82F6' for i in range(len(df))]

    fig_bar.add_trace(go.Bar(
        x=df["Nama Proses"],
        y=df["Effective CT (s)"],
        text=[f"{ct:.1f}s" for ct in df["Effective CT (s)"]],
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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_video_fixed")
