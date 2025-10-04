from ultralytics import YOLO
import cv2
import logging
import sys
import os

ANCHOS_REALES = {"bottle": 7, "chair": 45, "table": 80}
DISTANCIA_FOCAL = 800
LONGITUD_PASO = 53

logging.getLogger("ultralytics").setLevel(logging.ERROR)

def cargar_modelo():
    model_path = os.path.join(os.getcwd(), 'Modelo', 'yolov8n.pt')
    return YOLO(model_path)

def calcular_distancias(imge, model: YOLO):
    height, width = imge.shape[:2]
    punto_camara = (width // 2, height)
    results = model(imge)
    resultados_txt = []
    det = results[0]
    names_map = det.names
    for box in det.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        class_id = int(box.cls[0])
        label = names_map[class_id] if class_id in names_map else str(class_id)
        ancho_px = x2 - x1
        centro_objeto = ((x1 + x2) // 2, (y1 + y2) // 2)
        if label in ANCHOS_REALES and ancho_px != 0:
            distancia_cm = (ANCHOS_REALES[label] * DISTANCIA_FOCAL) / ancho_px
            pasos = round(distancia_cm / LONGITUD_PASO)
            resultados_txt.append(f"{label},{distancia_cm:.1f},{pasos}")
            cv2.rectangle(imge, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(imge, f"{label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.line(imge, punto_camara, centro_objeto, (0, 255, 0), 2)
            texto_distancia = f"{distancia_cm:.1f}cm | {pasos} pasos"
            cv2.putText(imge, texto_distancia, (centro_objeto[0] + 30, centro_objeto[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.rectangle(imge, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(imge, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return resultados_txt, imge

def guardar_resultados(ruta_txt: str, resultados_txt, imge):
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        for linea in resultados_txt:
            f.write(linea + '\n')
    nombre_img = os.path.splitext(os.path.basename(ruta_txt))[0] + '.jpg'
    ruta_img_resultado = os.path.join(os.path.dirname(ruta_txt), nombre_img)
    cv2.imwrite(ruta_img_resultado, imge)

def main():
    if len(sys.argv) < 3:
        print("Uso: python Distancia.py <ruta_imagen> <ruta_txt>")
        sys.exit(1)
    ruta_imagen = sys.argv[1]
    ruta_txt = sys.argv[2]
    imge = cv2.imread(ruta_imagen)
    if imge is None:
        print(f"No se pudo cargar la imagen: {ruta_imagen}")
        sys.exit(1)
    model = cargar_modelo()
    resultados_txt, imge_proc = calcular_distancias(imge, model)
    guardar_resultados(ruta_txt, resultados_txt, imge_proc)

if __name__ == '__main__':
    main()