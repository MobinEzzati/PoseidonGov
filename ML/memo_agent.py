import boto3
import json
import psycopg2
import sys
import re
import os
from dotenv import load_dotenv
from langsmith import traceable
from ML.risk_scoring import (
    compute_hhi, interpret_hhi,
    compute_recompete_risk, interpret_recompete,
    get_agency_breakdown
)


load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGSMITH_API_KEY"] = os.environ.get("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.environ.get("LANGCHAIN_PROJECT", "poseidongov")
os.environ["LANGSMITH_ENDPOINT"] = os.environ.get("LANGSMITH_ENDPOINT","https://eu.api.smith.langchain.com")

sys.path.append("..")


client = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


@traceable(name="generate_memo")
def generate_memo(cur, company_name: str) -> str:

    # Gather all data first
    hhi = compute_hhi(cur, company_name)
    recompete = compute_recompete_risk(cur, company_name)
    breakdown = get_agency_breakdown(cur, company_name)

    # Build the context
    agency_text = "\n".join([
        f"  - {row[0]}: ${row[1]:,.0f} ({row[2]}%)"
        for row in breakdown
    ])

    prompt = f"""You are a PE deal analyst. Write a concise investment diligence memo.

COMPANY: {company_name}

RISK SCORES:
- HHI Concentration: {hhi:.4f} ({interpret_hhi(hhi)})
- Recompete Risk: {recompete:.4f} ({interpret_recompete(recompete)})

AGENCY BREAKDOWN:
{agency_text}

Respond in EXACTLY this format:
<executive_summary>
2-3 sentences
</executive_summary>
<key_risks>
- Risk with specific numbers
- Risk with specific numbers
</key_risks>
<recommendation>
PASS or PROCEED — one sentence reason
Mention what advise our Business consulting team can provide to this business to make them more valuable ==> in three bullet points
</recommendation>
<Advises>
Mention what advise our Business consulting team can provide to this business to make them more valuable - in three bullet points

</Advises

"""

    response = client.invoke_model(
        modelId=MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def parse_memo(memo_text: str) -> dict:
    def extract(tag, text):
        match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    return {
        "executive_summary": extract("executive_summary", memo_text),
        "key_risks": extract("key_risks", memo_text),
        "recommendation": extract("recommendation", memo_text),
    }

if __name__ == "__main__":
    conn = psycopg2.connect(
        host="localhost", port=5432,
        dbname="poseidon", user="poseidon", password="localdev",
    )
    cur = conn.cursor()

    memo = generate_memo(cur, "CONCUR TECHNOLOGIES, INC.")

    result = parse_memo(memo_text=memo)
    print(result)

    cur.close()
    conn.close()