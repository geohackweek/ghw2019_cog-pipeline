provider "aws" {
  region  = "us-east-1"
}

# Variables
variable "region" {
  type    = "string"
  default = "us-east-1"
}

variable "tiler_bucket" {
  type    = "string"
  default = "aimeeb-datasets-public"
}

variable "stage_name" {
  description = "The stage name(production/staging/etc..)"
  default     = "production"
}

# API Gateway + Lambda
module "tiler_api" {
  source = "./modules/tiler_api"

  # General options
  project    = "tiler"
  stage_name = "${var.stage_name}"
  region     = "${var.region}"

  # Lambda options
  lambda_name    = "dynamic-tiler"
  lambda_runtime = "python3.6"
  lambda_memory  = "3008"
  lambda_timeout = "10"
  lambda_package = "package.zip" # local file created by `docker-compose run --rm package`
  lambda_handler = "tiler.api.APP"

  lambda_env = {
    PYTHONWARNINGS                     = "ignore"
    GDAL_DATA                          = "/var/task/share/gdal"
    GDAL_CACHEMAX                      = "512"
    VSI_CACHE                          = "TRUE"
    VSI_CACHE_SIZE                     = "536870912"
    CPL_TMPDIR                         = "/tmp"
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES = "YES"
    GDAL_HTTP_MULTIPLEX                = "YES"
    GDAL_HTTP_VERSION                  = "2"
    GDAL_DISABLE_READDIR_ON_OPEN       = "FALSE"
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS   = ".TIF,.ovr"
  }
}

resource "aws_iam_role_policy" "permissions" {
  name = "${module.tiler_api.lambda_role}-bucket-permission"
  role = "${module.tiler_api.lambda_role_id}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::${var.tiler_bucket}*"
    }
  ]
}
EOF
}

# Outputs
output "endpoint" {
  description = "tiler dynamic tiler endpoint url"
  value       = "${module.tiler_api.api_url}"
}
