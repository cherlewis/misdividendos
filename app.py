import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📄 Extractor de Dividendos ING")
st.write("Sube tus recibos de dividendos en PDF y obtén tu tabla al instante.")

archivos_pdf = st.file_uploader("Sube tus PDFs de ING aquí", type=["pdf"], accept_multiple_files=True)

def buscar_dato(patrones, texto, por_defecto="0,00"):
    """Prueba varios patrones de búsqueda hasta encontrar el dato correcto."""
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            for grupo in match.groups():
                if grupo is not None:
                    return grupo.strip()
    return por_defecto

if archivos_pdf:
    datos_extraidos = []
    
    for archivo in archivos_pdf:
        with pdfplumber.open(archivo) as pdf:
            texto = pdf.pages[0].extract_text(layout=True) 
            
            if not texto:
                texto = pdf.pages[0].extract_text()
            
            if texto:
                # --- NUEVA LÓGICA DE FECHA VALOR ---
                # 1. Buscamos todas las fechas con formato DD/MM/YYYY en el documento
                fechas_encontradas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                if fechas_encontradas:
                    # Las ordenamos temporalmente como YYYYMMDD para que Python sepa cuál es más antigua
                    fechas_ordenadas = sorted(fechas_encontradas, key=lambda f: f[6:] + f[3:5] + f[0:2])
                    # La Fecha Valor siempre es la más antigua de las que aparecen
                    fecha = fechas_ordenadas[0]
                else:
                    fecha = "No encontrada"

                # 2. Empresa 
                empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "No encontrada")
                empresa = empresa.split("   ")[0].strip()

                # 3. Importe por título
                importe_titulo = buscar_dato([
                    r"Importe por t[íi]tulo\s*:\s*([\d,]+)",       
                    r"Importe por t[íi]tulo\s*([\d,]+)",            
                    r"([\d,]+)\s*€\s*Importe por t[íi]tulo"         
                ], texto)

                # 4. Número de Títulos
                titulos = buscar_dato([
                    r"N[úu]mero de t[íi]tulos\s*:\s*(\d+)",          
                    r"(\d+)\s+N[úu]mero de t[íi]tulos",             
                    r"N[úu]mero de t[íi]tulos.*?(\d+)"              
                ], texto, "0")
                
                # 5. Importe Bruto
                bruto = buscar_dato([
                    r"Importe total bruto\s*:\s*([\d,]+)", 
                    r"([\d,]+)\s*€\s*Importe total bruto"
                ], texto)
                
                # 6. Retención en Origen
                ret_origen = buscar_dato([
                    r"Retenci[óo]n en origen\s*:\s*([\d,]+)", 
                    r"Retenci[óo]n en origen\s*([\d,]+)",
                    r"([\d,]+)\s*€\s*Retenci[óo]n en origen"
                ], texto)
                
                # 7. Retención en Destino
                ret_destino = buscar_dato([
                    r"Retenci[óo]n en destino\s*:\s*([\d,]+)", 
                    r"Retenci[óo]n\s*:\s*([\d,]+)",
                    r"([\d,]+)\s*€\s*:\s*Retenci[óo]n"
                ], texto)
                
                # 8. Importe Neto
                neto = buscar_dato([
                    r"Importe total neto\s*:\s*([\d,]+)", 
                    r"([\d,]+)\s*€\s*Importe total neto"
                ], texto)
                
                # Guardamos la fila final
                datos_extraidos.append({
                    "Documento": archivo.name,
                    "Fecha Valor": fecha,
                    "Empresa": empresa,
                    "Títulos": titulos,
                    "Importe/Título (€)": importe_titulo,
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
            file_name='dividendos_ING_completos.csv',
            mime='text/csv',
        )
