#  PoseidonGov
AI-powered deal-intelligence platform for PE firms evaluating aviation and 
GovCon assets. PoseidonGov automates due diligence, risk scoring, and 
evaluation cutting the manual research time and error rate that slow 
down analyst decision-making.

MVP scope: PE deals in government contracting, focused on aviation and 
construction. The architecture is built to generalize — the long-term goal 
is a diligence engine for PE more broadly, not just this niche.




<img width="628" height="673" alt="Screenshot 2026-09-13 at 6 55 13 PM" src="https://github.com/user-attachments/assets/16c2f72c-7ef6-4df6-b35e-067519eb823a" />


## What it does
- Ingests live federal procurement data (USASpending, SAM.gov, FAA)
- ML risk scoring: HHI concentration + recompete risk
- AI-generated diligence memos via AWS Bedrock (Claude Sonnet)
- 160+ companies scored, 4,730 contracts, 316K aircraft records

## Stack
   Python, FastAPI, PostgreSQL, Docker, AWS EC2/RDS/ECR/Bedrock

## Built by
Mobin Ezzati | MS Computer Science (AI/ML) — SM xU 2026
# CI/CD enabled
wrote and deployed a .Yaml file to make entire process of push -> docker build - > ecr - > deployed to EC2  automated
# automated deployment working
