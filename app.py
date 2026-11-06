import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Production Line Flow & Balancing Simulator", layout="wide")

st.title("🏭 Production Line Balancing & Real-Time Flow Simulator")
st.caption("Simulasi alur produksi nyata, kalkulasi MP otomatis, dan analisis bottleneck presisi")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Target & Waktu")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

# Calculate Takt Time (in seconds)
takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

st.markdown("---")

# --- STEP 1: INPUT DATA ---
st.subheader("1. Data Input Proses Produksi")
st.write("Isi nama proses, cycle time dasar, dan allowance. **Required MP** dihitung otomatis oleh sistem, lalu user mengisi **Actual MP** di kolom sebelah.")

# Default data awal
default_data = pd.DataFrame({
    "Nama Proses": ["Cutting Prep", "Stitching A", "Stitching B", "Assembly", "Quality Control", "Packing"],
    "Cycle Time Base (s)": [30.0, 55.0, 70.0, 40.0, 25.0, 20.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 1, 2, 1, 1, 1] # Kolom yang diisi user
})

# Tabel Interaktif
edited_df = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nama Proses": st.column_config.TextColumn("Nama Proses", required=True),
        "Cycle Time Base (s)": st.column_config.NumberColumn("CT Base (s)", min_value=0.1, format="%.2f"),
        "Allowance (%)": st.column_config.NumberColumn("Allowance (%)", min_value=0.0, max_value=100.0, format="%.1f"),
        "Actual MP": st.column_config.NumberColumn("Actual MP (Isi User)", min_value=1, step=1, required=True)
    }
)

