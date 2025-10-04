import { detectarAccion } from './comandos.js';

const video = document.getElementById('video');

function esDispositivoMovil() {
  return /Android|webOS|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

async function iniciarCamara(videoElement) {
  let constraints;
  if (esDispositivoMovil()) {
    constraints = { video: { facingMode: { exact: "environment" } }, audio: false };
  } else {
    constraints = { video: true, audio: false };
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    videoElement.srcObject = stream;
    await videoElement.play();
  } catch (err) {
    if (esDispositivoMovil() && constraints.video.facingMode && constraints.video.facingMode.exact) {
      try {
        constraints = { video: { facingMode: "environment" }, audio: false };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        videoElement.srcObject = stream;
        await videoElement.play();
        return;
      } catch (err2) {
        alert("No se pudo acceder a la cámara trasera.\n" + err2.message);
      }
    } else {
      alert("No se pudo acceder a la cámara.\n" + err.message);
    }
  }
}

// Iniciar la cámara automáticamente al cargar
iniciarCamara(video);

function capturarImagen(callback) {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(blob => {
    if (callback) callback(blob);
  }, 'image/jpeg');
}

export function capturarYEnviarImagen(endpoint) {
  if (window.estadoUI && typeof window.estadoUI.enviado === 'function') {
    window.estadoUI.enviado();
  }
  capturarImagen(blob => {
    if (!blob) return;
    const formData = new FormData();
    formData.append('imagen', blob, 'captura.jpg');
    fetch(endpoint, { method: 'POST', body: formData })
      .then(resp => resp.json())
      .then(data => {
        if (window.estadoUI && typeof window.estadoUI.recibiendo === 'function') {
          window.estadoUI.recibiendo?.();
        }
        if (data.audio_url) {
          if (window.estadoUI && typeof window.estadoUI.finalizada === 'function') {
            window.estadoUI.finalizada();
          }
          const audio = new Audio(data.audio_url);
          audio.onended = () => {
            if (window.estadoUI && typeof window.estadoUI.listo === 'function') {
              window.estadoUI.listo();
            }
          };
          audio.play();
        } else {
          if (window.estadoUI && typeof window.estadoUI.listo === 'function') {
            window.estadoUI.listo();
          }
        }
      })
      .catch(() => {
        // En caso de error mantenemos interfaz estable sin sobrescribir estados definidos
        if (window.estadoUI && typeof window.estadoUI.listo === 'function') {
          window.estadoUI.listo();
        }
      });
  });
}

// Exponer utilidad global opcional en caso de uso legacy
window.onSpeechCommandLocal = function(command){
  const accion = detectarAccion(command);
  if (accion === 'captura_imagen') return capturarYEnviarImagen('/procesar_objetos');
  if (accion === 'captura_obstaculos') return capturarYEnviarImagen('/procesar_obstaculos');
  if (accion === 'lectura_texto') return capturarYEnviarImagen('/procesar_lectura_texto');
  if (accion === 'distancia_pasos') return capturarYEnviarImagen('/procesar_distancia_pasos');
};
