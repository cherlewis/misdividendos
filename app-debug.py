import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="Debugger de ING", layout="wide")

st.title("🐞 Modo Rayos X: Debugger de Compra 2022")
st.write("Sube el PDF rebelde de la **Compra de 2022** para ver cómo la máquina lee los números realmente.")

archivo = st.file_uploader("Sube SOLO tu PDF de Compra aquí", type=["pdf"])

if archivo:
    with pdfplumber.open(archivo) as pdf:
        texto_layout = pdf.pages[0].extract_text(layout=True) or ""
        texto_normal = pdf.pages[0].extract_text() or ""
        
        texto_limpio = re.sub(r'\s+', ' ', texto_layout + " " + texto_normal)
        
    st.subheader("1. El texto 'aplastado' que lee la máquina:")
    st.code(texto_limpio, language="text")
    
    st.markdown("---")
    st.subheader("2. Búsqueda de la Operación")
    
    patron_bloque = r'(Compra|Venta)(.*?)(Detalle de la orden|Cuenta de cargo|Podrá solicitar)'
    match_op = re.search(patron_bloque, texto_limpio, re.IGNORECASE)
    
    if match_op:
        st.success("✅ ¡El bloque entre 'Compra' y 'Detalle de la orden' ha sido encontrado!")
        zona_numeros = match_op.group(2)
        st.write("**Texto atrapado en ese bloque:**")
        st.code(zona_numeros, language="text")
        
        # PRUEBA A: Usando delimitadores estrictos (El código que fallaba)
        importes_estrictos = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', zona_numeros)
        st.write("🔴 **Intento A (Estricto - Fallaba):**", importes_estrictos)
        
        # PRUEBA B: Sin delimitadores (Ignorando si está pegado a una 'X' u otra letra)
        importes_flexibles = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', zona_numeros)
        st.write("🟢 **Intento B (Flexible - Solución):**", importes_flexibles)
        
        if importes_flexibles:
            st.info(f"El Importe Total capturado con el Intento B es: **{importes_flexibles[-1]}**")
    else:
        st.error("❌ No se ha encontrado el bloque. El problema es otro.")
        # Buscamos en todo el texto por si acaso
        todos_los_numeros = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto_limpio)
        st.write("**Números encontrados en todo el documento:**", todos_los_numeros)
