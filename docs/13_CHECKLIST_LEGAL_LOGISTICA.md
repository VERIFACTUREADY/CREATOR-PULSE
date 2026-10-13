# 13 · Checklist legal, logístico y de lanzamiento

**Leyenda:** 🔴 bloqueante sin resolver · 🟡 pendiente no bloqueante · ✅ hecho en el prototipo

> Cualquier casilla sanitaria crítica sin marcar = **NO-GO** (Estudio §20).

## Producto y regulación
- [ ] 🔴 Identidad y finalidad prevista del producto exacto confirmadas (DP-02)
- [ ] 🔴 Clase sanitaria y declaración UE de conformidad del modelo verificadas (DP-02)
- [ ] 🔴 Venta por internet en España permitida, incluido el análisis de «adaptación individualizada» del RD 192/2023 art. 24.5 (DP-01)
- [ ] 🔴 Fabricante, representante, importador, lotes y RECOPS aclarados (DP-03)
- [ ] 🔴 Sin private label que convierta al titular en fabricante (DP-04)
- [ ] 🔴 Instrucciones, indicaciones, límites, advertencias y materiales en castellano cotejados (DP-06)
- [ ] 🔴 Revisión sanitaria y publicitaria, con autorización art. 38 si aplica (DP-05)
- [x] ✅ Claims de mandíbula, corazón, apnea, rendimiento, humor y porcentajes bloqueados en la web (verificado por `claims-lint`)

## Comercio, fiscalidad y privacidad
- [ ] 🔴 Titular identificado: razón social, NIF y domicilio (DP-09)
- [ ] 🔴 Alta fiscal y Seguridad Social revisadas; tipo de IVA del SKU (DP-22)
- [ ] 🔴 Políticas de desistimiento, higiene (art. 103.e), garantías y reclamaciones aprobadas por la asesoría (DP-10)
- [ ] 🔴 Aviso legal, privacidad y cookies revisados; banner nativo de cookies configurado (DP-10, DP-17)
- [x] ✅ Sin datos de salud en formularios
- [x] ✅ Sin píxeles ni cookies de marketing en el tema

## Logística y finanzas
- [ ] 🔴 ≥2 cotizaciones del mismo modelo, con aduana e IVA aclarados y entrega trazable (DP-07)
- [ ] 🔴 Contribución prudente ≥ umbral (ver `05_ECONOMIA_UNITARIA.xlsx`)
- [ ] 🔴 Capital para pedidos, retrasos y devoluciones (DP-08)
- [ ] 🔴 Categoría admitida por la pasarela de pagos (DP-11)
- [ ] 🔴 Proveedor que responde al cuestionario de diligencia del Estudio §16.1 por escrito

## Tienda
- [x] ✅ Prototipo funcional en móvil, sin checkout (QA local, `10_QA_LANZAMIENTO.md`)
- [ ] 🔴 QA repetido dentro de Shopify (tienda de desarrollo con contraseña) (DP-18)
- [ ] 🔴 Checkout de prueba sin cargos reales y emails transaccionales en castellano revisados
- [ ] 🔴 Prueba real de garantía, producto dañado, reembolso y queja sanitaria
- [ ] 🔴 Materiales visuales con derechos de uso (DP-14)
- [ ] 🟡 Marca y dominio verificados en OEPM/EUIPO (DP-12)
- [ ] 🟡 Test de usabilidad con 5 personas (DP-20)

## Cierre
- [ ] 🔴 **Auditoría externa** del prototipo (contenido, legal, accesibilidad y seguridad)
- [ ] 🔴 `03_GO_NO_GO.md` completo, con evidencia en cada fila
- [ ] 🔴 Autorización expresa y por escrito del titular para el lanzamiento
