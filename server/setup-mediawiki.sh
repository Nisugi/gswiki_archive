#!/bin/bash
#
# GSWiki Archive - MediaWiki Setup Script
# Run as root on Ubuntu 22.04/24.04
#
# Usage: sudo bash setup-mediawiki.sh
#

set -e

echo "=========================================="
echo "  GSWiki Archive - MediaWiki Setup"
echo "=========================================="

# Configuration
WIKI_DIR="/var/www/gswiki-archive"
DB_NAME="gswiki_archive"
DB_USER="gswiki"
DB_PASS=$(openssl rand -base64 16)
MEDIAWIKI_VERSION="1.41.1"
SERVER_NAME="${1:-$(hostname -I | awk '{print $1}')}"

echo ""
echo "Configuration:"
echo "  Install directory: $WIKI_DIR"
echo "  Database: $DB_NAME"
echo "  Server: http://gswiki-archive.gs-game.uk"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Update system
echo ""
echo "[1/7] Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo ""
echo "[2/7] Installing Nginx, PHP, MariaDB..."
apt install -y \
    nginx \
    mariadb-server \
    php-fpm \
    php-mysql \
    php-xml \
    php-mbstring \
    php-intl \
    php-curl \
    php-gd \
    php-apcu \
    php-cli \
    imagemagick \
    git \
    unzip \
    curl

# Get PHP version for FPM socket
PHP_VERSION=$(php -r "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION;")
echo "  PHP version: $PHP_VERSION"

# Secure MariaDB and create database
echo ""
echo "[3/7] Setting up database..."
mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';"
mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Save credentials
echo "DB_NAME=$DB_NAME" > /root/.gswiki-db-credentials
echo "DB_USER=$DB_USER" >> /root/.gswiki-db-credentials
echo "DB_PASS=$DB_PASS" >> /root/.gswiki-db-credentials
chmod 600 /root/.gswiki-db-credentials
echo "  Database credentials saved to /root/.gswiki-db-credentials"

# Download MediaWiki
echo ""
echo "[4/7] Downloading MediaWiki $MEDIAWIKI_VERSION..."
cd /tmp
if [ ! -f "mediawiki-$MEDIAWIKI_VERSION.tar.gz" ]; then
    wget "https://releases.wikimedia.org/mediawiki/1.41/mediawiki-$MEDIAWIKI_VERSION.tar.gz"
fi
tar -xzf "mediawiki-$MEDIAWIKI_VERSION.tar.gz"
rm -rf "$WIKI_DIR"
mv "mediawiki-$MEDIAWIKI_VERSION" "$WIKI_DIR"
chown -R www-data:www-data "$WIKI_DIR"

# Configure Nginx
echo ""
echo "[5/7] Configuring Nginx..."
cat > /etc/nginx/sites-available/gswiki-archive << NGINX
server {
    listen 80;
    server_name gswiki-archive.gs-game.uk;
    root $WIKI_DIR;
    index index.php;

    client_max_body_size 50M;

    location / {
        try_files \$uri \$uri/ @rewrite;
    }

    location @rewrite {
        rewrite ^/(.*)$ /index.php?title=\$1&\$args;
    }

    location ~ \.php$ {
        include fastcgi_params;
        fastcgi_pass unix:/run/php/php$PHP_VERSION-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico)$ {
        expires max;
        log_not_found off;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    # Deny access to sensitive files
    location ~ /(\.|LocalSettings\.php) {
        deny all;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/gswiki-archive /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Run MediaWiki installer
echo ""
echo "[6/7] Running MediaWiki installer..."
cd "$WIKI_DIR"
php maintenance/install.php \
    --dbname="$DB_NAME" \
    --dbuser="$DB_USER" \
    --dbpass="$DB_PASS" \
    --dbserver="localhost" \
    --lang="en" \
    --pass="ArchiveAdmin123!" \
    --scriptpath="" \
    --server="http://gswiki-archive.gs-game.uk" \
    "GSWiki Archive" \
    "Admin"

# Configure as read-only archive
echo ""
echo "[7/7] Configuring as read-only archive..."
cat >> "$WIKI_DIR/LocalSettings.php" << 'SETTINGS'

## ================================================
## GSWiki Archive - Read-Only Configuration
## ================================================

# Make wiki read-only
$wgReadOnly = "This is a read-only archive of GSWiki. Visit https://gswiki.play.net for the live wiki.";

# Disable account creation
$wgGroupPermissions['*']['createaccount'] = false;

# Disable editing for everyone
$wgGroupPermissions['*']['edit'] = false;
$wgGroupPermissions['user']['edit'] = false;
$wgGroupPermissions['sysop']['edit'] = false;

# Disable uploads
$wgEnableUploads = false;

# Site branding
$wgSitename = "GSWiki Archive";
$wgMetaNamespace = "GSWiki_Archive";

# Performance
$wgMainCacheType = CACHE_ACCEL;
$wgCacheDirectory = "$IP/cache";
$wgUseFileCache = true;
$wgFileCacheDirectory = "$IP/cache";

# Logo (we'll update this later)
# $wgLogo = "$wgResourceBasePath/resources/assets/archive-logo.png";

# Footer
$wgFooterIcons['poweredby']['gswiki'] = [
    "src" => "",
    "url" => "https://gswiki.play.net",
    "alt" => "Archived from GSWiki"
];

# Add archive notice to every page via site notice
$wgSiteNotice = '<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-bottom: 3px solid #e94560; padding: 10px 20px; text-align: center; color: white; font-family: sans-serif;">
<strong style="color: #e94560;">📦 ARCHIVED SNAPSHOT</strong> of GSWiki •
<a href="https://gswiki.play.net" style="color: #4fbdba;" target="_blank">View live wiki →</a>
</div>';
SETTINGS

# Set permissions
chown -R www-data:www-data "$WIKI_DIR"
chmod 600 "$WIKI_DIR/LocalSettings.php"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "MediaWiki installed at: http://gswiki-archive.gs-game.uk"
echo ""
echo "Admin login:"
echo "  Username: Admin"
echo "  Password: ArchiveAdmin123!"
echo "  (Change this password immediately!)"
echo ""
echo "Database credentials: /root/.gswiki-db-credentials"
echo ""
echo "Next steps:"
echo "  1. Visit http://gswiki-archive.gs-game.uk to verify it works"
echo "  2. Change the admin password"
echo "  3. Run the content import script"
echo ""
