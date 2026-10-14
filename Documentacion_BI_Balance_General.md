# BI Balance General — Documentación interna
## Contenido

- [BI Balance General — Documentación interna](#bi-balance-general--documentación-interna)
  - [Contenido](#contenido)
  - [1. Vista general del modelo](#1-vista-general-del-modelo)
    - [Relaciones activas](#relaciones-activas)
  - [2. Dim\_Cuentas](#2-dim_cuentas)
    - [Tablas del DW que usa la consulta](#tablas-del-dw-que-usa-la-consulta)
    - [Consulta SQL](#consulta-sql)
    - [Qué hace la consulta, paso a paso](#qué-hace-la-consulta-paso-a-paso)
    - [Estructura resultante](#estructura-resultante)
  - [3. Fac\_Netsuite](#3-fac_netsuite)
  - [4. Fac\_Ajustes](#4-fac_ajustes)
  - [5. FacNetsuiteConsolidado](#5-facnetsuiteconsolidado)
  - [6. Medida principal: Balance\_General\_YTD](#6-medida-principal-balance_general_ytd)
    - [Medida de apoyo: Monto\_Balance](#medida-de-apoyo-monto_balance)
    - [Código de la medida](#código-de-la-medida)
    - [Cómo leerla](#cómo-leerla)
  - [7. Nota importante: separación de Resultado del ejercicio y Resultados Acumulados](#7-nota-importante-separación-de-resultado-del-ejercicio-y-resultados-acumulados)
    - [La solicitud](#la-solicitud)
    - [El problema](#el-problema)
    - [Cómo se resolvió](#cómo-se-resolvió)
    - [Consecuencias](#consecuencias)
  - [8. Opcional: Dim\_L1, Dim\_L2 y Dim\_L3](#8-opcional-dim_l1-dim_l2-y-dim_l3)
    - [Fórmulas DAX](#fórmulas-dax)
    - [Relaciones](#relaciones)
    - [Configuración adicional](#configuración-adicional)

---

## 1. Vista general del modelo

```
NetSuite (ODBC) ──► Fac_Netsuite ─┐
                                  ├─► FacNetsuiteConsolidado ──► Dim_Cuentas ──► Dim_L3 ──► Dim_L2 ──► Dim_L1
DW RAW_NS ────────► Fac_Ajustes ──┘            │
                                               └──────────────► Dim_Tiempo
DW RAW_NS ────────► Dim_Cuentas
```

| Tabla | Tipo | Origen | Para qué sirve |
|---|---|---|---|
| `Dim_Cuentas` | Dimensión (SQL) | `DWH1-GOMEX` / `RAW_NS` | Catálogo de cuentas con su jerarquía L1/L2/L3 del balance corporativo |
| `Fac_Netsuite` | Hechos (ODBC) | NetSuite, DSN `NetsuiteDSN` | Movimiento mensual neto por cuenta |
| `Fac_Ajustes` | Hechos (SQL) | `DWH1-GOMEX` / `RAW_NS` | Reclasificaciones manuales de contabilidad |
| `FacNetsuiteConsolidado` | Hechos (tabla calculada DAX) | Unión de las dos anteriores | **Única tabla de hechos que usan las medidas** |
| `Dim_Tiempo` | Dimensión (tabla calculada DAX) | Rango de fechas de `Fac_Netsuite` | Calendario del reporte |
| `Dim_L1`, `Dim_L2`, `Dim_L3` | Dimensiones (tablas calculadas DAX) | Derivadas de `Dim_Cuentas` | Niveles de la matriz (ver sección 8) |
| `Dim_Unidades` | Tabla manual | Capturada en el pbix | Selector de unidades: $1, $000's, $Millones |

### Relaciones activas

| Desde (muchos) | Hacia (uno) | Filtro |
|---|---|---|
| `FacNetsuiteConsolidado[IdCuenta]` | `Dim_Cuentas[Internal_Id]` | Una dirección |
| `FacNetsuiteConsolidado[startdate]` | `Dim_Tiempo[Date]` | Una dirección |
| `Dim_Cuentas[L3]` | `Dim_L3[L3]` | Una dirección |
| `Dim_L3[L2]` | `Dim_L2[L2]` | Una dirección |
| `Dim_L2[L1]` | `Dim_L1[L1]` | Una dirección |

`Fac_Netsuite` y `Fac_Ajustes` **no** se relacionan con las dimensiones: solo alimentan a `FacNetsuiteConsolidado`.

---

## 2. Dim_Cuentas

Catálogo de cuentas contables con la jerarquía de 3 niveles del balance corporativo. Una fila por cuenta.

| Columna | Descripción |
|---|---|
| `Internal_Id` | ID interno de la cuenta en NetSuite. Llave contra los hechos |
| `Account` | Número de cuenta |
| `Acc-Name` | Número + nombre (`Number-Account`) |
| `Description` | Nombre de la cuenta |
| `L1`, `L2`, `L3` | Rubros de la jerarquía. Se ordenan por `Orden L1`, `Orden L2`, `Orden L3` |
| `Orden L1`, `Orden L2`, `Orden L3` | Posición de cada rubro en el reporte |
| `Tem` | Columna calculada DAX. Marca con 1 nueve cuentas de impuestos (292xx). Solo se usa como filtro en la página de validación `ValMontos` |

### Tablas del DW que usa la consulta

| Tabla | Contenido |
|---|---|
| `Netsuite.Accounts` | Catálogo de cuentas de NetSuite |
| `Netsuite.Accounts_Levels` | Rubros de cada reporte, con su padre (`ID_Padre`), nivel (`Nivel`) y posición (`Orden`) |
| `Netsuite.Accounts_ReportMapping` | Qué cuenta (`Internal_Id`) cae en qué rubro base (`FK_PL_Nivel_Base`) de cada reporte (`FK_Reporte`) |

Reportes relevantes en `FK_Reporte`: `5` = Balance Corporativo (el de este pbix), `3` = Estado de Resultados (P&L), `2` = Balance Comité (versión anterior).

### Consulta SQL

Servidor `DWH1-GOMEX`, base `RAW_NS`. Es el tercer bloque de [src/tablas.sql](src/tablas.sql).

```sql
---BI Balance--- CORPORATIVO (ARIETE+BRM+CARFIX)
DECLARE @FK_ReporteBalance INT = 5;
DECLARE @FK_ReportePyL INT = 3;
DECLARE @ID_Rubro_ResultadosEjercicio INT = 245;
;With Cuentas as (
	select c.*
	from Netsuite.Accounts c
),
Niveles as (
	select
	--LEVEL1
	l1.Orden OrdenL1,l1.Nombre_Rubro L1,
	--LEVEL2
	DENSE_RANK() OVER (ORDER BY l1.Orden ASC, l1.ID_Rubro, l2.Orden ASC, l2.ID_Rubro) AS OrdenL2,
	l2.Orden PoscicionL2,l2.Nombre_Rubro L2,
	--LEVEL3
	ROW_NUMBER() OVER (ORDER BY l1.Orden ASC, l2.Orden ASC, l3.Orden ASC) AS OrdenL3,
	l3.Orden PoscicionL3,l3.Nombre_Rubro L3, l3.ID_Rubro,l3.FK_Reporte
	from Netsuite.Accounts_Levels l3
	--L2
	join Netsuite.Accounts_Levels l2 on l3.ID_Padre=l2.ID_Rubro and l3.FK_Reporte=l2.FK_Reporte
	--L1
	join Netsuite.Accounts_Levels l1 on l2.ID_Padre=l1.ID_Rubro and l2.FK_Reporte=l1.FK_Reporte
	--Filtramos para tener el reporte que nos interesa dados el nivel inferior
	where l3.FK_Reporte= @FK_ReporteBalance and l3.Nivel=3
),
--Mapeo de Cuentas de P&L para el rubro de Resultados del Ejercicio (ID_Rubro 245) del balance
MapeoBalance as (
	select m.*
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=@FK_ReporteBalance
	union all
	select  m.Internal_Id, @FK_ReporteBalance FK_Reporte , @ID_Rubro_ResultadosEjercicio FK_PL_Nivel_Base
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=3--@FK_ReportePyL
	union all
	select 276000 Internal_Id, @FK_ReporteBalance FK_Reporte, 95 FK_PL_Nivel_Base
	union all
	select 276001 Internal_Id, @FK_ReporteBalance FK_Reporte, 93 FK_PL_Nivel_Base
)
--Balance
select a.Internal_Id,a.Number Account,a.Number+'-'+a.Account [Acc-Name] ,a.Account Description,
n.L1,n.L2,n.L3,n.OrdenL1 [Orden L1],n.OrdenL2 [Orden L2] , n.OrdenL3 [Orden L3]
from MapeoBalance m
join Cuentas a on m.Internal_Id=a.Internal_Id
join Niveles n on m.FK_PL_Nivel_Base=n.ID_Rubro and m.FK_Reporte=n.FK_Reporte
union all
--Traspaso: toma los Orden L1/L2/L3 del rubro real Resultados Acumulados
select top 1 99989,NULL,'Traspaso Resultados Ejercicios Anteriores','Traspaso Resultados Ejercicios Anteriores',n.L1,n.L2,n.L3,n.OrdenL1,n.OrdenL2,n.OrdenL3
from Niveles n
where n.L1='Capital Contable' and n.L3='Resultados Acumulados'
union all
select 99990,NULL,NULL,'Pasivo+Capital','Pasivo+Capital',NULL,NULL,98,998,9998
union all
select 99991,NULL,NULL,'Diferencia de Balance','Diferencia de Balance',NULL,NULL,99,999,9999
```


### Qué hace la consulta, paso a paso

1. **`Niveles`** arma la jerarquía L1 → L2 → L3 del reporte 5 uniendo `Accounts_Levels` consigo misma por `ID_Padre`, y calcula un orden global para L2 y L3.
2. **`MapeoBalance`** toma el mapeo cuenta → rubro del balance y le agrega **todas las cuentas del Estado de Resultados** (`FK_Reporte = 3`), asignándolas al rubro `245` = "Resultado del ejercicio, neto". Así el resultado del ejercicio se calcula desde las cuentas de ingresos y gastos, sin depender de un asiento de cierre.
3. El `select` final cruza mapeo, cuentas y niveles.
4. Se agregan **tres filas sintéticas** que no existen en NetSuite:

| `Internal_Id` | Fila | Para qué |
|---|---|---|
| `99989` | Traspaso Resultados Ejercicios Anteriores | Muestra, a nivel cuenta, la utilidad de años anteriores dentro de Resultados Acumulados (ver sección 7) |
| `99990` | Pasivo+Capital | Renglón de total. Su valor lo calcula la medida |
| `99991` | Diferencia de Balance | Renglón de cuadre (Activo − Pasivo − Capital). Su valor lo calcula la medida |

Estas filas no tienen movimientos en los hechos; solo existen para que la matriz tenga dónde pintar el valor.

### Estructura resultante

| L1 | L2 | Rubros L3 |
|---|---|---|
| Activo | Activo Circulante | 11 |
| Activo | Activo no Circulante | 9 |
| Pasivo | Pasivo circulante | 12 |
| Pasivo | Pasivo no Circulante | 7 |
| Capital Contable | Capital Social | 1 |
| Capital Contable | Reserva Legal | 1 |
| Capital Contable | Resultados Acumulados | 1 |
| Capital Contable | Resultado del ejercicio, neto | 1 |
| Pasivo+Capital | — | — |
| Diferencia de Balance | — | — |

---

## 3. Fac_Netsuite

Movimiento neto mensual por cuenta, leído directo de NetSuite por ODBC (DSN `NetsuiteDSN`, driver `NetSuite Drivers 64bit`).

| Columna | Descripción |
|---|---|
| `IdCuenta` | ID interno de la cuenta (`expenseaccount`) |
| `startdate` | Primer día del periodo contable |
| `Net` | Suma del importe contabilizado en el periodo (movimiento del mes, **no** saldo acumulado) |

```sql
select d.expenseaccount IdCuenta, p.startdate, sum(al.amount) Net
from transactionLine d
left outer join transaction t on t.id = d.transaction
left outer join accountingPeriod p on t.postingperiod = p.id
--AccountingLine
left outer join TransactionAccountingLine al on d.id = al.transactionline and d.transaction = al.transaction
left outer join Account a on d.expenseaccount = a.id
where d.subsidiary = 2 and t.posting = 'T'
group by d.expenseaccount, p.startdate
```

Puntos a tener en cuenta:

- Filtra `subsidiary = 2` y solo transacciones contabilizadas (`posting = 'T'`).
- Trae **todas** las cuentas y todos los periodos; el filtro de qué cuentas entran al balance lo hace la relación con `Dim_Cuentas`.
- Los montos vienen con el signo natural de NetSuite (pasivo y capital en negativo). La medida `Monto_Balance` los voltea.

---

## 4. Fac_Ajustes

Reclasificaciones manuales que contabilidad lleva en Google Sheets y que no existen en NetSuite. Las carga el ETL [src/main.py](src/main.py) a la tabla `Netsuite.ReclasificacionesContables`.

| Columna | Descripción |
|---|---|
| `IdCuenta` | ID interno de la cuenta afectada |
| `starddate` | Periodo contable (primer día del mes). Ojo: el nombre lleva una "d" de más; así está en el pbix |
| `Net` | Movimiento del mes |

```sql
select r.IdCuenta, r.PeriodoContable starddate, r.Monto Net
from Netsuite.ReclasificacionesContables r
where FK_Reporte = 5
```

Puntos a tener en cuenta:

- `FK_Reporte = 5` trae solo los ajustes del balance corporativo.
- El ETL ya convierte los saldos acumulados de la hoja en movimientos mensuales, por lo que la tabla tiene la misma forma que `Fac_Netsuite`.
- El ETL está pensado para que los ajustes cuadren en partida doble (la suma de movimientos por periodo debe ser cero), de modo que no descuadren el balance.
- El ETL incluye una "Cancelación global" fechada en agosto 2026 que revierte lo acumulado de cada cuenta: a partir de ese mes el efecto neto de los ajustes es cero.

Estructura de la tabla destino:

```sql
create table Netsuite.ReclasificacionesContables (
    FK_Reporte      int,
    PeriodoContable date,
    IdCuenta        int,
    Monto           float,
    Nota            nvarchar(max)
)
```

---

## 5. FacNetsuiteConsolidado

Tabla calculada que apila `Fac_Netsuite` y `Fac_Ajustes` en una sola tabla de hechos. **Es la única tabla de hechos relacionada con las dimensiones y la única que usan las medidas.**

```dax
FacNetsuiteConsolidado =
UNION(
    SELECTCOLUMNS(
        Fac_Netsuite,
        "IdCuenta", Fac_Netsuite[IdCuenta],
        "startdate", Fac_Netsuite[startdate],
        "Net", Fac_Netsuite[Net],
        "Origen_Dato", "Netsuite"
    ),
    SELECTCOLUMNS(
        Fac_Ajustes,
        "IdCuenta", Fac_Ajustes[IdCuenta],
        "startdate", Fac_Ajustes[starddate],
        "Net", Fac_Ajustes[Net],
        "Origen_Dato", "Reclasificación"
    )
)
```

| Columna | Descripción |
|---|---|
| `IdCuenta` | Se relaciona con `Dim_Cuentas[Internal_Id]` |
| `startdate` | Se relaciona con `Dim_Tiempo[Date]` |
| `Net` | Movimiento del mes |
| `Origen_Dato` | `"Netsuite"` o `"Reclasificación"`. Sirve para auditar o para ver el balance sin ajustes |

Cómo usarla:

- Toda medida nueva debe sumar `FacNetsuiteConsolidado[Net]`, nunca las tablas origen.
- Para agregar otra fuente de ajustes, se añade un tercer `SELECTCOLUMNS` al `UNION` con las mismas cuatro columnas y en el mismo orden.
- `Fac_Netsuite` y `Fac_Ajustes` conviene ocultarlas en la vista de informe para que nadie las use por error.

---

## 6. Medida principal: Balance_General_YTD

Es la medida que pinta la matriz del balance. Devuelve el **saldo a la fecha de corte seleccionada** en `Dim_Tiempo`.

A pesar del nombre, no todo es "YTD":

| Rubro | Cómo se acumula |
|---|---|
| Activo, Pasivo y Capital (excepto resultado del ejercicio) | Desde el inicio de la historia hasta la fecha de corte |
| Resultado del ejercicio, neto | Solo del 1 de enero del año seleccionado a la fecha de corte |
| Resultados Acumulados | Histórico + la utilidad de todos los años anteriores al seleccionado |

### Medida de apoyo: Monto_Balance

`Balance_General_YTD` se apoya en `Monto_Balance`, que suma los movimientos, aplica la unidad seleccionada y normaliza el signo:

```dax
Monto_Balance =
VAR SaldoBase = DIVIDE(SUM('FacNetsuiteConsolidado'[Net]), [Conversion], BLANK())
VAR Nivel1 = SELECTEDVALUE('Dim_Cuentas'[L1])
RETURN
    IF(
        Nivel1 IN {"Pasivo", "Capital Contable"},
        SaldoBase * -1,
        SaldoBase
    )
```

`[Conversion]` es `MAX(Dim_Unidades[Monto])` (1, 1,000 o 1,000,000).

> `Monto_Balance` solo voltea el signo cuando hay **un único L1** en contexto. Por eso no debe usarse sola en totales que mezclen Activo con Pasivo o Capital; para eso está `Balance_General_YTD`.

### Código de la medida

```dax
Balance_General_YTD =
VAR FechaFin = MAX('Dim_Tiempo'[Date])
VAR AnioSeleccionado = MAX('Dim_Tiempo'[Año])
VAR InicioAnioSeleccionado = DATE(AnioSeleccionado, 1, 1)

VAR L1_Actual = SELECTEDVALUE('Dim_L1'[L1], MAX('Dim_L1'[L1]))
VAR Account_Actual = SELECTEDVALUE('Dim_Cuentas'[Internal_Id])

-- La matriz está desplegada a cualquier nivel inferior a L1
VAR EstaEnSubnivel =
    ISINSCOPE('Dim_L2'[L2]) ||
    ISINSCOPE('Dim_L3'[L3]) ||
    ISINSCOPE('Dim_Cuentas'[Acc-Name]) ||
    ISINSCOPE('Dim_Cuentas'[Account])

-- La matriz está desplegada hasta cuenta individual
VAR EstaEnNivelCuenta =
    ISINSCOPE('Dim_Cuentas'[Acc-Name]) ||
    ISINSCOPE('Dim_Cuentas'[Account])

-- Utilidad de años anteriores al seleccionado (traspaso virtual a Resultados Acumulados)
VAR PyG_AniosAnteriores =
    CALCULATE(
        [Monto_Balance],
        REMOVEFILTERS('Dim_Cuentas'), REMOVEFILTERS('Dim_L1'), REMOVEFILTERS('Dim_L2'), REMOVEFILTERS('Dim_L3'),
        'Dim_Cuentas'[L2] = "Resultado del ejercicio, neto",
        FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] < InicioAnioSeleccionado)
    )

-- 1. CÁLCULO BASE FILA POR FILA
VAR SaldoCalculadoFilaPorFila =
    SUMX(
        VALUES('Dim_Cuentas'[L2]),
        IF(
            'Dim_Cuentas'[L2] = "Resultado del ejercicio, neto",
            CALCULATE(
                [Monto_Balance],
                FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] >= InicioAnioSeleccionado && 'Dim_Tiempo'[Date] <= FechaFin)
            ),
            CALCULATE(
                [Monto_Balance],
                FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] <= FechaFin)
            )
            + IF('Dim_Cuentas'[L2] = "Resultados Acumulados" && NOT EstaEnNivelCuenta, PyG_AniosAnteriores, 0)
        )
    )

-- 2. CÁLCULOS GLOBALES
VAR TotalActivo =
    CALCULATE(
        [Monto_Balance],
        REMOVEFILTERS('Dim_Cuentas'), REMOVEFILTERS('Dim_L1'), REMOVEFILTERS('Dim_L2'), REMOVEFILTERS('Dim_L3'),
        'Dim_Cuentas'[L1] = "Activo",
        FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] <= FechaFin)
    )

VAR TotalPasivo =
    CALCULATE(
        [Monto_Balance],
        REMOVEFILTERS('Dim_Cuentas'), REMOVEFILTERS('Dim_L1'), REMOVEFILTERS('Dim_L2'), REMOVEFILTERS('Dim_L3'),
        'Dim_Cuentas'[L1] = "Pasivo",
        FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] <= FechaFin)
    )

VAR CapitalHistorico =
    CALCULATE(
        [Monto_Balance],
        REMOVEFILTERS('Dim_Cuentas'), REMOVEFILTERS('Dim_L1'), REMOVEFILTERS('Dim_L2'), REMOVEFILTERS('Dim_L3'),
        'Dim_Cuentas'[L1] = "Capital Contable",
        'Dim_Cuentas'[L2] <> "Resultado del ejercicio, neto",
        FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] <= FechaFin)
    ) + PyG_AniosAnteriores

VAR ResultadoEjercicio =
    CALCULATE(
        [Monto_Balance],
        REMOVEFILTERS('Dim_Cuentas'), REMOVEFILTERS('Dim_L1'), REMOVEFILTERS('Dim_L2'), REMOVEFILTERS('Dim_L3'),
        'Dim_Cuentas'[L2] = "Resultado del ejercicio, neto",
        FILTER(ALL('Dim_Tiempo'), 'Dim_Tiempo'[Date] >= InicioAnioSeleccionado && 'Dim_Tiempo'[Date] <= FechaFin)
    )

VAR TotalCapital = CapitalHistorico + ResultadoEjercicio
VAR TotalPasivoMasCapital = TotalPasivo + TotalCapital

-- 3. RETORNO DE LA MEDIDA
RETURN
    IF(
        L1_Actual IN {"Pasivo+Capital", "Diferencia de Balance"} && EstaEnSubnivel,
        BLANK(),
        SWITCH(
            TRUE(),
            Account_Actual = 99989,
                PyG_AniosAnteriores,
            L1_Actual = "Capital Contable" && NOT ISINSCOPE('Dim_L2'[L2]),
                TotalCapital,
            L1_Actual = "Pasivo+Capital",
                TotalPasivoMasCapital,
            L1_Actual = "Diferencia de Balance",
                TotalActivo - TotalPasivoMasCapital,
            SaldoCalculadoFilaPorFila
        )
    )
```

### Cómo leerla

La medida decide qué devolver según la fila de la matriz en la que está parada:

| Fila de la matriz | Qué devuelve |
|---|---|
| Cuenta sintética `99989` | Utilidad de los años anteriores al seleccionado |
| Capital Contable (total L1) | Capital histórico + utilidad de años anteriores + resultado del ejercicio |
| Pasivo+Capital | Total Pasivo + Total Capital |
| Diferencia de Balance | Activo − (Pasivo + Capital). Debe dar cero |
| Pasivo+Capital o Diferencia, desplegadas a un subnivel | Vacío (no tienen detalle) |
| Cualquier otra fila | Saldo acumulado, calculado rubro L2 por rubro L2 |

El cálculo "fila por fila" recorre los L2 visibles con `SUMX` porque cada L2 puede necesitar una ventana de tiempo distinta (acumulado histórico vs. solo el año) y porque el signo se normaliza por L1.


---

## 7. Nota importante: separación de Resultado del ejercicio y Resultados Acumulados

### La solicitud

El equipo financiero pidió que en el Capital Contable se vean **por separado**:

- **Resultado del ejercicio, neto**: la utilidad o pérdida del año en curso.
- **Resultados Acumulados**: las utilidades o pérdidas de ejercicios anteriores.

### El problema

En los datos que se extraen de NetSuite la utilidad de cada año no se traspasa a Resultados Acumulados. Las cuentas de ingresos y gastos siguen acumulando indefinidamente, de modo que, sumadas sin más, toda la utilidad histórica aparecería como "resultado del ejercicio".

Además, para mostrarlos y subtotalizarlos por separado en la matriz, cada concepto necesita su propio rubro de segundo nivel.

### Cómo se resolvió

**1. Niveles ficticios (temporales) en el catálogo.** En `Netsuite.Accounts_Levels` para el reporte 5, dentro de Capital Contable se crearon rubros de nivel 2 que repiten el nombre de su rubro de nivel 3:

| L1 | L2 (ficticio) | L3 |
|---|---|---|
| Capital Contable | Capital Social | Capital Social |
| Capital Contable | Reserva Legal | Reserva Legal |
| Capital Contable | Resultados Acumulados | Resultados Acumulados |
| Capital Contable | Resultado del ejercicio, neto | Resultado del ejercicio, neto |

No aportan una agrupación contable real: existen para que cada concepto tenga su propio renglón L2 y para que la medida pueda distinguirlos por nombre. Son niveles temporales, sujetos a la estructura definitiva que se acuerde para el Capital Contable.

**2. Cuentas de resultados mapeadas al balance.** En la consulta de `Dim_Cuentas`, todas las cuentas del Estado de Resultados (`FK_Reporte = 3`) se asignan al rubro `245` "Resultado del ejercicio, neto".

**3. Traspaso virtual en la medida.** `Balance_General_YTD` parte la utilidad en dos según el año seleccionado:

| Porción | Dónde se muestra |
|---|---|
| Del 1 de enero del año seleccionado a la fecha de corte | Resultado del ejercicio, neto |
| Todo lo anterior al 1 de enero del año seleccionado (`PyG_AniosAnteriores`) | Se suma a Resultados Acumulados |

**4. Fila sintética `99989`.** Al desplegar Resultados Acumulados hasta cuenta, el traspaso aparece en su propio renglón "Traspaso Resultados Ejercicios Anteriores", para que el detalle sume igual que el subtotal.

### Consecuencias

- La medida identifica los rubros **por su texto exacto** (`"Resultado del ejercicio, neto"`, `"Resultados Acumulados"`, `"Capital Contable"`, `"Activo"`, `"Pasivo"`). Si se renombra un rubro en el catálogo, hay que actualizar las medidas.
- El ID de rubro `245` está fijo en la consulta. Si se recrea el catálogo, hay que revisarlo.
- El traspaso es solo de presentación: no genera ningún movimiento en NetSuite ni en el DW.

---

## 8. Opcional: Dim_L1, Dim_L2 y Dim_L3

Estas tres tablas son una **opción de diseño**, no un requisito. Los niveles ya existen como columnas en `Dim_Cuentas`; se sacaron a tablas propias para que la matriz muestre siempre todos los rubros (incluidos los renglones sintéticos sin movimientos) y para que la medida sepa en qué nivel está parada con `ISINSCOPE`.

Si se prescinde de ellas y se usan directamente `Dim_Cuentas[L1]`, `[L2]` y `[L3]`, hay que reescribir en `Balance_General_YTD` las referencias a `Dim_L1`, `Dim_L2` y `Dim_L3`.

### Fórmulas DAX

```dax
Dim_L1 =
SUMMARIZE(Dim_Cuentas, Dim_Cuentas[L1], Dim_Cuentas[Orden L1])
```

```dax
Dim_L2 =
SUMMARIZE(
    FILTER(Dim_Cuentas, NOT ISBLANK(Dim_Cuentas[L2])),
    Dim_Cuentas[L1], Dim_Cuentas[L2], Dim_Cuentas[Orden L2]
)
```

```dax
Dim_L3 =
SUMMARIZE(
    FILTER(Dim_Cuentas, NOT ISBLANK(Dim_Cuentas[L3])),
    Dim_Cuentas[L2], Dim_Cuentas[L3], Dim_Cuentas[Orden L3]
)
```

Los filtros `NOT ISBLANK` excluyen a "Pasivo+Capital" y "Diferencia de Balance", que solo existen en L1.

### Relaciones

Cadena de uno a muchos, filtro en una sola dirección:

```
Dim_L1[L1] 1 ──► * Dim_L2[L1]
Dim_L2[L2] 1 ──► * Dim_L3[L2]
Dim_L3[L3] 1 ──► * Dim_Cuentas[L3]
```

### Configuración adicional

- Ordenar `Dim_L1[L1]` por `Orden L1`, `Dim_L2[L2]` por `Orden L2` y `Dim_L3[L3]` por `Orden L3`.
- En la matriz, las filas van en este orden: `Dim_L1[L1]` → `Dim_L2[L2]` → `Dim_L3[L3]` → `Dim_Cuentas[Acc-Name]`.
- Las relaciones exigen que el nombre de cada L2 y cada L3 sea **único en todo el catálogo**. Dos rubros con el mismo nombre bajo padres distintos rompen la relación.

---

