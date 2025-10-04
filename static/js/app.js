import { detectarAccion } from './comandos.js';
import { capturarYEnviarImagen } from './camara.js';
import './mode_navegacion.js';

document.addEventListener('DOMContentLoaded', function() {
  const btnMicrofono = document.getElementById('microfono');
  const estado = document.getElementById('estado');
  const grabando = document.getElementById('grabando');

  // Utiliza las funciones de estadoUI si existen
  function setEstadoUI(etapa) {
    if (window.estadoUI && typeof window.estadoUI[etapa] === 'function') {
      window.estadoUI[etapa]();
    }
  }

  // Sistema de vibración con diferentes niveles
  const NIVELES_VIBRACION = {
    SUAVE: 1,
    MEDIO: 2,
    FUERTE: 3
  };

  // Configuración actual (puede ser modificada posteriormente)
  let nivelVibracion = NIVELES_VIBRACION.MEDIO;

  // Funciones de vibración con diferentes intensidades
  function vibracionEnvio() {
    if (!navigator.vibrate) return;
    
    switch(nivelVibracion) {
      case NIVELES_VIBRACION.SUAVE:
        navigator.vibrate(150); // Vibración suave y corta
        break;
      case NIVELES_VIBRACION.MEDIO:
        navigator.vibrate(250); // Vibración media
        break;
      case NIVELES_VIBRACION.FUERTE:
        navigator.vibrate(400); // Vibración fuerte
        break;
    }
  }

  function vibracionRecepcion() {
    if (!navigator.vibrate) return;
    
    switch(nivelVibracion) {
      case NIVELES_VIBRACION.SUAVE:
        navigator.vibrate([200, 80, 200]); // Patrón suave
        break;
      case NIVELES_VIBRACION.MEDIO:
        navigator.vibrate([300, 100, 300]); // Patrón medio
        break;
      case NIVELES_VIBRACION.FUERTE:
        navigator.vibrate([450, 150, 450]); // Patrón fuerte
        break;
    }
  }

  function vibracionError() {
    if (!navigator.vibrate) return;
    
    switch(nivelVibracion) {
      case NIVELES_VIBRACION.SUAVE:
        navigator.vibrate([80, 80, 80, 80, 80]); // Error suave
        break;
      case NIVELES_VIBRACION.MEDIO:
        navigator.vibrate([120, 100, 120, 100, 120]); // Error medio
        break;
      case NIVELES_VIBRACION.FUERTE:
        navigator.vibrate([200, 120, 200, 120, 200]); // Error fuerte
        break;
    }
  }

  function vibracionBotonPresionado() {
    if (!navigator.vibrate) return;
    
    switch(nivelVibracion) {
      case NIVELES_VIBRACION.SUAVE:
        navigator.vibrate(100); // Confirmación suave al presionar botón
        break;
      case NIVELES_VIBRACION.MEDIO:
        navigator.vibrate(150); // Confirmación media al presionar botón
        break;
      case NIVELES_VIBRACION.FUERTE:
        navigator.vibrate(200); // Confirmación fuerte al presionar botón
        break;
    }
  }

  function vibracionListo() {
    if (!navigator.vibrate) return;
    
    switch(nivelVibracion) {
      case NIVELES_VIBRACION.SUAVE:
        navigator.vibrate([50, 50, 50]); // Señal suave de "listo"
        break;
      case NIVELES_VIBRACION.MEDIO:
        navigator.vibrate([80, 60, 80]); // Señal media de "listo"
        break;
      case NIVELES_VIBRACION.FUERTE:
        navigator.vibrate([120, 80, 120]); // Señal fuerte de "listo"
        break;
    }
  }

  // Función para cambiar el nivel de vibración
  function cambiarNivelVibracion(nivel) {
    if (Object.values(NIVELES_VIBRACION).includes(nivel)) {
      nivelVibracion = nivel;
      // Vibración de confirmación del cambio
      if (navigator.vibrate) {
        navigator.vibrate([100, 50, 100, 50, 100]);
      }
      console.log('Nivel de vibración cambiado a:', nivel);
    }
  }

  // Función para probar vibración
  function probarVibracion() {
    console.log('Probando vibración - Nivel:', nivelVibracion);
    vibracionRecepcion();
  }

  // Hacer funciones disponibles globalmente para control externo
  window.vibracionControles = {
    cambiarNivel: cambiarNivelVibracion,
    probar: probarVibracion,
    niveles: NIVELES_VIBRACION,
    getNivelActual: () => nivelVibracion,
    vibracionEnvio: vibracionEnvio,
    vibracionRecepcion: vibracionRecepcion,
    vibracionError: vibracionError,
    vibracionBotonPresionado: vibracionBotonPresionado,
    vibracionListo: vibracionListo
  };

  let recognition;
  if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;

    // Lógica para manejar la acción devuelta por /procesar_audio y llamar a la ruta correcta
    function ejecutarAccion(accion){
      vibracionEnvio();
      switch(accion){
        case 'captura_imagen':
          setEstadoUI('enviado');
          return capturarYEnviarImagen('/procesar_objetos');
        case 'captura_obstaculos':
          setEstadoUI('enviado');
          return capturarYEnviarImagen('/procesar_obstaculos');
        case 'lectura_texto':
          setEstadoUI('enviado');
          return capturarYEnviarImagen('/procesar_lectura_texto');
        case 'distancia_pasos':
          setEstadoUI('enviado');
          return capturarYEnviarImagen('/procesar_distancia_pasos');
        case 'modo_navegacion':
          return activarModoNavegacion();
        case 'detener_navegacion':
          return detenerModoNavegacion();
      }
    }

    function activarModoNavegacion() {
      if (window.navigationMode && !window.navigationMode.navigationActive()) {
        window.navigationMode.startNavigation();
      }
      vibracionRecepcion();
    }

    function detenerModoNavegacion() {
      if (window.navigationMode && window.navigationMode.navigationActive()) {
        window.navigationMode.stopNavigation();
      }
      vibracionListo();
    }

    // Se usa la función importada desde camara.js (no redefinir aquí)

    // Modifica el callback de reconocimiento de voz para usar la acción
    recognition.onresult = function(event) {
      const transcript = event.results[0][0].transcript;
      vibracionEnvio(); // Vibración al enviar instrucción de voz
      setEstadoUI('enviado'); // Instrucción enviada, esperando respuesta...
      fetch('/procesar_audio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: transcript })
      })
      .then(resp => resp.json())
      .then(data => {
        setEstadoUI('recibiendo'); // Procesando respuesta...
        if (data.accion) { // backend clasificó comando
          ejecutarAccion(data.accion);
        } else if (data.audio_url) {
          setEstadoUI('finalizada');
          vibracionRecepcion();
          const audio = new Audio(data.audio_url);
          audio.onended = function() {
            setEstadoUI('listo');
            vibracionListo();
          };
          audio.play();
        } else {
          // fallback: intentar clasificar local si backend devolvió texto genérico
            const posible = detectarAccion(transcript);
            if (posible) {
              ejecutarAccion(posible);
            } else {
              setEstadoUI('listo');
              vibracionListo();
            }
        }
      })
      .catch(() => {
        vibracionError(); // Vibración de error
        estado.textContent = 'Error al enviar el texto al servidor';
      });
    };
    recognition.onend = function() {
      btnMicrofono.disabled = false;
      btnMicrofono.classList.remove('grabando');
      btnMicrofono.setAttribute('aria-pressed','false');
      if (grabando) grabando.style.display = 'none';
    };

    btnMicrofono.onclick = function() {
      vibracionBotonPresionado();
      recognition.start();
      btnMicrofono.disabled = true;
      btnMicrofono.classList.add('grabando');
      btnMicrofono.setAttribute('aria-pressed','true');
      if (grabando) grabando.style.display = 'inline';
      setEstadoUI('grabando');
      setTimeout(() => { recognition.stop(); }, 10000);
    };
  } else {
    btnMicrofono.disabled = true;
    estado.textContent = 'Tu navegador no soporta reconocimiento de voz.';
  }
});
