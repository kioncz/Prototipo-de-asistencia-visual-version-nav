"""Funciones auxiliares reutilizables para el backend.
No modifican el comportamiento externo, solo reducen duplicación.
"""
from __future__ import annotations
import os
import time
import subprocess
from typing import List, Tuple, Optional
from gtts import gTTS
from openai import OpenAI

# --- Paths base ---
DIR_INSTRUCCIONES = 'instrucciones_enviadas'
DIR_RESPUESTAS = 'respuestas_devuelta'
DIR_AUDIO = os.path.join('static', 'audio')

# --- Utilidades de archivos / carpetas ---

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def timestamp_now() -> str:
    return time.strftime('%Y%m%d_%H%M%S')

def save_upload(file_storage, subdir: str) -> Tuple[str, str]:
    """Guarda un archivo subido en subdir/capturas y devuelve (ruta_archivo, nombre_base_sin_ext)."""
    ensure_dir(subdir)
    nombre = f"captura_{timestamp_now()}.jpg"
    ruta = os.path.join(subdir, nombre)
    file_storage.save(ruta)
    base = os.path.splitext(nombre)[0]
    return ruta, base

# --- Subprocess / scripts externos ---

def run_python(script: str, *args: str) -> Tuple[int, str, str]:
    """Ejecuta un script Python con argumentos, devuelve (returncode, stdout, stderr)."""
    import sys
    cmd = [sys.executable, script, *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

# --- Lectura de resultados ---

def read_txt_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip()]

# --- OpenAI / Respuestas ---

def openai_answer(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 100) -> str:
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens
    )
    return completion.choices[0].message.content.strip()

# --- Logs / Audio ---

def save_log(instruccion: str, respuesta: str) -> None:
    ensure_dir(DIR_INSTRUCCIONES)
    ensure_dir(DIR_RESPUESTAS)
    with open(os.path.join(DIR_INSTRUCCIONES, 'instruccion.txt'), 'w', encoding='utf-8') as f:
        f.write(instruccion + '\n')
    with open(os.path.join(DIR_RESPUESTAS, 'respuesta.txt'), 'w', encoding='utf-8') as f:
        f.write(respuesta + '\n')


def synth_audio(texto: str, lang: str = 'es') -> str:
    ensure_dir(DIR_AUDIO)
    ruta = os.path.join(DIR_AUDIO, 'respuesta.mp3')
    tts = gTTS(text=texto, lang=lang)
    tts.save(ruta)
    return '/static/audio/respuesta.mp3'

# --- Prompt builders ---

def prompt_objetos(lista: List[str]) -> str:
    if lista:
        return ("Describe de manera clara y accesible para una persona con discapacidad visual la siguiente escena. "
                "No utilices negritas, asteriscos ni formato markdown, solo texto plano sencillo: "
                f"Se detectaron los siguientes objetos: {', '.join(lista)}.")
    return "No se detectaron objetos en la imagen."


def prompt_obstaculos(lista: List[str]) -> str:
    if lista:
        return ("Describe de manera clara y accesible para una persona con discapacidad visual la siguiente escena. "
                "No utilices negritas, asteriscos ni formato markdown, solo texto plano sencillo: "
                f"Se detectaron los siguientes obstáculos en el camino: {', '.join(lista)}. "
                "Enfócate en advertir sobre los obstáculos y su importancia para la navegación segura.")
    return "No se detectaron obstáculos en el camino."


def prompt_texto(lista: List[str]) -> str:
    if lista:
        return ("Lee y describe de manera clara y accesible para una persona con discapacidad visual el siguiente texto extraído de una imagen. "
                "No utilices negritas, asteriscos ni formato markdown, solo texto plano sencillo: "
                f"{' '.join(lista)}.")
    return "No se detectó texto en la imagen."


def prompt_distancia(lista: List[str]) -> str:
    if lista:
        return ("Indica de forma clara y accesible para una persona con discapacidad visual el nombre del objeto u obstáculo detectado, "
                "seguido únicamente de la distancia estimada en centímetros y el número de pasos. No incluyas contexto adicional ni repitas información, "
                "solo el nombre, la distancia y los pasos de forma sencilla y directa: " + ' '.join(lista) + '.')
    return "No se detectó distancia ni pasos en la imagen."

# --- Simple helper para historial voz a texto ---

def append_voz_a_texto(texto: str) -> None:
    ensure_dir('procesar_audio')
    with open(os.path.join('procesar_audio', 'voz_a_texto.txt'), 'a', encoding='utf-8') as f:
        f.write(texto + '\n')
