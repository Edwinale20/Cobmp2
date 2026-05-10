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
st.set_page_config(page_title="Habilitados Marca Propia", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("🟢 Reporte de Habilitados | Marca Propia 🏪")
st.markdown("✅ Arrastra aquí el archivo de habilitados, por división")
st.markdown("🔐 Esta app no guarda datos en la nube o en caché. Si deseas reiniciar todo solo da refresh a la página")
kpi_top = st.container()
