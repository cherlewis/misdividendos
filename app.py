import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="Debugger de ING", layout="wide")

st.title("🐞 Modo Rayos X: Debugger de Compra 2022")
st.write("Sube el PDF rebelde de la **Compra de 2022** para ver cómo la máquina lee los números realmente.")

archivo = st.file_uploader("Sube SOLO tu PDF de Compra aquí", type=["pdf"])

if archivo:
    with pdfplumber.open(archivo) as pdf:
        texto_layout = pdf.pages[0].extract_text(layout=True) or ""
        texto_normal = pdf.pages[0].extract_text() or ""
        
        texto_limpio = re.sub(r'\s+', ' ', texto_layout + " " + texto_normal)
        
    st.subheader("1. El texto 'aplastado' que lee la máquina:")
    st.code(texto_limpio, language="text")
    
    st.markdown("---")
    st.subheader("2. Búsqueda de la Operación")
    
    patron_bloque = r'(Compra|Venta)(.*?)(Detalle de la orden|Cuenta de cargo|Podrá solicitar)'
    match_op = re.search(patron_bloque, texto_limpio, re.IGNORECASE)
    
    if match_op:
        st.success("✅ ¡El bloque entre 'Compra' y 'Detalle de la orden' ha sido encontrado!")
        zona_numeros = match_op.group(2)
        st.write("**Texto atrapado en ese bloque:**")
        st.code(zona_numeros, language="text")
        
        # PRUEBA A: Usando delimitadores estrictos (El código que fallaba)
        importes_estrictos = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', zona_numeros)
        st.write("🔴 **Intento A (Estricto - Fallaba):**", importes_estrictos)
        
        # PRUEBA B: Sin delimitadores (Ignorando si está pegado a una 'X' u otra letra)
        importes_flexibles = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', zona_numeros)
        st.write("🟢 **Intento B (Flexible - Solución):**", importes_flexibles)
        
        if importes_flexibles:
            st.info(f"El Importe Total capturado con el Intento B es: **{importes_flexibles[-1]}**")
    else:
        st.error("❌ No se ha encontrado el bloque. El problema es otro.")
        # Buscamos en todo el texto por si acaso
        todos_los_numeros = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto_limpio)
        st.write("**Números encontrados en todo el documento:**", todos_los_numeros)





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
                        
                        # 1. Encontrar Tipo de Operación y los números
                        tipo_op = "Desconocido"
                        importe_total = "0,00"
                        titulos = "0"
                        
                        match_tipo = re.search(r'\b(Compra|Venta)\b', texto_limpio, re.IGNORECASE)
                        if match_tipo:
                            tipo_op = match_tipo.group(1).capitalize()
                            idx = match_tipo.end()
                            
                            # Tomamos los siguientes 300 caracteres justo después de la palabra "Compra" o "Venta"
                            zona_cruda = texto_limpio[idx:idx+300]
                            
                            # Cortamos la lectura en cuanto aparezca un IBAN, una fecha, o palabras clave
                            zona_numeros = re.split(r'(?:ES\d{10}|\b\d{2}/\d{2}/\d{4}\b|Cuenta|Detalle|Limitada)', zona_cruda, flags=re.IGNORECASE)[0]
                            
                            # Extraemos la secuencia limpia de precios
                            importes = re.findall(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', zona_numeros)
                            
                            if len(importes) >= 2:
                                precio_ud = euro_a_numero(importes[0])
                                efectivo = euro_a_numero(importes[1])
                                importe_total = importes[-1]
                                
                                # Tu cálculo matemático infalible de títulos (Efectivo / Precio)
                                if precio_ud > 0:
                                    titulos = str(int(round(efectivo / precio_ud)))

                        # 2. Encontrar ISIN (Ignorando las 'XXX' de los PDFs antiguos)
                        isins = re.findall(r'\b[A-Z]{2}[A-Z0-9]{10}\b', texto_limpio)
                        isin = "Desconocido"
                        for i in isins:
                            if "XXX" not in i:
                                isin = i
                                break
                        
                        # 3. Encontrar Fecha
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
