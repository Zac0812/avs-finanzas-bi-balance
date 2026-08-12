"""ETL de la reclasificación manual "Activo por derecho de uso vehiculos".

Convierte los montos acumulados de la hoja de Google Sheets mantenida por
contabilidad en movimientos mensuales, y los carga (reemplazo completo) en
Netsuite.ReclasificacionesContables (ver src/tablas.sql).
"""

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

SPREADSHEET_ID = "1R_iFnlj-cIOlDPBL0af3fbSIL2a1E47QIRM6ZOkhyYg"
WORKSHEET_NAME = "data autos propiedad"
DESCRIPCION = "Activo por derecho de uso vehiculos, neto"

# Valor fijo del reporte de Balance General en Netsuite.Accounts_Reports
FK_REPORTE_BALANCE = 2
# Par activo / contra-activo asignado a esta reclasificación (ver src/tablas.sql)
ID_CUENTA_ACTIVO = 276000
ID_CUENTA_CONTRA_ACTIVO = 276001

DW_SCHEMA = "Netsuite"
DW_TABLE = "ReclasificacionesContables"
SQL_DRIVER = "ODBC Driver 17 for SQL Server"


def get_sql_engine(server: str, database: str, driver: str = SQL_DRIVER) -> Engine:
    """Retorna un Engine de SQLAlchemy (autenticación Windows) listo para Pandas."""
    driver_encoded = driver.replace(" ", "+")
    conn_str = f"mssql+pyodbc://{server}/{database}?driver={driver_encoded}&trusted_connection=yes"
    return create_engine(conn_str)


def load_dataframe_to_sql(engine: Engine, df: pd.DataFrame, schema: str, table: str, mode: str = "delete") -> None:
    """Vacía una tabla del DW (DELETE o TRUNCATE) e inserta el DataFrame, en una sola transacción."""
    tabla_completa = f"{schema}.{table}"
    clear_stmt = "TRUNCATE TABLE" if mode == "truncate" else "DELETE FROM"
    with engine.begin() as conn:
        conn.execute(text(f"{clear_stmt} {tabla_completa}"))
        df.to_sql(schema=schema, name=table, con=conn, if_exists="append", index=False, chunksize=500, method="multi")


def extraer_vehiculos_propiedad(client: gspread.Client) -> pd.DataFrame:
    """Lee la hoja de reclasificación manual y retorna los montos acumulados por mes.

    Esta reclasificación no vive en NetSuite ni tiene ID de cuenta propio: contabilidad
    la mantiene a mano en Google Sheets porque hoy no hay otra forma de capturarla
    (ver REDME.md). Por eso este ETL empieza en una hoja y no en una consulta a NetSuite.
    """
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    # UNFORMATTED_VALUE: necesitamos MontoAcumulado como número, no como texto con formato
    data_range = worksheet.get("A:D", value_render_option="UNFORMATTED_VALUE")
    # La hoja trae su propio encabezado en la fila 1; lo reemplazamos por nombres fijos
    # (data_range[1:] descarta esa fila) para no depender de que nadie edite el título de la columna
    headers = ["No_Year", "No_Mes", "Descripcion", "MontoAcumulado"]
    records = [dict(zip(headers, row)) for row in data_range[1:]]
    df = pd.DataFrame(records)
    # La hoja puede tener más de una reclasificación a futuro; hoy solo procesamos esta.
    # El orden cronológico es obligatorio: transformar_reclasificacion() depende de él para el diff().
    return df.query("Descripcion == @DESCRIPCION").sort_values(by=["No_Year", "No_Mes"]).reset_index(drop=True)


def transformar_reclasificacion(df_vehiculos: pd.DataFrame) -> pd.DataFrame:
    """Convierte montos acumulados en movimientos mensuales, listos para el DW.

    La hoja de contabilidad reporta el saldo ACUMULADO a cada corte de mes (ej. "a
    marzo llevamos $130"), pero Netsuite.ReclasificacionesContables espera el
    MOVIMIENTO de ese mes (ej. "en marzo bajó $20"), igual que el resto de las
    transacciones del Balance. Por eso se deriva con diff() en vez de cargar el
    acumulado tal cual.
    """
    df = df_vehiculos.copy()

    # diff() = acumulado de este mes menos el del mes anterior = movimiento del mes.
    # El primer mes no tiene "mes anterior" (diff() da NaN ahí), así que su movimiento
    # es simplemente su acumulado completo: fillna cubre justo ese primer registro.
    df["Monto"] = df["MontoAcumulado"].diff().fillna(df["MontoAcumulado"])
    df["PeriodoContable"] = pd.to_datetime(df["No_Year"].astype(str) + "-" + df["No_Mes"].astype(str) + "-01")
    # Identifica esta reclasificación como parte del reporte de Balance General (no P&L)
    df["FK_Reporte"] = FK_REPORTE_BALANCE
    df = df[["FK_Reporte", "PeriodoContable", "Monto"]]

    # src/tablas.sql ya reserva 276000/276001 como el par activo / contra-activo de esta
    # reclasificación (partida doble): el mismo movimiento se registra dos veces, una vez
    # con signo positivo y otra negado, para que ambas cuentas del Balance sigan cuadrando
    # entre sí exactamente como cualquier otra transacción de NetSuite.
    return pd.concat(
        [
            df.assign(IdCuenta=ID_CUENTA_ACTIVO, Monto=lambda x: -x["Monto"]),
            df.assign(IdCuenta=ID_CUENTA_CONTRA_ACTIVO),
        ],
        axis=0,
    ).reset_index(drop=True)


def main() -> None:
    creds = Credentials.from_service_account_file(os.getenv("GOOGLE_CREDENTIALS"), scopes=SCOPES)
    client = gspread.authorize(creds)

    print(f"Extrayendo '{WORKSHEET_NAME}'...")
    df_vehiculos = extraer_vehiculos_propiedad(client)

    df_reclasificacion = transformar_reclasificacion(df_vehiculos)
    print(f"{len(df_reclasificacion)} filas listas para cargar en {DW_SCHEMA}.{DW_TABLE}")

    engine = get_sql_engine(server=os.getenv("DW_SERVER"), database=os.getenv("DW_DB_Netsuite"))
    load_dataframe_to_sql(engine=engine, df=df_reclasificacion, schema=DW_SCHEMA, table=DW_TABLE, mode="delete")
    print("Carga completa.")


if __name__ == "__main__":
    main()
