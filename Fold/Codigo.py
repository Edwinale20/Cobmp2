import pandas as pd
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

#----------------------------------------------------------------------------------------

   
st.set_page_config(page_title="Cobertura Marca Propia", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Cobertura | Marca Propia 🏪")
st.markdown("✅ Arrastra aquí tu archivo de inventarios")
st.markdown("✅ Esta app analiza en menos de 30 segundos las coberturas de todo el catálogo de tu categoría. Te ahorramos hasta 5 horas de trabajo semanales!")
st.markdown("✅ Puedes identificar los productos en desabasto, y aquellos con oportunidades." "Además identificar pocas UPTD, con el fin de seguir el plan APT")
st.markdown("🔐 Esta app no guarda datos en la nube o en caché. Si deseas reiniciar todo solo da refresh a la página")
kpi_top = st.container()

 
#----------------------------------------------------------------------------------------   

@st.cache_data
def Inventarios(archivo_xlsx):
    if archivo_xlsx is None:
        return None

    # Fila 3 como header (A3:L3), porque header es 0-index => 2 = tercera fila
    df = pd.read_excel(archivo_xlsx, sheet_name=0, header=2)

    # --- 1) Columna 8 (H) sin nombre -> "Descripción"
    # (columna 8 = índice 7)
    if df.shape[1] >= 8:
        df.columns = list(df.columns)  # asegurar que es lista
        df.columns.values[7] = "Descripción"

    # --- 2) Dropear "Metrics" (si existe)
    # (por si viene con mayúsculas/minúsculas diferentes)
    cols_lower = {c.lower(): c for c in df.columns if isinstance(c, str)}
    if "metrics" in cols_lower:
        df = df.drop(columns=[cols_lower["metrics"]])

    combined_df = df.copy()
    return combined_df

#---------------------------------------------------------------------------------------- AQUÍ defines el uploader y llamas a tu función ---
# Placeholder
uploader_placeholder = st.empty()

# El uploader vive dentro del placeholder (ahora XLSX)
archivo_xlsx = uploader_placeholder.file_uploader(
    "📤 Sube tu archivo de Inventarios (312 de BI)",
    type=["xlsx"]
)

if archivo_xlsx is not None:
    # Quitar uploader
    uploader_placeholder.empty()

    # Llamas tu función (misma salida: DataFrame)
    combined_df = Inventarios(archivo_xlsx)
    
#----------------------------------------------------------------------------------------    

INV = Inventarios(archivo_xlsx)  # <- como querías

if INV is None:
    st.stop()

st.success("✅ Los inventarios de tu categoría fueron cargados con éxito.")

#----------------------------------------------------------------------------------------


st.sidebar.image("https://raw.githubusercontent.com/Edwinale20/bullsaifx/main/Carpeta/el-logo.png", width=170)
st.sidebar.title("🔠  Filtros")

opciones_division = ['Ninguno'] + list(INV['División'].unique())
division = st.sidebar.selectbox('Seleccione la División', opciones_division)

#opciones_pareto = ['Total artículos', 'Infaltables 80/20']
#filtro_pareto = st.sidebar.selectbox('Filtrar Infaltables 80/20', opciones_pareto)

opciones_plaza = ['Ninguno'] + list(INV['Plaza'].unique())
plaza = st.sidebar.selectbox('Seleccione la Plaza', opciones_plaza)

opciones_mercado = ['Ninguno'] + list(INV['Mercado'].unique())
mercado = st.sidebar.selectbox('Seleccione el Mercado', opciones_mercado)

opciones_categoria = ['Ninguno'] + list(INV['Categoría'].unique())
categoria = st.sidebar.selectbox('Seleccione la Categoria', opciones_categoria)

#opciones_proveedor = ['Ninguno'] + list(INV['PROVEEDOR'].unique())
#proveedor = st.sidebar.selectbox('Seleccione el Proveedor', opciones_proveedor)

articulo_busqueda = st.sidebar.text_input("Buscar Artículo:")



# Filtrar por Proveedor
if division == 'Ninguno':
    df_venta_perdida_filtrada = INV
else:
    df_venta_perdida_filtrada = INV[INV['Division'] == division]

# Filtrar por Plaza
if plaza != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Plaza'] == plaza]

# Filtrar por Mercado
if mercado != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Mercado'] == mercado]

# Filtrar por Categoria
if categoria != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['Categoría'] == categoria]

