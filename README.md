<div align="center">
<h1>Asistente Visual – Prototipo de Asistencia por Visión</h1>
<p>Detección de objetos, obstáculos, lectura de texto y navegación en tiempo real para apoyo a personas con discapacidad visual.</p>
</div>

---

## 🧱 Arquitectura General

| Capa | Componentes | Descripción |
|------|-------------|-------------|
| Backend (Flask) | `Servidor.py`, `helpers.py` | Endpoints de voz, objetos, obstáculos, lectura, distancia y navegación. Helpers centralizan OpenAI, TTS, prompts y archivos. |
| Scripts externos | `Deteccion_Objetos.py`, `Deteccion_Obstaculos.py`, `Distancia.py`, `Lectura_texto.py` | Procesos separados (subprocess) para detección y OCR. Modularizados con `main()`. |
| Modelo | `Modelo/yolov8n.pt` | YOLOv8 nano (rapidez sobre precisión). |
| Frontend | `index.html`, JS en `static/js` (`app.js`, `camara.js`, `mode_navegacion.js`, `comandos.js`) | Voz, cámara, navegación unificada, overlay canvas, vibración háptica. |
| Utilidades | `static/js/comandos.js`, `cleanup_outputs.py` | Palabras clave → acción y limpieza de salidas. |

### Flujo Resumido
1. Usuario habla → Reconocimiento (webkit) → `/procesar_audio` clasifica o responde.
2. Para comandos de captura: se toma snapshot (`camara.js`) → endpoint específico.
3. Para navegación: el cliente envía frames periódicos (pull) → `/navegacion_frame` → JSON compacto → overlay dibujado.
4. OpenAI genera descripciones/lecturas → gTTS sintetiza → audio reproducido.

---

## 📁 Estructura de Carpetas (relevante)
```
Servidor.py
helpers.py
cleanup_outputs.py
Modelo/yolov8n.pt
static/
  js/
    app.js
    camara.js
    mode_navegacion.js
    comandos.js
  css/estilos.css
templates/
  index.html
objetos_detectados/
obstaculos_detectados/
imagen_texto/
distancia_pasos/
procesar_imagen/capturas/
```

---

## 🚀 Instalación Rápida
1. Crear entorno virtual (recomendado).
2. Instalar dependencias:
	 ```bash
	 pip install -r requirements.txt
	 ```
3. Exportar tu clave de OpenAI (Windows PowerShell):
	 ```powershell
	 $env:OPENAI_API_KEY="TU_CLAVE"
	 ```
4. Ejecutar servidor:
	 ```bash
	 python Servidor.py
	 ```
5. Abrir en navegador: http://localhost:5000/

---

## 🧠 Endpoints Principales
| Endpoint | Método | Propósito | Entrada | Salida resumida |
|----------|--------|-----------|---------|------------------|
| `/procesar_audio` | POST | Clasifica comando o responde texto | `{texto}` | `{accion}` o `{audio_url}` |
| `/procesar_objetos` | POST (multipart) | Detección de objetos | `imagen` | `mensaje, objetos[], audio_url` |
| `/procesar_obstaculos` | POST (multipart) | Obstáculos dentro camino | `imagen` | `mensaje, obstaculos[], audio_url` |
| `/procesar_lectura_texto` | POST (multipart) | OCR con resumen | `imagen` | `mensaje, texto[], audio_url` |
| `/procesar_distancia_pasos` | POST (multipart) | Estimación distancia/pasos | `imagen` | `mensaje, texto[], audio_url` |
| `/navegacion_frame` | POST (JSON) | Detección continua | `{frame, conf?, iou?, imgsz?, compact?, poly_id?}` | Formato compacto o extendido |

