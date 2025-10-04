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
    results = model(imagen, verbose=False)
    objetos_detectados = set()
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)
        objetos_detectados.add(label)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(imagen, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    return imagen, objetos_detectados

def guardar_resultados(ruta_imagen: str, imagen, objetos_detectados):
    carpeta_salida = os.path.join(os.getcwd(), 'objetos_detectados')
    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_archivo = os.path.basename(ruta_imagen)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    ruta_txt = os.path.join(carpeta_salida, f"detectado_{nombre_base}.txt")
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        for obj in objetos_detectados:
            f.write(f"{obj}\n")
    ruta_salida = os.path.join(carpeta_salida, f"detectado_{nombre_archivo}")
    cv2.imwrite(ruta_salida, imagen)
    print(f"Imagen procesada y guardada en: {ruta_salida}")
    print(f"Lista de objetos guardada en: {ruta_txt}")

def main():
    if len(sys.argv) < 2:
        print("Error: Debes proporcionar la ruta de la imagen como argumento.")
        sys.exit(1)
    ruta_imagen = sys.argv[1]
    model = cargar_modelo()
    imagen, objetos = procesar_imagen(ruta_imagen, model)
    guardar_resultados(ruta_imagen, imagen, objetos)

if __name__ == '__main__':
    main()