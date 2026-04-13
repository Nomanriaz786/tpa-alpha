---
description: "TPA Alpha admin panel with payment networks and affiliate management. Use GitHub for version control (user: Nomanriaz786, email: muhammadnomanriaz599@gmail.com). Deploy via SSH to AWS (3.93.192.182, sandra.pem key)."
---

# TPA Alpha Project Instructions

## 🎯 Project Overview

**TPA Alpha** is an admin control panel built with:
- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Backend**: Python FastAPI
- **Database**: SQLite (references in db/ folder)
- **Hosting**: AWS EC2 Ubuntu with Nginx + Let's Encrypt

---

## 🔐 Credentials Reference

| Service | Value |
|---------|-------|
| GitHub User | `Nomanriaz786` |
| GitHub Email | `muhammadnomanriaz599@gmail.com` |
| GitHub Token | `<SECRET_SEE_TEAM>` |
| GitHub Repo | https://github.com/Nomanriaz786/tpa-alpha.git |
| Server Address | `3.93.192.182` |
| Server Domain | `3-93-192-182.nip.io` |
| SSH User | `ubuntu` |
| SSH Key | `sandra.pem` (in project root) |
| App Path | `/var/www/tpa-alpha` |

---

## 📋 Key Files & Locations

```
tpa-alpha-bot/
├── frontend/
│   ├── src/features/settings/SettingsPage.tsx    ← Main admin settings page
│   ├── src/components/ui/                         ← UI components
│   ├── src/lib/format.ts                          ← Utility functions (.gitignored)
│   ├── src/lib/utils.ts                           ← Class name utils (.gitignored)
│   ├── dist/                                      ← Production build (nginx root)
│   └── package.json
├── backend/
│   ├── main.py                                     ← FastAPI entry
│   ├── admin_api/                                  ← Admin endpoints
│   ├── services/                                   ← Business logic
│   └── requirements.txt
└── deploy/
    └── systemd-*.service                           ← Service definitions
```

---

## 🚀 DEPLOYMENT WORKFLOW

**ALWAYS follow this sequence:**

### 1. Local Development
```bash
cd f:\MyProjects\discord_bot
# Make code changes
# Test locally if needed
git add .
git commit -m "descriptive message"
git push origin main
```

### 2. Deploy to Server
```bash
ssh -i "f:\MyProjects\discord_bot\sandra.pem" -o StrictHostKeyChecking=no ubuntu@3.93.192.182

# Full deployment (repeat each time):
sudo rm -rf /var/www/tpa-alpha
cd /var/www
GITHUB_TOKEN="<your-token>"  # Use actual token
GITHUB_REPO="https://${GITHUB_TOKEN}@github.com/Nomanriaz786/tpa-alpha.git"
sudo git clone $GITHUB_REPO tpa-alpha
sudo chown -R ubuntu:ubuntu /var/www/tpa-alpha

cd /var/www/tpa-alpha/tpa-alpha-bot/frontend
npm install
npm run build

cat /var/www/tpa-alpha/tpa-alpha-nginx.conf | sed 's|/home/ubuntu/apps/tpa-alpha-bot|/var/www/tpa-alpha/tpa-alpha-bot|g' > /tmp/tpa-alpha-nginx.conf
sudo cp /tmp/tpa-alpha-nginx.conf /etc/nginx/sites-available/tpa-alpha
sudo ln -sf /etc/nginx/sites-available/tpa-alpha /etc/nginx/sites-enabled/tpa-alpha
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Verify
```bash
# Test frontend
https://3-93-192-182.nip.io/settings

# Should see:
✅ Settings page loads
✅ Billing section visible
✅ Save button in footer (NOT at top)
✅ No console errors (F12)
```

---

## 🔍 Common Tasks

### Frontend Development
```bash
cd tpa-alpha-bot/frontend
npm install           # Install deps
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Production build
npm run build 2>&1 | grep -i error  # Check for errors
```

### Build & Deploy
```bash
# See: .github/instructions/deployment.instructions.md
# Full deployment guide with all commands
```

### Check Deployment Status
```bash
# From server:
curl -s -k https://3-93-192-182.nip.io/ | head -20  # Test HTML
curl -I -k https://3-93-192-182.nip.io/assets/index-Cy5SY32s.css  # Test CSS
sudo systemctl status nginx  # Check nginx
```

---

## ⚠️ IMPORTANT NOTES

1. **lib/ folder is .gitignored**: Files `src/lib/format.ts` and `src/lib/utils.ts` won't be in git. Copy them to server if build fails.

2. **SSH Key Required**: Deployment must use `sandra.pem`. No password SSH configured.

3. **Full Cleanup on Deploy**: Each deployment removes old code completely (`sudo rm -rf /var/www/tpa-alpha`). Don't use for incremental updates—always full rebuild.

4. **Nginx must be reloaded**: After pulling code, always run `sudo systemctl reload nginx` to serve new build.

5. **TypeScript strict mode**: All frontend code must pass TypeScript compilation (0 errors).

---

## 🔗 Full Deployment Reference

For complete deployment instructions including credentials, troubleshooting, and rollback procedures, see:
**→ `.github/instructions/deployment.instructions.md`**

---

## 📞 Quick Reference Links

- GitHub Repo: https://github.com/Nomanriaz786/tpa-alpha.git
- Live App: https://3-93-192-182.nip.io
- Settings Page: https://3-93-192-182.nip.io/settings
- App Path: `/var/www/tpa-alpha` (server)
- Frontend Root: `/var/www/tpa-alpha/tpa-alpha-bot/frontend/dist` (nginx)

---

## 📝 File Naming & Conventions

- **Settings Page**: `SettingsPage.tsx` (React component)
- **Services**: `admin_api/` folder (API endpoints)
- **Build Output**: `frontend/dist/` (optimized for nginx)
- **Config**: `tpa-alpha-nginx.conf` (nginx reverse proxy)
- **Credentials**: Stored locally, NOT in git

---

## ✅ Pre-Deployment Checklist

Before pushing code:
- [ ] Code changes tested locally
- [ ] TypeScript: 0 errors
- [ ] Committed to git with descriptive message
- [ ] Ready to push to main branch

Before running server deployment:
- [ ] Code pushed to GitHub
- [ ] SSH key (sandra.pem) available
- [ ] Server accessible (ping 3.93.192.182)
- [ ] Have GitHub token ready

---

This workspace follows the TPA Alpha deployment standards. Refer to `.github/instructions/deployment.instructions.md` for the complete, step-by-step deployment guide.
