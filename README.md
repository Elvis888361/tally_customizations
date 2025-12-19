### Tally Customizations

A custom ERPNext app that provides Tally-style accounting reports and features for users who are familiar with Tally ERP.

## Features

### 1. Tally Ledger Report

A General Ledger report that mimics the exact look and feel of Tally's Ledger Account view, including:

- **Tally-style columns**: Date, Particulars, Vch Type, Vch No, Debit, Credit
- **To/By notation**: Particulars column shows "To" or "By" prefix with contra accounts (Tally convention)
- **Opening and Closing Balance**: Displayed as separate rows
- **Total balancing**: Both debit and credit sides balance at the bottom
- **Simplified voucher types**: Maps ERPNext voucher types to Tally-style names (e.g., "Sales Invoice" → "Sales")

### Access the Report

After installation, navigate to:
**Reports → Tally Customizations → Tally Ledger**

### Report Filters

- **Company** (required): Select your company
- **Account** (required): Select the ledger account to view
- **From Date** & **To Date** (required): Date range for the report
- **Party Type** & **Party** (optional): Filter by specific customer/supplier

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench --site your-site-name install-app tally_customizations
```

For local development/testing (already installed on local.net):
```bash
cd /home/frappe/frappe-bench
bench --site local.net install-app tally_customizations
```

## Usage

### Accessing the Tally Ledger Report

1. Log in to your ERPNext site
2. Navigate to: **Reporting → Tally Customizations → Tally Ledger**
3. Set the required filters:
   - Company
   - Account (select a ledger account, not a group)
   - Date range (From Date and To Date)
4. Click **Refresh** to generate the report

### Understanding the Report

The report displays transactions in Tally format:

```
Opening Balance                           [Amount]

Date       Particulars      Vch Type    Vch No    Debit      Credit
---------- ---------------- ----------- --------- ---------- ----------
1-5-2023   By Opening...                          650,000
6-10-2023  To Sales         Sales       3         2,520,000
7-10-2023  By Bank          Receipt     23                   2,520,000

Closing Balance                                    [Amount]
---------- ---------------- ----------- --------- ---------- ----------
                                                   Total      Total
```

### Key Differences from Standard ERPNext GL

| Feature | Standard ERPNext GL | Tally Ledger |
|---------|-------------------|--------------|
| Column Layout | Account, Party, Voucher, Debit, Credit, Balance | Date, Particulars, Vch Type, Vch No, Debit, Credit |
| Particulars | Account names | "To/By" prefix with contra account |
| Balance | Running balance column | Opening/Closing balance rows |
| Voucher Names | Full names (Sales Invoice) | Tally style (Sales) |

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/tally_customizations
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
