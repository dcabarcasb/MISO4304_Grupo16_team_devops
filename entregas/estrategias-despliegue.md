# Estrategias de despliegue en AWS Elastic Beanstalk

Ambiente `blacklist-env` (aplicacion `blacklist-app`, us-east-1), plataforma
Python 3.12 en Amazon Linux 2023, balanceador ALB, Auto Scaling de **3 a 6**
instancias `t3.micro`. Cada estrategia despliega una version nueva del mismo
codigo; la version se lee del archivo `VERSION` y se expone en `GET /health`.

## Metodo de validacion (comun a todas las estrategias)

1. Antes de desplegar se registran los IDs de las instancias del ambiente.
2. Durante el despliegue `scripts/monitor-health.sh` consulta
   `GET /health` cada segundo y guarda hora, codigo HTTP, version e instancia
   (`host`) que respondio. Los logs estan en `entregas/monitoreo/`.
3. En la consola se revisan las pestanas **Events** y **Health & monitoring**
   (columna *Deployment ID* de cada instancia).
4. El tiempo total se toma de los eventos de Beanstalk: desde
   *"Environment update is starting."* hasta
   *"Environment update completed successfully."*.
5. Al terminar se comparan los IDs de instancia con los iniciales.

Nota: el reloj del equipo que corre el monitor esta ~30 s atrasado respecto a
AWS; los tiempos oficiales son los de los eventos de Beanstalk (UTC).

## Resumen

| # | Estrategia | Version | Instancias | Tiempo total | Instancias iniciales o nuevas | Errores observados |
|---|---|---|---|---|---|---|
| 1 | All at once | 1.0.0 -> 1.0.1 | 3 | 1 min 01 s | Iniciales | 3 x HTTP 502 (~4 s sin servicio) |
| 2 | Rolling (lote fijo de 1) | 1.0.1 -> 1.0.2 | 3 (2 en servicio por lote) | 9 min 18 s | Iniciales | 0 errores HTTP; 3 timeouts aislados |
| 3 | Rolling with additional batch (lote de 1) | 1.0.2 -> 1.0.3 | 3 -> 4 -> 3 | 10 min 26 s | Mixto: 1 nueva + 2 iniciales (1 inicial terminada) | 0 errores HTTP; 3 timeouts aislados |
| 4 | Immutable | 1.0.3 -> 1.0.4 | 3 -> 4 -> 6 -> 3 | 18 min 06 s | **Nuevas** (3 instancias nuevas; las 3 iniciales terminadas) | 0 errores HTTP; 3 timeouts aislados |

---

## 1. All at once (v1.0.0 -> v1.0.1)

- **a. Instancias utilizadas:** 3 (las 3 del Auto Scaling group se actualizan a
  la vez; no se lanzan instancias adicionales).
- **b. Validacion:** monitor de `/health` (`entregas/monitoreo/1-all-at-once.log`,
  147 peticiones) + Health & monitoring, donde las 3 instancias pasaron juntas
  al *Deployment ID 2*. El ultimo `1.0.0` se observo a las 21:20:59 y el primer
  `1.0.1` a las 21:21:05 (hora local del monitor); nunca convivieron ambas
  versiones.
- **c. Tiempo total:** **1 min 01 s** (02:21:03.9 -> 02:22:04.6 UTC).
- **d. Instancias:** se desplego sobre las **instancias iniciales**
  (`i-0acd6289032d5be16`, `i-0f88f75aab5964f23`, `i-067889e0968bd9361`),
  identicas antes y despues.
- **e. Capturas:** `entregas/capturas/estrategias/1-all-at-once/`
  (01 politica, 02 carga de la version, 03 health durante, 04 eventos).
- **f. Hallazgos:**
  - Es la estrategia mas rapida, pero **interrumpe el servicio**: hubo 3
    respuestas `502 Bad Gateway` consecutivas (~4 s) mientras gunicorn se
    reiniciaba en todas las instancias al mismo tiempo.
  - No hay mezcla de versiones: el cambio es atomico desde el punto de vista del
    cliente.
  - No requiere capacidad adicional (costo cero extra), pero un error en la
    version nueva afectaria al 100 % de las instancias; el rollback implica
    otro despliegue completo.

---

## 2. Rolling, lote fijo de 1 instancia (v1.0.1 -> v1.0.2)

Configuracion: *Deployment policy* = Rolling, *BatchSizeType* = Fixed,
*BatchSize* = 1.

- **a. Instancias utilizadas:** 3. Se actualiza 1 instancia por lote (3 lotes);
  durante cada lote solo 2 instancias atienden trafico. No se lanzan
  instancias nuevas.
