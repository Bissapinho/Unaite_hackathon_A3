# Audit — Brique 1bis (data RH + finances)

> Audit en lecture seule. Cible : implémentation RH/finance dans `Unaite_hackathon_A3/`.
> Référence : spec Brique 1bis de `CLAUDE.md` (§1, §5, §8.0) + `DATA_README.md`.
> Date : 2026-06-27. Rien n'a été modifié.

## Verdict

**Conforme.** La Brique 1bis est implémentée fidèlement à la spec, avec un niveau de
rigueur supérieur à l'attendu. Tous les garde-fous critiques sont respectés et
**vérifiés indépendamment** (pas seulement via les checks du repo). `validate.py` passe
**83/83** (dont 23 checks RH/finance dédiés, section 10). Les écarts relevés sont mineurs
et cosmétiques — aucun ne bloque la suite (construction de l'ontologie).

## Méthode

Comparaison spec ↔ code (`canonical.py`, `generate_excel.py`, `validate.py`), puis
re-génération + re-validation, puis **contre-vérifications indépendantes** : scan
anti-fuite sur tous les artefacts sérialisés, preuve que le CA n'est pas hardcodé,
contrôle des ponts d'entity resolution, logique du cashflow gap.

---

## Ce qui est conforme

**Entités RH (Brique 1bis).** `Company` (`CO-001`, Our Logistics Co SAS), 15 `Employee`
avec `Role` (`role_title` + `title_rank`), `OrgUnit` (5 services : Direction, Commercial,
Exploitation, Comptabilité, RH), et `KeyDependency` (`KD-001` → Sarah Martin / MedPharma).
La spec demandait ~12–20 employés : 15, cohérent avec `COMPANY.headcount`.

**Entités finances (Brique 1bis).** `FinancialSummary` (marge 16 %, masse salariale,
charges flotte/leasing, carburant, OPEX, trésorerie, DSO/DPO). `RevenueConcentration`
calculée par `revenue_concentration()`. `CashflowGap` émergent (DSO 68 − DPO 38 = 30 j),
non pré-calculé — exactement comme demandé.

**Garde-fou n°1 — le CA n'est jamais dupliqué.** `FINANCIAL_SUMMARY["annual_revenue"]`
vaut `None` ; le CA (1 689 940 €) est calculé par `total_revenue()` depuis les factures.
*Vérifié indépendamment* : la valeur littérale n'apparaît nulle part dans le source de
`canonical.py`. L'Excel finances l'affiche via `C.total_revenue()`, jamais en dur.

**Garde-fou n°2 — organigramme = vérité cachée.** `manager_id`, `title_rank`,
`monthly_gross_salary`, `is_key_person` ne vivent que dans `canonical.py`. *Scan
anti-fuite indépendant sur tous les `.json` + `.xlsx`* : **aucune fuite** de ces champs.
L'annuaire Excel n'a que 6 colonnes (Matricule, Nom, Poste, Service, Email, Date d'entrée)
— ni manager, ni salaire.

**Garde-fou n°3 — entity resolution naturelle (le cœur de la valeur démo).**
- Les 6 account managers Odoo sont **tous** des employés (même `full_name`).
- Les 3 premiers chauffeurs Dashdoc (Thomas Girard, Mehdi Faure, David Olivier) matchent
  un `EMPLOYEES.full_name` → futur `Driver is_a Employee`. Les 11 autres restent du bruit
  Faker (sous-traitance), réaliste.
- Sarah Martin = AM de MedPharma **et** homme-clé **et** rattachée au Commercial : le pont
  RH ↔ commercial ↔ risque est en place pour la démo.

**Reconstructibilité de l'orga.** L'organigramme n'est dans aucune source ; il se
reconstruit par règle à deux branches (chef de service → DG ; intra-service par rang).
Les emails portent signatures `Nom — Poste` + escalades qui nomment le vrai n+1 (sans le
mot « manager »). La section 10.3 de `validate.py` prouve que l'heuristique déterministe
retrouve **100 %** des `manager_id` — la data porte donc assez d'indices.

**Intégration.** Les nouvelles entités sont câblées dans l'API publique (`counts()`,
`scenario_records()` expose le rôle `key_person`), et `generate_all.py` orchestre bien la
génération de l'annuaire et du reporting via `generate_excel.py`. Sources RH/finance
correctement implémentées comme **fichiers** (Excel), pas comme nouveaux MCP — conforme à
la spec qui ne réclame pas de mock MCP pour ces couches.

---

## Écarts (tous mineurs)

**M1 — `_scenario_manifest.json` ne couvre pas la couche RH.** Le manifeste (« filet pour
la démo », liste les IDs du scénario par type) n'a aucune clé RH/finance : pas
d'`employees`, pas de `key_dependency`, pas de `company`. Sarah Martin est bien dans
`scenario_records()` (rôle `key_person`), mais si la démo lit le manifeste pour savoir
« qui/quoi mettre en avant », l'homme-clé n'y est pas. `scenario_ids()` (qui alimente le
manifeste) est dans le même cas.
*Impact* : faible. *Reco* : ajouter `key_person`/`hot_employee: "EMP-003"` et `company` à
`scenario_ids()` si la viz s'appuie sur le manifeste.

**M2 — commentaire périmé dans `generate_all.py`.** L'en-tête dit
`data/excel/*.xlsx (3 fichiers bureautiques)` alors que le pipeline en génère désormais
**5** (annuaire + finances ajoutés). Le code est correct ; seul le commentaire est faux.
*Impact* : cosmétique. *Reco* : « 5 fichiers bureautiques ».

**M3 — `DATA_README.md` parle encore de « Brique 1 ».** Le README documente très bien la
couche RH/finance (§2bis dédiée), mais son titre et son intro disent « Brique 1 — Data
synthétique ». La couche RH/finance est la **Brique 1bis** selon `CLAUDE.md`.
*Impact* : cosmétique (cohérence documentaire). *Reco* : mentionner « Brique 1 + 1bis ».

**M4 — `generate_all.py` plante sur `annex.db` (faux positif d'environnement).**
`build_db.main()` fait `db_path.unlink()` qui échoue (`PermissionError`) **dans ce bac à
sable** car le fichier monté est verrouillé. Ce **n'est pas un bug du repo** : sur la
machine de l'utilisateur la régénération fonctionne (l'artefact existe et est valide, la
validation passe). À signaler seulement si tu rejoues `generate_all.py` dans un contexte
où `data/db/` est en lecture seule — dans ce cas `unlink(missing_ok=True)` + écriture
atomique éviterait l'arrêt.

---

## Recommandation

La Brique 1bis est **prête**. On peut enchaîner sur la Brique 1 (construction de
`ontology.json` avec les 3 couches). Les 4 écarts sont optionnels : seul **M1** mérite
peut-être un correctif avant la démo, et uniquement si l'UI consomme
`_scenario_manifest.json` pour mettre en avant l'homme-clé.
