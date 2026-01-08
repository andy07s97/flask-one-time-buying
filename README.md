# Flask SaaS Template

Reusable Flask project template for MVPs and small SaaS products.

## Local Development

bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py

# Production

Ubuntu 22.04
Gunicorn + Nginx
systemd service included



---

## 7. How You Use This Template (Very Important)

### Step 1 — Create this repo once

- Create `flask-saas-template`
- Mark it as **Template Repository** in GitHub settings

### Step 2 — Start a new project

- Click **Use this template**
- Name it:
  - `sleep-ritual`
  - `ytt-transcript`
  - `clinic-scheduler`
- You now have:
  - Clean history
  - CI ready
  - Same structure every time

### Step 3 — Customize only:
- `README.md`
- `.env.example`
- `app/routes`
- `models.py`

---

## 8. Why This Template Works Long-Term

- App factory → multiple environments
- Blueprint-based routing → modular
- Ready for:
  - Login
  - Payments
  - Rate limiting
  - API keys
- Same deployment workflow every time

This is **exactly the kind of repo structure solo founders converge to after 3–5 projects**.

---

## 9. Next Logical Enhancements (Optional)

If you want, I can extend this template with:
- Flask-Login + user model
- Stripe / ECPay payment skeleton
- Rate limiting
- Admin panel
- GitHub Actions → EC2 deploy
- ARM-friendly (t4g.nano) production tuning

State which direction you want to extend first.
