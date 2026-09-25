# Rediseño de Layout — Estado de Situación Financiera

Guía paso a paso para adaptar el reporte `AF_DA Balance General.pbix` al mockup de referencia, **conservando el mecanismo de comparativo dinámico** que ya existe en el modelo (`Dim_Tiempo` = período actual, `Sel_Periodo_Comparativo` = período a comparar, ambos de selección libre — no es un "vs Año Anterior" fijo).

Todo lo de este documento se arma manualmente en Power BI Desktop (lienzo/formato de visuales). Las medidas DAX que se necesitan ya están creadas en el modelo — se listan en la sección 8.

> **Lienzo de referencia**: todas las coordenadas de este documento asumen una página de **1280 x 720 px** (el tamaño "16:9" por defecto de Power BI Desktop — Formato de página → Tamaño de la página → 16:9). Si tu página es de otro tamaño (ej. 1920x1080), usa las **columnas "%"** de cada tabla en vez de los px absolutos, o escala los px multiplicando por `tu_ancho / 1280` y `tu_alto / 720`.

---

## 1. Paleta de colores

| Uso | Color | Hex |
|---|---|---|
| Dominante (headers, marcos, texto principal) | Azul Marino Oscuro | `#0F172A` (alterno más claro: `#1E293B`) |
| Fondo de página | Gris muy claro | `#F8FAFC` |
| Fondo de tarjetas/contenedores | Blanco | `#FFFFFF` |
| Acento / selección activa | Azul Corporativo | `#2563EB` |
| Positivo / dentro de meta | Verde suave | `#16A34A` |
| Negativo / fuera de meta | Rojo coral | `#DC2626` |
| Texto secundario | Gris medio | `#64748B` |
| Líneas divisorias / bordes sutiles | Gris claro | `#E2E8F0` |

### Tema de reporte listo para importar

Guarda esto como `GrupoGomex_Theme.json` y cárgalo en **Vista → Temas → Explorar temas → Examinar temas**:

```json
{
  "name": "Grupo Gomex - Balance General",
  "dataColors": ["#2563EB", "#16A34A", "#DC2626", "#64748B", "#0F172A", "#93C5FD", "#86EFAC", "#FCA5A5", "#CBD5E1", "#1E293B"],
  "background": "#F8FAFC",
  "foreground": "#1E293B",
  "tableAccent": "#2563EB",
  "good": "#16A34A",
  "bad": "#DC2626",
  "neutral": "#64748B",
  "maximum": "#2563EB",
  "center": "#94A3B8",
  "minimum": "#DC2626",
  "textClasses": {
    "callout": { "color": "#0F172A", "fontFace": "Segoe UI" },
    "title": { "color": "#0F172A", "fontFace": "Segoe UI Semibold" },
    "header": { "color": "#FFFFFF", "fontFace": "Segoe UI Semibold" },
    "label": { "color": "#1E293B", "fontFace": "Segoe UI" }
  },
  "visualStyles": {
    "*": {
      "*": {
        "background": [{ "color": { "solid": { "color": "#FFFFFF" } } }],
        "border": [{ "show": true, "color": { "solid": { "color": "#E2E8F0" } }, "radius": 8 }]
      }
    }
  }
}
```

> `textClasses` solo admite `color` y `fontFace` (el esquema de temas de Power BI rechaza `backgroundColor` ahí). El fondo azul marino de la barra de encabezado no se define en el tema: se pone directamente en el rectángulo de esa zona (sección 3) con relleno `#0F172A` o `#1E293B`.
>
> Nota: según la versión de Desktop, algunas propiedades de `visualStyles` pueden no aplicarse a todos los visuales. Impórtalo y ajusta lo que no tome; los tamaños/bordes de cada visual también se pueden fijar manualmente con los valores de las secciones 3-6.

---

## 2. Estructura de 3 zonas y grid de referencia

