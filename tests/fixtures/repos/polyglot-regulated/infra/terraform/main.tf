terraform {
  required_version = ">= 1.5.0"
}

resource "aws_s3_bucket" "logs" {
  bucket = "polyglot-regulated-logs"
}
