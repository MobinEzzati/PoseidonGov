import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.invoke_model(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Say hello in one sentence."}]
    })
)



result = json.loads(response["body"].read())
print(result["content"][0]["text"])