import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Line Balancing Conveyor Simulator", layout="wide")

st.title("🏭 Production Line Conveyor & Station Simulator")
st.caption("Simulasi meja produksi berhadapan (Conveyor-style) dengan Takt Time counter dan Cycle Time per stasiun.")

# --- SIDEBAR: PARAMETER OPERASIONAL ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT DATA TABEL PROSES ---
st.subheader("1. Data Input Proses & Alokasi Meja Produksi")
st.write("Isi proses produksi. Sistem otomatis menyebar stasiun secara berpasangan di sisi atas dan bawah konveyor.")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting Prep", "Stitching Upper", "Stitching Tongue", "Eyestay Attach", "Assembly 1", "Assembly 2", "Outsole Cement", "Packing"],
    "Cycle Time Base (s)": [18.0, 22.0, 19.0, 25.0, 21.0, 20.0, 24.0, 17.0],
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

    # --- STEP 2: ANIMASI MEJA KONVEYOR BERHADAPAN ---
    st.markdown("---")
    st.subheader("2. 🎬 Simulasi Live Meja Aliran Konveyor Produksi")
    st.caption("Visualisasi posisi operator atas & bawah, konveyor tengah, timer detik berjalan, dan pergerakan unit sepatu sesuai Takt Time.")

    col_sim_btn, col_sim_info = st.columns([1, 3])
    with col_sim_btn:
        run_simulation = st.button("▶️ Jalankan Simulasi Konveyor", type="primary")

    if run_simulation:
        sim_placeholder = st.empty()
        timer_placeholder = st.empty()
        
        stations = df.to_dict('records')
        n_stations = len(stations)
        
        # Bagi stasiun menjadi dua sisi: Atas (Top) dan Bawah (Bottom)
        mid_point = (n_stations + 1) // 2
        top_stations = stations[:mid_point]
        bottom_stations = stations[mid_point:]
        
        total_simulation_steps = 40
        
        for step in range(total_simulation_steps):
            # Hitung waktu detik simulasi berjalan berdasarkan takt time
            current_second = int(step * (takt_time_sec / 5))
            timer_placeholder.markdown(f"### ⏱️ **Timer Berjalan: {current_second} Detik** *(Takt Time Target: {takt_time_sec:.1f}s)*")
            
            fig = go.Figure()
            
            # 1. Gambar Konveyor Tengah (Kotak Panjang Tempat Sepatu Berjalan)
            fig.add_shape(
                type="rect",
                x0=-0.5, y0=0.3, x1=max(len(top_stations), len(bottom_stations)) - 0.5, y2=1.7,
                fillcolor="#F3F4F6", line=dict(color="#374151", width=2)
            )
            
            # 2. Gambar Stasiun Sisi ATAS (Y = 2.5)
            for i, stn in enumerate(top_stations):
                is_bn = (stn["Nama Proses"] == bottleneck_process)
                box_color = "#EF4444" if is_bn else "#3B82F6"
                ct_val = stn["Effective CT (s)"]
                
                # Kotak Meja Operator Atas
                fig.add_trace(go.Scatter(
                    x=[i], y=[2.6],
                    mode="markers+text",
                    marker=dict(symbol="square", size=45, color=box_color, line=dict(width=2, color="black")),
                    text=[f"<b>{stn['Nama Proses']}</b><br>⏱️ CT: {ct_val:.1f}s"],
                    textposition="top center",
                    showlegend=False
                ))
                # Simbol Operator (Kepala 👤 di atas meja)
                fig.add_trace(go.Scatter(
                    x=[i], y=[3.3],
                    mode="text",
                    text=["👤 Operator"],
                    textposition="bottom center",
                    showlegend=False
                ))

            # 3. Gambar Stasiun Sisi BAWAH (Y = -0.6)
            for i, stn in enumerate(bottom_stations):
                is_bn = (stn["Nama Proses"] == bottleneck_process)
                box_color = "#EF4444" if is_bn else "#3B82F6"
                ct_val = stn["Effective CT (s)"]
                
                # Kotak Meja Operator Bawah
                fig.add_trace(go.Scatter(
                    x=[i], y=[-0.6],
                    mode="markers+text",
                    marker=dict(symbol="square", size=45, color=box_color, line=dict(width=2, color="black")),
                    text=[f"⏱️ CT: {ct_val:.1f}s<br><b>{stn['Nama Proses']}</b>"],
                    textposition="bottom center",
                    showlegend=False
                ))
                # Simbol Operator (Kepala 👤 di bawah meja)
                fig.add_trace(go.Scatter(
                    x=[i], y=[-1.3],
                    mode="text",
                    text=["👤 Operator"],
                    textposition="top center",
                    showlegend=False
                ))

            # 4. Pergerakan Sepatu (👟) di Konveyor Tengah Sesuai Takt Time / Step
            shoe_position = (step % max(len(top_stations), len(bottom_stations)))
            
            fig.add_trace(go.Scatter(
                x=[shoe_position], y=[1.0],
                mode="text+markers",
                marker=dict(size=25, color="#10B981", symbol="diamond"),
                text=["👟 WIP Shoebox"],
                textposition="middle center",
                showlegend=False
            ))

            # Layout Styling Grafik
            fig.update_layout(
                xaxis=dict(range=[-1, max(len(top_stations), len(bottom_stations))], showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(range=[-2.0, 4.0], showgrid=False, zeroline=False, showticklabels=False),
                height=450,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(240,253,244,0.5)"
            )

            sim_placeholder.plotly_chart(fig, use_container_width=True, key=f"conveyor_anim_{step}")
            time.sleep(0.2)

        st.success("🎉 Simulasi Aliran Konveyor Selesai!")

    # --- STEP 3: YAMAZUMI CHART ---
    st.markdown("---")
    st.subheader("3. Yamazumi Chart (Analisis Cycle Time vs Takt Time)")
    
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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart_main")
