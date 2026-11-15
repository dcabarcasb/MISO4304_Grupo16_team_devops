# Entrega Continua en AWS — Fargate + CodeDeploy (Entrega 3)

Guía de la Parte 1 (despliegue manual en AWS Fargate) y la Parte 2 (archivos de
configuración para CodeDeploy) del microservicio de lista negra global de emails.

Región: `us-east-1`. Cuenta: `565828850450`. Repositorio:
`dcabarcasb/MISO4304_Grupo16_team_devops`, rama `main`.

## Estado del despliegue manual (pasos 1.0 a 1.11)

| Recurso | Valor |
| --- | --- |
| Repositorio ECR | `565828850450.dkr.ecr.us-east-1.amazonaws.com/grupo16-blacklist` |
| Tag de la imagen manual | `manual-1.2.0` (y `manual-1.2.0-r2`) |
| Clúster ECS | `grupo16-cluster` |
| Servicio ECS | `grupo16-blacklist-service` (`ACTIVE`, Fargate, desired/running 2/2) |
| Definición de tarea | `grupo16-blacklist:2` |
| Target group | `grupo16-tg-blue` (`/health`, targets `healthy`) |
| DNS del ALB | `grupo16-alb-1185215880.us-east-1.elb.amazonaws.com` |
| Log group | `/ecs/grupo16-blacklist` |
| Parámetros SSM | `/grupo16/blacklist/{database_url,jwt_secret,static_token}` |

Verificación rápida:

```bash
curl "http://grupo16-alb-1185215880.us-east-1.elb.amazonaws.com/health"
# {"status":"ok","version":"1.2.0","host":"ip-172-31-11-141.ec2.internal"}
```

### Decisiones de implementación

- **Rol de ejecución:** en esta cuenta no existe `LabRole`; se usa
  `arn:aws:iam::565828850450:role/grupo16-ecs-task-execution-role`, que tiene
  `AmazonECSTaskExecutionRolePolicy` y una política inline con
  `ssm:GetParameter(s)` sobre `/grupo16/blacklist/*` y `kms:Decrypt`.
  Por eso `taskdef.json` referencia ese rol y no `LabRole`.
- **Git Bash en Windows:** convierte los argumentos que empiezan por `/` en rutas
  de Windows, de modo que `--name /grupo16/blacklist/...` falla con
  `ParameterNotFound`. Anteponer `MSYS_NO_PATHCONV=1` a los comandos de SSM.

## 1.12 Evidencias para el documento

Capturas manuales (consola) en `entregas/entrega3/capturas/`:

1. `01-ecr-repositorio-imagen.jpg` — ECR con el tag de la imagen.
2. `02-ecs-cluster-servicio.jpg` — clúster + servicio `ACTIVE`, desired/running 2/2.
3. `03-ecs-task-definition.jpg` — definición de tarea (ocultar valores de secretos).
4. `04-target-group-healthy.jpg` — target group con ambos targets `healthy`.
5. `05-alb-health.jpg` — DNS del ALB y respuesta de `/health`.
6. `06-postman-post-get-sin-token.jpg` — POST 201, GET 200 y petición sin token 401.
7. `07-cloudwatch-log-stream.jpg` — log stream de una tarea.

Evidencia por CLI (se guarda en `entregas/entrega3/evidencias/`):

```bash
export AWS_REGION=us-east-1
export TG_BLUE_ARN=$(aws elbv2 describe-target-groups --names grupo16-tg-blue \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws ecr describe-images --repository-name grupo16-blacklist \
  --query 'imageDetails[*].[imageTags,imagePushedAt]' --output table

aws ecs describe-services --cluster grupo16-cluster \
  --services grupo16-blacklist-service \
  --query 'services[0].[status,desiredCount,runningCount,taskDefinition]' --output table

aws ecs describe-task-definition --task-definition grupo16-blacklist:2 \
  --query 'taskDefinition.{family:family,revision:revision,cpu:cpu,memory:memory,role:executionRoleArn}' --output json

aws elbv2 describe-target-health --target-group-arn "$TG_BLUE_ARN" \
  --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]' --output table

curl "http://grupo16-alb-1185215880.us-east-1.elb.amazonaws.com/health"

aws logs describe-log-streams --log-group-name /ecs/grupo16-blacklist \
  --order-by LastEventTime --descending --max-items 3 \
  --query 'logStreams[*].logStreamName' --output table
```

