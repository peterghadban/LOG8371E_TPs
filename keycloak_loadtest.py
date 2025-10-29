'''Keycloak Load Test Script using Locust
To run, ensure you have Locust installed:
    pip install locust
Then start the docker container with Keycloak 26+ (no /auth prefix):
    docker-compose up -d
Finally, run the load test with:
    locust -f keycloak_loadtest.py --host=http://localhost:8080
'''


from locust import HttpUser, task, between
import json
import random
import string
import time
import threading

# ---------- Utility ----------
def rand_name(prefix):
    return prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

def random_bool():
    return random.choice([True, False])


# ---------- Shared Auth Token (thread-safe) ----------
shared_token = None
token_expiry = 0
lock = threading.Lock()

# ---------- CONFIG (set your Keycloak credentials here) ----------
KC_USERNAME = "admin"
KC_PASSWORD = "admin"
KC_REALM = "master"

def get_admin_token(client):
    """Request a new admin token from Keycloak 26+ (no /auth prefix)."""
    res = client.post(
        f"/realms/{KC_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KC_USERNAME,
            "password": KC_PASSWORD,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        name="Get admin token (shared)",
    )

    if res.status_code == 200:
        token_json = res.json()
        token = token_json.get("access_token", "")
        expires_in = token_json.get("expires_in", 60)
        expiry = time.time() + expires_in - 5
        print("[Auth] ✅ Obtained shared admin token.")
        return token, expiry
    else:
        print(f"[Auth] ❌ Failed ({res.status_code}): {res.text}")
        time.sleep(2)
        return None, 0


# ---------- Locust User ----------
class KeycloakUser(HttpUser):
    wait_time = between(1, 3)
    headers = {}

    created_users = []
    created_clients = []
    created_roles = []
    created_groups = []
    created_realms = []

    def ensure_token(self):
        """Ensure a valid shared token for all users."""
        global shared_token, token_expiry
        with lock:
            if not shared_token or time.time() > token_expiry:
                shared_token, token_expiry = get_admin_token(self.client)
        if shared_token:
            self.headers = {
                "Authorization": f"Bearer {shared_token}",
                "Content-Type": "application/json",
            }

    def think(self, action_type: str):
        """Simulate realistic human think time after actions."""
        ranges = {
            "create": (0.6, 1.8),
            "update": (0.8, 2.2),
            "delete": (0.5, 1.5),
            "misc":   (0.4, 1.2),
        }
        lo, hi = ranges.get(action_type, ranges["misc"])
        time.sleep(random.uniform(lo, hi))

    def on_start(self):
        """Authenticate once when a simulated user starts."""
        self.ensure_token()


    # ---------- CREATE ----------
    @task(1)
    def create_user(self):
        self.ensure_token()
        data = {"username": rand_name("user_"), "enabled": True}
        res = self.client.post(f"/admin/realms/{KC_REALM}/users",
                               headers=self.headers, data=json.dumps(data),
                               name="CREATE /users")
        if res.status_code in (201, 204):
            loc = res.headers.get("Location")
            if loc:
                user_id = loc.rstrip("/").split("/")[-1]
                self.created_users.append(user_id)
        self.think("create")

    @task(1)
    def create_client(self):
        self.ensure_token()
        data = {"clientId": rand_name("client_"), "enabled": True, "publicClient": True}
        res = self.client.post(f"/admin/realms/{KC_REALM}/clients",
                               headers=self.headers, data=json.dumps(data),
                               name="CREATE /clients")
        if res.status_code in (201, 204):
            loc = res.headers.get("Location")
            if loc:
                client_id = loc.rstrip("/").split("/")[-1]
                self.created_clients.append(client_id)
        self.think("create")

    @task(1)
    def create_role(self):
        self.ensure_token()
        role_name = rand_name("role_")
        data = {"name": role_name}
        res = self.client.post(f"/admin/realms/{KC_REALM}/roles",
                               headers=self.headers, data=json.dumps(data),
                               name="CREATE /roles")
        if res.status_code in (201, 204):
            self.created_roles.append(role_name)
        self.think("create")

    @task(1)
    def create_group(self):
        self.ensure_token()
        data = {"name": rand_name("group_")}
        res = self.client.post(f"/admin/realms/{KC_REALM}/groups",
                               headers=self.headers, data=json.dumps(data),
                               name="CREATE /groups")
        if res.status_code in (201, 204):
            loc = res.headers.get("Location")
            if loc:
                group_id = loc.rstrip("/").split("/")[-1]
                self.created_groups.append(group_id)
        self.think("create")

    # ---------- UPDATE ----------
    @task(1)
    def update_user(self):
        self.ensure_token()
        if self.created_users:
            user_id = random.choice(self.created_users)
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/{KC_REALM}/users/{user_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /users")
        self.think("update")

    @task(1)
    def update_client(self):
        self.ensure_token()
        if self.created_clients:
            client_id = random.choice(self.created_clients)
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/{KC_REALM}/clients/{client_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /clients")
        self.think("update")

    @task(1)
    def update_role(self):
        self.ensure_token()
        if self.created_roles:
            role_name = random.choice(self.created_roles)
            data = {"description": f"Updated {role_name}"}
            self.client.put(f"/admin/realms/{KC_REALM}/roles/{role_name}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /roles")
        self.think("update")

    @task(1)
    def update_group(self):
        self.ensure_token()
        if self.created_groups:
            group_id = random.choice(self.created_groups)
            data = {"name": f"{group_id}_updated"}
            self.client.put(f"/admin/realms/{KC_REALM}/groups/{group_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /groups")
        self.think("update")

    # ---------- DELETE ----------
    @task(1)
    def delete_user(self):
        self.ensure_token()
        if self.created_users:
            user_id = self.created_users.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/users/{user_id}",
                               headers=self.headers, name="DELETE /users")
        self.think("delete")

    @task(1)
    def delete_client(self):
        self.ensure_token()
        if self.created_clients:
            client_id = self.created_clients.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/clients/{client_id}",
                               headers=self.headers, name="DELETE /clients")
        self.think("delete")

    @task(1)
    def delete_role(self):
        self.ensure_token()
        if self.created_roles:
            role_name = self.created_roles.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/roles/{role_name}",
                               headers=self.headers, name="DELETE /roles")
        self.think("delete")

    @task(1)
    def delete_group(self):
        self.ensure_token()
        if self.created_groups:
            group_id = self.created_groups.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/groups/{group_id}",
                               headers=self.headers, name="DELETE /groups")
        self.think("delete")
