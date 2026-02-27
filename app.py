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
                # 1. Fecha Valor (Busca el formato DD/MM/YYYY después de "Fecha valor")
                match_fecha = re.search(r"Fecha valor.*?(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE | re.DOTALL)
                # Si no encuentra "Fecha valor", busca la primera fecha que aparezca en el documento
                if not match_fecha:
                    match_fecha = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
                fecha = match_fecha.group(1) if match_fecha else "No encontrada"

                # 2. Empresa
                match_empresa = re.search(r"Valor:\s*([^\n]+)", texto, re.IGNORECASE)
                empresa = match_empresa.group(1).strip() if match_empresa else "No encontrada"
                
                # 3. Número de títulos
                match_titulos = re.search(r"(\d+)\s*N[úu]mero de t[íi]tulos", texto, re.IGNORECASE)
                titulos = match_titulos.group(1) if match_titulos else "0"
                
                # 4. Importe Bruto
                match_bruto = re.search(r"Importe total bruto:\s*([\d,]+)\s*€", texto, re.IGNORECASE)
                bruto = match_bruto.group(1) if match_bruto else "0,00"
                
                # 5. Retención en Origen
                match_ret_origen = re.search(r"Retenci[óo]n en origen\s*([\d,]+)\s*€", texto, re.IGNORECASE)
                ret_origen = match_ret_origen.group(1) if match_ret_origen else "0,00"
                
                # 6. Retención (Destino)
                match_retencion = re.search(r"([\d,]+)\s*€\s*:\s*Retenci[óo]n", texto, re.IGNORECASE)
                retencion = match_retencion.group(1) if match_retencion else "0,00"
                
                # 7. Importe Neto
                match_neto = re.search(r"([\d,]+)\s*€\s*Importe total neto", texto, re.IGNORECASE)
                neto = match_neto.group(1) if match_neto else "0,00"
                
                # Guardamos la fila con todos los datos
                datos_extraidos.append({
                    "Documento": archivo.name,
                    "Fecha Valor": fecha,
                    "Empresa": empresa,
                    "Títulos": titulos,
                    "Bruto (€)": bruto,
                    "Ret. Origen (€)": ret_origen,
                    "Ret. Destino (€)": retencion,
                    "Neto (€)": neto
                })

    # Mostrar resultados
    if datos_extraidos:
        st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
        
        df = pd.DataFrame(datos_extraidos)
        st.dataframe(df)
        
        # Botón de descarga para Excel (.csv)
        csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
        st.download_button(
            label="⬇️ Descargar tabla para Excel (.csv)",
            data=csv,
            file_name='dividendos_ING_completos.csv',
            mime='text/csv',
        )
