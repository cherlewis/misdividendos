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
        "📄 Extractor Informe Fiscal ING (Div. y DRIPs)",
        "🏛️ Extractor Informe Fiscal (AEAT)",
        "⚖️ Auditoría Hacienda vs ING",
        "📉 Calculadora Plusvalías (Hacienda)",
        "🏢 Gestor de Empresas (DB)",
        "⚖️ Auditoría Pro (DB)", # <--- La nueva joya
        "🕵️‍♂️ Auditoría Interna (ING)",  # <--- ¡AQUÍ ESTÁ LA NUEVA!
        "✍️ Gestor Manual de Movimientos"  # <--- Añade esta línea

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
            respuesta = supabase.table("Empresas").select("Sector, Subsector, Pais, NombreING").execute()
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
# 🚀 APLICACIÓN 1: DIVIDENDOS
# ==========================================
elif opcion == "📊 Dividendos a Excel":
    st.title("📄 Extractor de Dividendos a Excel")
    st.write("Sube tus PDFs de dividendos de ING. Optimizado para detectar importes 'totales' y fechas de abono.")
    
    archivos_pdf = st.file_uploader("Sube tus PDFs de Dividendos aquí", type=["pdf"], accept_multiple_files=True, key="divs")

    if archivos_pdf:
        # Generamos una firma con los nombres para saber si has subido PDFs nuevos
        nombres_archivos = "".join([a.name for a in archivos_pdf])
        
        # ⚡ MEMORIA CACHÉ: Solo procesa si son archivos nuevos
        if "divs_df" not in st.session_state or st.session_state.get("divs_archivos") != nombres_archivos:
            datos_dividendos = []
            archivos_fallidos = [] # 🕵️‍♂️ LISTA NEGRA DE ERRORES
            total_archivos = len(archivos_pdf)
            barra_progreso = st.progress(0)
            texto_estado = st.empty()

            import pdfplumber # Lo importamos fuera del bucle para ahorrar recursos
            
            for i, archivo in enumerate(archivos_pdf):
                texto_estado.text(f"⏳ Procesando ({i+1}/{total_archivos}): {archivo.name}...")
                try:
                    with pdfplumber.open(archivo) as pdf:
                        texto = pdf.pages[0].extract_text()
                        
                        if not texto:
                            raise ValueError("El PDF está vacío o protegido.")
                            
                        # 1. EMPRESA
                        match_empresa = re.search(r"(?<!Fecha\s)Valor\s*[:\-]?\s*([A-Za-z0-9\.\-\&\' ]+)", texto, re.IGNORECASE)
                        empresa = match_empresa.group(1).strip() if match_empresa else "Empresa"
                        
                        if empresa == "Empresa" or "Cuenta de abono" in empresa:
                            match_fallback = re.search(r"([A-Z][A-Z\s\.]+(?:INC|CORP|SA|PLC|AG|NV).*)", texto)
                            if match_fallback: empresa = match_fallback.group(1).strip()

                        if empresa != "Empresa":
                            empresa = empresa.split("   ")[0].split("(")[0].strip()

                        # 2. FECHAS
                        fechas_todas = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
                        match_fecha_clara = re.search(r"(?<!valor\s)Fecha\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
                        fecha_abono = match_fecha_clara.group(1) if match_fecha_clara else (fechas_todas[-1] if fechas_todas else "00/00/0000")
                        
                        # 3. IMPORTES
                        def extraer_dinero(etiqueta, txt):
                            patron = etiqueta + r".*?([\d\.,]+\s*[A-Z€$]{1,3})"
                            res = re.search(patron, txt, re.IGNORECASE | re.DOTALL)
                            return res.group(1).strip() if res else "0,00 EUR"

                        importe_bruto = extraer_dinero("bruto", texto)
                        retencion_origen = extraer_dinero("origen", texto)
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
                    # 🚨 SI FALLA, LO APUNTA EN LA LISTA NEGRA Y SIGUE CON EL SIGUIENTE
                    archivos_fallidos.append(archivo.name)
            
                # 🧹 VACIADO AGRESIVO DE MEMORIA RAM POR CADA PDF
                import gc
                gc.collect()
                barra_progreso.progress((i + 1) / total_archivos)

            texto_estado.empty()

            if datos_dividendos:
                df = pd.DataFrame(datos_dividendos)

                # --- CRUCE CON BASE DE DATOS ---
                with st.spinner("🧠 Cruzando con tu Base de Datos..."):
                    try:
                        from supabase import create_client, Client
                        url = st.secrets["SUPABASE_URL"]
                        key = st.secrets["SUPABASE_KEY"]
                        supabase = create_client(url, key)
                        respuesta = supabase.table("Empresas").select("ISIN, NombreING, Pais, Sector, Subsector, NombreHacienda").execute()
                        df_db = pd.DataFrame(respuesta.data)
                        db_nombre = {str(row["NombreING"]).upper().strip(): row.to_dict() for _, row in df_db.iterrows()} if not df_db.empty else {}

                        sectores, subsectores, paises, nombres_ing, nombres_hac, isins = [], [], [], [], [], []
                        
                        for _, row in df.iterrows():
                            emp_pdf = str(row["Empresa_PDF"]).upper().strip()
                            
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

                # 📦 GUARDAR EN LA MEMORIA CACHÉ
                st.session_state["divs_df"] = df
                st.session_state["divs_archivos"] = nombres_archivos
                st.session_state["divs_fallidos"] = archivos_fallidos
                st.success(f"¡Se procesaron {len(df)} archivo(s) con éxito!")

        # ---------------------------------------------------------------------
        # 🔔 AVISO DE ARCHIVOS FALLIDOS (Se lee de la caché)
        # ---------------------------------------------------------------------
        if st.session_state.get("divs_fallidos"):
            lista_fallos = "\n".join([f"- {f}" for f in st.session_state["divs_fallidos"]])
            st.warning(f"⚠️ **Atención:** Hubo {len(st.session_state['divs_fallidos'])} archivo(s) que no se pudieron leer. Puede que estén corruptos o no sean de dividendos:\n\n{lista_fallos}")

        # ---------------------------------------------------------------------
        # RENDERIZAR TABLA Y DESCARGA
        # ---------------------------------------------------------------------
        if "divs_df" in st.session_state:
            df_mostrar = st.session_state["divs_df"].copy()
            
            df_mostrar['Fecha_Temporal'] = pd.to_datetime(df_mostrar['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_mostrar = df_mostrar.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])

            fila_totales = {col: "" for col in df_mostrar.columns}
            fila_totales["Fecha"] = "TOTALES"
            for col in ["Importe Bruto", "Ret. Origen", "Ret. Destino", "Importe Neto"]:
                suma = df_mostrar[col].apply(lambda x: euro_a_numero(str(x)) if pd.notnull(x) and x != "" and str(x) != "0,00 EUR" else 0).sum()
                fila_totales[col] = f"{formato_numero_tabla(suma)} EUR"
            
            df_mostrar = pd.concat([df_mostrar, pd.DataFrame([fila_totales])], ignore_index=True)
            
            st.dataframe(df_mostrar)
            
            # --- 🔘 BOTONES LADO A LADO ---
            col1, col2 = st.columns(2)
            
            with col1:
                csv = df_mostrar.to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="⬇️ Descargar Excel Enriquecido", data=csv, file_name='dividendos_enriquecidos.csv', mime='text/csv', use_container_width=True)
                
            with col2:
                if st.button("☁️ Añadir datos a base de datos", type="primary", use_container_width=True):
                    with st.spinner("Subiendo datos a MovimientosDividendos..."):
                        try:
                            from supabase import create_client, Client
                            supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                            
                            registros_a_subir = []
                            # Iteramos sobre el DF original de la caché (sin la fila de TOTALES)
                            for _, row in st.session_state["divs_df"].iterrows(): 
                                try:
                                    dia, mes, anio = str(row["Fecha"]).split("/")
                                    fecha_sql = f"{anio}-{mes}-{dia}"
                                    ejercicio_fiscal = int(anio)
                                except:
                                    fecha_sql = None
                                    ejercicio_fiscal = None
                                
                                bruto_ing = euro_a_numero(str(row["Importe Bruto"]))
                                ret_origen = euro_a_numero(str(row["Ret. Origen"]))
                                ret_destino = euro_a_numero(str(row["Ret. Destino"]))
                                
                                registros_a_subir.append({
                                    "fecha": fecha_sql,
                                    "empresa": str(row["NombreING"]),
                                    "isin": str(row["ISIN"]).strip(), # 🎯 AÑADIMOS EL DNI
                                    "bruto_ing": bruto_ing,
                                    "ret_origen_ing": ret_origen,
                                    "ret_destino_ing": ret_destino,
                                    "ejercicio_fiscal": ejercicio_fiscal
                                })

                            
                            if registros_a_subir:
                                supabase.table("MovimientosDividendos").insert(registros_a_subir).execute()
                                st.success(f"✅ ¡{len(registros_a_subir)} movimientos añadidos correctamente a MovimientosDividendos!")
                        except Exception as e:
                            st.error(f"❌ Error al subir a la Base de Datos: {e}")










# ==========================================
# 🚀 APLICACIÓN 2: COMPRAS Y VENTAS
# ==========================================
elif opcion == "🛒 Compras/Ventas a Excel":
    st.title("🛒 Extractor de Compras y Ventas")
    st.write("Sube tus justificantes de operaciones de bolsa (ING) para obtener el desglose de comisiones.")
    
    # Usamos una clave de reseteo para la caché si se cambian los archivos
    archivos_pdf_op = st.file_uploader("Sube tus PDFs de Operaciones aquí", type=["pdf"], accept_multiple_files=True, key="ops")

    if archivos_pdf_op:
        nombres_archivos = "".join([a.name for a in archivos_pdf_op])
        
        # 1. LECTURA Y PROCESAMIENTO (Solo se hace una vez)
        if "ops_df" not in st.session_state or st.session_state.get("ops_archivos") != nombres_archivos:
            datos_operaciones = []
            archivos_fallidos = [] # 🕵️‍♂️ LISTA DE CHIVATOS
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
                                # 🚨 Si no cumple el patrón, lo anotamos y pasamos al siguiente
                                archivos_fallidos.append(archivo.name)
                                continue
                                
                            fecha_ejecucion = match_fecha.group(2).strip()[:10] if match_fecha else "No encontrada"
                            tipo_orden = match_fecha.group(4).strip() if match_fecha else "Desconocido"
                            cambio_divisa = (match_fecha.group(7).strip() if match_fecha.group(7) else "1,000 EUR") if match_fecha else "Revisar"

                            # 🕵️‍♂️ IDENTIFICADOR DE DERECHOS
                            es_derecho = True if (".D " in empresa.upper() or ".D." in empresa.upper() or "DERECHO" in empresa.upper()) else False

                            datos_operaciones.append({
                                "Fecha": fecha_ejecucion, "Operación": tipo_op, "Tipo Orden": tipo_orden, 
                                "Empresa_PDF": empresa, "ISIN": isin, "Títulos": titulos, "Precio": precio,
                                "Importe Op.": importe_op, "Comisión ING": comision_ing, "Gastos Bolsa": gastos_bolsa,
                                "Impuestos": impuestos, "Comisión Cambio": comision_cambio, "Importe Total": importe_total,
                                "Mercado": mercado, "Divisa / Cambio": cambio_divisa, "Archivo": archivo.name,
                                "Es_Derecho": es_derecho,
                                "Titulos_Originales_PDF": titulos 
                            })
                        else:
                            archivos_fallidos.append(archivo.name)
                except Exception as e:
                    # 🚨 Si hay un error real de lectura del PDF, también lo anotamos
                    archivos_fallidos.append(archivo.name)
                
                gc.collect()
                barra_progreso.progress((i + 1) / total_archivos)

            texto_estado.empty()

            if datos_operaciones:
                df_op = pd.DataFrame(datos_operaciones)
                
                # CRUCE BÁSICO CON BASE DE DATOS
                with st.spinner("🧠 Cruzando datos..."):
                    try:
                        from supabase import create_client, Client
                        url = st.secrets["SUPABASE_URL"]
                        key = st.secrets["SUPABASE_KEY"]
                        supabase = create_client(url, key)
                        respuesta = supabase.table("Empresas").select("ISIN, NombreING, Pais, Sector, Subsector, NombreHacienda").execute()
                        df_db = pd.DataFrame(respuesta.data)
                        
                        if not df_db.empty:
                            df_db_limpio = df_db.dropna(subset=['ISIN']).drop_duplicates(subset=['ISIN'])
                            db_isin = df_db_limpio.set_index("ISIN").to_dict("index")
                            db_nombre = {str(row["NombreING"]).upper(): row.to_dict() for _, row in df_db.iterrows()}
                        else:
                            db_isin, db_nombre = {}, {}

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
                            
                            match = db_isin.get(isin_op) or db_nombre.get(nombre_norm)
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

                    except Exception as e:
                        st.error(f"⚠️ Error técnico real del cruce: {e}")
                
                st.session_state["ops_df"] = df_op
                st.session_state["ops_archivos"] = nombres_archivos
                st.session_state["ops_fallidos"] = archivos_fallidos # Guardamos los chivatos
                st.success(f"¡Se procesaron {len(df_op)} archivo(s) con éxito!")

        # ---------------------------------------------------------------------
        # 🔔 AVISO DE ARCHIVOS FALLIDOS (Si los hay)
        # ---------------------------------------------------------------------
        if st.session_state.get("ops_fallidos"):
            lista_fallos = "\n".join([f"- {f}" for f in st.session_state["ops_fallidos"]])
            st.warning(f"⚠️ **Archivos omitidos ({len(st.session_state['ops_fallidos'])}):** No se han podido procesar porque no tienen el formato exacto de Compra/Venta de ING:\n\n{lista_fallos}")

        # ---------------------------------------------------------------------
        # 2. INTERFAZ PARA INTRODUCIR ACCIONES EQUIVALENTES
        # ---------------------------------------------------------------------
        if "ops_df" in st.session_state:
            df_mostrar = st.session_state["ops_df"].copy()
            
            hay_derechos = df_mostrar["Es_Derecho"].any()

            if hay_derechos:
                st.markdown("---")
                st.warning("🧩 **¡Hemos detectado compra de Derechos!**")
                
                st.info("💡 **PISTA:** Ve a los movimientos del broker y busca el concepto **SUSCRIPCIÓN - EMPRESA AÑO - 0,00€ - X Tit**. La **X** será el número de acciones que debes introducir a continuación.")
                
                st.write("Indica el **número final de acciones completas** que obtuviste gracias a cada compra de derechos. El sistema calculará el precio unitario automáticamente.")
                
                derechos_indices = df_mostrar[df_mostrar["Es_Derecho"]].index
                
                with st.form("form_derechos"):
                    nuevos_titulos_dict = {}
                    
                    for idx in derechos_indices:
                        row = df_mostrar.loc[idx]
                        empresa_nombre = row["NombreING"]
                        derechos_comprados = row["Titulos_Originales_PDF"]
                        dinero_gastado = row["Importe Total"]
                        fecha_compra = row["Fecha"] 
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.info(f"**{empresa_nombre}** | El **{fecha_compra}** gastaste **{dinero_gastado}** comprando **{derechos_comprados}** derechos.")
                        with col2:
                            nuevos_titulos_dict[idx] = st.number_input(
                                f"Acciones obtenidas", 
                                min_value=1, 
                                value=1, 
                                step=1, 
                                key=f"acc_{idx}"
                            )
                    
                    boton_aplicar = st.form_submit_button("✅ Aplicar conversiones a Acciones")
                    
                    if boton_aplicar:
                        for idx, nuevas_acciones in nuevos_titulos_dict.items():
                            dinero_total = euro_a_numero(str(df_mostrar.loc[idx, 'Importe Total']))
                            
                            nuevo_precio = dinero_total / nuevas_acciones if nuevas_acciones > 0 else 0
                            
                            st.session_state["ops_df"].at[idx, 'Títulos'] = str(nuevas_acciones)
                            st.session_state["ops_df"].at[idx, 'Precio'] = f"{nuevo_precio:.4f} EUR".replace('.', ',')
                            st.session_state["ops_df"].at[idx, 'Operación'] = "Compra (Suscripción Acciones)"
                            st.session_state["ops_df"].at[idx, 'Es_Derecho'] = False 
                        
                        st.success("¡Conversiones aplicadas con éxito! Recalculando tabla...")
                        st.rerun() 


            
            # ---------------------------------------------------------------------
            # 3. GENERACIÓN DE TOTALES, EXCEL Y SUBIDA A SUPABASE
            # ---------------------------------------------------------------------
            if not df_mostrar["Es_Derecho"].any():
                columnas_finales = [
                    "Fecha", "Operación", "NombreING", "ISIN", "Pais", "Sector", "Subsector", 
                    "Títulos", "Precio", "Importe Op.", "Comisión ING", "Gastos Bolsa", 
                    "Impuestos", "Comisión Cambio", "Importe Total", "Mercado", "Divisa / Cambio", 
                    "NombreHacienda", "Archivo"
                ]
                df_export = df_mostrar[columnas_finales].copy()
                
                # Ordenamos cronológicamente
                df_export['Fecha_Temporal'] = pd.to_datetime(df_export['Fecha'], format='%d/%m/%Y', errors='coerce')
                df_export = df_export.sort_values(by='Fecha_Temporal', ascending=True).drop(columns=['Fecha_Temporal'])
                
                # Fila de totales visual (solo para el Excel y la pantalla, NO para la BBDD)
                fila_totales = {col: "" for col in df_export.columns}
                fila_totales["Fecha"] = "TOTALES"
                cols_a_sumar_op = ["Importe Op.", "Comisión ING", "Gastos Bolsa", "Impuestos", "Comisión Cambio", "Importe Total"]
                for col in cols_a_sumar_op:
                    suma = df_export[col].apply(lambda x: euro_a_numero(str(x)) if pd.notnull(x) and x != "" else 0).sum()
                    fila_totales[col] = f"{formato_numero_tabla(suma)} EUR"
                
                df_export_visual = pd.concat([df_export, pd.DataFrame([fila_totales])], ignore_index=True)
                
                st.dataframe(df_export_visual)
                
                st.markdown("---")
                
                # ---------------------------------------------------------------------
                # 🎛️ BOTONES DE ACCIÓN (EXCEL Y SUPABASE)
                # ---------------------------------------------------------------------
                col_excel, col_db = st.columns(2)
                
                with col_excel:
                    csv_op = df_export_visual.to_csv(index=False, sep=";").encode('utf-8-sig')
                    st.download_button(label="⬇️ Descargar Excel Enriquecido", data=csv_op, file_name='operaciones_bolsa_enriquecido.csv', mime='text/csv', use_container_width=True)


                with col_db:
                    if st.button("☁️ Guardar en MovimientosCompraVenta (DB)", type="primary", use_container_width=True):
                        with st.spinner("Comprobando duplicados y guardando en Supabase..."):
                            try:
                                from supabase import create_client, Client
                                url = st.secrets["SUPABASE_URL"]
                                key = st.secrets["SUPABASE_KEY"]
                                supabase = create_client(url, key)

                                # 1. Traer datos existentes para evitar duplicados
                                res_db = supabase.table("MovimientosCompraVenta").select("FechaEjecucion, ISIN, TipoOperacion, ImporteTotal").execute()
                                
                                db_existentes = set()
                                if res_db.data:
                                    for row_db in res_db.data:
                                        # Firma: YYYY-MM-DD_ISIN_OPERACION_IMPORTE
                                        imp_db = round(float(row_db.get("ImporteTotal", 0)), 2)
                                        firma = f"{row_db.get('FechaEjecucion')}_{row_db.get('ISIN')}_{row_db.get('TipoOperacion')}_{imp_db}"
                                        db_existentes.add(firma)

                                # 2. Preparar los registros nuevos
                                registros_a_subir = []
                                
                                for idx, row in df_export.iterrows():
                                    if row["Fecha"] == "TOTALES": continue
                                    
                                    try:
                                        fecha_sql = datetime.strptime(row["Fecha"], "%d/%m/%Y").strftime("%Y-%m-%d")
                                    except:
                                        fecha_sql = None
                                        
                                    isin = str(row["ISIN"]).strip()
                                    tipo_op = str(row["Operación"]).strip()
                                    imp_total = round(euro_a_numero(str(row["Importe Total"])), 2)

                                    firma_actual = f"{fecha_sql}_{isin}_{tipo_op}_{imp_total}"

                                    if firma_actual not in db_existentes and fecha_sql:
                                        # 🔒 CORTAFUEGOS DE DECIMALES (Obligamos a redondear a 2 y 4)
                                        titulos = round(euro_a_numero(str(row["Títulos"])), 4)
                                        precio = round(euro_a_numero(str(row["Precio"])), 4)
                                        imp_op = round(euro_a_numero(str(row["Importe Op."])), 2)
                                        
                                        comision_ing = round(euro_a_numero(str(row["Comisión ING"])), 2)
                                        gastos_bolsa = round(euro_a_numero(str(row["Gastos Bolsa"])), 2)
                                        impuestos = round(euro_a_numero(str(row["Impuestos"])), 2)
                                        com_cambio = round(euro_a_numero(str(row["Comisión Cambio"])), 2)
                                        
                                        # Sumas redondeadas para evitar el "fantasma" de los decimales
                                        gastos_totales = round(gastos_bolsa + impuestos, 2)
                                        total_comision = round(comision_ing + gastos_totales + com_cambio, 2)

                                        registros_a_subir.append({
                                            "ISIN": isin,
                                            "Titulos": titulos,
                                            "TipoOperacion": tipo_op,
                                            "Precio": precio,
                                            "ImporteOperacion": imp_op,
                                            "Comision": comision_ing,
                                            "Gastos": gastos_totales,
                                            "TotalComision": total_comision,
                                            "ImporteTotal": imp_total,
                                            "FechaEjecucion": fecha_sql,
                                            "ComisionCambioDivisa": com_cambio
                                        })

                                # 3. Inserción masiva
                                if registros_a_subir:
                                    supabase.table("MovimientosCompraVenta").insert(registros_a_subir).execute()
                                    st.success(f"✅ ¡Se han guardado {len(registros_a_subir)} movimientos NUEVOS en la base de datos!")
                                    st.balloons() 
                                else:
                                    st.info("ℹ️ No se han guardado datos. Todos los PDFs procesados ya estaban registrados en Supabase (Duplicados detectados y omitidos).")

                            except Exception as e:
                                st.error(f"❌ Error al conectar o guardar en la base de datos: {e}")










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
# 🚀 APLICACIÓN 4: EXTRACTOR INFORME FISCAL ING
# ==========================================
elif opcion == "📄 Extractor Informe Fiscal ING (Div. y DRIPs)":
    st.title("📄 Extractor Total del Informe Fiscal ING")
    st.write("Sube el PDF de Información Fiscal de ING. Extraeremos DRIPs, Dividendos y los enviaremos a tu base de datos.")

    from datetime import datetime
    import pandas as pd
    import re
    
    anio_fiscal_defecto = datetime.now().year - 1

    ejercicio_fiscal_ing = st.number_input(
        "📅 Año Fiscal del documento (ING):", 
        min_value=2020, 
        max_value=2050, 
        value=anio_fiscal_defecto, 
        key="año_ing"
    )
    
    archivos_pdf_inf = st.file_uploader("Sube tu PDF de Datos Fiscales de ING aquí", type=["pdf"], accept_multiple_files=True, key="inf_ing")

    def obtener_bandera(isin, empresa):
        if isinstance(isin, str) and len(isin) >= 2 and isin != "ISIN no encontrado":
            prefijo = isin[:2].upper()
            banderas = {"ES": "España", "US": "USA", "DE": "Alemania", "FR": "Francia", "NL": "Países Bajos", "GB": "Reino Unido"}
            if prefijo in banderas: return banderas[prefijo]
        if " INC" in str(empresa).upper() or " CORP" in str(empresa).upper(): return "USA"
        if " NV" in str(empresa).upper(): return "Países Bajos"
        if " PLC" in str(empresa).upper(): return "Reino Unido"
        if "L'OREAL" in str(empresa).upper() or "LOREAL" in str(empresa).upper(): return "Francia"
        if "LVMH" in str(empresa).upper() or "LOUIS VUITTON" in str(empresa).upper(): return "Francia"
        if "DANONE" in str(empresa).upper() or "SANOFI" in str(empresa).upper(): return "Francia"
        return "Desconocido"

    if archivos_pdf_inf:
        datos_informe = []
        with st.spinner("Analizando Informe Fiscal de ING y cruzando con tu base de datos..."):
            
            map_empresa_isin = {}
            try:
                from supabase import create_client, Client
                supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                res_empresas = supabase.table("Empresas").select("ISIN, NombreING").execute()
                
                if res_empresas.data:
                    for e in res_empresas.data:
                        if e.get("NombreING") and e.get("ISIN"):
                            map_empresa_isin[str(e["NombreING"]).strip().upper()] = str(e["ISIN"]).strip()
            except Exception as e:
                st.warning(f"⚠️ No se pudo cargar la tabla de Empresas: {e}")

            # 🧠 DICCIONARIO MAESTRO CORREGIDO
            map_alias = {
                "REDEIA": "ES0173093024", "RED ELECTRICA": "ES0173093024",
                "NATURGY": "ES0116870314", "GAS NATURAL": "ES0116870314",
                "MAPFRE": "ES0124244E34", "LOGISTA": "ES0105027009",
                "VIDRALA": "ES0183746314", "VID": "ES0183746314",
                "VISCOFAN": "ES0184262212", "VIS": "ES0184262212",
                "EBRO": "ES0112501012", "LINEA": "ES0105546008",
                "MIQUEL": "ES0164180012", "GR.C.OCCIDEN": "ES0116920333", # 🎯 Catalana Occidente arreglado
                "IBERPAPEL": "ES0147561015", "ENAGAS": "ES0130960018",
                "ENDESA": "ES0130670112", "BA.SABADELL": "ES0113860A34",
                "TELEFONICA": "ES0178430E18", "ACS": "ES0167050915",
                "IBERDROLA": "ES0144580Y14", "IBE": "ES0144580Y14",
                "BBVA": "ES0113211835"
            }

            for archivo in archivos_pdf_inf:
                try:
                    import pdfplumber
                    with pdfplumber.open(archivo) as pdf:
                        texto_completo = ""
                        for page in pdf.pages:
                            texto_pagina = page.extract_text(layout=True)
                            if not texto_pagina: texto_pagina = page.extract_text()
                            if texto_pagina: texto_completo += texto_pagina + "\n"
                        
                        if texto_completo:
                            lineas = texto_completo.split('\n')
                            patron_drip = r"(?i)(.*?)\s+(Nacional|Internacional)\s+(\d{2}/\d{2}/\d{4})\s+STOCK DIVIDEND\s+(\d+)\s+([\d.,]+)\s*€"
                            patron_div = r"(?i)(.*?)\s+(Nacional|Internacional)\s+(Dividendo|Primas de asistencia|Primas de emisi[oó]n|Primas de emision)\s+([\d,.]+)\s*€\s+([\d,.]+)\s*€(?:\s+([\d,.]+)\s*€)?"
                            
                            for idx, linea in enumerate(lineas):
                                match_drip = re.search(patron_drip, linea)
                                if match_drip:
                                    empresa_full = match_drip.group(1).strip()
                                    fecha = match_drip.group(3).strip()
                                    titulos = match_drip.group(4).strip()
                                    importe = match_drip.group(5).strip()
                                    
                                    isin_encontrado = ""
                                    for j in range(1, 4):
                                        if idx + j >= len(lineas): break
                                        match_isin = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", lineas[idx + j])
                                        if match_isin:
                                            isin_encontrado = match_isin.group(1)
                                            break
                                            
                                    if not isin_encontrado:
                                        emp_up = empresa_full.upper()
                                        emp_up_clean = re.sub(r'\.D\..*|\sD\..*|\.D.*', '', emp_up).strip()
                                        
                                        if emp_up_clean in map_alias:
                                            isin_encontrado = map_alias[emp_up_clean]
                                        elif emp_up_clean in map_empresa_isin:
                                            isin_encontrado = map_empresa_isin[emp_up_clean]
                                        else:
                                            for n_ing, isin_val in map_empresa_isin.items():
                                                if len(emp_up_clean) >= 3 and (n_ing in emp_up_clean or emp_up_clean in n_ing):
                                                    isin_encontrado = isin_val
                                                    break

                                    bruto_num = euro_a_numero(importe)
                                    pais_origen = obtener_bandera(isin_encontrado, empresa_full)

                                    datos_informe.append({
                                        "fecha_abono": fecha,
                                        "isin": isin_encontrado,
                                        "concepto": "STOCK DIVIDEND",
                                        "importe_neto": bruto_num,
                                        "retencion_origen": 0.0,
                                        "porcentaje_retencion_origen": 0.0,
                                        "retencion_destino": 0.0,
                                        "porcentaje_retencion_destino": 0.0,
                                        "importe_bruto": bruto_num,
                                        "empresa": empresa_full,
                                        "pais": pais_origen,
                                        "cuenta_valores": "",
                                        "numero_titulos": float(titulos) if titulos.isdigit() else 0.0,
                                        "cuenta_abono": "",
                                        "retencion_recuperable": 0.0
                                    })
                                    continue
                                
                                match_div = re.search(patron_div, linea)
                                if match_div:
                                    empresa_raw = match_div.group(1).strip()
                                    mercado = match_div.group(2).strip().capitalize()
                                    concepto_extraido = match_div.group(3).strip().upper()
                                    bruto = match_div.group(4).strip()
                                    
                                    if mercado == "Nacional":
                                        ret_origen = "0,00"
                                        ret_destino = match_div.group(5).strip()
                                    else:
                                        ret_origen = match_div.group(5).strip()
                                        ret_destino = match_div.group(6).strip() if match_div.group(6) else "0,00"
                                    
                                    isin_encontrado = ""
                                    match_isin = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", empresa_raw)
                                    if match_isin:
                                        isin_encontrado = match_isin.group(1)
                                        empresa_full = empresa_raw.replace(f"({isin_encontrado})", "").strip()
                                    else:
                                        empresa_full = empresa_raw
                                        for j in range(1, 3):
                                            if idx + j < len(lineas):
                                                match_isin_next = re.search(r"\(([A-Z]{2}[A-Z0-9]{10})\)", lineas[idx + j])
                                                if match_isin_next:
                                                    isin_encontrado = match_isin_next.group(1)
                                                    break

                                    if not isin_encontrado:
                                        emp_up = empresa_full.upper()
                                        emp_up_clean = re.sub(r'\.D\..*|\sD\..*|\.D.*', '', emp_up).strip()
                                        
                                        if emp_up_clean in map_alias:
                                            isin_encontrado = map_alias[emp_up_clean]
                                        elif emp_up_clean in map_empresa_isin:
                                            isin_encontrado = map_empresa_isin[emp_up_clean]
                                        else:
                                            for n_ing, isin_val in map_empresa_isin.items():
                                                if len(emp_up_clean) >= 3 and (n_ing in emp_up_clean or emp_up_clean in n_ing):
                                                    isin_encontrado = isin_val
                                                    break

                                    bruto_num = euro_a_numero(bruto)
                                    ret_ori_num = euro_a_numero(ret_origen)
                                    ret_des_num = euro_a_numero(ret_destino)
                                    neto_num = bruto_num - ret_ori_num - ret_des_num
                                    
                                    pct_ori = round((ret_ori_num / bruto_num) * 100, 2) if bruto_num > 0 else 0.0
                                    pct_des = round((ret_des_num / bruto_num) * 100, 2) if bruto_num > 0 else 0.0
                                    
                                    pais_origen = obtener_bandera(isin_encontrado, empresa_full)
                                    
                                    recuperable = 0.0
                                    if ret_ori_num > 0:
                                        pais_limpio = pais_origen.strip().upper()
                                        if pais_limpio in ["FRANCIA", "FRANCE", "ALEMANIA", "GERMANY"]:
                                            maximo_recuperable = bruto_num * 0.15
                                            recuperable = round(min(ret_ori_num, maximo_recuperable), 2)
                                        else:
                                            recuperable = ret_ori_num

                                    datos_informe.append({
                                        "fecha_abono": f"31/12/{ejercicio_fiscal_ing}",
                                        "isin": isin_encontrado,
                                        "concepto": concepto_extraido,
                                        "importe_neto": round(neto_num, 2),
                                        "retencion_origen": round(ret_ori_num, 2),
                                        "porcentaje_retencion_origen": pct_ori,
                                        "retencion_destino": round(ret_des_num, 2),
                                        "porcentaje_retencion_destino": pct_des,
                                        "importe_bruto": round(bruto_num, 2),
                                        "empresa": empresa_full,
                                        "pais": pais_origen,
                                        "cuenta_valores": "",
                                        "numero_titulos": 0.0, 
                                        "cuenta_abono": "",
                                        "retencion_recuperable": recuperable
                                    })
                except Exception as e:
                    st.warning(f"⚠️ Error procesando {archivo.name}: {e}")

        if datos_informe:
            df_ing = pd.DataFrame(datos_informe)
            st.write("📊 **Vista previa de los datos estructurados:**")
            st.dataframe(df_ing)

            st.info("💡 **Filtro Anti-Duplicados Activado:** El sistema identificará operaciones repetidas comparando el ISIN y el Importe Bruto con lo que ya existe en la nube.")

            col_excel, col_db = st.columns(2)
            
            with col_excel:
                csv_ing = df_ing.to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Descargar Excel (ING)", 
                    data=csv_ing, 
                    file_name=f"Informe_ING_{ejercicio_fiscal_ing}.csv", 
                    mime='text/csv', 
                    use_container_width=True
                )

            with col_db:
                if st.button("☁️ Subir a Base de Datos (informefiscaling)", type="primary", use_container_width=True):
                    with st.spinner("Comprobando duplicados y guardando en Supabase..."):
                        try:
                            res_db = supabase.table("informefiscaling").select("isin, importe_bruto").eq("ejercicio_fiscal", int(ejercicio_fiscal_ing)).execute()
                            
                            db_existentes = []
                            if res_db.data:
                                for row_db in res_db.data:
                                    isin_db = str(row_db.get("isin", "")).strip()
                                    imp_db = round(float(row_db.get("importe_bruto", 0)), 2)
                                    firma = f"{isin_db}_{imp_db}"
                                    db_existentes.append(firma)
                            
                            registros_a_subir = []
                            for _, row in df_ing.iterrows():
                                isin_excel = str(row["isin"]).strip()
                                imp_excel = round(float(row["importe_bruto"]), 2)
                                firma_actual = f"{isin_excel}_{imp_excel}"
                                
                                if firma_actual in db_existentes:
                                    db_existentes.remove(firma_actual)
                                else:
                                    registro = {
                                        "fecha_abono": str(row["fecha_abono"]),
                                        "isin": isin_excel[:50],
                                        "concepto": str(row["concepto"])[:100],
                                        "importe_neto": float(row["importe_neto"]),
                                        "retencion_origen": float(row["retencion_origen"]),
                                        "porcentaje_retencion_origen": float(row["porcentaje_retencion_origen"]),
                                        "retencion_destino": float(row["retencion_destino"]),
                                        "porcentaje_retencion_destino": float(row["porcentaje_retencion_destino"]),
                                        "importe_bruto": float(row["importe_bruto"]),
                                        "empresa": str(row["empresa"])[:250],
                                        "pais": str(row["pais"])[:100],
                                        "cuenta_valores": str(row["cuenta_valores"]),
                                        "numero_titulos": float(row["numero_titulos"]),
                                        "cuenta_abono": str(row["cuenta_abono"]),
                                        "retencion_recuperable": float(row["retencion_recuperable"]),
                                        "ejercicio_fiscal": int(ejercicio_fiscal_ing) 
                                    }
                                    registros_a_subir.append(registro)
                            
                            if registros_a_subir:
                                supabase.table("informefiscaling").insert(registros_a_subir).execute()
                                st.success(f"✅ ¡{len(registros_a_subir)} registros NUEVOS guardados en 'informefiscaling' para {ejercicio_fiscal_ing}!")
                                st.balloons()
                            else:
                                st.info("ℹ️ No se ha subido nada. Todos los datos de este PDF ya estaban en tu base de datos (0 duplicados).")
                                
                        except Exception as e:
                            st.error(f"❌ Error al guardar en DB: {e}")















# ==========================================
# 🚀 APLICACIÓN 5: AUDITORÍA HACIENDA VS ING
# ==========================================
elif opcion == "⚖️ Auditoría Hacienda vs ING":
    st.title("⚖️ Auditor Inteligente y Subida a DB")
    st.markdown("""**¡El fin del caos con los nombres y los ISINs!**
    Cruza automáticamente tus dividendos de ING con el borrador de Hacienda y guárdalos de forma segura en tu base de datos.""")

    # 📅 PEDIMOS EL AÑO FISCAL PARA LA BASE DE DATOS
    ejercicio_fiscal = st.number_input("📅 ¿De qué Año Fiscal es esta auditoría?", min_value=2020, max_value=2050, value=2024)

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
            if "Fecha Abono" in df_ing.columns:
                df_ing = df_ing[df_ing["Fecha Abono"] != "TOTALES"]
            
            if archivo_aeat.name.endswith('.csv'):
                df_aeat = pd.read_csv(archivo_aeat, sep=None, engine='python')
            else:
                df_aeat = pd.read_excel(archivo_aeat, engine='openpyxl')

            # Detección de columnas de AEAT
            col_bruto_aeat = "Importe Íntegro" if "Importe Íntegro" in df_aeat.columns else df_aeat.columns[7]
            col_ret_aeat = "Retenciones" if "Retenciones" in df_aeat.columns else df_aeat.columns[9]
            col_nom_aeat = "Nombre Emisor" if "Nombre Emisor" in df_aeat.columns else df_aeat.columns[2]

            st.success("¡Archivos cargados! Cruzando los datos por coincidencia de importes...")

            # ---------------------------------------------------------
            # PREPARACIÓN ING (Ahora arrastramos fecha y ret_origen)
            # ---------------------------------------------------------
            df_ing['Bruto_Num'] = df_ing['Importe Bruto (€)'].apply(euro_a_numero).round(2)
            df_ing['Ret_Dest_Num'] = df_ing['Retención en destino (€)'].apply(euro_a_numero).round(2)
            df_ing['Ret_Orig_Num'] = df_ing['Retención en origen (€)'].apply(euro_a_numero).round(2)
            
            df_ing = df_ing[df_ing['Bruto_Num'] > 0]

            ing_agrup = df_ing.groupby('Bruto_Num').agg({
                'Empresa': lambda x: ' + '.join(x.unique()),
                'Ret_Dest_Num': 'sum',
                'Ret_Orig_Num': 'sum',
                'Fecha Abono': 'first' # Capturamos la primera fecha
            }).reset_index()
            
            ing_agrup.rename(columns={'Bruto_Num': 'Importe Bruto', 'Empresa': 'Empresa(s) en ING'}, inplace=True)

            # ---------------------------------------------------------
            # PREPARACIÓN HACIENDA
            # ---------------------------------------------------------
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

            # ---------------------------------------------------------
            # EL CRUCE MÁGICO
            # ---------------------------------------------------------
            df_cruce = pd.merge(ing_agrup, aeat_agrup, on='Importe Bruto', how='outer').fillna(0)

            df_cruce['Empresa(s) en ING'] = df_cruce['Empresa(s) en ING'].replace(0, "❌ No consta en tu ING")
            df_cruce['Emisor(es) en Hacienda'] = df_cruce['Emisor(es) en Hacienda'].replace(0, "❌ Falta en tu Borrador")
            
            df_cruce['Dif. Retención'] = (df_cruce['Ret_Dest_Num'] - df_cruce['Retención AEAT']).round(2)

            def determinar_estado(row):
                if row['Empresa(s) en ING'] == "❌ No consta en tu ING": return "🔴 Añadido por Hacienda"
                if row['Emisor(es) en Hacienda'] == "❌ Falta en tu Borrador": return "🔴 Te falta declararlo"
                if abs(row['Dif. Retención']) > 0.05: return "🟡 Falla la Retención"
                return "🟢 Cuadra Perfecto"

            df_cruce['Estado'] = df_cruce.apply(determinar_estado, axis=1)

            # ---------------------------------------------------------
            # TABLA VISUAL
            # ---------------------------------------------------------
            df_cruce['Importe Bruto (€)'] = df_cruce['Importe Bruto'].apply(formato_numero_tabla)
            df_cruce['Ret. ING (€)'] = df_cruce['Ret_Dest_Num'].apply(formato_numero_tabla)
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
            
            st.markdown("---")
            
            # ---------------------------------------------------------------------
            # 🎛️ BOTONES DE ACCIÓN (EXCEL Y SUPABASE)
            # ---------------------------------------------------------------------
            col_excel, col_db = st.columns(2)
            
            with col_excel:
                csv_audit = df_final.to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="⬇️ Descargar Excel Auditoría", data=csv_audit, file_name=f'auditoria_dividendos_{ejercicio_fiscal}.csv', mime='text/csv', use_container_width=True)

            with col_db:
                if st.button("☁️ Guardar en MovimientosDividendos (DB)", type="primary", use_container_width=True):
                    with st.spinner("Comprobando duplicados y guardando en Supabase..."):
                        try:
                            from supabase import create_client, Client
                            url = st.secrets["SUPABASE_URL"]
                            key = st.secrets["SUPABASE_KEY"]
                            supabase = create_client(url, key)

                            # 1. Traer datos para evitar duplicados del mismo año fiscal
                            res_db = supabase.table("MovimientosDividendos").select("ejercicio_fiscal, bruto_ing").eq("ejercicio_fiscal", ejercicio_fiscal).execute()
                            
                            db_existentes = set()
                            if res_db.data:
                                for row_db in res_db.data:
                                    # Nuestra Huella Digital: Año + Importe Bruto
                                    imp_db = round(float(row_db.get("bruto_ing", 0)), 2)
                                    firma = f"{row_db.get('ejercicio_fiscal')}_{imp_db}"
                                    db_existentes.add(firma)

                            # 2. Preparar los registros mapeados a tu Schema
                            registros_a_subir = []
                            
                            for idx, row in df_cruce.iterrows():
                                bruto = round(float(row["Importe Bruto"]), 2)
                                firma_actual = f"{ejercicio_fiscal}_{bruto}"
                                
                                if firma_actual not in db_existentes:
                                    
                                    # Convertimos la fecha. Si pone "Resumen 2024", la dejamos vacía en SQL (None)
                                    fecha_sql = None
                                    try:
                                        fecha_str = str(row.get("Fecha Abono", ""))
                                        if "/" in fecha_str:
                                            fecha_sql = datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                                    except:
                                        pass
                                        
                                    # Mezclamos los nombres si uno de ellos falla
                                    empresa_final = row['Empresa(s) en ING']
                                    if "❌" in empresa_final:
                                        empresa_final = row['Emisor(es) en Hacienda']

                                    registros_a_subir.append({
                                        "fecha": fecha_sql,
                                        "empresa": empresa_final[:250], 
                                        "bruto_ing": bruto,
                                        "ret_origen_ing": round(float(row.get("Ret_Orig_Num", 0)), 2),
                                        "ret_destino_ing": round(float(row.get("Ret_Dest_Num", 0)), 2),
                                        "bruto_aeat": bruto, 
                                        "ret_aeat": round(float(row.get("Retención AEAT", 0)), 2),
                                        "diferencia": round(float(row.get("Dif. Retención", 0)), 2),
                                        "estado": str(row["Estado"]),
                                        "ejercicio_fiscal": int(ejercicio_fiscal)
                                    })

                            # 3. Subida a la nube
                            if registros_a_subir:
                                supabase.table("MovimientosDividendos").insert(registros_a_subir).execute()
                                st.success(f"✅ ¡Se han guardado {len(registros_a_subir)} dividendos auditados de {ejercicio_fiscal} en la base de datos!")
                                st.balloons()
                            else:
                                st.info(f"ℹ️ No se han guardado datos. Todos los dividendos de {ejercicio_fiscal} ya estaban registrados (Protección Antiduplicados).")

                        except Exception as e:
                            st.error(f"❌ Error al conectar o guardar en la base de datos: {e}")

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
        respuesta = supabase.table("Empresas").select("*").order("NombreING").execute()
        return pd.DataFrame(respuesta.data)

    df_empresas = cargar_empresas()

    # 3. Interfaz con 5 Pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Añadir", "✏️ Editar", "📋 Ver Tabla", "🔄 Importar / Exportar", "🚨 Peligro"])

    # --- PESTAÑA 1: AÑADIR ---
    with tab1:
        st.subheader("Añadir una nueva empresa")
        with st.form("form_add", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                isin_add = st.text_input("ISIN (ej. US7134481081)")
                nombre_add = st.text_input("Nombre en ING")
                nombre_hac_add = st.text_input("Nombre en Hacienda")
            with col2:
                pais_add = st.text_input("País (ej. 🇺🇸 USA)")
                sector_add = st.text_input("Sector")
                subsector_add = st.text_input("Subsector")
            with col3:
                cap_add = st.text_input("Capitalización (ej. Large CAP)")
                ticker_add = st.text_input("Ticker (Google, ej. NASDAQ:PEP)")
                ticker_y_add = st.text_input("Ticker Yahoo (ej. PEP)")
                moneda_add = st.text_input("Moneda (ej. USD, EUR)")

            submit_add = st.form_submit_button("💾 Guardar Empresa")
            if submit_add:
                if nombre_add and isin_add:
                    nueva_empresa = {
                        "ISIN": isin_add, "NombreING": nombre_add, "NombreHacienda": nombre_hac_add,
                        "Pais": pais_add, "Sector": sector_add, "Subsector": subsector_add,
                        "Capitalizacion": cap_add, "Ticker": ticker_add, 
                        "TickerYahoo": ticker_y_add, "MonedaCotizacion": moneda_add
                    }
                    supabase.table("Empresas").insert(nueva_empresa).execute()
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
                col1, col2, col3 = st.columns(3)
                with col1:
                    isin_ed = st.text_input("ISIN", value=datos_actuales.get('ISIN', ''))
                    nombre_ed = st.text_input("Nombre en ING", value=datos_actuales.get('NombreING', ''))
                    nombre_hac_ed = st.text_input("Nombre Hacienda", value=datos_actuales.get('NombreHacienda', '') or '')
                with col2:
                    pais_ed = st.text_input("País", value=datos_actuales.get('Pais', '') or '')
                    sector_ed = st.text_input("Sector", value=datos_actuales.get('Sector', '') or '')
                    subsector_ed = st.text_input("Subsector", value=datos_actuales.get('Subsector', '') or '')
                with col3:
                    cap_ed = st.text_input("Capitalización", value=datos_actuales.get('Capitalizacion', '') or '')
                    ticker_ed = st.text_input("Ticker (Google)", value=datos_actuales.get('Ticker', '') or '')
                    ticker_y_ed = st.text_input("Ticker Yahoo", value=datos_actuales.get('TickerYahoo', '') or '')
                    moneda_ed = st.text_input("Moneda", value=datos_actuales.get('MonedaCotizacion', '') or '')

                submit_edit = st.form_submit_button("🔄 Actualizar Cambios")
                if submit_edit:
                    cambios = {
                        "ISIN": isin_ed, "NombreING": nombre_ed, "NombreHacienda": nombre_hac_ed,
                        "Pais": pais_ed, "Sector": sector_ed, "Subsector": subsector_ed,
                        "Capitalizacion": cap_ed, "Ticker": ticker_ed, 
                        "TickerYahoo": ticker_y_ed, "MonedaCotizacion": moneda_ed
                    }
                    supabase.table("Empresas").update(cambios).eq("id", str(datos_actuales['id'])).execute()
                    st.success(f"✅ ¡Datos de {nombre_ed} actualizados!")
                    import time
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("No hay empresas en la base de datos todavía.")

    # --- PESTAÑA 3: VER TABLA Y PRECIOS EN VIVO ---
    with tab3:
        st.subheader("Base de Datos Actual")
        if not df_empresas.empty:
            # 💡 MEJORA: Añadimos TickerYahoo a las columnas visibles
            columnas_mostrar = ["ISIN", "NombreING", "Ticker", "TickerYahoo", "Pais", "Sector", "Capitalizacion"]
            cols_existentes = [col for col in columnas_mostrar if col in df_empresas.columns]
            st.dataframe(df_empresas[cols_existentes], use_container_width=True)
            
            st.markdown("---")
            st.write("📈 **Añadir datos del mercado en tiempo real**")
            if st.button("🔄 Cargar Cotizaciones en Vivo"):
                if "TickerYahoo" not in df_empresas.columns:
                    st.error("Necesitas asegurar que la columna 'TickerYahoo' esté cargada desde Supabase.")
                else:
                    import yfinance as yf
                    with st.spinner("Conectando con Wall Street para descargar precios..."):
                        precios_actuales = []
                        variaciones = []
                        
                        for idx, row in df_empresas.iterrows():
                            # 💡 MEJORA CLAVE: Ahora le decimos a Wall Street que busque el TickerYahoo
                            ticker_bursatil = row.get("TickerYahoo", "")
                            
                            # Si TickerYahoo está vacío, probamos con el Ticker normal por si acaso
                            if pd.isna(ticker_bursatil) or str(ticker_bursatil).strip() == "":
                                ticker_bursatil = row.get("Ticker", "")

                            if pd.notna(ticker_bursatil) and str(ticker_bursatil).strip() != "":
                                try:
                                    info = yf.Ticker(str(ticker_bursatil).strip()).info
                                    precio = info.get('currentPrice', info.get('regularMarketPrice', 0))
                                    moneda = info.get('currency', row.get('MonedaCotizacion', 'EUR'))
                                    cierre_ant = info.get('previousClose', 0)
                                    
                                    if precio > 0:
                                        precios_actuales.append(f"{precio:.2f} {moneda}")
                                        var_pct = ((precio - cierre_ant) / cierre_ant) * 100 if cierre_ant > 0 else 0
                                        variaciones.append(f"{var_pct:+.2f}%")
                                    else:
                                        precios_actuales.append("No disp.")
                                        variaciones.append("-")
                                except:
                                    precios_actuales.append("Error Ticker")
                                    variaciones.append("-")
                            else:
                                precios_actuales.append("Sin Ticker")
                                variaciones.append("-")
                        
                        df_empresas_vivo = df_empresas.copy()
                        df_empresas_vivo["Precio Actual"] = precios_actuales
                        df_empresas_vivo["Variación Hoy"] = variaciones
                        
                        st.success("¡Cotizaciones actualizadas al segundo!")
                        
                        cols_finales = ["NombreING", "TickerYahoo", "Precio Actual", "Variación Hoy", "Sector"]
                        cols_finales_existentes = [c for c in cols_finales if c in df_empresas_vivo.columns]
                        st.dataframe(df_empresas_vivo[cols_finales_existentes], use_container_width=True)

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
                # 💡 MEJORA: Exportar las nuevas columnas para no perderlas
                columnas_export = ["ISIN", "NombreING", "NombreHacienda", "Pais", "Sector", "Subsector", "Capitalizacion", "Ticker", "TickerYahoo", "MonedaCotizacion"]
                cols_exp_existentes = [c for c in columnas_export if c in df_empresas.columns]
                csv_export = df_empresas[cols_exp_existentes].to_csv(index=False, sep=";").encode('utf-8-sig')
                st.download_button(label="⬇️ Descargar CSV", data=csv_export, file_name="BaseDatos_Empresas.csv", mime="text/csv")
            else:
                st.warning("No hay datos para exportar.")
                
        with col_imp:
            st.subheader("📥 Carga Masiva (Anti-Duplicados)")
            st.write("Sube tu CSV con tus datos. **Asegúrate de que los nombres de las columnas coincidan con la base de datos**.")
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

                        supabase.table("Empresas").upsert(registros_preparados).execute()
                        
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
                    supabase.table("Empresas").delete().gt("id", 0).execute()
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
# ==========================================
# 🚀 APLICACIÓN: AUDITORÍA PRO (DB)
# ==========================================
elif opcion == "⚖️ Auditoría Pro (DB)":
    st.title("⚖️ Auditoría Pro (Base de Datos)")
    st.write("Cruza los datos directamente desde Supabase, dividendo a dividendo (1 a 1). El sistema usa la columna ISIN y analiza su 'ADN' para conectar los derechos temporales con sus empresas matrices.")

    from datetime import datetime
    import pandas as pd
    anio_fiscal_defecto = datetime.now().year - 1

    ejercicio_auditar = st.number_input(
        "📅 ¿Qué Año Fiscal quieres auditar?", 
        min_value=2020, 
        max_value=2050, 
        value=anio_fiscal_defecto
    )

    st.markdown("---")

    if st.button("🔍 Iniciar Auditoría Pro (1 a 1)", type="primary", use_container_width=True):
        with st.spinner(f"Descargando y emparejando dividendos 1 a 1 del año {ejercicio_auditar}..."):
            try:
                from supabase import create_client, Client
                supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

                def isin_coincide(i1, i2):
                    if not i1 or not i2: return False
                    if i1 == i2: return True
                    if i1.startswith("ES") and i2.startswith("ES") and len(i1) >= 9 and len(i2) >= 9:
                        return i1[4:9] == i2[4:9]
                    return False

                res_ing = supabase.table("informefiscaling").select("id, isin, empresa, importe_bruto, retencion_destino, retencion_origen, concepto, retencion_recuperable, pais").eq("ejercicio_fiscal", int(ejercicio_auditar)).execute()
                res_aeat = supabase.table("informefiscalaeat").select("id, isin, codigo_emisor, nombre_emisor, importe_integro, retenciones, clave").eq("ejercicio_fiscal", int(ejercicio_auditar)).execute()

                if not res_ing.data and not res_aeat.data:
                    st.warning(f"🤷‍♂️ No hay datos guardados en ninguna de las dos tablas para el año {ejercicio_auditar}.")
                else:
                    ing_list = []
                    if res_ing.data:
                        for row in res_ing.data:
                            isin_limpio = str(row.get("isin", "")).replace('\xa0', '').replace(' ', '').strip().upper()
                            ing_list.append({
                                "id": row["id"],
                                "isin": isin_limpio,
                                "empresa": str(row.get("empresa", "")).strip(),
                                "concepto": str(row.get("concepto", "")).strip(),
                                "pais": str(row.get("pais", "Desconocido")).strip(),
                                "bruto": round(float(row.get("importe_bruto", 0)), 2),
                                "ret": round(float(row.get("retencion_destino", 0)), 2),
                                "ret_ori": round(float(row.get("retencion_origen", 0)), 2), 
                                "ret_recup": round(float(row.get("retencion_recuperable", 0)), 2), 
                                "comprobado": False  
                            })

                    aeat_list = []
                    if res_aeat.data:
                        for row in res_aeat.data:
                            isin_limpio = str(row.get("isin", "")).replace('\xa0', '').replace(' ', '').strip().upper()
                            aeat_list.append({
                                "id": row["id"],
                                "isin": isin_limpio,
                                "empresa": str(row.get("nombre_emisor", "")).strip(),
                                "clave": str(row.get("clave", "")).strip(),
                                "bruto": round(float(row.get("importe_integro", 0)), 2),
                                "ret": round(float(row.get("retenciones", 0)), 2),
                                "comprobado": False 
                            })

                    resultados = []

                    for div_ing in ing_list:
                        if div_ing["comprobado"]: continue
                        
                        mejor_pareja = None
                        for div_aeat in aeat_list:
                            if not div_aeat["comprobado"]:
                                if isin_coincide(div_ing["isin"], div_aeat["isin"]) and abs(div_aeat["bruto"] - div_ing["bruto"]) <= 0.02:
                                    mejor_pareja = div_aeat
                                    break 
                        
                        if mejor_pareja:
                            div_ing["comprobado"] = True
                            mejor_pareja["comprobado"] = True
                            
                            dif_b = div_ing["bruto"] - mejor_pareja["bruto"]
                            dif_r = div_ing["ret"] - mejor_pareja["ret"]
                            estado = "✅ Ok" if abs(dif_r) <= 0.05 else "⚠️ Descuadre Ret."
                            
                            resultados.append({
                                "Estado": estado,
                                "Concepto": mejor_pareja["clave"] if mejor_pareja["clave"] else div_ing["concepto"],
                                "ISIN": f'{div_ing["isin"]} / {mejor_pareja["isin"]}' if div_ing["isin"] != mejor_pareja["isin"] else div_ing["isin"],
                                "Empresa": div_ing["empresa"] if div_ing["empresa"] else mejor_pareja["empresa"],
                                "Pais": div_ing["pais"], 
                                "Bruto_ING": div_ing["bruto"],
                                "Bruto_AEAT": mejor_pareja["bruto"],
                                "Dif_Bruto": dif_b,
                                "Ret_ING": div_ing["ret"],
                                "Ret_AEAT": mejor_pareja["ret"],
                                "Dif_Ret": dif_r,
                                "Ret_Ori_ING": div_ing["ret_ori"], 
                                "Ret_Recuperable_ING": div_ing["ret_recup"] 
                            })
                        else:
                            resultados.append({
                                "Estado": "❌ Falta en AEAT",
                                "Concepto": div_ing["concepto"],
                                "ISIN": div_ing["isin"],
                                "Empresa": div_ing["empresa"],
                                "Pais": div_ing["pais"], 
                                "Bruto_ING": div_ing["bruto"],
                                "Bruto_AEAT": 0.0,
                                "Dif_Bruto": div_ing["bruto"],
                                "Ret_ING": div_ing["ret"],
                                "Ret_AEAT": 0.0,
                                "Dif_Ret": div_ing["ret"],
                                "Ret_Ori_ING": div_ing["ret_ori"], 
                                "Ret_Recuperable_ING": div_ing["ret_recup"] 
                            })

                    for div_aeat in aeat_list:
                        if not div_aeat["comprobado"]:
                            resultados.append({
                                "Estado": "❌ Falta en ING",
                                "Concepto": div_aeat["clave"],
                                "ISIN": div_aeat["isin"],
                                "Empresa": div_aeat["empresa"],
                                "Pais": "España",
                                "Bruto_ING": 0.0,
                                "Bruto_AEAT": div_aeat["bruto"],
                                "Dif_Bruto": -div_aeat["bruto"],
                                "Ret_ING": 0.0,
                                "Ret_AEAT": div_aeat["ret"],
                                "Dif_Ret": -div_aeat["ret"],
                                "Ret_Ori_ING": 0.0, 
                                "Ret_Recuperable_ING": 0.0 
                            })

                    df_cruce = pd.DataFrame(resultados)
                    df_cruce = df_cruce.sort_values(by=["Estado", "Empresa"], ascending=[False, True])

                    st.subheader("🎯 Resumen del Cruce Fiscal 1 a 1")
                    
                    tot_bruto_ing = df_cruce["Bruto_ING"].sum()
                    tot_bruto_aeat = df_cruce["Bruto_AEAT"].sum()
                    dif_global_bruto = tot_bruto_ing - tot_bruto_aeat

                    tot_bruto_consolidado = 0.0
                    tot_bruto_extranjero = 0.0
                    
                    # 🎯 LA LISTA NEGRA: Paises y empresas que NO sumarán al extranjero
                    paises_excluidos = ["ESPAÑA", "ES", "", "REINO UNIDO", "UK", "GB", "UNITED KINGDOM", "GREAT BRITAIN"]
                    empresas_excluidas = ["UNILEVER", "LYONDELLBASELL", "LYB"]
                    
                    for _, row in df_cruce.iterrows():
                        # Lógica Consolidado
                        if "Falta en" in row["Estado"]:
                            tot_bruto_consolidado += row["Bruto_ING"] if row["Bruto_ING"] != 0 else row["Bruto_AEAT"]
                        else:
                            tot_bruto_consolidado += row["Bruto_ING"]
                            
                        # Lógica Bruto Extranjero con Lista Negra
                        pais_upper = str(row.get("Pais", "")).strip().upper()
                        empresa_upper = str(row.get("Empresa", "")).strip().upper()
                        
                        es_excluida = False
                        
                        # 1. Comprobar si el país está excluido (España o UK)
                        if pais_upper in paises_excluidos:
                            es_excluida = True
                            
                        # 2. Comprobar si el nombre de la empresa está excluido (Unilever o LYB)
                        for emp in empresas_excluidas:
                            if emp in empresa_upper:
                                es_excluida = True
                                break
                                
                        # Si ha superado todos los filtros, lo sumamos
                        if not es_excluida:
                            tot_bruto_extranjero += row["Bruto_ING"]

                    tot_bruto_añadir_aeat = df_cruce[df_cruce["Estado"] == "❌ Falta en AEAT"]["Bruto_ING"].sum()
                    tot_ret_recuperable = df_cruce["Ret_Recuperable_ING"].sum()

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Bruto Total (ING)", f"{tot_bruto_ing:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    col2.metric("Bruto Total (AEAT)", f"{tot_bruto_aeat:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    
                    color_delta = "normal" if abs(dif_global_bruto) <= 1 else ("inverse" if dif_global_bruto < 0 else "off")
                    col3.metric("Descuadre Global Bruto", f"{dif_global_bruto:,.2f} €", delta=round(dif_global_bruto, 2), delta_color=color_delta)
                    
                    texto_extranjero = f"{tot_bruto_extranjero:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                    col4.metric(
                        "Bruto Extranjero (Resto)", 
                        texto_extranjero, 
                        help="Suma de los dividendos brutos cobrados en el extranjero. Excluye: España, UK, Unilever y LyondellBasell."
                    )
                    
                    st.markdown("<br>", unsafe_allow_html=True) 
                    
                    col5, col6, col7 = st.columns(3)
                    
                    texto_consolidado = f"{tot_bruto_consolidado:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                    col5.metric(
                        "Bruto Consolidado (Cas. 29 y 36)", 
                        texto_consolidado, 
                        help="Este es el valor total y real de tus dividendos que debes introducir en las Casillas 29 y 36 de tu Declaración de la Renta."
                    )
                    
                    texto_añadir = f"{tot_bruto_añadir_aeat:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                    col6.metric(
                        "Bruto a añadir a la declaración", 
                        texto_añadir, 
                        help="Dinero que has cobrado según el banco pero que Hacienda no sabe. Tienes que añadirlo en tu borrador."
                    )
                    
                    texto_recup = f"{tot_ret_recuperable:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                    col7.metric(
                        "Retención Origen Recuperable", 
                        texto_recup, 
                        help="Suma total de la retención en origen recuperable por doble imposición internacional para empresas extranjeras (Casilla 588)."
                    )

                    st.markdown("### 🔍 Detalle Dividendo a Dividendo")
                    
                    cols_a_mostrar = [col for col in df_cruce.columns if col not in ["Pais", "Ret_Ori_ING"]]
                    
                    # 🎯 SOLUCIONADO EL ERROR DE PANDAS: cambiado 'applymap' por 'map'
                    df_mostrar = df_cruce[cols_a_mostrar].style.format({
                        "Bruto_ING": "{:.2f} €", "Bruto_AEAT": "{:.2f} €", "Dif_Bruto": "{:.2f} €",
                        "Ret_ING": "{:.2f} €", "Ret_AEAT": "{:.2f} €", "Dif_Ret": "{:.2f} €",
                        "Ret_Recuperable_ING": "{:.2f} €" 
                    }).map(
                        lambda x: f"color: {'#ff4b4b' if abs(x) > 0.10 else '#21c354'}", 
                        subset=["Dif_Bruto", "Dif_Ret"]
                    )
                    
                    st.dataframe(df_mostrar, use_container_width=True, height=600)

                    csv_cruce = df_cruce.to_csv(index=False, sep=";").encode('utf-8-sig')
                    st.download_button(
                        label="⬇️ Descargar Auditoría (CSV)", 
                        data=csv_cruce, 
                        file_name=f"Auditoria_Pro_1a1_{ejercicio_auditar}.csv", 
                        mime='text/csv'
                    )

            except Exception as e:
                st.error(f"❌ Error interno al realizar la auditoría: {e}")











