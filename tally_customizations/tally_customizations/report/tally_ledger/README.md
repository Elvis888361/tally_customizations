# Tally Ledger Report

This report provides a Tally-style General Ledger view for individual accounts in ERPNext.

## Features

1. **Tally-Style Format**:
   - Date, Particulars, Vch Type, Vch No, Debit, Credit columns
   - Opening Balance row at the top
   - Closing Balance row at the bottom
   - Total balancing row

2. **Particulars Column**:
   - Shows contra accounts with "To" or "By" prefix (Tally convention)
   - "By" indicates the source of funds (debit transactions)
   - "To" indicates the destination of funds (credit transactions)

3. **Voucher Type Mapping**:
   - Sales Invoice → Sales
   - Purchase Invoice → Purchase
   - Payment Entry → Payment
   - Journal Entry → Journal
   - And more...

## How to Use

1. Navigate to: **Reports > Tally Customizations > Tally Ledger**

2. Set the following filters:
   - **Company** (required): Select your company
   - **Account** (required): Select the account to view (must be a leaf account, not a group)
   - **From Date** (required): Start date of the period
   - **To Date** (required): End date of the period
   - **Party Type** (optional): Filter by party type (Customer, Supplier, etc.)
   - **Party** (optional): Filter by specific party

3. Click **Refresh** to generate the report

## Report Structure

```
Opening Balance                           650,000
Date         Particulars      Vch Type   Vch No   Debit      Credit
----------   --------------   --------   ------   --------   ---------
6-10-2023    To Sales         Sales      3        2,520,000
7-10-2023    By Bank          Receipt    23                  2,520,000
...
Closing Balance                                    0          1,083,000
----------                                         --------   ---------
                                                   22,331,000 22,331,000
```

## Technical Details

### Files
- `tally_ledger.json` - Report metadata
- `tally_ledger.py` - Python logic for data fetching and formatting
- `tally_ledger.js` - JavaScript for filters and client-side formatting

### Key Functions
- `get_opening_balance()` - Calculates balance before from_date
- `get_gl_entries()` - Fetches GL entries for the period
- `format_particulars()` - Formats contra accounts with To/By prefix
- `map_voucher_type()` - Maps ERPNext voucher types to Tally names

## Differences from Standard ERPNext General Ledger

| Feature | ERPNext GL | Tally Ledger |
|---------|-----------|--------------|
| Layout | Multiple columns with account details | Simplified Tally-style columns |
| Particulars | Shows account names only | Shows "To/By" prefix with contra account |
| Voucher Type | Full ERPNext names | Tally-style short names |
| Balance Display | Running balance column | Opening/Closing balance rows |
| Grouping | Multiple grouping options | Single account focus |

## Customization

To customize the report:

1. **Modify voucher type mapping**: Edit `map_voucher_type()` function
2. **Change particulars format**: Edit `format_particulars()` function
3. **Add more columns**: Update `get_columns()` function
4. **Adjust styling**: Modify the formatter in the .js file

## Troubleshooting

**Issue**: Report shows "Please select an Account"
- **Solution**: Ensure you've selected a valid account (not a group account)

**Issue**: No data showing
- **Solution**: Check if there are GL entries for the selected account in the date range

**Issue**: Particulars showing "Various"
- **Solution**: This happens when the GL entry has multiple contra accounts

## Support

For issues or feature requests, please contact your system administrator.
