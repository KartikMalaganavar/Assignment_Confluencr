#!/usr/bin/env python3
import argparse
import dataclasses
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx


@dataclasses.dataclass
class TestResult:
    name: str
    passed: bool
    detail: str
    extra: str | None = None


def make_payload(txn_id: str, amount: int = 1500) -> dict:
    return {
        "transaction_id": txn_id,
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": amount,
        "currency": "INR",
    }


def extract_status(response_json):
    # Supports both object and list response shapes.
    if isinstance(response_json, list):
        if not response_json:
            return None
        return response_json[0].get("status")
    if isinstance(response_json, dict):
        return response_json.get("status")
    return None


def get_transaction(client: httpx.Client, base_url: str, txn_id: str):
    return client.get(f"{base_url}/v1/transactions/{txn_id}")


def poll_processed(
    client: httpx.Client, base_url: str, txn_id: str, max_wait_seconds: int, poll_interval_seconds: float
) -> tuple[bool, str | None]:
    deadline = time.time() + max_wait_seconds
    last_status = None
    while time.time() < deadline:
        resp = get_transaction(client, base_url, txn_id)
        if resp.status_code == 200:
            status = extract_status(resp.json())
            last_status = status
            if status == "PROCESSED":
                return True, status
        time.sleep(poll_interval_seconds)
    return False, last_status


def run_health_check(client: httpx.Client, base_url: str) -> TestResult:
    try:
        resp = client.get(f"{base_url}/")
        if resp.status_code != 200:
            return TestResult("Health Check", False, f"Expected 200, got {resp.status_code}")
        body = resp.json()
        if body.get("status") != "HEALTHY":
            return TestResult("Health Check", False, f"Expected HEALTHY, got {body.get('status')!r}")
        return TestResult("Health Check", True, "Health check endpoint working correctly")
    except Exception as exc:  # noqa: BLE001
        return TestResult("Health Check", False, f"Exception: {exc}")


def run_response_time(client: httpx.Client, base_url: str, max_ack_ms: float) -> TestResult:
    txn_id = f"speed_{uuid.uuid4().hex[:10]}"
    payload = make_payload(txn_id)
    try:
        started = time.perf_counter()
        resp = client.post(f"{base_url}/v1/webhooks/transactions", json=payload)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if resp.status_code // 100 != 2:
            return TestResult("Response Time", False, f"Expected 2xx, got {resp.status_code}")
        if elapsed_ms > max_ack_ms:
            return TestResult("Response Time", False, f"Response took {elapsed_ms:.1f}ms (> {max_ack_ms:.0f}ms)")
        return TestResult("Response Time", True, f"Responded in {elapsed_ms:.1f}ms with 2xx status ({resp.status_code})")
    except Exception as exc:  # noqa: BLE001
        return TestResult("Response Time", False, f"Exception: {exc}")


def run_transaction_processing(
    client: httpx.Client, base_url: str, processing_wait_seconds: int, poll_interval_seconds: float
) -> TestResult:
    txn_id = f"processing_{uuid.uuid4().hex[:10]}"
    try:
        post_resp = client.post(f"{base_url}/v1/webhooks/transactions", json=make_payload(txn_id))
        if post_resp.status_code // 100 != 2:
            return TestResult("Transaction Processing", False, f"Webhook failed: {post_resp.status_code}")
        ok, status = poll_processed(client, base_url, txn_id, processing_wait_seconds, poll_interval_seconds)
        if not ok:
            return TestResult(
                "Transaction Processing",
                False,
                f"Expected PROCESSED status after {processing_wait_seconds}s, got {status!r}",
            )
        return TestResult("Transaction Processing", True, "Transaction moved to PROCESSED state")
    except Exception as exc:  # noqa: BLE001
        return TestResult("Transaction Processing", False, f"Exception: {exc}")


