import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="Debugger de ING", layout="wide")

st.title("🐞 Modo Rayos X: Debugger de PDFs")
st.write("Sube el PDF rebelde de la **Compra de 2022** para ver cómo están ordenados los datos por dentro.")

archivo = st.file_uploader("Sube tu PDF aquí", type=["pdf"])

if archivo:
    with pdfplumber.open(archivo) as pdf:
        # Extraemos el texto de dos formas distintas
        texto_layout = pdf.pages[0].extract_text(layout=True) or ""
        texto_normal = pdf.pages[0].extract_text() or ""
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👁️ Modo Layout (Intenta mantener espacios)")
        st.code(texto_layout, language="text")
        
    with col2:
        st.subheader("🤖 Modo Interno (Orden real de lectura)")
        st.code(texto_normal, language="text")
        
    st.markdown("---")
    st.subheader("🎯 Prueba de Extracción de Importes")
    
    # Vamos a cazar todos los números con formato europeo (Ej: 1.113,02) en el Modo Layout
    importes_layout = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', texto_layout)
    st.write("**Números detectados en Modo Layout:**", importes_layout)
    
    importes_normal = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', texto_normal)
    st.write("**Números detectados en Modo Interno:**", importes_normal)