```
┌───────────────────────────────────────────────────────────────────┐
│  ZONA SUPERIOR — Encabezado + Slicers            h=96px   (13.3%) │
├───────────────────────────────────────────────────────────────────┤
│  ZONA MEDIA — 4 KPI Cards                         h=130px  (18.1%) │
├───────────────────────────────────┬─────────────────────────────────┤
│  ZONA INFERIOR IZQUIERDA (70%)     │  ZONA INFERIOR DERECHA (30%)   │
│  Matriz Balance General            │  Razones Financieras           │
│  w=851px                           │  w=365px           h=482px (67%)│
└───────────────────────────────────┴─────────────────────────────────┘
```

### Tabla de zonas (px sobre lienzo 1280x720)

| Zona | x | y | Ancho | Alto | Márgenes |
|---|---|---|---|---|---|
| Página completa | 0 | 0 | 1280 | 720 | Margen exterior 24px en los 4 lados |
| Superior (header) | 0 | 0 | 1280 | 96 | — |
| Media (KPIs) | 0 | 102 | 1280 | 130 | Gap vertical 6px con la zona superior |
| Inferior izquierda (matrix) | 24 | 238 | 851 | 482 | — |
| Inferior derecha (razones) | 891 | 238 | 365 | 482 | Gap horizontal 16px con la matriz |

---

## 3. Zona superior — Encabezado y filtros (x=0,y=0,w=1280,h=96)

| Elemento | x | y | Ancho | Alto | Fuente / tamaño | Color |
|---|---|---|---|---|---|---|
| Fondo de la barra (rectángulo) | 0 | 0 | 1280 | 96 | — | Relleno `#F4F5F7` (o `#0F172A` si prefieres oscuro, ver mockup) |
| Título "Estado de Situación Financiera" | 24 | 10 | 520 | 28 | Segoe UI Semibold, **20pt** | `#0F172A` |
| Subtítulo "Análisis del Balance General…" | 24 | 40 | 520 | 18 | Segoe UI, **10pt** | `#64748B` |
| Logo Grupo Gomex | 1180 | 8 | 90 | 54 | — | — |
| Badge BETA/BORRADOR (forma redondeada) | 1096 | 14 | 64 | 24 | Segoe UI Semibold, **8pt**, radio de esquina 12px | Fondo `#E2E8F0`, texto `#475569` |
| Slicer Año (dropdown) | 560 | 10 | 90 | 26 | Segoe UI, **9pt** | — |
| Slicer Mes (Tile horizontal) | 560 | 40 | 420 | 26 | Segoe UI, **9pt**, cada botón ~34x24px | Seleccionado: fondo `#2563EB` texto blanco; no seleccionado: fondo `#FFFFFF` texto `#1E293B` |
| Slicer comparativo (Tile horizontal, período a comparar) | 560 | 68 | 420 | 24 | Segoe UI, **8pt** | Igual esquema de color, pero borde `#94A3B8` para diferenciarlo visualmente del slicer principal |

El slicer de mes/tile **no es un visual especial**: es el visual **Slicer** estándar sobre `Dim_Tiempo[Mes_Texto]`, con Formato → Opciones de segmentación → Estilo: **Mosaico (Tile)**, Disposición: **Horizontal**. El slicer comparativo es igual pero sobre `Sel_Periodo_Comparativo[AgnoMes]`.

---

## 4. Zona media — 4 KPI Cards (y=102, h=130)

Ancho de cada tarjeta: `(1280 - 2×24 - 3×16) / 4 = 296px`. Posiciones:

| Tarjeta | x | y | Ancho | Alto |
|---|---|---|---|---|
| Total Activo | 24 | 102 | 296 | 130 |
| Total Pasivo | 336 | 102 | 296 | 130 |
| Capital Contable | 648 | 102 | 296 | 130 |
| Solvencia / Apalancamiento | 960 | 102 | 296 | 130 |

### Composición interna de cada tarjeta (relativo a su propio x,y)

| Elemento | x | y | Ancho | Alto | Fuente / tamaño | Color |
|---|---|---|---|---|---|---|
| Fondo tarjeta | 0 | 0 | 296 | 130 | — | `#FFFFFF`, borde 1px `#E2E8F0`, radio 8px |
| Ícono (izquierda) | 16 | 16 | 28 | 28 | — | `#2563EB` sobre círculo `#EFF6FF` |
| Título ("Total Activo", etc.) | 52 | 18 | 220 | 18 | Segoe UI Semibold, **11pt** | `#64748B` |
| Valor grande | 16 | 44 | 264 | 40 | Segoe UI Semibold, **26pt** | `#0F172A` (o formato condicional rojo/negro en Capital Contable) |
| Variación vs comparativo (flecha + %) | 16 | 92 | 264 | 20 | Segoe UI, **11pt** | Automático del visual (verde/rojo) |
| Subtítulo pequeño ("vs [mes comparativo]") | 16 | 110 | 264 | 16 | Segoe UI, **8pt** | `#94A3B8` |

