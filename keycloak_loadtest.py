from locust import HttpUser, task, between
import json
import random
import string
import time


# ---------- Utility ----------
def rand_name(prefix):
    """Generate a random name with a given prefix."""
    return prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


# ---------- Locust User ----------
class KeycloakUser(HttpUser):
    wait_time = between(1, 3)
    token_expires_at = 0
    token = ""
    headers = {}

    # -------- AUTHENTICATION --------
    def authenticate(self):
        """Get a new admin token."""
        res = self.client.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "username": "admin",
                "password": "admin",
                "grant_type": "password",
                "client_id": "admin-cli",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="Get admin token",
        )

        if res.status_code == 200:
            token_json = res.json()
            self.token = token_json.get("access_token", "")
            expires_in = token_json.get("expires_in", 60)
            # Refresh slightly before expiration
            self.token_expires_at = time.time() + expires_in - 5
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        else:
            print(f"❌ Auth failed: {res.status_code}, {res.text}")
            self.token = ""
            self.headers = {}

    def ensure_token(self):
        """Ensure a valid token before each task."""
        if time.time() > self.token_expires_at or not self.token:
            self.authenticate()

    def on_start(self):
        """Authenticate when a simulated user starts."""
        self.authenticate()

    # -------- TASKS --------
    @task(3)
    def list_users(self):
        """GET all users"""
        self.ensure_token()
        self.client.get("/admin/realms/master/users", headers=self.headers, name="GET /users")

    @task(2)
    def create_user(self):
        """POST create a new user"""
        self.ensure_token()
        data = {"username": rand_name("user_"), "enabled": True}
        self.client.post(
            "/admin/realms/master/users",
            headers=self.headers,
            data=json.dumps(data),
            name="POST /users",
        )

    @task(2)
    def list_clients(self):
        """GET all clients"""
        self.ensure_token()
        self.client.get("/admin/realms/master/clients", headers=self.headers, name="GET /clients")

    @task(1)
    def create_client(self):
        """POST create a new client"""
        self.ensure_token()
        data = {
            "clientId": rand_name("client_"),
            "enabled": True,
            "publicClient": True,
        }
        self.client.post(
            "/admin/realms/master/clients",
            headers=self.headers,
            data=json.dumps(data),
            name="POST /clients",
        )

    @task(1)
    def list_roles(self):
        """GET all roles"""
        self.ensure_token()
        self.client.get("/admin/realms/master/roles", headers=self.headers, name="GET /roles")

    @task(1)
    def list_groups(self):
        """GET all groups"""
        self.ensure_token()
        self.client.get("/admin/realms/master/groups", headers=self.headers, name="GET /groups")
