# Lista Negra Global de Emails - Microservicio

Primera version de un microservicio REST para gestionar la lista negra global de
emails de una organizacion. Permite agregar emails a la lista negra y consultar
si un email ya esta bloqueado.

Proyecto - DevOps - Grupo 16 - Universidad de los Andes.

## Stack tecnologico

- Python 3
- Flask + Flask-RESTful
- Flask-SQLAlchemy (ORM)
- Flask-Marshmallow + Marshmallow (serializacion/validacion)
- Flask-JWT-Extended (autenticacion con Bearer Token)
- Werkzeug
- PostgreSQL
- pytest (pruebas)

## Estructura del proyecto

```
proyecto_grupo_16/
├── app/
│   ├── __init__.py          # Fabrica de la aplicacion y comandos CLI
│   ├── config.py            # Configuracion via variables de entorno
│   ├── extensions.py        # Instancias de db, ma, jwt
│   ├── models.py            # Modelo BlacklistEmail
│   ├── schemas.py           # Esquemas de validacion/serializacion
│   └── resources/
│       ├── __init__.py      # Registro de endpoints
│       └── blacklist.py     # POST /blacklists y GET /blacklists/<email>
├── tests/                   # Pruebas con pytest
├── postman/                 # Coleccion y environment de Postman
├── requirements.txt
├── run.py                   # Punto de entrada local
└── .env.example
```

## Requisitos previos

- Python 3.10 o superior
- Un servidor PostgreSQL en ejecucion (local o remoto)

## Instalacion

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Linux / macOS
```

Edite `.env` y ajuste al menos `DATABASE_URL`. Cree la base de datos en
PostgreSQL (por ejemplo `blacklist`) antes de continuar.

### Variables de entorno

| Variable           | Descripcion                                             |
| ------------------ | ------------------------------------------------------- |
| `DATABASE_URL`     | Cadena de conexion a PostgreSQL.                        |
| `JWT_SECRET_KEY`   | Clave para firmar/verificar los JWT.                    |
| `STATIC_API_TOKEN` | Token estatico predefinido que debe incluir el Bearer.  |
| `HOST` / `PORT`    | Host y puerto del servidor local (por defecto 0.0.0.0:5000). |

## Ejecucion

```bash
# Crear las tablas
flask init-db

# Generar el token (Bearer) estatico
flask create-token

# Levantar el servidor
python run.py
```

El microservicio queda disponible en `http://localhost:5000`.

## Pruebas

Las pruebas unitarias cubren todos los endpoints de la API y por defecto usan
SQLite en memoria, por lo que no requieren un servidor de base de datos:

```bash
pytest -v
```

| Archivo                   | Endpoint                 | Escenarios                                                                 |
| ------------------------- | ------------------------ | -------------------------------------------------------------------------- |
| `tests/test_health.py`    | `GET /health`            | Responde sin token, version configurada, ignora encabezado Authorization   |
| `tests/test_blacklist.py` | `POST /blacklists`       | 401 sin token, 403 token invalido, 201 creacion y persistencia (IP), 409 duplicado (incluye mayusculas), 400 por body vacio, email/UUID invalidos o motivo > 255, motivo opcional |
| `tests/test_blacklist.py` | `GET /blacklists/<email>`| 401 sin token, 403 token invalido, email bloqueado, no bloqueado, busqueda sin distinguir mayusculas |

Para ejecutarlas contra PostgreSQL configure `TEST_DATABASE_URL`:

```bash
export TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/blacklist_test
pytest -v
```

## Integracion continua (AWS CodeBuild + CodePipeline)

El archivo `buildspec.yml` define el build que ejecuta AWS CodeBuild en cada
commit a `main` (disparado por AWS CodePipeline):

1. **install:** Python 3.11 e instalacion de `requirements.txt`.
2. **build:** `pytest` con reporte JUnit (visible en la pestaña *Reports* de
   CodeBuild). Si alguna prueba falla, el build falla y no se genera artefacto.
3. **artifacts:** ZIP listo para Elastic Beanstalk (`app/`, `.ebextensions/`,
   `Procfile`, `requirements.txt`, `run.py`) almacenado en S3. No hay despliegue
   automatico (solo CI).