Usa el visual **Card (nuevo)**: Callout = `RF_AT` / `RF_PT` / `RF_CC` / `RF_Solvencia`; Reference/Comparison value = `RF_AT_Comp` / `RF_PT_Comp` / `RF_CC_Comp` / `RF_Solvencia_Comp` (el visual calcula solo el % y la flecha, tamaño de fuente configurable en el panel Formato → Valor de referencia → Texto → 11pt).

Para Capital Contable en rojo si es negativo: Formato → Valor del indicador → Color de fuente → Formato condicional, campo `RF_CC`, regla `< 0 → #DC2626`, `>= 0 → #0F172A`.

---

## 5. Zona inferior izquierda (x=24,y=238,w=851,h=482) — Matriz Balance General

| Elemento | Tamaño / propiedad | Valor |
|---|---|---|
| Encabezado de columnas | Fuente, tamaño | Segoe UI Semibold, **10pt**, texto blanco sobre fondo `#0F172A`, alto de fila 28px |
| Filas de detalle (cuenta) | Fuente, tamaño | Segoe UI, **9pt**, alto de fila 24px |
| Filas de subtotal (L1/L2/L3) | Fuente, tamaño | Segoe UI Semibold, **10pt**, alto de fila 26px, fondo `#F1F5F9` |
| Bandas alternadas | Color | `#F8FAFC` / `#FFFFFF` |
| Bordes de cuadrícula | Grosor / color | 1px, `#E2E8F0` (nunca negro puro) |
| Ancho columna "Concepto" | Ancho | ~280px (35% del ancho total) |
| Ancho columnas numéricas (Dic X, Dic Y, Var $, Var %, Index) | Ancho | ~114px cada una (resto repartido entre 5 columnas) |
| Alineación | — | Texto izquierda, números derecha |

Formato → **Opciones de estilo → Diseño de fila: Escalonado (Stepped layout)**, indentado 12px por nivel.

Formato condicional en `Var` e `Index`: usa **íconos** (▲/▼, tamaño 12px) en vez de fondo completo de color, basado en `VarColor`/`IndexColor` (ya existen), aplicados como color de fuente (no relleno de celda).

---

## 6. Zona inferior derecha (x=891,y=238,w=365,h=482) — Razones Financieras

4 bloques apilados, cada uno `365 x 114px` con gap vertical de 8px:

| Bloque | x (relativo a la zona) | y (relativo a la zona) | Alto |
|---|---|---|---|
| Deuda Neta % (Gauge) | 0 | 0 | 114 |
| Solvencia / Apalancamiento | 0 | 122 | 114 |
| Razón Corriente | 0 | 244 | 114 |
| ROE | 0 | 366 | 114 |

### Composición interna de cada bloque (114px de alto)

| Elemento | y (relativo al bloque) | Alto | Fuente / tamaño | Color |
|---|---|---|---|---|
| Fondo del bloque | 0 | 114 | — | `#FFFFFF`, borde 1px `#E2E8F0`, radio 8px |
| Título ("Deuda Neta %", etc.) | 10 | 16 | Segoe UI Semibold, **11pt** | `#0F172A` |
| Valor grande (o Gauge) | 28 | 56 | Segoe UI Semibold, **22pt** (Gauge: usar tamaño de fuente 20pt en el panel de datos del propio visual) | `#0F172A` |
| Texto de meta ("Meta ≤ 60%") | 28 | 14 | Segoe UI, **8pt**, alineado a la derecha | `#94A3B8` |
| Barra/indicador de progreso (si no es Gauge) | 86 | 10 | — | Relleno con formato condicional (`RF_..._Color`) |
| Texto de estado ("Dentro de rango", etc.) | 98 | 14 | Segoe UI, **9pt** | Verde `#16A34A` / rojo `#DC2626` según `RF_..._Color` |

