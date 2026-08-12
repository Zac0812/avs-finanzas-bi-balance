No te preocupes es correcto que faltaban cuentas por mapear, las cuales ya mueron incorporadas, y las que quedan son IVA o ISR, las cuales no afecta al reporte en si,
sin embargo mi medida Necesito que me apoyes a validar mi medida `Balance_General_YTD`. En contexto:

Estoy construyendo un reporte financiero de Balance General en Power BI utilizando una tabla de dimensión de cuentas desnormalizada (Dim_Cuentas) con los niveles L1, L2, L3 y Acc-Name, relacionada con una tabla de hechos transaccionales (Fac_Netsuite) y una tabla de tiempo (Dim_Tiempo).

El Problema Contable:

1. Filas Inyectadas: En el UNION ALL de la dimensión creé filas virtuales al nivel de L1 llamadas "Pasivo+Capital" y "Diferencia de Balance" para cuadrar el balance visualmente.

2. Doble Comportamiento Temporal en Capital Contable:

Las cuentas de PyG (Estado de Resultados, mapeadas bajo "Resultado del ejercicio") deben mostrar solo los movimientos del año en curso (YTD desde el 1 de enero hasta la fecha seleccionada (año y mes) en filtros).

Sin embargo, el equipo contable exige que los saldos históricos de esas mismas cuentas de PyG correspondientes a años anteriores al año seleccionado se sumen y se muestren dentro de la sección de "Resultados Acumulados" (junto con las cuentas reales de utilidades retenidas que ya existen en esa categoría).







Veo que en terminos general funciono correctamente, para los subtotales ie. L1,L2 y L3 pero que pasa si el usuario hable cuetnas no va ver el cuadre por cuenta eso se podría resolver de alguna manera 


Perfecto, funciono ahora tengo un tema visual

Actualmente ya tengo creado mi matrix con mis columnas de `Balance_General_YTD`, `Balance_General_Comparativo`, `Index` y `Var`, Respectivamente tiene el formato de Número seperado por commas sin decimales, para los 3 primeros elementos y porcentajes sin decimales para Var. Así mismo todos tiene el formato de color rojo en caso de tener valores negativos, funciona y se ve bien sin embargo sigo queriendo tener los titulos dinamicos lo que estab pensando es hacer algo como una tabla de medidas dinamicas algo como :

Medidas Dinamicas = 
DATATABLE(
    "Titulo", STRING,
    "Orden", INTEGER,
    {
        { "2022", 1 },
        { "2023", 2 },
        { "2024", 3 },
        { "2025", 4 },
        { "2026", 5 },
    }
)

Para los filtros de `Balance_General_YTD` y otra similar para `Balance_General_Comparativo` así tendriamos de manera dinamica dado sus filtros dos medidas dinamicas en cierto sentido dado el año para poder anexarlas en la matrix, como lo ves 





pero el teme de las cards es que si hacen grande la matriz o la focalizan se pierden esos titulos, hagamos algo diferentes, crea una tabla llamada medida dinamicas como te mostraba:

Medidas Dinamicas = 
DATATABLE(
    "Titulo", STRING,
    "Orden", INTEGER,
    {
        { "2022", 1 },
        { "2023", 2 },
        { "2024", 3 },
        { "2025", 4 },
        { "2026", 5 },
       { "vs 2022", 6 },
        { "vs 2023", 7 },
        { "vs 2024", 8 },
        { "vs2025", 9 },
        { "vs 2026", 10 },
        { "Index", 11 },
        {"Var,12}
    }
)

En dicha nueva tabla vamos a crear una medida:

Balance Valor =
RETURN
    SWITCH(
        TRUE(),
        SelectedTitle = "2025", IF(FilterYear = 2026, [LY], BLANK()),
        SelectedTitle = "2024", IF(FilterYear = 2025, [LY], BLANK()),
        SelectedTitle = "2023", IF(FilterYear = 2024, [LY], BLANK()),

        SelectedTitle = "Budget 2025", IF(FilterYear = 2025, [Dinam Master Plan], BLANK()),
        SelectedTitle = "Budget 2024", IF(FilterYear = 2024, [Dinam Master Plan], BLANK()),
        SelectedTitle = "Budget 2026", IF(FilterYear = 2026, [Dinam Master Plan], BLANK()),
        SelectedTitle = "Index Fcs vs LY", [3_ Indx Fcst vs LY],
        SelectedTitle = "Index Fcs vs Bud", [4_ Indx Fcst vs Bdgt],
        BLANK()
    )


Podrísa modificar las medidas que hemos creado basado en la tabla de hechos `Fac_Netsuite` y migrarlas a `FacNetsuiteConsolidado` que es resultado de un join de dos tablas para tener los montos reales del p&l




Respecto a nuestro ETL que se encuentra almacenado en `C:\Users\luis.meza\Desktop\Analista Pricing\Cloude Code Projects\Balance General\test\BalanceGeneralPruebas.ipynb` especificamente el apartado de Activo por derecho de uso vehiculos podrías generear un codigo en python i.e .main . Sigue las mejores practicas sin embargo intenta no normalizar en exceso el codigo dado que es algo simple



Necesito que realizes una copia de `credenciales/credsDrive.json` a  `credenciales/credsDriveTest.json` con un ejemplo de las credentciales que se necesitan crear en google dado que cuando subamos el proyecto a git no podremos subir las credenciales pero si la carpeta que lo contiene y la estrucutra lo mismo para `.env.test` que es el ejemplo de como esta `env`

Creame de igual manera el gitignore para según lo que creas conveniente omitor para poder tener nuestro control de versión importante mencionar que `C:\Users\luis.meza\Desktop\Analista Pricing\Cloude Code Projects\Balance General\test\BalanceGeneralPruebas.ipynb` si lo vamos a subir solo asegura que no tenga ninguna clave expuesta
