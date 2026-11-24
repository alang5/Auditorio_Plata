# Auditorio Plata

Sistema de emisión de boletos gratuitos para el
Concierto Navideño.

Aforo máximo: 20,000 personas.

## Tecnologías
- Python
- FastAPI
- Oracle Database
- Readers-Writers
- Threading
- PDF y QR


## Instalación y ejecución de Auditorio Plata

### 1. Requisitos previos

Para ejecutar el proyecto se necesita:

- Python 3.11 o superior.
- Git.
- Oracle Database Free (local o remoto).
- Acceso a una terminal (PowerShell, CMD o Bash).
- Conexión a internet para instalar las dependencias.
- Cloudflare Tunnel (opcional, para acceso público).

> La base de datos Oracle debe estar configurada y accesible antes de iniciar el servidor.

### 2. Descargar el repositorio

Clonar el proyecto desde GitHub:

```bash
git clone https://github.com/alang5/Auditorio_Plata
cd Auditorio_Plata
```

### 3. Crear y activar el entorno virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

El archivo incluye las librerías necesarias para FastAPI, Oracle, PDF, QR y el spawner.

### 4. Configurar Oracle Database

La aplicación utiliza Oracle Database Free mediante el puerto 1521 y el servicio `FREEPDB1` en la instalación local de Windows utilizada durante el desarrollo.

Es necesario crear un usuario con permisos para administrar las tablas y secuencias.

Conectarse como administrador mediante SQL*Plus:

```bash
sqlplus system@localhost:1521/FREEPDB1
```

Ejecutar los siguientes comandos SQL únicamente si el usuario todavía no existe:

```sql
CREATE USER auditorio_app
IDENTIFIED BY "CONTRASENA_SEGURA"
DEFAULT TABLESPACE USERS
QUOTA 100M ON USERS;

GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE
TO auditorio_app;
```

Crear las tablas, restricciones y secuencias utilizando el script del repositorio:

```bash
sqlplus auditorio_app@localhost:1521/FREEPDB1 @sql/esquema.sql
```

SQL*Plus solicitará la contraseña del usuario.

> Este script se ejecuta solamente para inicializar una base de datos nueva. No debe ejecutarse nuevamente sobre tablas que ya contienen boletos.

### 5. Configurar las variables de entorno

En la raíz del proyecto, crear un archivo llamado `.env`:

```dotenv
ORACLE_USER=auditorio_app
ORACLE_PASSWORD=CONTRASENA_SEGURA
ORACLE_DSN=localhost:1521/FREEPDB1
```

Modificar los valores según la configuración de Oracle.

Si la base de datos está alojada en otro servidor, sustituir `localhost` por su dirección y utilizar el puerto y nombre de servicio correspondientes.

> Por seguridad, `.env` no debe subirse a GitHub. Está excluido mediante `.gitignore`.

### 6. Iniciar el servidor web

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python -m uvicorn servidor.main:app --host 127.0.0.1 --port 8000
```

Abrir las siguientes direcciones:

| Dirección | Descripción |
|---|---|
| http://127.0.0.1:8000/ | Página principal |
| http://127.0.0.1:8000/aforo | Consulta de disponibilidad |
| http://127.0.0.1:8000/docs | Documentación de la API |

La página permite consultar el aforo, solicitar boletos y descargar archivos PDF con códigos QR.

Para detener el servidor, presionar `Ctrl + C`.

### 7. Ejecutar el spawner concurrente

Mantener FastAPI ejecutándose y abrir una segunda terminal.

Activar el entorno virtual y ejecutar:

```bash
python -m spawner.spawner --solicitudes 100 --hilos 100 --concurrentes 10 --modo uniforme --ventana 60
```

Para ejecutar una prueba en modo ráfaga:

```bash
python -m spawner.spawner --solicitudes 100 --hilos 100 --concurrentes 10 --modo rafaga --ventana 60
```

El spawner utiliza hilos para realizar solicitudes HTTP al servidor y registra:

- Identificador del hilo.
- Hora de envío y recepción.
- Folio obtenido.
- Estado de la solicitud.
- Latencia de respuesta.

Los resultados se guardan automáticamente en:

```text
spawner/resultados/
```

**Nota:** estas pruebas generan boletos reales en Oracle y modifican el contador de aforo.

### 8. Laboratorio de condiciones de carrera

El proyecto incluye un laboratorio web independiente para demostrar el comportamiento del sistema sin y con sincronización.

Iniciar el laboratorio:

```bash
python -m uvicorn pruebas.demo_web:app --host 127.0.0.1 --port 8001
```

Abrir:

http://127.0.0.1:8001/

La página permite ejecutar dos experimentos:

- Sin sincronización: demuestra folios duplicados y actualizaciones perdidas.
- Con Readers–Writers: controla el acceso a la sección crítica y respeta el aforo experimental.

Ambas pruebas utilizan 10 solicitudes HTTP y un aforo de 3 lugares.

Los resultados se guardan en:

```text
pruebas/resultados_demo_web/
```

Este laboratorio utiliza un contador experimental en memoria y no modifica la base de datos Oracle.

### 9. Acceso público mediante Cloudflare Tunnel (opcional)

Para acceder a la aplicación desde otra computadora o celular a través de internet, instalar `cloudflared`.

En Windows:

```powershell
winget install --id Cloudflare.cloudflared -e
```

Con FastAPI ejecutándose en el puerto 8000, abrir otra terminal y ejecutar:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflare generará una URL HTTPS temporal con un formato similar a:

```text
https://nombre-aleatorio.trycloudflare.com
```

**Consideraciones:**

- El túnel es temporal.
- La URL puede cambiar cada vez que se reinicia.
- FastAPI y Cloudflare deben permanecer ejecutándose.
- La computadora anfitriona debe mantenerse encendida.
- No equivale a un servidor alojado permanentemente en la nube.
- No se recomienda exponer públicamente los endpoints sin protección de acceso.

### 10. Ejecución en otra computadora

Para instalar el proyecto en otro equipo se deben realizar los pasos 1 al 6, asegurándose de configurar correctamente la conexión a Oracle.

No es necesario instalar Oracle en cada computadora si todas se conectan a una base de datos remota existente.

Si solamente se desea utilizar la página como usuario, basta con abrir su URL pública desde un navegador; no se requiere instalar Python ni Oracle.

### 11. Detener los servicios

Para finalizar la ejecución:

1. Detener FastAPI con `Ctrl + C`.
2. Detener el spawner o laboratorio, si están ejecutándose.
3. Detener Cloudflare Tunnel con `Ctrl + C`.

Los datos almacenados en Oracle permanecen guardados después de detener la aplicación.
