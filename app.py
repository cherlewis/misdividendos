import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import zipfile
from datetime import datetime

st.set_page_config(page_title="Centro Financiero ING", layout="wide")

# ==========================================
# 🧠 FUNCIONES COMPARTIDAS
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

def euro_a_numero(euro_str):
    """Convierte un texto con formato '32,93' o '1.000,00' a número matemático."""
    try:
        return float(euro_str.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def formatear_moneda(numero):
    """Convierte un número matemático de vuelta a formato europeo '1.000,00 €'"""
    return f"{numero:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

# ==========================================
# 🧭 MENÚ LATERAL
# ==========================================
st.sidebar.title("🛠️ Menú Principal")
st.sidebar.write("Elige la herramienta que quieres usar:")

opcion = st.sidebar.radio(
    "", 
    [
        "📊 Dividendos a Excel", 
        "🛒 Compras/Ventas a Excel", 
        "🗂️ Renombrador de PDFs"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Sube tus documentos arrastrándolos todos a la vez.")

# ==========================================
# 🚀 APLICACIÓN 1: DIVIDENDOS
# ==========================================
if opcion == "📊 Dividendos a Excel":
    st.title("📊 Extractor de Dividendos y Dashboard")
    st.write("Sube tus recibos de dividendos en PDF de ING para extraer los datos y ver tu resumen.")

    archivos_pdf = st.file_uploader("Sube tus PDFs aquí", type=["pdf"], accept_multiple_files=True, key="div")

    if archivos_pdf:
        datos_extraidos = []
        for archivo in archivos_pdf:
            with pdfplumber.open(archivo) as pdf:
                texto = pdf.pages[0].extract_text(layout=True) 
                if not texto: texto = pdf.pages[0].extract_text()
                
                if texto:
                    fechas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                    fecha_abono = sorted(fechas, key=lambda f: f[6:] + f[3:5] + f[0:2])[0] if fechas else "No encontrada"

                    empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Desconocida").split("   ")[0].strip()
                    concepto = f"DIVIDENDO ({empresa})"

                    importe_titulo = buscar_dato([r"Importe por t[íi]tulo\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe por t[íi]tulo"], texto)
                    titulos = buscar_dato([r"N[úu]mero de t[íi]tulos\s*:\s*(\d+)", r"N[úu]mero de t[íi]tulos.*?(\d+)"], texto, "0")
                    bruto = buscar_dato([r"Importe total bruto\s*:\s*([\d,]+)"], texto)
                    ret_origen = buscar_dato([r"Retenci[óo]n en origen\s*:\s*([\d,]+)", r"Retenci[óo]n en origen\s*([\d,]+)"], texto)
                    ret_destino = buscar_dato([r"Retenci[óo]n en destino\s*:\s*([\d,]+)", r"Retenci[óo]n\s*:\s*([\d,]+)"], texto)
                    neto = buscar_dato([r"Importe total neto\s*:\s*([\d,]+)"], texto)

                    pct_origen = calcular_porcentaje(ret_origen, bruto)
                    pct_destino = calcular_porcentaje(ret_destino, bruto)
                    cuenta_abono = buscar_dato([r"(1465\s*0100\s*93\s*\d{10})"], texto, "N/A")
                    cuenta_valores = buscar_dato([r"(91\s*\d{10})"], texto, "0")

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
            
            # Ordenar por fecha temporal
            df['Fecha_Temporal'] = pd.to_datetime(df['Fecha Abono'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            # --- DASHBOARD VISUAL ---
            st.markdown("---")
            st.subheader("📈 Resumen de tus Dividendos")
            
            # Calculamos los totales
            df['num_bruto'] = df['Importe Bruto (€)'].apply(euro_a_numero)
            df['num_neto'] = df['Importe Neto (€)'].apply(euro_a_numero)
            df['num_impuestos'] = df['Retención en origen (€)'].apply(euro_a_numero) + df['Retención en destino (€)'].apply(euro_a_numero)
            
            total_bruto = df['num_bruto'].sum()
            total_impuestos = df['num_impuestos'].sum()
            total_neto = df['num_neto'].sum()
            
            # Mostramos las tarjetas superiores (KPIs)
            col1, col2, col3 = st.columns(3)
            col1.metric("Bruto Generado", formatear_moneda(total_bruto))
            col2.metric("Impuestos Pagados (Origen+Destino)", formatear_moneda(total_impuestos))
            col3.metric("Neto a la Cuenta", formatear_moneda(total_neto))
            
            st.write("") # Espacio
            
            # Gráfico de barras: Dividendos por empresa
            st.markdown("**Top Pagadores (Neto por Empresa):**")
            datos_grafico = df.groupby('Empresa')['num_neto'].sum().reset_index()
            # Ordenamos de mayor a menor para que el gráfico quede más bonito
            datos_grafico = datos_grafico.sort_values(by='num_neto', ascending=False)
            st.bar_chart(datos_grafico.set_index('Empresa'))
            st.markdown("---")
            
            # Limpiamos las columnas matemáticas auxiliares antes de mostrar la tabla
            df = df.drop(columns=['num_bruto', 'num_neto', 'num_impuestos'])
            
            # --- TABLA Y DESCARGA ---
            st.subheader("📋 Tabla de Datos Detallada")
            st.dataframe(df)
            csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel (.csv)", data=csv, file_name='dividendos.csv', mime='text/csv')

# ==========================================
# 🚀 APLICACIÓN 2: COMPRAS Y VENTAS
# ==========================================
elif opcion == "🛒 Compras/Ventas a Excel":
    st.title("🛒 Extractor de Compras y Ventas")
    st.write("Sube tus justificantes de operaciones de bolsa (ING) para obtener el desglose de comisiones.")

    archivos_pdf_op = st.file_uploader("Sube tus PDFs de Operaciones aquí", type=["pdf"], accept_multiple_files=True, key="ops")

    if archivos_pdf_op:
        datos_operaciones = []
        for archivo in archivos_pdf_op:
            with pdfplumber.open(archivo) as pdf:
                texto = pdf.pages[0].extract_text(layout=True)
                if not texto: texto = pdf.pages[0].extract_text()
                
                if texto:
                    patron_int = r"(\d+)\s+([A-Z0-9\s\.\-\&]+?)\s+([A-Z]{2}[A-Z0-9]{10})\s+([A-Z\s]+?)\s+(Compra|Venta)\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})"
                    patron_nac = r"(\d+)\s+([A-Z0-9\s\.\-\&]+?)\s+([A-Z]{2}[A-Z0-9]{10})\s+([A-Z\s]+?)\s+(Compra|Venta)\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})\s+([\d,]+\s+[A-Z]{3})"
                    
                    match_int = re.search(patron_int, texto)
                    match_nac = re.search(patron_nac, texto) if not match_int else None
                    
                    patron_fecha = r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s+(\d+)\s+([A-Za-z áéíóúÁÉÍÓÚ]+?)\s+([\d,]+\s+[A-Z]{3})(?:\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}))?(?:\s+([\d,]+\s+[A-Z]{3}))?\s+([\d,]+\s+[A-Z]{3})"
                    match_fecha = re.search(patron_fecha, texto)

                    if match_int:
                        datos = [g.strip() for g in match_int.groups()]
                        titulos, empresa, isin, mercado, tipo_op, precio, importe_op, comision_ing, gastos_bolsa, impuestos, comision_cambio, importe_total = datos
                    elif match_nac:
                        datos = [g.strip() for g in match_nac.groups()]
                        titulos, empresa, isin, mercado, tipo_op, precio, importe_op, comision_ing, gastos_bolsa, impuestos, importe_total = datos
                        comision_cambio = "0,00 EUR"
                    else:
                        titulos, empresa, isin, mercado, tipo_op, precio, importe_op, comision_ing, gastos_bolsa, impuestos, comision_cambio, importe_total = ["Revisar Manualmente"] * 12
                        
                    if match_fecha:
                        fecha_ejecucion = match_fecha.group(2).strip()[:10] 
                        tipo_orden = match_fecha.group(4).strip()
                        cambio_divisa = match_fecha.group(7).strip() if match_fecha.group(7) else "1,000 EUR"
                    else:
                        fechas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                        fecha_ejecucion = fechas[0] if fechas else "No encontrada"
                        tipo_orden = "Desconocido"
                        cambio_divisa = "Revisar"

                    datos_operaciones.append({
                        "Fecha": fecha_ejecucion,
                        "Operación": tipo_op,
                        "Tipo Orden": tipo_orden, 
                        "Empresa": empresa,
                        "ISIN": isin,
                        "Títulos": titulos,
                        "Precio": precio,
                        "Importe Op.": importe_op,
                        "Comisión ING": comision_ing,
                        "Gastos Bolsa": gastos_bolsa,
                        "Impuestos": impuestos,
                        "Comisión Cambio": comision_cambio,
                        "Importe Total": importe_total,
                        "Mercado": mercado,
                        "Divisa / Cambio": cambio_divisa,
                        "Archivo": archivo.name
                    })

        if datos_operaciones:
            st.success(f"¡Se procesaron {len(datos_operaciones)} archivo(s) con éxito!")
            df_op = pd.DataFrame(datos_operaciones)
            df_op['Fecha_Temporal'] = pd.to_datetime(df_op['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_op = df_op.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            st.dataframe(df_op)
            csv_op = df_op.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel", data=csv_op, file_name='operaciones_bolsa.csv', mime='text/csv')

# ==========================================
# 🚀 APLICACIÓN 3: RENOMBRADOR INTELIGENTE
# ==========================================
elif opcion == "🗂️ Renombrador de PDFs":
    st.title("🗂️ Renombrador Automático Inteligente")
    st.write("Sube **cualquier PDF de ING** (dividendos, compras o ventas mezclados). El sistema los identificará y nombrará automáticamente.")

    archivos_pdf_ren = st.file_uploader("Sube tus PDFs aquí", type=["pdf"], accept_multiple_files=True, key="ren")

    if archivos_pdf_ren:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for archivo in archivos_pdf_ren:
                with pdfplumber.open(archivo) as pdf:
                    texto = pdf.pages[0].extract_text(layout=True)
                    if not texto: texto = pdf.pages[0].extract_text()
                    
                    if texto:
                        fechas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                        fecha_ordenada = sorted(fechas, key=lambda f: f[6:] + f[3:5] + f[0:2])[0] if fechas else "00000000"
                        if fecha_ordenada != "00000000":
                            fecha_formateada = datetime.strptime(fecha_ordenada, "%d/%m/%Y").strftime("%Y%m%d")
                        else:
                            fecha_formateada = "00000000"

                        patron_trade = r"(\d+)\s+([A-Z0-9\s\.\-\&]+?)\s+([A-Z]{2}[A-Z0-9]{10})\s+([A-Z\s]+?)\s+(Compra|Venta)\s+([\d,]+\s+[A-Z]{3})"
                        match_trade = re.search(patron_trade, texto)

                        if match_trade:
                            empresa = match_trade.group(2).strip()
                            tipo_operacion = match_trade.group(5).strip().capitalize()
                            es_trade = True
                        else:
                            empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Empresa")
                            empresa = empresa.split("   ")[0].strip()
                            es_trade = False

                        empresa_limpia = re.sub(r'\(.*?\)', '', empresa) 
                        empresa_limpia = re.sub(r'[^a-zA-Z0-9]', ' ', empresa_limpia) 
                        empresa_limpia = "".join([palabra.capitalize() for palabra in empresa_limpia.split()])
                        
                        if es_trade:
                            nuevo_nombre = f"{fecha_formateada}-{tipo_operacion}{empresa_limpia}.pdf"
                        else:
                            nuevo_nombre = f"{fecha_formateada}-Dividendo{empresa_limpia}.pdf"
                            
                        archivo.seek(0)
                        zip_file.writestr(nuevo_nombre, archivo.read())
                        st.write(f"✅ Listo: `{archivo.name}` ➡️ **`{nuevo_nombre}`**")

        st.success("¡Todos los archivos han sido analizados y empaquetados!")
        st.download_button(label="📦 Descargar ZIP con PDFs renombrados", data=zip_buffer.getvalue(), file_name="Movimientos_Organizados.zip", mime="application/zip")
