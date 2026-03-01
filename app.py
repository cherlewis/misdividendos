Programa Payton backup de seguridad


import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import zipfile
import gc  
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
    try:
        limpio = re.sub(r'[^\d,.-]', '', str(euro_str))
        if not limpio: return 0.0
        return float(limpio.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def formatear_moneda(numero):
    return f"{numero:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

def formato_numero_tabla(numero):
    return f"{numero:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def calcular_retencion_recuperable(pct_str, bruto_str, ret_o_str):
    bruto = euro_a_numero(bruto_str)
    ret_o = euro_a_numero(ret_o_str)
    if pct_str in ["15%", "25%", "26,375%"]:
        max_recuperable = bruto * 0.15
        recuperable = min(ret_o, max_recuperable)
        return formato_numero_tabla(recuperable)
    return "0,00"

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
        "🗂️ Renombrador de PDFs",
        "📄 Informe Fiscal (Div. y DRIPs)",
        "⚖️ Auditoría Hacienda vs ING",
        "📉 Calculadora Plusvalías (Hacienda)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Sube tus documentos arrastrándolos todos a la vez.")

# ==========================================
# 🚀 APLICACIÓN 1: DIVIDENDOS Y DASHBOARD
# ==========================================
if opcion == "📊 Dividendos a Excel":
    st.title("📊 Extractor de Dividendos y Dashboard")
    st.write("Sube tus recibos de dividendos en PDF de ING para extraer los datos y ver tu resumen.")
    archivos_pdf = st.file_uploader("Sube tus PDFs aquí", type=["pdf"], accept_multiple_files=True, key="div")

    if archivos_pdf:
        datos_extraidos = []
        total_archivos = len(archivos_pdf)
        barra_progreso = st.progress(0)
        texto_estado = st.empty()

        for i, archivo in enumerate(archivos_pdf):
            texto_estado.text(f"⏳ Procesando ({i+1}/{total_archivos}): {archivo.name}...")
            try:
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
                        ret_recuperable = calcular_retencion_recuperable(pct_origen, bruto, ret_origen)
                        cuenta_abono = buscar_dato([r"(1465\s*0100\s*93\s*\d{10})"], texto, "N/A")
                        cuenta_valores = buscar_dato([r"(91\s*\d{10})"], texto, "0")

                        datos_extraidos.append({
                            "Fecha Abono": fecha_abono, "Concepto": concepto, "Importe Neto (€)": neto,
                            "Retención en origen (€)": ret_origen, "% retención en origen": pct_origen,
                            "Retención en destino (€)": ret_destino, "% retención en destino": pct_destino,
                            "Importe Bruto (€)": bruto, "Empresa": empresa, "Cuenta de Valores": cuenta_valores,
                            "Número de títulos": titulos, "Importe por título (€)": importe_titulo, "Cuenta Abono": cuenta_abono,
                            "Retención Recuperable (Max 15%) (€)": ret_recuperable
                        })
            except Exception as e:
                st.warning(f"⚠️ Error al procesar '{archivo.name}'. Se ha omitido.")
            
            gc.collect() 
            barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()

        if datos_extraidos:
            st.success(f"¡Se procesaron {len(datos_extraidos)} archivo(s) con éxito!")
            df = pd.DataFrame(datos_extraidos)
            df['Fecha_Temporal'] = pd.to_datetime(df['Fecha Abono'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            st.markdown("---")
            st.subheader("📈 Resumen de tus Dividendos")
            df['num_bruto'] = df['Importe Bruto (€)'].apply(euro_a_numero)
            df['num_neto'] = df['Importe Neto (€)'].apply(euro_a_numero)
            df['num_ret_origen'] = df['Retención en origen (€)'].apply(euro_a_numero)
            df['num_ret_destino'] = df['Retención en destino (€)'].apply(euro_a_numero)
            
            total_bruto = df['num_bruto'].sum()
            total_impuestos = df['num_ret_origen'].sum() + df['num_ret_destino'].sum()
            total_neto = df['num_neto'].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Bruto Generado", formatear_moneda(total_bruto))
            col2.metric("Impuestos Pagados (Total)", formatear_moneda(total_impuestos))
            col3.metric("Neto a la Cuenta", formatear_moneda(total_neto))
            
            st.write("")
            st.subheader("🌍 Desglose Fiscal (Nacional vs Extranjero)")
            def agrupar_pais(pct):
                if pct in ["15%", "25%", "26,375%"]: return "Extranjero (USA, Francia, Alemania)"
                elif pct == "0%": return "España (Nacional)"
                else: return "Otros"
            df['Grupo_Pais'] = df['% retención en origen'].apply(agrupar_pais)
            
            cols_paises = st.columns(2)
            for i, grupo in enumerate(["España (Nacional)", "Extranjero (USA, Francia, Alemania)"]):
                df_grupo = df[df['Grupo_Pais'] == grupo]
                with cols_paises[i]:
                    st.markdown(f"**{grupo}**")
                    st.write(f"💰 Bruto Total: **{formatear_moneda(df_grupo['num_bruto'].sum())}**")
                    st.write(f"🏛️ Ret. en Origen Total: **{formatear_moneda(df_grupo['num_ret_origen'].sum())}**")
                    
            st.markdown("---")
            df = df.drop(columns=['num_bruto', 'num_neto', 'num_ret_origen', 'num_ret_destino', 'Grupo_Pais'])
            
            fila_totales = {col: "" for col in df.columns}
            fila_totales["Fecha Abono"] = "TOTALES"
            cols_a_sumar = ["Importe Neto (€)", "Retención en origen (€)", "Retención en destino (€)", "Importe Bruto (€)", "Retención Recuperable (Max 15%) (€)"]
            for col in cols_a_sumar:
                suma = df[col].apply(euro_a_numero).sum()
                fila_totales[col] = formato_numero_tabla(suma)
            
            df = pd.concat([df, pd.DataFrame([fila_totales])], ignore_index=True)
            
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
        total_archivos = len(archivos_pdf_op)
        barra_progreso = st.progress(0)
        texto_estado = st.empty()

        for i, archivo in enumerate(archivos_pdf_op):
            texto_estado.text(f"⏳ Procesando ({i+1}/{total_archivos}): {archivo.name}...")
            try:
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
                            continue
                            
                        fecha_ejecucion = match_fecha.group(2).strip()[:10] if match_fecha else "No encontrada"
                        tipo_orden = match_fecha.group(4).strip() if match_fecha else "Desconocido"
                        cambio_divisa = (match_fecha.group(7).strip() if match_fecha.group(7) else "1,000 EUR") if match_fecha else "Revisar"

                        datos_operaciones.append({
                            "Fecha": fecha_ejecucion, "Operación": tipo_op, "Tipo Orden": tipo_orden, 
                            "Empresa": empresa, "ISIN": isin, "Títulos": titulos, "Precio": precio,
                            "Importe Op.": importe_op, "Comisión ING": comision_ing, "Gastos Bolsa": gastos_bolsa,
                            "Impuestos": impuestos, "Comisión Cambio": comision_cambio, "Importe Total": importe_total,
                            "Mercado": mercado, "Divisa / Cambio": cambio_divisa, "Archivo": archivo.name
                        })
            except Exception as e:
                st.warning(f"⚠️ Error al procesar '{archivo.name}'. Se ha omitido.")
            
            gc.collect()
            barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()

        if datos_operaciones:
            st.success(f"¡Se procesaron {len(datos_operaciones)} archivo(s) con éxito!")
            df_op = pd.DataFrame(datos_operaciones)
            df_op['Fecha_Temporal'] = pd.to_datetime(df_op['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_op = df_op.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            fila_totales = {col: "" for col in df_op.columns}
            fila_totales["Fecha"] = "TOTALES"
            cols_a_sumar_op = ["Importe Op.", "Comisión ING", "Gastos Bolsa", "Impuestos", "Comisión Cambio", "Importe Total"]
            for col in cols_a_sumar_op:
                suma = df_op[col].apply(euro_a_numero).sum()
                fila_totales[col] = f"{formato_numero_tabla(suma)} EUR"
            
            df_op = pd.concat([df_op, pd.DataFrame([fila_totales])], ignore_index=True)
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
        total_archivos = len(archivos_pdf_ren)
        barra_progreso = st.progress(0)
        texto_estado = st.empty()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, archivo in enumerate(archivos_pdf_ren):
                texto_estado.text(f"⏳ Analizando y renombrando ({i+1}/{total_archivos}): {archivo.name}...")
                try:
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
                except Exception as e:
                    st.warning(f"⚠️ Error al renombrar '{archivo.name}'. Se ha omitido.")

                gc.collect()
                barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()
        st.success("¡Todos los archivos procesables han sido empaquetados!")
        st.download_button(label="📦 Descargar ZIP con PDFs renombrados", data=zip_buffer.getvalue(), file_name="Movimientos_Organizados.zip", mime="application/zip")

# ==========================================
# 🚀 APLICACIÓN 4: INFORME FISCAL (DIVIDENDOS Y DRIPS)
# ==========================================
elif opcion == "📄 Informe Fiscal (Div. y DRIPs)":
    st.title("📄 Extractor Total del Informe Fiscal")
    st.write("Sube tu **Informe Fiscal Anual de ING** en PDF para extraer de golpe **todos los Dividendos** y **DRIPs**.")
    archivos_pdf_inf = st.file_uploader("Sube tu PDF de Datos Fiscales aquí", type=["pdf"], accept_multiple_files=True, key="inf")

    if archivos_pdf_inf:
        datos_informe = []
        total_archivos = len(archivos_pdf_inf)
        barra_progreso = st.progress(0)
        texto_estado = st.empty()

        for i, archivo in enumerate(archivos_pdf_inf):
            texto_estado.text(f"⏳ Analizando Informe Fiscal ({i+1}/{total_archivos}): {archivo.name}...")
            try:
                with pdfplumber.open(archivo) as pdf:
                    texto_completo = ""
                    for page in pdf.pages:
                        texto_pagina = page.extract_text(layout=True)
                        if not texto_pagina: texto_pagina = page.extract_text()
                        if texto_pagina: texto_completo += texto_pagina + "\n"
                    
                    if texto_completo:
                        lineas = texto_completo.split('\n')
                        patron_drip = r"(.*?)\s+(Nacional|Internacional)\s+(\d{2}/\d{2}/\d{4})\s+STOCK DIVIDEND\s+(\d+)\s+([\d.,]+)\s*€"
                        patron_div = r"(.*?)\s+(Nacional|Internacional)\s+DIVIDENDO\s+([\d,.]+)\s*€\s+([\d,.]+)\s*€(?:\s+([\d,.]+)\s*€)?"
                        
                        for idx, linea in enumerate(lineas):
                            match_drip = re.search(patron_drip, linea)
                            if match_drip:
                                empresa_part1 = match_drip.group(1).strip()
                                mercado = match_drip.group(2).strip()
                                fecha = match_drip.group(3).strip()
                                titulos = match_drip.group(4).strip()
                                importe = match_drip.group(5).strip()
                                
                                empresa_full = empresa_part1
                                isin_encontrado = "ISIN no encontrado"
                                
                                for j in range(1, 4):
                                    if idx + j >= len(lineas): break
                                    linea_siguiente = lineas[idx + j].strip()
                                    if not linea_siguiente: continue
                                    match_isin = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", linea_siguiente)
                                    if match_isin:
                                        isin_encontrado = match_isin.group(1)
                                        break
                                    else:
                                        palabra = linea_siguiente.split("   ")[0].strip()
                                        if palabra: empresa_full += " " + palabra

                                titulos_float = float(titulos) if titulos.isdigit() else 1.0
                                importe_float = euro_a_numero(importe)
                                imp_titulo = formato_numero_tabla(importe_float / titulos_float) if titulos_float > 0 else "0,00"

                                datos_informe.append({
                                    "Fecha Abono": fecha,
                                    "ISIN": isin_encontrado, 
                                    "Concepto": f"STOCK DIVIDENDO ({empresa_full})",
                                    "Importe Neto (€)": importe,
                                    "Retención en origen (€)": "0,00",
                                    "% retención en origen": "0%",
                                    "Retención en destino (€)": "0,00",
                                    "% retención en destino": "0%",
                                    "Importe Bruto (€)": importe,
                                    "Empresa": empresa_full,
                                    "Cuenta de Valores": "0",
                                    "Número de títulos": titulos,
                                    "Importe por título (€)": imp_titulo,
                                    "Cuenta Abono": "N/A",
                                    "Retención Recuperable (Max 15%) (€)": "0,00"
                                })
                                continue
                            
                            match_div = re.search(patron_div, linea)
                            if match_div:
                                empresa_raw = match_div.group(1).strip()
                                mercado = match_div.group(2).strip()
                                bruto = match_div.group(3).strip()
                                
                                if mercado == "Nacional":
                                    ret_origen = "0,00"
                                    ret_destino = match_div.group(4).strip()
                                else:
                                    ret_origen = match_div.group(4).strip()
                                    ret_destino = match_div.group(5).strip() if match_div.group(5) else "0,00"
                                
                                isin_encontrado = "ISIN no encontrado"
                                match_isin = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", empresa_raw)
                                if match_isin:
                                    isin_encontrado = match_isin.group(1)
                                    empresa_full = empresa_raw.replace(f"({isin_encontrado})", "").strip()
                                else:
                                    empresa_full = empresa_raw
                                    for j in range(1, 3):
                                        if idx + j < len(lineas):
                                            linea_siguiente = lineas[idx + j].strip()
                                            match_isin_next = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", linea_siguiente)
                                            if match_isin_next:
                                                isin_encontrado = match_isin_next.group(1)
                                                break

                                bruto_num = euro_a_numero(bruto)
                                ret_o_num = euro_a_numero(ret_origen)
                                ret_d_num = euro_a_numero(ret_destino)
                                neto_num = bruto_num - ret_o_num - ret_d_num
                                
                                pct_origen = calcular_porcentaje(ret_origen, bruto)
                                pct_destino = calcular_porcentaje(ret_destino, bruto)
                                ret_recuperable = calcular_retencion_recuperable(pct_origen, bruto, ret_origen)

                                datos_informe.append({
                                    "Fecha Abono": "Resumen 2024",
                                    "ISIN": isin_encontrado, 
                                    "Concepto": f"DIVIDENDO ({empresa_full})",
                                    "Importe Neto (€)": formato_numero_tabla(neto_num),
                                    "Retención en origen (€)": ret_origen,
                                    "% retención en origen": pct_origen,
                                    "Retención en destino (€)": ret_destino,
                                    "% retención en destino": pct_destino,
                                    "Importe Bruto (€)": bruto,
                                    "Empresa": empresa_full,
                                    "Cuenta de Valores": "0",
                                    "Número de títulos": "Varios", 
                                    "Importe por título (€)": "0,00",
                                    "Cuenta Abono": "N/A",
                                    "Retención Recuperable (Max 15%) (€)": ret_recuperable
                                })
            except Exception as e:
                st.warning(f"⚠️ Error al leer '{archivo.name}'. Se ha omitido.")
            
            gc.collect()
            barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()

        if datos_informe:
            st.success(f"¡Magia! Se extrajeron {len(datos_informe)} operaciones del informe fiscal.")
            df_informe = pd.DataFrame(datos_informe)
            
            columnas_ordenadas = ["Fecha Abono", "ISIN", "Concepto", "Importe Neto (€)", "Retención en origen (€)", 
                                  "% retención en origen", "Retención en destino (€)", "% retención en destino", 
                                  "Importe Bruto (€)", "Empresa", "Cuenta de Valores", "Número de títulos", 
                                  "Importe por título (€)", "Cuenta Abono", "Retención Recuperable (Max 15%) (€)"]
            df_informe = df_informe[columnas_ordenadas]
            
            fila_totales = {col: "" for col in df_informe.columns}
            fila_totales["Fecha Abono"] = "TOTALES"
            cols_a_sumar_inf = ["Importe Neto (€)", "Retención en origen (€)", "Retención en destino (€)", "Importe Bruto (€)", "Retención Recuperable (Max 15%) (€)"]
            for col in cols_a_sumar_inf:
                suma = df_informe[col].apply(euro_a_numero).sum()
                fila_totales[col] = formato_numero_tabla(suma)
            
            df_informe = pd.concat([df_informe, pd.DataFrame([fila_totales])], ignore_index=True)
            st.dataframe(df_informe)
            csv_informe = df_informe.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel (Con Totales)", data=csv_informe, file_name='informe_fiscal_completo.csv', mime='text/csv')


# ==========================================
# 🚀 APLICACIÓN 6: CALCULADORA DE PLUSVALÍAS
# ==========================================
elif opcion == "📉 Calculadora Plusvalías (Hacienda)":
    st.title("📉 Calculadora de Plusvalías (Valor de Adquisición y Transmisión)")
    st.markdown("Sube **exactamente 2 PDFs**: el justificante de la **Compra** y el de la **Venta**. El sistema calculará el resultado neto a declarar en Hacienda.")

    archivos_cv = st.file_uploader("Sube tus 2 PDFs (Compra y Venta) aquí", type=["pdf"], accept_multiple_files=True, key="cv")

    if archivos_cv:
        if len(archivos_cv) != 2:
            st.warning("⚠️ Por favor, sube exactamente 2 archivos (uno de compra y uno de venta) para poder hacer el cálculo.")
        else:
            operaciones = []
            for archivo in archivos_cv:
                try:
                    with pdfplumber.open(archivo) as pdf:
                        texto_layout = pdf.pages[0].extract_text(layout=True) or ""
                        texto_normal = pdf.pages[0].extract_text() or ""
                        texto_limpio = re.sub(r'\s+', ' ', texto_layout + " " + texto_normal)
                        
                        # 1. Encontrar Tipo de Operación y zona de números
                        patron_bloque = r'\b(Compra|Venta)\b(.*?)(?:Detalle de la orden|Cuenta de cargo|Podrá solicitar)'
                        match_op = re.search(patron_bloque, texto_limpio, re.IGNORECASE)
                        
                        tipo_op = "Desconocido"
                        importes = []
                        
                        if match_op:
                            tipo_op = match_op.group(1).capitalize()
                            zona_numeros = match_op.group(2)
                            importes = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', zona_numeros)
                        else:
                            match_tipo = re.search(r'\b(Compra|Venta)\b', texto_limpio, re.IGNORECASE)
                            if match_tipo: tipo_op = match_tipo.group(1).capitalize()
                            importes = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', texto_limpio)

                        # 2. Encontrar ISIN (Ignoramos las 'XXX')
                        isins = re.findall(r'\b[A-Z]{2}[A-Z0-9]{10}\b', texto_limpio)
                        isin = "Desconocido"
                        for i in isins:
                            if "XXX" not in i:
                                isin = i
                                break
                        
                        # 3. Encontrar Fecha
                        fechas = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', texto_limpio)
                        fecha = fechas[0] if fechas else "Desconocida"
                        
                        # 4. Cálculo Matemático de Títulos (Efectivo / Precio)
                        titulos = "0"
                        importe_total = "0,00"
                        
                        if len(importes) >= 2:
                            precio_ud = euro_a_numero(importes[0])
                            efectivo = euro_a_numero(importes[1])
                            importe_total = importes[-1]
                            
                            # Si el precio es mayor que 0, calculamos los títulos exactos
                            if precio_ud > 0:
                                titulos = str(int(round(efectivo / precio_ud)))
                                
                        operaciones.append({
                            "Tipo": tipo_op, 
                            "ISIN": isin, 
                            "Fecha": fecha, 
                            "Títulos": titulos,
                            "Importe Total": importe_total
                        })
                except Exception as e:
                    st.error(f"Error procesando {archivo.name}: {e}")
            
            compra = next((op for op in operaciones if op['Tipo'] == 'Compra'), None)
            venta = next((op for op in operaciones if op['Tipo'] == 'Venta'), None)

            if compra and venta:
                val_adquisicion = euro_a_numero(compra['Importe Total'])
                val_transmision = euro_a_numero(venta['Importe Total'])
                plusvalia = val_transmision - val_adquisicion
                
                st.markdown("---")
                st.subheader(f"📊 Resultado Fiscal: Acciones de {compra['ISIN']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**🛒 COMPRA (Valor Adquisición)**\n\nFecha: {compra['Fecha']}\n\nTítulos: **{compra['Títulos']}**\n\n**Total: {formatear_moneda(val_adquisicion)}**")
                with col2:
                    st.success(f"**💰 VENTA (Valor Transmisión)**\n\nFecha: {venta['Fecha']}\n\nTítulos: **{venta['Títulos']}**\n\n**Total: {formatear_moneda(val_transmision)}**")
                with col3:
                    if plusvalia > 0:
                        st.success(f"**📈 GANANCIA (Plusvalía)**\n\nA declarar en Hacienda:\n\n## + {formatear_moneda(plusvalia)}")
                    else:
                        st.error(f"**📉 PÉRDIDA (Minusvalía)**\n\nA compensar en Hacienda:\n\n## {formatear_moneda(plusvalia)}")
                
                st.markdown("---")
                st.markdown("💡 **Tip Fiscal:** Copia directamente el **Valor de Adquisición** y el **Valor de Transmisión** en la casilla de *Transmisión de acciones negociadas* de Renta Web. Las comisiones de ING ya están sumadas en la compra y restadas en la venta.")
            else:
                st.error(f"❌ No se han detectado los datos de Compra y Venta. Operaciones leídas:\n{operaciones}")
