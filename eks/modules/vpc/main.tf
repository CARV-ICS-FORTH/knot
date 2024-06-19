################################################################################
# VPC Module
################################################################################


module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "eks-vpc"
  cidr = "10.0.0.0/16"

  providers = {
    aws = aws.us-east-1
  }

  azs = ["us-east-1a", "us-east-1b", "us-east-1c"]
  #private_subnets     = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k)]
  #public_subnets      = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 4)]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}


################################################################################
# VPC Endpoints Module
################################################################################

# Implement this later