def run_idempotency(client: httpx.Client, base_url: str, processing_wait_seconds: int, poll_interval_seconds: float) -> TestResult:
    txn_id = f"idempotent_{uuid.uuid4().hex[:10]}"
    payload = make_payload(txn_id)
    try:
        first = client.post(f"{base_url}/v1/webhooks/transactions", json=payload)
        second = client.post(f"{base_url}/v1/webhooks/transactions", json=payload)
        if first.status_code // 100 != 2:
            return TestResult("Idempotency", False, f"First webhook failed: {first.status_code}")
        if second.status_code // 100 != 2:
            return TestResult("Idempotency", False, f"Duplicate webhook failed: {second.status_code}")

        ok, status = poll_processed(client, base_url, txn_id, processing_wait_seconds, poll_interval_seconds)
        if not ok:
            return TestResult("Idempotency", False, f"Duplicate webhook did not settle to PROCESSED, got {status!r}")
        return TestResult("Idempotency", True, "Duplicate webhook handled without processing error")
    except Exception as exc:  # noqa: BLE001
        return TestResult("Idempotency", False, f"Exception: {exc}")


def run_concurrent_transactions(
    client: httpx.Client,
    base_url: str,
    processing_wait_seconds: int,
    poll_interval_seconds: float,
    concurrent_count: int,
) -> TestResult:
    txns = [f"concurrent_{uuid.uuid4().hex[:8]}_{i}" for i in range(concurrent_count)]
    payloads = [make_payload(txn_id, amount=1000 + i) for i, txn_id in enumerate(txns)]

    def post_one(payload: dict) -> int:
        return client.post(f"{base_url}/v1/webhooks/transactions", json=payload).status_code

    try:
        with ThreadPoolExecutor(max_workers=concurrent_count) as ex:
            codes = list(ex.map(post_one, payloads))
        bad_codes = [code for code in codes if code // 100 != 2]
        if bad_codes:
            return TestResult("Concurrent Transactions", False, f"Concurrent webhook failures: {bad_codes}")

        failed = []
        for txn_id in txns:
            ok, status = poll_processed(client, base_url, txn_id, processing_wait_seconds, poll_interval_seconds)
            if not ok:
                failed.append((txn_id, status))
        if failed:
            return TestResult("Concurrent Transactions", False, f"Not all concurrent transactions processed: {failed}")
        return TestResult("Concurrent Transactions", True, f"All {concurrent_count} concurrent transactions are being processed")
    except Exception as exc:  # noqa: BLE001
        return TestResult("Concurrent Transactions", False, f"Exception: {exc}")


def print_report(results: list[TestResult], total_seconds: float) -> int:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    verdict = "PASS" if passed == total else "FAIL"
    print(f"RESULT: {verdict} ({passed} / {total} tests passed)\n")
    print("Test results:")
    for res in results:
        state = "PASS" if res.passed else "FAIL"
        print(f"- {state} | {res.name}")
        print(f"  - {res.detail}")
        if res.extra:
            print(f"  - {res.extra}")
    print(f"\nTotal time: {total_seconds:.1f}s")
    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Assignment validator script")
    parser.add_argument("--base-url", default="https://assignment-confluencr.onrender.com", help="Base URL of API")
    parser.add_argument("--request-timeout-seconds", type=float, default=10.0, help="HTTP request timeout")
    parser.add_argument("--max-ack-ms", type=float, default=1000.0, help="Max webhook ACK latency in ms")
    parser.add_argument("--processing-wait-seconds", type=int, default=40, help="Max wait for PROCESSED status")
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0, help="Polling interval for status checks")
    parser.add_argument("--concurrent-count", type=int, default=3, help="Number of concurrent webhooks")
    args = parser.parse_args()

    started = time.perf_counter()
    with httpx.Client(timeout=args.request_timeout_seconds) as client:
        results = [
            run_health_check(client, args.base_url),
            run_response_time(client, args.base_url, args.max_ack_ms),
            run_transaction_processing(client, args.base_url, args.processing_wait_seconds, args.poll_interval_seconds),
            run_idempotency(client, args.base_url, args.processing_wait_seconds, args.poll_interval_seconds),
            run_concurrent_transactions(
                client,
                args.base_url,
                args.processing_wait_seconds,
                args.poll_interval_seconds,
                args.concurrent_count,
            ),
        ]
    total = time.perf_counter() - started
    return print_report(results, total)


if __name__ == "__main__":
    sys.exit(main())
