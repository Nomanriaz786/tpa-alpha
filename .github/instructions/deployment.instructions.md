---
description: "Use when deploying TPA Alpha to production. Covers end-to-end workflow: make local changes → test → commit → push → SSH to server → pull code → build → restart services. Includes all credentials, server paths, and verification steps."
name: "TPA Alpha Deployment Workflow"
---

# TPA Alpha Deployment Instructions

## 🔐 Credentials & Access

### GitHub
- **Repository**: https://github.com/Nomanriaz786/tpa-alpha.git
- **GitHub Username**: `Nomanriaz786`
- **GitHub Email**: `muhammadnomanriaz599@gmail.com`
- **GitHub Token**: Contact team or check `.vscode/settings.json` (SECRET - not in git)

### Server Access
- **Address**: `3.93.192.182`
- **Domain**: `3-93-192-182.nip.io`
- **Username**: `ubuntu`
- **SSH Key**: `sandra.pem` (located at `f:\MyProjects\discord_bot\sandra.pem`)
- **App Path**: `/var/www/tpa-alpha`
- **Frontend Root**: `/var/www/tpa-alpha/tpa-alpha-bot/frontend/dist`

### SSL/HTTPS
- **Domain**: `3-93-192-182.nip.io`
- **Certificate**: Let's Encrypt (auto-configured)
- **Nginx Config**: `/etc/nginx/sites-available/tpa-alpha`

---

## 📋 Full Deployment Workflow

### ✅ PHASE 1: LOCAL DEVELOPMENT (On Your Machine)

#### 1.1 Make Code Changes
```bash
# Navigate to project
cd f:\MyProjects\discord_bot

# Make changes to files (e.g., SettingsPage.tsx)
# Test locally if needed with npm run dev

# Check which files changed
git status
```

#### 1.2 Commit Changes Locally
```bash
cd f:\MyProjects\discord_bot

# Stage changes
git add .

# Commit with descriptive message
git commit -m "Refactor Settings page: move Save button to Billing section footer"

# View commit
git log --oneline -1
```

#### 1.3 Push to GitHub
```bash
# Push to main branch
git push origin main

# Verify push succeeded
git log --oneline -3  # Should show latest commits

# Verify on GitHub
# Visit: https://github.com/Nomanriaz786/tpa-alpha
```

---

### ✅ PHASE 2: SERVER DEPLOYMENT (On Ubuntu 3.93.192.182)

#### 2.1 Connect to Server via SSH
```bash
ssh -i "f:\MyProjects\discord_bot\sandra.pem" -o StrictHostKeyChecking=no ubuntu@3.93.192.182
```

#### 2.2 Create/Clean Deployment Directory
```bash
# Create apps directory if needed
mkdir -p /var/www

# Remove old code (FULL CLEANUP - NO BACKUPS)
sudo rm -rf /var/www/tpa-alpha

# Verify it's gone
ls -la /var/www/ | grep tpa-alpha || echo "✅ Old deployment cleaned"
```

#### 2.3 Pull Fresh Code from GitHub
```bash
# Clone repository to /var/www
cd /var/www
# Note: Use actual GitHub token (stored securely, not in git)
GITHUB_TOKEN="<your-token-here>"
GITHUB_REPO="https://${GITHUB_TOKEN}@github.com/Nomanriaz786/tpa-alpha.git"
sudo git clone $GITHUB_REPO tpa-alpha 2>&1 | tail -5

# Fix ownership to ubuntu user (REQUIRED for npm install)
sudo chown -R ubuntu:ubuntu /var/www/tpa-alpha

# Verify clone
ls -la /var/www/tpa-alpha | head -10
```

#### 2.4 Build Frontend
```bash
# Navigate to frontend
cd /var/www/tpa-alpha/tpa-alpha-bot/frontend

# Install dependencies (includes dev dependencies for TypeScript compilation)
npm install 2>&1 | tail -5

# Copy missing lib files if needed (NOT in git)
# These files are .gitignored, so copy from local if available
# mkdir -p src/lib
# scp -i sandra.pem format.ts utils.ts ubuntu@3.93.192.182:/var/www/tpa-alpha/tpa-alpha-bot/frontend/src/lib/

# Build production bundle
npm run build 2>&1 | tail -15

# Verify build succeeded
ls -lh /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist/
```

#### 2.5 Configure & Restart Nginx
```bash
# Update nginx config with /var/www paths
cat /var/www/tpa-alpha/tpa-alpha-nginx.conf | sed 's|/home/ubuntu/apps/tpa-alpha-bot|/var/www/tpa-alpha/tpa-alpha-bot|g' > /tmp/tpa-alpha-nginx.conf

# Install nginx config
sudo cp /tmp/tpa-alpha-nginx.conf /etc/nginx/sites-available/tpa-alpha
sudo ln -sf /etc/nginx/sites-available/tpa-alpha /etc/nginx/sites-enabled/tpa-alpha

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Verify nginx is running
sudo systemctl status nginx | head -3
```

#### 2.6 Verify Backend (if applicable)
```bash
# Build backend if needed
cd /var/www/tpa-alpha/tpa-alpha-bot/backend
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Start backend service
sudo systemctl start tpa-alpha-backend || true
sudo systemctl status tpa-alpha-backend | head -3
```

