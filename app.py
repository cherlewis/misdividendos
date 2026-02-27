import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📄 Extractor de Dividendos (Formato ING)")
st.write("Sube tus reportes de dividendos en PDF y obtén una tabla lista para Excel.")

# accept_multiple_files=True permite subir varios PDFs a la vez!
archivos_pdf = st.file_uploader("Sube tus PDFs aquí", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    datos_extraidos = []
    
    for archivo in archivos_pdf:
        with pdfplumber.open(archivo) as pdf:
            # Extraemos el texto de la primera página
            texto = pdf.pages[0].extract_text()
            
            if texto:
                # AQUÍ ESTÁ LA MAGIA: Las Expresiones Regulares (Regex)
                # Buscamos patrones específicos dentro de todo el texto caótico del PDF
                
                # 1. Buscar la Empresa (Ej: "Valor: VIDRALA(VID)")
                match_empresa = re.search(r"Valor:\s*([^\n]+)", texto)
                empresa = match_empresa.group(1).strip() if match_empresa else "No encontrada"
                
                # 2. Buscar Importe Bruto (Ej: "Importe total bruto:\n 40,65 €")
                match_bruto = re.search(r"Importe total bruto:\s*([\d,]+)\s*€", texto)
                bruto = match_bruto.group(1) if match_bruto else "0,00"
                
                # 3. Buscar Importe Neto (Ej: "32,93 €\n\n\nImporte total neto:")
                match_neto = re.search(r"([\d,]+)\s*€\s*Importe total neto", texto)
                neto = match_neto.group(1) if match_neto else "0,00"
                
                # Guardamos los datos de este PDF en nuestra lista
                datos_extraidos.append({
                    "Documento": archivo.name,
                    "Empresa": empresa,
                    "Bruto (€)": bruto,
                    "Neto (€)": neto
                })

    # Si logramos extraer datos de al menos un PDF, mostramos la tabla
    if datos_extraidos:
        st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
        
        # Convertimos la lista en una tabla (DataFrame)
        df = pd.DataFrame(datos_extraidos)
        st.dataframe(df)
        
        # Botón para descargar
        csv = df.to_csv(index=False, sep=";").encode('utf-8-sig') # sep=";" ayuda a que Excel en español lo lea mejor
        st.download_button(
            label="⬇️ Descargar tabla para Excel (.csv)",
            data=csv,
            file_name='dividendos_extraidos.csv',
            mime='text/csv',
        )
