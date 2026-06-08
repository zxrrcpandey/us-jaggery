# US Jaggery

A custom [Frappe](https://frappeframework.com)/[ERPNext](https://erpnext.com) (v15) app
that tailors the **Chart of Accounts** for US Jaggery: a custom **Auto-ID** for every
account, a **Description** field, a reworked Account list/tree, and a one-shot provisioner
that sets up the company alongside [India Compliance](https://github.com/resilient-tech/india-compliance).

---

## Features

### Auto-ID (the client's account identifier)
A custom field **`custom_auto_id`** (label **Auto-ID**) on the Account doctype, kept
separate from ERPNext's native `account_number` so account **names stay clean** (e.g.
`Cash on Hand`, not `1010 - Cash on Hand`).

- **Auto-increments** for new accounts: leaving Auto-ID blank assigns the next number
  **within the account's group** (`max(sibling Auto-IDs) + 1`). It is **collision-safe**
  (skips numbers already used in the company) and **never numbers group/header accounts**.
- **Searchable** — `custom_auto_id` is added to the Account doctype's `search_fields`, so
  typing an Auto-ID in **any account link field (e.g. Journal Entry)** resolves the account.
- Implemented as a `before_insert` doc-event hook so an existing/imported Auto-ID is
  never overwritten — only blank ones are filled.

### Description
A **`custom_description`** (Small Text) field on every Account, shown on the form and as a
list-view column.

### Account list & tree
- **List view** columns: **Auto-ID · Description · Account Name · Status** (the docname
  "ID" / native Account Number columns are hidden). Auto-ID is the first column; accounts
  without one show **—**. Accounts **with** an Auto-ID sort to the top (numeric order).
- **Chart of Accounts tree** shows the Auto-ID in brackets next to each ledger, e.g.
  `BANK OF INDIA [10120]`.

### Chart of Accounts provisioning
`us_jaggery.setup.client_coa` creates the **US Jaggery** company (standard/India chart +
India Compliance GST/TDS accounts), sets up the Auto-ID field, list/tree settings, and can
optionally import the client's 185-account chart (`setup/data/client_accounts.json`),
mapping the source (Sage-style) account types onto ERPNext groups and tagging real bank
accounts as `Bank`.

---

## Project structure

```
us_jaggery/
├── hooks.py                      # doc_events + doctype_list_js / doctype_tree_js
├── overrides/
│   ├── account.py                # Auto-ID auto-increment hook (before_insert)
│   └── account_tree.py           # tree node provider returning custom_auto_id
├── public/js/
│   ├── account_list.js           # list view: hide ID col, Auto-ID first (— when empty),
│   │                             #   non-empty-first sort, formatters
│   └── account_tree.js           # tree view: render "<name> [Auto-ID]"
└── setup/
    ├── client_coa.py             # company + Auto-ID field + views + CoA import
    └── data/client_accounts.json # client's 185-account chart (id, name, type)
```

---

## Provisioning

ERPNext's master fixtures (UOMs, Warehouse Types) come from the setup wizard, so the
provisioner ensures them before creating the company. Order matters: the Auto-ID field
must exist **before** the company is created (the hook reads its column).

Run on a site (use a frappe script if `bench execute` misbehaves on your bench):

```bash
# Full setup, WITHOUT importing the client chart (client builds it manually):
bench --site <site> execute us_jaggery.setup.client_coa.provision --kwargs "{'import_chart': False}"

# Full setup INCLUDING the 185-account client chart:
bench --site <site> execute us_jaggery.setup.client_coa.provision
```

`provision()` runs: erpnext fixtures → Auto-ID field + list/tree settings → create
company → (optionally) import accounts. It is idempotent / re-runnable.

Key functions in `setup/client_coa.py`:

| Function | Purpose |
|---|---|
| `provision(company, import_chart=True)` | one-shot first-time setup |
| `setup_auto_id_field()` | create Auto-ID + Description fields, search/list/title settings |
| `create_company(company)` | create the US Jaggery company (chart + GST/TDS) |
| `import_accounts(company)` | import the 185 client accounts (collision-aware naming) |
| `reimport_with_auto_id(company)` | wipe a prior import and re-import cleanly |

---

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site <site> install-app us_jaggery
bench --site <site> execute us_jaggery.setup.client_coa.provision --kwargs "{'import_chart': False}"
```

Requires `erpnext` and `india_compliance` installed on the site first.

---

## Notes

- Account **names are unique per company** in ERPNext. Because the Auto-ID lives in a
  separate field (not in the name), the importer appends the Auto-ID in parentheses only
  to the handful of accounts whose names would otherwise collide (e.g. an FDR that exists
  as both an asset and a loan-against-it liability).
- The Auto-ID column / tree label / list ordering are served from `public/js`; run
  `bench build --app us_jaggery` after changing those files.

---

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/us_jaggery
pre-commit install
```

Tools: `ruff`, `eslint`, `prettier`, `pyupgrade`.

## License

mit