if articulo_busqueda:
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[
        df_venta_perdida_filtrada['Artículo'].str.contains(
            articulo_busqueda, case=False, na=False
        )
    ]


if articulo_busqueda:
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[
        df_venta_perdida_filtrada['Artículo'].str.contains(articulo_busqueda, case=False, na=False)]
    

#----------------------------------------------------------------------------------------

@st.cache_data
def cobertura_tabla(df):
    
    df.columns = df.columns.astype(str).str.strip()

    TOTALES = {
        "Coahuila (Saltillo)":85,"Coahuila (Torreón)":54,"Morelos":12,"México":390,
        "Nuevo León":751,"Puebla":22,"Quintana Roo":103,"Tamaulipas (Matamoros)":59,
        "Tamaulipas (Reynosa)":168,"Baja California (Tijuana)":86,"Baja California (Mexicali)":61,
        "Baja California (Ensenada)":24,"Jalisco":181,"Yucatán":29,"Sonora (Hermosillo)":21,
    }
    ART = "Artículo"
    PLZ = "Plaza"
    TND = "Tienda"
   
    g = (df[[ART,PLZ,TND]].astype(str)
         .groupby([ART,PLZ])[TND]
         .nunique()
         .reset_index(name="Tiendas_con_art"))

    tot = pd.DataFrame({PLZ:list(TOTALES.keys()), "Tiendas_totales":list(TOTALES.values())})
    base = g.merge(tot, on=PLZ, how="left")

   
    if base["Tiendas_totales"].isna().any():
        obs = df.groupby(PLZ)[TND].nunique().rename("obs").reset_index()
        base = base.merge(obs, on=PLZ, how="left")
        base["Tiendas_totales"] = base["Tiendas_totales"].fillna(base["obs"])

    base["Cobertura %"] = (base["Tiendas_con_art"] / base["Tiendas_totales"] * 100).clip(0,100)

    pivot = base.pivot(index=ART, columns=PLZ, values="Cobertura %")

    # Guardar versión numérica para estilo
    numeric = pivot.copy()

    # Formato porcentaje bonito
    pivot = pivot.round(0).astype("Int64").astype(str) + "%"
    pivot = pivot.replace({"<NA>%": "Sin abasto"})

    return pivot, numeric



# === USO CORRECTO ===
pivot, numeric = cobertura_tabla(df_venta_perdida_filtrada)

# Función para aplicar colores
def color_sem(serie):
    colors = []
    for v in serie:
        if pd.isna(v):  # Sin abasto
            colors.append("background-color: lightgray; color: black;")
        elif v < 40:
            colors.append("background-color: #ff4d4d; color: white;")  # Rojo
        elif v < 90:
            colors.append("background-color: #ffd633; color: black;")  # Amarillo
        else:
            colors.append("background-color: #5cd65c; color: black;")  # Verde
    return colors

# Estilo sobre numeric
styled = numeric.style.apply(color_sem, axis=0).format("{:.0f}%", na_rep="Sin abasto")

# 👇 Mostrar con colores en Streamlit
st.markdown(styled.to_html(), unsafe_allow_html=True)