---

### ✅ PHASE 3: DEPLOYMENT VERIFICATION

#### 3.1 Test Frontend Access
```bash
# Test HTTPS
curl -s -k https://3-93-192-182.nip.io/ | head -20

# Check HTTP response
curl -s -I -k https://3-93-192-182.nip.io/ | head -1

# Check CSS loads
curl -s -I -k https://3-93-192-182.nip.io/assets/index-Cy5SY32s.css | grep "content-type"

# Check JS loads
curl -s -I -k https://3-93-192-182.nip.io/assets/index-BurJIYxr.js | grep "content-type"
```

#### 3.2 Browse in Browser
```
🌐 Visit: https://3-93-192-182.nip.io/settings
✅ Verify:
   - Settings page loads without errors
   - Billing section visible
   - Save button in Billing footer (NOT at top)
   - CheckCircle2 icon and "Saved" text should appear on save
   - Payment networks table displays
   - All styling and fonts loaded correctly
   - No console errors (F12 → Console)
```

#### 3.3 Verify Code Changes
```bash
# Check specific code is deployed
curl -s -k https://3-93-192-182.nip.io/assets/index-BurJIYxr.js | grep -c "Saved" && echo "✅ Code changes present"

# View build artifacts
du -sh /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist
ls -lh /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist/assets/
```

#### 3.4 Check Services
```bash
# Frontend (nginx)
sudo systemctl status nginx | grep "Active:" | grep "running"

# Backend (if applicable)
sudo systemctl status tpa-alpha-backend | grep "Active:" || echo "Backend service info:"
sudo systemctl status tpa-alpha-backend | head -5

# View error logs if needed
sudo tail -50 /var/log/nginx/error.log
```

---

## 🔄 QUICK DEPLOYMENT SCRIPT

Run this automated deployment after code is pushed to GitHub:

```bash
#!/bin/bash
set -e

echo "🚀 TPA Alpha Deployment Starting..."

# Phase 1: Clean & Clone
echo "📥 Pulling fresh code..."
sudo rm -rf /var/www/tpa-alpha
cd /var/www
GITHUB_TOKEN="<your-token-here>"  # Store securely
GITHUB_REPO="https://${GITHUB_TOKEN}@github.com/Nomanriaz786/tpa-alpha.git"
sudo git clone $GITHUB_REPO tpa-alpha
sudo chown -R ubuntu:ubuntu /var/www/tpa-alpha

# Phase 2: Build Frontend
echo "🔨 Building frontend..."
cd /var/www/tpa-alpha/tpa-alpha-bot/frontend
npm install
npm run build

# Phase 3: Configure Nginx
echo "⚙️ Configuring nginx..."
cat /var/www/tpa-alpha/tpa-alpha-nginx.conf | sed 's|/home/ubuntu/apps/tpa-alpha-bot|/var/www/tpa-alpha/tpa-alpha-bot|g' > /tmp/tpa-alpha-nginx.conf
sudo cp /tmp/tpa-alpha-nginx.conf /etc/nginx/sites-available/tpa-alpha
sudo ln -sf /etc/nginx/sites-available/tpa-alpha /etc/nginx/sites-enabled/tpa-alpha
sudo nginx -t && sudo systemctl reload nginx

echo "✅ Deployment complete!"
echo "🌐 Visit: https://3-93-192-182.nip.io/settings"
```

---

## 🔍 TROUBLESHOOTING

### Frontend Not Loading
```bash
# Check nginx error log
sudo tail -50 /var/log/nginx/error.log

# Verify dist folder exists
ls -la /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist/

# Check nginx config is valid
sudo nginx -t

# Reload nginx manually
sudo systemctl reload nginx
```

### CSS/JS Assets Missing
```bash
# Verify assets were built
ls -lh /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist/assets/

# Check nginx can access them
curl -v https://3-93-192-182.nip.io/assets/index-Cy5SY32s.css 2>&1 | head -20

# Check file permissions
ls -la /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist/assets/
```

### Build Fails
```bash
# Check Node.js version
node -v  # Should be v20.x

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
cd /var/www/tpa-alpha/tpa-alpha-bot/frontend
rm -rf node_modules package-lock.json
npm install

# Try build again
npm run build 2>&1 | tail -20
```

### Missing lib Files (TypeScript Error)
```bash
# Create lib directory
mkdir -p /var/www/tpa-alpha/tpa-alpha-bot/frontend/src/lib

# From local machine, copy files
scp -i "f:\MyProjects\discord_bot\sandra.pem" \
  "f:\MyProjects\discord_bot\tpa-alpha-bot\frontend\src\lib\format.ts" \
  "ubuntu@3.93.192.182:/var/www/tpa-alpha/tpa-alpha-bot/frontend/src/lib/"

scp -i "f:\MyProjects\discord_bot\sandra.pem" \
  "f:\MyProjects\discord_bot\tpa-alpha-bot\frontend\src\lib\utils.ts" \
  "ubuntu@3.93.192.182:/var/www/tpa-alpha/tpa-alpha-bot/frontend/src/lib/"

# Retry build
cd /var/www/tpa-alpha/tpa-alpha-bot/frontend
npm run build
```

