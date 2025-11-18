# Laboratory Portal

Main SPA for all laboratory users (Admin, Technician, Pathologist).

## Features

### Admin Views
- Tenant configuration
- User management
- LIS connection configuration
- Auto-verification settings
- System health monitoring

### Technician Views
- Review queue
- Sample search and filtering
- Result details with flagged reasons
- Approve/reject workflow

### Pathologist Views
- Escalated review queue
- All samples and results
- Detailed review with clinical comments

## Tech Stack

- Vue.js 3
- Vue Router (role-based routing)
- Pinia (state management)
- Axios (API client)

## Running

```bash
npm install
npm run dev
```

## Building

```bash
npm run build
```