La configuracion paso a paso en la consola de AWS esta en
[docs/ci-aws-setup.md](docs/ci-aws-setup.md).

## API REST

Todos los endpoints requieren el encabezado `Authorization: Bearer <token>`.

### POST /blacklists

Agrega un email a la lista negra global. Internamente el servicio guarda la IP de
origen y la fecha/hora de la solicitud.

Request body (`application/json`):

```json
{
  "email": "blocked@example.com",
  "app_uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "blocked_reason": "Enviaba spam a los clientes"
}
```

- `email` (String): obligatorio, formato de email valido.
- `app_uuid` (String): obligatorio, debe ser un UUID valido.
- `blocked_reason` (String): opcional, maximo 255 caracteres.

Respuesta `201 Created`:

```json
{
  "message": "Email blocked@example.com was added to the global blacklist.",
  "created": true
}
```

Respuestas de error: `400` (datos invalidos), `401` (token ausente), `403`
(token invalido), `409` (el email ya existe en la lista negra).

### GET /blacklists/<email>

Indica si un email esta en la lista negra global y el motivo.

Respuesta `200 OK`:

```json
{
  "is_blacklisted": true,
  "blocked_reason": "Enviaba spam a los clientes"
}
```

Si el email no esta en la lista:

```json
{
  "is_blacklisted": false,
  "blocked_reason": null
}
```

## Postman

En la carpeta `postman/` se incluyen:

- `collection.json`: coleccion con los dos endpoints y escenarios de prueba.
- `environment.json`: environment con `base_url`, `token` y `email`.

Importe ambos en Postman, ejecute `flask create-token` y pegue el valor en la
variable `token` del environment. Luego importe la coleccion y ejecute las
peticiones.

## Despliegue en AWS Elastic Beanstalk

El repositorio ya incluye lo necesario para la plataforma **Python (Amazon Linux 2023)**:

- `Procfile`: levanta la app con `gunicorn` en el puerto 8000 (nginx de Beanstalk hace proxy).
- `.ebextensions/01_environment.config`: ambiente con balanceador (ALB), auto scaling
  de **3 a 6 instancias**, health check en `GET /health` y health reporting mejorado.
- `GET /health`: endpoint sin token que responde `200` con `status`, `version`
  (variable `APP_VERSION`) y `host` (instancia que atendio la solicitud). Sirve para
  validar las estrategias de despliegue: cambie `APP_VERSION` entre versiones y
  consulte `/health` en bucle para ver que instancias tienen la version nueva.
- Con `AUTO_CREATE_TABLES=1` las tablas se crean al arrancar la aplicacion.

### Pasos

1. Crear una instancia **RDS PostgreSQL** y permitir en su security group el acceso
   (puerto 5432) desde el security group de las instancias de Beanstalk.
2. Generar el paquete a desplegar:

   ```bash
   git archive -o deploy.zip HEAD
   ```

3. Crear la aplicacion y el ambiente en Beanstalk (plataforma Python) subiendo
   `deploy.zip`. En AWS Academy usar `LabRole` / `LabInstanceProfile`.
4. Configurar en el ambiente las variables de entorno (no van en el repositorio):

   | Variable           | Ejemplo                                                        |
   | ------------------ | -------------------------------------------------------------- |
   | `DATABASE_URL`     | `postgresql+psycopg2://usuario:clave@<endpoint-rds>:5432/blacklist` |
   | `JWT_SECRET_KEY`   | clave larga y aleatoria                                        |
   | `STATIC_API_TOKEN` | token estatico de la API                                       |

5. Generar el Bearer token con los mismos `JWT_SECRET_KEY` y `STATIC_API_TOKEN`
   configurados en Beanstalk:

   ```bash
   flask create-token
   ```

6. Verificar: `curl http://<url-beanstalk>/health`.

La estrategia de despliegue (all at once, rolling, rolling with additional batch,
immutable, traffic splitting) se cambia en *Configuration > Updates, monitoring and
logging > Deployment policy* antes de cada nueva version.

## Documentación pública del API

[Consultar documentación en Postman](https://documenter.getpostman.com/view/58993096/2sBYHSx1BC)

Incluye endpoints, ejemplos de solicitudes y respuestas y escenarios de prueba.
Para ejecutar la colección, configure `base_url` y un token propio en el entorno de Postman.