### Formato Navegación Compacto (`compact:true`)
```json
{
	"d": [
		[x1,y1,x2,y2,label,en_camino,conf,base_x,base_y,dist_cm,pasos],
		...
	],
	"t": 5,       // total detecciones
	"ec": 2,      // en_camino
	"c": 0.25,    // conf
	"i": 0.45,    // iou
	"g": 640,     // imgsz
	"ms": 87,     // inference ms
	"pid": "640x480-216", // id polígono
	"p": [[x,y], ...]      // sólo si cambió el polígono
}
```

Campos añadidos (extendido recientemente):
- dist_cm: distancia estimada (cm) si la clase tiene ancho real conocido.
- pasos: distancia en pasos redondeada (LONGITUD_PASO=53cm). Rango de interés 1–5 para vibración.

### Ventajas del modo compacto
- Menos ancho de banda y GC.
- Reutilización de polígono (cache por `poly_id`).
- Fácil de reconstruir a objetos ricos en cliente.

---

## 🎥 Modo Navegación (Detalles)
Integrado en la misma página (`index.html`) a través de `mode_navegacion.js` (la página `navegacion.html` fue eliminada).

Proceso (`mode_navegacion.js`):
1. Captura frame → JPEG base64 (calidad adaptativa 0.55–0.85).
2. Intervalo dinámico según latencia de inferencia (120–600 ms).
3. Smoothing ALPHA=0.4 por etiqueta para reducir jitter.
4. Overlay: polígono cacheado (trapecio del camino) + cajas + puntos base + texto de obstáculos en trayectoria.
5. Limpieza completa al detener (abort fetch + remove overlay + parar tracks de la cámara).

Mejoras recientes:
- JSON compacto con claves abreviadas y cache de polígono (`poly_id`).
- Eliminado panel de métricas/indicadores NAV.
- Control exclusivo por voz (“modo navegación” / “detener navegación”).
- Cálculo opcional de distancia y pasos (bottle, chair, table) para vibración de proximidad.

Parámetros ajustables:
| Parámetro | Ubicación | Efecto |
|-----------|----------|--------|
| `INTERVALO_MS` | mode_navegacion.js | Intervalo base de envío |
| `conf` / `iou` | POST body | Filtro de detecciones |
| `imgsz` | POST body | Resolución inferencia YOLO |
| `calidad` | mode_navegacion.js | Calidad JPEG adaptativa |

Perfiles sugeridos:
- Dispositivo lento: `conf=0.3`, `iou=0.5`, `imgsz=512`.
- Máxima precisión ligera: `conf=0.15`, `imgsz=640`.
- Ahorro datos: `compact:true`, calidad mínima 0.55.

Comandos de voz clave:
- “modo navegación” → inicia envío de frames.
- “detener navegación” → detiene y desmonta overlay.

---

## 🔁 Scripts Externos
Cada script se puede ejecutar manualmente:
```bash
python Deteccion_Objetos.py ruta_imagen.jpg
python Deteccion_Obstaculos.py ruta_imagen.jpg
python Distancia.py ruta_imagen.jpg salida.txt
python Lectura_texto.py ruta_imagen.jpg salida.txt
```
Todos generan archivos `detectado_*.txt` y/o imágenes anotadas en sus carpetas.

### 🧹 Limpieza de salidas (`cleanup_outputs.py`)
Evita crecimiento indefinido de carpetas de resultados eliminando archivos con antigüedad mayor a X días.

Carpetas cubiertas:
```
objetos_detectados
obstaculos_detectados
imagen_texto
distancia_pasos
procesar_imagen/capturas
procesar_audio (si existe)
```

Uso:
```bash
python cleanup_outputs.py           # Mantiene 3 días (por defecto)
python cleanup_outputs.py --days 2  # Cambiar días
python cleanup_outputs.py --dry-run # Mostrar sin borrar
python cleanup_outputs.py --yes     # Evitar confirmación
```

---

## 🧩 Helpers Destacados (`helpers.py`)
| Función | Propósito |
|---------|-----------|
| `openai_answer` | Abstracción de Chat Completions |
| `synth_audio` | gTTS → MP3 reutilizable |
| `save_log` | Guarda instrucción y respuesta |
| `run_python` | Ejecuta script externo |
| `read_txt_lines` | Lee resultados de detección |
| `prompt_*` | Prompts consistentes para cada caso |

