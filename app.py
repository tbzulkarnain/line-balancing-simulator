import streamlit as st
import pandas as pd
import json
import math
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Line Balancing Simulator", layout="wide")

# --- VISITOR COUNTER LOGIC (FILE-BASED PERSISTENT ACROSS REFRESHES) ---
counter_file = "visitor_count.txt"

if "visited_session" not in st.session_state:
    st.session_state.visited_session = True
    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r") as f:
                current_count = int(f.read().strip())
        except:
            current_count = 1175
        current_count += 1
    else:
        current_count = 1176
    
    # Simpan kembali ke file
    with open(counter_file, "w") as f:
        f.write(str(current_count))
    
    st.session_state.visitor_count = current_count
else:
    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r") as f:
                st.session_state.visitor_count = int(f.read().strip())
        except:
            st.session_state.visitor_count = 1175
    else:
        st.session_state.visitor_count = 1175

formatted_visitors = f"{st.session_state.visitor_count:05d}"
digits_html = "".join([
    f'<span style="display:inline-block; background:linear-gradient(180deg, #e2e8f0 0%, #ffffff 50%, #cbd5e1 100%); border:1px solid #94a3b8; border-radius:3px; padding:2px 6px; margin:0 1px; font-family:monospace; font-weight:bold; font-size:16px; color:#0f172a; box-shadow:inset 0 1px 2px rgba(0,0,0,0.1);">{d}</span>'
    for d in formatted_visitors
])

# --- HEADER & VISITOR COUNTER DI UJUNG KANAN ATAS ---
col_title, col_vis = st.columns([4, 1])
with col_title:
    st.title("🏭 Production Line Balancing Simulator")
    st.caption("Real-time line simulation: Target Demand/Hour, FX Rate, Labor Cost in USD ($), & IE Metrics.")

