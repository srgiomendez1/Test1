# Pagos Tintorería Tauro

Página sencilla (un solo `index.html`, sin servidor) para calcular los pagos mensuales
de la venta de Tintorería Tauro, ligados a la tasa de **CETES a 28 días** de Banxico.

## Qué muestra
1. **Próximo pago**: monto, tasa usada y un menú para elegir otra tasa semanal (la más reciente, etc.).
2. **Adeudo**: pagos atrasados + interés por atraso, a la fecha de corte elegida.
3. **Tabla completa** de los 48 pagos; cada pago se puede marcar como recibido.

## Reglas (igual que el Excel "TABLA3 - Tintoreria Tauro pagos")
- Capital: 5,000,000 / 48 por mes. Interés: saldo × CETES / 12.
- Tasa: última subasta semanal de CETES 28 días del mes en que inicia el periodo.
- IVA 16% sobre (capital + interés); ISR retenido 1.25% de (capital + interés).
- Pagos 1 y 2 se dejan con las tasas que se cobraron (9.74% y 9.37%).

## Actualización automática
`.github/workflows/update-cetes.yml` (en la raíz del repo) corre `scripts/update_cetes.py` todas las noches a las 8 pm hora del Centro,
descarga la serie SF43936 de Banxico (sin token) y actualiza `data/cetes.json`.
La página trae las tasas también incluidas, por si el archivo no carga.

## Publicar
Settings → Pages → Deploy from branch → `main` / root.
