# GigLedger Tax Features

*Category: general | Saved: 2026-03-25 06:19*

# GigLedger Tax Features

## Schedule C Generation & Tax Calculations

### Schedule C Part I - Income
- **Line 1**: Gross receipts from all gig platforms
- **Line 2**: Returns and allowances
- **Line 4**: Cost of goods sold (COGS)
- **Line 6**: Other income (tips, bonuses, rewards)
- **Line 7**: Total income (Line 1 - Line 2 - Line 4 + Line 6)

### Schedule C Part II - Expenses
20+ expense categories mapped to Schedule C lines:

| Line | Category | Examples |
|------|----------|----------|
| 8 | Car and truck expenses | Mileage deductions at IRS standard rate |
| 9 | Leases/rent | Phone plans, workspace rental |
| 10 | Repairs and maintenance | Vehicle repairs, equipment fixes |
| 11 | Supplies | Gloves, bags, phone mounts |
| 12 | Taxes and licenses | Business licenses, permits |
| 13 | Utilities | Phone service, internet |
| 14 | Insurance | Vehicle insurance, business insurance |
| 15 | Other expenses | Miscellaneous business costs |

### Mileage Deduction Engine
- **IRS Standard Mileage Rate**: ~$0.67/mile (2025 rate)
- **Automatic calculation**: Total business miles × rate
- **Trip classification**: Only `.delivery`, `.pickup`, `.betweenGigs`, `.toFromFirstLast` count
- **Non-deductible**: `.commute` (home to first gig, last gig to home) and `.other`

### Home Office Deduction
**Simplified Method**:
- **Rate**: $5 per square foot
- **Maximum**: 300 sq ft = $1,500 deduction
- **Eligibility**: Regular and exclusive business use space

### Schedule SE - Self-Employment Tax
**Calculation Formula**:
```
Net Profit × 92.35% × 15.3% = SE Tax
```

**Breakdown**:
- **Social Security**: 12.4% (on first $160,200 of net profit)
- **Medicare**: 2.9% (on all net profit)
- **Additional Medicare Tax**: 0.9% for high earners (income > $200k)

**Example**:
- Net Profit: $50,000
- SE Tax: $50,000 × 92.35% × 15.3% = $7,077.23

### Tax Withholding & Set-Aside
- **Recommended quarterly estimate**: 25-30% of net income
- **Automatic calculations**: Real-time tax liability preview
- **Set-aside tracking**: Track how much you've saved for taxes

### Estimated Tax Payments (Quarterly)
- **Q1**: January 15 (for income Jan-Mar)
- **Q2**: April 15 (for income Apr-Jun)
- **Q3**: July 15 (for income Jul-Sep)
- **Q4**: October 15 (for income Oct-Dec)

### Tax Packet Export
**Includes**:
- Full Schedule C report
- Schedule SE calculation
- Mileage log with dates, routes, and classifications
- Expense itemization
- Income summary by platform
- Home office deduction worksheet

## Key Tax Benefits for Gig Workers

1. **Mileage Deduction**: Business miles × $0.67
2. **Vehicle Expenses**: Gas, maintenance, insurance (actual or standard)
3. **Phone & Internet**: Business-use percentage
4. **Home Office**: Up to $1,500 with simplified method
5. **Supplies & Equipment**: All business purchases deductible
6. **Health Insurance**: Premiums deductible (subject to limits)
7. **Retirement Contributions**: SEP IRA, Solo 401(k)

## IRS Compliance
- All calculations follow IRS Pub 535 (Business Expenses)
- Mileage rates updated annually
- Schedule C format follows current tax year requirements
- Audit-ready documentation with full GPS tracking logs

## Year-End Reporting
- **1099-K reconciliation**: Compare app earnings vs. platform 1099s
- **Tax year closing**: Lock data, generate final reports
- **Archive access**: Historical data for prior year filings