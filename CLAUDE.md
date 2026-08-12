# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Ignore: The file `Notas.md`

## Project purpose

ETL pipeline feeding a Power BI report of the company's Balance General (balance sheet). It reconciles NetSuite's native chart of accounts with a manually-maintained "Comite" (committee) classification, and layers in manual accounting reclassifications that only exist in a Google Sheet — into a SQL Server data warehouse table.

Context (see [REDME.md](REDME.md), in Spanish) — the "Comite" balance sheet requires a manual reclassification (e.g. "Activo por derecho de uso vehiculos") maintained by the accounting team in a Google Sheet tab with no account IDs or structured storage. This repo's job is to extract that sheet, transform it into dated, per-account amounts, and load it into a DW table on a schedule, since accounting cannot provide it any other way today.

## Status

This is an early-stage project. There is no production Python source yet — `src/` currently only holds the target table DDL. The working ETL logic lives as a prototype notebook at [test/BalanceGeneralPruebas.ipynb](test/BalanceGeneralPruebas.ipynb) and is the reference implementation to port into `src/` when productionizing.

## Setup & running

```
pip install -r requirements.txt
```

No build, lint, or automated test tooling is configured. To run/iterate on the ETL logic, open the notebook in Jupyter:

```
jupyter notebook test/BalanceGeneralPruebas.ipynb
```

Requires local ODBC drivers to be installed for `pyodbc` to connect:
- `NetSuite Drivers 64bit` (NetSuite/Oracle analytics connector)
- `ODBC Driver 17 for SQL Server` (target DW)

### Environment / credentials

Config is loaded via `python-dotenv` from a git-ignored `.env`. Required variables:
- `GOOGLE_CREDENTIALS` — path to the Google service account JSON (see `credenciales/`, git-ignored)
- `ORACLE_USER`, `ORACLE_PASS`, `ORACLE_HOST`, `ORACLE_PORT`, `ORACLE_ROLE_ID`, `ORACLE_ACCOUNT_ID` — NetSuite (via Oracle ODBC) connection
- `DW_SERVER`, `DW_DB_Netsuite` — target SQL Server data warehouse (`DW-GOMEX` / `RAW_NS`)

Never read or print `.env` or `credenciales/*.json` contents back to the user.

## Architecture / data flow

The pipeline joins three sources and lands the result in one DW table:

1. **NetSuite account catalog** — pulled live via `pyodbc` from NetSuite's `Account` table (Oracle ODBC connector, see `get_oracle_conn`). This is the authoritative list of account IDs (`id`, `acctnumber`, `fullname`, `accttype`, `isinactive`).
2. **Comite mapping sheet** (Google Sheet "Mapeo Balance General Comite-Netsuite", tab `Mapeo`) — hand-maintained crosswalk from NetSuite account number to the 3-level NetSuite hierarchy (`L1/L2/L3_Netsuite`) and the 3-level Comite hierarchy (`L1/L2/L3_Comite`) used in the final report. Joined to (1) on account number to resolve NetSuite account IDs for every Comite-mapped account.
3. **NetSuite transaction balances** — a NetSuite SQL query aggregates `transactionLine`/`TransactionAccountingLine` by account, accounting period, subsidiary (`subsidiary = 2`) into monthly net amounts, filtered to the account IDs resolved in step 2.
4. **Manual reclassification sheet** (separate Google Sheet, tab `data autos propiedad`) — accounting's manual adjustments (currently just "Activo por derecho de uso vehiculos"), which have no account ID or period key of their own. The notebook derives monthly deltas from the sheet's cumulative amounts (`.diff()`), assigns a hardcoded `FK_Reporte` and pair of `IdCuenta` values (asset/contra-asset split), and produces rows shaped like the DW target table.

Only step 4's output is currently loaded to SQL Server, into `Netsuite.ReclasificacionesContables` (schema in [src/tablas.sql](src/tablas.sql): `FK_Reporte`, `PeriodoContable`, `IdCuenta`, `Monto`, `Nota`) on server `DW-GOMEX`, database `RAW_NS`. Loading is delete-then-append per `load_dataframe_to_sql` (whole-table `DELETE`/`TRUNCATE` + `df.to_sql` in one transaction) — there is no incremental/upsert logic, so any load is a full replace.

Steps 1–3 (`df_MapeoBalance`, `df_Balance`, `df_resumen`) currently only produce a local Excel summary (`Resumen.xlsx`) for validation — they are not yet part of an automated load. When extending this pipeline, keep new account-hierarchy/aggregation logic aligned with this existing merge pattern (account number is the join key between NetSuite and the mapping sheet; NetSuite account `id` is the join key between the mapping sheet and transaction balances).

Google Sheets access uses a service account (`gspread` + `google-auth`) scoped to `spreadsheets` and `drive`; each sheet is opened by its spreadsheet ID (visible in the sheet URLs referenced in [REDME.md](REDME.md)).
