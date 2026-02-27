import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📄 Extractor Profesional de Dividendos ING")
st.write("Sube tus recibos de dividendos en PDF y obtén tu tabla lista para importar.")

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

def calcular_porcentaje(parte_str, total_str):
    """Calcula el % de retención e identifica retenciones exactas por país."""
    try:
        p = float(parte_str.replace('.', '').replace(',', '.'))
        t = float(total_str.replace('.', '').replace(',', '.'))
        if t == 0 or p == 0: 
            return "0%"
        
        ratio = p / t
        
        # Reconocimiento inteligente de los tramos fiscales
        if 0.26 <= ratio <= 0.27:
            return "26,375%"  # Alemania
        elif 0.245 <= ratio <= 0.255:
            return "25%"      # Francia
        elif 0.14 <= ratio <= 0.16:
            return "15%"      # USA (Con formulario W-8BEN)
        elif 0.185 <= ratio <= 0.195:
            return "19%"      # España (Destino)
            
        # Si es un porcentaje distinto a estos, lo calcula matemáticamente con 2 decimales
        return f"{round(ratio * 100, 2):g}%".replace('.', ',')
    except:
        return "0%"

if archivos_pdf:
    datos_extraidos = []
    
    for archivo in archivos_pdf:
        with pdfplumber.open(archivo) as pdf:
            texto = pdf.pages[0].extract_text(layout=True) 
            
            if not texto:
                texto = pdf.pages[0].extract_text()
            
            if texto:
                # 1. Fecha Abono
                fechas_encontradas = re.findall(r"\d{2}/\d{2}/\d{4}", texto)
                if fechas_encontradas:
                    fechas_ordenadas = sorted(fechas_encontradas, key=lambda f: f[6:] + f[3:5] + f[0:2])
                    fecha_abono = fechas_ordenadas[0]
                else:
                    fecha_abono = "No encontrada"

                # 2. Empresa
                empresa = buscar_dato([r"Valor:\s*(.+?)(?=\s{2,}|$)", r"REALTY INCOME.*|VIDRALA.*"], texto, "Desconocida")
                empresa = empresa.split("   ")[0].strip()

                # 3. Concepto
                concepto = f"DIVIDENDO ({empresa})"

                # 4. Datos Económicos y Títulos
                importe_titulo = buscar_dato([r"Importe por t[íi]tulo\s*:\s*([\d,]+)", r"Importe por t[íi]tulo\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe por t[íi]tulo"], texto)
                titulos = buscar_dato([r"N[úu]mero de t[íi]tulos\s*:\s*(\d+)", r"(\d+)\s+N[úu]mero de t[íi]tulos", r"N[úu]mero de t[íi]tulos.*?(\d+)"], texto, "0")
                bruto = buscar_dato([r"Importe total bruto\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe total bruto"], texto)
                ret_origen = buscar_dato([r"Retenci[óo]n en origen\s*:\s*([\d,]+)", r"Retenci[óo]n en origen\s*([\d,]+)", r"([\d,]+)\s*€\s*Retenci[óo]n en origen"], texto)
                ret_destino = buscar_dato([r"Retenci[óo]n en destino\s*:\s*([\d,]+)", r"Retenci[óo]n\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*:\s*Retenci[óo]n"], texto)
                neto = buscar_dato([r"Importe total neto\s*:\s*([\d,]+)", r"([\d,]+)\s*€\s*Importe total neto"], texto)

                # 5. Porcentajes de Retención (Ahora exactos por país)
                pct_origen = calcular_porcentaje(ret_origen, bruto)
                pct_destino = calcular_porcentaje(ret_destino, bruto)

                # 6. Cuentas
                cuenta_abono = buscar_dato([r"(1465\s*0100\s*93\s*\d{10})", r"(1465\s*010093\s*\d{10})"], texto, "N/A")
                cuenta_valores = buscar_dato([r"(91\s*\d{10})", r"(1465\s*0100\s*91\s*\d{10})"], texto, "0")

                # ==========================================
                # ORDENACIÓN DE COLUMNAS EXACTA
                # ==========================================
                datos_extraidos.append({
                    "Fecha Abono": fecha_abono,
                    "Concepto": concepto,
                    "Importe Neto (€)": neto,
                    "Retención en origen (€)": ret_origen,
                    "% Retención en origen": pct_origen,
                    "Retención en destino (€)": ret_destino,
                    "% Retención en destino": pct_destino,
                    "Importe Bruto (€)": bruto,
                    "Empresa": empresa,
                    "Cuenta de Valores": cuenta_valores,
                    "Número de títulos": titulos,
                    "Importe por título (€)": importe_titulo,
                    "Cuenta Abono": cuenta_abono
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
