# Guion del video de sustentacion – Proyecto 1, Entrega 1 (Grupo 16)

**Duracion objetivo: 9 min 30 s** (limite 10:00; todo lo que pase del minuto 10
no se evalua). El video se graba **mostrando evidencia en vivo** (GitHub, consola
de AWS, Postman, terminal), no leyendo el PDF.

Reparto sugerido: **I1** = Integrante 1, **I2**, **I3**, **I4**.

---

## Antes de grabar (checklist)

- [ ] Ambiente `blacklist-env` en **Ok** y RDS `blacklist-db` en **Available**.
- [ ] Politica de despliegue cambiada a **All at once** (Configuration →
      Updates, monitoring and logging → Edit). Esperar a que quede *Ok*.
      (Se usa en la demo en vivo de la seccion 6; tarda ~1 min.)
- [ ] Paquete listo: `.\scripts\build-zip.ps1 -Version 1.0.5` → `dist/blacklist-v1.0.5.zip`.
- [ ] Postman: workspace abierto, environment **Blacklist Microservice - AWS
      Beanstalk** seleccionado y variable `token` con el valor de
      `BEARER_TOKEN` del `.env` (no mostrar el `.env` en pantalla).
- [ ] Pestanas abiertas en este orden: GitHub (repo) · RDS (blacklist-db) ·
      Beanstalk (blacklist-env) · EC2 Instances (filtro blacklist-env) ·
      Postman · documentacion publicada de Postman.
- [ ] Terminal listo con el monitor (sin ejecutarlo aun):
      `bash scripts/monitor-health.sh http://blacklist-grupo16.us-east-1.elasticbeanstalk.com entregas/monitoreo/demo.log`
      y en otra terminal `tail -f entregas/monitoreo/demo.log`.
- [ ] Ocultar o recortar: contrasenas, valores de variables de entorno,
      `.env`, tokens. Cerrar notificaciones.
- [ ] Ensayar una vez con cronometro.

---

## 0:00 – 0:30 · Introduccion (I1)

**Pantalla:** portada o README del repo.

> "Somos el Grupo 16 de DevOps. En esta entrega desplegamos manualmente, sin
> CI/CD, un microservicio en Python/Flask para gestionar la lista negra global
> de emails sobre AWS Elastic Beanstalk, con PostgreSQL en RDS. Vamos a
> mostrar el codigo, la infraestructura en AWS, las pruebas en Postman y cuatro
> estrategias de despliegue."

## 0:30 – 1:40 · Repositorio en GitHub (I1)

**Pantalla:** `github.com/dcabarcasb/MISO4304_Grupo16_team_devops`

1. Estructura: `app/`, `tests/`, `postman/`, `.ebextensions/`, `Procfile`,
   `requirements.txt` → "stack exigido: Flask, Flask-SQLAlchemy, Flask-RESTful,
   Flask-Marshmallow, Flask-JWT-Extended, Werkzeug y PostgreSQL".
2. Abrir `app/resources/blacklist.py`:
   - `POST /blacklists`: valida `email`, `app_uuid` (UUID obligatorio) y
     `blocked_reason` (opcional, max 255) y **guarda la IP de origen y la
     fecha/hora**.
   - `GET /blacklists/<email>`: retorna `is_blacklisted` y `blocked_reason`.
   - Ambos con `@jwt_required()` → Bearer Token estatico.
3. `app/models.py`: columnas `request_ip` y `created_at`.
4. `.ebextensions/01_environment.config`: ALB, Auto Scaling **3–6**,
   health check `/health`, health reporting *enhanced*.
5. Historial de commits / PRs del equipo (1 clic en *Commits*).

## 1:40 – 2:40 · RDS (I2)

**Pantalla:** RDS → Databases → `blacklist-db`

> "La persistencia esta en RDS PostgreSQL 18.3, instancia db.t4g.micro,
> Single-AZ, **sin acceso publico**."

1. Pestana *Connectivity & security*: endpoint, puerto 5432, VPC por defecto.
2. Clic en el security group `blacklist-rds-sg` → *Inbound rules*:
   > "Solo se permite el puerto 5432 desde el security group de las
   > instancias de Beanstalk; la base no es accesible desde Internet."
3. Pestana *Configuration*: base inicial `blacklist`.

## 2:40 – 4:10 · Elastic Beanstalk y health checks (I2)

**Pantalla:** Beanstalk → `blacklist-env`

1. *Overview*: Health **Ok**, plataforma Python 3.12 / AL2023, dominio,
   version en ejecucion.
2. *Configuration*:
   - **Capacity**: Load balanced, min 3 / max 6, `t3.micro`.
   - **Load balancer**: ALB, proceso *default* → **Health check path
     `/health`**, codigo 200, intervalo 15 s, umbrales 3/5.
   - **Updates, monitoring and logging**: *Enhanced* health; politica de
     despliegue.
   - **Environment properties**: mostrar solo los **nombres**
     (`DATABASE_URL`, `JWT_SECRET_KEY`, `STATIC_API_TOKEN`) — no los valores.
3. *Health & monitoring*: 3 instancias en **Ok**.
4. Navegador: abrir `http://blacklist-grupo16.us-east-1.elasticbeanstalk.com/health`
   y refrescar 3–4 veces:
   > "El campo `host` cambia: el balanceador reparte entre las 3 instancias."

