# lambda-twitter-rolling-icon

A simple Lambda Function
- changes your Twitter profile image (and description) at a fixed interval
- this interval is defined in schedule expression of EventBridge Event

## Prerequisites

- get Twitter Access Token and Access Token Secret. [see here](https://developer.twitter.com/ja/docs/basics/authentication/guides/access-tokens)
- get Twitter API Key and Secret (a.k.a. Consumer Key and Secret). [see here](https://developer.twitter.com/en/docs/authentication/oauth-1-0a/api-key-and-secret)
- create a S3 bucket and store images for your Twitter account.

```bash
aws s3 mb s3://your-bucket
aws s3 cp your-icon-image.png s3://your-bucket/ # more than two files!!
```

## Provisioning

You can use [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) to provision this function.

```bash
sam build
sam deploy --guided
```
