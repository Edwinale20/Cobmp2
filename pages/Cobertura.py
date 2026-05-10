import pandas as pd
import duckdb 
import glob
import os
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import subprocess
import zipfile
import io
import tempfile
#---------------------------------------------------------------------------------------- 
st.set_page_config(page_title="Habilitados Marca Propia", page_icon="🔓", layout="wide", initial_sidebar_state="expanded")
st.title("🔓 Reporte de Habilitados | Marca Propia 🏪")
st.markdown("✅ Arrastra aquí el archivo de habilitados, por división")
st.markdown("🔐 Esta app no guarda datos en la nube o en caché. Si deseas reiniciar todo solo da refresh a la página")
kpi_top = st.container()


def color_sem(s):
    return ["background-color:#ff4d4d;color:white;" if pd.notna(v) and v < 40
            else "background-color:#ffd633;" if pd.notna(v) and v < 95
            else "background-color:#5cd65c;" if pd.notna(v)
            else "background-color:lightgray;" for v in s]

#---------------------------------------------------------------------------------------- 
#1: Mapping Plaza → División
PLAZA_DIV = {
    "Tamaulipas (Reynosa)": "Coahuila-Tamaulipas",
    "Tamaulipas (Matamoros)": "Coahuila-Tamaulipas",
    "Coahuila (Saltillo)": "Coahuila-Tamaulipas",
    "Coahuila (Torreón)": "Coahuila-Tamaulipas",
    "México": "México-Península", "Puebla": "México-Península",
    "Morelos": "México-Península", "Yucatán": "México-Península",
    "Quintana Roo": "México-Península",
    "Jalisco": "Pacífico",
    "Baja California (Tijuana)": "Pacífico",
    "Baja California (Ensenada)": "Pacífico",
    "Baja California (Mexicali)": "Pacífico",
    "Sonora (Hermosillo)": "Pacífico",
    "Nuevo León": "Nuevo León",
}
#1.2: Función de lectura de archivos
@st.cache_data
def cargar(archivos_info):
    dfs = []
    for nombre, contenido in archivos_info:
        d = pd.read_excel(io.BytesIO(contenido), header=5)
        d.columns = d.columns.astype(str).str.strip()

        # 👇 NUEVO: cleanup ANTES de detectar división
        d = d.drop(columns=["Plaza", "Campo", "Categoría", "Indicadores", "Unnamed: 11"],
                   errors="ignore")
        d = d.rename(columns={
            "Unnamed: 2":  "Plaza",
            "Unnamed: 4":  "Campo",
            "Unnamed: 8":  "Categoría",
            "Unnamed: 10": "Descripción",
        })

        # Ahora sí, con la Plaza real
        plazas = d["Plaza"].dropna().unique() if "Plaza" in d.columns else []
        divs = {PLAZA_DIV.get(p) for p in plazas} - {None}
        d["División"] = list(divs)[0] if len(divs) == 1 else "Desconocida"
        dfs.append(d)
    return pd.concat(dfs, ignore_index=True)

#1.3: Uploader + persistir en session_state
if "HAB" not in st.session_state:
    archivos = st.file_uploader(
        "📤 Sube o arrastra los 4 archivos de Habilitados",
        type=["xlsx"], accept_multiple_files=True
    )
    if not archivos:
        st.stop()

    HAB = cargar([(a.name, a.getbuffer().tobytes()) for a in archivos])
    HAB_COL = next((c for c in HAB.columns if str(c).startswith("Habilitar")), None)
    if not HAB_COL:
        st.error("No se encontró la columna 'Habilitar Pedir'")
        st.stop()

    st.session_state["HAB"] = HAB
    st.session_state["HAB_COL"] = HAB_COL


#1.4: Recuperar de session_state
HAB = st.session_state["HAB"]
HAB_COL = st.session_state["HAB_COL"]
st.success(f"✅ {len(HAB):,} filas cargadas")

#---------------------------------------------------------------------------------------- 
#2.1: Filtros
def filtro(label, serie):
    ops = ["Todos"] + sorted(serie.dropna().astype(str).unique().tolist())
    return st.sidebar.selectbox(label, ops)

df = HAB.copy()
for col in ["División", "Plaza", "Categoría"]:
    if col in df.columns:
        sel = filtro(col, df[col])
        if sel != "Todos":
            df = df[df[col] == sel]
if "Descripción" in df.columns:
    desc_disp = sorted(df["Descripción"].dropna().astype(str).unique().tolist())
    sel_desc = st.sidebar.multiselect("Descripción", desc_disp)
    if sel_desc:
        df = df[df["Descripción"].isin(sel_desc)]

st.sidebar.markdown("---")
nivel = st.sidebar.radio("Vista por:", ["División", "Plaza"], horizontal=True)

# Tabla principal
TOT = HAB.groupby(nivel)["Tienda"].nunique().to_dict()

#---------------------------------------------------------------------------------------- 
#4: Tabla de habilitados
@st.cache_data
def pct_hab(df, _tot, hab_col, nivel):
    hab = df[df[hab_col] == 1]
    base = hab.groupby(["Descripción", nivel])["Tienda"].nunique().reset_index(name="t")
    base["pct"] = (base["t"] / base[nivel].map(_tot) * 100).clip(0, 100)
    return base.pivot(index="Descripción", columns=nivel, values="pct")

tabla = pct_hab(df, TOT, HAB_COL, nivel)

st.subheader(f"📊 % Habilitados por {nivel}")

styled = tabla.style.apply(color_sem, axis=0).format("{:.0f}%", na_rep="No habilitado")
st.markdown(f"<div style='overflow:auto; max-height:600px'>{styled.to_html()}</div>",
            unsafe_allow_html=True)


