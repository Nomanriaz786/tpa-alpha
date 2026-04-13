# TPA Alpha Bot

Discord bot and admin portal for subscription/affiliate management.

## Deployment Information

### Production Server

- **Server IP:** `3.93.192.182`
- **Domain:** `https://3-93-192-182.nip.io`
- **Project Path:** `/home/ubuntu/apps/tpa-alpha-bot`
- **SSH Access:** `ssh -i sandra.pem ubuntu@3.93.192.182`
- **PEM Key Location:** `f:\MyProjects\discord_bot\sandra.pem`

### Deployment Process

1. **Copy Changed Files**
   ```bash
   scp -i sandra.pem <local-file> ubuntu@3.93.192.182:/home/ubuntu/apps/tpa-alpha-bot/<path>/
   ```

2. **Frontend Rebuild** (from server)
   ```bash
   cd /home/ubuntu/apps/tpa-alpha-bot/frontend
   npm run build
   ```

3. **Server Cleanup** (remove temp files)
   ```bash
   rm -f /home/ubuntu/*.sql /home/ubuntu/*.mjs /home/ubuntu/*.sh /home/ubuntu/*.py /home/ubuntu/*.tar.gz
   ```

### Key Directories

- **Frontend:** `/home/ubuntu/apps/tpa-alpha-bot/frontend`
- **Backend:** `/home/ubuntu/apps/tpa-alpha-bot/backend`  
- **Bot Code:** `/home/ubuntu/apps/tpa-alpha-bot/bot`

### Frontend Architecture

- **Framework:** React 19 + Vite
- **Build:** `npm run build` outputs to `dist/`
- **Pages:**
  - `/login` - Admin login
  - `/dashboard` - Dashboard (protected)
  - `/subscribers` - Subscriber management with TradingView username column
  - `/affiliates` - Promo code management
  - `/settings` - Admin settings

### Recent Changes

- **2026-04-11:** Added TradingView username column to subscriber table with copy functionality in both table rows and detail modal.

## Local Development

```bash
cd frontend
npm install
npm run dev
```

## Documentation

See [live-url-report.md](docs/live-url-report.md) for API endpoints and protected routes.
