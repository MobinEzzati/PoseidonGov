import sys
from urllib.parse import quote

import requests

TIMEOUT = 60  # seconds; generous for Lambda cold starts and memo generation

KNOWN = ["UNITED AIRLINES, INC.", "FEDERAL EXPRESS CORPORATION", "WARBELOW'S AIR VENTURES, INC"]
UNKNOWN = "NOT A REAL COMPANY"
RISK_KEYS = {"hhi", "hhi_label", "recompete_risk", "recompete_label",
             "recompete_method", "agency_breakdown"}


def company_url(base: str, name: str, suffix: str) -> str:
    return f"{base}/companies/{quote(name, safe='')}/{suffix}"


def check(results: list, name: str, response, expected_codes: set, extra=None) -> None:
    """Record PASS/FAIL for one request. `extra` is an optional function that
    inspects the JSON body and returns an error message, or None if fine."""
    ok = response.status_code in expected_codes
    note = f"status {response.status_code}"
    if ok and extra is not None:
        problem = extra(response.json())
        if problem:
            ok, note = False, problem
    results.append((name, "PASS" if ok else "FAIL", note))


def run(base: str, test_memo: bool) -> list:
    results = []
    get = lambda url: requests.get(url, timeout=TIMEOUT)

    check(results, "health", get(f"{base}/health"), {200})

    check(results, "companies list", get(f"{base}/companies"), {200},
          lambda body: None if body else "empty company list")

    for name in KNOWN:
        r = get(company_url(base, name, "risk"))
        check(results, f"risk: {name}", r, {200},
              lambda body: None if RISK_KEYS <= body.keys()
              else f"missing keys {RISK_KEYS - body.keys()}")
        if r.status_code == 200:
            results[-1] = (*results[-1][:2], f"{results[-1][2]}, method={r.json()['recompete_method']}")

    check(results, "risk: unknown company", get(company_url(base, UNKNOWN, "risk")), {404})

    check(results, "fleet: UNITED AIRLINES, INC.",
          get(company_url(base, "UNITED AIRLINES, INC.", "fleet")), {200})
    # Unknown company may return 404 or an empty fleet; anything 5xx is a bug.
    check(results, "fleet: unknown company", get(company_url(base, UNKNOWN, "fleet")), {200, 404})

    if test_memo:
        check(results, "memo: UNITED AIRLINES, INC.",
              get(company_url(base, "UNITED AIRLINES, INC.", "memo")), {200},
              lambda body: None if body.get("executive_summary") else "no executive_summary")

    return results


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = (args[0] if args else "http://localhost:8000").rstrip("/")
    test_memo = "--memo" in sys.argv

    print(f"Smoke test against {base}\n")
    try:
        results = run(base, test_memo)
    except requests.exceptions.RequestException as e:
        print(f"Could not reach the API: {e}")
        sys.exit(1)

    for name, status, note in results:
        print(f"{status:4}  {name:40s} {note}")

    failed = sum(status == "FAIL" for _, status, _ in results)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()