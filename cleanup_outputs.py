"""Script de limpieza de archivos generados.

Elimina (por defecto) TODO el contenido de las carpetas de resultados para evitar acumulación:
- objetos_detectados/
- obstaculos_detectados/
- imagen_texto/
- distancia_pasos/
- procesar_imagen/capturas/
- respuestas_devuelta/
- instrucciones_enviadas/
- static/audio/
- procesar_audio/

Modo seguro (default): pide confirmación.
Se puede usar --yes para no preguntar.
Se puede usar --dry-run para ver qué eliminaría.

Uso:
    python cleanup_outputs.py           # interactivo
    python cleanup_outputs.py --yes     # limpia sin preguntar
    python cleanup_outputs.py --dry-run # solo muestra
    python cleanup_outputs.py --keep-days 3  # conserva archivos modificados en los últimos 3 días

"""
from __future__ import annotations
import os
import argparse
import time
from datetime import datetime, timedelta

CARPETAS = [
    'objetos_detectados',
    'obstaculos_detectados',
    'imagen_texto',
    'distancia_pasos',
    os.path.join('procesar_imagen', 'capturas'),
    'respuestas_devuelta',
    'instrucciones_enviadas',
    os.path.join('static', 'audio'),
    'procesar_audio',
]

EXTCONSERVAR = {'.gitkeep'}  # por si decides añadir marcadores vacíos


def listar_archivos(base: str):
    for root, _dirs, files in os.walk(base):
        for f in files:
            yield os.path.join(root, f)


def debe_eliminar(path: str, limite_timestamp: float | None) -> bool:
    if not os.path.isfile(path):
        return False
    if os.path.splitext(path)[1].lower() in EXTCONSERVAR:
        return False
    if limite_timestamp is None:
        return True
    mtime = os.path.getmtime(path)
    return mtime < limite_timestamp


def limpiar(dry_run: bool, keep_days: int | None):
    limite_ts = None
    if keep_days is not None and keep_days > 0:
        limite_dt = datetime.now() - timedelta(days=keep_days)
        limite_ts = limite_dt.timestamp()
    total = 0
    eliminados = 0
    for carpeta in CARPETAS:
        if not os.path.exists(carpeta):
            continue
        for path in listar_archivos(carpeta):
            total += 1
            if debe_eliminar(path, limite_ts):
                print(f"ELIMINAR: {path}" if dry_run else f"Eliminando: {path}")
                if not dry_run:
                    try:
                        os.remove(path)
                        eliminados += 1
                    except Exception as e:
                        print(f"  (Error al eliminar {path}: {e})")
            else:
                print(f"CONSERVAR: {path}")
    print(f"\nResumen: {eliminados if not dry_run else '---'} eliminados / {total} archivos considerados.")
    if keep_days is not None:
        print(f"(Se conservaron archivos modificados en los últimos {keep_days} días)")


def main():
    parser = argparse.ArgumentParser(description='Limpia archivos generados del asistente visual.')
    parser.add_argument('--yes', action='store_true', help='No pedir confirmación (modo no interactivo).')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar sin eliminar.')
    parser.add_argument('--keep-days', type=int, default=None, help='Conservar archivos recientes (días).')
    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        print('Este script eliminará archivos generados en:')
        for c in CARPETAS:
            print(' -', c)
        resp = input('¿Continuar? (escribe SI para confirmar): ').strip().lower()
        if resp != 'si':
            print('Cancelado.')
            return

    limpiar(dry_run=args.dry_run, keep_days=args.keep_days)


if __name__ == '__main__':
    main()