## 4:10 – 6:00 · Escenarios de prueba en Postman (I3)

**Pantalla:** Postman → coleccion **Blacklist Microservice**, environment AWS.

1. Mostrar el environment AWS (`base_url` de Beanstalk; `token` como *secret*).
2. Ejecutar en vivo 3 requests mostrando request/response:
   - **Add email to blacklist** → `201` (body con `email`, `app_uuid`,
     `blocked_reason`; pestana *Tests* en verde).
   - **Check if email is blacklisted** → `200` `is_blacklisted: true` y el motivo.
   - **Rechazar solicitud sin token** → `401`.
3. **Run collection** (Collection Runner) con el environment AWS: mostrar
   todos los tests en verde (201, 409 duplicado, 400 UUID/email/motivo
   invalidos, 401 sin token, 200 no registrado, 422 token invalido, health).
   > "El email se genera aleatorio en cada corrida, por eso la coleccion se
   > puede repetir."
4. Abrir la **documentacion publicada**
   (`documenter.getpostman.com/view/58993096/2sBYHSx1BC`): endpoints con
   ejemplos de request y response.

## 6:00 – 9:00 · Estrategias de despliegue (I4)

**6:00 – 6:40 · Contexto**
**Pantalla:** Beanstalk → *Application versions* (v1.0.0 … v1.0.4).

> "Ejecutamos cuatro estrategias sobre el grupo de 3 a 6 instancias. Cada una
> desplego una version nueva; la version se expone en `/health`, y un script
> consultaba ese endpoint cada segundo para validar el despliegue en vivo."

Mostrar la tabla resumen (puede ser la del `estrategias-despliegue.md` en
GitHub, 5 s):

| Estrategia | Tiempo | Instancias | Iniciales/nuevas | Caida |
|---|---|---|---|---|
| All at once | 1 min 01 s | 3 | Iniciales | Si, ~4 s (502) |
| Rolling (lote 1) | 9 min 18 s | 3 (2 en servicio) | Iniciales | No |
| Rolling + lote adicional | 10 min 26 s | 3 → 4 → 3 | Mixto | No |
| Immutable | 18 min 06 s | 3 → 6 → 3 | Nuevas | No |

**6:40 – 7:50 · Demo en vivo: All at once (v1.0.5)**

1. Iniciar el monitor en la terminal (mitad de pantalla) con `tail -f`.
2. Beanstalk → *Upload and deploy* → `blacklist-v1.0.5.zip`, etiqueta `v1.0.5`
   → mostrar "*will be deployed using the AllAtOnce policy*" → **Deploy**.
3. Mientras corre (~1 min), narrar:
   > "Las 3 instancias se actualizan a la vez; en el monitor vemos unos
   > segundos de 502 y luego todas responden 1.0.5. Es la mas rapida pero
   > tiene caida de servicio."
4. Mostrar *Events*: "Environment update is starting" → "completed
   successfully" → tiempo total.

**7:50 – 8:20 · Rolling**
**Pantalla:** *Events* (paginas anteriores) o captura del documento.
> "Con lote de 1 se actualiza una instancia a la vez (Batch 1, 2, 3). No hubo
> errores, pero la capacidad bajo a 2 de 3 y convivieron v1.0.1 y v1.0.2. Tardo
> 9 min 18 s porque cada lote espera los health checks del ALB."

**8:20 – 8:45 · Rolling with additional batch**
> "Beanstalk lanzo una cuarta instancia antes de empezar, asi nunca bajo de 3
> instancias. Al final termino una de las originales: el ambiente quedo con una
> instancia nueva y dos iniciales. 10 min 26 s, sin errores."

**8:45 – 9:10 · Immutable**
**Pantalla:** EC2 → Instances (filtro `blacklist-env`, incluir *terminated*).
> "Creo un Auto Scaling group temporal, verifico primero una instancia y luego
> lanzo las demas: llegamos a 6 instancias. Cuando las nuevas estuvieron sanas,
> termino las 3 originales —aqui se ven en *Terminated*. Es la mas lenta,
> 18 minutos, y la mas costosa, pero la mas segura: el rollback es descartar el
> grupo temporal."

## 9:10 – 9:30 · Cierre (I1 o I4)

> "En resumen: el microservicio cumple los dos endpoints con Bearer Token,
> persiste en RDS, esta desplegado en Beanstalk con health checks y Auto
> Scaling de 3 a 6, y comparamos cuatro estrategias: All at once para
> velocidad, Rolling sin costo extra, Rolling con lote adicional para mantener
> capacidad e Immutable para maxima seguridad. Gracias."

---

## Consejos

- Si algo tarda (carga de la consola), **cortar en edicion**; no narrar esperas.
- Si la demo en vivo de All at once excede el tiempo, reemplazarla por los
  eventos y el log ya guardado (`entregas/monitoreo/1-all-at-once.log`, lineas
  con `HTTP=502`).
- Hablar sobre la pantalla en vivo; el PDF solo como apoyo puntual (el tutor
  lo revisa aparte).
- Despues de grabar: **eliminar el ambiente de Beanstalk y la base RDS** para
  no seguir generando costos (salvo que el tutor cite a sustentacion
  sincrona; en ese caso esperar a esa sesion).
