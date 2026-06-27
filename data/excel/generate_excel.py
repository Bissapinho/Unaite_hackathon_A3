"""generate_excel.py — Génère 3 fichiers .xlsx depuis canonical.py (source de vérité).

Tout vient de `data.canonical`. Aucune valeur métier en dur.
Idempotent : réécrit les fichiers à chaque exécution. Lançable seul.
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data import canonical as C  # noqa: E402

from openpyxl import Workbook  # noqa: E402

EXCEL_DIR = ROOT / "data" / "excel"


def _write_sheet(filename: str, headers: list[str], rows: list[list]) -> int:
    """Écrit un classeur (1 feuille) : en-têtes + lignes. Retourne le nb de lignes de données."""
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    path = EXCEL_DIR / filename
    wb.save(path)
    return len(rows)


def _fmt_euros(amount) -> str:
    """Formate un montant en euros lisibles, ex. 2400 -> '€2,400'."""
    return f"€{amount:,}"


def main() -> None:
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Carrier backup matrix
    backup_headers = ["Route", "Backup Carrier", "Max Cold Chain Capacity", "Emergency Rate"]
    backup_rows = [
        [r["route"], r["backup_carrier"], r["max_cold_chain_capacity"], _fmt_euros(r["emergency_rate"])]
        for r in C.CARRIER_BACKUP_MATRIX
    ]
    n_backup = _write_sheet("carrier_backup_matrix.xlsx", backup_headers, backup_rows)

    # 2. Customer priority list
    customer_headers = ["Customer", "Priority Tier", "Account Manager", "Escalation Required"]
    customer_rows = [
        [
            c["name"],
            c["priority_tier"],
            c["account_manager"],
            "Yes" if c["priority_tier"] == "Platinum" else "No",
        ]
        for c in C.CUSTOMERS
    ]
    n_customers = _write_sheet("customer_priority_list.xlsx", customer_headers, customer_rows)

    # 3. Warehouse inventory snapshot
    inventory_headers = ["Warehouse", "SKU", "Available Units", "Reserved Units"]
    inventory_rows = [
        [r["warehouse_id"], r["sku"], r["available_units"], r["reserved_units"]]
        for r in C.INVENTORY
    ]
    n_inventory = _write_sheet("warehouse_inventory_snapshot.xlsx", inventory_headers, inventory_rows)

    # 4. Annuaire interne (RH) — SANS hiérarchie (pas de colonne Manager / N+1).
    #    Un annuaire liste QUI travaille là et à quel poste, PAS qui commande qui.
    #    La hiérarchie se reconstruit en croisant Poste (rang implicite) + Service
    #    + signatures/escalades d'emails. NE JAMAIS exposer manager_id ni salaire ici.
    directory_headers = ["Matricule", "Nom", "Poste", "Service", "Email", "Date d'entrée"]
    directory_rows = [
        [e["employee_id"], e["full_name"], e["role_title"], e["org_unit"],
         e["email"], e["hire_date"]]
        for e in C.EMPLOYEES
    ]
    n_directory = _write_sheet("company_directory.xlsx", directory_headers, directory_rows)

    # 5. Reporting de gestion — agrégats société + concentration du CA par client.
    #    Aucune valeur de CA en dur : tout vient des helpers de canonical.py.
    fs = C.FINANCIAL_SUMMARY
    finance_headers = ["Poste", "Valeur"]
    finance_rows = [
        ["Période", fs["period"]],
        ["Chiffre d'affaires (CA, 12 mois)", _fmt_euros(C.total_revenue())],
        ["Masse salariale (mensuelle)", _fmt_euros(fs["payroll_monthly"])],
        ["Charges flotte / leasing (mensuel)", _fmt_euros(fs["fleet_leasing_monthly"])],
        ["Carburant (mensuel)", _fmt_euros(fs["fuel_monthly"])],
        ["Autres OPEX (mensuel)", _fmt_euros(fs["other_opex_monthly"])],
        ["Marge brute %", f"{fs['gross_margin_pct']:.1%}"],
        ["DSO (encaissement clients, jours)", fs["dso_days"]],
        ["DPO (paiement fournisseurs, jours)", fs["dpo_days"]],
        ["Trésorerie disponible", _fmt_euros(fs["cash_on_hand"])],
        [],  # séparateur
        ["Concentration du CA par client", ""],
        ["Client", "CA", "Part %"],
    ]
    for r in C.revenue_concentration():
        finance_rows.append([r["name"], _fmt_euros(r["revenue"]), f"{r['share']:.1%}"])
    n_finance = _write_sheet("finances_summary.xlsx", finance_headers, finance_rows)

    print("Fichiers Excel générés dans", EXCEL_DIR)
    print(f"  carrier_backup_matrix.xlsx       : {n_backup} lignes")
    print(f"  customer_priority_list.xlsx      : {n_customers} lignes")
    print(f"  warehouse_inventory_snapshot.xlsx: {n_inventory} lignes")
    print(f"  company_directory.xlsx           : {n_directory} lignes")
    print(f"  finances_summary.xlsx            : {n_finance} lignes")


if __name__ == "__main__":
    main()
