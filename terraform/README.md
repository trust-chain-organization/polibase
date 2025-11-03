# Polibase Terraform Infrastructure

This directory contains Terraform configurations for deploying Polibase on Google Cloud Platform (GCP).

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Post-Deployment](#post-deployment)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This Terraform configuration provisions the following GCP resources:

- **Compute**: Cloud Run services (Streamlit UI, Monitoring Dashboard, Workers)
- **Database**: Cloud SQL for PostgreSQL 15
- **Storage**: Google Cloud Storage buckets (minutes, backups, exports)
- **Networking**: VPC, subnets, VPC Access Connector
- **Security**: Secret Manager, IAM roles, service accounts
- **AI/ML**: Vertex AI integration (via IAM permissions)
- **Monitoring**: Cloud Logging, Cloud Monitoring integration

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│           Cloud Load Balancer (Future)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────────┐
│ Streamlit UI │ │ Monitoring │ │    Workers     │
│ (Cloud Run)  │ │ (Cloud Run)│ │  (Cloud Run)   │
└───────┬──────┘ └─────┬──────┘ └─────┬──────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┴───────────────┬──────────┐
        │                               │          │
┌───────▼──────┐              ┌─────────▼─────┐   │
│   Cloud SQL  │              │  Secret Mgr   │   │
│  PostgreSQL  │              │  (Secrets)    │   │
└──────────────┘              └───────────────┘   │
                                                   │
                              ┌────────────────────▼───┐
                              │ Google Cloud Storage   │
                              │ (Minutes, Backups)     │
                              └────────────────────────┘
```

For detailed architecture information, see [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## ✅ Prerequisites

### 1. Required Tools

Install the following tools:

```bash
# Terraform (>= 1.0)
brew install terraform

# Google Cloud SDK
brew install google-cloud-sdk

# Optional: direnv for environment variable management
brew install direnv
```

### 2. GCP Project Setup

1. Create a GCP project or use an existing one
2. Enable billing for the project
3. Authenticate with GCP:

```bash
gcloud auth login
gcloud auth application-default login
```

4. Set your project:

```bash
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID
```

### 3. Enable Required APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable cloudtrace.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 4. Set Up Terraform Backend (Optional but Recommended)

For production use, store Terraform state in a GCS bucket:

```bash
# Create a bucket for Terraform state
gsutil mb -p $PROJECT_ID -l asia-northeast1 gs://$PROJECT_ID-terraform-state

# Enable versioning
gsutil versioning set on gs://$PROJECT_ID-terraform-state

# Uncomment the backend configuration in main.tf
```

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
cd terraform/
```

### 2. Configure Variables

```bash
# Copy the example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

Required variables to configure:
- `project_id`: Your GCP project ID
- `database_password`: A strong password for PostgreSQL
- `google_api_key`: Your Google Gemini API key
- Container images: Update with your GCR/Artifact Registry URLs

### 3. Build and Push Container Images

Before deploying, build and push your Docker images:

```bash
# From the project root directory
cd ..

# Build images (replace PROJECT_ID with your actual project ID)
docker build -f docker/Dockerfile -t gcr.io/PROJECT_ID/streamlit-ui:latest .
docker build -f docker/Dockerfile -t gcr.io/PROJECT_ID/monitoring-dashboard:latest .
# ... build other images

# Push to GCR
docker push gcr.io/PROJECT_ID/streamlit-ui:latest
docker push gcr.io/PROJECT_ID/monitoring-dashboard:latest
# ... push other images
```

### 4. Initialize Terraform

```bash
cd terraform/
terraform init
```

### 5. Review the Plan

```bash
terraform plan
```

Review the resources that will be created. Terraform will show approximately 30-40 resources.

### 6. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm.

**Note**: Initial deployment takes approximately 10-15 minutes, primarily due to Cloud SQL instance creation.

## ⚙️ Configuration

### Environment-Specific Configurations

#### Development Environment

```hcl
environment              = "development"
database_tier            = "db-f1-micro"
enable_high_availability = false
enable_backup            = true
```

#### Production Environment

```hcl
environment              = "production"
database_tier            = "db-custom-2-8192"  # 2 vCPU, 8GB RAM
enable_high_availability = true
enable_backup            = true
backup_retention_days    = 30
```

### Database Tier Options

| Tier | vCPU | Memory | Use Case | Monthly Cost (approx.) |
|------|------|--------|----------|------------------------|
| `db-f1-micro` | Shared | 0.6GB | Development | $7-10 |
| `db-g1-small` | Shared | 1.7GB | Small staging | $25-30 |
| `db-custom-1-3840` | 1 | 3.75GB | Small production | $50-60 |
| `db-custom-2-8192` | 2 | 8GB | Standard production | $150-180 |
| `db-custom-4-16384` | 4 | 16GB | High-traffic production | $300-350 |

### Module Configuration

The infrastructure is modularized into separate components:

- **network**: VPC, subnets, VPC connector
- **database**: Cloud SQL PostgreSQL
- **security**: Secret Manager, IAM, service accounts
- **storage**: GCS buckets
- **app**: Cloud Run services

You can customize each module by passing different variables in `main.tf`.

## 🚀 Deployment

### Standard Deployment

```bash
# Initialize (first time only)
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan
```

### Targeted Deployment

Deploy only specific modules:

```bash
# Deploy only network module
terraform apply -target=module.network

# Deploy only database module
terraform apply -target=module.database
```

### Workspace Management

For managing multiple environments:

```bash
# Create workspaces
terraform workspace new development
terraform workspace new staging
terraform workspace new production

# Switch workspaces
terraform workspace select development

# List workspaces
terraform workspace list
```

## 📦 Post-Deployment

### 1. Verify Deployment

```bash
# Get all outputs
terraform output

# Get specific output
terraform output streamlit_url
```

### 2. Access Services

```bash
# Get service URLs
STREAMLIT_URL=$(terraform output -raw streamlit_url)
MONITORING_URL=$(terraform output -raw monitoring_url)

# Open in browser
open $STREAMLIT_URL
open $MONITORING_URL
```

### 3. Initialize Database

Connect to Cloud SQL and run migrations:

```bash
# Get database connection name
DB_CONNECTION=$(terraform output -raw database_connection_name)

# Connect using Cloud SQL Proxy
cloud-sql-proxy $DB_CONNECTION &

# Run migrations (from project root)
cd ..
./reset-database.sh
```

### 4. Configure DNS (Optional)

For production deployments, configure custom domains:

1. Purchase a domain (e.g., polibase.example.com)
2. Create Cloud DNS zone
3. Add A/CNAME records pointing to Cloud Run URLs
4. Update Cloud Run services with custom domains

## 🔧 Maintenance

### Updating Infrastructure

```bash
# Pull latest changes
git pull

# Review changes
terraform plan

# Apply updates
terraform apply
```

### Scaling Resources

#### Scale Cloud Run Services

Edit `terraform.tfvars`:

```hcl
# In modules/app/main.tf, adjust:
scaling {
  min_instance_count = 2  # Increase minimum instances
  max_instance_count = 20 # Increase maximum instances
}
```

#### Upgrade Database

```hcl
# In terraform.tfvars
database_tier = "db-custom-4-16384"  # Upgrade to 4 vCPU, 16GB RAM
```

Then apply:

```bash
terraform apply
```

**⚠️ Warning**: Upgrading database tier requires a restart, causing brief downtime.

### Backup and Recovery

#### Manual Backup

```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=$(terraform output -raw database_instance_name) \
  --project=$PROJECT_ID
```

#### Restore from Backup

```bash
# List backups
gcloud sql backups list \
  --instance=$(terraform output -raw database_instance_name)

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=$(terraform output -raw database_instance_name) \
  --backup-project=$PROJECT_ID
```

### Cost Optimization

#### Reduce Costs for Development

```hcl
environment = "development"
database_tier = "db-f1-micro"
enable_high_availability = false

# In modules/app/main.tf
scaling {
  min_instance_count = 0  # Scale to zero when idle
}
```

#### Monitor Costs

```bash
# View current month costs
gcloud billing projects describe $PROJECT_ID --format="value(billingAccountName)"

# Set up budget alerts in GCP Console
```

## 🐛 Troubleshooting

### Common Issues

#### 1. VPC Peering Failed

**Error**: `Error creating Service Networking Connection`

**Solution**:
```bash
# Ensure Service Networking API is enabled
gcloud services enable servicenetworking.googleapis.com

# Delete and retry
terraform destroy -target=google_service_networking_connection.private_vpc_connection
terraform apply
```

#### 2. Cloud SQL Creation Timeout

**Error**: `timeout while waiting for state to become 'READY'`

**Solution**: Cloud SQL creation can take 10-20 minutes. If it times out, check the GCP Console to see if the instance is still being created. If so, simply run `terraform apply` again.

#### 3. Container Image Not Found

**Error**: `failed to resolve image: image not found`

**Solution**:
```bash
# Build and push images first
docker build -t gcr.io/$PROJECT_ID/streamlit-ui:latest .
docker push gcr.io/$PROJECT_ID/streamlit-ui:latest

# Verify image exists
gcloud container images list --repository=gcr.io/$PROJECT_ID
```

#### 4. Insufficient Permissions

**Error**: `Error 403: ... does not have permission`

**Solution**:
```bash
# Grant yourself the required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/editor"
```

#### 5. Terraform State Lock

**Error**: `Error acquiring the state lock`

**Solution**:
```bash
# Force unlock (use carefully!)
terraform force-unlock LOCK_ID
```

### Debugging

#### Enable Terraform Debug Logging

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log
terraform apply
```

#### Check Cloud Run Logs

```bash
# View logs for a service
gcloud run services logs read streamlit-ui-development \
  --region=asia-northeast1 \
  --limit=50
```

#### Connect to Cloud SQL

```bash
# Using Cloud SQL Proxy
cloud-sql-proxy $(terraform output -raw database_connection_name) &

# Connect with psql
psql -h 127.0.0.1 -U polibase_user -d polibase_db
```

## 🗑 Cleanup

### Destroy All Resources

**⚠️ Warning**: This will delete all data permanently!

```bash
# Preview what will be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy
```

### Destroy Specific Resources

```bash
# Destroy only Cloud Run services
terraform destroy -target=module.app

# Destroy only database (⚠️ data loss!)
terraform destroy -target=module.database
```

## 📚 Additional Resources

- [Terraform GCP Provider Documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Polibase Architecture Documentation](../docs/ARCHITECTURE.md)

## 🤝 Contributing

When making changes to Terraform configurations:

1. Test changes in a separate environment first
2. Run `terraform fmt` to format files
3. Run `terraform validate` to check syntax
4. Document any new variables or outputs
5. Update this README if adding new resources

## 📄 License

This infrastructure code is part of the Polibase project.
