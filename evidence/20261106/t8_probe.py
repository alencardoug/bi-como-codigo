"""T8 of docs/publishing_pipeline.md §7: what Google does with this job's own
GitHub OIDC token. Run inside a GitHub Actions job with `id-token: write`:

    python3 evidence/20261106/t8_probe.py --provider "$WIF_PROVIDER" --expect-sts refused
    python3 evidence/20261106/t8_probe.py --provider "$WIF_PROVIDER" --expect-sts issued \
        --expect "$SA_PREVIEW=issued" --expect "$SA_LIVE=denied"

It requests the job's JWT for the provider's default audience, prints the JWT's
claims that the provider's condition and bindings read — never the JWT —,
exchanges it at Google's STS directly, with no action in between, and, when
STS issues a federated token, asks IAM Credentials for a short access token of
each account named by --expect. Every token is masked in the log and kept only
in memory; an issued access token is discarded unused. What Google answers on
a refusal is printed in full: it is the evidence. A refusal at STS counts only
when Google names the attribute condition. Exit 0 only if every outcome is the
one expected. Standard library only, so it runs from a bare checkout.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

STS = "https://sts.googleapis.com/v1/token"
# Names kept apart from the secret guard's sensitive keys: a public endpoint
# and RFC 8693 type URNs, not credentials.
GENERATE_URL = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{}:generateAccessToken"
URN_JWT = "urn:ietf:params:oauth:token-type:jwt"
URN_ACCESS = "urn:ietf:params:oauth:token-type:access_token"
CLAIMS = ("repository", "ref", "workflow_ref", "job_workflow_ref", "event_name", "environment", "sub")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """No redirect is expected from these endpoints; following one would carry
    a bearer token to wherever it points."""

    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def mask(value: str) -> None:
    print(f"::add-mask::{value}", flush=True)


def call(request: urllib.request.Request) -> tuple[int, dict]:
    try:
        with OPENER.open(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(body)
        except ValueError:
            return error.code, {"body": body}


def job_jwt(audience: str) -> str:
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&" + urllib.parse.urlencode({"audience": audience})
    status, body = call(urllib.request.Request(url, headers={
        "Authorization": "bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"], "User-Agent": "bi-como-codigo-t8"}))
    if status != 200 or "value" not in body:
        sys.exit(f"GitHub issued no OIDC token: HTTP {status}")
    mask(body["value"])
    return body["value"]


def claims(jwt: str) -> dict:
    payload = jwt.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def exchange(jwt: str, provider: str) -> tuple[int, dict]:
    form = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "audience": "//iam.googleapis.com/" + provider,
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "requested_token_type": URN_ACCESS,
        "subject_token_type": URN_JWT,
        "subject_token": jwt,
    }).encode()
    return call(urllib.request.Request(STS, data=form, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "bi-como-codigo-t8"}))


def impersonate(federated: str, account: str) -> tuple[int, dict]:
    # The narrowest scope and the shortest lifetime: the token is never used.
    body = json.dumps({"scope": ["https://www.googleapis.com/auth/userinfo.email"], "lifetime": "300s"}).encode()
    return call(urllib.request.Request(GENERATE_URL.format(urllib.parse.quote(account, safe="@.")), data=body,
                                       method="POST", headers={"Authorization": "Bearer " + federated,
                                                               "Content-Type": "application/json",
                                                               "User-Agent": "bi-como-codigo-t8"}))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, help="projects/<number>/locations/global/workloadIdentityPools/<pool>/providers/<id>")
    parser.add_argument("--expect-sts", required=True, choices=["issued", "refused"])
    parser.add_argument("--expect", action="append", default=[], metavar="ACCOUNT=issued|denied")
    args = parser.parse_args(argv)
    expected = {}
    for item in args.expect:
        account, _, outcome = item.rpartition("=")
        if not account or outcome not in ("issued", "denied"):
            parser.error(f"--expect {item!r}: ACCOUNT=issued|denied")
        expected[account] = outcome
    if args.expect_sts == "refused" and expected:
        parser.error("--expect needs --expect-sts issued")

    jwt = job_jwt("https://iam.googleapis.com/" + args.provider)
    seen = claims(jwt)
    print("JWT claims:", json.dumps({k: seen.get(k) for k in CLAIMS}, sort_keys=True))

    ok = True
    status, body = exchange(jwt, args.provider)
    if status == 200 and "access_token" in body:
        federated = body["access_token"]
        mask(federated)
        print("STS: HTTP 200, a federated token issued (kept in memory, masked)")
        sts = "issued"
    else:
        print(f"STS: HTTP {status}, refused:", json.dumps(body, sort_keys=True))
        # Refused on the provider's condition, as T11 recorded it — not on a
        # malformed token or a wrong audience, which would prove nothing.
        sts = "refused" if (status == 400 and body.get("error") == "unauthorized_client"
                            and "attribute condition" in body.get("error_description", "")) else f"HTTP {status}"
    if sts != args.expect_sts:
        print(f"UNEXPECTED: STS {sts}, expected {args.expect_sts}")
        ok = False

    for account, outcome in expected.items():
        if sts != "issued":
            print(f"{account}: not tried, STS issued no federated token")
            ok = False
            continue
        status, body = impersonate(federated, account)
        if status == 200 and "accessToken" in body:
            mask(body["accessToken"])
            print(f"{account}: HTTP 200, an access token issued, expiring {body.get('expireTime')} (discarded unused)")
            got = "issued"
        else:
            print(f"{account}: HTTP {status}:", json.dumps(body, sort_keys=True))
            got = "denied" if status == 403 and body.get("error", {}).get("status") == "PERMISSION_DENIED" else f"HTTP {status}"
        if got != outcome:
            print(f"UNEXPECTED: {account} {got}, expected {outcome}")
            ok = False

    print("as expected" if ok else "NOT as expected")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
