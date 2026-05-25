# GitHub Secrets Setup Guide

Complete guide to configuring all required GitHub repository secrets for the CI/CD pipeline.

---

## 📋 Secrets Overview

These 10 secrets must be added to GitHub for the pipeline to deploy correctly. The `deploy.yml` injects them at runtime — none of them ever touch the repository.

| Secret | Purpose | Where Used |
|--------|---------|------------|
| `AZURE_VM_HOST` | VM IP or hostname | SSH connection |
| `AZURE_VM_USER` | SSH username | SSH connection |
| `AZURE_VM_PRIVATE_KEY` | SSH private key (full file) | SSH connection |
| `POSTGRES_PASSWORD` | Superset's Postgres password | `docker/.env` |
| `DATABASE_PASSWORD` | Superset internal DB password | `docker/.env` |
| `SUPERSET_SECRET_KEY` | Flask secret key for Superset | `docker/.env` |
| `ADMIN_PASSWORD` | Superset admin UI password | `docker/.env` |
| `WEATHER_API_KEY` | WeatherStack API key | `airflow/.env` |
| `WEATHER_API_CITY` | City name for API | `airflow/.env` |
| `WEATHER_API_BASE_URL` | WeatherStack base URL | `airflow/.env` |

---

## 🔐 How to Add Secrets

1. Open your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each secret below

---

## 📦 Secret Details

### VM Access (3 secrets)

**`AZURE_VM_HOST`**
Your Azure VM's public IP address or DNS hostname.
```
20.45.123.456
```
Find it: Azure Portal → Your VM → Overview → Public IP address

---

**`AZURE_VM_USER`**
The SSH username for your VM. Azure default is `azureuser` unless you customised it.
```
azureuser
```

---

**`AZURE_VM_PRIVATE_KEY`**
The full contents of your SSH private key file — including the header and footer lines.

```bash
# Print your key to copy
cat ~/.ssh/id_rsa

# Or if you use a named key
cat ~/.ssh/azure_vm_key
```

Copy everything including `-----BEGIN RSA PRIVATE KEY-----` through `-----END RSA PRIVATE KEY-----`.

To verify the public key is on your VM:
```bash
cat ~/.ssh/authorized_keys
```

---

### Database Passwords (2 secrets)

The project uses two separate Postgres password secrets because Superset has an internal database (`superset_db`) managed by its own user, separate from the main weather data DB.

**`POSTGRES_PASSWORD`**
Password for the `superset` Postgres user (used by the `db` container's `superset_db` database).

**`DATABASE_PASSWORD`**
Password Superset's app uses to connect to its metadata database.

Generate secure values for both:
```bash
openssl rand -base64 32
```

> Use different values for each.

---

### Superset Secrets (2 secrets)

**`SUPERSET_SECRET_KEY`**
Flask secret key used to sign sessions and cookies. Generate with:
```bash
openssl rand -base64 42
```

**`ADMIN_PASSWORD`**
Password for the Superset `admin` user in the UI at `http://localhost:8088`.
```bash
openssl rand -base64 24
```

---

### Weather API (3 secrets)

**`WEATHER_API_KEY`**
Your API key from [weatherstack.com](https://weatherstack.com). Sign up for a free account, then copy your key from the Dashboard.

**`WEATHER_API_CITY`**
The city name passed to the API. Must be a name WeatherStack recognises.
```
London
Sydney
Tokyo
```

**`WEATHER_API_BASE_URL`**
The WeatherStack API base URL.
```
http://api.weatherstack.com/current
```

> Note: The free tier only supports `http://`, not `https://`. If you upgrade your plan, use `https://`.

---

## ✅ Setup Checklist

```
VM Access:
  [ ] AZURE_VM_HOST
  [ ] AZURE_VM_USER
  [ ] AZURE_VM_PRIVATE_KEY

Database:
  [ ] POSTGRES_PASSWORD
  [ ] DATABASE_PASSWORD

Superset:
  [ ] SUPERSET_SECRET_KEY
  [ ] ADMIN_PASSWORD

Weather API:
  [ ] WEATHER_API_KEY
  [ ] WEATHER_API_CITY
  [ ] WEATHER_API_BASE_URL
```

---

## 🧪 Test SSH Connection Locally

Before triggering a deploy, verify your SSH key works from your local machine:

```bash
ssh -i ~/.ssh/id_rsa azureuser@your-vm-ip "echo '✓ SSH connection successful'"
```

---

## ❓ Troubleshooting

**Deploy step fails with `Permission denied (publickey)`**
- Make sure you copied the *private* key (not the `.pub` file)
- Paste the complete file contents including header/footer
- Verify the public key counterpart exists in `~/.ssh/authorized_keys` on the VM

**`docker compose` fails with missing env vars**
- Secret names are case-sensitive — check for typos against the table above
- The deploy script writes `docker/.env` and `airflow/.env` at runtime from secrets; if a secret is missing the file will be incomplete

**Superset login fails after deploy**
- `ADMIN_PASSWORD` in GitHub must match exactly what you expect to log in with
- Check with: `docker logs superset_init_container | tail -30`

---

## 🔒 Security Notes

- All `.env` files are written at deploy time from GitHub Secrets and are **never committed to the repo**
- The `AZURE_VM_PRIVATE_KEY` is written to `~/.ssh/id_rsa` in the runner, used once, and discarded
- Rotate secrets immediately if you suspect exposure — especially `WEATHER_API_KEY` and `SUPERSET_SECRET_KEY`