### Token para Postman

El repositorio no incluye `.env` (no se versiona). El token se genera leyendo los
secretos de SSM:

```bash
export MSYS_NO_PATHCONV=1
export JWT_SECRET_KEY=$(aws ssm get-parameter --name /grupo16/blacklist/jwt_secret \
  --with-decryption --query Parameter.Value --output text)
export STATIC_API_TOKEN=$(aws ssm get-parameter --name /grupo16/blacklist/static_token \
  --with-decryption --query Parameter.Value --output text)
JWT_SECRET_KEY="$JWT_SECRET_KEY" STATIC_API_TOKEN="$STATIC_API_TOKEN" \
  .venv/Scripts/python.exe -m flask --app run.py create-token
```

En Postman: environment `base_url = http://grupo16-alb-1185215880.us-east-1.elb.amazonaws.com`,
`token = <JWT generado>`. Ejecutar `POST /blacklists` (201), `GET /blacklists/<email>`
(200), una petición sin token (401) y la colección completa.

## 1.13 Solución de problemas

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `CannotPullContainerError` | Sin ruta a ECR | Habilitar IP pública o NAT; verificar salida del SG y permisos ECR |
| Targets `unhealthy` | Puerto/ruta o SG incorrectos | Puerto 8000, `/health`, SG de ECS permite 8000 desde SG del ALB |
| La tarea termina de inmediato | App cae / env inválido | Revisar logs en CloudWatch; verificar parámetros SSM y permisos del rol |
| `503` del ALB | Sin targets sanos | Esperar el grace period; revisar salud de targets |
| Error de conexión a BD | SG de RDS / URL | Puerto 5432 desde SG de ECS; `DATABASE_URL` correcto |

Problemas reales encontrados en esta cuenta:

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `AccessDenied`/`NoSuchEntity` al usar `LabRole` | La cuenta no tiene ese rol | Usar `grupo16-ecs-task-execution-role` |
| `ParameterNotFound` con nombres `/grupo16/...` | Git Bash convierte la ruta | `MSYS_NO_PATHCONV=1 aws ssm ...` |
| CodeBuild falla en `docker build` | `Privileged` deshabilitado | Habilitar `Privileged` en el proyecto |
| `docker push` con `AccessDenied` | Rol de CodeBuild sin permisos ECR | Adjuntar `AmazonEC2ContainerRegistryPowerUser` |
| `SubscriptionRequiredException` en CodeDeploy | Servicio no habilitado en la cuenta | Ver nota de la Parte 3 |

## Parte 2 — Archivos para CodeDeploy

### 2.1 `appspec.yaml`

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: "blacklist"
          ContainerPort: 8000
```

`<TASK_DEFINITION>` lo reemplaza CodeDeploy/CodePipeline con la revisión que
registra. `ContainerName` debe coincidir con `taskdef.json`.

### 2.2 `taskdef.json`

Plantilla con la misma familia que la definición manual y la imagen como
placeholder literal `<IMAGE1_NAME>`. No incluye contraseñas ni secretos: los
valores vienen de SSM.

### 2.3 Parámetros SSM

Ya existen (una sola vez). Verificación:

```bash
MSYS_NO_PATHCONV=1 aws ssm describe-parameters --region us-east-1 \
  --parameter-filters "Key=Name,Option=BeginsWith,Values=/grupo16/blacklist/" \
  --query 'Parameters[*].[Name,Type]' --output table
