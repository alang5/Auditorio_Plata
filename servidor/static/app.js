
const disponiblesEl = document.getElementById("disponibles");
const emitidosEl = document.getElementById("emitidos");
const progresoEl = document.getElementById("progreso");

const estadoEl = document.getElementById("estado-servidor");
const boton = document.getElementById("btn-boleto");
const mensajeEl = document.getElementById("mensaje");

const resultadoEl = document.getElementById("resultado");
const folioEl = document.getElementById("folio");
const descargarEl = document.getElementById("descargar");

let enviando = false;
let hayDisponibilidad = false;
let solicitudPendiente = null;


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

        boton.disabled = enviando || !hayDisponibilidad;

    } catch (error) {

        hayDisponibilidad = false;
        disponiblesEl.textContent = "--";
        emitidosEl.textContent = "--";
        estadoEl.textContent = "Error de conexión";
        boton.disabled = true;

        console.error(error);
    }
}


// ========================================
// SOLICITAR BOLETO
// ========================================

async function solicitarBoleto() {

    if (enviando || !hayDisponibilidad) {
        return;
    }

    enviando = true;
    boton.disabled = true;
    boton.textContent = "Procesando solicitud...";

    mensajeEl.textContent = "";
    resultadoEl.classList.add("oculto");

    // Conservar el mismo ID si falla la red
    if (!solicitudPendiente) {
        solicitudPendiente = crypto.randomUUID();
    }

    try {

        const respuesta = await fetch("/boletos", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                solicitud_id: solicitudPendiente,
                hilo_id: "web"
            })
        });

        const datos = await respuesta.json();

        if (!respuesta.ok) {

            if (respuesta.status === 409) {
                solicitudPendiente = null;
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

        folioEl.textContent = folio;

        descargarEl.href =
            "/boletos/" + Number(coincidencia[1]) + "/pdf";

        resultadoEl.classList.remove("oculto");

        mensajeEl.textContent = "Solicitud completada.";

    } catch (error) {

        mensajeEl.textContent = error.message;

    } finally {

        enviando = false;
        boton.textContent = "Solicitar boleto gratuito";

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
