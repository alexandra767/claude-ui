# GigLedger Project Overview

*Category: general | Saved: 2026-03-25 00:02*

# GigLedger - Project Overview

**Purpose**: Comprehensive financial tracking and tax preparation app for gig workers (DoorDash, Uber, etc.) that automates mileage tracking, expense management, and generates Schedule C tax documents.

## Core Data Models

### MileageTrip (21KB)
- **Purpose enum**: delivery, pickup, betweenGigs, toFromFirstLast, maintenance, supplies, commute, other
- **Deductibility**: Only `.commute` and `.other` are non-deductible
- **GPS tracking**: Stores route coordinates as encoded Data
- **Business status**: Auto-syncs with purpose (commute/other = personal)
- **Tax calculations**: Automatic mileage deduction at IRS rates
- **Trip splitting**: Can split long trips at specified GPS points

### ScheduleCPreview (13KB)
- **Part I - Income**: Gross receipts, returns, COGS, other income
- **Part II - Expenses**: 20+ expense categories mapped to Schedule C lines
- **Part III - Net Profit**: Line 31 net profit calculation
- **Schedule SE**: Self-employment tax (15.3% × 92.35% of net profit)

### EarningsEntry
- Tracks daily earnings from platforms (gross, tips, bonuses, hours, miles)

### Expense
- Individual expense items with Schedule C line mapping and business % allocation

## Core Services

### ScheduleCService (8KB)
- `generateScheduleC()` - Main computation engine
- Maps earnings/mileage/expenses to Schedule C lines
- Computes home office deduction (simplified method: $5/sq ft, max 300 sq ft)
- Computes self-employment tax with Additional Medicare Tax support

### ExportService (87KB)
- **CSV exports**: Earnings, Mileage, Expenses, AllData combined
- **PDF exports**: Schedule C formatted report, Tax Packet PDF (comprehensive multi-page document)

### CSVImportService (13KB)
- Auto-detects DoorDash vs Uber format
- RFC 4180 compliant parser (handles quoted fields, escaped quotes)
- Column mapping and validation
- Duplicate detection and parse warnings

### AutoTrackingService (66KB)
- Background trip detection with notifications
- GPS-based auto-tracking for active gig sessions

## App Structure
```
GigLedger/
├── Models/              # Data layer (SwiftData + plain structs)
├── Services/           # Business logic
├── ViewModels/         # SwiftUI view models
├── Views/              # SwiftUI views
│   ├── Dashboard/
│   ├── Earnings/
│   ├── Mileage/
│   ├── Expenses/
│   └── Taxes/
└── GigLedgerApp.swift
```

## Key Features
1. Auto GPS Tracking with background trip detection
2. Trip Classification (Business/Personal) with user review
3. Tax Deduction Calculator with real-time Schedule C preview
4. CSV Imports from DoorDash/Uber earnings
5. Multi-platform Support (iPhone, iPad, Apple Watch, Widgets)
6. Schedule C PDF Export for printable tax documents
7. Home Office Deduction support (simplified method)

## Tax Logic Highlights

**Mileage Deduction**:
- Only confirmed business trips count
- Deduction = totalMiles × IRS.standardMileageRate (e.g., $0.67/mile for 2025)

**Self-Employment Tax**:
- SE tax = 92.35% of net profit × 15.3%
- 12.4% Social Security + 2.9% Medicare
- Additional Medicare Tax support for high earners

**Home Office Deduction**:
- Simplified method: $5 per sq ft
- Maximum 300 sq ft = $1,500 deduction

## User Flow
1. User enables GPS auto-tracking
2. App detects trips and requires classification
3. User reviews and confirms business/Personal status
4. Earnings imported from CSV or entered manually
5. Expenses recorded with business % allocation
6. Schedule C generated with all deductions
7. Tax packet exported as PDF for accountant/IRS