"""Muestra solo la parte del medio de un JWT (los datos legibles), sin la firma.

    python pruebas/ver_token.py TOKEN
"""
import base64
import json
import sys

partes = sys.argv[1].split(".")
datos = partes[1] + "=" * (-len(partes[1]) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(datos)), indent=2))
