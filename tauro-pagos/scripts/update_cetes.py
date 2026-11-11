#!/usr/bin/env python3
"""Descarga la tasa de CETES a 28 días (subasta semanal) de Banxico y la guarda en data/cetes.json.

Usa la exportación CSV pública del SIE de Banxico (cuadro CF107, serie SF43936).
No requiere token. Solo usa la biblioteca estándar de Python.
"""
import datetime as dt
import json
import pathlib
import urllib.parse
import urllib.request

URL = "https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarSeries"
SERIE = "SF43936"
DESDE = "2024-12-01"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "cetes.json"


def descargar():
    hoy = dt.date.today()
    form = {
        "idCuadro": "CF107", "sector": "22", "version": "3", "locale": "es",
        "series": SERIE, "anoInicial": "2024", "anoFinal": str(hoy.year),
        "tipoInformacion": "", "metadatosWeb": "true",
        "formatoCSV.x": "1", "formatoCSV.y": "1",
    }
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(form).encode(),
                                 headers={"User-Agent": "cetes-updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        texto = r.read().decode("latin-1")
    datos = []
    for linea in texto.splitlines():
        partes = linea.strip().split(",")
        if len(partes) != 2 or not partes[0][:2].isdigit():
            continue
        try:
            fecha = dt.datetime.strptime(partes[0], "%d/%m/%Y").date().isoformat()
            tasa = float(partes[1])
        except ValueError:
            continue  # "N/E" u otros valores no numéricos
        if fecha >= DESDE:
            datos.append([fecha, tasa])
    if len(datos) < 50:
        raise SystemExit(f"Respuesta inesperada de Banxico ({len(datos)} filas); no se actualiza.")
    return datos


def main():
    datos = descargar()
    previo = json.loads(OUT.read_text()) if OUT.exists() else {}
    if previo.get("datos") == datos:
        print("Sin cambios.")
        return
    OUT.write_text(json.dumps({
        "fuente": "Banxico SIE, serie SF43936 (Cetes 28 dias, tasa de rendimiento, subasta semanal)",
        "actualizado": dt.date.today().isoformat(),
        "datos": datos,
    }, indent=0))
    print(f"Actualizado: {len(datos)} tasas, última {datos[-1]}")


if __name__ == "__main__":
    main()
