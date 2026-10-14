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

Las pruebas requieren una base de datos PostgreSQL disponible (se recomienda una
base separada, por ejemplo `blacklist_test`). Configure `TEST_DATABASE_URL` si
desea usar otra cadena de conexion:

```bash
set TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/blacklist_test
pytest -v
```

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