---

## ♿ Accesibilidad
- Botones con `aria-label`.
- Estados con `role="status"` y `aria-live="polite"`.
- Micrófono con `aria-pressed` dinámico.
- Feedback háptico configurable (tres intensidades).

### 🔔 Sistema de vibraciones
`app.js` expone API global `window.vibracionControles`:
```js
vibracionControles.cambiarNivel(vibracionControles.niveles.SUAVE);
vibracionControles.getNivelActual();
vibracionControles.probar();
```
Eventos diferenciados: envío, recepción, error, botón micrófono, listo.

#### Vibración continua por proximidad (modo navegación)
Mientras haya al menos un obstáculo en_camino con pasos entre 1 y 5 se genera vibración periódica escalonada:
- Pasos 5 → vibración leve y menos frecuente
- Pasos 1 → vibración más intensa y frecuente

Patrones base (antes de factor por nivel SUAVE/MEDIO/FUERTE):
| Pasos | Patrón | Intervalo (ms) |
|-------|--------|----------------|
| 5 | 80 | 1600 |
| 4 | [100,70,100] | 1200 |
| 3 | [140,80,140] | 900 |
| 2 | [180,90,180] | 650 |
| 1 | [260,120,260] | 450 |

Factor por nivel (SUAVE=0.9x, MEDIO=1.0x, FUERTE=1.15x) aplicado a cada duración del patrón.

API adicional:
```js
navigationMode.toggleProximityVibration(false); // desactivar temporalmente
navigationMode.proximityTest(3);                // probar patrón pasos=3
```

Clases con distancia/pasos actualmente: bottle, chair, table. Añadir más editando ANCHOS_REALES en `Servidor.py`.

---

## 🔒 Consideraciones de Seguridad (pendientes)
- No hay autenticación (prototipo local).
- Subprocess podría validarse con listas blancas.
- Archivos subidos no se validan por tipo MIME real (mejorable).

---

## 📊 Mejoras Realizadas (Resumen)
- Cliente OpenAI global (menos latencia TLS).
- Decodificación `cv2.imdecode` en navegación (más rápido que PIL→NumPy).
- JSON compacto + cache de polígono.
- Modularización JS y eliminación de duplicados.
- Refactor scripts y backend sin romper contratos.
- Accesibilidad básica añadida.
- Unificación de navegación (eliminados archivos legacy `navegacion.html` / `navegacion.js`).
- Eliminado panel de métricas e indicadores NAV.
- Sistema de vibración central configurado.
- Script de limpieza de salidas incorporado.

---

## 🛣️ Roadmap Sugerido
1. Integrar detección directa (eliminar subprocess) para menor latencia.
2. Endpoint `/health` + métricas agregadas.
3. Dockerfile para despliegue reproducible.
4. Notificación háptica/audio para NUEVOS obstáculos detectados.
5. Modo offline parcial (detección + TTS local).
6. Script benchmark (FPS, latencia media, p95).
7. Tests automatizados con mocks OpenAI/gTTS.
8. Cache de respuestas para no repetir audios similares.

---

## 🧪 Prueba Rápida Manual (ejemplos)
1. Levantar servidor.
2. Ir a `/` y decir: “describe los objetos”.
3. Decir: “modo navegación”.
4. Ver overlay (cajas, polígono) y ajustes dinámicos.
5. Decir: “detener navegación”.
6. Probar: “obstáculos”, “leer texto”, “distancia”.

---

## ✅ Estado Actual
El prototipo está estable, modular y listo para iteraciones de optimización (el cuello principal ahora es la inferencia YOLO + subprocess externos).

---

## © Notas
Uso educativo / prototipo. Ajustar claves y seguridad antes de despliegues productivos.

---

