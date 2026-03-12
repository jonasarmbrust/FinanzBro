---
description: After comprehensive changes - update docs, run tests, push, and deploy
---

This workflow should be used (or suggested to the user) after comprehensive code changes.

// turbo-all

1. Run the full test suite:

```powershell
python -m pytest tests/ -v --tb=short
```

2. If any tests fail, **STOP** — fix them first before continuing.

3. Update documentation if any of the following changed:
   - Scoring logic → update `docs/scoring.md`
   - Architecture (new modules, endpoints, data flow) → update `docs/architecture.md`
   - Features, API endpoints, deployment → update `README.md`
   
   Only update sections that actually changed. Keep existing content intact.

4. Stage all changes:

```powershell
git add -A
```

5. Check what will be committed:

```powershell
git status
```

6. Create a descriptive commit message (German if changes were discussed in German):

```powershell
git commit -m "<beschreibende Nachricht>"
```

7. Push to GitHub:

```powershell
git push
```

8. Ask the user: **"Soll ich auch auf Cloud Run deployen?"**

9. If user confirms, deploy:

```powershell
gcloud run deploy finanzbro --source . --region europe-west1 --update-env-vars ENVIRONMENT=production,GCP_PROJECT_ID=job-automation-jonas
```
