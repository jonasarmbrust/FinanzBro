#!/bin/bash
# FinanzBro - Google Cloud Run Deployment
#
# Voraussetzungen:
#   1. gcloud CLI installiert und eingeloggt: gcloud auth login
#   2. GCP Projekt gesetzt: gcloud config set project DEIN-PROJEKT-ID
#   3. Cloud Run API aktiviert: gcloud services enable run.googleapis.com
#
# Verwendung:
#   chmod +x deploy.sh
#   ./deploy.sh

set -e

# ============ Konfiguration ============
SERVICE_NAME="finanzbro"
REGION="europe-west1"

# API Keys werden als Env-Vars gesetzt
# Alternativ: Google Secret Manager nutzen
echo "🚀 Deploying FinanzBro to Cloud Run..."
echo "   Service: $SERVICE_NAME"
echo "   Region:  $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI nicht gefunden. Bitte installieren:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    echo "❌ Kein GCP Projekt gesetzt. Bitte ausführen:"
    echo "   gcloud config set project DEIN-PROJEKT-ID"
    exit 1
fi
echo "   Projekt: $PROJECT"
echo ""

# Deploy from source (Cloud Build + Cloud Run in einem Schritt)
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 1 \
    --timeout 300 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT}" \
    --set-env-vars "FMP_API_KEY=${FMP_API_KEY:-}" \
    --set-env-vars "PARQET_ACCESS_TOKEN=${PARQET_ACCESS_TOKEN:-}" \
    --set-env-vars "PARQET_PORTFOLIO_ID=${PARQET_PORTFOLIO_ID:-}" \
    --set-env-vars "DAILY_REFRESH_TIME=06:00" \
    --set-env-vars "PRICE_UPDATE_INTERVAL_MIN=30"

echo ""
echo "✅ Deployment erfolgreich!"
echo ""

# Get service URL
URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' 2>/dev/null)
echo "🌐 Dashboard erreichbar unter: $URL"
echo ""
echo "💡 Tipp: API Keys als Env-Vars setzen:"
echo "   export FMP_API_KEY=dein_key"
echo "   export PARQET_ACCESS_TOKEN=dein_token"
echo "   ./deploy.sh"
