import cv2
import easyocr
import os
import sys
import numpy as np

def preparar_rutas(ruta_imagen: str, ruta_txt_arg: str | None):
    if ruta_txt_arg:
        ruta_txt = ruta_txt_arg
        ruta_img_resultado = ruta_imagen  # sobrescribe
    else:
        carpeta_destino = os.path.join(os.getcwd(), 'imagen_texto')
        os.makedirs(carpeta_destino, exist_ok=True)
        ruta_txt = os.path.join(carpeta_destino, 'texto_extraido.txt')
        ruta_img_resultado = os.path.join(carpeta_destino, 'resultado_texto.jpg')
    return ruta_txt, ruta_img_resultado

def ocr_imagen(img):
    reader = easyocr.Reader(['es'], gpu=False)
    return reader.readtext(img)

def dibujar_resultados(img, result):
    drawn = img.copy()
    for (bbox, text, conf) in result:
        pts = [tuple(map(int, point)) for point in bbox]
        cv2.polylines(drawn, [np.array(pts)], isClosed=True, color=(0,255,0), thickness=2)
    return drawn

def main():
    if len(sys.argv) < 2:
        print("Error: Debes proporcionar la ruta de la imagen como argumento.")
        sys.exit(1)
    ruta_imagen = sys.argv[1]
    ruta_txt_arg = sys.argv[2] if len(sys.argv) > 2 else None
    img = cv2.imread(ruta_imagen)
    if img is None:
        print("Error: No se pudo cargar la imagen.")
        sys.exit(1)
    ruta_txt, ruta_img_resultado = preparar_rutas(ruta_imagen, ruta_txt_arg)
    result = ocr_imagen(img)
    texto = ' '.join([r[1] for r in result])
    print("Texto reconocido:", texto)
    drawn = dibujar_resultados(img, result)
    cv2.imwrite(ruta_img_resultado, drawn)
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        f.write(texto)

if __name__ == '__main__':
    main()