- **b. Validacion:** monitor de `/health` (`entregas/monitoreo/2-rolling.log`,
  514 peticiones) + eventos *"Batch N: Starting application deployment on
  instance(s) [...]"* + Health & monitoring, donde se ve una instancia en
  *Pending application update* / *Deployment ID 4* mientras las otras siguen
  en el 3. En la ventana de mezcla (21:28:29 -> 21:33:08 hora local) el
  balanceador devolvio 106 respuestas `1.0.1` y 104 `1.0.2`.
  Orden de los lotes: `i-0acd6289032d5be16` -> `i-0f88f75aab5964f23` ->
  `i-067889e0968bd9361`.
- **c. Tiempo total:** **9 min 18 s** (02:27:57.1 -> 02:37:15.3 UTC).
  Cada lote tarda ~2 min 40 s: ~35 s para desplegar el codigo y ~2 min
  esperando que el ALB marque la instancia como sana (health check cada 15 s,
  umbral de 3 checks sanos + desregistro de 20 s).
- **d. Instancias:** se desplego sobre las **instancias iniciales** (mismos 3
  IDs antes y despues).
- **e. Capturas:** `entregas/capturas/estrategias/2-rolling/`
  (01 politica, 02 revision de cambios, 03 carga de version, 04-06 health
  durante el despliegue con versiones mezcladas, 07-08 eventos por lote,
  09 health final).
- **f. Hallazgos:**
  - **Sin caida del servicio:** 0 respuestas 5xx; solo 3 timeouts de 3 s
    aislados (0,6 %), asociados a la salida/entrada de instancias del
    balanceador.
  - **Capacidad reducida** al 66 % durante todo el despliegue (2 de 3
    instancias).
  - **Conviven dos versiones** durante ~5 min: los clientes reciben
    respuestas de v1.0.1 y v1.0.2 alternadamente, lo que exige que las
    versiones sean compatibles (API y esquema de BD).
  - Es ~9 veces mas lenta que All at once, porque cada lote espera los health
    checks del ALB; Beanstalk registro un estado *Degraded* transitorio
    mientras la instancia del lote 3 se registraba en el balanceador.

---

## 3. Rolling with additional batch, lote fijo de 1 (v1.0.2 -> v1.0.3)

Configuracion: *Deployment policy* = RollingWithAdditionalBatch,
*BatchSizeType* = Fixed, *BatchSize* = 1.

- **a. Instancias utilizadas:** 3 iniciales + **1 adicional** = **4** durante
  el despliegue; al final vuelve a 3. La capacidad en servicio nunca bajo de 3.
- **b. Validacion:** monitor de `/health`
  (`entregas/monitoreo/3-rolling-additional-batch.log`, 680 peticiones) +
  eventos + Health & monitoring, donde aparecen **4 instancias**: la nueva
  `i-0be989469ee779a06` en *Pending* y luego con *Deployment ID 5* mientras
  las originales seguian en el 4. En el monitor aparecio un cuarto host
  (`ip-172-31-88-76`) respondiendo `1.0.3` desde las 21:46:14 (hora local).
- **c. Tiempo total:** **10 min 26 s** (02:44:05.7 -> 02:54:32.3 UTC). El
  ambiente volvio a *Green* a las 02:56:52 UTC, una vez desregistrada la
  instancia sobrante.
- **d. Instancias:** **mixto**. Secuencia observada:
  1. Lote 1: se lanza la instancia nueva `i-0be989469ee779a06` con v1.0.3.
  2. Lote 2: se actualiza `i-0acd6289032d5be16` (inicial).
  3. Lote 3: se actualiza `i-067889e0968bd9361` (inicial).
  4. Se termina la instancia sobrante `i-0f88f75aab5964f23` (inicial, que
     seguia con v1.0.2 y nunca fue actualizada).

  Resultado: 1 instancia nueva + 2 iniciales actualizadas in-place.
- **e. Capturas:** `entregas/capturas/estrategias/3-rolling-additional-batch/`
  (01 politica, 02 revision, 03 carga de version, 04-06 health con 4
  instancias y versiones mezcladas, 07 eventos de terminacion de la
  sobrante, 08 eventos del lote adicional, 09 health final).
- **f. Hallazgos:**
  - **Sin caida del servicio y sin perdida de capacidad**: el lote extra
    compensa la instancia que sale de servicio en cada lote. 0 respuestas
    5xx; 3 timeouts aislados (0,4 %).
  - Es la mas lenta de las tres hasta ahora: suma ~1 min 15 s para lanzar la
    instancia EC2 nueva antes del primer lote.
  - **Costo adicional temporal**: una instancia mas durante ~10 min.
  - Beanstalk no "devuelve" la instancia nueva: termina una **original**
    (la que quedo sin actualizar), por lo que el ambiente final mezcla
    instancias nuevas y viejas.
  - Tras finalizar, la salud paso brevemente a *Degraded/Severe* mientras la
    instancia terminada se desregistraba del ALB (*draining*), lo que no
    afecto a los clientes.
  - Igual que Rolling, conviven dos versiones durante el despliegue.