if not edited_df.empty and takt_time_sec > 0:
    df = edited_df.copy()
    
    # 1. Standard Time = Base CT * (1 + Allowance/100)
    df["Standard Time (s)"] = df["Cycle Time Base (s)"] * (1 + df["Allowance (%)"] / 100)
    
    # 2. Required MP (Kalkulasi Otomatis Sistem) = Standard Time / Takt Time
    df["Required MP (Calc)"] = df["Standard Time (s)"] / takt_time_sec
    
    # 3. Effective CT per Station = Standard Time / Actual MP
    df["Effective CT (s)"] = df["Standard Time (s)"] / df["Actual MP"]
    
    # Identifikasi Bottleneck
    max_ct = df["Effective CT (s)"].max()
    bottleneck_idx = df["Effective CT (s)"].idxmax()
    bottleneck_process = df.loc[bottleneck_idx, "Nama Proses"]
    
    total_std_time = df["Standard Time (s)"].sum()
    total_effective_ct = df["Effective CT (s)"].sum()
    total_actual_mp = df["Actual MP"].sum()
    num_stations = len(df)
    
    # Metrics
    balancing_rate = (total_effective_ct / (max_ct * num_stations)) * 100
    balance_delay = 100 - balancing_rate
    
    # --- STEP 2: SUMMARY METRICS & OUTPUT SIMULATOR (WAKTU TERTENTU) ---
    st.markdown("---")
    st.subheader("2. Ringkasan Kinerja & Estimasi Output Waktu")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Balancing Rate", f"{balancing_rate:.2f}%")
    col2.metric("🚨 Bottleneck Station", f"{bottleneck_process}", delta=f"{max_ct:.1f} s/pcs", delta_color="inverse")
    col3.metric("👥 Total Actual MP", f"{total_actual_mp} Orang")
    col4.metric("📦 Max Output / Jam", f"{int(3600 / max_ct)} pcs")

    # Simulasi Output Berdasarkan Menit Setup (Misal 10 Menit, 30 Menit, atau 1 Shift)
    st.info("💡 **Kalkulator Kapasitas Output Berdasarkan Waktu Nyata (Bottleneck-Controlled):**")
    sim_time_minutes = st.slider("Pilih Durasi Waktu Simulasi (Menit):", min_value=1, max_value=480, value=10, step=5)
    
    # Output dibatasi oleh stasiun paling lambat (Bottleneck)
    seconds_available = sim_time_minutes * 60
    est_output_units = int(seconds_available / max_ct) if max_ct > 0 else 0
    
    col_a, col_b = st.columns(2)
    col_a.metric(f"⏱️ Waktu Berjalan ({sim_time_minutes} Menit)", f"{seconds_available:,} Detik")
    col_b.metric(f"🚀 Estimasi Total Output Tercapai", f"{est_output_units} Pcs", delta=f"Rata-rata {est_output_units/sim_time_minutes:.2f} pcs/menit")

    # --- STEP 3: GRAFIK YAMAZUMI ---
    st.markdown("---")
    st.subheader("3. Grafik Analisis Beban Kerja vs Takt Time")

    fig = go.Figure()
    colors = ['#FF4B4B' if i == bottleneck_idx else '#00C0F2' for i in range(len(df))]

    fig.add_trace(go.Bar(
        x=df["Nama Proses"],
        y=df["Effective CT (s)"],
        text=[f"Req: {req_mp:.1f}<br>Act: {act_mp} MP<br>({ct:.1f}s)" for req_mp, act_mp, ct in zip(df["Required MP (Calc)"], df["Actual MP"], df["Effective CT (s)"])],
        textposition='auto',
        marker_color=colors,
        name="Effective CT"
    ))

    fig.add_hline(
        y=takt_time_sec, 
        line_dash="dash", 
        line_color="red", 
        annotation_text=f"Takt Time Target ({takt_time_sec:.1f}s)", 
        annotation_position="top right"
    )

    fig.update_layout(
        title="Effective Cycle Time per Station (Dibandingkan Takt Time)",
        xaxis_title="Alur Proses Produksi",
        yaxis_title="Waktu Siklus Efektif (Detik)",
        template="plotly_white",
        height=420
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- STEP 4: ANIMASI KONVEYOR / MEJA ALIRAN PRODUKSI NYATA ---
    st.markdown("---")
    st.subheader("4. 🎬 Animasi Meja Aliran Produksi (Conveyor Flow Simulation)")
    st.write("Simulasi ini memperlihatkan pergerakan barang secara visual dari stasiun ke stasiun berdasarkan Cycle Time aktual. Anda bisa melihat di mana barang menumpuk (*Bottleneck*).")

    if st.button("▶️ Mulai Simulasi Meja Konveyor"):
        sim_container = st.container()
        
        with sim_container:
            st.write("🔄 **Status Aliran Barang di Jalur Produksi (Real-Time Simulation Steps):**")
            
            # Buat placeholder visual untuk tiap proses (seperti kotak stasiun kerja di pabrik)
            station_cols = st.columns(len(df))
            station_boxes = []
            
            for idx, col in enumerate(station_cols):
                p_name = df.iloc[idx]["Nama Proses"]
                with col:
                    st.markdown(f"**Stasiun {idx+1}**")
                    box = st.empty()
                    station_boxes.append(box)

            log_box = st.empty()
            
            # Jalankan simulasi pergerakan barang selama beberapa siklus simulasi
            num_cycles_sim = 5
            for cycle in range(1, num_cycles_sim + 1):
                log_box.markdown(f"🔹 **Siklus Produksi ke-{cycle} Berjalan...**")
                
                # Simulasi bertahap dari proses pertama ke terakhir
                for step in range(len(df)):
                    p_name = df.iloc[step]["Nama Proses"]
                    ct_eff = df.iloc[step]["Effective CT (s)"]
                    
                    # Update status visual stasiun
                    for i, box in enumerate(station_boxes):
                        station_name = df.iloc[i]["Nama Proses"]
                        station_ct = df.iloc[i]["Effective CT (s)"]
                        
                        if i == step:
                            if station_ct == max_ct:
                                box.error(f"🚨 **{station_name}**\n\n[PROSES BERJALAN]\n⚠️ *BOTTLENECK!* (WIP Menumpuk: {station_ct:.1f}s)")
                            else:
                                box.info(f"⚙️ **{station_name}**\n\n[PROSES BERJALAN]\n⏳ {station_ct:.1f}s")
                        elif i < step:
                            box.success(f"✅ **{station_name}**\n\n[SELESAI]\n📦 Barang Terkirim")
                        else:
                            box.warning(f"⏳ **{station_name}**\n\n[MENUNGGU]\n📦 Standby WIP")
                    
                    # Kecepatan animasi disesuaikan dengan proporsi CT proses tersebut
                    time.sleep(min(max(ct_eff / 20.0, 0.1), 0.8))
                
                time.sleep(0.3)
            
            log_box.success("🎉 Simulasi Aliran Konveyor Selesai! Terlihat jelas stasiun mana yang memperlambat laju produksi.")

    # --- STEP 5: SARAN PERBAIKAN (IMPROVEMENT) ---
    st.markdown("---")
    st.subheader("5. 💡 Analisis & Rekomendasi Perbaikan")
    
    req_mp_bottleneck = df.loc[bottleneck_idx, "Required MP (Calc)"]
    act_mp_bottleneck = df.loc[bottleneck_idx, "Actual MP"]
    
    st.warning(f"""
    * **Analisis Bottleneck Utama:** Proses **{bottleneck_process}** memiliki beban tertinggi dengan CT efektif **{max_ct:.2f} detik**.
    * **Rekomendasi Manpower:** Sistem menghitung kebutuhan (*Required MP*) di stasiun ini adalah **{req_mp_bottleneck:.2f} orang**. Saat ini *Actual MP* yang dipasang adalah **{act_mp_bottleneck} orang**. 
      * *Saran:* Jika Anda menambah **Actual MP** pada proses *{bottleneck_process}* atau membagi elemen kerjanya (Line Balancing), maka *Balancing Rate* akan naik secara signifikan dan kapasitas output per waktu tertentu akan meningkat!
    """)
