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

def euro_a_numero(val):
    try:
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        
        limpio = re.sub(r'[^\d,.-]', '', str(val))
        if not limpio: return 0.0
        
        if ',' in limpio and '.' in limpio:
            if limpio.rfind(',') > limpio.rfind('.'):
                limpio = limpio.replace('.', '').replace(',', '.')
            else:
                limpio = limpio.replace(',', '')
        elif ',' in limpio:
            limpio = limpio.replace(',', '.')
            
        return float(limpio)
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
        "📊 Cuadro de Mando (Dashboard)",
        "📊 Dividendos a Excel", 
        "🛒 Compras/Ventas a Excel", 
        "🗂️ Renombrador de PDFs",
        "📄 Informe Fiscal (Div. y DRIPs)",
        "⚖️ Auditoría Hacienda vs ING",
        "📉 Calculadora Plusvalías (Hacienda)",
        "🏢 Gestor de Empresas (DB)",
        "⚖️ Auditoría Pro (DB)" # <--- La nueva joya
    ]
)




st.sidebar.markdown("---")
st.sidebar.info("💡 Sube tus documentos arrastrándolos todos a la vez.")




# ==========================================
# 🚀 APLICACIÓN 0: CUADRO DE MANDO (DASHBOARD)
# ==========================================
if opcion == "📊 Cuadro de Mando (Dashboard)":
    st.title("📊 Cuadro de Mando: Análisis de Cartera")
    st.write("Visualización interactiva de tu diversificación basada en tu Base de Datos.")

    try:
        from supabase import create_client, Client
        url: str = st.secrets["SUPABASE_URL"]
        key: str = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
        
        with st.spinner("Cargando datos estratégicos..."):
            respuesta = supabase.table("Empresas_Table").select("Sector, Subsector, Pais, NombreING").execute()
            df_dash = pd.DataFrame(respuesta.data)

        if not df_dash.empty:
            # --- MÉTRICAS RÁPIDAS ---
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Empresas", len(df_dash))
            col_m2.metric("Sectores", df_dash['Sector'].nunique())
            col_m3.metric("Países", df_dash['Pais'].nunique())

            st.markdown("---")

            # --- GRÁFICOS INTERACTIVOS (PLOTLY) ---
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.subheader("🌎 Diversificación por País")
                # Gráfico de tarta interactivo de Streamlit
                df_pais = df_dash['Pais'].value_counts().reset_index()
                df_pais.columns = ['País', 'Cantidad']
                st.write("Distribución porcentual:")
                st.vega_lite_chart(df_pais, {
                    'mark': {'type': 'arc', 'innerRadius': 50, 'tooltip': True},
                    'encoding': {
                        'theta': {'field': 'Cantidad', 'type': 'quantitative'},
                        'color': {'field': 'País', 'type': 'nominal', 'legend': {"orient": "bottom"}},
                    },
                }, use_container_width=True)

            with col_g2:
                st.subheader("🏗️ Diversificación por Sector")
                df_sect = df_dash['Sector'].value_counts().reset_index()
                df_sect.columns = ['Sector', 'Cantidad']
                st.write("Peso por industria:")
                st.vega_lite_chart(df_sect, {
                    'mark': {'type': 'arc', 'innerRadius': 50, 'tooltip': True},
                    'encoding': {
                        'theta': {'field': 'Cantidad', 'type': 'quantitative'},
                        'color': {'field': 'Sector', 'type': 'nominal', 'legend': {"orient": "bottom"}},
                    },
                }, use_container_width=True)

            st.markdown("---")
            
            # --- GRÁFICO DE BARRAS DE SUBSECTORES ---
            st.subheader("🔍 Análisis Detallado de Subsectores")
            df_sub = df_dash['Subsector'].value_counts().reset_index()
            df_sub.columns = ['Subsector', 'Empresas']
            df_sub = df_sub.sort_values('Empresas', ascending=False).head(15)
            
            st.bar_chart(df_sub.set_index('Subsector'))

            # --- TABLA DE APOYO ---
            st.markdown("---")
            with st.expander("📄 Ver listado completo de activos"):
                st.dataframe(df_dash.sort_values(by='Sector'), use_container_width=True)

        else:
            st.info("Aún no tienes empresas en tu base de datos. Ve a la pestaña '🏢 Gestor de Empresas' para añadir las primeras.")

    except Exception as e:
        st.error(f"⚠️ Error al cargar el Dashboard: {e}")







