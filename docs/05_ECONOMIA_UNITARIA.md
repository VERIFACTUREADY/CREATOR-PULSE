# 05 · Economía unitaria

**Archivo editable:** `05_ECONOMIA_UNITARIA.xlsx` (hojas Leyenda · Supuestos · Escenarios · Sensibilidad; 55 fórmulas, 0 errores tras recalcular).
Las celdas **amarillas con texto azul** se editan. La columna **REAL** está vacía a propósito: solo se rellena con cotizaciones firmadas.

## Fórmula (Estudio §9.2)

`Contribución = PVP / (1 + IVA) − coste completo puesto en cliente − reserva de incidencias − (PVP × comisión % + comisión fija)`

## Resultados con los supuestos de los informes (todos HIPOTÉTICOS)

| Escenario | PVP | Coste | Reserva | Comisión | Contribución | ¿≥ 7 €? | Tras CAC 10 € | Pedidos con 50 € |
|---|---:|---:|---:|---:|---:|:-:|---:|---:|
| 1. Desfavorable | 24,90 € | 16,00 € | 3,00 € | 1,02 € | **0,56 €** | NO | −9,44 € | 3 |
| 2. Base | 29,90 € | 14,00 € | 2,50 € | 1,17 € | **7,04 €** | Sí, por 4 céntimos | −2,96 € | 3 |
| 3. Mejor logística | 29,90 € | 10,00 € | 2,00 € | 1,17 € | **11,54 €** | Sí | 1,54 € | 5 |
| 4. PVP superior | 34,90 € | 14,00 € | 2,50 € | 1,31 € | **11,03 €** | Sí | 1,03 € | 3 |
| 5. Ejemplo del Maestro | 29,90 € | 14,40 € | 2,00 € | 1,17 € | **7,14 €** | Sí, por 14 céntimos | −2,86 € | 3 |

He recalculado las cinco filas y coinciden con los informes, así que no hay errores aritméticos.

## Lectura

1. **Con publicidad de pago, todos los escenarios realistas pierden dinero.** Con un CAC de 10 €, el caso base y el del Maestro son negativos.
2. **El caso base supera el umbral por solo 4 céntimos.** El umbral recomendado está entre 7 y 8 €, así que por encima de 7,04 € está en la zona de riesgo.
3. **50 € financian 3 pedidos** si el proveedor cobra al momento (Shopify liquida en ≥3 días hábiles, S27).
4. **Competencia a 19,99–24,19 €.** Vender a 29,90 € exige una diferencia comprobable. Una web más clara no basta (Estudio §5.1).
5. No hay recompra: el producto es reutilizable. No modelar suscripciones.

## Qué falta para que esta hoja sea útil (DP-07, DP-11, DP-22)

- Dos o más cotizaciones firmadas a un código postal español, con DDP o desglose de aranceles, IVA de importación y el derecho de 3 € (S28).
- La tarifa real de pago para vuestro plan y país.
- El tipo de IVA del producto y quién es el importador legal.
