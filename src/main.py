"""ETL de las reclasificaciones manuales del Balance General Corporativo (FK_Reporte = 5).

Reemplaza a src/main_comite_old.py (proceso vigente para FK_Reporte = 2). Lee dos
pestañas del libro de contabilidad, convierte sus montos acumulados en movimientos
mensuales y las une en un solo conjunto (más una cancelación global por cuenta en Agosto 2026) con la forma de Netsuite.ReclasificacionesContables
(ver src/tablas.sql).

Por defecto NO toca el DW: solo genera un Excel de revisión. La inserción requiere el
flag --cargar y es un APPEND (no borra lo que ya existe en la tabla).

    python src/main.py             # genera data/processed/Revision_Reclasificaciones_FK5.xlsx
    python src/main.py --cargar    # además hace append en RAW_NS.Netsuite.ReclasificacionesContables
"""

import argparse
import os

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = "161vanW8jb2X7Z0MACL9YQo7qYdXHuW6dVwvefcmPz8Q"
WORKSHEET_PROPIEDAD = "Correción Propiedad"
WORKSHEET_SUBSIDIARIA = "Subsidiaria"

# Valor fijo del reporte de Balance General Corporativo (ARIETE+BRM+CARFIX)
FK_REPORTE_CORPORATIVO = 5
# Par de cuentas de la corrección de propiedad: la primera con signo positivo, la segunda negado
ID_CUENTA_PROPIEDAD_POSITIVA = 1253
ID_CUENTA_PROPIEDAD_NEGATIVA = 276

# Cancelación global: reversa el total acumulado de cada cuenta en este periodo
PERIODO_CANCELACION = pd.Timestamp("2026-08-01")
NOTA_CANCELACION = "Cancelación global"

DW_SCHEMA = "Netsuite"
DW_TABLE = "ReclasificacionesContables"
SQL_DRIVER = "ODBC Driver 17 for SQL Server"

EXCEL_REVISION = os.path.join("data", "processed", "Revision_Reclasificaciones_FK5.xlsx")
COLUMNAS_DW = ["FK_Reporte", "PeriodoContable", "IdCuenta", "Monto", "Nota"]


def get_sql_engine(server: str, database: str, driver: str = SQL_DRIVER) -> Engine:
    """Retorna un Engine de SQLAlchemy (autenticación Windows) listo para Pandas."""
    driver_encoded = driver.replace(" ", "+")
    conn_str = f"mssql+pyodbc://{server}/{database}?driver={driver_encoded}&trusted_connection=yes"
    return create_engine(conn_str)


def append_dataframe_to_sql(engine: Engine, df: pd.DataFrame, schema: str, table: str, fk_reporte: int) -> None:
    """Agrega el DataFrame a la tabla del DW sin borrar nada, en una sola transacción.

    Como es un append puro, correrlo dos veces duplicaría los datos: si la tabla ya
    tiene filas de este FK_Reporte se aborta en vez de insertar.
    """
    tabla_completa = f"{schema}.{table}"
    with engine.begin() as conn:
        existentes = conn.execute(
            text(f"SELECT COUNT(*) FROM {tabla_completa} WHERE FK_Reporte = :fk"), {"fk": fk_reporte}
        ).scalar()
        if existentes:
            raise RuntimeError(
                f"{tabla_completa} ya tiene {existentes} filas con FK_Reporte={fk_reporte}; "
                "se aborta para no duplicar la carga."
            )
        # INSERT directo (executemany) en vez de df.to_sql: to_sql de pandas 1.x no es compatible con SQLAlchemy 2.x
        filas = df.assign(PeriodoContable=df["PeriodoContable"].dt.date).to_dict("records")
        columnas = ", ".join(df.columns)
        valores = ", ".join(f":{c}" for c in df.columns)
        conn.execute(text(f"INSERT INTO {tabla_completa} ({columnas}) VALUES ({valores})"), filas)


