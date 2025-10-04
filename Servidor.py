from flask import Flask, render_template, request, jsonify
import os, sys, base64, io, time, shutil
from openai import OpenAI
from dotenv import load_dotenv
from ultralytics import YOLO
import cv2
import numpy as np

# Helpers centralizados
from helpers import (
    openai_answer,
    save_log,
    synth_audio,
    append_voz_a_texto,
    prompt_objetos,
    prompt_obstaculos,
    prompt_texto,
    prompt_distancia,
    read_txt_lines,
    run_python,
)

load_dotenv()
key = os.getenv("OPENAI_API_KEY")
openai_client = None  # Cliente global lazy para reducir latencia de creación repetida
app = Flask(__name__)

# ------------------ DISTANCIA / PASOS (reutilizado de Distancia.py) ------------------
# Anchos reales aproximados en centímetros (puedes ampliar este diccionario).
ANCHOS_REALES = {"bottle": 7, "chair": 45, "table": 80}
DISTANCIA_FOCAL = 800  # Focal aproximada usada para convertir tamaño en pixeles a distancia
LONGITUD_PASO = 53     # Longitud de paso estimada (cm) para convertir distancia a pasos

# ------------------ UTILIDADES NAVEGACION ------------------
def punto_en_poligono(px, py, vertices):
    inside = False
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        cond = ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-9) + x1)
        if cond:
            inside = not inside
    return inside

def construir_poligono_camino(w:int, h:int):
    top_y = int(h * 0.45)
    poly = [
        (int(w * 0.05), h - 1),
        (int(w * 0.25), top_y),
        (int(w * 0.75), top_y),
        (int(w * 0.95), h - 1)
    ]
    poly_id = f"{w}x{h}-{top_y}"
    return poly, poly_id

# Estado modelo navegación
modelo_navegacion = None


@app.route('/')
def interfaz():
    return render_template('index.html')


 # Ruta /navegacion eliminada (legacy) tras unificar navegación en index.html

@app.route('/procesar_audio', methods=['POST'])
def procesar_audio():
    """Procesa comandos de voz / texto y retorna acción o audio.
    Refactor: usa helpers para reducir latencia y duplicación.
    """
    global openai_client
    data = request.get_json(silent=True) or {}
    texto = data.get('texto', '').strip()
    if not texto:
        return jsonify({'error': 'No se recibió texto'}), 400

    # Clasificación rápida de comandos locales sin invocar OpenAI.
    if es_comando_captura_objetos(texto):
        return jsonify({'accion': 'captura_imagen'})
    if es_comando_captura_obstaculos(texto):
        return jsonify({'accion': 'captura_obstaculos'})
    if es_comando_lectura_texto(texto):
        return jsonify({'accion': 'lectura_texto'})
    if es_comando_distancia_pasos(texto):
        return jsonify({'accion': 'distancia_pasos'})
    if es_comando_modo_navegacion(texto):
        return jsonify({'accion': 'modo_navegacion'})
    if es_comando_detener_navegacion(texto):
        return jsonify({'accion': 'detener_navegacion'})

    # Reutilizar cliente para reducir overhead TLS / handshake
    if openai_client is None and key:
        openai_client = OpenAI(api_key=key)

    system_prompt = (
        "eres una inteligencia artificial especializada en asistencia visual para personas con discapacidad visual. "
        "Su función principal es interpretar y describir con precisión el entorno visual mediante procesamiento de imágenes y lenguaje natural. "
        "Limítate a este dominio. No uses formato markdown, solo texto plano."
    )

    try:
        # Si tenemos cliente global úsalo, si no fallback a helper (que crea uno temporal)
        if openai_client:
            completion = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": texto}
                ],
                max_tokens=100
            )
            respuesta = completion.choices[0].message.content.strip()
        else:
            respuesta = openai_answer(key, system_prompt, texto, max_tokens=100)
    except Exception as e:
        return jsonify({'error': f'Fallo OpenAI: {e}'}), 500

    # Registrar
    save_log(texto, respuesta)
    append_voz_a_texto(texto)
    # Audio
    audio_url = synth_audio(respuesta)
    return jsonify({'audio_url': audio_url})