### Nginx Config Error
```bash
# Check syntax
sudo nginx -t

# View current config
cat /etc/nginx/sites-available/tpa-alpha

# Reload if valid
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🔙 ROLLBACK PROCEDURE

If deployment fails or you need to go back to previous version:

```bash
# On server:
cd /var/www/tpa-alpha

# Show git history
git log --oneline -10

# Checkout previous commit
git checkout HEAD~1

# Rebuild frontend
cd tpa-alpha-bot/frontend
npm run build

# Reload nginx
sudo systemctl reload nginx

# Verify
curl -s -k https://3-93-192-182.nip.io/ | head -10
```

---

## 📊 DEPLOYMENT CHECKLIST

**Before Deployment:**
- [ ] Code changes tested locally
- [ ] Changes committed to git
- [ ] Changes pushed to GitHub (verify on https://github.com/Nomanriaz786/tpa-alpha)
- [ ] GitHub token is valid
- [ ] Sandra.pem SSH key is present at `f:\MyProjects\discord_bot\sandra.pem`

**During Deployment:**
- [ ] SSH connection to server successful
- [ ] Old deployment cleaned
- [ ] Code cloned from GitHub
- [ ] Permissions fixed (ubuntu:ubuntu)
- [ ] Dependencies installed
- [ ] Frontend built successfully (0 TypeScript errors)
- [ ] Nginx configured and tested
- [ ] Nginx reloaded

**After Deployment:**
- [ ] Frontend accessible at https://3-93-192-182.nip.io
- [ ] Settings page loads
- [ ] All code changes visible
- [ ] CSS/JS assets loading
- [ ] No console errors (F12)
- [ ] Services running (nginx status)
- [ ] HTTP/2 200 responses

---

## 🔧 KEY CONFIGURATION FILES

### Local Git Config
```bash
user.email = muhammadnomanriaz599@gmail.com
user.name = Nomanriaz786
remote.origin.url = https://github.com/Nomanriaz786/tpa-alpha.git
```

### SSH Command Template
```bash
ssh -i "f:\MyProjects\discord_bot\sandra.pem" \
    -o StrictHostKeyChecking=no \
    ubuntu@3.93.192.182 \
    "COMMAND_HERE"
```

### SCP File Transfer (if needed)
```bash
# Copy FROM local TO server
scp -i "f:\MyProjects\discord_bot\sandra.pem" \
    local_file \
    ubuntu@3.93.192.182:/remote/path/

# Copy FROM server TO local
scp -i "f:\MyProjects\discord_bot\sandra.pem" \
    ubuntu@3.93.192.182:/remote/file \
    local_path/
```

---

## 📝 DEPLOYMENT FLOW SUMMARY

```
1. LOCAL MACHINE
   ├─ Make code changes
   ├─ Test locally
   ├─ Commit changes (git commit)
   └─ Push to GitHub (git push origin main)

2. SSH TO SERVER (ubuntu@3.93.192.182 via sandra.pem)
   ├─ Clean: sudo rm -rf /var/www/tpa-alpha
   ├─ Pull: git clone from GitHub
   ├─ Fix Ownership: sudo chown -R ubuntu:ubuntu
   └─ Build: cd frontend && npm install && npm run build

3. CONFIGURE & RESTART
   ├─ Update nginx config (sed replace paths)
   ├─ Copy config: sudo cp to /etc/nginx/sites-available/
   ├─ Test: sudo nginx -t
   └─ Reload: sudo systemctl reload nginx

4. VERIFY
   ├─ curl HTTPS endpoints
   ├─ Check CSS/JS loading
   ├─ Browse to https://3-93-192-182.nip.io/settings
   ├─ Verify code changes present
   └─ Check for console errors (F12)
```

---

## 📞 REFERENCE

- **GitHub Repo**: https://github.com/Nomanriaz786/tpa-alpha.git
- **Live URL**: https://3-93-192-182.nip.io
- **Server Path**: /var/www/tpa-alpha
- **Frontend Build**: npm run build
- **Nginx Reload**: sudo systemctl reload nginx
- **Frontend Root**: /var/www/tpa-alpha/tpa-alpha-bot/frontend/dist

---

## ✅ DEPLOYMENT COMPLETE INDICATORS

All of these should be true after successful deployment:

1. ✅ GitHub shows latest commit
2. ✅ `/var/www/tpa-alpha` exists on server
3. ✅ `/var/www/tpa-alpha/tpa-alpha-bot/frontend/dist` has files
4. ✅ Nginx config test passes
5. ✅ `sudo systemctl status nginx` shows "active (running)"
6. ✅ `curl -k https://3-93-192-182.nip.io/` returns HTTP 200
7. ✅ Browser loads https://3-93-192-182.nip.io/settings
8. ✅ Code changes visible in page
9. ✅ Console (F12) shows no errors
10. ✅ CSS and JS files load successfully

---

**REMEMBER**: Always verify on the live URL before considering deployment complete!
