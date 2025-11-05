 # Nginx Reverse Proxy Setup Guide

## 📋 Overview

This setup allows you to access the Door Lock backend API at:
- **Public URL:** `https://your-domain.example.com/doorlock/`
- **Internal:** `http://localhost:7000/`

**Benefits:**
✅ No port number in URLs  
✅ Clean API endpoints  
✅ Easy SSL/HTTPS setup  
✅ Better security (port 7000 not exposed)  
✅ Can host multiple services on same domain  

---

## 🚀 Quick Setup

### 1. Install Nginx (if not installed)

```bash
sudo apt update
sudo apt install nginx -y
```

### 2. Copy Configuration

```bash
cd /path/to/fingerprint-camera-door-lock/Backend
sudo cp nginx.conf /etc/nginx/sites-available/doorlock
```

### 3. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/doorlock /etc/nginx/sites-enabled/
```

### 4. Test Configuration

```bash
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 5. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 6. Verify Nginx is Running

```bash
sudo systemctl status nginx
```

---

## 🧪 Testing

### Test Backend (Direct - Internal)
```bash
curl http://localhost:7000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T...",
  "service": "door-lock-backend"
}
```

### Test via Nginx (Public)
```bash
curl http://your-domain.example.com/doorlock/health
```

Should return the same response!

### Test Other Endpoints
```bash
# Get model info
curl http://your-domain.example.com/doorlock/api/get-model-info

# Get users
curl http://your-domain.example.com/doorlock/api/get-users
```

---

## 🔒 Setup SSL/HTTPS (Recommended)

### Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Get SSL Certificate

```bash
sudo certbot --nginx -d your-domain.example.com
```

Follow the prompts:
1. Enter email address
2. Agree to Terms of Service
3. Choose whether to share email
4. Select option 2 to redirect HTTP to HTTPS

### Test Auto-Renewal

```bash
sudo certbot renew --dry-run
```

### Verify HTTPS

```bash
curl https://your-domain.example.com/doorlock/health
```

---

## 🔧 How It Works

### URL Mapping

| Client Request | Nginx Rewrites To | Backend Receives |
|---------------|-------------------|------------------|
| `/doorlock/health` | `/health` | `/health` |
| `/doorlock/api/get-users` | `/api/get-users` | `/api/get-users` |
| `/doorlock/models/model.pkl` | `/models/model.pkl` | `/models/model.pkl` |

### The Magic Line

```nginx
rewrite ^/doorlock(/.*)$ $1 break;
```

This removes `/doorlock` prefix before forwarding to backend.

**Example:**
- Client requests: `/doorlock/api/get-users`
- Rewrite rule removes `/doorlock`
- Backend receives: `/api/get-users`

---

## 📝 Configuration Details

### Location Block

```nginx
location /doorlock/ {
    # Remove /doorlock prefix
    rewrite ^/doorlock(/.*)$ $1 break;
    
    # Forward to local Flask server
    proxy_pass http://localhost:7000;
    
    # Preserve client information
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeouts (adjust if needed)
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

---

## 🐛 Troubleshooting

### Issue: 502 Bad Gateway

**Cause:** Backend not running

**Solution:**
```bash
# Check if backend is running
pm2 status doorlock-backend

# If not running, start it
pm2 start server.py --name doorlock-backend

# Or run directly
cd Backend
python3 server.py
```

### Issue: 404 Not Found

**Cause:** Nginx config not loaded or incorrect

**Solution:**
```bash
# Check if config exists
ls -l /etc/nginx/sites-enabled/doorlock

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Issue: Connection Refused

**Cause:** Nginx not running

**Solution:**
```bash
# Start nginx
sudo systemctl start nginx

# Enable on boot
sudo systemctl enable nginx
```

### Issue: SSL Certificate Errors

**Cause:** Certificate expired or not properly installed

**Solution:**
```bash
# Renew certificates
sudo certbot renew

# Check certificate status
sudo certbot certificates
```

### Check Nginx Logs

**Error log:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**Access log:**
```bash
sudo tail -f /var/log/nginx/access.log
```

---

## 🔐 Security Best Practices

### 1. Don't Expose Port 7000

Make sure firewall blocks external access to port 7000:

```bash
# Allow nginx ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block port 7000 from external (only allow localhost)
# Don't add: sudo ufw allow 7000/tcp
```

### 2. Use HTTPS Only (Production)

Uncomment the HTTP to HTTPS redirect in nginx.conf:

```nginx
server {
    listen 80;
    server_name your-domain.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. Rate Limiting (Optional)

Add to nginx config to prevent abuse:

```nginx
limit_req_zone $binary_remote_addr zone=doorlock:10m rate=10r/s;

location /doorlock/ {
    limit_req zone=doorlock burst=20;
    # ... rest of config
}
```

### 4. IP Whitelisting (Optional)

If you want to restrict access to specific IPs:

```nginx
location /doorlock/ {
    allow 192.168.1.0/24;  # Your home network
    allow YOUR_RASPBERRY_PI_IP;
    deny all;
    # ... rest of config
}
```

---

## 🔄 Updating Configuration

### Modify nginx.conf

```bash
sudo nano /etc/nginx/sites-available/doorlock
```

### Test Changes

```bash
sudo nginx -t
```

### Apply Changes

```bash
sudo systemctl reload nginx
```

---

## 📊 Monitoring

### Check Nginx Status

```bash
sudo systemctl status nginx
```

### View Active Connections

```bash
sudo nginx -T | grep -A 20 "server {"
```

### Monitor Access in Real-Time

```bash
sudo tail -f /var/log/nginx/access.log | grep doorlock
```

### Check Backend Health

```bash
watch -n 5 'curl -s http://localhost:7000/health | jq'
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Backend runs on localhost:7000
- [ ] Nginx is active: `sudo systemctl status nginx`
- [ ] Config syntax valid: `sudo nginx -t`
- [ ] Health check works: `curl http://localhost:7000/health`
- [ ] Nginx proxy works: `curl http://your-domain.example.com/doorlock/health`
- [ ] SSL certificate installed (if using HTTPS)
- [ ] HTTPS works: `curl https://your-domain.example.com/doorlock/health`
- [ ] Firewall configured (80, 443 open; 7000 blocked externally)
- [ ] PM2 auto-restart enabled: `pm2 startup`
- [ ] Logs are accessible: `sudo tail /var/log/nginx/error.log`

---

## 📚 Additional Resources

- [Nginx Official Docs](https://nginx.org/en/docs/)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Let's Encrypt](https://letsencrypt.org/)

---

## 🎉 All Done!

Your backend is now accessible at:
- **API Base:** `https://your-domain.example.com/doorlock`
- **Health Check:** `https://your-domain.example.com/doorlock/health`
- **Internal:** `http://localhost:7000` (not exposed)

Clean, secure, and production-ready! 🚀
