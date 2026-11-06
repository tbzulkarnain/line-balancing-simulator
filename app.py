import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Line Balancing & Bottleneck Visualizer", layout="wide")

st.title("🏭 Line Balancing & Bottleneck Visualizer")
st.caption("Aplikasi simulasi alur produksi dan analisis bottleneck interaktif")

# --- SIDEBAR: OPERATIONAL PARAMETERS ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

# Calculate Takt Time (in seconds)
takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

st.markdown("---")

# --- STEP 1: INPUT DATA TABEL PROSES ---
st.subheader("1. Input Data Aliran Proses")
st.write("Silakan isi data proses, cycle time dasar, allowance, dan jumlah operator (MP).")

# Default template data
default_data = pd.DataFrame({
    "Nama Proses": ["Proses A", "Proses B", "Proses C", "Proses D", "Proses E"],
    "Cycle Time Base (detik)": [45.0, 65.0, 30.0, 80.0, 40.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0, 10.0],
    "Jumlah MP": [1, 1, 1, 1, 1]
})

# Data Editor (Tabel Interaktif Kosong / Customizable)
edited_df = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nama Proses": st.column_config.TextColumn("Nama Proses", required=True),
        "Cycle Time Base (detik)": st.column_config.NumberColumn("CT Base (s)", min_value=0.1, format="%.2f"),
        "Allowance (%)": st.column_config.NumberColumn("Allowance (%)", min_value=0.0, max_value=100.0, format="%.1f"),
        "Jumlah MP": st.column_config.NumberColumn("Manpower (MP)", min_value=1, step=1)
    }
)

if not edited_df.empty and takt_time_sec > 0:
    # --- STEP 2: PERHITUNGAN LINE BALANCING ---
    df = edited_df.copy()
    
    # Standard Time per unit = Base CT * (1 + Allowance/100)
    df["Standard Time (s)"] = df["Cycle Time Base (detik)"] * (1 + df["Allowance (%)"] / 100)
    
    # Effective Cycle Time per MP = Standard Time / Jumlah MP
    df["Effective CT (s)"] = df["Standard Time (s)"] / df["Jumlah MP"]
    
    # Identification
    max_ct = df["Effective CT (s)"].max()
    bottleneck_process = df.loc[df["Effective CT (s)"] == max_ct, "Nama Proses"].values[0]
    
    total_std_time = df["Standard Time (s)"].sum()
    total_effective_ct = df["Effective CT (s)"].sum()
    total_mp = df["Jumlah MP"].sum()
    num_stations = len(df)
    
    # Line Balancing Metrics
    # Balancing Rate (%) = Total Std Time / (Bottleneck CT * Total Stations/MP) * 100
    balancing_rate = (total_effective_ct / (max_ct * num_stations)) * 100
    balance_delay = 100 - balancing_rate
    output_per_hour = 3600 / max_ct if max_ct > 0 else 0

    st.markdown("---")
    st.subheader("2. Summary Performance & Line Balancing Rate")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Balancing Rate", f"{balancing_rate:.2f}%", delta=f"{balancing_rate - 85:.1f}% vs Target 85%")
    col2.metric("⏳ Balance Delay", f"{balance_delay:.2f}%")
    col3.metric("🚨 Bottleneck Station", f"{bottleneck_process}", delta=f"{max_ct:.1f} s", delta_color="inverse")
    col4.metric("📦 Est. Output / Jam", f"{int(output_per_hour)} pcs")

    # --- STEP 3: VISUALISASI YAMAZUMI / LINE BALANCING CHART ---
    st.markdown("---")
    st.subheader("3. Grafik Balancing & Identifikasi Bottleneck")

    colors = ['#FF4B4B' if ct == max_ct else '#00C0F2' if ct > takt_time_sec else '#29B6F6' for ct in df["Effective CT (s)"]]

    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df["Nama Proses"],
        y=df["Effective CT (s)"],
        text=[f"{val:.1f}s (MP:{mp})" for val, mp in zip(df["Effective CT (s)"], df["Jumlah MP"])],
        textposition='auto',
        marker_color=colors,
        name="Effective CT"
    ))

    # Takt Time Line
    fig.add_hline(
        y=takt_time_sec, 
        line_dash="dash", 
        line_color="red", 
        annotation_text=f"Takt Time ({takt_time_sec:.1f}s)", 
        annotation_position="top right"
    )

    fig.update_layout(
        title="Cycle Time per Station vs Takt Time Target",
        xaxis_title="Proses / Stasiun",
        yaxis_title="Effective Cycle Time (Detik)",
        template="plotly_white",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- STEP 4: ANIMASI STREAM SIMULASI FLOW PRODUKSI ---
    st.markdown("---")
    st.subheader("4. 🎬 Animasi Live Aliran Produksi & Penumpukan WIP")
    st.write("Tekan tombol di bawah untuk melihat simulasi pergerakan unit dan titik penumpukan barang (bottleneck).")

    if st.button("▶️ Jalankan Animasi Simulation Flow"):
        progress_placeholders = {row["Nama Proses"]: st.empty() for _, row in df.iterrows()}
        status_placeholders = {row["Nama Proses"]: st.empty() for _, row in df.iterrows()}
        
        # Simulation Loop (10 Cycles)
        for cycle in range(1, 11):
            st.caption(f"Loop Simulasi Run ke-{cycle}/10")
            for idx, row in df.iterrows():
                p_name = row["Nama Proses"]
                ct_eff = row["Effective CT (s)"]
                
                # Visual indikator load
                load_ratio = ct_eff / takt_time_sec
                
                if load_ratio > 1.0:
                    status_text = f"🚨 **{p_name}** [BOTTLENECK] - Penumpukan WIP terjadi!"
                else:
                    status_text = f"✅ **{p_name}** - Flow Lancar"
                
                status_placeholders[p_name].markdown(status_text)
                
                # Animasi progress bar disesuaikan dengan durasi relatif CT
                sim_speed = ct_eff / max_ct # Normalisasi waktu simulasi
                for p in range(0, 101, 20):
                    progress_placeholders[p_name].progress(p, text=f"{p_name} ({ct_eff:.1f}s)")
                    time.sleep(sim_speed * 0.05)
            time.sleep(0.2)
        st.success("Simulasi Selesai!")

    # --- STEP 5: RECOMMENDATION / IMPROVEMENT SUGGESTION ---
    st.markdown("---")
    st.subheader("5. 💡 Rekomendasi Improvement")
    
    st.warning(f"""
    **Area Bottleneck:** Process **{bottleneck_process}** memiliki Effective Cycle Time tertinggi yaitu **{max_ct:.2f} detik**.
    
    **Saran Tindakan di Lapangan:**
    1. **Penambahan Manpower (MP)**: Coba tambahkan 1 MP pada *{bottleneck_process}* di tabel input atas untuk membagi beban kerja.
    2. **Line Balancing / Element Combining**: Transfer sebagian elemen kerja dari *{bottleneck_process}* ke stasiun dengan CT terendah.
    3. **KAIZEN / ECRS**: Lakukan analisis gerakan (*Motion Study*) pada *{bottleneck_process}* untuk menekan *Allowance* atau hilangkan *Waste*.
    """)
