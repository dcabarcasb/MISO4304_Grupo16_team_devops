# CI en AWS — CodeBuild + CodePipeline (Entrega 2)

Guía de configuración del pipeline de integración continua para el microservicio
de lista negra global de emails.

## Prerrequisitos

- Región: `us-east-1` (AWS Academy).
- Repositorio: `dcabarcasb/MISO4304_Grupo16_team_devops`.
- Rama: `main`.
- `buildspec.yml` en la raíz del repositorio y ya publicado en `main`.
- Las pruebas unitarias corren con SQLite en CI (variable `TEST_DATABASE_URL`).
- El artefacto es un ZIP en S3 (sin despliegue automático / sin CD).

## 4.1 Crear el bucket de artefactos (S3)

1. S3 → **Create bucket**.
2. Name: `grupo16-blacklist-artifacts` (debe ser único globalmente; agregue iniciales si está tomado).
3. Region: la misma de todo el proyecto (`us-east-1`).
4. Deje **Block Public Access** activado y el cifrado por defecto. Create.

## 4.2 Crear la conexión con GitHub (CodeStar Connections)

1. Developer Tools → **Settings → Connections → Create connection**.
2. Provider: **GitHub** → name `grupo16-github` → **Connect to GitHub** → autorizar → seleccionar el repositorio `MISO4304_Grupo16_team_devops` → **Connect**.
3. El estado debe quedar en **Available** (puede tardar un minuto).

## 4.3 Crear el proyecto de CodeBuild

1. CodeBuild → **Create build project**.
2. **Project name:** `grupo16-blacklist-build`.
3. **Source:** GitHub → conexión `grupo16-github` → repositorio `MISO4304_Grupo16_team_devops` → rama `main`.
4. **Environment:**
   - Managed image, OS **Ubuntu**, runtime **Standard**, imagen `aws/codebuild/standard:7.0` (incluye Python 3.11).
   - **Privileged:** desactivado (no se usa Docker).
   - **Service role:** **Existing role → `LabRole`** (AWS Academy). Si `LabRole` no permite escribir en S3, use "New service role".
5. **Buildspec:** "Use a buildspec file" → ruta `buildspec.yml` (debe estar publicado en `main`).
6. **Artifacts:** Type **Amazon S3** → bucket `grupo16-blacklist-artifacts` → nombre `blacklist-build` → empaquetado **Zip**.
7. **Logs:** CloudWatch logs habilitado (necesario para las capturas de pantalla).
8. **Environment variables** (si no están definidas en el buildspec):
   - `TEST_DATABASE_URL` = `sqlite:///./test_ci.db`
9. Create. Luego **Start build** una vez para confirmar que ejecuta `pytest` y sube el ZIP.

## 4.4 Crear el CodePipeline

1. CodePipeline → **Create pipeline** → nombre `grupo16-blacklist-pipeline`.
2. **Service role:** Existing role → `LabRole` (o crear uno nuevo).
3. **Source stage:**
   - Provider **GitHub (via GitHub App)** → conexión `grupo16-github`.
   - Repositorio `MISO4304_Grupo16_team_devops`, rama `main`.
   - **Change detection:** GitHub webhooks (por defecto) → se dispara en cada push a `main`.
4. **Build stage:** provider **AWS CodeBuild** → proyecto `grupo16-blacklist-build`.
5. **Deploy stage:** **Skip deploy stage** (sin CD, según el enunciado).
6. Create. La primera ejecución inicia automáticamente.

## 4.5 Evidencias a capturar

- **Ejecución exitosa:** grafo de ejecución del CodePipeline (todo en verde), logs de CodeBuild mostrando `pytest` en verde y el objeto `blacklist-build.zip` creado en S3.
- **Ejecución fallida:** publicar temporalmente un commit que rompa una prueba (p. ej. cambiar un assert), dejar correr el pipeline, capturar la etapa Build fallida y la salida de la prueba que falla; luego revertir el commit y volver a ejecutar.
- Capturar también el estado de la conexión, la configuración del proyecto de CodeBuild y las etapas source/build del pipeline para el documento PDF.
