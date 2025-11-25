# 🚀 Deployment Guide

## ✅ Optimized Automated Deployment

Everything is automated! Just push code to GitHub.

---

## 📦 How to Deploy

```bash
# 1. Make your changes
git add .

# 2. Commit
git commit -m "feat: your changes here"

# 3. Push
git push origin main
```

**That's it!** GitHub Actions will:
- ✅ Detect what changed (backend/frontend)
- ✅ Build only changed components
- ✅ Use cache (fast builds)
- ✅ Deploy to Azure
- ✅ Health check everything
- ✅ Create backup for rollback

---

## ⏱️ Build Times

**Backend only changed:** ~3-5 min  
**Frontend only changed:** ~3-5 min  
**Both changed:** ~6-10 min (parallel)  
**Nothing changed:** ~30 sec (skip build, just deploy)

---

## 🔄 Rollback

If something goes wrong:

```bash
ssh -i voilavoicebookingvm_key.pem azureuser@98.66.139.255
cd ~/voilavoicebooking

# Rollback everything
./rollback.sh all

# Or specific component
./rollback.sh backend
./rollback.sh frontend
```

---

## 🌐 Access URLs

**Backend API:** http://98.66.139.255:8081  
**Dashboard:** http://98.66.139.255:8082  
**Booking:** http://98.66.139.255:8000

---

## 📊 Check Deployment Status

GitHub Actions: https://github.com/imhtp-dev/voilavoicebooking/actions
