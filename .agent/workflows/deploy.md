---
description: Deploy FinanzBro to Google Cloud Run
---

1. First, run tests to make sure everything is green:

// turbo
```powershell
python -m pytest tests/ -v --tb=short
```

2. If any tests fail, stop and fix them before deploying.

3. Deploy to Cloud Run using gcloud:

```powershell
gcloud run deploy finanzbro --source . --region europe-west1 --update-env-vars ENVIRONMENT=production,GCP_PROJECT_ID=job-automation-jonas
```

4. Verify the deployment by checking the Cloud Run URL shown in the output.