---

## 4. Immutable (v1.0.3 -> v1.0.4)

Configuracion: *Deployment policy* = Immutable (el tamano de lote no aplica).

- **a. Instancias utilizadas:** 3 iniciales + **3 nuevas** en un Auto Scaling
  group temporal: hasta **6 instancias** en paralelo (3 -> 4 -> 6 -> 3).
- **b. Validacion:** monitor de `/health` (`entregas/monitoreo/4-immutable.log`,
  894 peticiones; respondieron **6 hosts distintos**) + eventos + EC2 →
  Instances, donde se ven primero 4 y luego 6 instancias *running*, y al
  final las 3 originales en *Terminated*; en Health & monitoring las 3
  instancias finales tienen *Deployment ID 6*.
- **c. Tiempo total:** **18 min 06 s** (03:03:28.7 -> 03:21:34.7 UTC).
- **d. Instancias:** **nuevas**. Iniciales `i-0be989469ee779a06`,
  `i-0acd6289032d5be16`, `i-067889e0968bd9361` (terminadas) -> finales
  `i-0162ce24b7bf06889`, `i-0028d353a4144f877`, `i-0a94de034ecb5cdbd`.
  Secuencia:
  1. Crea un ASG temporal y lanza **1 instancia de prueba** con v1.0.4.
  2. Cuando pasa los health checks (*"Test instance passed health checks"*),
     lanza las 2 restantes.
  3. Espera que las 3 nuevas esten sanas en el ALB, las mueve al ASG
     permanente y ejecuta la configuracion post-despliegue.
  4. Termina las 3 instancias viejas y el ASG temporal.
- **e. Capturas:** `entregas/capturas/estrategias/4-immutable/`
  (01 politica, 02 revision, 03 carga de version, 04 EC2 con la instancia de
  verificacion, 05 EC2 con 6 instancias, 06 health con nuevas y viejas,
  07 eventos, 08 EC2 con las viejas terminadas, 09 health final).
- **f. Hallazgos:**
  - **Sin caida del servicio ni reduccion de capacidad**: 0 respuestas 5xx;
    3 timeouts aislados (0,3 %). Las instancias viejas siguieron atendiendo
    hasta que las nuevas estuvieron sanas.
  - Es la estrategia **mas lenta** (~18 min): lanzar instancias EC2 nuevas,
    verificar primero una de prueba y luego terminar las viejas toma tiempo.
  - **Mayor costo temporal**: el doble de instancias (6) durante el
    despliegue; hay que considerar los limites de la cuenta.
  - **Rollback mas seguro**: si la instancia de prueba falla, solo se
    descarta el ASG temporal y las instancias originales nunca se tocan.
  - Durante la ventana de transicion conviven v1.0.3 y v1.0.4 (las nuevas se
    registran en el mismo ALB antes de retirar las viejas).
  - Las instancias quedan "limpias" (recien creadas), evitando deriva de
    configuracion de despliegues anteriores in-place.

---

## Comparativo y conclusiones

| Criterio | All at once | Rolling | Rolling + batch adicional | Immutable |
|---|---|---|---|---|
| Tiempo total | **1 min 01 s** | 9 min 18 s | 10 min 26 s | 18 min 06 s |
| Caida de servicio | Si (~4 s, 502) | No | No | No |
| Capacidad minima | 0 % | 66 % | 100 % | 100 % |
| Instancias maximas | 3 | 3 | 4 | 6 |
| Mezcla de versiones | No | Si | Si | Si (breve) |
| Instancias finales | Iniciales | Iniciales | Mixtas | Nuevas |
| Costo extra | Ninguno | Ninguno | 1 instancia ~10 min | 3 instancias ~15 min |
| Rollback | Redesplegar todo | Redesplegar | Redesplegar | Descartar ASG temporal |

- **All at once** sirve para ambientes de desarrollo o cuando se acepta una
  breve indisponibilidad.
- **Rolling** evita la caida sin costo extra, a cambio de capacidad reducida
  y versiones mezcladas.
- **Rolling with additional batch** mantiene la capacidad completa con un
  costo extra pequeno; util para produccion con trafico constante.
- **Immutable** es la mas segura (no toca las instancias en servicio y el
  rollback es inmediato), a cambio de ser la mas lenta y costosa.