with col_vis:
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <div style="font-size: 11px; font-weight: bold; color: #475569; letter-spacing: 1px; margin-bottom: 4px;">VISITORS</div>
        <div>{digits_html}</div>
    </div>
    """, unsafe_allow_html=True)

# --- PRODUCTION PARAMETERS ---
st.markdown("### ⚙️ Production Line Parameters")
col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    target_demand_per_hour = st.number_input("Target Production (Pairs/Hour)", value=300, step=5, key="input_demand_hour")
with col_p2:
    monthly_salary_idr = st.number_input("Monthly Salary per Operator (IDR)", value=5500000.0, step=100000.0, format="%.2f", key="input_monthly_salary_idr")
with col_p3:
    fx_rate = st.number_input("FX Rate (IDR to USD)", value=17000.0, step=100.0, format="%.2f", key="input_fx_rate")

takt_time_sec = 3600 / target_demand_per_hour if target_demand_per_hour > 0 else 0
st.info(f"⏱️ **Target Takt Time**: {takt_time_sec:.2f} s/pair | **Working Hours**: 173 Hours/Month | **FX**: 1 USD = Rp{fx_rate:,.0f}")

# --- STEP 1: SINGLE INPUT TABLE ---
st.markdown("---")
st.subheader("1. Process Input Data & Actual MP Configuration")
st.write("Enter Process Name, Base CT, and Allowance. **Actual MP** auto-calculates (rounded up) and can be adjusted manually.")

if "line_data" not in st.session_state:
    st.session_state.line_data = pd.DataFrame({
        "Nama Proses": ["st collar lining", "st tip", "st counter", "hotmelt", "st margin", "punching", "insert lace"],
        "Cycle Time Base (s)": [10.0, 35.0, 12.0, 18.0, 17.0, 15.0, 15.0],
        "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    })

temp_df = st.session_state.line_data.copy()
temp_df["Standard Time (s)"] = temp_df["Cycle Time Base (s)"] * (1 + temp_df["Allowance (%)"] / 100)

temp_df["Auto MP"] = temp_df["Standard Time (s)"].apply(lambda st_val: max(1, math.ceil(st_val / takt_time_sec)) if takt_time_sec > 0 else 1)
temp_df["Actual MP"] = temp_df["Auto MP"]

edited_df = st.data_editor(
    temp_df[["Nama Proses", "Cycle Time Base (s)", "Allowance (%)", "Standard Time (s)", "Actual MP"]],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nama Proses": st.column_config.TextColumn("Process Name", required=True),
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
    
    # 1. Manpower Utilization
    df["Theoretical MP"] = df["Standard Time (s)"] / takt_time_sec
    total_theo_mp = df["Theoretical MP"].sum()
    total_actual_mp = df["Actual MP"].sum()
    mp_utilization = (total_theo_mp / total_actual_mp) * 100 if total_actual_mp > 0 else 0

    # 2. Bottleneck & Line Efficiency
    max_ct = df["Effective CT (s)"].max()
    bottleneck_idx = df["Effective CT (s)"].idxmax()
    bottleneck_process = df.loc[bottleneck_idx, "Nama Proses"]
    
    total_effective_ct = df["Effective CT (s)"].sum()
    num_stations = len(df)
    line_efficiency = (total_effective_ct / (max_ct * num_stations)) * 100

    # 3. Labor Productivity & Labor Cost per Pair (in USD $)
    labor_productivity = target_demand_per_hour / total_actual_mp if total_actual_mp > 0 else 0
    
    monthly_working_hours = 173.0
    monthly_salary_usd = monthly_salary_idr / fx_rate if fx_rate > 0 else 0
    hourly_salary_usd = monthly_salary_usd / monthly_working_hours if monthly_working_hours > 0 else 0
    total_hourly_labor_cost_usd = total_actual_mp * hourly_salary_usd
    labor_cost_per_pair_usd = total_hourly_labor_cost_usd / target_demand_per_hour if target_demand_per_hour > 0 else 0

    # METRICS SUMMARY
    st.markdown("---")
    st.subheader("📊 Key Performance Indicators (KPIs)")
    
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    row1_c1.metric("🎯 MP Utilization", f"{mp_utilization:.1f}%")
    row1_c2.metric("📊 Line Efficiency", f"{line_efficiency:.1f}%")
    row1_c3.metric("🚨 Bottleneck", f"{bottleneck_process}", delta=f"{max_ct:.1f} s/pair", delta_color="inverse")

    row2_c1, row2_c2, row2_c3 = st.columns(3)
    row2_c1.metric("👥 Total Manpower", f"{total_actual_mp} Persons")
    row2_c2.metric("⚡ Labor Productivity", f"{labor_productivity:.1f} Pairs/P/H")
    row2_c3.metric("💰 Labor Cost / Pair", f"${labor_cost_per_pair_usd:,.2f} USD")

    # --- STEP 2: CANVAS ANIMATION ---
    st.markdown("---")
    st.subheader("2. 🎬 Shoe Production Line Simulation (One-Piece Flow)")
    st.caption("Simulation runs for 1 Hour (3600 Seconds). Clean conveyor view with orthogonal motion and accurate WIP/queue count badges.")

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
                gap: 16px;
                flex-wrap: wrap;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
            }}
            .speed-control {{
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
                font-weight: bold;
                color: #1e293b;
            }}
            .speed-control input {{
                cursor: pointer;
            }}
            button {{
                background-color: #2563eb;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 13px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: background-color 0.2s;
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
            button.record {{
                background-color: #059669;
            }}
            button.record:hover {{
                background-color: #047857;
            }}
            button.recording-active {{
                background-color: #ea580c;
                animation: pulse 1.2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.7; }}
                100% {{ opacity: 1; }}
            }}
        </style>
    </head>
    <body>
        <div id="canvas-container">
            <h4 id="timer-display" style="margin: 0 0 6px 0; color: #1e293b; font-size: 14px;">⏱️ Simulation Time: 0.0s / 3600.0s (1 Hour)</h4>
            <canvas id="simCanvas" width="1040" height="260"></canvas>
            <div class="panel">
                <div class="controls">
                    <button onclick="startSimulation()">▶ Play</button>
                    <button onclick="pauseSimulation()">⏸ Pause</button>
                    <button class="reset" onclick="resetSimulation()">🔄 Reset</button>
                    <div class="speed-control">
                        <span>⚡ Speed: <span id="speed-val">20</span>x</span>
                        <input type="range" id="speedRange" min="1" max="50" value="20" step="1" oninput="updateSpeed(this.value)">
                    </div>
                    <button id="record-btn" class="record" onclick="toggleRecording()">🎥 Record 2m Clip</button>
                </div>
            </div>
        </div>

        <script>
            const stations = {stations_json};
            const taktTime = {takt_val};
            const MAX_TIME = 3600.0;

            const canvas = document.getElementById("simCanvas");
            const ctx = canvas.getContext("2d");
            const timerDisplay = document.getElementById("timer-display");
            const recordBtn = document.getElementById("record-btn");
            const speedValSpan = document.getElementById("speed-val");
            const speedRangeInput = document.getElementById("speedRange");

            if (!window.simState) {{
                window.simState = {{
                    timeElapsed: 0.0,
                    isRunning: false,
                    isFinished: false,
                    products: [],
                    finishedCount: 0,
                    spawnTimer: 0.0,
                    lastTimestamp: null,
                    speedMultiplier: 20.0
                }};
            }} else {{
                speedRangeInput.value = window.simState.speedMultiplier;
                speedValSpan.innerText = window.simState.speedMultiplier;
            }}

            let mediaRecorder = null;
            let recordedChunks = [];
            let isRecording = false;
            let recordTimeout = null;
            let recordCountdownInterval = null;

            const nStations = stations.length;
            const colSpacing = (canvas.width - 30) / Math.max(1, nStations);
            const tableWidth = Math.max(13, Math.min(32, colSpacing * 0.7));
            const tableHeight = Math.max(26, Math.min(42, tableWidth * 1.3));
            const fontSize = Math.max(9, Math.min(12, Math.floor(11 * (10 / Math.max(8, nStations)))));

            function updateSpeed(val) {{
                window.simState.speedMultiplier = parseFloat(val);
                speedValSpan.innerText = val;
            }}

            function getStationCoords(i) {{
                let isTop = (i % 2 === 0);
                let x = 15 + i * colSpacing + (colSpacing / 2);
                let tableY = isTop ? 68 : 192;
                return {{ x: x, tableY: tableY, isTop: isTop }};
            }}

            function drawScene() {{
                ctx.fillStyle = "#dcedc8";
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Konveyor Utama
                ctx.fillStyle = "#f1f8e9";
                ctx.strokeStyle = "#1f2937";
                ctx.lineWidth = 1.5;
                ctx.fillRect(8, 105, canvas.width - 16, 50);
                ctx.strokeRect(8, 105, canvas.width - 16, 50);

                stations.forEach(function(stn, i) {{
                    let pos = getStationCoords(i);
                    let x = pos.x;
                    let tableY = pos.tableY;
                    let isTop = pos.isTop;

                    // Meja Operator
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

                    // Operator Icon
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

                    // Hitung total sepatu yang terkait di stasiun ini (working + fetching + conveyor_wait antre)
                    let uniqueProcesses = [...new Set(stations.map(s => s.process_name))];
                    let stnProcessName = stn.process_name;
                    let processIndex = uniqueProcesses.indexOf(stnProcessName);

                    let countAtStation = window.simState.products.filter(p => {{
                        if (p.currentStationIdx === i && (p.status === 'working' || p.status === 'fetching_x' || p.status === 'fetching_y')) {{
                            return true;
                        }}
                        if (p.currentProcessStep === processIndex && (p.status === 'conveyor_wait' || p.status === 'conveyor')) {{
                            let candidateStations = stations.map((s, idx) => ({{...s, idx}})).filter(s => s.process_name === stnProcessName);
                            if (candidateStations[0].idx === i) {{
                                return true;
                            }}
                        }}
                        return false;
                    }}).length;

                    if (countAtStation > 0) {{
                        ctx.fillStyle = stn.is_bottleneck ? "#dc2626" : "#047857";
                        ctx.beginPath();
                        ctx.roundRect(x + (tableWidth/2 + 2), tableY - 9, 24, 12, 2);
                        ctx.fill();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 9px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText("👟" + countAtStation, x + (tableWidth/2 + 14), tableY - 1);
                    }}
                }});

                // Render produk sepatu
                window.simState.products.forEach(function(prod) {{
                    let isQueued = (prod.status === 'queued' || prod.status === 'conveyor_wait');
                    ctx.fillStyle = isQueued ? "#fee2e2" : "#ffffff";
                    ctx.strokeStyle = isQueued ? "#dc2626" : "#1f2937";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.roundRect(prod.x - 8, prod.y - 8, 16, 16, 2);
                    ctx.fill();
                    ctx.stroke();

                    ctx.font = "10px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText("👟", prod.x, prod.y + 4);

                    if (prod.status === 'working') {{
                        let stn = stations[prod.currentStationIdx];
                        let pos = getStationCoords(prod.currentStationIdx);
                        let prog = Math.min(100, (prod.workElapsed / stn.std_time) * 100);
                        ctx.fillStyle = "#1e293b";
                        ctx.fillRect(pos.x - 9, pos.tableY + 9, 18, 2.5);
                        ctx.fillStyle = "#10b981";
                        ctx.fillRect(pos.x - 9, pos.tableY + 9, 18 * (prog / 100), 2.5);
                    }}
                }});

                let totalWipInLine = window.simState.products.length;
                ctx.fillStyle = "#111827";
                ctx.font = "bold 11px Arial";
                ctx.textAlign = "left";
                ctx.fillText("⏱️ Time: " + window.simState.timeElapsed.toFixed(0) + "s   |   📦 Output: " + window.simState.finishedCount + " Pairs   |   🔄 WIP: " + totalWipInLine + " Pairs" + (window.simState.isFinished ? " — ✅ COMPLETED" : ""), 10, 252);
                
                timerDisplay.innerText = "⏱️ Simulation Time: " + window.simState.timeElapsed.toFixed(1) + "s / 3600.0s (Speed: " + window.simState.speedMultiplier + "x)" + (window.simState.isFinished ? " — Completed!" : "");
            }}

            function update(timestamp) {{
                if (!window.simState.isRunning) return;

                if (!window.simState.lastTimestamp) window.simState.lastTimestamp = timestamp;
                let deltaTime = (timestamp - window.simState.lastTimestamp) / 1000;
                window.simState.lastTimestamp = timestamp;

                let adjustedDelta = deltaTime * window.simState.speedMultiplier;
                window.simState.timeElapsed += adjustedDelta;

                if (window.simState.timeElapsed >= MAX_TIME) {{
                    window.simState.timeElapsed = MAX_TIME;
                    window.simState.isRunning = false;
                    window.simState.isFinished = true;
                    drawScene();
                    if (isRecording) stopRecording();
                    return;
                }}

                window.simState.spawnTimer += adjustedDelta;

                if (window.simState.spawnTimer >= Math.max(1.0, taktTime)) {{
                    window.simState.spawnTimer = 0;
                    window.simState.products.push({{
                        id: Math.random(),
                        x: 12,
                        y: 130,
                        status: 'conveyor',
                        currentProcessStep: 0,
                        currentStationIdx: -1,
                        workElapsed: 0
                    }});
                }}

                let uniqueProcesses = [...new Set(stations.map(s => s.process_name))];

                window.simState.products.forEach(function(prod, idx) {{
                    let targetProcName = uniqueProcesses[prod.currentProcessStep];
                    let candidateStations = stations.map((s, i) => Object.assign({{}}, s, {{ idx: i }})).filter(s => s.process_name === targetProcName);
                    
                    let availableStation = candidateStations.find(cs => !window.simState.products.some(p => p.currentStationIdx === cs.idx && (p.status === 'working' || p.status === 'fetching_x' || p.status === 'fetching_y' || p.status === 'returning_y' || p.status === 'returning_x')));

                    if (prod.status === 'conveyor' || prod.status === 'conveyor_wait') {{
                        if (availableStation) {{
                            prod.currentStationIdx = availableStation.idx;
                            let targetPos = getStationCoords(availableStation.idx);
                            
                            prod.targetX = targetPos.x;
                            prod.targetY = targetPos.tableY;
                            prod.status = 'fetching_x';
                        }} else {{
                            let firstStationOfProc = candidateStations[0];
                            let targetPos = getStationCoords(firstStationOfProc.idx);
                            
                            let aheadCount = 0;
                            for (let j = 0; j < idx; j++) {{
                                if (window.simState.products[j].currentProcessStep === prod.currentProcessStep && (window.simState.products[j].status === 'conveyor_wait' || window.simState.products[j].status === 'conveyor')) {{
                                    aheadCount++;
                                }}
                            }}

                            let stopX = targetPos.x - (aheadCount * 22) - 15;
                            if (stopX < 12) stopX = 12;

                            prod.y = 130;
                            if (prod.x < stopX) {{
                                prod.x += 100 * adjustedDelta;
                                if (prod.x >= stopX) {{
                                    prod.x = stopX;
                                    prod.status = 'conveyor_wait';
                                }} else {{
                                    prod.status = 'conveyor';
                                }}
                            }} else {{
                                prod.x = stopX;
                                prod.status = 'conveyor_wait';
                            }}
                        }}
                    }} else if (prod.status === 'fetching_x') {{
                        let moveStep = 200 * adjustedDelta;
                        if (Math.abs(prod.targetX - prod.x) <= moveStep) {{
                            prod.x = prod.targetX;
                            prod.status = 'fetching_y';
                        }} else {{
                            prod.x += (prod.targetX > prod.x) ? moveStep : -moveStep;
                        }}
                        prod.y = 130;
                    }} else if (prod.status === 'fetching_y') {{
                        let moveStep = 200 * adjustedDelta;
                        if (Math.abs(prod.targetY - prod.y) <= moveStep) {{
                            prod.y = prod.targetY;
                            prod.status = 'working';
                            prod.workElapsed = 0;
                        }} else {{
                            prod.y += (prod.targetY > prod.y) ? moveStep : -moveStep;
                        }}
                    }} else if (prod.status === 'working') {{
                        let stn = stations[prod.currentStationIdx];
                        prod.workElapsed += adjustedDelta;

                        if (prod.workElapsed >= stn.std_time) {{
                            prod.currentProcessStep++;
                            if (prod.currentProcessStep >= uniqueProcesses.length) {{
                                window.simState.finishedCount++;
                                prod.status = 'finished';
                            }} else {{
                                prod.status = 'returning_y';
                            }}
                        }}
                    }} else if (prod.status === 'returning_y') {{
                        let moveStep = 200 * adjustedDelta;
                        let targetY = 130;
                        if (Math.abs(targetY - prod.y) <= moveStep) {{
                            prod.y = targetY;
                            prod.status = 'conveyor';
                            prod.workElapsed = 0;
                        }} else {{
                            prod.y += (targetY > prod.y) ? moveStep : -moveStep;
                        }}
                    }}
                }});

                window.simState.products = window.simState.products.filter(p => p.status !== 'finished');

                drawScene();
                window.requestAnimationFrame(update);
            }}

            function startSimulation() {{
                if (!window.simState.isRunning && !window.simState.isFinished) {{
                    window.simState.isRunning = true;
                    window.simState.lastTimestamp = null;
                    window.requestAnimationFrame(update);
                }}
            }}

            function pauseSimulation() {{
                window.simState.isRunning = false;
                window.simState.lastTimestamp = null;
            }}

            function resetSimulation() {{
                if (isRecording) stopRecording();
                pauseSimulation();
                window.simState.timeElapsed = 0;
                window.simState.finishedCount = 0;
                window.simState.spawnTimer = 0;
                window.simState.products = [];
                window.simState.isFinished = false;
                window.simState.lastTimestamp = null;
                drawScene();
            }}

            function toggleRecording() {{
                if (!isRecording) {{
                    startRecording();
                }} else {{
                    stopRecording();
                }}
            }}

            function startRecording() {{
                if (!window.simState.isRunning && !window.simState.isFinished) {{
                    startSimulation();
                }}
                
                recordedChunks = [];
                const stream = canvas.captureStream(30);
                
                let options = {{ mimeType: 'video/webm; codecs=vp9' }};
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {{
                    options = {{ mimeType: 'video/webm' }};
                }}

                try {{
                    mediaRecorder = new MediaRecorder(stream, options);
                }} catch (e) {{
                    mediaRecorder = new MediaRecorder(stream);
                }}

                mediaRecorder.ondataavailable = function(event) {{
                    if (event.data.size > 0) {{
                        recordedChunks.push(event.data);
                    }}
                }};

                mediaRecorder.onstop = function() {{
                    const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'line_balancing_simulation_clip.webm';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(() => {{
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    }}, 100);
                }};

                mediaRecorder.start();
                isRecording = true;
                recordBtn.classList.add("recording-active");

                let secondsLeft = 120;
                recordBtn.innerText = "⏹ Stop Rec (" + Math.floor(secondsLeft/60) + "m " + (secondsLeft%60) + "s)";

                recordCountdownInterval = setInterval(() => {{
                    secondsLeft--;
                    if (secondsLeft > 0) {{
                        let m = Math.floor(secondsLeft / 60);
                        let s = secondsLeft % 60;
                        recordBtn.innerText = "⏹ Stop Rec (" + m + "m " + s + "s)";
                    }}
                }}, 1000);

                recordTimeout = setTimeout(() => {{
                    if (isRecording) stopRecording();
                }}, 120000);
            }}

            function stopRecording() {{
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                    mediaRecorder.stop();
                }}
                isRecording = false;
                clearTimeout(recordTimeout);
                clearInterval(recordCountdownInterval);
                recordBtn.classList.remove("recording-active");
                recordBtn.innerText = "🎥 Record 2m Clip";
            }}

            drawScene();
            if (window.simState.isRunning) {{
                window.requestAnimationFrame(update);
            }}
        </script>
    </body>
    </html>
    """

    st.components.v1.html(html_code, height=415, scrolling=False)

    # --- STEP 3: YAMAZUMI CHART ---
    st.markdown("---")
    st.subheader("3. Yamazumi Chart (Effective CT vs Takt Time Analysis)")
    
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
        annotation_text=f"Target Takt Time ({takt_time_sec:.1f}s)"
    )

    fig_bar.update_layout(height=380, template="plotly_white")
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_final_v17")

    # --- STEP 4: INDUSTRIAL ENGINEERING (IE) EXECUTIVE SUMMARY ---
    st.markdown("---")
    st.subheader("📋 4. Industrial Engineering (IE) Executive Summary")
    
    st.markdown(f"""
    * **Bottleneck Identification & Action**: Process **`{bottleneck_process}`** acts as the primary constraint with an Effective CT of **`{max_ct:.2f}s`**. Instead of adding headcount (which degrades MP utilization), prioritize **method engineering** or **operator upskilling** to reduce cycle time.
    * **Key Performance Indicators (KPIs & Cost)**:
      * **Manpower Utilization**: **`{mp_utilization:.1f}%`** *(Recommended standard: **$\ge$ 85%**).* If below target, optimize work allocation rather than adding workers.
      * **Line Efficiency**: **`{line_efficiency:.1f}%`** *(Cycle time balance across stations).*
      * **Labor Productivity**: **`{labor_productivity:.1f} Pairs/Person/Hour`**.
      * **Labor Cost per Pair**: **`${labor_cost_per_pair_usd:,.2f} USD`** *(Calculated from monthly salary of Rp{monthly_salary_idr:,.0f}, FX rate of Rp{fx_rate:,.0f}, standard divider of **173 hours/month**, total manpower of `{total_actual_mp}`, and target production rate).*
    """)
