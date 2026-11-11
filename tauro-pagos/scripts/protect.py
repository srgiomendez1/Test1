#!/usr/bin/env python3
"""Cifra (o descifra) la página con contraseña.

La página publicada (index.html) solo contiene el contenido cifrado con AES-256-GCM.
La llave se deriva de la contraseña con PBKDF2-SHA256; la contraseña no se guarda en ningún lado.

  Cifrar:    TAURO_PASSWORD=... python scripts/protect.py encrypt app.html index.html
  Descifrar: TAURO_PASSWORD=... python scripts/protect.py decrypt index.html app.html

Mantenga app.html (el original sin cifrar) FUERA del repositorio.
Requiere: pip install cryptography
"""
import base64
import json
import os
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 310_000
GATE = Path(__file__).resolve().parent / "gate.html"
MARK = re.compile(r'<script id="payload" type="application/json">(.*?)</script>', re.S)


def key_for(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


def password() -> str:
    pw = os.environ.get("TAURO_PASSWORD")
    if not pw:
        raise SystemExit("Defina TAURO_PASSWORD con la contraseña.")
    return pw


def encrypt(src: Path, out: Path) -> None:
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(key_for(password(), salt)).encrypt(iv, src.read_bytes(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    payload = json.dumps({"v": 1, "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)})
    gate = GATE.read_text(encoding="utf-8")
    out.write_text(MARK.sub(lambda m: f'<script id="payload" type="application/json">{payload}</script>', gate),
                   encoding="utf-8")
    print(f"Cifrado: {out} ({len(ct):,} bytes)")


def decrypt(src: Path, out: Path) -> None:
    p = json.loads(MARK.search(src.read_text(encoding="utf-8")).group(1))
    d = lambda k: base64.b64decode(p[k])
    out.write_bytes(AESGCM(key_for(password(), d("salt"))).decrypt(d("iv"), d("ct"), None))
    print(f"Descifrado: {out}")


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("encrypt", "decrypt"):
        raise SystemExit(__doc__)
    (encrypt if sys.argv[1] == "encrypt" else decrypt)(Path(sys.argv[2]), Path(sys.argv[3]))