# ==========================================
# 🚀 APLICACIÓN 10: EXTRACTOR INFORME FISCAL AEAT
# ==========================================
elif opcion == "🏛️ Extractor Informe Fiscal (AEAT)":
    st.title("🏛️ Extractor Total del Informe Fiscal AEAT")
    st.write("Sube el archivo Excel o CSV de tus datos fiscales descargado de Hacienda. El sistema lo leerá, traducirá los nombres de las empresas, obtendrá su ISIN y lo guardará en tu base de datos.")

    from datetime import datetime
    import re
    
    anio_fiscal_defecto = datetime.now().year - 1

    ejercicio_fiscal_aeat = st.number_input(
        "📅 ¿De qué Año Fiscal son estos datos?", 
        min_value=2020, 
        max_value=2050, 
        value=anio_fiscal_defecto
    )
    
    archivo_aeat = st.file_uploader("Sube el Excel/CSV de Hacienda", type=["csv", "xlsx", "xls"], key="inf_aeat_solo")

    if archivo_aeat:
        with st.spinner("Analizando formato de Hacienda, cazando ISINs y conectando con tu Base de Datos..."):
            try:
                # 1️⃣ LECTURA DEL ARCHIVO
                if archivo_aeat.name.endswith('.csv'):
                    df_aeat = pd.read_csv(archivo_aeat, sep=None, engine='python')
                else:
                    df_aeat = pd.read_excel(archivo_aeat)

                df_aeat = df_aeat.fillna("")

                # -------------------------------------------------------------
                # 🕵️‍♂️ CAZADOR DE CABECERAS
                # -------------------------------------------------------------
                cols_actuales = " ".join([str(c).lower() for c in df_aeat.columns])
                if "emisor" not in cols_actuales and "declarante" not in cols_actuales:
                    header_idx = -1
                    for idx, row in df_aeat.head(15).iterrows():
                        fila_texto = " ".join([str(val).lower() for val in row.values])
                        if "emisor" in fila_texto and ("integro" in fila_texto.replace("í", "i") or "retencion" in fila_texto.replace("ó", "o")):
                            header_idx = idx
                            break
                    
                    if header_idx != -1:
                        df_aeat.columns = [str(c).strip() for c in df_aeat.iloc[header_idx]]
                        df_aeat = df_aeat.iloc[header_idx + 1:].reset_index(drop=True)
                
                cols = df_aeat.columns.tolist()
                def encontrar_columna(claves):
                    for col in cols:
                        if any(c.lower() in col.lower() for c in claves): return col
                    return None

                col_codigo = encontrar_columna(["emisor", "código", "codigo"])
                col_nif_emi = encontrar_columna(["nif emisor", "nif del emisor"])
                col_nom_emi = encontrar_columna(["nombre emisor", "nombre del emisor"])
                col_nif_dec = encontrar_columna(["nif declarante", "nif del declarante"])
                col_nom_dec = encontrar_columna(["nombre declarante", "apellidos", "razón social declarante", "razon social"])
                col_clave = encontrar_columna(["clave"])
                col_tipo = encontrar_columna(["tipo"])
                col_bruto = encontrar_columna(["íntegro", "integro", "bruto", "rendimiento", "importe"])
                col_penal = encontrar_columna(["penalización", "penalizacion"])
                col_ret = encontrar_columna(["retencion", "retención", "retenciones"])
                col_gastos = encontrar_columna(["gastos", "deducibles"])

                # 2️⃣ DESCARGAMOS TU DICCIONARIO DE EMPRESAS (AMPLIADO A 5000 Y LIMPIO)
                try:
                    from supabase import create_client, Client
                    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
                    
                    # 🚀 Aumento del límite de descarga a 5000 para evitar que Supabase esconda datos
                    res_empresas = supabase.table("Empresas").select("ISIN, NombreING, NombreHacienda").limit(5000).execute()
                    lista_empresas = res_empresas.data if res_empresas.data else []
                    
                    map_isin = {}
                    map_hac = {}
                    map_ing = {}
                    map_name_to_isin = {}
                    isins_en_db = set()
                    
                    for e in lista_empresas:
                        # 🚀 Limpieza extrema anti espacios invisibles
                        isin_val = str(e.get("ISIN", "")).replace('\xa0', '').strip().upper()
                        nom_ing = str(e.get("NombreING", "")).replace('\xa0', '').strip().upper()
                        nom_hac = str(e.get("NombreHacienda", "")).replace('\xa0', '').strip().upper()
                        
                        if isin_val:
                            isins_en_db.add(isin_val)
                            if nom_ing and isin_val not in map_isin: 
                                map_isin[isin_val] = nom_ing
                        if nom_hac and nom_ing: map_hac[nom_hac] = nom_ing
                        if nom_ing: map_ing[nom_ing] = nom_ing
                        
                        if isin_val:
                            if nom_hac: map_name_to_isin[nom_hac] = isin_val
                            if nom_ing: map_name_to_isin[nom_ing] = isin_val

                except Exception as e:
                    st.warning(f"⚠️ No se pudo cargar la tabla de Empresas: {e}")
                    map_isin, map_hac, map_ing, map_name_to_isin, isins_en_db = {}, {}, {}, {}, set()

                # -------------------------------------------------------------
                # 🚨 DICCIONARIO DE CASOS ESPECIALES
                # -------------------------------------------------------------
                map_scrip_dividends = {}
                map_nombres_rebeldes = {
                    "BANCO DE SABADELL, S.A.": "ES0113860A34",
                    "BANCO SABADELL": "ES0113860A34"
                }

                # 3️⃣ ENRIQUECEMOS EL DATAFRAME
                def enriquecer_fila(row):
                    raw_codigo = str(row.get(col_codigo, "")).replace('\xa0', '').strip() if col_codigo else ""
                    raw_emisor = str(row.get(col_nom_emi, "")).replace('\xa0', '').strip() if col_nom_emi else ""
                    
                    if raw_emisor.lower() in ["emisor", "nombre emisor", "nombre del emisor"]:
                        return pd.Series(["", ""]) 

                    codigo_upper = raw_codigo.upper()
                    emisor_upper = raw_emisor.upper()
                    
                    def limpiar_ruido(texto):
                        t = texto
                        ruidos = [", S.A.", " S.A.", " S.A", ", S.L.", " S.L.", " S.L", " INC.", " INC", " CORP.", " CORP", " PLC", " N.V.", ","]
                        for r in ruidos:
                            t = t.replace(r, "")
                        t = t.replace("BANCO DE ", "BANCO ")
                        return t.strip()
                        
                    emisor_limpio = limpiar_ruido(emisor_upper)

                    # A. TRADUCTOR DE NOMBRE INICIAL
                    nombre_traducido = raw_emisor 
                    if emisor_upper in map_hac: 
                        nombre_traducido = map_hac[emisor_upper]
                    elif emisor_limpio in map_hac: 
                        nombre_traducido = map_hac[emisor_limpio]
                    else:
                        for n_ing in sorted(map_ing.keys(), key=len, reverse=True):
                            # Reducimos a >=3 letras para que detecte cosas cortas como "ACS"
                            if n_ing and len(n_ing) >= 3 and (n_ing in emisor_upper or n_ing in emisor_limpio):
                                nombre_traducido = map_ing[n_ing]
                                break

                    # B. 🎯 CAZADOR DE ISIN
                    isin_encontrado = ""
                    
                    if emisor_upper in map_nombres_rebeldes:
                        isin_encontrado = map_nombres_rebeldes[emisor_upper]
                    else:
                        texto_combinado = f"{codigo_upper} {emisor_upper}"
                        match_isin = re.search(r"([A-Z]{2}[A-Z0-9]{10})", texto_combinado)
                        
                        if match_isin:
                            isin_encontrado = match_isin.group(1)
                            if isin_encontrado in map_scrip_dividends:
                                isin_encontrado = map_scrip_dividends[isin_encontrado]
                        else:
                            if emisor_upper in map_name_to_isin: isin_encontrado = map_name_to_isin[emisor_upper]
                            elif emisor_limpio in map_name_to_isin: isin_encontrado = map_name_to_isin[emisor_limpio]
                            elif nombre_traducido.upper() in map_name_to_isin: isin_encontrado = map_name_to_isin[nombre_traducido.upper()]
                            else:
                                for n_db in sorted(map_name_to_isin.keys(), key=len, reverse=True):
                                    if n_db and len(n_db) >= 3 and (n_db in emisor_upper or n_db in emisor_limpio):
                                        isin_encontrado = map_name_to_isin[n_db]
                                        break
                    
                    # C. REGLA DE ORO: EL ISIN ES EL REY
                    if isin_encontrado and isin_encontrado in map_isin:
                        nombre_traducido = map_isin[isin_encontrado]

                    return pd.Series([isin_encontrado, nombre_traducido])

                df_aeat[["ISIN_Detectado", "Empresa_Traducida"]] = df_aeat.apply(enriquecer_fila, axis=1)

                cols_order = ["ISIN_Detectado", "Empresa_Traducida"] + [c for c in df_aeat.columns if c not in ["ISIN_Detectado", "Empresa_Traducida"]]
                df_aeat = df_aeat[cols_order]

                st.write("📊 **Vista previa de los datos enriquecidos (Listos para subir):**")
                st.dataframe(df_aeat)

                # -------------------------------------------------------------
                # 🚨 ESCÁNER DE COHERENCIA CONTRA LA TABLA "EMPRESAS"
                # -------------------------------------------------------------
                empresas_sin_isin = set()
                isins_no_registrados = set()
                
                info_derechos_warning = {
                    "ES06670509O8": " ➡️ *Derechos de ACS*",
                    "ES06670509P5": " ➡️ *Derechos de ACS*",
                    "ES06670509Q3": " ➡️ *Derechos de ACS*",
                    "ES06670509R1": " ➡️ *Derechos de ACS*",
                    "ES06445809S7": " ➡️ *Derechos de Iberdrola*",
                    "ES06445809U3": " ➡️ *Derechos de Iberdrola*",
                    "FR001400UH43": " ➡️ *Acciones de Lealtad de L'Oréal*"
                }
                
                for _, row in df_aeat.iterrows():
                    isin_val = str(row.get("ISIN_Detectado", "")).strip()
                    nom_val = str(row.get("Empresa_Traducida", "")).strip()
                    raw_nom = str(row.get(col_nom_emi, "")).strip()
                    
                    if raw_nom.lower() in ["emisor", "nombre emisor", "nombre del emisor"] or (row.get(col_bruto, "") == "" and row.get(col_ret, "") == ""):
                        continue 

                    if not isin_val:
                        empresas_sin_isin.add(nom_val if nom_val else raw_nom)
                    elif isin_val not in isins_en_db:
                        etiqueta_extra = info_derechos_warning.get(isin_val, "")
                        if not etiqueta_extra and isin_val.startswith("ES06"):
                            etiqueta_extra = " ➡️ *Posibles derechos de acción matriz*"
                            
                        isins_no_registrados.add(f"{nom_val} (ISIN: {isin_val}){etiqueta_extra}")

                if empresas_sin_isin or isins_no_registrados:
                    st.warning("⚠️ **ATENCIÓN: Tienes tareas pendientes en tu Gestor de Empresas**")
                    
                    if empresas_sin_isin:
                        st.markdown("**1️⃣ Empresas sin ISIN (Añádelas en el Gestor de Empresas):**")
                        for emp in sorted(list(empresas_sin_isin)):
                            st.write(f"- ❌ {emp}")
                            
                    if isins_no_registrados:
                        st.markdown("**2️⃣ ISINs detectados en el Excel, pero que NO están guardados en tu base de datos:**")
                        for isin_f in sorted(list(isins_no_registrados)):
                            st.write(f"- 🔍 {isin_f}")
                            
                    st.info("💡 **Consejo:** Añade estas empresas en la pestaña '🏢 Gestor de Empresas (DB)' antes de auditar, para que el cruce sea 100% perfecto.")
                else:
                    st.success("✅ ¡Matrícula de Honor! Todos los ISINs del Excel están perfectamente registrados en tu base de datos.")

                st.markdown("---")

                # -------------------------------------------------------------
                st.info("💡 **Filtro Anti-Duplicados Inteligente Activado:** El sistema cotejará Código + NIF + Importe.")

                if st.button("☁️ Subir a Base de Datos (informefiscalaeat)", type="primary"):
                    with st.spinner("Comprobando duplicados y subiendo a la nube..."):
                        try:
                            res_db = supabase.table("informefiscalaeat").select("codigo_emisor, nif_emisor, nombre_emisor, importe_integro").eq("ejercicio_fiscal", int(ejercicio_fiscal_aeat)).execute()
                            
                            db_existentes = [] 
                            if res_db.data:
                                for row_db in res_db.data:
                                    cod_db = str(row_db.get("codigo_emisor", "")).strip() 
                                    nif_db = str(row_db.get("nif_emisor", "")).strip()
                                    nom_db = str(row_db.get("nombre_emisor", "")).strip()
                                    identificador = nif_db if nif_db else nom_db 
                                    imp_db = round(float(row_db.get("importe_integro", 0)), 2)
                                    
                                    firma = f"{cod_db}_{identificador}_{imp_db}"
                                    db_existentes.append(firma) 

                            registros_aeat = []
                            
                            for _, row in df_aeat.iterrows():
                                val_bruto = euro_a_numero(row.get(col_bruto, 0)) if col_bruto else 0.0
                                val_ret = euro_a_numero(row.get(col_ret, 0)) if col_ret else 0.0
                                
                                if val_bruto == 0 and val_ret == 0: 
                                    continue 
                                    
                                raw_codigo = str(row.get(col_codigo, "")).strip() if col_codigo else ""
                                raw_emisor = str(row.get(col_nom_emi, "")).strip() if col_nom_emi else ""
                                
                                if raw_emisor.lower() in ["emisor", "nombre emisor", "nombre del emisor"]:
                                    continue
                                
                                nombre_traducido = str(row.get("Empresa_Traducida", raw_emisor)).strip()
                                isin_encontrado = str(row.get("ISIN_Detectado", "")).strip()

                                nif_emi_excel = str(row.get(col_nif_emi, "")).strip()[:50] if col_nif_emi else ""
                                identificador_excel = nif_emi_excel if nif_emi_excel else nombre_traducido[:250]
                                importe_excel = round(val_bruto, 2)
                                
                                firma_actual = f"{raw_codigo[:100]}_{identificador_excel}_{importe_excel}"

                                if firma_actual in db_existentes:
                                    db_existentes.remove(firma_actual)
                                else:
                                    registro = {
                                        "nif_declarante": str(row.get(col_nif_dec, "")).strip()[:50] if col_nif_dec else "",
                                        "nombre_declarante": str(row.get(col_nom_dec, "")).strip()[:250] if col_nom_dec else "",
                                        "codigo_emisor": raw_codigo[:100],
                                        "nif_emisor": nif_emi_excel,
                                        "nombre_emisor": nombre_traducido[:250], 
                                        "clave": str(row.get(col_clave, "")).strip()[:50] if col_clave else "",
                                        "tipo": str(row.get(col_tipo, "")).strip()[:50] if col_tipo else "",
                                        "importe_integro": importe_excel,
                                        "penalizacion": round(euro_a_numero(row.get(col_penal, 0)), 2) if col_penal else 0.0,
                                        "retenciones": round(val_ret, 2),
                                        "gastos_deducibles": round(euro_a_numero(row.get(col_gastos, 0)), 2) if col_gastos else 0.0,
                                        "ejercicio_fiscal": int(ejercicio_fiscal_aeat),
                                        "isin": isin_encontrado[:50] 
                                    }
                                    registros_aeat.append(registro)
                            
                            if registros_aeat:
                                supabase.table("informefiscalaeat").insert(registros_aeat).execute()
                                st.success(f"✅ ¡{len(registros_aeat)} operaciones NUEVAS guardadas con éxito para el año {ejercicio_fiscal_aeat}!")
                                st.balloons()
                            else:
                                st.info("ℹ️ No se ha subido nada. Todos los datos de este Excel ya estaban en tu base de datos (0 duplicados).")
                                
                        except Exception as e:
                            st.error(f"❌ Error al comunicar con Supabase: {e}")
            except Exception as e:
                st.error(f"❌ Error procesando el archivo: {e}")