def _leer_pestana(client: gspread.Client, worksheet_name: str, rango: str, headers: list[str]) -> pd.DataFrame:
    """Lee un rango de la hoja con nombres de columna fijos (la fila 1 de la hoja se descarta).

    UNFORMATTED_VALUE: necesitamos los montos como número, no como texto con formato.
    Nombres fijos para no depender de que nadie edite los títulos de la hoja.
    """
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)
    data_range = worksheet.get(rango, value_render_option="UNFORMATTED_VALUE")
    records = [dict(zip(headers, row)) for row in data_range[1:]]
    df = pd.DataFrame(records, columns=headers)
    # Descarta filas vacías o incompletas al final de la hoja
    return df.dropna(subset=["No_Year", "No_Mes", headers[-1]]).reset_index(drop=True)


def extraer_propiedad(client: gspread.Client) -> pd.DataFrame:
    """Pestaña 'Correción Propiedad': A=No_Year, B=No_Mes, F=Monto (acumulado, ya filtrado)."""
    df = _leer_pestana(
        client,
        WORKSHEET_PROPIEDAD,
        "A:F",
        ["No_Year", "No_Mes", "Descripcion", "MontoContabilidad", "PyL", "MontoAcumulado"],
    )
    return df[["No_Year", "No_Mes", "MontoAcumulado"]]


def extraer_subsidiaria(client: gspread.Client) -> pd.DataFrame:
    """Pestaña 'Subsidiaria': A=No_Year, B=No_Mes, C=Monto (acumulado), D=IdCuenta (ya viene en la hoja)."""
    df = _leer_pestana(client, WORKSHEET_SUBSIDIARIA, "A:D", ["No_Year", "No_Mes", "MontoAcumulado", "IdCuenta"])
    return df.astype({"IdCuenta": int})


def _a_movimiento_mensual(df: pd.DataFrame, por: str | None = None) -> pd.DataFrame:
    """Convierte montos acumulados en movimientos mensuales (Monto) y arma PeriodoContable.

    Los datos de la hoja son el saldo ACUMULADO a cada corte de mes, pero la tabla del DW
    espera el MOVIMIENTO del mes, como el resto de las transacciones del Balance. Se deriva
    con diff(); el primer mes de cada serie no tiene mes anterior, así que su movimiento es
    su acumulado completo. `por` separa las series cuando hay varias cuentas en la misma hoja.
    """
    df = df.copy()
    df["PeriodoContable"] = pd.to_datetime(df["No_Year"].astype(int).astype(str) + "-" + df["No_Mes"].astype(int).astype(str) + "-01")
    orden = ([por] if por else []) + ["PeriodoContable"]
    df = df.sort_values(orden).reset_index(drop=True)

    series = df.groupby(por)["MontoAcumulado"] if por else df["MontoAcumulado"]
    df["Monto"] = series.diff().fillna(df["MontoAcumulado"])

    # diff() asume meses consecutivos: un hueco metería varios meses de movimiento en uno solo
    meses = df["PeriodoContable"].dt.year * 12 + df["PeriodoContable"].dt.month
    meses_previos = (meses.groupby(df[por]) if por else meses).diff()
    huecos = df[meses_previos.notna() & (meses_previos != 1)]
    if not huecos.empty:
        raise ValueError(f"Hay meses faltantes o repetidos en la hoja; revisar:\n{huecos.to_string()}")
    return df


def transformar_propiedad(df: pd.DataFrame) -> pd.DataFrame:
    """Correción Propiedad: un movimiento mensual registrado como par de cuentas (partida doble)."""
    df = _a_movimiento_mensual(df)
    base = df[["PeriodoContable", "MontoAcumulado", "Monto"]].assign(FK_Reporte=FK_REPORTE_CORPORATIVO, Nota=WORKSHEET_PROPIEDAD)
    return pd.concat(
        [
            base.assign(IdCuenta=ID_CUENTA_PROPIEDAD_POSITIVA),
            base.assign(IdCuenta=ID_CUENTA_PROPIEDAD_NEGATIVA, Monto=lambda x: -x["Monto"]),
        ],
        axis=0,
    ).reset_index(drop=True)


