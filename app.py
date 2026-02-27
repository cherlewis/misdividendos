import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📄 Extractor de Dividendos ING a Excel")
st.write("Sube tus recibos de dividendos en PDF y obtén tu tabla al instante.")

archivos_pdf = st.file_uploader("Sube tus PDFs de ING aquí", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    datos_extraidos = []
    
    for archivo in archivos_pdf:
        with pdfplumber.open(archivo) as pdf:
            texto = pdf.pages[0].extract_text()
            
            if texto:
                # 1. Empresa
                match_empresa = re.search(r"Valor:\s*([^\n]+)", texto)
                empresa = match_empresa.group(1).strip() if match_empresa else "No encontrada"
                
                # 2. Número de títulos (En ING suele venir el número justo ANTES de "Número de títulos")
                match_titulos = re.search(r"([\d.,]+)\s+Número de títulos", texto)
                titulos = match_titulos.group(1) if match_titulos else "0"
                
                # 3. Importe Bruto
                match_bruto = re.search(r"Importe total bruto:\s*([\d,]+)\s*€", texto)
                bruto = match_bruto.group(1) if match_bruto else "0,00"
                
                # 4. Retención en Origen
                match_ret_origen = re.search(r"Retención en origen\s*([\d,]+)\s*€", texto)
                ret_origen = match_ret_origen.group(1) if match_ret_origen else "0,00"
                
                # 5. Retención (Destino / España) 
                # En tu PDF viene como "7,72 € \n : \n Retención"
                match_retencion = re.search(r"([\d,]+)\s*€\s*:\s*Retención", texto)
                retencion = match_retencion.group(1) if match_retencion else "0,00"
                
                # 6. Importe Neto
                match_neto = re.search(r"([\d,]+)\s*€\s*Importe total neto", texto)
                neto = match_neto.group(1) if match_neto else "0,00"
                
                # Guardamos la fila
                datos_extraidos.append({
                    "Documento": archivo.name,
                    "Empresa": empresa,
                    "Títulos": titulos,
                    "Bruto (€)": bruto,
                    "Ret. Origen (€)": ret_origen,
                    "Ret. Destino (€)": retencion,
                    "Neto (€)": neto
                })

    if datos_extraidos:
        st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
        
        df = pd.DataFrame(datos_extraidos)
        st.dataframe(df)
        
        # Descarga optimizada para Excel en español
        csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
        st.download_button(
            label="⬇️ Descargar tabla para Excel (.csv)",
            data=csv,
            file_name='dividendos_ING_completos.csv',
            mime='text/csv',
        )
