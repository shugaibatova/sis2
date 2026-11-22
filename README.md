# SIS 2 — Lambda functions (least-privilege role, version, alias)

Two Lambda functions (`create_item`, `get_item`) backed by one DynamoDB table.
Every function has:

| Requirement | Where in `template.yaml` |
|---|---|
| Least-privilege role | `CreateItemRole` (only `dynamodb:PutItem` on the one table), `GetItemRole` (only `dynamodb:GetItem`); logs only to their own log group |
| Published version | `CreateItemVersion`, `GetItemVersion` (`AWS::Lambda::Version`) |
| Alias | `CreateItemAlias`, `GetItemAlias` (`live`, points to the published version) |

Next week API Gateway and Step Functions should call the **alias ARN** (see Outputs), not `$LATEST`.

## Requirements
- AWS CLI v2, configured (`aws configure` or SSO profile) with permission to create IAM roles, Lambda, DynamoDB, CloudFormation
- An S3 bucket for packaging (any bucket you own)
- Python 3.13 locally (for unit tests only)

## Step by step

1. **Run unit tests (no AWS needed)**
   ```bash
   python3 -m unittest discover -s tests -v
   ```

2. **Package the code** (uploads the function folders to S3 and rewrites `Code:` in the template)
   ```bash
   aws cloudformation package \
     --template-file template.yaml \
     --s3-bucket <YOUR_BUCKET> \
     --output-template-file packaged.yaml
   ```

3. **Deploy**
   ```bash
   aws cloudformation deploy \
     --template-file packaged.yaml \
     --stack-name sis2-lambda \
     --capabilities CAPABILITY_IAM \
     --parameter-overrides Environment=dev ReleaseTag=v1
   ```

4. **Read the outputs** (version numbers, alias ARNs, role ARNs)
   ```bash
   aws cloudformation describe-stacks --stack-name sis2-lambda \
     --query "Stacks[0].Outputs" --output table
   ```

5. **Invoke through the alias** (note the `:live` suffix)
   ```bash
   aws lambda invoke --function-name <CreateItemFunctionName>:live \
     --cli-binary-format raw-in-base64-out \
     --payload '{"id":"1","name":"book"}' out.json && cat out.json

   aws lambda invoke --function-name <GetItemFunctionName>:live \
     --cli-binary-format raw-in-base64-out \
     --payload '{"id":"1"}' out.json && cat out.json
   ```
   Expected: `201` with the item, then `200` with the same item.

6. **Show the version and alias exist** (evidence for the defence)
   ```bash
   aws lambda list-versions-by-function --function-name <CreateItemFunctionName>
   aws lambda get-alias --function-name <CreateItemFunctionName> --name live
   ```

7. **Prove the role is least-privilege**
   ```bash
   aws iam list-role-policies --role-name <role name from RoleArn>
   aws iam get-role-policy --role-name <role name> --policy-name create-item-least-privilege
   ```
   Optional negative test: temporarily try `get_item` logic from `create_item` — it fails with `AccessDenied`, because `create_item` has no `GetItem`.

8. **Release a new version**
   Edit code in `src/...`, then repeat steps 2–3 with a new tag:
   `ReleaseTag=v2`. A new version is published and the `live` alias moves to it.
   Older versions are kept (`Retain`), so you can roll back by deploying with the old tag
   or by `aws lambda update-alias --function-name ... --name live --function-version <old>`.

## Clean up (important)
```bash
aws cloudformation delete-stack --stack-name sis2-lambda
aws cloudformation wait stack-delete-complete --stack-name sis2-lambda
```
`AWS::Lambda::Version` resources use `Retain`, so old versions stay attached to the
function until the function is deleted. Because the function itself is deleted with the stack,
versions disappear with it. Also delete the packaging S3 objects you uploaded.

## Notes for the defence
- Why not `AWSLambdaBasicExecutionRole`? It allows `logs:CreateLogGroup` on `*`. Here the log groups are created by the template and each role can write only to its own group.
- Why an alias? Callers get a stable ARN; releases change what the alias points to, not the callers.
- Versions are immutable: code + config are frozen at publish time.
