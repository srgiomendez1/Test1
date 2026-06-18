# Los Reyes Quiniela Mundial 2026 ⚽

Rastreador de la quiniela del Mundial 2026 entre amigos. Sitio estático (sin
servidor, sin API key, gratis en GitHub Pages) que toma los resultados de los
partidos automáticamente, califica las predicciones de cada quien y muestra la
tabla de posiciones en vivo.

## Cómo funciona la puntuación

Reproduce exactamente la lógica del Excel (los dos criterios **se suman**):

| Acierto | Puntos |
|---|---|
| Acertar ganador o empate (resultado) | **+1** |
| Acertar el marcador exacto (incluye el resultado) | **+2** → **3 en total** |
| Fallar | 0 |

Los partidos **en vivo** suman puntos provisionales (se pueden incluir/excluir
con el switch en la tabla). Alcance: **fase de grupos** (72 partidos, 12
jugadores).

## Datos / Resultados

- **Base (siempre disponible):** [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
  — dominio público, sin API key, con CORS habilitado. Se actualiza durante el
  torneo.
- **En vivo (opcional):** se puede superponer un marcador en vivo definiendo la
  variable de repositorio `LIVE_SOURCE_URL` (una API pública sin key). Si no
  está disponible, el sitio sigue funcionando con la base.

`scripts/fetch_results.py` (ejecutado por GitHub Actions) normaliza todo a
`data/results.json`. El navegador lee ese archivo y, si falta, recurre
directamente a openfootball.

## Estructura

```
index.html                 # SPA en español
assets/js/scoring.js       # reglas de puntuación (probadas)
assets/js/data.js          # carga/merge de datos + fallback a openfootball
assets/js/app.js           # render de las 3 vistas
data/bets.json             # predicciones (generadas del Excel)
data/results.json          # resultados (commit del Action)
data/teams-es.json         # nombres en español + banderas
scripts/convert_bets.py    # Excel -> data/bets.json
scripts/fetch_results.py   # fuentes -> data/results.json
scripts/test_scoring.js    # node scripts/test_scoring.js
.github/workflows/         # update-results.yml (cron) + pages.yml (deploy)
```

## Actualizar las apuestas (nuevo Excel)

```bash
pip install openpyxl
python3 scripts/convert_bets.py "ruta/al/Concentrado.xlsx" -o data/bets.json
```

El script alinea los nombres en español con los de openfootball
(`scripts/team_aliases.py`) y respeta la orientación local/visitante de la
fuente oficial (voltea el marcador cuando el Excel lo tiene al revés). Avisa si
algún equipo o partido no se pudo mapear.

## Publicar en GitHub Pages

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. Hacer merge de esta rama a la rama por defecto (`main`). El workflow
   `pages.yml` publica el sitio en cada push.
3. (Opcional, en vivo) **Settings → Secrets and variables → Actions → Variables**
   → crear `LIVE_SOURCE_URL` con una API pública de marcadores en vivo.

> ⚠️ **Importante:** GitHub solo ejecuta workflows programados (`cron`) desde la
> **rama por defecto**. Para que `update-results.yml` corra cada 10 min, este
> archivo debe estar en `main`. Mientras tanto se puede correr a mano con
> **Actions → Update results → Run workflow**.

## Pruebas

```bash
node scripts/test_scoring.js      # reglas de puntuación
python3 -m http.server 8000       # abrir http://localhost:8000
```
