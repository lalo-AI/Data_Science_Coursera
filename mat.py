import streamlit as st
import requests
import base64
import pyaudio
import numpy as np
from gtts import gTTS
import io
from datetime import datetime
import openpyxl

# Configuración de la API de ChatGPT
api_url = "https://api.openai.com/v1/chat/completions"
api_key = "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"  # Reemplaza con tu clave de API de OpenAI

# Configuración de PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=8192)

# Configuración de la sesión de Streamlit
st.title("Grabación y Transcripción de Audio con ChatGPT")

def transcribe_audio(audio_data):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": audio_data},
        ],
         "model": "text-davinci-003",
    }

    response_json = {}  # Inicializar la variable fuera del bloque try

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()  # Esto lanzará una excepción si la solicitud no fue exitosa
        response_json = response.json()
        query = response_json["choices"][0]["message"]["content"]
        return query
    except requests.exceptions.HTTPError as errh:
        print(f"Error HTTP: {errh}")
        return ""
    except requests.exceptions.ConnectionError as errc:
        print(f"Error de conexión: {errc}")
        return ""
    except requests.exceptions.Timeout as errt:
        print(f"Error de tiempo de espera: {errt}")
        return ""
    except requests.exceptions.RequestException as err:
        print(f"Error de solicitud: {err}")
        print(f"Respuesta JSON completa: {response_json}")
        return ""

def create_excel(resumen_text, accion_list):
    # Función para crear un archivo Excel y escribir los datos
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Minuta'

    if resumen_text:
        ws.append(['Resumen'])
        ws.append([resumen_text])

    if accion_list:
        ws.append(['ID', 'Acción', 'Responsable', 'Fecha'])
        for idx, accion in enumerate(accion_list, start=1):
            ws.append([idx, accion['accion'], accion['responsable'], accion['fecha']])

    wb.save('minuta.xlsx')

# Botón para iniciar la grabación de la minuta
if st.button("Minuta"):
    st.session_state.recording = True
    st.session_state.resumen_audio = []

    while st.session_state.recording:
        st.write("Esperando comandos: Resumen o Acciones...")
        audio_chunk = stream.read(8192)
        st.session_state.resumen_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

        if "resumen" in transcribe_audio(np.concatenate(st.session_state.resumen_audio).tolist()).lower():
            st.write("Comenzando el reconocimiento de voz para resumen. Di 'done' para finalizar.")
            st.session_state.resumen_audio = []

            while True:
                audio_chunk = stream.read(8192)
                st.session_state.resumen_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                if "done" in transcribe_audio(np.concatenate(st.session_state.resumen_audio).tolist()).lower():
                    resumen_text = transcribe_audio(np.concatenate(st.session_state.resumen_audio[:-1]))
                    create_excel(resumen_text, None)
                    st.session_state.recording = False
                    break

        elif "acciones" in transcribe_audio(np.concatenate(st.session_state.resumen_audio).tolist()).lower():
            st.write("Comenzando el reconocimiento de voz para acciones. Di 'done' para finalizar cada acción.")
            st.session_state.resumen_audio = []
            accion_list = []

            while True:
                # Grabar la acción
                st.write("Por favor, di la acción. Di 'done' para finalizar.")
                accion_audio = []
                while True:
                    audio_chunk = stream.read(8192)
                    accion_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    if "done" in transcribe_audio(np.concatenate(accion_audio).tolist()).lower():
                        break

                # Grabar el responsable
                st.write("Ahora, di el responsable. Di 'done' para finalizar.")
                responsable_audio = []
                while True:
                    audio_chunk = stream.read(8192)
                    responsable_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    if "done" in transcribe_audio(np.concatenate(responsable_audio)).lower():
                        break

                # Grabar la fecha
                st.write("Finalmente, di la fecha en formato DD/MM/AAAA. Di 'done' para finalizar.")
                fecha_audio = []
                while True:
                    audio_chunk = stream.read(8192)
                    fecha_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    if "done" in transcribe_audio(np.concatenate(fecha_audio).tolist()).lower():
                        break

                # Convertir la fecha a un formato de fecha de Excel
                fecha_excel = datetime.now().strftime("%Y-%m-%d")
                try:
                    fecha_excel = datetime.strptime(transcribe_audio(np.concatenate(fecha_audio[:-1])), "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    pass

                accion_list.append({
                    'accion': transcribe_audio(np.concatenate(accion_audio[:-1])),
                    'responsable': transcribe_audio(np.concatenate(responsable_audio[:-1])),
                    'fecha': fecha_excel
                })

                st.write("¿Listo para la siguiente acción? Di 'listo' o 'fin' para finalizar.")

                siguiente_audio = []
                while True:
                    audio_chunk = stream.read(8192)
                    siguiente_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    if "fin" in transcribe_audio(np.concatenate(siguiente_audio).tolist()).lower():
                        break

                    if "listo" in transcribe_audio(np.concatenate(siguiente_audio).tolist()).lower():
                        break

                if "fin" in transcribe_audio(np.concatenate(siguiente_audio).tolist()).lower():
                    break

            create_excel(None, accion_list)
            st.session_state.recording = False

# Cierre de la transmisión y PyAudio al cerrar
st.text("Cerrando la transmisión y PyAudio al cerrar la aplicación.")
stream.stop_stream()
stream.close()
p.terminate()