# ==========================================
# 🚀 APLICACIÓN 11: AUDITORÍA INTERNA (ING vs MOVS)
# ==========================================
elif opcion == "🕵️‍♂️ Auditoría Interna (ING)":
    st.title("🕵️‍♂️ Auditoría Interna (ING)")
    st.write("Cruza los datos del **Informe Fiscal Anual de ING** con la suma de los **PDFs de Dividendos individuales**. Ahora potenciado con cruce exacto por ISIN.")

    from datetime import datetime
    import pandas as pd
    anio_fiscal_defecto = datetime.now().year - 1

    ejercicio_auditar = st.number_input(
        "📅 ¿Qué Año Fiscal quieres auditar internamente?", 
        min_value=2020, 
        max_value=2050, 
        value=anio_fiscal_defecto
    )

    st.markdown("---")

    if st.button("🔍 Iniciar Auditoría Interna", type="primary", use_container_width=True):
        with st.spinner(f"Cruzando Informe Fiscal vs Movimientos Individuales de {ejercicio_auditar}..."):
            try:
                from supabase import create_client, Client
                supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

                # 🧠 Función de ADN para los ISINs
                def isin_coincide(i1, i2):
                    if not i1 or not i2: return False
                    if i1 == i2: return True
                    if i1.startswith("ES") and i2.startswith("ES") and len(i1) >= 9 and len(i2) >= 9:
                        return i1[4:9] == i2[4:9]
                    return False

                # 1️⃣ DESCARGAR DATOS DE AMBAS TABLAS (AHORA CON ISIN)
                res_inf = supabase.table("informefiscaling").select("id, isin, empresa, importe_bruto, retencion_destino, retencion_origen, concepto").eq("ejercicio_fiscal", int(ejercicio_auditar)).execute()
                res_movs = supabase.table("MovimientosDividendos").select("id, isin, empresa, bruto_ing, ret_origen_ing, ret_destino_ing, fecha").eq("ejercicio_fiscal", int(ejercicio_auditar)).execute()

                if not res_inf.data and not res_movs.data:
                    st.warning(f"🤷‍♂️ No hay datos guardados en ninguna de las dos tablas para el año {ejercicio_auditar}.")
                else:
                    inf_list = []
                    if res_inf.data:
                        for row in res_inf.data:
                            inf_list.append({
                                "id": row["id"],
                                "isin": str(row.get("isin", "")).strip().upper(),
                                "empresa": str(row.get("empresa", "")).strip(),
                                "bruto": round(float(row.get("importe_bruto", 0)), 2),
                                "ret_des": round(float(row.get("retencion_destino", 0)), 2),
                                "ret_ori": round(float(row.get("retencion_origen", 0)), 2),
                                "comprobado": False
                            })

                    mov_list = []
                    if res_movs.data:
                        for row in res_movs.data:
                            mov_list.append({
                                "id": row["id"],
                                "isin": str(row.get("isin", "")).strip().upper(),
                                "fecha": str(row.get("fecha", "")),
                                "empresa": str(row.get("empresa", "")).strip(),
                                "bruto": round(float(row.get("bruto_ing", 0)), 2),
                                "ret_des": round(float(row.get("ret_destino_ing", 0)), 2),
                                "ret_ori": round(float(row.get("ret_origen_ing", 0)), 2),
                                "comprobado": False
                            })

                    resultados = []

                    for inf in inf_list:
                        if inf["comprobado"]: continue
                        
                        mejor_pareja = None
                        for mov in mov_list:
                            if not mov["comprobado"]:
                                # 🎯 CRUCE PERFECTO: Mismo ADN de ISIN y mismo Bruto
                                if isin_coincide(inf["isin"], mov["isin"]) and abs(mov["bruto"] - inf["bruto"]) <= 0.02:
                                    mejor_pareja = mov
                                    break
                        
                        if mejor_pareja:
                            inf["comprobado"] = True
                            mejor_pareja["comprobado"] = True
                            
                            dif_b = inf["bruto"] - mejor_pareja["bruto"]
                            dif_r_des = inf["ret_des"] - mejor_pareja["ret_des"]
                            dif_r_ori = inf["ret_ori"] - mejor_pareja["ret_ori"]
                            
                            if abs(dif_b) <= 0.05 and abs(dif_r_des) <= 0.05 and abs(dif_r_ori) <= 0.05:
                                estado = "✅ Ok"
                            else:
                                estado = "⚠️ Descuadre Ret."
                                
                            resultados.append({
                                "Estado": estado,
                                "ISIN": inf["isin"],
                                "Empresa": inf["empresa"],
                                "Bruto_Inf": inf["bruto"],
                                "Bruto_Mov": mejor_pareja["bruto"],
                                "Dif_Bruto": dif_b,
                                "Ret_Des_Inf": inf["ret_des"],
                                "Ret_Des_Mov": mejor_pareja["ret_des"],
                                "Dif_Ret_Des": dif_r_des,
                                "Ret_Ori_Inf": inf["ret_ori"],
                                "Ret_Ori_Mov": mejor_pareja["ret_ori"],
                                "Dif_Ret_Ori": dif_r_ori
                            })
                        else:
                            resultados.append({
                                "Estado": "❌ Falta en Movimientos (PDF)",
                                "ISIN": inf["isin"],
                                "Empresa": inf["empresa"],
                                "Bruto_Inf": inf["bruto"],
                                "Bruto_Mov": 0.0,
                                "Dif_Bruto": inf["bruto"],
                                "Ret_Des_Inf": inf["ret_des"],
                                "Ret_Des_Mov": 0.0,
                                "Dif_Ret_Des": inf["ret_des"],
                                "Ret_Ori_Inf": inf["ret_ori"],
                                "Ret_Ori_Mov": 0.0,
                                "Dif_Ret_Ori": inf["ret_ori"]
                            })
                            
                    for mov in mov_list:
                        if not mov["comprobado"]:
                            resultados.append({
                                "Estado": "❌ Falta en Informe Fiscal",
                                "ISIN": mov["isin"],
                                "Empresa": mov["empresa"],
                                "Bruto_Inf": 0.0,
                                "Bruto_Mov": mov["bruto"],
                                "Dif_Bruto": -mov["bruto"],
                                "Ret_Des_Inf": 0.0,
                                "Ret_Des_Mov": mov["ret_des"],
                                "Dif_Ret_Des": -mov["ret_des"],
                                "Ret_Ori_Inf": 0.0,
                                "Ret_Ori_Mov": mov["ret_ori"],
                                "Dif_Ret_Ori": -mov["ret_ori"]
                            })
                            
                    # 5️⃣ RENDERIZADO VISUAL
                    df_cruce = pd.DataFrame(resultados)
                    df_cruce = df_cruce.sort_values(by=["Estado", "Empresa"], ascending=[False, True])

                    st.subheader("🎯 Resumen de la Auditoría Interna")
                    
                    tot_bruto_inf = df_cruce["Bruto_Inf"].sum()
                    tot_bruto_mov = df_cruce["Bruto_Mov"].sum()
                    dif_global_bruto = tot_bruto_inf - tot_bruto_mov
                    
                    tot_ret_des_inf = df_cruce["Ret_Des_Inf"].sum()
                    tot_ret_des_mov = df_cruce["Ret_Des_Mov"].sum()
                    dif_global_ret_des = tot_ret_des_inf - tot_ret_des_mov

                    tot_ret_ori_inf = df_cruce["Ret_Ori_Inf"].sum()
                    tot_ret_ori_mov = df_cruce["Ret_Ori_Mov"].sum()
                    dif_global_ret_ori = tot_ret_ori_inf - tot_ret_ori_mov

                    st.markdown("##### 💰 Importe Bruto")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto (Informe Fiscal)", f"{tot_bruto_inf:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    c2.metric("Bruto (Movimientos)", f"{tot_bruto_mov:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    color_d_b = "normal" if abs(dif_global_bruto) <= 1 else "inverse"
                    c3.metric("Descuadre Bruto", f"{dif_global_bruto:,.2f} €", delta=round(dif_global_bruto, 2), delta_color=color_d_b)
                    
                    st.markdown("##### 🇪🇸 Retención en Destino (España)")
                    c4, c5, c6 = st.columns(3)
                    c4.metric("Ret. Destino (Informe Fiscal)", f"{tot_ret_des_inf:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    c5.metric("Ret. Destino (Movimientos)", f"{tot_ret_des_mov:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    color_d_rd = "normal" if abs(dif_global_ret_des) <= 1 else "inverse"
                    c6.metric("Descuadre Ret. Destino", f"{dif_global_ret_des:,.2f} €", delta=round(dif_global_ret_des, 2), delta_color=color_d_rd)

                    st.markdown("##### 🌍 Retención en Origen (Extranjero)")
                    c7, c8, c9 = st.columns(3)
                    c7.metric("Ret. Origen (Informe Fiscal)", f"{tot_ret_ori_inf:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    c8.metric("Ret. Origen (Movimientos)", f"{tot_ret_ori_mov:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
                    color_d_ro = "normal" if abs(dif_global_ret_ori) <= 1 else "inverse"
                    c9.metric("Descuadre Ret. Origen", f"{dif_global_ret_ori:,.2f} €", delta=round(dif_global_ret_ori, 2), delta_color=color_d_ro)

                    st.markdown("### 🔍 Detalle Dividendo a Dividendo")
                    
                    df_mostrar = df_cruce.style.format({
                        "Bruto_Inf": "{:.2f} €", "Bruto_Mov": "{:.2f} €", "Dif_Bruto": "{:.2f} €",
                        "Ret_Des_Inf": "{:.2f} €", "Ret_Des_Mov": "{:.2f} €", "Dif_Ret_Des": "{:.2f} €",
                        "Ret_Ori_Inf": "{:.2f} €", "Ret_Ori_Mov": "{:.2f} €", "Dif_Ret_Ori": "{:.2f} €"
                    }).map(
                        lambda x: f"color: {'#ff4b4b' if abs(x) > 0.10 else '#21c354'}", 
                        subset=["Dif_Bruto", "Dif_Ret_Des", "Dif_Ret_Ori"]
                    )
                    
                    st.dataframe(df_mostrar, use_container_width=True, height=600)

                    csv_cruce = df_cruce.to_csv(index=False, sep=";").encode('utf-8-sig')
                    st.download_button(
                        label="⬇️ Descargar Auditoría Interna (CSV)", 
                        data=csv_cruce, 
                        file_name=f"Auditoria_Interna_ING_{ejercicio_auditar}.csv", 
                        mime='text/csv'
                    )

            except Exception as e:
                st.error(f"❌ Error interno al realizar la auditoría: {e}")




# ==========================================
# 🚀 APLICACIÓN: GESTOR MANUAL DE MOVIMIENTOS
# ==========================================
elif opcion == "✍️ Gestor Manual de Movimientos":
    st.title("✍️ Gestor Manual de Movimientos")
    st.write("Añade, edita o elimina dividendos manualmente en tu base de datos `MovimientosDividendos`.")

    try:
        from supabase import create_client, Client
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # Descargar los datos actuales para mostrarlos y poder seleccionarlos
        res = supabase.table("MovimientosDividendos").select("*").order("fecha", desc=True).execute()
        
        import pandas as pd
        df_movs = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        # Creamos las pestañas de navegación
        tab1, tab2, tab3, tab4 = st.tabs(["👀 Ver Datos", "➕ Añadir", "✏️ Editar", "🗑️ Borrar"])

        # -------------------------------------------------------------
        # PESTAÑA 1: VER DATOS
        # -------------------------------------------------------------
        with tab1:
            st.subheader("Datos actuales en la Base de Datos")
            if not df_movs.empty:
                # Ordenamos las columnas para que se vean bonitas
                cols_orden = ["id", "fecha", "empresa", "isin", "bruto_ing", "ret_origen_ing", "ret_destino_ing", "ejercicio_fiscal"]
                # Filtramos solo las columnas que existen en el dataframe
                cols_mostrar = [c for c in cols_orden if c in df_movs.columns]
                st.dataframe(df_movs[cols_mostrar], use_container_width=True)
            else:
                st.info("ℹ️ La base de datos está vacía en este momento.")

        # -------------------------------------------------------------
        # PESTAÑA 2: AÑADIR UN REGISTRO
        # -------------------------------------------------------------
        with tab2:
            st.subheader("➕ Añadir Nuevo Movimiento")
            with st.form("form_add_movimiento", clear_on_submit=True):
                col1, col2 = st.columns(2)
                f_fecha = col1.date_input("📅 Fecha de abono")
                f_empresa = col2.text_input("🏢 Empresa")
                f_isin = col1.text_input("🆔 ISIN")
                f_bruto = col2.number_input("💰 Importe Bruto (€)", min_value=0.0, step=0.01, format="%.2f")
                f_ret_ori = col1.number_input("🌍 Retención Origen (€)", min_value=0.0, step=0.01, format="%.2f")
                f_ret_des = col2.number_input("🇪🇸 Retención Destino (€)", min_value=0.0, step=0.01, format="%.2f")
                
                submitted_add = st.form_submit_button("Guardar Nuevo Movimiento", type="primary")
                
                if submitted_add:
                    nuevo_registro = {
                        "fecha": f_fecha.strftime("%Y-%m-%d"),
                        "empresa": f_empresa.strip().upper(),
                        "isin": f_isin.strip().upper(),
                        "bruto_ing": float(f_bruto),
                        "ret_origen_ing": float(f_ret_ori),
                        "ret_destino_ing": float(f_ret_des),
                        "ejercicio_fiscal": f_fecha.year
                    }
                    supabase.table("MovimientosDividendos").insert(nuevo_registro).execute()
                    st.success("✅ Movimiento añadido correctamente. Refrescando...")
                    import time; time.sleep(1)
                    st.rerun() # Refresca la página para mostrar los datos nuevos

        # -------------------------------------------------------------
        # PESTAÑA 3: EDITAR UN REGISTRO
        # -------------------------------------------------------------
        with tab3:
            st.subheader("✏️ Editar Movimiento Existente")
            if not df_movs.empty:
                # Crear una lista de opciones legible para el usuario
                opciones_edit = df_movs.apply(lambda x: f"ID: {x['id']} | {x['fecha']} | {x['empresa']} | {x['bruto_ing']}€", axis=1).tolist()
                seleccion_edit = st.selectbox("📌 Selecciona el movimiento que quieres editar:", opciones_edit, key="sel_edit")
                
                if seleccion_edit:
                    id_seleccionado = int(seleccion_edit.split(" | ")[0].replace("ID: ", ""))
                    fila_sel = df_movs[df_movs["id"] == id_seleccionado].iloc[0]
                    
                    with st.form("form_edit_movimiento"):
                        from datetime import datetime
                        fecha_defecto = datetime.strptime(fila_sel["fecha"], "%Y-%m-%d").date() if fila_sel["fecha"] else datetime.now().date()
                        
                        col1, col2 = st.columns(2)
                        e_fecha = col1.date_input("📅 Fecha de abono", value=fecha_defecto)
                        e_empresa = col2.text_input("🏢 Empresa", value=str(fila_sel.get("empresa", "")))
                        e_isin = col1.text_input("🆔 ISIN", value=str(fila_sel.get("isin", "")))
                        e_bruto = col2.number_input("💰 Importe Bruto (€)", value=float(fila_sel.get("bruto_ing", 0.0)), step=0.01, format="%.2f")
                        e_ret_ori = col1.number_input("🌍 Retención Origen (€)", value=float(fila_sel.get("ret_origen_ing", 0.0)), step=0.01, format="%.2f")
                        e_ret_des = col2.number_input("🇪🇸 Retención Destino (€)", value=float(fila_sel.get("ret_destino_ing", 0.0)), step=0.01, format="%.2f")
                        
                        submitted_edit = st.form_submit_button("💾 Guardar Cambios", type="primary")
                        
                        if submitted_edit:
                            datos_actualizados = {
                                "fecha": e_fecha.strftime("%Y-%m-%d"),
                                "empresa": e_empresa.strip().upper(),
                                "isin": e_isin.strip().upper(),
                                "bruto_ing": float(e_bruto),
                                "ret_origen_ing": float(e_ret_ori),
                                "ret_destino_ing": float(e_ret_des),
                                "ejercicio_fiscal": e_fecha.year
                            }
                            supabase.table("MovimientosDividendos").update(datos_actualizados).eq("id", id_seleccionado).execute()
                            st.success("✅ Registro actualizado correctamente. Refrescando...")
                            import time; time.sleep(1)
                            st.rerun()
            else:
                st.info("ℹ️ No hay movimientos para editar.")

        # -------------------------------------------------------------
        # PESTAÑA 4: BORRAR REGISTROS
        # -------------------------------------------------------------
        with tab4:
            st.subheader("🗑️ Borrar Movimiento a Mano")
            if not df_movs.empty:
                opciones_del = df_movs.apply(lambda x: f"ID: {x['id']} | {x['fecha']} | {x['empresa']} | {x['bruto_ing']}€", axis=1).tolist()
                seleccion_del = st.selectbox("📌 Selecciona el movimiento a ELIMINAR:", opciones_del, key="sel_del")
                
                if st.button("❌ Eliminar Registro Seleccionado"):
                    id_a_borrar = int(seleccion_del.split(" | ")[0].replace("ID: ", ""))
                    supabase.table("MovimientosDividendos").delete().eq("id", id_a_borrar).execute()
                    st.success("🗑️ Registro eliminado. Refrescando...")
                    import time; time.sleep(1)
                    st.rerun()
                
                st.markdown("---")
                st.markdown("### 🚨 Zona de Peligro")
                st.error("⚠️ Esta acción borrará **absolutamente todos** los datos de la tabla `MovimientosDividendos` y no se puede deshacer.")
                
                if st.button("🔥 BORRAR TODOS LOS DATOS", type="primary"):
                    # Confirmación rápida
                    supabase.table("MovimientosDividendos").delete().neq("id", -1).execute()
                    st.success("💥 Base de datos limpiada por completo. Refrescando...")
                    import time; time.sleep(1)
                    st.rerun()
            else:
                st.info("ℹ️ La base de datos ya está vacía.")

    except Exception as e:
        st.error(f"❌ Error de conexión con la base de datos: {e}")





