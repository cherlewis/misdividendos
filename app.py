import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📄 Extractor de Dividendos ING (Españoles y Americanos)")
st.write("Sube tus recibos de dividendos en PDF y obtén tu tabla al instante.")

archivos_pdf = st.file_uploader("Sube tus PDFs de ING aquí", type=["pdf"], accept_multiple_files=True)

def buscar_dato(patrones, texto, por_defecto="0,00"):
    """Prueba varios patrones de búsqueda hasta encontrar el dato correcto."""
    for patron in patrones:
        # re.MULTILINE permite buscar línea por línea correctamente
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            # Devuelve el primer grupo encontrado
            for grupo in match.groups():
                if grupo is not None:
                    return grupo.strip()
    return por_defecto

if archivos_pdf:
    datos_extraidos = []
    
    for archivo in archivos_pdf:
        with pdfplumber.open(archivo) as pdf:
            # MAGIA: layout=True fuerza a mantener la estructura visual con espacios
            texto = pdf.pages[0].extract_text(layout=True) 
            
            # Si layout=True falla, usamos el texto normal como plan B
            if not texto:
                texto = pdf.pages[0].extract_text()
            
            if texto:
                # 1. Fecha Valor
                fecha = buscar_dato([r"Fecha valor.*?(\d{2}/\d{2}/\d{4})", r"(\d{2}/\d{2}/\d{4})"], texto, "No encontrada")
                
                # 2. Empresa (Realty Income, Vidrala, etc.)
                empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "No encontrada")
                # Limpiamos si se cuela algo extra al lado
                empresa = empresa.split("   ")[0].strip()

                # 3. Número de Títulos
                titulos = buscar_dato([
                    r"N[úu]mero de t[íi]tulos\s*:\s*(\d+)",          # Formato nuevo/americano
                    r"(\d+)\s+N[úu]mero de t[íi]tulos",             # Formato antiguo
                    r"N[úu]mero de t[íi]tulos.*?(\d+)"              # Por si hay espacios de por medio
                ], texto, "0")
                
                # 4. Importe Bruto
                bruto = buscar_dato([
                    r"Importe total bruto\s*:\s*([\d,]+)", 
                    r"([\d,]+)\s*€\s*Importe total bruto"
                ], texto)
                
                # 5. Retención en Origen (USA u otros)
                ret_origen = buscar_dato([
                    r"Retenci[óo]n en origen\s*:\s*([\d,]+)", 
                    r"Retenci[óo]n en origen\s*([\d,]+)",
                    r"([\d,]+)\s*€\s*Retenci[óo]n en origen"
                ], texto)
                
                # 6. Retención en Destino (España)
                ret_destino = buscar_dato([
                    r"Retenci[óo]n en destino\s*:\s*([\d,]+)", 
                    r"Retenci[óo]n\s*:\s*([\d,]+)",
                    r"([\d,]+)\s*€\s*:\s*Retenci[óo]n"
                ], texto)
                
                # 7. Importe Neto
                neto = buscar_dato([
                    r"Importe total neto\s*:\s*([\d,]+)", 
                    r"([\d,]+)\s*€\s*Importe total neto"
                ], texto)
                
                datos_extraidos.append({
                    "Documento": archivo.name,
                    "Fecha Valor": fecha,
                    "Empresa": empresa,
                    "Títulos": titulos,
                    "Bruto (€)": bruto,
                    "Ret. Origen (€)": ret_origen,
                    "Ret. Destino (€)": ret_destino,
                    "Neto (€)": neto
                })

    if datos_extraidos:
        st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
        
        df = pd.DataFrame(datos_extraidos)
        st.dataframe(df)
        
        csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
        st.download_button(
            label="⬇️ Descargar tabla para Excel (.csv)",
            data=csv,
            file_name='dividendos_completos.csv',
            mime='text/csv',
        )
