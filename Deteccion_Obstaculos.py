from ultralytics import YOLO
import cv2
import logging
import sys
import os

logging.getLogger("ultralytics").setLevel(logging.ERROR)

def cargar_modelo():
    model_path = os.path.join(os.getcwd(), 'Modelo', 'yolov8n.pt')
    return YOLO(model_path)

def procesar_imagen(ruta_imagen: str, model: YOLO):
    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        print(f"Error: No se pudo cargar la imagen {ruta_imagen}")
        sys.exit(1)
    height, width = imagen.shape[:2]
    camino_x1, camino_y1 = int(width * 0.2), int(height * 0.4)
    camino_x2, camino_y2 = int(width * 0.8), height
    cv2.rectangle(imagen, (camino_x1, camino_y1), (camino_x2, camino_y2), (0, 255, 0), 2)
    results = model(imagen, verbose=False)
    obstaculos_detectados = set()
    det = results[0]
    names_map = det.names
    for box in det.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        class_id = int(box.cls[0]) if hasattr(box, 'cls') else None
        label = names_map[class_id] if class_id is not None else 'Objeto'
        if camino_x1 < x1 < camino_x2 and camino_y1 < y2 < camino_y2:
            color = (0, 0, 255)
            obstaculos_detectados.add(label)
            cv2.putText(imagen, "Obstáculo detectado!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            color = (255, 0, 0)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), color, 2)
        cv2.putText(imagen, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return imagen, obstaculos_detectados

def guardar_resultados(ruta_imagen: str, imagen, obstaculos_detectados):
    carpeta_salida = os.path.join(os.getcwd(), 'obstaculos_detectados')
    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_archivo = os.path.basename(ruta_imagen)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    ruta_txt = os.path.join(carpeta_salida, f"detectado_{nombre_base}.txt")
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        for obj in obstaculos_detectados:
            f.write(f"{obj}\n")
    ruta_salida = os.path.join(carpeta_salida, f"detectado_{nombre_archivo}")
    cv2.imwrite(ruta_salida, imagen)
    print(f"Imagen procesada y guardada en: {ruta_salida}")
    print(f"Lista de obstáculos guardada en: {ruta_txt}")

def main():
    if len(sys.argv) < 2:
        print("Error: Debes proporcionar la ruta de la imagen como argumento.")
        sys.exit(1)
    ruta_imagen = sys.argv[1]
    model = cargar_modelo()
    imagen, obstaculos = procesar_imagen(ruta_imagen, model)
    guardar_resultados(ruta_imagen, imagen, obstaculos)

if __name__ == '__main__':
    main()