@app.route('/procesar_objetos', methods=['POST'])
def procesar_objetos():
    global openai_client
    file = request.files.get('imagen')
    if not file:
        return jsonify({'error': 'Falta archivo imagen'}), 400
    carpeta_capturas = os.path.join(os.getcwd(), 'procesar_imagen', 'capturas')
    os.makedirs(carpeta_capturas, exist_ok=True)
    nombre_archivo = f"captura_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta_archivo = os.path.join(carpeta_capturas, nombre_archivo)
    file.save(ruta_archivo)
    # Ejecutar script detección
    rc, _, err = run_python('Deteccion_Objetos.py', ruta_archivo)
    if rc != 0:
        return jsonify({'error': 'Fallo script detección', 'detalle': err}), 500
    carpeta_objetos = os.path.join(os.getcwd(), 'objetos_detectados')
    ruta_txt = os.path.join(carpeta_objetos, f"detectado_{os.path.splitext(nombre_archivo)[0]}.txt")
    objetos = read_txt_lines(ruta_txt)
    prompt = prompt_objetos(objetos)
    system_prompt = "Eres una inteligencia artificial especializada en asistencia visual para personas con discapacidad visual. Describe la escena de forma clara, concisa y accesible."
    try:
        if openai_client is None and key:
            openai_client = OpenAI(api_key=key)
        if openai_client:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                max_tokens=100
            )
            respuesta = completion.choices[0].message.content.strip()
        else:
            respuesta = openai_answer(key, system_prompt, prompt, max_tokens=100)
    except Exception as e:
        return jsonify({'error': f'Fallo OpenAI: {e}'}), 500
    save_log(prompt, respuesta)
    audio_url = synth_audio(respuesta)
    return jsonify({'mensaje': respuesta, 'objetos': objetos, 'audio_url': audio_url})

@app.route('/procesar_obstaculos', methods=['POST'])
def procesar_obstaculos():
    global openai_client
    file = request.files.get('imagen')
    if not file:
        return jsonify({'error': 'Falta archivo imagen'}), 400
    carpeta_capturas = os.path.join(os.getcwd(), 'procesar_imagen', 'capturas')
    os.makedirs(carpeta_capturas, exist_ok=True)
    nombre_archivo = f"captura_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta_archivo = os.path.join(carpeta_capturas, nombre_archivo)
    file.save(ruta_archivo)
    rc, _, err = run_python('Deteccion_Obstaculos.py', ruta_archivo)
    if rc != 0:
        return jsonify({'error': 'Fallo script detección', 'detalle': err}), 500
    carpeta_obst = os.path.join(os.getcwd(), 'obstaculos_detectados')
    ruta_txt = os.path.join(carpeta_obst, f"detectado_{os.path.splitext(nombre_archivo)[0]}.txt")
    obstaculos = read_txt_lines(ruta_txt)
    prompt = prompt_obstaculos(obstaculos)
    system_prompt = "Eres una IA de asistencia visual. Describe obstáculos detectados con énfasis en seguridad, claro y conciso."
    try:
        if openai_client is None and key:
            openai_client = OpenAI(api_key=key)
        if openai_client:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                max_tokens=100
            )
            respuesta = completion.choices[0].message.content.strip()
        else:
            respuesta = openai_answer(key, system_prompt, prompt, max_tokens=100)
    except Exception as e:
        return jsonify({'error': f'Fallo OpenAI: {e}'}), 500
    save_log(prompt, respuesta)
    audio_url = synth_audio(respuesta)
    return jsonify({'mensaje': respuesta, 'obstaculos': obstaculos, 'audio_url': audio_url})

@app.route('/procesar_lectura_texto', methods=['POST'])
def procesar_lectura_texto():
    global openai_client
    file = request.files.get('imagen')
    if not file:
        return jsonify({'error': 'Falta archivo imagen'}), 400
    carpeta_capturas = os.path.join(os.getcwd(), 'procesar_imagen', 'capturas')
    os.makedirs(carpeta_capturas, exist_ok=True)
    nombre_archivo = f"captura_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta_archivo = os.path.join(carpeta_capturas, nombre_archivo)
    file.save(ruta_archivo)
    carpeta_texto = os.path.join(os.getcwd(), 'imagen_texto')
    os.makedirs(carpeta_texto, exist_ok=True)
    ruta_img_resultado = os.path.join(carpeta_texto, f"detectado_{os.path.splitext(nombre_archivo)[0]}.jpg")
    shutil.copy2(ruta_archivo, ruta_img_resultado)
    ruta_txt = os.path.join(carpeta_texto, f"detectado_{os.path.splitext(nombre_archivo)[0]}.txt")
    rc, _, err = run_python('Lectura_texto.py', ruta_img_resultado, ruta_txt)
    if rc != 0:
        return jsonify({'error': 'Fallo script OCR', 'detalle': err}), 500
    texto_lines = read_txt_lines(ruta_txt)
    prompt = prompt_texto(texto_lines)
    system_prompt = ("Eres un asistente para personas con discapacidad visual. Resume, corrige y complementa el texto extraído para que sea claro y útil. ")
    try:
        if openai_client is None and key:
            openai_client = OpenAI(api_key=key)
        if openai_client:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                max_tokens=200
            )
            respuesta = completion.choices[0].message.content.strip()
        else:
            respuesta = openai_answer(key, system_prompt, prompt, max_tokens=200)
    except Exception as e:
        return jsonify({'error': f'Fallo OpenAI: {e}'}), 500
    save_log(prompt, respuesta)
    audio_url = synth_audio(respuesta)
    return jsonify({'mensaje': respuesta, 'texto': texto_lines, 'audio_url': audio_url})

