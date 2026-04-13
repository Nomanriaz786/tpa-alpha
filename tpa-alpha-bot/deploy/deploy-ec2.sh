#!/bin/bash
# TPA Alpha Bot - EC2 Auto-Deploy Script
# Usage: bash deploy-ec2.sh <domain> <bot_token> <app_id> <guild_id>

set -e

DOMAIN=${1:-"tpa-alpha.example.com"}
BOT_TOKEN=${2:-""}
APP_ID=${3:-""}
GUILD_ID=${4:-""}

if [ -z "$BOT_TOKEN" ] || [ -z "$APP_ID" ] || [ -z "$GUILD_ID" ]; then
    echo "Usage: bash deploy-ec2.sh <domain> <bot_token> <app_id> <guild_id>"
    exit 1
fi

echo "🚀 TPA Alpha Bot - EC2 Auto-Deployment"
echo "======================================="
echo "Domain: $DOMAIN"
echo "Starting deployment..."

# Step 1: System updates
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3-pip python3-venv nodejs npm postgresql postgresql-contrib nginx git curl certbot python3-certbot-nginx

# Step 2: Clone repository
echo "📥 Cloning repository..."
cd /home/ubuntu
if [ ! -d "tpa-alpha-bot" ]; then
    git clone https://github.com/your-repo/tpa-alpha-bot.git
fi
cd tpa-alpha-bot

# Step 3: Backend setup
echo "⚙️  Setting up backend..."
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Step 4: Create .env file
echo "🔐 Configuring environment..."
cat > .env << EOF
DISCORD_BOT_TOKEN=$BOT_TOKEN
DISCORD_APPLICATION_ID=$APP_ID
GUILD_ID=$GUILD_ID
ADMIN_DISCORD_IDS=your_admin_id
VIP_ROLE_NAME=TPA Alpha 👑
WEB_BASE_URL=https://$DOMAIN
DATABASE_URL=postgresql+asyncpg://tpa_user:tpa_password@localhost:5432/tpa_alpha
ADMIN_EMAIL=admin@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
PRICE_PER_MONTH_USD=100
PAYMENT_TOLERANCE_USD=5
POLL_INTERVAL_SECONDS=60
PENDING_PAYMENT_TTL_HOURS=24
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4
EOF

# Step 5: Database setup
echo "🗄️  Setting up PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql << PSQL
CREATE DATABASE tpa_alpha;
CREATE USER tpa_user WITH PASSWORD 'tpa_password';
ALTER ROLE tpa_user SET client_encoding TO 'utf8';
ALTER ROLE tpa_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tpa_user SET default_transaction_deferrable TO on;
ALTER ROLE tpa_user SET default_timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tpa_alpha TO tpa_user;
PSQL

# Step 6: Frontend build
echo "🎨 Building frontend..."
cd frontend
npm install --production
npm run build
cd ..

# Step 7: Create systemd services
echo "⚡ Setting up systemd services..."

sudo tee /etc/systemd/system/tpa-backend.service > /dev/null << EOF
[Unit]
Description=TPA Alpha Backend API
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tpa-alpha-bot/backend
Environment="PATH=/home/ubuntu/tpa-alpha-bot/backend/venv/bin"
ExecStart=/home/ubuntu/tpa-alpha-bot/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/tpa-bot.service > /dev/null << EOF
[Unit]
Description=TPA Alpha Discord Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tpa-alpha-bot
Environment="PATH=/home/ubuntu/tpa-alpha-bot/backend/venv/bin"
EnvironmentFile=/home/ubuntu/tpa-alpha-bot/.env
ExecStart=/home/ubuntu/tpa-alpha-bot/backend/venv/bin/python bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Configure Nginx
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/tpa-alpha > /dev/null << 'NGINX'
upstream tpa_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    location / {
        root /home/ubuntu/tpa-alpha-bot/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
    
    location /api/ {
        proxy_pass http://tpa_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo sed -i "s/\$DOMAIN/$DOMAIN/g" /etc/nginx/sites-available/tpa-alpha
sudo ln -sf /etc/nginx/sites-available/tpa-alpha /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Step 9: Get SSL certificate
echo "🔒 Obtaining SSL certificate..."
sudo certbot certonly --nginx -d $DOMAIN --agree-tos --no-eff-email --non-interactive

# Step 10: Enable and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable tpa-backend tpa-bot
sudo systemctl start tpa-backend tpa-bot

# Step 11: Verify services
echo "✅ Verifying deployment..."
sleep 5
sudo systemctl status tpa-backend --no-pager
sudo systemctl status tpa-bot --no-pager

echo ""
echo "=================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================="
echo ""
echo "🌐 Access your bot:"
echo "   Dashboard: https://$DOMAIN"
echo "   API: https://$DOMAIN/api/health"
echo ""
echo "📋 Next steps:"
echo "   1. Add Discord interactions endpoint:"
echo "      https://$DOMAIN/api/webhooks/interactions"
echo "   2. Test bot commands in Discord:"
echo "      /setup /grant /revoke /status"
echo ""
echo "📊 View logs:"
echo "   Backend: sudo journalctl -u tpa-backend -f"
echo "   Bot: sudo journalctl -u tpa-bot -f"
echo ""