```

Si hay que recrearlos, usar `aws ssm put-parameter --type SecureString --overwrite`
con `MSYS_NO_PATHCONV=1` y los valores reales.

### 2.4 `buildspec.yml`

Fases: `install` (Python 3.12 + dependencias), `pre_build` (login en ECR y tag =
SHA del commit), `build` (`on-failure: ABORT`, `pytest`, `docker build/push`),
`post_build` (`imageDetail.json`). Artefactos: `appspec.yaml`, `taskdef.json`,
`imageDetail.json`. Reporte JUnit en `reports/junit.xml`.

El buildspec anterior de Elastic Beanstalk quedó en `buildspec-eb.yml` para que
la evidencia de la Entrega 2 siga siendo reproducible.

### 2.5 Proyecto de CodeBuild

En `grupo16-blacklist-build`:

1. `Privileged` habilitado (necesario para Docker).
2. Variable de entorno `ECR_REPO_NAME=grupo16-blacklist` (se conserva
   `TEST_DATABASE_URL`).
3. Imagen `aws/codebuild/amazonlinux-x86_64-standard:5.0` y Python 3.12.
4. Rol de servicio con permiso de subida a ECR
   (`AmazonEC2ContainerRegistryPowerUser`).
5. Artefactos en S3 `grupo16-blacklist-artifacts` (nombre `blacklist-build`).

Aplicado por CLI:

```bash
aws codebuild update-project --name grupo16-blacklist-build --region us-east-1 \
  --environment '{"type":"LINUX_CONTAINER","image":"aws/codebuild/amazonlinux-x86_64-standard:5.0","computeType":"BUILD_GENERAL1_MEDIUM","privilegedMode":true,"imagePullCredentialsType":"CODEBUILD","environmentVariables":[{"name":"TEST_DATABASE_URL","value":"sqlite:///./test_ci.db","type":"PLAINTEXT"},{"name":"ECR_REPO_NAME","value":"grupo16-blacklist","type":"PLAINTEXT"}]}'

aws iam attach-role-policy \
  --role-name codebuild-grupo16-blacklist-build-service-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

### 2.6 Validación local

```bash
docker build -t grupo16-blacklist:local .
docker run --rm -p 8001:8000 \
  -e DATABASE_URL="sqlite:////tmp/blacklist.db" \
  -e JWT_SECRET_KEY=local -e STATIC_API_TOKEN=local \
  -e AUTO_CREATE_TABLES=1 grupo16-blacklist:local
curl http://localhost:8001/health

python -m json.tool taskdef.json > /dev/null && echo "taskdef.json OK"
grep -c '<IMAGE1_NAME>' taskdef.json   # >= 1
```

### 2.7 Build manual de CodeBuild

```bash
aws codebuild start-build --project-name grupo16-blacklist-build --region us-east-1
```

Verificar en la consola: 19 pruebas aprobadas y reporte JUnit; nuevo tag en ECR
igual al SHA del commit; artefacto con `appspec.yaml`, `taskdef.json` e
`imageDetail.json`:

```bash
aws s3 cp s3://grupo16-blacklist-artifacts/blacklist-build.zip . 
unzip -p blacklist-build.zip imageDetail.json
# {"ImageURI":"565828850450.dkr.ecr.us-east-1.amazonaws.com/grupo16-blacklist:<sha>"}
```

Opcional (evidencia de CI fallido): romper un `assert`, confirmar que
`on-failure: ABORT` evita la subida de la imagen y revertir el cambio.

### 2.8 Orden de commit

Los archivos de la Parte 2 se commitean antes de agregar la etapa Deploy. No se
versionan `.env`, contraseñas ni tokens; solo IDs de cuenta, ARNs y rutas de
parámetros SSM.

## Nota sobre la Parte 3

El servicio manual usa el controlador de despliegue `ECS` (rolling update). Para
el blue/green de CodeDeploy se necesita un servicio con controlador
`CODE_DEPLOY`, además de la aplicación y el deployment group de CodeDeploy.

En esta cuenta `CodeDeploy` responde `SubscriptionRequiredException`
(`aws deploy list-applications`), por lo que la Parte 3 no puede completarse
hasta que el servicio esté habilitado en la cuenta/laboratorio.
