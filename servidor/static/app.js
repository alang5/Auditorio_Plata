
const disponiblesEl = document.getElementById("disponibles");
const emitidosEl = document.getElementById("emitidos");
const progresoEl = document.getElementById("progreso");

const estadoEl = document.getElementById("estado-servidor");
const boton = document.getElementById("btn-boleto");
const mensajeEl = document.getElementById("mensaje");

const resultadoEl = document.getElementById("resultado");
const folioEl = document.getElementById("folio");
const descargarEl = document.getElementById("descargar");
const tipoResultadoEl = document.getElementById("tipo-resultado");
const opcionesTipo = document.querySelectorAll('input[name="tipo_boleto"]');

let enviando = false;
let hayDisponibilidad = false;
let solicitudPendiente = null;
let tipoPendiente = null;

function actualizarControles() {
    // Si hay una solicitud pendiente, se puede reintentar incluso con aforo agotado.
    boton.disabled = enviando || (!hayDisponibilidad && !solicitudPendiente);
    opcionesTipo.forEach(opcion => {
        opcion.disabled = enviando || solicitudPendiente !== null;
    });
}


// ========================================
// CONSULTAR AFORO
// ========================================

async function consultarAforo() {

    try {
        const respuesta = await fetch("/aforo", {
            cache: "no-store"
        });

        if (!respuesta.ok) {
            throw new Error("No se pudo consultar el aforo");
        }

        const datos = await respuesta.json();

        disponiblesEl.textContent =
            datos.disponibles.toLocaleString("es-MX");

        emitidosEl.textContent =
            datos.emitidos.toLocaleString("es-MX");

        const porcentaje =
            (datos.emitidos / datos.aforo) * 100;

        progresoEl.style.width = porcentaje + "%";

        hayDisponibilidad = datos.disponibles > 0;

        estadoEl.textContent = hayDisponibilidad
            ? "Sistema disponible"
            : "Aforo agotado";

        actualizarControles();

    } catch (error) {

        hayDisponibilidad = false;
        disponiblesEl.textContent = "--";
        emitidosEl.textContent = "--";
        estadoEl.textContent = "Error de conexión";
        actualizarControles();

        console.error(error);
    }
}


// ========================================
// SOLICITAR BOLETO
// ========================================

async function solicitarBoleto() {

    if (enviando || (!hayDisponibilidad && !solicitudPendiente)) {
        return;
    }

    enviando = true;
    boton.disabled = true;
    boton.textContent = "Procesando solicitud...";

    mensajeEl.textContent = "";
    resultadoEl.classList.add("oculto");

    // Conservar el mismo ID si falla la red
    if (!solicitudPendiente) {
        // Se conserva también el tipo de boleto en los reintentos.
        tipoPendiente = document.querySelector('input[name="tipo_boleto"]:checked').value;
        solicitudPendiente = crypto.randomUUID();
    }
    actualizarControles();

    try {

        const respuesta = await fetch("/boletos", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                solicitud_id: solicitudPendiente,
                hilo_id: "web",
                tipo_boleto: tipoPendiente
            })
        });

        const datos = await respuesta.json();

        if (!respuesta.ok) {

            if (respuesta.status === 409 || respuesta.status === 400 || respuesta.status === 422) {
                solicitudPendiente = null;
                tipoPendiente = null;
            }

            throw new Error(
                typeof datos.detail === "string"
                    ? datos.detail
                    : "No se pudo emitir el boleto"
            );
        }

        const folio = datos.folio;
        const coincidencia = /^AP-(\d+)$/.exec(folio);

        if (!coincidencia) {
            throw new Error("El servidor devolvió un folio inválido");
        }

        solicitudPendiente = null;
        tipoPendiente = null;

        folioEl.textContent = folio;
        tipoResultadoEl.textContent = datos.tipo_boleto;

        descargarEl.href =
            "/boletos/" + Number(coincidencia[1]) + "/pdf";

        resultadoEl.classList.remove("oculto");

        mensajeEl.textContent = "Solicitud completada.";

    } catch (error) {

        mensajeEl.textContent = error.message;
        if (solicitudPendiente) {
            mensajeEl.textContent += " Puedes reintentar la misma solicitud.";
        }

    } finally {

        enviando = false;
        boton.textContent = solicitudPendiente ? "Reintentar solicitud" : "Solicitar boleto gratuito";
        actualizarControles();

        await consultarAforo();
    }
}


// ========================================
// EVENTOS
// ========================================

boton.addEventListener("click", solicitarBoleto);

// Consulta inicial
consultarAforo();

// Actualización cada 15 segundos
setInterval(consultarAforo, 15000);
