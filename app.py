import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Line Balancing Flow Simulator", layout="wide")

st.title("🏭 Production Line Balancing & Visualizer")

# --- SIDEBAR: OPERATIONAL PARAMETERS ---
st.sidebar.header("⚙️ Parameter Operasional")
available_time_min = st.sidebar.number_input("Waktu Kerja Efektif (Menit/Shift)", value=480, step=10)
target_demand = st.sidebar.number_input("Target Production (Pcs/Shift)", value=400, step=10)

takt_time_sec = (available_time_min * 60) / target_demand if target_demand > 0 else 0
st.sidebar.metric(label="⏱️ Takt Time Target", value=f"{takt_time_sec:.2f} det/pcs")

# --- STEP 1: INPUT TABEL PROSES ---
st.subheader("1. Data Input Proses & Manpower")

default_data = pd.DataFrame({
    "Nama Proses": ["Cutting", "Sewing", "Assembly", "Packing"],
    "Cycle Time Base (s)": [30.0, 50.0, 75.0, 25.0],
    "Allowance (%)": [10.0, 10.0, 10.0, 10.0],
    "Actual MP": [1, 1, 1, 1]
})

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
    df["Standard Time (s)"] = df["Cycle Time Base (s)"] * (1 + df["Allowance (%)"] / 100)
    df["Required MP (Calc)"] = df["Standard Time (s)"] / takt_time_sec
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
    col3.metric("👥 Total Actual MP", f"{df['Actual MP'].sum()} Orang")
    col4.metric("📦 Est. Output / Jam", f"{int(3600 / max_ct)} pcs")

    # --- STEP 2: ANIMASI FLOW DENGAN SKEMA GAMBAR (CONVEYOR STREAM) ---
    st.markdown("---")
    st.subheader("2. 🎬 Visual Animasi Aliran Produksi & Bottleneck")
    st.caption("Visualisasi posisi barang (📦) bergerak dari Raw Material melintasi setiap stasiun kerja sesuai Cycle Time aktual.")

    if st.button("▶️ Jalankan Animasi Aliran Produksi"):
        anim_placeholder = st.empty()
        
        stations = list(df["Nama Proses"])
        n_stations = len(stations)
        
        x_raw = 0
        x_stations = list(range(1, n_stations + 1))
        total_steps = 50
        
        for step in range(total_steps):
            fig = go.Figure()

            # 1. Gambar Raw Material (Tumpukan di Kiri)
            fig.add_trace(go.Scatter(
                x=[x_raw], y=[0],
                mode="text+markers",
                marker=dict(symbol="square", size=28, color="#10B981"),
                text=["🧱 Raw Material"],
                textposition="bottom center",
                showlegend=False
            ))

            # 2. Gambar Stasiun Kerja & Panah Alur
            for i, st_name in enumerate(stations):
                ct_val = df.iloc[i]["Effective CT (s)"]
                is_bn = (i == bottleneck_idx)
                
                box_color = "#EF4444" if is_bn else "#3B82F6"
                
                fig.add_trace(go.Scatter(
                    x=[x_stations[i]], y=[0],
                    mode="markers+text",
                    marker=dict(symbol="square", size=35, color=box_color, line=dict(width=2, color="black")),
                    text=[f"⏱️ <b>{ct_val:.1f}s</b><br><br><br><b>{st_name}</b><br>(MP: {df.iloc[i]['Actual MP']})"],
                    textposition="top center",
                    showlegend=False
                ))

                # Panah Alur Antar Stasiun
                prev_x = x_raw if i == 0 else x_stations[i-1]
                fig.add_annotation(
                    x=x_stations[i] - 0.2, y=0,
                    ax=prev_x + 0.2, ay=0,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=1.5,
                    arrowwidth=2,
                    arrowcolor="#9CA3AF"
                )

            # 3. Posisi Item/Barang (📦) Bergerak
            current_pos = (step % (n_stations + 1))
            
            if current_pos > 0:
                item_x = current_pos
                fig.add_trace(go.Scatter(
                    x=[item_x], y=[0.15],
                    mode="markers+text",
                    marker=dict(symbol="square", size=20, color="#F59E0B"),
                    text=["📦 Unit WIP"],
                    textposition="top center",
                    showlegend=False
                ))

            # Styling Tampilan Plotly
            fig.update_layout(
                xaxis=dict(range=[-0.5, n_stations + 1.5], showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(range=[-0.5, 0.8], showgrid=False, zeroline=False, showticklabels=False),
                height=320,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            # Menggunakan unique key agar Streamlit tidak error Duplicate Element ID saat loop animasi
            anim_placeholder.plotly_chart(fig, use_container_width=True, key=f"anim_frame_{step}")
            time.sleep(0.15)

    # --- STEP 3: GRAFIK YAMAZUMI ---
    st.markdown("---")
    st.subheader("3. Yamazumi Chart (Cycle Time vs Takt Time)")
    
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
    st.plotly_chart(fig_bar, use_container_width=True, key="yamazumi_chart")
