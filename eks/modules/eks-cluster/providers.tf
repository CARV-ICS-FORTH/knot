
provider "aws" {
  profile = var.profile
  region  = var.main-region
  alias   = "us-east-1"
}