### 6.1 Deuda Neta % — Gauge (medidor radial)
- Visual: **Gauge**. Valor: `RF_DeudaNeta_Pct`. Mínimo 0, Máximo 1 (100%). Meta/Target: `RF_Meta_DeudaNeta`.
- Formato → Datos del indicador → Color: formato condicional con `RF_DeudaNeta_Color`.
- Formato → Texto del indicador → tamaño **20pt**.
- Subtítulo: `RF_DeudaNeta_Estado` (Card de texto, 9pt, debajo del Gauge).

### 6.2 Solvencia / Apalancamiento — Card + barra de progreso
- Card (nuevo): valor `RF_Solvencia`, tamaño **22pt**.
- Barra de progreso: gráfico de barras de 1 categoría/1 barra, alto 10px, valor `RF_Solvencia`, línea constante (Analytics → Constant line) en `RF_Meta_Solvencia`, grosor de línea 1.5px, color `#94A3B8`.
- Color de barra: formato condicional con `RF_Solvencia_Color`. Subtítulo: `RF_Solvencia_Estado`.

### 6.3 Razón Corriente — Card + barra de progreso
- Valor: `Razon_Circulante` (22pt). Meta: `RF_Meta_RazonCorriente`.
- Color: `RF_RazonCorriente_Color`. Subtítulo: `RF_RazonCorriente_Estado`.

### 6.4 ROE — Card + barra de progreso
- Valor: `RF_ROE` (22pt). Meta: `RF_Meta_ROE`.
- Color: `RF_ROE_Color`. Subtítulo: `RF_ROE_Estado`.

### Ocultar fórmulas, mostrarlas solo en tooltip
1. Crea una **página de tooltip**: Formato de página → Tipo de página: Tooltip → tamaño **200 x 150px** (tamaño estándar de tooltip en Power BI).
2. Contenido de esa página: texto 9pt con las medidas `RF_Operando1_Texto`, `RF_Operando2_Texto`, `RF_Resultado_Texto` (y sus `_Comp` si quieres mostrar ambos períodos).
3. En cada visual de la sección 6, Formato → **Tooltips → Tipo: Página de informe** → selecciona esa página.

---

## 7. Escala tipográfica (resumen)

| Elemento | Fuente | Tamaño | Peso | Color |
|---|---|---|---|---|
| Título de página | Segoe UI | 20pt | Semibold | `#0F172A` |
| Subtítulo de página | Segoe UI | 10pt | Regular | `#64748B` |
| Badge de estado | Segoe UI | 8pt | Semibold | `#475569` |
| Texto de slicer | Segoe UI | 9pt | Regular | `#1E293B` |
| Título de KPI Card | Segoe UI | 11pt | Semibold | `#64748B` |
| Valor de KPI Card | Segoe UI | 26pt | Semibold | `#0F172A` |
| Variación de KPI Card | Segoe UI | 11pt | Regular | auto (verde/rojo) |
| Encabezado de matriz | Segoe UI | 10pt | Semibold | `#FFFFFF` |
| Fila de detalle de matriz | Segoe UI | 9pt | Regular | `#1E293B` |
| Fila de subtotal de matriz | Segoe UI | 10pt | Semibold | `#0F172A` |
| Título de bloque de razón financiera | Segoe UI | 11pt | Semibold | `#0F172A` |
| Valor de razón financiera | Segoe UI | 22pt | Semibold | `#0F172A` |
| Meta / caption | Segoe UI | 8pt | Regular | `#94A3B8` |
| Estado (semáforo) | Segoe UI | 9pt | Regular | `#16A34A` / `#DC2626` |
| Texto de tooltip | Segoe UI | 9pt | Regular | `#1E293B` |

Alineación general: números siempre a la derecha, texto siempre a la izquierda (Formato de columna en Matrix/Table → Alineación de valores).

---

## 8. Catálogo de medidas DAX

