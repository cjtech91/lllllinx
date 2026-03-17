# PRD — PisoFi Commander

## Original Problem Statement
Build a Piso WiFi system using Linux, SQL, JavaScript, and low CPU usage app behavior, with multiple VLANs for sub-vendo, running on Orange Pi, Raspberry Pi, and x86/x64 (EFI + Legacy), with board pin support for coin, relay, and bill pins. x86/x64 GPIO should be disabled.

## User Choices (Confirmed)
- Full scope MVP: web admin panel + backend API + SQL DB + GPIO control service + VLAN config generator
- SQL engine: SQLite (lightweight, low CPU)
- Voucher logic: time-based PIN vouchers (30m/1h/3h and custom)
- Sub-vendo model: per-sub-vendo VLAN with separate rate limits and sales reports
- Hardware runtime: OPI + RPI GPIO enabled with presets; x86/x64 GPIO disabled

## Architecture Decisions
- Frontend: React + shadcn/ui + axios + recharts
- Backend: FastAPI single service with domain endpoints
- Database: SQLite file (`backend/pisofi.db`) for low-resource devices
- Runtime model: software GPIO event/log handling with board profile validation and x86/x64 guardrails
- Config output: generated Linux VLAN/QoS shell script from app data

## User Personas
1. Piso WiFi owner/operator needing quick voucher and sales handling
2. Small ISP or hotspot reseller managing multiple sub-vendo VLAN zones
3. Field technician configuring board profiles and pin mappings

## Core Requirements (Static)
- Fast, low CPU usage control panel
- Time-based voucher PIN generation and redemption
- VLAN/sub-vendo creation with rate limits
- Sales reporting and trend visibility
- GPIO profile management (OPI/RPI active, x86/x64 disabled)
- Linux config export for deployment

## What’s Implemented
### 2026-03-17
- Built complete multi-page admin panel:
  - Dashboard
  - Vouchers (profile create, PIN generation, PIN redeem)
  - Sub-vendo VLAN manager
  - GPIO/relay/pulse controls + pin map
  - Reports page with metrics and chart
  - Config export page
- Implemented backend API with SQLite persistence:
  - `/api/dashboard/summary`
  - `/api/voucher-profiles`, `/api/vouchers`, `/api/vouchers/generate`, `/api/vouchers/redeem`
  - `/api/subvendos` CRUD
  - `/api/hardware/profiles`, `/api/hardware/profile`, `/api/hardware/pins`
  - `/api/gpio/relay`, `/api/gpio/pulse`, `/api/gpio/events`
  - `/api/reports/sales`, `/api/config/export`
- Added hardware presets:
  - Orange Pi H3/H5
  - Orange Pi Zero 3 (229/228/72)
  - Raspberry Pi (2/3/4)
  - NanoPi H3/H5
  - x86/x64 profile with GPIO disabled
- Added persistent system status widget (CPU/RAM/TEMP + board)
- Added comprehensive `data-testid` coverage for critical UX and controls
- Completed automated testing (backend + frontend) with passing report
- Added deployment documentation:
  - `/app/DEPLOYMENT_MOBAXTERM.md`

## Prioritized Backlog
### P0 (High)
- Split backend monolith (`server.py`) into routers/services for maintainability
- Add explicit loading/error states to all data-fetching pages
- Add authentication/role control for production admin access

### P1 (Medium)
- Add printable voucher ticket template and batch export
- Add editable sub-vendo update form in UI (not delete/create only)
- Add board-specific real GPIO driver adapters (RPi.GPIO/libgpiod/per-board)

### P2 (Lower)
- Add daily auto-backup for SQLite
- Add multi-language labels and localization
- Add richer analytics filters and date ranges

## Next Tasks List
1. Refactor backend into modules (`routers/`, `services/`, `db/`)
2. Add UX loading/error placeholders for all API pages
3. Implement optional secure local admin login
4. Create one-command installer script for board provisioning
