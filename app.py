import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import zipfile
from datetime import datetime

# Configuramos la página para que sea más ancha y tenga título en la pestaña del navegador
st.set_page_config(page_title="Centro de Dividendos", layout="wide")

# ==========================================
# 🧠 FUNCIONES COMPARTIDAS (El "Cerebro")
# ==========================================
def buscar_dato(patrones, texto, por_defecto="0,00"):
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            for grupo in match.groups():
                if grupo is not None:
                    return grupo.strip()
    return por_defecto

def calcular_porcentaje(parte_str, total_str):
    try:
        p = float(parte_str.replace('.', '').replace(',', '.'))
        t = float(total_str.replace('.', '').replace(',', '.'))
        if t == 0 or p == 0: return "0%"
        ratio = p / t
        if 0.26 <= ratio <= 0.27: return "26,375%"
        elif 0.245 <= ratio <= 0.255: return "25%"
        elif 0.14 <= ratio <= 0.16: return "15%"
        elif 0.185 <= ratio <= 0.195: return "19%"
        return f"{round(ratio * 100, 2):g}%".replace('.', ',')
    except:
        return "0%"

# ==========================================
# 🧭 MENÚ LATERAL (La Navegación)
# ==========================================
st.sidebar.title("🛠️ Menú Principal")
st.sidebar.write("Elige la herramienta que quieres usar:")

opcion = st.sidebar.radio(
    "", # Dejamos el título del radio vacío para que quede más limpio
    ["📊 Extractor a Excel", "🗂️ Renombrador de PDFs"]
)

# Línea separadora en el menú
st.sidebar.markdown("---")
st.sidebar.info("💡 Puedes subir varios PDFs a la vez en ambas herramientas.")


# ==========================================
# 🚀 APLICACIÓN 1: EXTRACTOR A EXCEL
# ==========================================
if opcion == "📊 Extractor a Excel":
    st.title("📊 Extractor Profesional de Dividendos ING")
    st.write("Sube tus recibos de dividendos en PDF y obtén tu tabla lista para importar.")

    archivos_pdf = st.file_uploader("Sube tus PDFs de ING aquí", type=["pdf"], accept_multiple_files=True, key="ext")

    if archivos_pdf:
        datos_extraidos = []
        for archivo in archivos_pdf:
            with pdfplumber.open(archivo) as pdf:
                texto = pdf.pages[0].extract_text(layout=True) 
                if not texto: texto = pdf.pages[0].extract_text()
                
                if texto:
                    fechas_encontradas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                    if fechas_encontradas:
                        fechas_ordenadas = sorted(fechas_encontradas, key=lambda f: f[6:] + f[3:5] + f[0:2])
                        fecha_abono = fechas_ordenadas[0]
                    else: fecha_abono = "No encontrada"

                    empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Desconocida")
                    empresa = empresa.split("   ")[0].strip()
                    concepto = f"DIVIDENDO ({empresa})"

                    importe_titulo = buscar_dato([r"Importe por t[íi]tulo\s*:\s*([\d,]+)", r"Importe por t[íi]tulo\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe por t[íi]tulo"], texto)
                    titulos = buscar_dato([r"N[úu]mero de t[íi]tulos\s*:\s*(\d+)", r"(\d+)\s+N[úu]mero de t[íi]tulos", r"N[úu]mero de t[íi]tulos.*?(\d+)"], texto, "0")
                    bruto = buscar_dato([r"Importe total bruto\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe total bruto"], texto)
                    ret_origen = buscar_dato([r"Retenci[óo]n en origen\s*:\s*([\d,]+)", r"Retenci[óo]n en origen\s*([\d,]+)", r"([\d,]+)\s*€\s*Retenci[óo]n en origen"], texto)
                    ret_destino = buscar_dato([r"Retenci[óo]n en destino\s*:\s*([\d,]+)", r"Retenci[óo]n\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*:\s*Retenci[óo]n"], texto)
                    neto = buscar_dato([r"Importe total neto\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe total neto"], texto)

                    pct_origen = calcular_porcentaje(ret_origen, bruto)
                    pct_destino = calcular_porcentaje(ret_destino, bruto)

                    cuenta_abono = buscar_dato([r"(1465\s*0100\s*93\s*\d{10})", r"(1465\s*010093\s*\d{10})"], texto, "N/A")
                    cuenta_valores = buscar_dato([r"(91\s*\d{10})", r"(1465\s*0100\s*91\s*\d{10})"], texto, "0")

                    datos_extraidos.append({
                        "Fecha Abono": fecha_abono, "Concepto": concepto, "Importe Neto (€)": neto,
                        "Retención en origen (€)": ret_origen, "% retención en origen": pct_origen,
                        "Retención en destino (€)": ret_destino, "% retención en destino": pct_destino,
                        "Importe Bruto (€)": bruto, "Empresa": empresa, "Cuenta de Valores": cuenta_valores,
                        "Número de títulos": titulos, "Importe por título (€)": importe_titulo, "Cuenta Abono": cuenta_abono
                    })

        if datos_extraidos:
            st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
            df = pd.DataFrame(datos_extraidos)
            df['Fecha_Temporal'] = pd.to_datetime(df['Fecha Abono'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            st.dataframe(df)
            
            csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar tabla para Excel (.csv)", data=csv, file_name='dividendos_ING_ordenados.csv', mime='text/csv')


# ==========================================
# 🚀 APLICACIÓN 2: RENOMBRADOR DE PDFs
# ==========================================
elif opcion == "🗂️ Renombrador de PDFs":
    st.title("🗂️ Renombrador Automático de PDFs")
    st.write("Sube tus PDFs. El sistema te devolverá un ZIP con los nombres: `YYYYMMDD-MovimientoEmpresa.pdf`")

    archivos_pdf_ren = st.file_uploader("Sube tus PDFs aquí", type=["pdf"], accept_multiple_files=True, key="ren")

    if archivos_pdf_ren:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for archivo in archivos_pdf_ren:
                with pdfplumber.open(archivo) as pdf:
                    texto = pdf.pages[0].extract_text(layout=True)
                    if not texto: texto = pdf.pages[0].extract_text()
                    
                    if texto:
                        fechas_encontradas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                        if fechas_encontradas:
                            fechas_ordenadas = sorted(fechas_encontradas, key=lambda f: f[6:] + f[3:5] + f[0:2])
                            fecha_abono = fechas_ordenadas[0]
                            fecha_formateada = datetime.strptime(fecha_abono, "%d/%m/%Y").strftime("%Y%m%d") 
                        else: fecha_formateada = "00000000"

                        empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Empresa")
                        empresa = empresa.split("   ")[0].strip()
                        empresa_limpia = re.sub(r'\(.*?\)', '', empresa) 
                        empresa_limpia = re.sub(r'[^a-zA-Z0-9]', ' ', empresa_limpia) 
                        empresa_limpia = "".join([palabra.capitalize() for palabra in empresa_limpia.split()])
                        
                        nuevo_nombre = f"{fecha_formateada}-Movimiento{empresa_limpia}.pdf"
                        
                        archivo.seek(0)
                        zip_file.writestr(nuevo_nombre, archivo.read())
                        st.write(f"✅ Listo: `{archivo.name}` ➡️ **`{nuevo_nombre}`**")

        st.success("¡Todos los archivos han sido empaquetados!")
        st.download_button(label="📦 Descargar ZIP con PDFs renombrados", data=zip_buffer.getvalue(), file_name="Movimientos_Dividendos.zip", mime="application/zip")