# === 1) Cobertura por artículo (global) ======================================
def cobertura_por_articulo(df, totales_por_plaza: dict, umbral_inv: int = 2):
    pick = lambda names: next((c for c in names if c in df.columns), None)
    ART = pick(["Artículo"])
    PLZ = pick(["Plaza"])
    TND = pick(["Tienda"])

    d = df[[ART,PLZ,TND] + ([INV] if INV else [])].copy().astype({PLZ:str, TND:str, ART:str})
    d["_pres"] = (pd.to_numeric(d[INV], errors="coerce").fillna(0) > umbral_inv) if INV else True
    pres = d.groupby([ART,PLZ,TND], as_index=False)["_pres"].max()
    num = pres.groupby([ART,PLZ])["_pres"].sum().reset_index(name="Tiendas_con_art")

    tot = pd.DataFrame({PLZ:list(totales_por_plaza.keys()), "Tiendas_totales":list(totales_por_plaza.values())})
    base = num.merge(tot, on=PLZ, how="left")

    # Fallback si falta total para alguna plaza → usa tiendas observadas
    if base["Tiendas_totales"].isna().any():
        obs = pres.groupby(PLZ)[TND].nunique().rename("obs").reset_index()
        base = base.merge(obs, on=PLZ, how="left")
        base["Tiendas_totales"] = base["Tiendas_totales"].fillna(base["obs"])

    # Cobertura GLOBAL del artículo (sumando plazas)
    art = (base.groupby(ART)
           .agg(Tiendas_con_art=("Tiendas_con_art","sum"),
                Tiendas_totales=("Tiendas_totales","sum"))
           .reset_index())
    art["Cobertura_%"] = (art["Tiendas_con_art"]/art["Tiendas_totales"]*100).clip(0,100)
    return art  # columnas: [ARTICULO, Tiendas_con_art, Tiendas_totales, Cobertura_%]



TOTALES_PLAZA = {
    "Coahuila (Saltillo)":85, "Coahuila (Torreón)":54, "Morelos":12, "México":390,
    "Nuevo León":751, "Puebla":22, "Quintana Roo":103, "Tamaulipas (Matamoros)":59,
    "Tamaulipas (Reynosa)":168, "Baja California (Tijuana)":86, "Baja California (Mexicali)":61,
    "Baja California (Ensenada)":24, "Jalisco":181, "Yucatán":30, "Sonora (Hermosillo)":21,
}




@st.cache_data
def cobertura_por_division(df, totales_por_plaza: dict, umbral_inv: int = 3):
    pick = lambda names: next((c for c in names if c in df.columns), None)
    ART = pick(["Artículo"])
    PLZ = pick(["Plaza"])
    TND = pick(["Tienda"])
    DIV = pick(["Division"])


    d = df[[ART,PLZ,TND,DIV] + ([INV] if INV else [])].copy().astype({PLZ:str, TND:str, ART:str, DIV:str})
    d["_pres"] = (pd.to_numeric(d[INV], errors="coerce").fillna(0) > umbral_inv) if INV else True
    pres = d.groupby([DIV,ART,PLZ,TND], as_index=False)["_pres"].max()

    # Número de tiendas por artículo dentro de cada división
    num = pres.groupby([DIV,ART,PLZ])["_pres"].sum().reset_index(name="Tiendas_con_art")
    tot = pd.DataFrame({PLZ:list(totales_por_plaza.keys()), "Tiendas_totales":list(totales_por_plaza.values())})
    base = num.merge(tot, on=PLZ, how="left")

    base["Cobertura_%"] = (base["Tiendas_con_art"]/base["Tiendas_totales"]*100).clip(0,100)

    # 🔑 Cobertura promedio por división (promedio de artículos, no suma global)
    resumen = base.groupby(DIV)["Cobertura_%"].mean().reset_index()

    # renombramos para vista
    resumen = resumen.rename(columns={"Cobertura_%":"Cobertura (%)"})

    return resumen

tabla_div = cobertura_por_division(df_venta_perdida_filtrada, TOTALES_PLAZA, umbral_inv=3)

# 🎨 Estilo semáforo bonito
def color(val):
    try:
        v = float(val)
    except:
        return "background-color: lightgray; color: black; text-align:center;"
    if v >= 90:
        return "background-color: #B9F6CA; text-align:center; font-weight:bold;"
    if v >= 80:
        return "background-color: #FFF59D; text-align:center; font-weight:bold;"
    return "background-color: #EF9A9A; text-align:center; font-weight:bold;"

styled = (
    tabla_div.style
        .format({"Cobertura (%)": "{:.1f}%"})
        .applymap(color, subset=["Cobertura (%)"])
        .set_properties(**{"text-align": "center", "border": "1px solid #ddd", "padding": "4px"})
)

st.dataframe(styled, use_container_width=True)

