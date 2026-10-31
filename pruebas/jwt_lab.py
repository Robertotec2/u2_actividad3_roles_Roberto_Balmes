"""Ayudas de laboratorio para las pruebas: peticiones con token y un JWT vencido.

El token vencido se firma con el mismo JWT_SECRET del servidor (se lee del ambiente o de .env)
solo para probar que el servidor lo rechaza. No se usa en la API.
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import time
import urllib.request

URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")
MYSQL = os.getenv("MYSQL_CMD", "mysql -h127.0.0.1 -P3307 -uingresos -pingresos ingresos")
RAIZ = os.path.join(os.path.dirname(__file__), "..")


def gql(query, variables=None, token=None, operation=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"query": query, "variables": variables or {}}
    if operation:
        body["operationName"] = operation
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def dato(query, campo, token=None, variables=None):
    r = gql(query, variables, token)
    if r.get("errors"):
        raise SystemExit(f"Error preparando datos ({campo}): {r['errors'][0]['message']}")
    return r["data"][campo]


def error(r):
    return r["errors"][0]["message"] if r.get("errors") else None


def sql(consulta):
    out = subprocess.run(MYSQL.split() + ["-N", "-e", consulta], capture_output=True, text=True)
    return out.stdout.strip()


def login(email, password):
    return dato('mutation($e: String!, $p: String!) { login(input: {email: $e, password: $p}) { token } }',
                "login", variables={"e": email, "p": password})["token"]


def recortar(token):
    return token[:30] + "...(recortado)"


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def secreto():
    if os.getenv("JWT_SECRET"):
        return os.environ["JWT_SECRET"]
    for linea in open(os.path.join(RAIZ, ".env")):
        if linea.startswith("JWT_SECRET="):
            return linea.split("=", 1)[1].strip()
    raise SystemExit("Falta JWT_SECRET")


def token_vencido(company_user_id, company_id, hace_segundos=300):
    cab = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    datos = _b64(json.dumps({"companyUserId": company_user_id, "companyId": company_id,
                             "exp": int(time.time()) - hace_segundos}).encode())
    firma = hmac.new(secreto().encode(), f"{cab}.{datos}".encode(), hashlib.sha256).digest()
    return f"{cab}.{datos}.{_b64(firma)}"


def alterar(token):
    # cambia una letra de los datos: la firma ya no coincide
    cab, datos, firma = token.split(".")
    c = "A" if datos[5] != "A" else "B"
    return f"{cab}.{datos[:5]}{c}{datos[6:]}.{firma}"
