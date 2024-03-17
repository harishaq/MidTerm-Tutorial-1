#!/usr/bin/env python
from constructs import Construct
from cdktf import App, NamedRemoteWorkspace, TerraformStack, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.s3_bucket import S3Bucket, S3BucketConfig, S3BucketWebsite
from cdktf_cdktf_provider_aws.s3_bucket_website_configuration import S3BucketWebsiteConfiguration
from cdktf_cdktf_provider_aws.s3_bucket_acl import S3BucketAcl
from cdktf_cdktf_provider_aws.s3_bucket_ownership_controls import S3BucketOwnershipControls, S3BucketOwnershipControlsRule
from cdktf_cdktf_provider_aws.s3_bucket_public_access_block import S3BucketPublicAccessBlock
from cdktf_cdktf_provider_aws.s3_bucket_policy import S3BucketPolicy
import json
#from cdktf_cdktf_provider_aws.s3_bucket import S3Bucket, S3BucketWebsite, S3BucketOwnershipControls, S3BucketPublicAccessBlock
# 3. for uploading files
from cdktf_cdktf_provider_aws.s3_object import S3Object
import mimetypes
import os



class MyStack(TerraformStack):
    def __init__(self, scope: Construct, ns: str):
        super().__init__(scope, ns)

        AwsProvider(self, "AWS", region="us-east-1")

        #C1. reate an S3 bucket
        bucket = S3Bucket(self, "MyBucket",
                          bucket="tutorial-1-static-web-hosting", # Ensure this is unique
                          )
                          
        # Configure static website hoting: 
                          
        # resource "aws_s3_bucket_website_configuration" "example" {
        #   bucket = aws_s3_bucket.example.id
        
        #   index_document {
        #     suffix = "index.html"
        #   }
        
        #   error_document {
        #     key = "error.html"
        #   }
        
        # }
        
        website_config = S3BucketWebsiteConfiguration(self, "WebsiteConfiguration",
                            bucket=bucket.bucket,
                            index_document={ "suffix":"index.html"},
                            error_document={ "key":"error.html"}
                            )
                            
        # output the website url
        TerraformOutput(self, "website_url",
                value=website_config.website_endpoint,
                )
        
        
        # 2. Allow public access to teh bucket
        # See https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_acl
        s3ownership = S3BucketOwnershipControls(self, "S3BucketOwnershipControls",
                                    bucket=bucket.bucket,
                                    rule=S3BucketOwnershipControlsRule(object_ownership="BucketOwnerPreferred")
                                    )
        s3publicacces = S3BucketPublicAccessBlock(self, "S3BucketPublicAccessBlock", 
                                    bucket=bucket.bucket,
                                    block_public_acls=False,
                                    block_public_policy=False,
                                    ignore_public_acls=False,
                                    restrict_public_buckets=False)
        
        bucket_acl = S3BucketAcl(self, "MyBucketAcl", bucket=bucket.bucket, acl="public-read", depends_on = [s3ownership, s3publicacces ])
        
        # adding s3 bucket policy allow read acces to the website content
        # resource "aws_s3_bucket_policy" "allow_access_from_another_account" {
        #   bucket = aws_s3_bucket.example.id
        #   policy = data.aws_iam_policy_document.allow_access_from_another_account.json
        # }
        
        # {
        #     "Version": "2012-10-17",
        #     "Statement": [
        #         {
        #             "Sid": "PublicReadGetObject",
        #             "Effect": "Allow",
        #             "Principal": "*",
        #             "Action": "s3:GetObject",
        #             "Resource": "arn:aws:s3:::tutorial-1-static-web-hosting/*"
        #         }
        #     ]
        # }
        
        bucket_policy = S3BucketPolicy(self, "PublicReadPolicy", 
                        bucket=bucket.bucket, 
                         policy=json.dumps({
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Sid": "PublicReadGetObject",
                                    "Effect": "Allow",
                                    "Principal": "*",
                                    "Action": "s3:GetObject",
                                    "Resource": "arn:aws:s3:::"+bucket.bucket+"/*"
                                }
                            ]
                        }),
                        depends_on = [bucket_acl] )
        
        
        # 3. upload static websit content to S3
        #  https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object
        
        # resource "aws_s3_object" "object" {
        #   bucket = "your_bucket_name"
        #   key    = "new_object_key"
        #   source = "path/to/file"
        
        #   # The filemd5() function is available in Terraform 0.11.12 and later
        #   # For Terraform 0.11.11 and earlier, use the md5() function and the file() function:
        #   # etag = "${md5(file("path/to/file"))}"
        #   etag = filemd5("path/to/file")
        # }
        
        location="static-website"
        
        for root, dirs, files in os.walk(location):

            for file in files:
                print(os.path.join(root, file))
                file_rel_path = os.path.join(root, file)
                mime_type, _ = mimetypes.guess_type(file_rel_path)
                # exluding the parent folder
                file_location_s3 = os.path.sep.join(file_rel_path.split(os.path.sep)[1:])
                print(file_rel_path, " ", file_location_s3 , " ", mime_type )
                S3Object(self, "object-"+file_location_s3, 
                            bucket=bucket.bucket, 
                            key=file_location_s3, 
                            source=os.path.abspath(file_rel_path), 
                            content_type=mime_type )
        
        
    
app = App()
MyStack(app, "static_website_s3")

app.synth()
