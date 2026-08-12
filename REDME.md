# Balance General (Comité) — Power BI

## Objetivo

Construir un reporte de Power BI que muestre el **Balance General** de la compañía bajo la clasificación de **Comité**, distinta del catálogo de cuentas nativo de NetSuite.

## Fuentes de información

El proyecto depende de varios insumos brindados por el área contable:

- **[Mapeo Balance General Comite-Netsuite](https://docs.google.com/spreadsheets/d/1-qkcgiDrKz8Xo21B75GCiJtTm89FCjmqUagy8u_THVg/edit?gid=0#gid=0)** (Google Sheet, pestaña `Mapeo`). Contiene dos mapeos del balance general; para este proyecto se implementa únicamente el de **Comité**. Cruza el número de cuenta de NetSuite con la jerarquía de 3 niveles de NetSuite (`L1/L2/L3_Netsuite`) y la jerarquía de 3 niveles de Comité (`L1/L2/L3_Comite`).
- **Catálogo de cuentas de NetSuite** — se consulta en vivo vía ODBC (Oracle/NetSuite) desde la tabla `Account`, para resolver los IDs de cuenta correspondientes a cada fila del mapeo anterior.
- **Balances de NetSuite** — agregación mensual de `transactionLine` / `TransactionAccountingLine` por cuenta, periodo contable y subsidiaria, filtrada a las cuentas resueltas en el mapeo.
- **[Reclasificaciones contables](https://docs.google.com/spreadsheets/d/1R_iFnlj-cIOlDPBL0af3fbSIL2a1E47QIRM6ZOkhyYg/edit?gid=642561501#gid=642561501)** (Google Sheet, pestaña `data autos propiedad`). Reclasificación manual que el área contable realiza fuera de NetSuite (actualmente solo "Activo por derecho de uso vehículos").

El catálogo de mapeo Comité-NetSuite se administra mediante un gestor de cuentas desarrollado internamente por el Gerente de Data Analytics: [Sheet Manager](https://script.google.com/a/macros/avis.com.mx/s/AKfycbxsy4Ix4DPU09eV3Gx2-dppjjPf3KEigMJq9ZnzuXuL-VrxpRrdXDiXu7fRlKZGS0XH/exec).

## El problema a resolver

El balance de Comité requiere incorporar la reclasificación manual de contabilidad, la cual **solo existe en el Google Sheet mencionado**, sin ningún tipo de estructura o identificador que la ligue al catálogo de cuentas. Esto genera dos dilemas:

1. **Falta de almacenamiento estructurado** — la información vive en un sheet de uso manual y depende de que el área contable la mantenga actualizada; no hay una fuente de sistema para ella.
2. **Ausencia de identificadores contables** — al ser un ajuste manual, el sheet no registra IDs de cuenta ni periodo contable de forma explícita; hay que derivarlos.

## Solución (etapa actual)

De manera provisional se construyó un ETL que:

1. Extrae la información del sheet de reclasificaciones.
2. Deriva montos mensuales a partir de los saldos acumulados de la pestaña (`.diff()`).
3. Asigna manualmente el reporte (`FK_Reporte`) y el par de cuentas (activo/contra-activo) correspondiente.
4. Carga el resultado (reemplazo total, delete-then-append) a la tabla `Netsuite.ReclasificacionesContables` en el servidor `DW-GOMEX`, base `RAW_NS`.

La lógica de referencia está prototipada en el notebook [`test/BalanceGeneralPruebas.ipynb`](test/BalanceGeneralPruebas.ipynb), en la sección **"Activo por derecho de uso vehículos"**, que ejemplifica cómo leer, transformar y subir los datos. Este notebook es la implementación de referencia que aún debe portarse a `src/` para productivizarse (ver [CLAUDE.md](CLAUDE.md)).

La estructura de la tabla destino está definida en [`src/tablas.sql`](src/tablas.sql):

```sql
create table Netsuite.ReclasificacionesContables (
    FK_Reporte      int,
    PeriodoContable date,
    IdCuenta        int,
    Monto           float,
    Nota            nvarchar(max)
)
```

## Estado

Solo el paso de reclasificaciones manuales (punto 4 arriba) está automatizado hacia SQL Server. El resto del flujo (mapeo Comité-NetSuite + balances de NetSuite) hoy solo produce un Excel de validación (`Resumen.xlsx`) y aún no está integrado al pipeline de carga. Ver [CLAUDE.md](CLAUDE.md) para el detalle técnico de arquitectura, variables de entorno y cómo ejecutar el notebook.







