

#Server: DW-GOMEX
#DB: RAW_NS

USE RAW_NS
/*
Tabla para el almacenamiento de las reclasificaciones manuales de contabilidad 
*/

create table Netsuite.ReclasificacionesContables (
FK_Reporte int, 
PeriodoContable date,
IdCuenta int,
Monto float,
Nota nvarchar(max)
)




---BI Balance--- 
-- 1. Declaramos e inicializamos la variable
DECLARE @FK_ReporteBalance INT = 2;
DECLARE @FK_ReportePyL INT = 3;
DECLARE @ID_Rubro_ResultadosEjercicio INT = 129;
;With Cuentas as (
--Cuentas Contables + Cuentas Contables de Sueldos y Salarios de la Operación
	select c.*
	from Netsuite.Accounts c
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
	union all
	select 276000, '15400000', 'Ajuste Activo por derecho de uso vehiculos', 1
	union all
	select 276001, '15400001', 'Ajuste Activo por derecho de uso vehiculos', 1
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
	where l3.FK_Reporte=@FK_ReporteBalance and l3.Nivel=3
),
--Mapeo de Cuentas de P&L para el rubro de Resultados del Ejercicio (ID_Rubro 129) del balance
MapeoBalance as (
	select m.*
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=@FK_ReporteBalance  
	union all 
	select  m.Internal_Id, @FK_ReporteBalance FK_Reporte , @ID_Rubro_ResultadosEjercicio FK_PL_Nivel_Base
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=3--@FK_ReportePyL  
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
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
--order by n.OrdenL1 asc,n.OrdenL2 asc, n.OrdenL3 asc
union all
select 99989,NULL,'Traspaso Resultados Ejercicios Anteriores','Traspaso Resultados Ejercicios Anteriores','Capital Contable','Resultados Acumulados','Resultados Acumulados',3,7,37
union all
select 99990,NULL,NULL,'Pasivo+Capital','Pasivo+Capital',NULL,NULL,98,998,9998
union all
select 99991,NULL,NULL,'Diferencia de Balance','Diferencia de Balance',NULL,NULL,99,999,9999










---BI Balance 3 Niveles Fco Soria 4 Niveles--- 

-- 1. Declaramos e inicializamos la variable
DECLARE @FK_ReporteBalance INT = 4;
DECLARE @FK_ReportePyL INT = 3;
DECLARE @ID_Rubro_ResultadosEjercicio INT = 183;
;With Cuentas as (
--Cuentas Contables + Cuentas Contables de Sueldos y Salarios de la Operación
	select c.*
	from Netsuite.Accounts c
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
	union all
	select 276000, '15400000', 'Ajuste Activo por derecho de uso vehiculos', 1
	union all
	select 276001, '15400001', 'Ajuste Activo por derecho de uso vehiculos', 1
),
Niveles as (
	select 
	--LEVEL1
	l1.Orden OrdenL1,l1.Nombre_Rubro L1,
	--L2
	DENSE_RANK() OVER (ORDER BY l1.Orden ASC, l1.ID_Rubro, l2.Orden ASC, l2.ID_Rubro) AS OrdenL2,
	l2.Orden PoscicionL2,l2.Nombre_Rubro L2,
	--L3
	DENSE_RANK() OVER (ORDER BY l1.Orden ASC, l1.ID_Rubro, l2.Orden ASC, l2.ID_Rubro,l3.Orden ASC, l3.ID_Rubro) AS OrdenL3,
	l3.Orden PoscicionL3,l3.Nombre_Rubro L3, --l3.ID_Rubro,l3.FK_Reporte,
	--L4
	ROW_NUMBER() OVER (ORDER BY l1.Orden ASC, l2.Orden ASC, l3.Orden,l4.Orden ASC) AS OrdenL4,
	l4.Orden PoscicionL4,l4.Nombre_Rubro L4, l4.ID_Rubro,l4.FK_Reporte
	from Netsuite.Accounts_Levels l4 
	--L3
	join Netsuite.Accounts_Levels l3 on l4.ID_Padre=l3.ID_Rubro and l4.FK_Reporte=l3.FK_Reporte
	--L2
	join Netsuite.Accounts_Levels l2 on l3.ID_Padre=l2.ID_Rubro and l3.FK_Reporte=l2.FK_Reporte
	--L1
	join Netsuite.Accounts_Levels l1 on l2.ID_Padre=l1.ID_Rubro and l2.FK_Reporte=l1.FK_Reporte
	where l4.FK_Reporte=@FK_ReporteBalance and l4.Nivel=4
	--ORDER BY OrdenL1 ASC, OrdenL4 ASC
),
--Mapeo de Cuentas de P&L para el rubro de Resultados del Ejercicio  del balance
MapeoBalance as (
	select m.*
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=@FK_ReporteBalance  
	union all 
	select  m.Internal_Id, @FK_ReporteBalance FK_Reporte , @ID_Rubro_ResultadosEjercicio FK_PL_Nivel_Base
	from Netsuite.Accounts_ReportMapping m
	where m.FK_Reporte=3--@FK_ReportePyL  
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
	union all 
	select 276000 Internal_Id, @FK_ReporteBalance FK_Reporte, 143 FK_PL_Nivel_Base
	union all 
	select 276001 Internal_Id, @FK_ReporteBalance FK_Reporte, 145 FK_PL_Nivel_Base
)
--Balance 
select a.Internal_Id,a.Number Account,a.Number+'-'+a.Account [Acc-Name] ,a.Account Description,
n.L1,n.L2,n.L3,n.L4,
n.OrdenL1 [Orden L1],n.OrdenL2 [Orden L2] , n.OrdenL3 [Orden L3],n.OrdenL4 [Orden L4]
from MapeoBalance m
join Cuentas a on m.Internal_Id=a.Internal_Id 
join Niveles n on m.FK_PL_Nivel_Base=n.ID_Rubro and m.FK_Reporte=n.FK_Reporte
--order by n.OrdenL1 asc,n.OrdenL2 asc, n.OrdenL3 asc
--union all
--select 99989,NULL,'Traspaso Resultados Ejercicios Anteriores','Traspaso Resultados Ejercicios Anteriores','Capital Contable','Capital Contable','Resultados Acumulados','Resultados Acumulados',3,7,37
--union all
--select 99990,NULL,NULL,'Pasivo+Capital','Pasivo+Capital',NULL,NULL,98,998,9998
--union all
--select 99991,NULL,NULL,'Diferencia de Balance','Diferencia de Balance',NULL,NULL,99,999,9999














---BI Balance--- CORPORATIVO (ARIETE+BRM+CARFIX)
-- 3. Declaramos e inicializamos la variable
DECLARE @FK_ReporteBalance INT = 5;
DECLARE @FK_ReportePyL INT = 3;
DECLARE @ID_Rubro_ResultadosEjercicio INT = 245;
;With Cuentas as (
--Cuentas Contables + Cuentas Contables de Sueldos y Salarios de la Operación
	select c.*
	from Netsuite.Accounts c
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
	--union all
	--select 276000, '15400000', 'Ajuste Activo por derecho de uso vehiculos', 1
	--union all
	---select 276001, '15400001', 'Ajuste Activo por derecho de uso vehiculos', 1
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
	where l3.FK_Reporte=@FK_ReporteBalance and l3.Nivel=3
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
	--Reclasifación contable 
	--https://docs.google.com/spreadsheets/d/1P5ItjEsw3yh8wvev7ZWYop3BomhwEfX7Fdf_UFCLXYU/edit?gid=263435312#gid=263435312
	--pestaña Ideas de la reclasificación
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
--order by n.OrdenL1 asc,n.OrdenL2 asc, n.OrdenL3 asc
union all
select 99989,NULL,'Traspaso Resultados Ejercicios Anteriores','Traspaso Resultados Ejercicios Anteriores','Capital Contable','Resultados Acumulados','Resultados Acumulados',3,7,37
union all
select 99990,NULL,NULL,'Pasivo+Capital','Pasivo+Capital',NULL,NULL,98,998,9998
union all
select 99991,NULL,NULL,'Diferencia de Balance','Diferencia de Balance',NULL,NULL,99,999,9999

