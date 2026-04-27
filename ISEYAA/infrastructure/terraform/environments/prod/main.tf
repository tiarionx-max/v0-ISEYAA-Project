# ============================================================
# ISEYAA — Terraform Infrastructure
# AWS af-south-1 (Cape Town) — Primary Region
# PRD Reference: §5.4 Cloud Infrastructure — AWS
# ============================================================
# Usage:
#   cd infrastructure/terraform/environments/prod
#   terraform init
#   terraform plan -out=tfplan
#   terraform apply tfplan
# ============================================================

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.45"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.29"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state stored in S3 + DynamoDB lock
  backend "s3" {
    bucket         = "iseyaa-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "af-south-1"
    encrypt        = true
    kms_key_id     = "alias/iseyaa-terraform"
    dynamodb_table = "iseyaa-terraform-locks"
  }
}

# ── Providers ─────────────────────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ISEYAA"
      Environment = var.environment
      ManagedBy   = "Terraform"
      State       = "OgunState"
      Owner       = "OgunStateCTO"
    }
  }
}

provider "aws" {
  alias  = "dr"
  region = var.dr_region   # eu-west-1 disaster recovery

  default_tags {
    tags = {
      Project     = "ISEYAA"
      Environment = "${var.environment}-dr"
      ManagedBy   = "Terraform"
    }
  }
}

# ── Variables ─────────────────────────────────────────────────────────────────

variable "aws_region"   { default = "af-south-1" }
variable "dr_region"    { default = "eu-west-1" }
variable "environment"  { default = "production" }
variable "project_name" { default = "iseyaa" }

variable "eks_cluster_version"     { default = "1.30" }
variable "eks_node_instance_types" { default = ["t3.xlarge", "t3.2xlarge"] }
variable "eks_min_nodes"           { default = 3 }
variable "eks_max_nodes"           { default = 20 }
variable "eks_desired_nodes"       { default = 5 }

variable "rds_instance_class"  { default = "db.t3.large" }
variable "rds_engine_version"  { default = "16.2" }
variable "rds_storage_gb"      { default = 100 }
variable "rds_multi_az"        { default = true }

variable "elasticache_node_type"  { default = "cache.t3.medium" }
variable "elasticache_num_nodes"  { default = 2 }

# ── Networking ────────────────────────────────────────────────────────────────

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.7"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs              = ["af-south-1a", "af-south-1b", "af-south-1c"]
  private_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets   = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  database_subnets = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false   # Multi-AZ NAT for HA
  one_nat_gateway_per_az = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # Required for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"             = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}

locals {
  cluster_name = "${var.project_name}-eks-${var.environment}"
}

# ── EKS Cluster ───────────────────────────────────────────────────────────────

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = local.cluster_name
  cluster_version = var.eks_cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    general = {
      instance_types = var.eks_node_instance_types
      min_size       = var.eks_min_nodes
      max_size       = var.eks_max_nodes
      desired_size   = var.eks_desired_nodes

      labels = {
        workload = "general"
      }
    }

    ai_workloads = {
      instance_types = ["t3.2xlarge"]
      min_size       = 1
      max_size       = 5
      desired_size   = 2

      labels = {
        workload = "ai"
      }
      taints = [{
        key    = "workload"
        value  = "ai"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  # AWS Load Balancer Controller
  enable_cluster_creator_admin_permissions = true
}

# ── RDS PostgreSQL (Primary — Multi-AZ) ──────────────────────────────────────

module "rds_primary" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.6"

  identifier = "${var.project_name}-postgres-${var.environment}"

  engine               = "postgres"
  engine_version       = var.rds_engine_version
  instance_class       = var.rds_instance_class
  allocated_storage    = var.rds_storage_gb
  max_allocated_storage = 500

  db_name  = "iseyaa_db"
  username = "iseyaa_user"
  port     = 5432

  multi_az               = var.rds_multi_az
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.rds_sg.security_group_id]

  maintenance_window       = "Mon:03:00-Mon:04:00"
  backup_window            = "02:00-03:00"
  backup_retention_period  = 30
  skip_final_snapshot      = false
  deletion_protection      = true

  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  performance_insights_enabled = true
  monitoring_interval          = 60

  parameters = [
    { name = "shared_preload_libraries", value = "pg_stat_statements" },
    { name = "log_min_duration_statement", value = "1000" },  # Log queries >1s
    { name = "work_mem", value = "16384" },
  ]
}

# Separate RDS for Wallet Service (financial isolation)
module "rds_wallet" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.6"

  identifier    = "${var.project_name}-postgres-wallet-${var.environment}"
  engine        = "postgres"
  engine_version = var.rds_engine_version
  instance_class = "db.t3.large"
  allocated_storage = 50
  max_allocated_storage = 200

  db_name  = "iseyaa_wallet_db"
  username = "iseyaa_wallet"
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.rds_sg.security_group_id]

  backup_retention_period = 90   # 90 days for financial data
  deletion_protection     = true
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds.arn
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project_name}-redis-${var.environment}"
  description          = "ISEYAA Redis — sessions, caching, rate limiting, real-time"

  node_type            = var.elasticache_node_type
  num_cache_clusters   = var.elasticache_num_nodes
  engine               = "redis"
  engine_version       = "7.2"
  port                 = 6379

  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [module.redis_sg.security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = aws_secretsmanager_secret_version.redis_auth.secret_string

  automatic_failover_enabled = true
  multi_az_enabled           = true

  snapshot_retention_limit = 7
  snapshot_window          = "02:30-03:30"
}

# ── S3 Buckets ────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "media" {
  bucket = "${var.project_name}-media-${var.environment}"
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

# Block all public access to S3 (served via CloudFront only)
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── KMS Keys ──────────────────────────────────────────────────────────────────

resource "aws_kms_key" "rds" {
  description             = "ISEYAA RDS encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_key" "s3" {
  description             = "ISEYAA S3 encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "eks_cluster_endpoint"     { value = module.eks.cluster_endpoint }
output "eks_cluster_name"         { value = module.eks.cluster_name }
output "rds_primary_endpoint"     { value = module.rds_primary.db_instance_endpoint }
output "rds_wallet_endpoint"      { value = module.rds_wallet.db_instance_endpoint }
output "redis_endpoint"           { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "media_bucket_name"        { value = aws_s3_bucket.media.bucket }
output "vpc_id"                   { value = module.vpc.vpc_id }
