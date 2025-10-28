from locust import HttpUser, task, between
import json
import random
import string
import time

# ---------- Utility ----------
def rand_name(prefix):
    """Generate a random name with a given prefix."""
    return prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

def random_bool():
    return random.choice([True, False])

# ---------- Locust User ----------
class KeycloakUser(HttpUser):
    wait_time = between(1, 3)
    token_expires_at = 0
    token = ""
    headers = {}

    # Store created resource IDs for update/delete
    created_users = []
    created_clients = []
    created_roles = []
    created_groups = []
    created_realms = []

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
            self.token_expires_at = time.time() + expires_in - 5
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        else:
            print(f"Auth failed: {res.status_code}, {res.text}")
            self.token = ""
            self.headers = {}

    def ensure_token(self):
        """Ensure a valid token before each task."""
        if time.time() > self.token_expires_at or not self.token:
            self.authenticate()

    def on_start(self):
        """Authenticate when a simulated user starts."""
        self.authenticate()

    # ---------- CREATE ----------
    @task(1)
    def create_user(self):
        self.ensure_token()
        data = {"username": rand_name("user_"), "enabled": True}
        res = self.client.post("/admin/realms/master/users", headers=self.headers, data=json.dumps(data), name="POST /users")
        if res.status_code in (201, 204):
            location = res.headers.get("Location")
            if location:
                user_id = location.rstrip("/").split("/")[-1]
                self.created_users.append(user_id)

    @task(1)
    def create_client(self):
        self.ensure_token()
        data = {"clientId": rand_name("client_"), "enabled": True, "publicClient": True}
        res = self.client.post("/admin/realms/master/clients", headers=self.headers, data=json.dumps(data), name="POST /clients")
        if res.status_code in (201, 204):
            location = res.headers.get("Location")
            if location:
                client_id = location.rstrip("/").split("/")[-1]
                self.created_clients.append(client_id)

    @task(1)
    def create_role(self):
        self.ensure_token()
        data = {"name": rand_name("role_")}
        res = self.client.post("/admin/realms/master/roles", headers=self.headers, data=json.dumps(data), name="POST /roles")
        if res.status_code in (201, 204):
            location = res.headers.get("Location")
            if location:
                role_id = location.rstrip("/").split("/")[-1]
                self.created_roles.append(role_id)

    @task(1)
    def create_group(self):
        self.ensure_token()
        data = {"name": rand_name("group_")}
        res = self.client.post("/admin/realms/master/groups", headers=self.headers, data=json.dumps(data), name="POST /groups")
        if res.status_code in (201, 204):
            location = res.headers.get("Location")
            if location:
                group_id = location.rstrip("/").split("/")[-1]
                self.created_groups.append(group_id)

    @task(1)
    def create_realm(self):
        self.ensure_token()
        data = {"realm": rand_name("realm_"), "enabled": True}
        res = self.client.post("/admin/realms", headers=self.headers, data=json.dumps(data), name="POST /realms")
        if res.status_code in (201, 204):
            location = res.headers.get("Location")
            if location:
                realm_id = location.rstrip("/").split("/")[-1]
                self.created_realms.append(realm_id)

    # ---------- UPDATE ----------
    @task(1)
    def update_user(self):
        self.ensure_token()
        if self.created_users:
            user_id = random.choice(self.created_users)
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/master/users/{user_id}", headers=self.headers, data=json.dumps(data), name="PUT /users")

    @task(1)
    def update_client(self):
        self.ensure_token()
        if self.created_clients:
            client_id = random.choice(self.created_clients)
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/master/clients/{client_id}", headers=self.headers, data=json.dumps(data), name="PUT /clients")

    @task(1)
    def update_role(self):
        self.ensure_token()
        if self.created_roles:
            role_id = random.choice(self.created_roles)
            data = {"description": f"Updated role {role_id}"}
            self.client.put(f"/admin/realms/master/roles/{role_id}", headers=self.headers, data=json.dumps(data), name="PUT /roles")

    @task(1)
    def update_group(self):
        self.ensure_token()
        if self.created_groups:
            group_id = random.choice(self.created_groups)
            data = {"name": f"{group_id}_updated"}
            self.client.put(f"/admin/realms/master/groups/{group_id}", headers=self.headers, data=json.dumps(data), name="PUT /groups")

    @task(1)
    def update_realm(self):
        self.ensure_token()
        if self.created_realms:
            realm_id = random.choice(self.created_realms)
            data = {"displayName": f"Updated {realm_id}"}
            self.client.put(f"/admin/realms/{realm_id}", headers=self.headers, data=json.dumps(data), name="PUT /realms")

    # ---------- DELETE ----------
    @task(1)
    def delete_user(self):
        self.ensure_token()
        if self.created_users:
            user_id = self.created_users.pop()
            self.client.delete(f"/admin/realms/master/users/{user_id}", headers=self.headers, name="DELETE /users")

    @task(1)
    def delete_client(self):
        self.ensure_token()
        if self.created_clients:
            client_id = self.created_clients.pop()
            self.client.delete(f"/admin/realms/master/clients/{client_id}", headers=self.headers, name="DELETE /clients")

    @task(1)
    def delete_role(self):
        self.ensure_token()
        if self.created_roles:
            role_id = self.created_roles.pop()
            self.client.delete(f"/admin/realms/master/roles/{role_id}", headers=self.headers, name="DELETE /roles")

    @task(1)
    def delete_group(self):
        self.ensure_token()
        if self.created_groups:
            group_id = self.created_groups.pop()
            self.client.delete(f"/admin/realms/master/groups/{group_id}", headers=self.headers, name="DELETE /groups")

    @task(1)
    def delete_realm(self):
        self.ensure_token()
        if self.created_realms:
            realm_id = self.created_realms.pop()
            self.client.delete(f"/admin/realms/{realm_id}", headers=self.headers, name="DELETE /realms")