@app.route('/procesar_distancia_pasos', methods=['POST'])
def procesar_distancia_pasos():
    global openai_client
    file = request.files.get('imagen')
    if not file:
        return jsonify({'error': 'Falta archivo imagen'}), 400
    carpeta_capturas = os.path.join(os.getcwd(), 'procesar_imagen', 'capturas')
    os.makedirs(carpeta_capturas, exist_ok=True)
    nombre_archivo = f"captura_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    ruta_archivo = os.path.join(carpeta_capturas, nombre_archivo)
    file.save(ruta_archivo)
    carpeta_resultado = os.path.join(os.getcwd(), 'distancia_pasos')
    os.makedirs(carpeta_resultado, exist_ok=True)
    ruta_img_resultado = os.path.join(carpeta_resultado, f"detectado_{os.path.splitext(nombre_archivo)[0]}.jpg")
    shutil.copy2(ruta_archivo, ruta_img_resultado)
    ruta_txt = os.path.join(carpeta_resultado, f"detectado_{os.path.splitext(nombre_archivo)[0]}.txt")
    rc, _, err = run_python('Distancia.py', ruta_img_resultado, ruta_txt)
    if rc != 0:
        return jsonify({'error': 'Fallo script distancia', 'detalle': err}), 500
    texto_lines = read_txt_lines(ruta_txt)
    prompt = prompt_distancia(texto_lines)
    system_prompt = ("Eres un asistente para personas con discapacidad visual. Entrega únicamente nombre del objeto, distancia y pasos de forma clara.")
    try:
        if openai_client is None and key:
            openai_client = OpenAI(api_key=key)
        if openai_client:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                max_tokens=200
            )
            respuesta = completion.choices[0].message.content.strip()
        else:
            respuesta = openai_answer(key, system_prompt, prompt, max_tokens=200)
    except Exception as e:
        return jsonify({'error': f'Fallo OpenAI: {e}'}), 500
    save_log(prompt, respuesta)
    audio_url = synth_audio(respuesta)
    return jsonify({'mensaje': respuesta, 'texto': texto_lines, 'audio_url': audio_url})


# --- Palabras clave para comandos de captura de objetos ---
def es_comando_captura_objetos(texto):
    palabras_clave = [
        'describe', 'describeme', 'objetos', 'foto', 'captura', 'imagen', 'enfrente', 'ves',
        'detectar objeto', 'detectar objetos', 'qué ves', 'qué hay', 'muéstrame', 'mostrar', 'analiza', 'analizar'
    ]
    texto_minus = texto.lower()
    return any(palabra in texto_minus for palabra in palabras_clave)

# --- Palabras clave para comandos de captura de obstáculos ---
def es_comando_captura_obstaculos(texto):
    palabras_clave = [
        'obstáculo', 'obstaculo', 'obstáculos', 'obstaculos', 'peligro', 'camino', 'bloqueo', 'impedimento',
        'detecta obstáculo', 'detecta obstaculo', 'hay algo en el camino', 'bloqueado', 'impide', 'frente', 'adelante'
    ]
    texto_minus = texto.lower()
    return any(palabra in texto_minus for palabra in palabras_clave)

# --- Palabras clave para comandos de lectura de texto ---
def es_comando_lectura_texto(texto):
    palabras_clave = [
        'leer', 'lectura', 'texto', 'leeme', 'lee', 'texto en voz alta', 'leer texto',
        'qué dice', 'qué está escrito', 'palabras', 'contenido escrito', 'puedes leer', 'me puedes leer', 'qué pone', 'dime lo que dice'
    ]
    texto_minus = texto.lower()
    return any(palabra in texto_minus for palabra in palabras_clave)

# --- Palabras clave para comandos de distancia y pasos ---
def es_comando_distancia_pasos(texto):
    palabras_clave = [
        'cuántos pasos', 'cuantos pasos', 'qué tan lejos', 'a qué distancia', 'está lejos', 'está cerca', 'puedo llegar', 
        'me acerco', 'me alejo', 'cuánto camino', 'cuánto falta', 'cuánto tengo que caminar', 'cuánto me falta', 'está a muchos pasos', 'está a pocos pasos'
    ]
    texto_minus = texto.lower()
    return any(palabra in texto_minus for palabra in palabras_clave)

# --- Palabras clave para comandos de modo de navegación ---
def es_comando_modo_navegacion(texto):
    palabras_clave = [
        'modo deteccion', 'modo detección', 'modo navegacion', 'modo navegación', 'activar navegacion', 'activar deteccion'
    ]
    texto_minus = texto.lower()
    return any(p in texto_minus for p in palabras_clave)

