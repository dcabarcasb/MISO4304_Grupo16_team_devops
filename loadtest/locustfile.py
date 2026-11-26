"""Prueba de estres del microservicio de lista negra (Entrega 4).

Mezcla trafico valido e invalido para observar en New Relic el tiempo de
respuesta de los servicios y de la base de datos, el Apdex y los errores.

Uso (el token es el Bearer JWT del ambiente a probar):

    export BLACKLIST_TOKEN=<jwt>
    locust -f loadtest/locustfile.py --headless \
        --host http://grupo16-alb-1185215880.us-east-1.elb.amazonaws.com
"""
import os
import random
import uuid

from locust import HttpUser, LoadTestShape, between, task

TOKEN = os.environ["BLACKLIST_TOKEN"]
APP_UUID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"


class BlacklistUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        self.auth = {"Authorization": f"Bearer {TOKEN}"}
        self.emails = []

    @task(3)
    def add_email(self):
        email = f"load-{uuid.uuid4().hex[:12]}@example.com"
        with self.client.post(
            "/blacklists",
            json={"email": email, "app_uuid": APP_UUID, "blocked_reason": "stress"},
            headers=self.auth,
            name="POST /blacklists",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.emails.append(email)
                resp.success()
            else:
                resp.failure(f"status {resp.status_code}")

    @task(6)
    def get_blacklisted(self):
        email = random.choice(self.emails) if self.emails else "nadie@example.com"
        self.client.get(
            f"/blacklists/{email}", headers=self.auth, name="GET /blacklists/[email]"
        )

    @task(2)
    def get_unknown(self):
        self.client.get(
            f"/blacklists/unknown-{uuid.uuid4().hex[:8]}@example.com",
            headers=self.auth,
            name="GET /blacklists/[email]",
        )

    # Escenarios de error esperados: se marcan como exitosos en Locust para
    # no ensuciar su reporte, pero New Relic los registra como errores 4xx.
    @task(1)
    def post_invalid(self):
        with self.client.post(
            "/blacklists",
            json={"email": "no-es-email", "app_uuid": "no-es-uuid"},
            headers=self.auth,
            name="POST /blacklists (invalido)",
            catch_response=True,
        ) as resp:
            resp.success() if resp.status_code == 400 else resp.failure(
                f"status {resp.status_code}"
            )

    @task(1)
    def get_without_token(self):
        with self.client.get(
            "/blacklists/x@example.com",
            name="GET /blacklists/[email] (sin token)",
            catch_response=True,
        ) as resp:
            resp.success() if resp.status_code == 401 else resp.failure(
                f"status {resp.status_code}"
            )

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")


class StepLoad(LoadTestShape):
    """Escalones de carga: 10 -> 25 -> 50 -> 100 usuarios, ~2.5 min cada uno."""

    steps = [(150, 10), (300, 25), (450, 50), (600, 100)]
    spawn_rate = 5

    def tick(self):
        run_time = self.get_run_time()
        for limit, users in self.steps:
            if run_time < limit:
                return users, self.spawn_rate
        return None
