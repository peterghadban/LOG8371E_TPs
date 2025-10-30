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
        expiry = time.time() + 15
        print("[Auth] ✅ Obtained shared admin token.")
        return token, expiry
    else:
        print(f"[Auth] ❌ Failed ({res.status_code}): {res.text}")
        time.sleep(2)
        return None, 0


# ---------- Locust User ----------
class KeycloakUser(HttpUser):
    wait_time = between(1, 3) # Modify random think time here
    headers = {}

    created_users = []
    created_clients = []
    created_roles = []
    created_groups = []
    created_realms = []

    to_delete_users = []
    to_delete_clients = []
    to_delete_roles = []
    to_delete_groups = []


    def ensure_token(self):
        """Ensure a valid shared token for all users."""
        global shared_token, token_expiry
        if not shared_token or time.time() > token_expiry:
            with lock:
                if not shared_token or time.time() > token_expiry:
                    shared_token, token_expiry = get_admin_token(self.client)
        if shared_token:
            self.headers = {
                "Authorization": f"Bearer {shared_token}",
                "Content-Type": "application/json",
            }

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

    @task(1)
    def create_role(self):
        self.ensure_token()
        role_name = rand_name("role_")
        data = {"name": role_name}
        
        res = self.client.post(
            f"/admin/realms/{KC_REALM}/roles",
            headers=self.headers,
            data=json.dumps(data),
            name="CREATE /roles"
        )
        
        if res.status_code in (201, 204):
            self.created_roles.append(role_name)

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

    # ---------- UPDATE ----------
    @task(1)
    def update_user(self):
        self.ensure_token()
        if self.created_users:
            user_id = self.created_users.pop()
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/{KC_REALM}/users/{user_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /users")
            self.to_delete_users.append(user_id)

    @task(1)
    def update_client(self):
        self.ensure_token()
        if self.created_clients:
            client_id = self.created_clients.pop()
            data = {"enabled": random_bool()}
            self.client.put(f"/admin/realms/{KC_REALM}/clients/{client_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /clients")
            self.to_delete_clients.append(client_id)
            

    @task(1)
    def update_role(self):
        self.ensure_token()
        if self.created_roles:
            role_name = self.created_roles.pop()

            res = self.client.get(
                f"/admin/realms/{KC_REALM}/roles/{role_name}",
                headers=self.headers,
                name="GET /roles"
            )
            if res.status_code == 200:
                role_data = res.json()
                # Modify description (or any field you want)
                role_data["description"] = f"Updated {role_name}"

                # Send full valid payload
                self.client.put(
                    f"/admin/realms/{KC_REALM}/roles/{role_name}",
                    headers=self.headers,
                    data=json.dumps(role_data),
                    name="UPDATE /roles"
                )

                self.to_delete_roles.append(role_name)

    @task(1)
    def update_group(self):
        self.ensure_token()
        if self.created_groups:
            group_id = self.created_groups.pop()
            data = {"name": f"{group_id}_updated"}
            self.client.put(f"/admin/realms/{KC_REALM}/groups/{group_id}",
                            headers=self.headers, data=json.dumps(data),
                            name="UPDATE /groups")
            self.to_delete_groups.append(group_id)

    # ---------- DELETE ----------
    @task(1)
    def delete_user(self):
        self.ensure_token()
        if self.to_delete_users:
            user_id = self.to_delete_users.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/users/{user_id}",
                               headers=self.headers, name="DELETE /users")

    @task(1)
    def delete_client(self):
        self.ensure_token()
        if self.to_delete_clients:
            client_id = self.to_delete_clients.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/clients/{client_id}",
                               headers=self.headers, name="DELETE /clients")

    @task(1)
    def delete_role(self):
        self.ensure_token()
        if self.to_delete_roles:
            role_name = self.to_delete_roles.pop()

            self.client.delete(f"/admin/realms/{KC_REALM}/roles/{role_name}",
                               headers=self.headers, name="DELETE /roles")

    @task(1)
    def delete_group(self):
        self.ensure_token()
        if self.to_delete_groups:
            group_id = self.to_delete_groups.pop()
            self.client.delete(f"/admin/realms/{KC_REALM}/groups/{group_id}",
                               headers=self.headers, name="DELETE /groups")