def es_comando_detener_navegacion(texto):
    palabras_clave = [
        'detener navegacion', 'detener navegación', 'parar navegacion', 'parar navegación', 'salir navegacion', 'salir navegación'
    ]
    texto_minus = texto.lower()
    return any(p in texto_minus for p in palabras_clave)

@app.route('/navegacion_frame', methods=['POST'])
def navegacion_frame():
    """Recibe frame base64 y retorna detecciones (modo compacto opcional)."""
    global modelo_navegacion
    data = request.get_json(silent=True) or {}
    b64 = data.get('frame')
    if not b64:
        return jsonify({'error': 'no frame'}), 400
    conf = float(data.get('conf', 0.25))
    iou = float(data.get('iou', 0.45))
    imgsz = data.get('imgsz') or 640
    compact = bool(data.get('compact', False))
    client_poly_id = data.get('poly_id')
    if ',' in b64:
        b64 = b64.split(',', 1)[1]
    try:
        img_bytes = base64.b64decode(b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            return jsonify({'error': 'bad image decode'}), 400
        frame_np = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    except Exception as e:
        return jsonify({'error': f'bad image: {e}'}), 400
    if modelo_navegacion is None:
        try:
            modelo_navegacion = YOLO(os.path.join(os.getcwd(), 'Modelo', 'yolov8n.pt'))
        except Exception as e:
            return jsonify({'error': f'model load fail: {e}'}), 500
    import time as _t
    t0 = _t.time()
    try:
        results = modelo_navegacion(frame_np, verbose=False, conf=conf, iou=iou, imgsz=imgsz)
    except Exception as e:
        return jsonify({'error': f'inference fail: {e}'}), 500
    infer_ms = int((_t.time() - t0) * 1000)
    h, w = frame_np.shape[:2]
    poly, poly_id = construir_poligono_camino(w, h)
    enviar_poly = (client_poly_id != poly_id)
    detecciones = []
    detecciones_compact = [] if compact else None
    if results and len(results) > 0 and hasattr(results[0], 'boxes'):
        det = results[0]
        names_map = det.names
        for box in det.boxes:
            try:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0]) if hasattr(box, 'cls') else None
                label = names_map[class_id] if class_id is not None else 'Objeto'
                score = float(box.conf[0]) if hasattr(box, 'conf') else None
                base_x = int((x1 + x2) / 2)
                base_y = y2
                en_camino = punto_en_poligono(base_x, base_y, poly)

                # Calculo distancia y pasos si la etiqueta está en ANCHOS_REALES
                dist_cm = None
                pasos = None
                ancho_px = (x2 - x1)
                if label in ANCHOS_REALES and ancho_px > 0:
                    try:
                        dist_cm_val = (ANCHOS_REALES[label] * DISTANCIA_FOCAL) / float(ancho_px)
                        dist_cm = round(dist_cm_val, 1)
                        pasos_calc = dist_cm_val / LONGITUD_PASO
                        pasos = int(round(pasos_calc))
                        # Limitamos pasos a un rango razonable para evitar valores extremos
                        if pasos < 0 or pasos > 999: pasos = None
                    except Exception:
                        dist_cm = None
                        pasos = None
                if compact:
                    # Formato compacto extendido: + dist_cm, pasos (pueden ser None)
                    detecciones_compact.append([
                        x1, y1, x2, y2, label,
                        1 if en_camino else 0,
                        score,
                        base_x, base_y,
                        dist_cm, pasos
                    ])
                else:
                    detecciones.append({
                        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                        'label': label,
                        'en_camino': en_camino,
                        'confidencia': score,
                        'base_x': base_x,
                        'base_y': base_y,
                        'dist_cm': dist_cm,
                        'pasos': pasos
                    })
            except Exception:
                continue
    if compact:
        en_camino_count = sum(1 for d in detecciones_compact if d[5] == 1)
        resp = {
            'd': detecciones_compact,
            't': len(detecciones_compact),
            'ec': en_camino_count,
            'c': conf,
            'i': iou,
            'g': imgsz,
            'ms': infer_ms,
            'pid': poly_id
        }
        if enviar_poly:
            resp['p'] = poly
        return jsonify(resp)
    else:
        en_camino_count = sum(1 for d in detecciones if d['en_camino'])
        return jsonify({
            'detecciones': detecciones,
            'total': len(detecciones),
            'en_camino': en_camino_count,
            'conf': conf,
            'iou': iou,
            'imgsz': imgsz,
            'inference_ms': infer_ms,
            'camino_poly': poly if enviar_poly else None,
            'poly_id': poly_id
        })

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)