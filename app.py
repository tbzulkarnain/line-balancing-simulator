import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Line Balancing Flow Simulator", layout="wide")

st.title("🏭 Production Line Flow Simulator (One-Piece Flow)")
st.caption("Simulasi aliran produksi interaktif: Barang bergerak di konveyor, ditarik oleh operator stasiun sesuai Cycle Time masing-masing.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES ---
st.subheader("1. Data Input Proses & Cycle Time")
st.write("Atur tahapan proses dan waktu siklus (*Cycle Time*) tiap stasiun kerja.")

default_data = pd.DataFrame({
    "Nama Proses": ["Insert", "Stitching", "Assembly", "Outsole", "Packing"],
    "Cycle Time Base (s)": [4.0, 6.0, 5.0, 7.0, 4.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 1, 1, 1, 1]
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

    # --- STEP 2: ANIMASI KANVAS ONE-PIECE FLOW (MENIRU CONTOH VIDEO) ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Visual Aliran Barang (One-Piece Flow)")
    st.caption("Barang berjalan di konveyor, masuk ke meja operator untuk dikerjakan sesuai Cycle Time, lalu diteruskan ke stasiun berikutnya.")

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
                background: #eef2f7;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                padding: 15px;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 1000px;
                box-sizing: border-box;
            }}
            canvas {{
                background: #ffffff;
                border-radius: 8px;
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
                padding: 10px 22px;
                font-size: 15px;
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
            <h3 id="timer-display" style="margin: 0 0 12px 0; color: #1e293b; font-size: 18px;">⏱️ Waktu Simulasi: 0.0 Detik</h3>
            <canvas id="simCanvas" width="960" height="420"></canvas>
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

            const nStations = stations.length;
            const spacing = canvas.width / (nStations + 1);

            // Status masing-masing stasiun: memegang barang atau kosong, dan progress pengerjaan
            let stationState = stations.map(function() {{
                return {{ hasItem: false, progress: 0, completed: false }};
            }});

            // Antrean barang di konveyor awal masuk
            let conveyorQueue = 3; 
            let finishedCount = 0;

            function drawScene() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // 1. Gambar Jalur Konveyor Tengah (Tempat barang mengalir)
                ctx.fillStyle = "#f1f5f9";
                ctx.strokeStyle = "#64748b";
                ctx.lineWidth = 2;
                ctx.fillRect(40, 165, canvas.width - 80, 70);
                ctx.strokeRect(40, 165, canvas.width - 80, 70);

                // Garis tengah konveyor
                ctx.strokeStyle = "#cbd5e1";
                ctx.setLineDash([8, 8]);
                ctx.beginPath();
                ctx.moveTo(40, 200);
                ctx.lineTo(canvas.width - 40, 200);
                ctx.stroke();
                ctx.setLineDash([]);

                // 2. Gambar Stasiun Kerja (Meja Operator & Indikator)
                stations.forEach(function(stn, i) {{
                    let x = spacing * (i + 1);
                    let yTop = 70;
                    let state = stationState[i];

                    // Kotak Meja Operator
                    ctx.fillStyle = stn.is_bottleneck ? "#ef4444" : "#3b82f6";
                    ctx.fillRect(x - 45, yTop - 25, 90, 50);
                    ctx.strokeStyle = "#0f172a";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x - 45, yTop - 25, 90, 50);

                    // Teks Nama Proses & CT
                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 11px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(stn.name, x, yTop - 8);
                    ctx.font = "10px Arial";
                    ctx.fillText("CT: " + stn.ct.toFixed(1) + "s", x, yTop + 10);

                    // Ikon Operator 👤 di atas meja
                    ctx.fillStyle = "#0f172a";
                    ctx.font = "14px Arial";
                    ctx.fillText("👤", x, yTop - 35);

                    // Progress bar pengerjaan di meja operator
                    ctx.fillStyle = "#e2e8f0";
                    ctx.fillRect(x - 40, yTop + 32, 80, 6);
                    if (state.hasItem) {{
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(x - 40, yTop + 32, (80 * (state.progress / 100)), 6);
                    }}

                    // Jika operator sedang memegang/mengerjakan barang (👟 / 📦)
                    if (state.hasItem) {{
                        ctx.fillStyle = "#f59e0b";
                        ctx.fillRect(x - 12, 120, 24, 24);
                        ctx.strokeStyle = "#b45309";
                        ctx.strokeRect(x - 12, 120, 24, 24);
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "12px Arial";
                        ctx.fillText("📦", x, 137);
                    }}
                }});

                // 3. Tampilkan Barang di Titik Konveyor yang Belum Masuk / Sudah Selesai
                ctx.fillStyle = "#475569";
                ctx.font = "bold 12px Arial";
                ctx.textAlign = "left";
                ctx.fillText("Total Selesai: " + finishedCount + " Pcs", 50, 370);
            }}

            function update() {{
                if (!isRunning) return;
                
                timeElapsed += 0.1;

                // Logika Aliran One-Piece Flow per Stasiun
                stations.forEach(function(stn, idx) {{
                    let state = stationState[idx];

                    if (!state.hasItem && !state.completed) {{
                        // Stasiun mengambil barang dari antrean / stasiun sebelumnya
                        if (idx === 0 || stationState[idx - 1].completed) {{
                            state.hasItem = true;
                            state.progress = 0;
                            if (idx > 0) {{
                                stationState[idx - 1].completed = false;
                                stationState[idx - 1].hasItem = false;
                            }}
                        }}
                    }} else if (state.hasItem) {{
                        // Pengerjaan barang berdasarkan cycle time stasiun tersebut
                        let increment = (0.1 / stn.ct) * 100;
                        state.progress += increment;

                        if (state.progress >= 100) {{
                            state.progress = 100;
                            // Jika stasiun terakhir selesai, hitung sebagai finished product
                            if (idx === stations.length - 1) {{
                                finishedCount++;
                                state.hasItem = false;
                                state.progress = 0;
                                // Reset untuk simulasi kontinu
                                setTimeout(function() {{
                                    stationState[0].hasItem = false;
                                }}, 200);
                            }} else {{
                                state.completed = true;
                            }}
                        }}
                    }}
                }});

                timerDisplay.innerText = "⏱️ Waktu Simulasi: " + timeElapsed.toFixed(1) + " Detik";
                
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
                finishedCount = 0;
                stationState = stations.map(function() {{
                    return {{ hasItem: false, progress: 0, completed: false }};
                }});
                timerDisplay.innerText = "⏱️ Waktu Simulasi: 0.0 Detik";
                drawScene();
            }}

            drawScene();
        </script>
    </body>
    </html>
    """

    st.components.v1.html(html_code, height=500, scrolling=False)

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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_flow")
