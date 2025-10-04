import cv2
from ultralytics import YOLO
import logging
import os

def modo_navegacion(fuente=0, modelo_relativo='Modelo/yolov8n.pt'):
    """Muestra en tiempo real detección de objetos y obstáculo en el camino.

    - No guarda imágenes ni txt.
    - Dibuja un rectángulo verde como "camino".
    - Si un objeto cae dentro del camino se pinta en rojo y se marca como obstáculo.
    - Presiona 'q' para salir.
    """
    logging.getLogger("ultralytics").setLevel(logging.ERROR)
    model_path = os.path.join(os.getcwd(), modelo_relativo)
    if not os.path.exists(model_path):
        print(f"No se encontró el modelo en: {model_path}")
        return
    model = YOLO(model_path)

    cap = cv2.VideoCapture(fuente)
    if not cap.isOpened():
        print("No se pudo abrir la cámara/fuente de video")
        return

    print("Modo navegación en vivo iniciado. Presiona 'q' para salir.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No se pudo leer frame de la cámara")
            break

        height, width = frame.shape[:2]
        camino_x1, camino_y1 = int(width * 0.2), int(height * 0.4)
        camino_x2, camino_y2 = int(width * 0.8), height
        cv2.rectangle(frame, (camino_x1, camino_y1), (camino_x2, camino_y2), (0, 255, 0), 2)

        results = model(frame, verbose=False)
        obstaculos = set()
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            class_id = int(box.cls[0]) if hasattr(box, 'cls') else None
            label = results[0].names[class_id] if class_id is not None else "Objeto"
            if camino_x1 < x1 < camino_x2 and camino_y1 < y2 < camino_y2:
                color = (0, 0, 255)
                obstaculos.add(label)
                cv2.putText(frame, "Obstaculo!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            else:
                color = (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if obstaculos:
            txt = ' | '.join(sorted(obstaculos))
            cv2.putText(frame, f"En camino: {txt}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

        cv2.imshow('Modo Navegacion', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    modo_navegacion()