def transformar_subsidiaria(df: pd.DataFrame) -> pd.DataFrame:
    """Subsidiaria: la hoja ya trae IdCuenta por registro, así que el diff() es por cuenta."""
    df = _a_movimiento_mensual(df, por="IdCuenta")
    return df.assign(FK_Reporte=FK_REPORTE_CORPORATIVO, Nota=WORKSHEET_SUBSIDIARIA)[
        ["PeriodoContable", "MontoAcumulado", "Monto", "FK_Reporte", "Nota", "IdCuenta"]
    ]


def generar_cancelacion_global(df: pd.DataFrame) -> pd.DataFrame:
    """Un registro por IdCuenta que revierte todo lo acumulado, fechado en PERIODO_CANCELACION.

    Monto = -(suma de todos los movimientos de la cuenta), así el saldo acumulado de cada
    cuenta queda en 0 a partir de ese periodo. MontoAcumulado = 0 refleja ese saldo final.
    """
    cancelacion = df.groupby("IdCuenta", as_index=False)["Monto"].sum()
    return cancelacion.assign(
        Monto=-cancelacion["Monto"],
        MontoAcumulado=0.0,
        PeriodoContable=PERIODO_CANCELACION,
        FK_Reporte=FK_REPORTE_CORPORATIVO,
        Nota=NOTA_CANCELACION,
    )


def exportar_revision(df_detalle: pd.DataFrame, path: str = EXCEL_REVISION) -> None:
    """Excel de revisión previo a la carga: filas exactas del DW + detalle con el acumulado de origen."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_carga = df_detalle[COLUMNAS_DW]
    # Cuadre de partida doble: por periodo el movimiento total de todas las cuentas debe ser 0
    cuadre = df_carga.groupby("PeriodoContable", as_index=False)["Monto"].sum().rename(columns={"Monto": "SumaMontos"})
    resumen = df_carga.pivot_table(index="PeriodoContable", columns="IdCuenta", values="Monto", aggfunc="sum").reset_index()
    with pd.ExcelWriter(path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        df_carga.to_excel(writer, sheet_name="Carga", index=False)
        df_detalle[["Nota", "IdCuenta", "PeriodoContable", "MontoAcumulado", "Monto"]].sort_values(
            ["Nota", "IdCuenta", "PeriodoContable"]
        ).to_excel(writer, sheet_name="Detalle", index=False)
        resumen.to_excel(writer, sheet_name="Movimiento x Cuenta", index=False)
        cuadre.to_excel(writer, sheet_name="Cuadre", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cargar", action="store_true", help="hace append en el DW (por defecto solo genera el Excel)")
    args = parser.parse_args()

    creds = Credentials.from_service_account_file(os.getenv("GOOGLE_CREDENTIALS"), scopes=SCOPES)
    client = gspread.authorize(creds)

    print(f"Extrayendo '{WORKSHEET_PROPIEDAD}' y '{WORKSHEET_SUBSIDIARIA}'...")
    df_propiedad = transformar_propiedad(extraer_propiedad(client))
    df_subsidiaria = transformar_subsidiaria(extraer_subsidiaria(client))

    df_base = pd.concat([df_propiedad, df_subsidiaria], axis=0).reset_index(drop=True)
    df_cancelacion = generar_cancelacion_global(df_base)
    df_detalle = pd.concat([df_base, df_cancelacion], axis=0).reset_index(drop=True)
    print(
        f"{len(df_detalle)} filas ({len(df_propiedad)} propiedad + {len(df_subsidiaria)} subsidiaria "
        f"+ {len(df_cancelacion)} cancelación global)"
    )

    # Revisión aprobada: la exportación a Excel queda desactivada. Descomentar para volver a revisar antes de cargar.
    # exportar_revision(df_detalle)
    # print(f"Excel de revisión: {EXCEL_REVISION}")

    if not args.cargar:
        print("Sin --cargar: no se modificó el DW.")
        return

    engine = get_sql_engine(server=os.getenv("DW_SERVER"), database=os.getenv("DW_DB_Netsuite"))
    append_dataframe_to_sql(engine, df_detalle[COLUMNAS_DW], DW_SCHEMA, DW_TABLE, FK_REPORTE_CORPORATIVO)
    print(f"Append completo en {DW_SCHEMA}.{DW_TABLE}.")


if __name__ == "__main__":
    main()
