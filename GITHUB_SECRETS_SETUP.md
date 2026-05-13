# GitHub Secrets Setup Guide

Complete guide to configuring all required GitHub repository secrets for CI/CD automation.

---

## 📋 Secrets Overview

You need to add 7 secrets to GitHub for your CI/CD pipeline to work. Here's the quick summary:

| Secret | Type | Priority | Source |
|--------|------|----------|--------|
| `AZURE_VM_HOST` | VM IP/hostname | ⭐⭐⭐ | Azure Portal |
| `AZURE_VM_USER` | SSH username | ⭐⭐⭐ | Your VM setup |
| `AZURE_VM_PRIVATE_KEY` | SSH private key | ⭐⭐⭐ | Your local machine |
| `DB_PASSWORD` | PostgreSQL password | ⭐⭐⭐ | You create this |
| `WEATHER_API_KEY` | WeatherStack API key | ⭐⭐⭐ | weatherstack.com |
| `WEATHER_API_CITY` | City name | ⭐⭐ | You choose |
| `SUPERSET_ADMIN_PASSWORD` | Admin password | ⭐⭐ | You create this |

---

## 🔐 How to Add Secrets to GitHub

### Step 1: Go to GitHub Secrets Panel

1. Open your repository: `github.com/Rainman4301/WeatherETL`
2. Click **Settings** (top right)
3. Click **Secrets and variables** (left sidebar)
4. Click **Actions** tab

### Step 2: Add Each Secret

Click **New repository secret** for each item below and add the values.

---

## 📦 What Each Secret Is & How to Get It

### 1. `AZURE_VM_HOST` ⭐⭐⭐

**What:** Your Azure VM's public IP address or hostname

**How to get it:**
- Go to [Azure Portal](https://portal.azure.com)
- Find your VM in the resource list
- Click Overview → look for **Public IP address**
- Or use the **DNS name** if available

**Examples:**
```
20.45.123.456
vm-weather.eastus.cloudapp.azure.com
```

---

### 2. `AZURE_VM_USER` ⭐⭐⭐

**What:** SSH username for your Azure VM

**How to get it:**
- Usually `azureuser` (Azure default)
- Or the custom username you created when setting up the VM

**Examples:**
```
azureuser
```

---

### 3. `AZURE_VM_PRIVATE_KEY` ⭐⭐⭐

**What:** Your SSH private key file (the entire file contents)

**How to get it:**

**If you already have an SSH key:**
```bash
cat ~/.ssh/azure_vm_key
```

**If you don't have an SSH key yet:**
```bash
# Generate new key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_vm_key -N ""

# View the private key
cat ~/.ssh/azure_vm_key
```

**How to add to GitHub:**
1. Open the file: `cat ~/.ssh/azure_vm_key`
2. Copy the **entire content** (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)
3. Paste into GitHub secret

⚠️ **Important:** Copy the entire file, not just a part of it!

---

### 4. `DB_PASSWORD` ⭐⭐⭐

**What:** PostgreSQL database password (you choose this)

**How to create a secure password:**

```bash
# Option 1: Using openssl
openssl rand -base64 32

# Option 2: Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Requirements:**
- At least 12 characters
- Mix of uppercase, lowercase, numbers, and special characters
- No simple passwords like `password` or `123456`

**Example:**
```
Kj8$mNp2@vL9xQ4%wR7eYuT3
```

---

### 5. `WEATHER_API_KEY` ⭐⭐⭐

**What:** Your WeatherStack API key for weather data

**How to get it:**
1. Go to [weatherstack.com](https://weatherstack.com)
2. Sign up for free account (free tier available)
3. Go to Dashboard → API keys
4. Copy your API key

**Example:**
```
abc123def456ghi789jkl012
```

⚠️ Keep this secret! Never commit to GitHub.

---

### 6. `WEATHER_API_CITY` ⭐⭐

**What:** The city to fetch weather for

**How to choose:**
- Any valid city name that WeatherStack recognizes

**Examples:**
```
London
New York
Paris
Tokyo
Sydney
```

---

### 7. `SUPERSET_ADMIN_PASSWORD` ⭐⭐

**What:** Admin password for Superset visualization dashboard

**How to create:**
```bash
openssl rand -base64 32
```

**Requirements:**
- Secure and different from other passwords
- Only needed if using Superset (optional)

---

## ✅ Setup Checklist

Use this to verify you've added all secrets:

```
GitHub Secrets Setup Checklist:

Azure VM Access:
  [ ] AZURE_VM_HOST
  [ ] AZURE_VM_USER
  [ ] AZURE_VM_PRIVATE_KEY

Database:
  [ ] DB_PASSWORD

Weather API:
  [ ] WEATHER_API_KEY
  [ ] WEATHER_API_CITY

Superset (Optional):
  [ ] SUPERSET_ADMIN_PASSWORD
```

---

## 🧪 Test Your Secrets

### Test SSH Connection Locally

Before deploying, verify your SSH key works:

```bash
ssh -i ~/.ssh/azure_vm_key azureuser@your-vm-ip "echo Success!"
```

Should output: `Success!`

---

## 🚨 Security Best Practices

**DO** ✅
- Use strong passwords (uppercase, lowercase, numbers, special chars)
- Keep SSH private key safe on your local machine
- Rotate secrets regularly
- Use GitHub Secrets (never hardcode)
- Different secrets for different environments

**DON'T** ❌
- Commit `.env` files to Git
- Share SSH private keys via email
- Use simple passwords
- Hardcode secrets in code
- Reuse same credentials everywhere

---

## ❓ Troubleshooting

**SSH deployment fails with "Permission denied (publickey)"**
- Check `AZURE_VM_PRIVATE_KEY` is the complete file
- Verify public key is added to VM's `~/.ssh/authorized_keys`

**"WEATHER_API_KEY environment variable is not set"**
- Verify secret name is spelled exactly: `WEATHER_API_KEY` (case-sensitive)
- Check GitHub Secrets list shows the secret

**PostgreSQL connection fails on VM**
- Ensure `DB_PASSWORD` matches value used locally
- Verify secret name is `DB_PASSWORD`

---

## 🔄 Next Steps

1. ✅ Add all 7 secrets to GitHub
2. 📖 Read [DEVELOPMENT_AND_DEPLOYMENT_GUIDE.md](DEVELOPMENT_AND_DEPLOYMENT_GUIDE.md) for local setup and CI/CD workflow
3. 🚀 Follow the deployment guide to set up your environment and run your first pipeline
