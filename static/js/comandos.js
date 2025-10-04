// Centralización de palabras clave y utilidades de comandos
// Mantener sincronía con lógica backend (Servidor.py)

export const palabrasClave = {
  objetos: [
    'describe', 'describeme', 'objetos', 'foto', 'captura', 'imagen', 'enfrente', 'ves',
    'detectar objeto', 'detectar objetos', 'qué ves', 'qué hay', 'muéstrame', 'mostrar', 'analiza', 'analizar'
  ],
  obstaculos: [
    'obstáculo', 'obstaculo', 'obstáculos', 'obstaculos', 'peligro', 'camino', 'bloqueo', 'impedimento',
    'detecta obstáculo', 'detecta obstaculo', 'hay algo en el camino', 'bloqueado', 'impide', 'frente', 'adelante'
  ],
  lectura: [
    'leer', 'lectura', 'texto', 'leeme', 'lee', 'texto en voz alta', 'leer texto',
    'qué dice', 'qué está escrito', 'palabras', 'contenido escrito', 'puedes leer', 'me puedes leer', 'qué pone', 'dime lo que dice'
  ],
  distancia: [
    'cuántos pasos', 'cuantos pasos', 'qué tan lejos', 'a qué distancia', 'está lejos', 'está cerca', 'puedo llegar',
    'me acerco', 'me alejo', 'cuánto camino', 'cuánto falta', 'cuánto tengo que caminar', 'cuánto me falta', 'está a muchos pasos', 'está a pocos pasos'
  ],
  navegar: [
    'modo deteccion', 'modo detección', 'modo navegacion', 'modo navegación', 'activar navegacion', 'activar deteccion'
  ],
  detenerNavegar: [
    'detener navegacion', 'detener navegación', 'parar navegacion', 'parar navegación', 'salir navegacion', 'salir navegación'
  ]
};

export function detectarAccion(command){
  const t = command.toLowerCase();
  const incl = arr => arr.some(p=> t.includes(p));
  if (incl(palabrasClave.objetos)) return 'captura_imagen';
  if (incl(palabrasClave.obstaculos)) return 'captura_obstaculos';
  if (incl(palabrasClave.lectura)) return 'lectura_texto';
  if (incl(palabrasClave.distancia)) return 'distancia_pasos';
  if (incl(palabrasClave.navegar)) return 'modo_navegacion';
  if (incl(palabrasClave.detenerNavegar)) return 'detener_navegacion';
  return null;
}
