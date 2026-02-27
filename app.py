import streamlit as st

# Esto crea el título de tu página web
st.title("🚀 Mi Primera App en Python")

# Esto escribe texto normal
st.write("¡Hola Mundo! Si estás leyendo esto, Python y Streamlit están funcionando perfectamente en internet.")

# Esto crea un botón para subir archivos mágicamente
archivo = st.file_uploader("Sube un archivo PDF de prueba aquí")

if archivo is not None:
    # Si el usuario sube algo, mostramos un mensaje de éxito
    st.success("¡Archivo subido correctamente! (Aún no procesamos el PDF, pero la interfaz ya funciona)")