# ==========================================
# 🚀 APLICACIÓN 1: DIVIDENDOS
# ==========================================
if opcion == "📊 Dividendos a Excel":
    st.title("📄 Extractor de Dividendos a Excel")
    st.write("Sube tus PDFs de dividendos de ING. Optimizado para detectar importes 'totales' y fechas de abono.")
    archivos_pdf = st.file_uploader("Sube tus PDFs de Dividendos aquí", type=["pdf"], accept_multiple_files=True)

    if archivos_pdf:
        datos_dividendos = []
        total_archivos = len(archivos_pdf)
        barra_progreso = st.progress(0)
        texto_estado = st.empty()

        for i, archivo in enumerate(archivos_pdf):
            texto_estado.text(f"⏳ Procesando ({i+1}/{total_archivos}): {archivo.name}...")
            try:
                import pdfplumber
                with pdfplumber.open(archivo) as pdf:
                    texto = pdf.pages[0].extract_text()
                    
                    if texto:
                        # 1. EMPRESA: Buscamos "Valor:" pero ignoramos si viene de "Fecha valor"
                        # Usamos una búsqueda más precisa para evitar los encabezados
                        match_empresa = re.search(r"(?<!Fecha\s)Valor\s*[:\-]?\s*([A-Za-z0-9\.\-\&\' ]+)", texto, re.IGNORECASE)
                        empresa = match_empresa.group(1).strip() if match_empresa else "Empresa"
                        
                        if empresa == "Empresa" or "Cuenta de abono" in empresa:
                             # Intento B: Buscar línea que contenga INC, CORP, SA o similar
                             match_fallback = re.search(r"([A-Z][A-Z\s\.]+(?:INC|CORP|SA|PLC|AG|NV).*)", texto)
                             if match_fallback: empresa = match_fallback.group(1).strip()

                        if empresa != "Empresa":
                            empresa = empresa.split("   ")[0].split("(")[0].strip()

                        # 2. FECHAS: Priorizamos la fecha que NO sea la "Fecha valor"
                        fechas_todas = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
                        # En Pepsi, la fecha de abono suele ser la más reciente o la que aparece cerca de "Fecha" a secas
                        match_fecha_clara = re.search(r"(?<!valor\s)Fecha\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
                        fecha_abono = match_fecha_clara.group(1) if match_fecha_clara else (fechas_todas[-1] if fechas_todas else "00/00/0000")
                        
                        # 3. IMPORTES: Captura ultra-flexible (busca la etiqueta y luego el primer número con moneda)
                        def extraer_dinero(etiqueta, txt):
                            # Busca la etiqueta y salta cualquier palabra hasta encontrar un número con coma y moneda/símbolo
                            patron = etiqueta + r".*?([\d\.,]+\s*[A-Z€$]{1,3})"
                            res = re.search(patron, txt, re.IGNORECASE | re.DOTALL)
                            return res.group(1).strip() if res else "0,00 EUR"

                        importe_bruto = extraer_dinero("bruto", texto)
                        retencion_origen = extraer_dinero("origen", texto)
                        # Para destino, a veces ING solo pone "Retención:"
                        retencion_destino = extraer_dinero("destino", texto)
                        if retencion_destino == "0,00 EUR":
                            retencion_destino = extraer_dinero("Retención:", texto)
                            
                        importe_neto = extraer_dinero("neto", texto)
                        if importe_neto == "0,00 EUR":
                            importe_neto = extraer_dinero("líquido", texto)
                        
                        cambio_divisa = buscar_dato([r"Cambio\s*[:\-]?\s*([\d\.,]+)"], texto, "1,000")
                        titulos = buscar_dato([r"títulos\s*[:\-]?\s*([\d\.,]+)"], texto, "0")

                        datos_dividendos.append({
                            "Fecha": fecha_abono,
                            "Empresa_PDF": empresa,
                            "Títulos": titulos,
                            "Importe Bruto": importe_bruto,
                            "Ret. Origen": retencion_origen,
                            "Ret. Destino": retencion_destino,
                            "Importe Neto": importe_neto,
                            "Divisa / Cambio": cambio_divisa,
                            "Archivo": archivo.name
                        })
            except Exception as e:
                st.error(f"⚠️ Error al leer '{archivo.name}': {e}")
            
            import gc
            gc.collect()
            barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()

        if datos_dividendos:
            import pandas as pd
            df = pd.DataFrame(datos_dividendos)


            # --- CRUCE CON BASE DE DATOS (Con Traductor de Derechos) ---
            with st.spinner("🧠 Cruzando con tu Base de Datos..."):
                try:
                    from supabase import create_client, Client
                    url: str = st.secrets["SUPABASE_URL"]
                    key: str = st.secrets["SUPABASE_KEY"]
                    supabase: Client = create_client(url, key)
                    respuesta = supabase.table("Empresas_Table").select("ISIN, NombreING, Pais, Sector, Subsector, NombreHacienda").execute()
                    df_db = pd.DataFrame(respuesta.data)
                    db_nombre = {str(row["NombreING"]).upper().strip(): row.to_dict() for _, row in df_db.iterrows()} if not df_db.empty else {}

                    sectores, subsectores, paises, nombres_ing, nombres_hac, isins = [], [], [], [], [], []
                    
                    for _, row in df.iterrows():
                        emp_pdf = str(row["Empresa_PDF"]).upper().strip()
                        
                        # 🕵️‍♂️ TRADUCTOR DE DERECHOS (Igual que en la App 2)
                        # Si es un derecho, lo "traducimos" al nombre de la empresa matriz
                        if emp_pdf.startswith("IBE.D"): emp_pdf = "IBERDROLA"
                        elif emp_pdf.startswith("VIS.D"): emp_pdf = "VISCOFAN"
                        elif emp_pdf.startswith("VID.D"): emp_pdf = "VIDRALA"
                        elif emp_pdf.startswith("REP.D"): emp_pdf = "REPSOL"
                        elif emp_pdf.startswith("TEF.D"): emp_pdf = "TELEFONICA"
                        elif emp_pdf.startswith("ACS.D"): emp_pdf = "ACS"
                        elif emp_pdf.startswith("FER.D"): emp_pdf = "FERROVIAL"
                        elif emp_pdf.startswith("ELE.D"): emp_pdf = "ENDESA"

                        match = db_nombre.get(emp_pdf)
                        if not match:
                            for n_db, d_db in db_nombre.items():
                                if n_db in emp_pdf or emp_pdf in n_db:
                                    match = d_db; break
                        
                        if match:
                            sectores.append(match.get("Sector", "Pendiente"))
                            subsectores.append(match.get("Subsector", "Pendiente"))
                            paises.append(match.get("Pais", "Desconocido"))
                            isins.append(match.get("ISIN", ""))
                            nombres_ing.append(match.get("NombreING", row["Empresa_PDF"]))
                            nombres_hac.append(match.get("NombreHacienda", ""))
                        else:
                            sectores.append("Pendiente")
                            subsectores.append("Pendiente")
                            paises.append("Desconocido")
                            isins.append("")
                            nombres_ing.append(row["Empresa_PDF"])
                            nombres_hac.append("Revisar")

                    df["Sector"], df["Subsector"], df["Pais"] = sectores, subsectores, paises
                    df["ISIN"], df["NombreING"], df["NombreHacienda"] = isins, nombres_ing, nombres_hac

                    
                    cols_finales = ["Fecha", "NombreING", "ISIN", "Pais", "Sector", "Subsector", "Títulos", "Importe Bruto", "Ret. Origen", "Ret. Destino", "Importe Neto", "Divisa / Cambio", "NombreHacienda", "Archivo"]
                    df = df[cols_finales]
                except Exception as e:
                    st.error(f"⚠️ Error al cruzar datos: {e}")

            st.success(f"¡Se procesaron {len(df)} archivo(s) con éxito!")
            df['Fecha_Temporal'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])

            # Fila de Totales
            fila_totales = {col: "" for col in df.columns}
            fila_totales["Fecha"] = "TOTALES"
            for col in ["Importe Bruto", "Ret. Origen", "Ret. Destino", "Importe Neto"]:
                suma = df[col].apply(lambda x: euro_a_numero(str(x)) if pd.notnull(x) and x != "" and str(x) != "0,00 EUR" else 0).sum()
                fila_totales[col] = f"{formato_numero_tabla(suma)} EUR"
            
            df = pd.concat([df, pd.DataFrame([fila_totales])], ignore_index=True)
            st.dataframe(df)
            csv = df.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel Enriquecido", data=csv, file_name='dividendos_enriquecidos.csv', mime='text/csv')









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
                        # 🔒 CANDADO HORIZONTAL: Usamos [ \t] en lugar de \s para que NO salte de línea y lea tu nombre
                        patron_int = r"(\d[\d\.]*)[ \t]+([A-Za-z0-9\.\-\&\' ]+?)[ \t]+([A-Z]{2}[A-Z0-9]{10})[ \t]+([A-Za-z0-9\.\-\(\) ]+?)[ \t]+(Compra|Venta)[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})"
                        patron_nac = r"(\d[\d\.]*)[ \t]+([A-Za-z0-9\.\-\&\' ]+?)[ \t]+([A-Z]{2}[A-Z0-9]{10})[ \t]+([A-Za-z0-9\.\-\(\) ]+?)[ \t]+(Compra|Venta)[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})[ \t]+([\d,]+[ \t]*[A-Z]{3})"
                        
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
                            "Empresa_PDF": empresa, "ISIN": isin, "Títulos": titulos, "Precio": precio,
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
            df_op = pd.DataFrame(datos_operaciones)
            
            # ==========================================
            # 🧠 LA MAGIA: CRUCE CON BASE DE DATOS
            # ==========================================
            with st.spinner("🧠 Cruzando datos y traduciendo derechos..."):
                try:
                    from supabase import create_client, Client
                    url: str = st.secrets["SUPABASE_URL"]
                    key: str = st.secrets["SUPABASE_KEY"]
                    supabase: Client = create_client(url, key)
                    
                    respuesta = supabase.table("Empresas_Table").select("ISIN, NombreING, Pais, Sector, Subsector, NombreHacienda").execute()
                    df_db = pd.DataFrame(respuesta.data)
                    
                    if not df_db.empty:
                        df_db_limpio = df_db.dropna(subset=['ISIN']).drop_duplicates(subset=['ISIN'])
                        db_isin = df_db_limpio.set_index("ISIN").to_dict("index")
                        
                        # 🔧 LA SOLUCIÓN: Añadimos .to_dict() para que Pandas no se vuelva loco al comprobar si existe
                        db_nombre = {str(row["NombreING"]).upper(): row.to_dict() for _, row in df_db.iterrows()}
                    else:
                        db_isin = {}
                        db_nombre = {}

                    # 🕵️‍♂️ TRADUCTOR DE DERECHOS ESPAÑOLES
                    def normalizar_derechos(nombre_pdf):
                        n = str(nombre_pdf).upper()
                        if n.startswith("IBE.D"): return "IBERDROLA"
                        if n.startswith("VIS.D"): return "VISCOFAN"
                        if n.startswith("VID.D"): return "VIDRALA"
                        if n.startswith("REP.D"): return "REPSOL"
                        if n.startswith("TEF.D"): return "TELEFONICA"
                        if n.startswith("ACS.D"): return "ACS"
                        if n.startswith("FER.D"): return "FERROVIAL"
                        if n.startswith("SAB.D"): return "BANCO SABADELL"
                        if n.startswith("ELE.D"): return "ENDESA"
                        return n

                    sectores, subsectores, paises, nombres_ing, nombres_hac = [], [], [], [], []

                    for _, row in df_op.iterrows():
                        isin_op = str(row["ISIN"])
                        empresa_pdf = str(row["Empresa_PDF"])
                        nombre_norm = normalizar_derechos(empresa_pdf)
                        
                        match = None
                        if isin_op in db_isin:
                            match = db_isin[isin_op]
                        elif nombre_norm in db_nombre:
                            match = db_nombre[nombre_norm]
                            
                        # Ahora 'match' siempre será un diccionario limpio, y el 'if' funcionará perfectamente
                        if match:
                            sectores.append(match.get("Sector", "Pendiente de Clasificar"))
                            subsectores.append(match.get("Subsector", "Pendiente de Clasificar"))
                            paises.append(match.get("Pais", "Desconocido"))
                            nombres_ing.append(match.get("NombreING", empresa_pdf))
                            nombres_hac.append(match.get("NombreHacienda", ""))
                        else:
                            sectores.append("Pendiente de Clasificar")
                            subsectores.append("Pendiente de Clasificar")
                            paises.append("Desconocido")
                            nombres_ing.append(empresa_pdf)
                            nombres_hac.append(f"CODIGO: {isin_op}")

                    df_op["Sector"] = sectores
                    df_op["Subsector"] = subsectores
                    df_op["Pais"] = paises
                    df_op["NombreING"] = nombres_ing
                    df_op["NombreHacienda"] = nombres_hac

                    columnas_finales = [
                        "Fecha", "Operación", "NombreING", "ISIN", "Pais", "Sector", "Subsector", 
                        "Títulos", "Precio", "Importe Op.", "Comisión ING", "Gastos Bolsa", 
                        "Impuestos", "Comisión Cambio", "Importe Total", "Mercado", "Divisa / Cambio", 
                        "NombreHacienda", "Archivo"
                    ]
                    df_op = df_op[columnas_finales]
                except Exception as e:
                    st.error(f"⚠️ Error técnico real del cruce: {e}")
                    st.warning("Generando Excel básico...")
            # ==========================================
            # ==========================================
            # ==========================================

            st.success(f"¡Se procesaron y cruzaron {len(df_op)} archivo(s) con éxito!")
            df_op['Fecha_Temporal'] = pd.to_datetime(df_op['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_op = df_op.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
            
            fila_totales = {col: "" for col in df_op.columns}
            fila_totales["Fecha"] = "TOTALES"
            cols_a_sumar_op = ["Importe Op.", "Comisión ING", "Gastos Bolsa", "Impuestos", "Comisión Cambio", "Importe Total"]
            for col in cols_a_sumar_op:
                suma = df_op[col].apply(lambda x: euro_a_numero(str(x)) if pd.notnull(x) and x != "" else 0).sum()
                fila_totales[col] = f"{formato_numero_tabla(suma)} EUR"
            
            df_op = pd.concat([df_op, pd.DataFrame([fila_totales])], ignore_index=True)
            
            st.dataframe(df_op)
            csv_op = df_op.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel Enriquecido", data=csv_op, file_name='operaciones_bolsa_enriquecido.csv', mime='text/csv')

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
                            match_isin = re.search(r"([A-Z]{2}[A-Z0-9]{10})", texto)
                            match_tipo = re.search(r"\b(Compra|Venta)\b", texto, re.IGNORECASE)
                            
                            if match_isin and match_tipo and "Tipo de orden" in texto:
                                es_trade = True
                                tipo_operacion = match_tipo.group(1).capitalize()
                                match_ejecucion = re.search(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}", texto)
                                if match_ejecucion:
                                    fecha_ordenada = match_ejecucion.group(1)
                                else:
                                    fecha_ordenada = fechas[1] if len(fechas) >= 2 else (fechas[0] if fechas else "00000000")
                                
                                # 🔒 CANDADO HORIZONTAL EN EL RENOMBRADOR
                                match_linea = re.search(rf"(\d[\d\.]*)[ \t]+([A-Za-z0-9\.\-\&\' ]+?)[ \t]+{match_isin.group(1)}", texto)
                                empresa = match_linea.group(2).strip() if match_linea else match_isin.group(1)
                            else:
                                es_trade = False
                                fecha_ordenada = sorted(fechas, key=lambda f: f[6:] + f[3:5] + f[0:2])[0] if fechas else "00000000"
                                empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Empresa")
                                empresa = empresa.split("   ")[0].strip()

                            fecha_formateada = datetime.strptime(fecha_ordenada, "%d/%m/%Y").strftime("%Y%m%d") if fecha_ordenada != "00000000" else "00000000"

                            # 🕵️‍♂️ TRADUCTOR DE NOMBRES PARA EL PDF FINAL
                            n_upper = empresa.upper()
                            if n_upper.startswith("IBE.D"): empresa = "DerechosIberdrola"
                            elif n_upper.startswith("VIS.D"): empresa = "DerechosViscofan"
                            elif n_upper.startswith("VID.D"): empresa = "DerechosVidrala"
                            elif n_upper.startswith("REP.D"): empresa = "DerechosRepsol"
                            elif n_upper.startswith("TEF.D"): empresa = "DerechosTelefonica"
                            elif n_upper.startswith("ACS.D"): empresa = "DerechosACS"
                            elif n_upper.startswith("FER.D"): empresa = "DerechosFerrovial"
                            elif n_upper.startswith("SAB.D"): empresa = "DerechosBancoSabadell"
                            elif n_upper.startswith("ELE.D"): empresa = "DerechosEndesa"
                            else:
                                empresa_limpia = re.sub(r'\(.*?\)', '', empresa) 
                                empresa_limpia = re.sub(r'[^a-zA-Z0-9]', ' ', empresa_limpia) 
                                empresa = "".join([palabra.capitalize() for palabra in empresa_limpia.split()])
                            
                            if es_trade:
                                nuevo_nombre = f"{fecha_formateada}-{tipo_operacion}{empresa}.pdf"
                            else:
                                nuevo_nombre = f"{fecha_formateada}-Dividendo{empresa}.pdf"
                                
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

    def formato_hacienda(val):
        return f"{euro_a_numero(val):.2f}"
        
    def obtener_bandera(isin, empresa):
        if isinstance(isin, str) and len(isin) >= 2 and isin != "ISIN no encontrado":
            prefijo = isin[:2].upper()
            banderas = {
                "ES": "🇪🇸 España", "US": "🇺🇸 USA", "DE": "🇩🇪 Alemania", 
                "FR": "🇫🇷 Francia", "NL": "🇳🇱 Países Bajos", "GB": "🇬🇧 Reino Unido", 
                "IE": "🇮🇪 Irlanda", "CH": "🇨🇭 Suiza", "IT": "🇮🇹 Italia",
                "BE": "🇧🇪 Bélgica", "PT": "🇵🇹 Portugal", "SE": "🇸🇪 Suecia",
                "CA": "🇨🇦 Canadá", "JP": "🇯🇵 Japón", "AU": "🇦🇺 Australia"
            }
            if prefijo in banderas:
                return banderas[prefijo]
        
        empresa_mayus = str(empresa).upper()
        
        # 📚 DICCIONARIO INFALIBLE 
        conocidas = {
            "BASF": "🇩🇪 Alemania", "ALLIANZ": "🇩🇪 Alemania",
            "LOUIS VUITTON": "🇫🇷 Francia", "LVMH": "🇫🇷 Francia",
            "AHOLD": "🇳🇱 Países Bajos", "ASML": "🇳🇱 Países Bajos",
            "MONDI": "🇬🇧 Reino Unido", "PEPSICO": "🇺🇸 USA",
            "T ROWE PRICE": "🇺🇸 USA", "MCDONALDS": "🇺🇸 USA",
            "3M CO": "🇺🇸 USA", "TYSON FOODS": "🇺🇸 USA",
            "REALTY INCOME": "🇺🇸 USA", "W.P. CAREY": "🇺🇸 USA",
            "AMERICAN TOWER": "🇺🇸 USA", "VERIZON": "🇺🇸 USA",
            "INTEL": "🇺🇸 USA", "PHILIP MORRIS": "🇺🇸 USA",
            "BRITISH AMERICAN": "🇬🇧 Reino Unido",
            "VODAFONE": "🇬🇧 Reino Unido",
            "ASSOCIATED BRITISH": "🇬🇧 Reino Unido",
            "DIAGEO": "🇬🇧 Reino Unido"
        }
        
        for clave, pais in conocidas.items():
            if clave in empresa_mayus:
                return pais
                
        if " INC" in empresa_mayus or " CORP" in empresa_mayus or " LLC" in empresa_mayus: return "🇺🇸 USA"
        if " NV" in empresa_mayus: return "🇳🇱 Países Bajos"
        if " AG" in empresa_mayus: return "🇩🇪 Alemania"
        if " PLC" in empresa_mayus: return "🇬🇧 Reino Unido"
        if " SA" in empresa_mayus: return "🇪🇸/🇫🇷 SA"
            
        return "🏳️ Desconocido"

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
                                imp_titulo = importe_float / titulos_float if titulos_float > 0 else 0.0

                                datos_informe.append({
                                    "Fecha Abono": fecha,
                                    "ISIN": isin_encontrado, 
                                    "Concepto": f"STOCK DIVIDENDO ({empresa_full})",
                                    "Importe Neto (€)": formato_hacienda(importe),
                                    "Retención en origen (€)": "0.00",
                                    "% retención en origen": "0%",
                                    "Retención en destino (€)": "0.00",
                                    "% retención en destino": "0%",
                                    "Importe Bruto (€)": formato_hacienda(importe),
                                    "Empresa": empresa_full,
                                    "País": obtener_bandera(isin_encontrado, empresa_full),
                                    "Cuenta de Valores": "0",
                                    "Número de títulos": titulos,
                                    "Importe por título (€)": f"{imp_titulo:.2f}",
                                    "Cuenta Abono": "N/A",
                                    "Retención Recuperable (Max 15%) (€)": "0.00"
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
                                    "Importe Neto (€)": f"{neto_num:.2f}",
                                    "Retención en origen (€)": formato_hacienda(ret_origen),
                                    "% retención en origen": pct_origen,
                                    "Retención en destino (€)": formato_hacienda(ret_destino),
                                    "% retención en destino": pct_destino,
                                    "Importe Bruto (€)": formato_hacienda(bruto),
                                    "Empresa": empresa_full,
                                    "País": obtener_bandera(isin_encontrado, empresa_full),
                                    "Cuenta de Valores": "0",
                                    "Número de títulos": "Varios", 
                                    "Importe por título (€)": "0.00",
                                    "Cuenta Abono": "N/A",
                                    "Retención Recuperable (Max 15%) (€)": formato_hacienda(ret_recuperable)
                                })
            except Exception as e:
                st.warning(f"⚠️ Error al leer '{archivo.name}'. Se ha omitido.")
            
            gc.collect()
            barra_progreso.progress((i + 1) / total_archivos)

        texto_estado.empty()

        if datos_informe:
            st.success(f"¡Magia! Se extrajeron {len(datos_informe)} operaciones del informe fiscal en formato Hacienda.")
            
            total_bruto_029 = sum(euro_a_numero(d["Importe Bruto (€)"]) for d in datos_informe)
            
            datos_ext = [d for d in datos_informe if d["% retención en origen"] in ["15%", "25%", "26,375%"]]
            total_bruto_588 = sum(euro_a_numero(d["Importe Bruto (€)"]) for d in datos_ext)
            total_neto_588 = sum(euro_a_numero(d["Importe Neto (€)"]) for d in datos_ext)
            total_ret_recup_588 = sum(euro_a_numero(d["Retención Recuperable (Max 15%) (€)"]) for d in datos_ext)

            st.markdown("---")
            st.header("📝 Resumen Automático para la Renta")
            
            st.info("**Casilla 029** (Dividendos y demás rendimientos por la participación en fondos propios de entidades)")
            st.metric("Suma Total Dividendo Bruto", f"{total_bruto_029:.2f} €")
            
            st.info("**Casilla 588** (Deducción por doble imposición internacional)")
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Total Brutos (USA/FRA/ALE)", f"{total_bruto_588:.2f} €")
            col_r2.metric("Total Netos (USA/FRA/ALE)", f"{total_neto_588:.2f} €")
            col_r3.metric("Retención Recuperable (Máx 15%)", f"{total_ret_recup_588:.2f} €")
            st.caption("*Nota: La retención ya está calculada aplicando automáticamente el tope máximo legal del 15% para países como Alemania o Francia.*")
            st.markdown("---")

            df_informe = pd.DataFrame(datos_informe)
            
            columnas_ordenadas = ["Fecha Abono", "ISIN", "Concepto", "Importe Neto (€)", "Retención en origen (€)", 
                                  "% retención en origen", "Retención en destino (€)", "% retención en destino", 
                                  "Importe Bruto (€)", "Empresa", "País", "Cuenta de Valores", "Número de títulos", 
                                  "Importe por título (€)", "Cuenta Abono", "Retención Recuperable (Max 15%) (€)"]
            df_informe = df_informe[columnas_ordenadas]
            
            fila_totales = {col: "" for col in df_informe.columns}
            fila_totales["Fecha Abono"] = "TOTALES"
            cols_a_sumar_inf = ["Importe Neto (€)", "Retención en origen (€)", "Retención en destino (€)", "Importe Bruto (€)", "Retención Recuperable (Max 15%) (€)"]
            for col in cols_a_sumar_inf:
                suma = df_informe[col].apply(euro_a_numero).sum()
                fila_totales[col] = f"{suma:.2f}"
            
            df_informe = pd.concat([df_informe, pd.DataFrame([fila_totales])], ignore_index=True)
            st.dataframe(df_informe)
            csv_informe = df_informe.to_csv(index=False, sep=";").encode('utf-8-sig')
            st.download_button(label="⬇️ Descargar Excel (Formato AEAT)", data=csv_informe, file_name='informe_fiscal_completo.csv', mime='text/csv')

# ==========================================
# 🚀 APLICACIÓN 5: AUDITORÍA HACIENDA VS ING
# ==========================================
elif opcion == "⚖️ Auditoría Hacienda vs ING":
    st.title("⚖️ Auditor Inteligente (Basado en Importes)")
    st.markdown("""**¡El fin del caos con los nombres y los ISINs!**
    Como Hacienda y los bancos usan nombres distintos para las acciones extranjeras, este auditor cruza los datos usando **el importe exacto del dividendo**. 
    Si Hacienda dice que cobraste 88,40€ y ING dice que Logista te pagó 88,40€, el sistema los unirá automáticamente.""")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1️⃣ Sube tu Excel de ING")
        archivo_ing = st.file_uploader("Sube el archivo CSV de ING (App 4)", type=["csv"], key="ing_audit")
    with col2:
        st.subheader("2️⃣ Sube los Datos de Hacienda")
        archivo_aeat = st.file_uploader("Sube el Excel/CSV de la AEAT", type=["csv", "xlsx", "xls"], key="aeat_audit")

    if archivo_ing and archivo_aeat:
        try:
            df_ing = pd.read_csv(archivo_ing, sep=";")
            df_ing = df_ing[df_ing["Fecha Abono"] != "TOTALES"]
            
            if archivo_aeat.name.endswith('.csv'):
                df_aeat = pd.read_csv(archivo_aeat, sep=None, engine='python')
            else:
                df_aeat = pd.read_excel(archivo_aeat, engine='openpyxl')

            col_bruto_aeat = "Importe Íntegro" if "Importe Íntegro" in df_aeat.columns else df_aeat.columns[7]
            col_ret_aeat = "Retenciones" if "Retenciones" in df_aeat.columns else df_aeat.columns[9]
            col_nom_aeat = "Nombre Emisor" if "Nombre Emisor" in df_aeat.columns else df_aeat.columns[2]

            st.success("¡Archivos cargados! Cruzando los datos por coincidencia de importes...")

            df_ing['Bruto_Num'] = df_ing['Importe Bruto (€)'].apply(euro_a_numero).round(2)
            df_ing['Ret_Num'] = df_ing['Retención en destino (€)'].apply(euro_a_numero).round(2)
            
            df_ing = df_ing[df_ing['Bruto_Num'] > 0]

            ing_agrup = df_ing.groupby('Bruto_Num').agg({
                'Empresa': lambda x: ' + '.join(x.unique()),
                'Ret_Num': 'sum'
            }).reset_index()
            ing_agrup.rename(columns={'Bruto_Num': 'Importe Bruto', 'Empresa': 'Empresa(s) en ING', 'Ret_Num': 'Retención ING'}, inplace=True)

            df_aeat['Bruto_Num'] = df_aeat[col_bruto_aeat].apply(euro_a_numero).round(2)
            df_aeat['Ret_Num'] = df_aeat[col_ret_aeat].apply(euro_a_numero).round(2)
            df_aeat = df_aeat[df_aeat['Bruto_Num'] > 0]

            def limpiar_nombre_aeat(x):
                return str(x).replace("CODIGO:", "ISIN:").strip()
            df_aeat['Nombre Limpio'] = df_aeat[col_nom_aeat].apply(limpiar_nombre_aeat)

            aeat_agrup = df_aeat.groupby('Bruto_Num').agg({
                'Nombre Limpio': lambda x: ' + '.join(x.unique()),
                'Ret_Num': 'sum'
            }).reset_index()
            aeat_agrup.rename(columns={'Bruto_Num': 'Importe Bruto', 'Nombre Limpio': 'Emisor(es) en Hacienda', 'Ret_Num': 'Retención AEAT'}, inplace=True)

            df_cruce = pd.merge(ing_agrup, aeat_agrup, on='Importe Bruto', how='outer').fillna(0)

            df_cruce['Empresa(s) en ING'] = df_cruce['Empresa(s) en ING'].replace(0, "❌ No consta en tu ING")
            df_cruce['Emisor(es) en Hacienda'] = df_cruce['Emisor(es) en Hacienda'].replace(0, "❌ Falta en tu Borrador")
            
            df_cruce['Dif. Retención'] = (df_cruce['Retención ING'] - df_cruce['Retención AEAT']).round(2)

            def determinar_estado(row):
                if row['Empresa(s) en ING'] == "❌ No consta en tu ING": return "🔴 Añadido por Hacienda"
                if row['Emisor(es) en Hacienda'] == "❌ Falta en tu Borrador": return "🔴 Te falta declararlo"
                if abs(row['Dif. Retención']) > 0.05: return "🟡 Falla la Retención"
                return "🟢 Cuadra Perfecto"

            df_cruce['Estado'] = df_cruce.apply(determinar_estado, axis=1)

            df_cruce['Importe Bruto (€)'] = df_cruce['Importe Bruto'].apply(formato_numero_tabla)
            df_cruce['Ret. ING (€)'] = df_cruce['Retención ING'].apply(formato_numero_tabla)
            df_cruce['Ret. AEAT (€)'] = df_cruce['Retención AEAT'].apply(formato_numero_tabla)
            df_cruce['Diferencia Ret. (€)'] = df_cruce['Dif. Retención'].apply(formato_numero_tabla)

            df_cruce = df_cruce.sort_values(by='Estado', ascending=False)
            
            df_final = df_cruce[['Importe Bruto (€)', 'Empresa(s) en ING', 'Emisor(es) en Hacienda', 'Ret. ING (€)', 'Ret. AEAT (€)', 'Diferencia Ret. (€)', 'Estado']]

            st.markdown("---")
            st.subheader("📋 Tabla de Auditoría (Vinculada por Importes)")
            
            st.dataframe(
                df_final.style.applymap(
                    lambda x: 'background-color: #d4edda' if '🟢' in str(x) 
                    else ('background-color: #f8d7da' if '🔴' in str(x) 
                    else ('background-color: #fff3cd' if '🟡' in str(x) else '')), 
                    subset=['Estado']
                ),
                use_container_width=True
            )

        except Exception as e:
            st.error(f"❌ Error al procesar los archivos. Detalles: {e}")

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
                        
                        tipo_op = "Desconocido"
                        importe_total = "0,00"
                        titulos = "0"
                        
                        match_tipo = re.search(r'\b(Compra|Venta)\b\s+(?=\d)', texto_limpio, re.IGNORECASE)
                        
                        if match_tipo:
                            tipo_op = match_tipo.group(1).capitalize()
                            idx = match_tipo.end()
                            
                            zona_cruda = texto_limpio[idx:idx+300]
                            zona_numeros = re.split(r'(?:ES\d{10}|\b\d{2}/\d{2}/\d{4}\b|Cuenta|Detalle|Limitada)', zona_cruda, flags=re.IGNORECASE)[0]
                            importes = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', zona_numeros)
                            
                            if len(importes) >= 2:
                                precio_ud = euro_a_numero(importes[0])
                                efectivo = euro_a_numero(importes[1])
                                importe_total = importes[-1] 
                                
                                if precio_ud > 0:
                                    titulos = str(int(round(efectivo / precio_ud)))

                        isins = re.findall(r'\b[A-Z]{2}[A-Z0-9]{10}\b', texto_limpio)
                        isin = "Desconocido"
                        for i in isins:
                            if "XXX" not in i:
                                isin = i
                                break
                        
                        fechas = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', texto_limpio)
                        fecha = fechas[0] if fechas else "Desconocida"
                        
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
                st.error(f"❌ Faltan datos. Operaciones detectadas:\n{operaciones}")






# ==========================================
# 🚀 APLICACIÓN 7: GESTOR DE EMPRESAS (SUPABASE)
# ==========================================
elif opcion == "🏢 Gestor de Empresas (DB)":
    st.title("🏢 Gestor de Base de Datos de Empresas")
    st.write("Conectado a tu base de datos Supabase en tiempo real.")

    # 1. Conexión limpia a Supabase
    try:
        from supabase import create_client, Client
        url: str = st.secrets["SUPABASE_URL"]
        key: str = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        st.stop()

    # 2. Función para leer los datos
    def cargar_empresas():
        respuesta = supabase.table("Empresas_Table").select("*").order("NombreING").execute()
        return pd.DataFrame(respuesta.data)

    df_empresas = cargar_empresas()

    # 3. Interfaz con 5 Pestañas (¡Añadida la pestaña de Peligro!)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Añadir", "✏️ Editar", "📋 Ver Tabla", "🔄 Importar / Exportar", "🚨 Peligro"])

    # --- PESTAÑA 1: AÑADIR ---
    with tab1:
        st.subheader("Añadir una nueva empresa")
        with st.form("form_add", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                isin_add = st.text_input("ISIN (ej. US7134481081)")
                nombre_add = st.text_input("Nombre en ING (ej. PEPSICO)")
                nombre_hac_add = st.text_input("Nombre en Hacienda (ej. CODIGO: US7134481081)")
            with col2:
                pais_add = st.text_input("País (ej. 🇺🇸 USA)")
                sector_add = st.text_input("Sector (ej. Consumo Defensivo)")
                subsector_add = st.text_input("Subsector (ej. Bebidas)")

            submit_add = st.form_submit_button("💾 Guardar Empresa")
            if submit_add:
                if nombre_add and isin_add:
                    nueva_empresa = {
                        "ISIN": isin_add, 
                        "NombreING": nombre_add,
                        "NombreHacienda": nombre_hac_add,
                        "Pais": pais_add, 
                        "Sector": sector_add, 
                        "Subsector": subsector_add
                    }
                    supabase.table("Empresas_Table").insert(nueva_empresa).execute()
                    st.success(f"✅ ¡{nombre_add} guardada correctamente!")
                    import time
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("⚠️ El Nombre en ING y el ISIN son obligatorios.")

    # --- PESTAÑA 2: EDITAR ---
    with tab2:
        st.subheader("Editar datos de una empresa")
        if not df_empresas.empty:
            empresa_seleccionada = st.selectbox("Selecciona la empresa:", df_empresas['NombreING'].tolist())
            datos_actuales = df_empresas[df_empresas['NombreING'] == empresa_seleccionada].iloc[0]

            with st.form("form_edit"):
                col1, col2 = st.columns(2)
                with col1:
                    isin_ed = st.text_input("ISIN", value=datos_actuales.get('ISIN', ''))
                    nombre_ed = st.text_input("Nombre en ING", value=datos_actuales.get('NombreING', ''))
                    nombre_hac_ed = st.text_input("Nombre en Hacienda", value=datos_actuales.get('NombreHacienda', '') or '')
                with col2:
                    pais_ed = st.text_input("País", value=datos_actuales.get('Pais', '') or '')
                    sector_ed = st.text_input("Sector", value=datos_actuales.get('Sector', '') or '')
                    subsector_ed = st.text_input("Subsector", value=datos_actuales.get('Subsector', '') or '')

                submit_edit = st.form_submit_button("🔄 Actualizar Cambios")
                if submit_edit:
                    cambios = {
                        "ISIN": isin_ed, 
                        "NombreING": nombre_ed,
                        "NombreHacienda": nombre_hac_ed,
                        "Pais": pais_ed, 
                        "Sector": sector_ed, 
                        "Subsector": subsector_ed
                    }
                    supabase.table("Empresas_Table").update(cambios).eq("id", str(datos_actuales['id'])).execute()
                    st.success(f"✅ ¡Datos de {nombre_ed} actualizados!")
                    import time
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("No hay empresas en la base de datos todavía.")

    # --- PESTAÑA 3: VER TABLA ---
    with tab3:
        st.subheader("Base de Datos Actual")
        if not df_empresas.empty:
            columnas_mostrar = ["ISIN", "NombreING", "Pais", "Sector", "Subsector", "NombreHacienda"]
            st.dataframe(df_empresas[columnas_mostrar], use_container_width=True)
            st.metric("Total de Empresas", len(df_empresas))
        else:
            st.write("La base de datos está vacía.")

    # --- PESTAÑA 4: IMPORTAR / EXPORTAR ---
    with tab4:
        col_imp, col_exp = st.columns(2)
        
        with col_exp:
            st.subheader("📤 Copia de Seguridad")
            st.write("Descarga todas tus empresas en formato Excel/CSV.")
            if not df_empresas.empty:
                columnas_export = ["ISIN", "NombreING", "NombreHacienda", "Pais", "Sector", "Subsector"]
                csv_export = df_empresas[columnas_export].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="⬇️ Descargar CSV", data=csv_export, file_name="BaseDatos_Empresas.csv", mime="text/csv")
            else:
                st.warning("No hay datos para exportar.")
                
        with col_imp:
            st.subheader("📥 Carga Masiva (Anti-Duplicados)")
            st.write("Sube un CSV. **Obligatorio:** Las columnas deben ser exactamente: `ISIN`, `NombreING`, `NombreHacienda`, `Pais`, `Sector`, `Subsector`.")
            archivo_csv = st.file_uploader("Sube tu archivo CSV", type=["csv"])
            
            if archivo_csv:
                try:
                    df_import = pd.read_csv(archivo_csv, sep=None, engine='python', encoding='utf-8-sig')
                    df_import = df_import.fillna("") 
                    
                    st.write(f"📊 Detectadas {len(df_import)} filas. Aquí tienes todas:")
                    st.dataframe(df_import)
                    
                    if st.button("🚀 Confirmar e Importar / Actualizar"):
                        if not df_empresas.empty:
                            empresas_existentes = dict(zip(df_empresas['NombreING'], df_empresas['id']))
                        else:
                            empresas_existentes = {}

                        registros_preparados = []
                        nuevos = 0
                        actualizados = 0

                        for idx, row in df_import.iterrows():
                            nombre = row.get('NombreING', '')
                            registro = row.to_dict()
                            registro.pop('id', None)

                            if nombre in empresas_existentes:
                                registro['id'] = int(empresas_existentes[nombre])
                                actualizados += 1
                            else:
                                nuevos += 1
                                
                            registros_preparados.append(registro)

                        supabase.table("Empresas_Table").upsert(registros_preparados).execute()
                        
                        st.success(f"✅ ¡Proceso completado! Se han añadido {nuevos} nuevas empresas y actualizado {actualizados} existentes.")
                        import time
                        time.sleep(4) 
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al leer o importar. Detalles: {e}")

    # --- PESTAÑA 5: ZONA DE PELIGRO ---
    with tab5:
        st.subheader("⚠️ Zona de Peligro")
        st.write("Opciones destructivas para el mantenimiento de tu base de datos.")
        
        with st.expander("Desplegar opciones para borrar la base de datos"):
            st.warning("🚨 ¡ATENCIÓN! Si pulsas este botón, se borrarán absolutamente todos los registros de tu base de datos en la nube. Te recomendamos hacer una 'Copia de Seguridad' en la pestaña anterior antes de continuar.")
            
            if st.button("🗑️ SÍ, BORRAR TODA LA BASE DE DATOS", type="primary"):
                try:
                    # Borramos todos los registros con ID mayor a 0
                    supabase.table("Empresas_Table").delete().gt("id", 0).execute()
                    
                    st.success("✅ ¡Base de datos vaciada por completo!")
                    import time
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al intentar borrar: {e}")




# ==========================================
# 🚀 APLICACIÓN 8: ASISTENTE DE RENTA WEB
# ==========================================
elif opcion == "💸 Asistente de Renta Web":
    st.title("💸 Asistente Fiscal: Casillas de la Renta")
    st.write("Sube tus PDFs de dividendos del año fiscal para calcular los importes exactos de las casillas.")
    
    archivos_renta = st.file_uploader("Sube todos tus PDFs de dividendos del año aquí", type=["pdf"], accept_multiple_files=True, key="renta")

    if archivos_renta:
        resumen_fiscal = []
        with st.spinner("Calculando impuestos..."):
            for archivo in archivos_renta:
                try:
                    with pdfplumber.open(archivo) as pdf:
                        texto = pdf.pages[0].extract_text()
                        if texto:
                            # Reutilizamos nuestra lógica de extracción ultra-flexible
                            def extraer_val(etiqueta, txt):
                                patron = etiqueta + r".*?([\d\.,]+\s*[A-Z€$]{1,3})"
                                res = re.search(patron, txt, re.IGNORECASE | re.DOTALL)
                                return euro_a_numero(res.group(1)) if res else 0.0

                            bruto = extraer_val("bruto", texto)
                            ret_origen = extraer_val("origen", texto)
                            ret_destino = extraer_val("destino", texto)
                            if ret_destino == 0:
                                ret_destino = extraer_val("Retención:", texto)

                            # Identificamos si es nacional o internacional por la retención en origen
                            es_extranjero = ret_origen > 0
                            
                            resumen_fiscal.append({
                                "Bruto": bruto,
                                "Ret_Origen": ret_origen,
                                "Ret_Destino": ret_destino,
                                "Es_Extranjero": es_extranjero
                            })
                except:
                    continue

        if resumen_fiscal:
            df_fiscal = pd.DataFrame(resumen_fiscal)
            
            # --- CÁLCULOS PARA LAS CASILLAS ---
            # Casilla 029: Suma de todos los brutos (Nacionales + Extranjeros)
            total_bruto = df_fiscal["Bruto"].sum()
            
            # Casilla 029 (Retenciones): Solo las retenciones practicadas en España (Ret. Destino)
            total_ret_espana = df_fiscal["Ret_Destino"].sum()
            
            # Casilla 588 (Doble Imposición): 
            # Aquí la norma dice: Te deduces lo pagado fuera, pero con el límite del 15% del bruto.
            # Lo calculamos línea a línea para ser exactos.
            df_ext = df_fiscal[df_fiscal["Es_Extranjero"] == True].copy()
            df_ext["Max_Deduccion"] = df_ext["Bruto"] * 0.15
            df_ext["Deduccion_Real"] = df_ext[["Ret_Origen", "Max_Deduccion"]].min(axis=1)
            
            total_deduccion_588 = df_ext["Deduccion_Real"].sum()
            total_bruto_extranjero = df_ext["Bruto"].sum()

            # --- INTERFAZ VISUAL ---
            st.success("¡Análisis fiscal completado!")
            
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                st.subheader("📝 Casilla 029")
                st.info("Rendimientos del capital mobiliario")
                st.metric("Ingresos íntegros (Bruto total)", f"{formato_numero_tabla(total_bruto)} €")
                st.metric("Retenciones (Pagado en España)", f"{formato_numero_tabla(total_ret_espana)} €")

            with col_f2:
                st.subheader("🌍 Casilla 588")
                st.info("Deducción por doble imposición internacional")
                st.metric("Importe para deducir", f"{formato_numero_tabla(total_deduccion_588)} €")
                st.caption(f"Calculado sobre un bruto extranjero de {formato_numero_tabla(total_bruto_extranjero)} €")

            st.markdown("---")
            
            with st.expander("💡 ¿Cómo rellenar esto en Renta Web?"):
                st.markdown(f"""
                1. **En la Casilla 029:** Suma el importe de **{formato_numero_tabla(total_bruto)} €** en la columna de ingresos.
                2. **En la misma Casilla 029:** En el apartado de retenciones, asegúrate de que figuren los **{formato_numero_tabla(total_ret_espana)} €**.
                3. **En la Casilla 588:** Busca el apartado de 'Doble Imposición Internacional'. En 'Rentas incluidas en la base del ahorro' pon el bruto extranjero ({formatear_moneda(total_bruto_extranjero)}) y en 'Impuesto pagado en el extranjero' pon **{formato_numero_tabla(total_deduccion_588)} €**.
                """)




# ==========================================
# 🚀 APLICACIÓN 9: AUDITORÍA PRO (DB)
# ==========================================
elif opcion == "⚖️ Auditoría Pro (DB)":
    st.title("⚖️ Auditoría Fiscal Profesional (Base de Datos)")
    st.write("Cruza los datos oficiales de Hacienda con tus registros de ING y guarda el resultado.")

    # Conexión Segura a Supabase
    try:
        from supabase import create_client, Client
        url: str = st.secrets["SUPABASE_URL"]
        key: str = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Error de conexión a la base de datos: {e}")
        st.stop()


    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1️⃣ Datos de ING")
        file_ing = st.file_uploader("Sube el CSV de ING (App 1 o 4)", type=["csv"], key="ing_pro")
    with col2:
        st.subheader("2️⃣ Datos de Hacienda")
        file_aeat = st.file_uploader("Sube el Excel/CSV de la AEAT", type=["csv", "xlsx"], key="aeat_pro")

    if file_ing and file_aeat:
        try:
            # Procesar ING
            df_ing = pd.read_csv(file_ing, sep=";")
            df_ing = df_ing[df_ing["Fecha"] != "TOTALES"] # Limpiar fila totales
            
            # Procesar AEAT
            if file_aeat.name.endswith('.csv'):
                df_aeat = pd.read_csv(file_aeat, sep=None, engine='python')
            else:
                df_aeat = pd.read_excel(file_aeat)

            # Estandarizar importes para el cruce
            df_ing['Bruto_Num'] = df_ing['Importe Bruto'].apply(euro_a_numero).round(2)
            
            # Identificar columnas AEAT (Hacienda suele cambiar nombres)
            col_bruto_aeat = next((c for c in df_aeat.columns if "Íntegro" in c or "bruto" in c.lower()), df_aeat.columns[0])
            df_aeat['Bruto_Num'] = df_aeat[col_bruto_aeat].apply(euro_a_numero).round(2)

            # --- CRUCE MÁGICO ---
            df_cruce = pd.merge(
                df_ing[['Fecha', 'NombreING', 'Bruto_Num', 'Ret. Destino']], 
                df_aeat[[col_bruto_aeat, 'Bruto_Num']], 
                on='Bruto_Num', 
                how='outer', 
                suffixes=('_ING', '_AEAT')
            )

            st.subheader("📋 Previsualización del Cruce")
            
            # Lógica de Estados
            def definir_estado(row):
                if pd.isna(row['NombreING']): return "Falta en ING"
                if pd.isna(row[col_bruto_aeat]): return "Falta en AEAT"
                return "OK"

            df_cruce['Estado'] = df_cruce.apply(definir_estado, axis=1)
            st.dataframe(df_cruce)

            if st.button("💾 Guardar Auditoría en Base de Datos"):
                registros = []
                for _, r in df_cruce.iterrows():
                    registros.append({
                        "empresa": str(r['NombreING']) if pd.notna(r['NombreING']) else "Desconocido",
                        "bruto_ing": float(r['Bruto_Num']) if pd.notna(r['Bruto_Num']) else 0,
                        "bruto_aeat": float(r['Bruto_Num']) if pd.notna(r[col_bruto_aeat]) else 0,
                        "estado": r['Estado'],
                        "ejercicio_fiscal": 2024 # Se puede hacer dinámico
                    })
                
                supabase.table("Auditoria_Fiscal").insert(registros).execute()
                st.success("✅ ¡Auditoría guardada! Ahora tus discrepancias están registradas.")

        except Exception as e:
            st.error(f"Error en el cruce: {e}")

    # --- HISTÓRICO ---
    st.markdown("---")
    st.subheader("📜 Historial de Discrepancias Guardadas")
    res = supabase.table("Auditoria_Fiscal").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data))


