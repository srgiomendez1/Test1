# Calculadora de pagos (privada)

`index.html` está **cifrado** (AES-256-GCM, llave derivada de la contraseña con PBKDF2-SHA256).
Sin la contraseña solo se ve una pantalla para escribirla; la contraseña no se guarda en este repositorio.

## Editar la página
1. Descifrar:  `TAURO_PASSWORD=... python scripts/protect.py decrypt index.html /ruta/fuera/del/repo/app.html`
2. Editar `app.html` (fuera del repositorio; nunca lo suba sin cifrar).
3. Cifrar:     `TAURO_PASSWORD=... python scripts/protect.py encrypt /ruta/fuera/del/repo/app.html index.html`

Requiere `pip install cryptography`. Cada vez que se vuelve a cifrar, los aparatos que tenían
la contraseña recordada la piden una vez más.

## Tasas CETES
`.github/workflows/update-cetes.yml` (en la raíz del repo) corre `scripts/update_cetes.py` todas las noches
a las 8 pm hora del Centro, descarga la serie SF43936 de Banxico (dato público, sin token) y actualiza
`data/cetes.json`, que la página lee después de abrirse.
