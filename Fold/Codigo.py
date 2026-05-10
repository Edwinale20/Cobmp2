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
st.set_page_config(page_title="Cobertura Marca Propia", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Cobertura y Habilitados | Marca Propia 🏪")
st.markdown("✅ Arrastra aquí el archivo de inventarios")
st.markdown("🔐 Esta app no guarda datos en la nube o en caché. Si deseas reiniciar todo solo da refresh a la página")
kpi_top = st.container()

#----------------------------------------------------------------------------------------   
#1: Creación de Excel a DuckDB
@st.cache_resource
def get_con():
    con = duckdb.connect(":memory:")
    con.execute("INSTALL excel; LOAD excel;")
    return con

# 1.1: Cargar inventarios a DuckDB
def Inventarios(archivo_subido):
    if archivo_subido is None:
        return None
    
    con = get_con()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo_subido.getbuffer())
        path = tmp.name

    con.execute("""
        CREATE OR REPLACE TABLE inv AS
        SELECT * FROM read_xlsx(?, header = true)
    """, [path])
    os.unlink(path)
    return con

#1.2 Uploader
uploader_placeholder = st.empty()
archivo_xlsx = uploader_placeholder.file_uploader(
    "📤 Sube tu archivo de Inventarios", type=["xlsx"]
)
if archivo_xlsx is None:
    st.stop()
uploader_placeholder.empty()
con = Inventarios(archivo_xlsx)
st.success("✅ Los inventarios fueron cargados con éxito.")

INV = con.execute("SELECT * FROM inv").df()
ultima_fecha = INV["Fecha"].max() if "Fecha" in INV.columns else pd.Timestamp.today()
INV = INV.rename(columns={INV.columns[8]: "Descripción"})
INV = INV.drop(columns=[c for c in INV.columns if str(c).lower() == "metrics"], errors="ignore")
#1.3
@st.cache_data
def calcular_totales_plaza(inv):
    """Universo de tiendas por Plaza, derivado del archivo (no del df filtrado)."""
    return inv.groupby("Plaza")["Tienda"].nunique().to_dict()

TOTALES_PLAZA = calcular_totales_plaza(INV)
# =========================
# SECCIÓN 2 — Filtros sidebar
# =========================

#2.1: Filtros
st.sidebar.markdown("---")
st.markdown(f"📅 Datos actualizados al: **{pd.to_datetime(ultima_fecha).strftime('%d %b %Y')}**")

def filtro(label, serie):
    ops = ["Todos"] + sorted(serie.dropna().astype(str).unique().tolist())
    return st.sidebar.selectbox(label, ops)

df = INV.copy()

# Descripción multiselect
if "Descripción" in df.columns:
    desc_disp = sorted(df["Descripción"].dropna().astype(str).unique().tolist())
    sel_desc = st.sidebar.multiselect("Descripción", desc_disp)
    if sel_desc:
        df = df[df["Descripción"].isin(sel_desc)]
        
for col, label in [("División","División"), ("Plaza","Plaza"),
                   ("Mercado","Mercado"), ("Categoría","Categoría")]:
    if col in df.columns:
        sel = filtro(label, df[col])
        if sel != "Todos":
            df = df[df[col] == sel]

#2.2 Catalogación al final, multiselect sobre el df ya filtrado
if "Catalogación" in df.columns:
    cats_disp = sorted(df["Catalogación"].dropna().astype(str).unique().tolist())
    sel_cats = st.sidebar.multiselect("Catalogación", cats_disp, default=cats_disp)
    if sel_cats:
        df = df[df["Catalogación"].isin(sel_cats)]

# =========================
# SECCIÓN 4 — Calculos y tabla
# =========================
#4.1 Colores
def color_sem(serie):
    colors = []
    for v in serie:
        if pd.isna(v):
            colors.append("background-color: lightgray; color: black;")
        elif v < 40:
            colors.append("background-color: #ff4d4d; color: white;")
        elif v < 90:
            colors.append("background-color: #ffd633; color: black;")
        else:
            colors.append("background-color: #5cd65c; color: black;")
    return colors
    
#4.2: Tabla de cobertura
@st.cache_data
def cobertura_tabla(df, totales):              # ← quita el default =TOTALES_PLAZA
    base = (df.groupby(["Descripción", "Plaza"])["Tienda"]
              .nunique()
              .reset_index(name="tiendas"))
    base["cobertura"] = (base["tiendas"] / base["Plaza"].map(totales) * 100).clip(0, 100)
    return base.pivot(index="Descripción", columns="Plaza", values="cobertura")

numeric = cobertura_tabla(df, TOTALES_PLAZA)   # ← pásalo explícito
styled = (numeric.style
          .apply(color_sem, axis=0)
          .format("{:.0f}%", na_rep="Sin abasto"))

st.markdown(
    f"<div style='overflow:auto; max-height:700px'>{styled.to_html()}</div>",
    unsafe_allow_html=True
)