### Ya existían en el modelo
| Medida | Qué hace |
|---|---|
| `Monto_Balance` | Monto con signo por cuenta/período |
| `Balance_General_YTD` | Saldo acumulado YTD por nivel L1/L2/L3/cuenta |
| `Balance_General_Comparativo` | Igual que arriba, evaluado en `Sel_Periodo_Comparativo[Fecha]` |
| `Var`, `Var Natural`, `Index`, `Index Natural` | Variación y proporción entre período actual y comparativo |
| `VarColor`, `IndexColor` | Semáforo de color para `Var`/`Index` |
| `Apalancamiento`, `Razon_Circulante`, `Capital_de_Trabajo` | Razones ya existentes (se reutilizan) |
| `Titulo_YTD_Movil`, `Titulo_Comparativo` | Texto del mes seleccionado por período |

### Creadas para el bloque de Razones Financieras (sesión anterior)
| Medida | Fórmula / propósito |
|---|---|
| `RF_PT`, `RF_AT`, `RF_ACP`, `RF_PCP`, `RF_PLP`, `RF_CC` | Bases (Pasivo/Activo/Circulantes/Capital), período actual |
| `RF_PT_Comp` … `RF_CC_Comp` | Mismas bases, período comparativo |
| `RF_DeudaNeta_Pct`, `RF_Solvencia`, `RF_CapitalTrabajoNeto_Pct`, `RF_Apalancamiento`, `RF_Capitalizacion_Pct` | Las 5 razones, período actual |
| `..._Comp` de cada una | Las 5 razones, período comparativo |
| `Dim_Razon_Financiera` (tabla) + `RF_Operando1_Valor/Texto`, `RF_Operando2_Valor/Texto`, `RF_Resultado_Valor/Texto` (+ `_Comp`) | Matriz dinámica de 5 filas para la tabla apilada PT/AT/DN |

### Nuevas (creadas para este rediseño)
| Medida | Fórmula / propósito |
|---|---|
| `RF_UtilidadNeta` | Utilidad del ejercicio YTD (para ROE), período actual |
| `RF_UtilidadNeta_Comp` | Igual, período comparativo |
| `RF_ROE` | `DIVIDE(RF_UtilidadNeta, RF_CC)` |
| `RF_ROE_Comp` | `DIVIDE(RF_UtilidadNeta_Comp, RF_CC_Comp)` |
| `RF_Meta_DeudaNeta` | Constante 0.60 (60%) |
| `RF_Meta_Solvencia` | Constante 1.50 |
| `RF_Meta_RazonCorriente` | Constante 1.20 |
| `RF_Meta_ROE` | Constante 0.10 (10%) |
| `RF_DeudaNeta_Color` / `RF_DeudaNeta_Estado` | Verde/rojo + texto si `RF_DeudaNeta_Pct <= Meta` |
| `RF_Solvencia_Color` / `RF_Solvencia_Estado` | Verde/rojo + texto si `RF_Solvencia <= Meta` |
| `RF_RazonCorriente_Color` / `RF_RazonCorriente_Estado` | Verde/rojo + texto si `Razon_Circulante >= Meta` |
| `RF_ROE_Color` / `RF_ROE_Estado` | Verde/rojo + texto si `RF_ROE >= Meta` |

Todas estas medidas nuevas viven en la tabla `_Medidas`, carpetas `Razones Financieras\Base`, `\Razones`, `\Metas` y `\Semaforo`.

**Nota sobre "Metas"**: hoy son constantes fijas en DAX (0.60, 1.50, 1.20, 0.10). Si más adelante quieres que el equipo de finanzas las edite sin tocar el modelo, se pueden mover a una tabla chica editable (`Dim_Metas_Financieras`) — avísame si quieres que la arme.

---

## 9. Orden sugerido de implementación

1. Importa el tema de color (sección 1).
2. Arma la zona superior con las coordenadas de la sección 3.
3. Arma las 4 KPI cards con las coordenadas de la sección 4.
4. Reformatea la matriz con las coordenadas/tamaños de la sección 5.
5. Arma los 4 bloques de Razones Financieras con las coordenadas de la sección 6.
6. Crea la página de tooltip y enlázala a los 4 bloques.
7. Revisa contra la tabla de la sección 7 que ningún texto quede fuera de la escala tipográfica definida.
