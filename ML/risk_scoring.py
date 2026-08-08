import psycopg2
import datetime


def interpret_hhi(hhi: float) -> str:
    if hhi > 0.6:
        return "HIGH RISK"
    elif hhi > 0.3:
        return "MODERATE"
    else:
        return "HEALTHY"
    
def interpret_recompete(score: float) -> str:
    if score > 0.7:
        return "HIGH"
    elif score > 0.4:
        return "MEDIUM"
    else:
        return "LOW"
        

def compute_hhi(cur, company_name: str) -> float:
    # original clean query — parameterized, no hardcoding
    cur.execute("""
        SELECT awarding_agency, SUM(amount) as total
        FROM award
        WHERE recipient_name = %s
        GROUP BY awarding_agency
    """, (company_name,))
    rows = cur.fetchall()
    total = sum(row[1] for row in rows)
    hhi = sum((row[1] / total) ** 2 for row in rows)
    return hhi


def get_agency_breakdown(cur, company_name: str):
    # the breakdown query — for human-readable output
    cur.execute("""
        SELECT awarding_agency, SUM(amount) as total,
               ROUND(SUM(amount) / (SELECT SUM(amount) FROM award 
               WHERE recipient_name = %s) * 100, 1) as pct
        FROM award
        WHERE recipient_name = %s
        GROUP BY awarding_agency
        ORDER BY total DESC
    """, (company_name, company_name))
    return cur.fetchall()

def score_all_companies(cur, min_awards: int = 5) -> list:
    cur.execute("""
        SELECT recipient_name, COUNT(*) as award_count
        FROM award
        WHERE amount > 0
        GROUP BY recipient_name
        HAVING COUNT(*) >= %s
    """, (min_awards,))
    companies = [row[0] for row in cur.fetchall()]
    
    results = []
    for company in companies:
        hhi = compute_hhi(cur, company)
        
        results.append((
        company,
        hhi,
        interpret_hhi(hhi),
        compute_recompete_risk(cur, company),
        ))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results
def save_score_scores(cur, conn, scores):
    for company, hhi, label, recompete in scores:
        cur.execute(
            """
            INSERT INTO risk_score (recipient_name, as_of, hhi_agency, recompete_risk)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (recipient_name, as_of) DO UPDATE 
                SET hhi_agency = EXCLUDED.hhi_agency,
                    recompete_risk = EXCLUDED.recompete_risk
            """,
            (company, datetime.date.today(), hhi, recompete)
        )
    conn.commit()
    print(f"Saved {len(scores)} risk scores")

def compute_recompete_risk(cur, company_name: str) -> float:
    cur.execute (
        """
        SELECT amount, pop_end
        from Award
        WHERE recipient_name = %s
        AND pop_end is not Null 
        AND amount > 0
        """
        ,
        (company_name,))
    
    rows = cur.fetchall()
    if not rows:
        return 0.0 
    max_amount = max( row[0] for row in rows)
    today = datetime.date.today()

    scores = []
    for amount, pop_end in rows:
        days_remaining = (pop_end - today).days
        days_score = max(0, min(1, (365 - days_remaining) / 365))
        amount_score = float(amount) / float(max_amount)
        recompete_risk =  (days_score + amount_score)/ 2
        scores.append(recompete_risk)

    return max(scores)

# def list_companies(cur):
#     res = {}
#     cur.execute("""
#         SELECT recipient_name,recompete_risk FROM risk_score
#     """)

#     rows = cur.fetchall()

#     for row in rows :
#         res[row[0]] = row[1]

#     return res



if __name__ == "__main__":

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="poseidon",
        user="poseidon",
        password="localdev",
    )
    cur = conn.cursor()

    company = "CONCUR TECHNOLOGIES, INC."
    hhi = compute_hhi(cur, company)
    print(f"HHI for {company}: {hhi:.4f} — {interpret_hhi(hhi)}")

    print("\nAgency breakdown:")
    rows = get_agency_breakdown(cur, company)
    for agency, total, pct in rows:
        print(f"  {agency[:45]:45} {pct}%")
    for company in ["CW GOVERNMENT TRAVEL INC", "FEDERAL EXPRESS CORPORATION"]:

        hhi = compute_hhi(cur, company)
        print(f"{company}: {hhi:.4f} — {interpret_hhi(hhi)}")
    print("\nAll companies ranked by concentration risk:")
    all_scores = score_all_companies(cur)
    for company, hhi, hhi_label, recompete in all_scores:

        print(f"  {company[:40]:40} HHI:{hhi:.2f} {hhi_label:10} Recompete:{recompete:.2f} {interpret_recompete(recompete)}")


    for company in ["CW GOVERNMENT TRAVEL INC", "FEDERAL EXPRESS CORPORATION"]:
             ## compute_recompete_risk
             print("compute result")
             tst = compute_recompete_risk(cur,company_name=company)
             print(tst)
    
    

    # save_score_scores(cur, conn, all_scores)
    list_companies(cur=cur)
    cur.close()
    conn.close()

