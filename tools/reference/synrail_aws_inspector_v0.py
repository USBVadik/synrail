"""Synrail AWS state inspector.

Generic primitive that verifies claims about deployed AWS resources against
their actual state. Designed to be called from `synrail verify-aws-state` and
to be reusable across submissions.

Design constraints
------------------
- boto3 is an optional dependency. If unavailable, the inspector returns a
  structured "unavailable" result and the caller can decide how to surface
  this. We do not crash the rest of Synrail.
- Read-only AWS API calls only. Inspector never mutates AWS state.
- One dispatcher per resource type. Adding a new resource type means adding
  one function and registering it in RESOURCE_VERIFIERS.
- Each verifier returns a ClaimResult with: passed (bool), actual (dict),
  diff (list[str]), error (str | None).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

try:
    import boto3  # type: ignore
    from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover - boto3 optional
    boto3 = None  # type: ignore
    BotoCoreError = Exception  # type: ignore
    ClientError = Exception  # type: ignore
    BOTO3_AVAILABLE = False


@dataclass
class ClaimResult:
    """Result of verifying one aws_state_claim."""

    claim_id: str
    resource_type: str
    identifier: str
    passed: bool
    actual: dict[str, Any] = field(default_factory=dict)
    diff: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_value(actual: dict[str, Any], dotted_path: str) -> Any:
    """Walk a dotted path through nested dicts. Returns None if missing."""
    cursor: Any = actual
    for part in dotted_path.split("."):
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None
    return cursor


def _compare_expected(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """Return list of diff strings. Empty list means full match."""
    diffs: list[str] = []
    for key, expected_value in expected.items():
        actual_value = _resolve_value(actual, key)
        if actual_value != expected_value:
            diffs.append(
                f"{key}: expected {expected_value!r}, got {actual_value!r}"
            )
    return diffs


def _aws_session(region: str | None = None):
    """Create a boto3 session honoring AWS_PROFILE / AWS_REGION env vars."""
    if not BOTO3_AVAILABLE:
        return None
    profile = os.environ.get("AWS_PROFILE")
    region_name = region or os.environ.get("AWS_REGION") or os.environ.get(
        "AWS_DEFAULT_REGION"
    )
    if profile:
        return boto3.Session(profile_name=profile, region_name=region_name)
    return boto3.Session(region_name=region_name)


# --- Resource verifiers -----------------------------------------------------


def verify_s3_bucket(identifier: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Inspect a single S3 bucket's encryption + public-access-block + versioning + replication state."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    s3 = session.client("s3")
    actual: dict[str, Any] = {"bucket": identifier}
    try:
        enc = s3.get_bucket_encryption(Bucket=identifier)
        rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        if rules:
            algo = (
                rules[0]
                .get("ApplyServerSideEncryptionByDefault", {})
                .get("SSEAlgorithm")
            )
            actual["encryption"] = {"algorithm": algo}
    except ClientError as exc:
        actual["encryption"] = {"error": str(exc)}
    try:
        pab = s3.get_public_access_block(Bucket=identifier)
        actual["public_access_block"] = {
            "block_public_acls": pab["PublicAccessBlockConfiguration"].get(
                "BlockPublicAcls"
            ),
            "block_public_policy": pab["PublicAccessBlockConfiguration"].get(
                "BlockPublicPolicy"
            ),
            "ignore_public_acls": pab["PublicAccessBlockConfiguration"].get(
                "IgnorePublicAcls"
            ),
            "restrict_public_buckets": pab["PublicAccessBlockConfiguration"].get(
                "RestrictPublicBuckets"
            ),
        }
    except ClientError as exc:
        actual["public_access_block"] = {"error": str(exc)}
    # Versioning state. Returns "Enabled", "Suspended", or absent (= "Disabled").
    try:
        ver = s3.get_bucket_versioning(Bucket=identifier)
        actual["versioning_status"] = ver.get("Status", "Disabled")
    except ClientError as exc:
        actual["versioning_status"] = {"error": str(exc)}
    # Cross-Region Replication. Absent = no rule configured.
    try:
        rep = s3.get_bucket_replication(Bucket=identifier)
        rules = rep.get("ReplicationConfiguration", {}).get("Rules", [])
        if rules:
            first = rules[0]
            actual["replication_rule_status"] = first.get("Status")
            dest_bucket_arn = first.get("Destination", {}).get("Bucket")
            actual["replication_destination_bucket_arn"] = dest_bucket_arn
        else:
            actual["replication_rule_status"] = "NotConfigured"
    except ClientError as exc:
        # NoSuchReplicationConfiguration is the normal "not configured" path.
        if "NoSuchReplicationConfiguration" in str(exc):
            actual["replication_rule_status"] = "NotConfigured"
        else:
            actual["replication_rule_status"] = {"error": str(exc)}
    return actual


def verify_wafv2_web_acl(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect a WAFv2 Web ACL by ARN. Caller passes ARN as identifier."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    arn = identifier
    parts = arn.split("/")
    if len(parts) < 4:
        raise ValueError(f"Invalid WAFv2 Web ACL ARN: {arn}")
    name = parts[-2]
    web_acl_id = parts[-1]
    scope = "REGIONAL" if "regional" in arn.lower() else "CLOUDFRONT"
    region = "us-east-1" if scope == "CLOUDFRONT" else None
    waf = _aws_session(region=region).client("wafv2")
    resp = waf.get_web_acl(Name=name, Scope=scope, Id=web_acl_id)
    web_acl = resp.get("WebACL", {})
    rules = web_acl.get("Rules", [])
    return {
        "arn": arn,
        "name": web_acl.get("Name"),
        "default_action": list(web_acl.get("DefaultAction", {}).keys())[0]
        if web_acl.get("DefaultAction")
        else None,
        "rule_count": len(rules),
        "rule_names": [r.get("Name") for r in rules],
        "rules": rules,
    }


def verify_route53_health_check(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect a Route 53 health check by id."""
    session = _aws_session(region="us-east-1")
    if session is None:
        raise RuntimeError("boto3 unavailable")
    r53 = session.client("route53")
    resp = r53.get_health_check_status(HealthCheckId=identifier)
    observations = resp.get("HealthCheckObservations", [])
    statuses = [
        obs.get("StatusReport", {}).get("Status", "") for obs in observations
    ]
    healthy_count = sum(1 for s in statuses if "Success" in s)
    return {
        "health_check_id": identifier,
        "observation_count": len(observations),
        "healthy_count": healthy_count,
        "status": "Healthy" if healthy_count > 0 else "Unhealthy",
        "raw_statuses": statuses,
    }


def verify_lambda_function(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect a Lambda function configuration."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    lam = session.client("lambda")
    resp = lam.get_function_configuration(FunctionName=identifier)
    concurrency: dict[str, Any] = {}
    try:
        cresp = lam.get_function_concurrency(FunctionName=identifier)
        concurrency = {
            "reserved_concurrency": cresp.get("ReservedConcurrentExecutions")
        }
    except ClientError:
        concurrency = {"reserved_concurrency": None}
    return {
        "function_name": resp.get("FunctionName"),
        "runtime": resp.get("Runtime"),
        "memory_size": resp.get("MemorySize"),
        "timeout": resp.get("Timeout"),
        "kms_key_arn": resp.get("KMSKeyArn"),
        "vpc_config": resp.get("VpcConfig"),
        "state": resp.get("State"),
        **concurrency,
    }


def verify_kms_key(identifier: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Inspect a KMS key. identifier may be a key id, alias, or ARN."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    kms = session.client("kms")
    resp = kms.describe_key(KeyId=identifier)
    metadata = resp.get("KeyMetadata", {})
    rot: dict[str, Any] = {}
    try:
        rresp = kms.get_key_rotation_status(KeyId=identifier)
        rot = {"rotation_enabled": rresp.get("KeyRotationEnabled")}
    except ClientError:
        rot = {"rotation_enabled": None}
    return {
        "key_id": metadata.get("KeyId"),
        "arn": metadata.get("Arn"),
        "key_state": metadata.get("KeyState"),
        "key_manager": metadata.get("KeyManager"),
        "key_spec": metadata.get("KeySpec"),
        "enabled": metadata.get("Enabled"),
        "multi_region": metadata.get("MultiRegion", False),
        **rot,
    }


def verify_guardduty_findings(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect GuardDuty findings count for a detector. identifier = detector id."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    gd = session.client("guardduty")
    finding_ids = []
    paginator = gd.get_paginator("list_findings")
    for page in paginator.paginate(DetectorId=identifier):
        finding_ids.extend(page.get("FindingIds", []))
    return {
        "detector_id": identifier,
        "finding_count": len(finding_ids),
        "finding_ids_sample": finding_ids[:10],
    }


def verify_rds_cluster(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect an RDS / Aurora cluster."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    rds = session.client("rds")
    resp = rds.describe_db_clusters(DBClusterIdentifier=identifier)
    clusters = resp.get("DBClusters", [])
    if not clusters:
        return {"cluster_id": identifier, "exists": False}
    cluster = clusters[0]
    return {
        "cluster_id": cluster.get("DBClusterIdentifier"),
        "status": cluster.get("Status"),
        "engine": cluster.get("Engine"),
        "engine_version": cluster.get("EngineVersion"),
        "is_global_cluster_member": bool(cluster.get("GlobalClusterIdentifier")),
        "global_cluster_id": cluster.get("GlobalClusterIdentifier"),
        "writer_count": sum(
            1 for m in cluster.get("DBClusterMembers", []) if m.get("IsClusterWriter")
        ),
        "reader_count": sum(
            1
            for m in cluster.get("DBClusterMembers", [])
            if not m.get("IsClusterWriter")
        ),
        "storage_encrypted": cluster.get("StorageEncrypted"),
        "kms_key_id": cluster.get("KmsKeyId"),
    }


def verify_budgets_budget(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect AWS Budgets configuration. identifier = budget name."""
    session = _aws_session(region="us-east-1")
    if session is None:
        raise RuntimeError("boto3 unavailable")
    sts = session.client("sts")
    account = sts.get_caller_identity()["Account"]
    bud = session.client("budgets")
    resp = bud.describe_budget(AccountId=account, BudgetName=identifier)
    b = resp.get("Budget", {})
    nresp = bud.describe_notifications_for_budget(
        AccountId=account, BudgetName=identifier
    )
    return {
        "budget_name": b.get("BudgetName"),
        "budget_type": b.get("BudgetType"),
        "limit": b.get("BudgetLimit", {}),
        "time_unit": b.get("TimeUnit"),
        "notification_count": len(nresp.get("Notifications", [])),
        "notifications": nresp.get("Notifications", []),
    }


def verify_rds_global_cluster(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect an Aurora Global Database cluster. identifier = global cluster id."""
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    rds = session.client("rds")
    resp = rds.describe_global_clusters(GlobalClusterIdentifier=identifier)
    clusters = resp.get("GlobalClusters", [])
    if not clusters:
        return {"global_cluster_id": identifier, "exists": False}
    cluster = clusters[0]
    members = cluster.get("GlobalClusterMembers", [])
    writer_member_arn = next(
        (m.get("DBClusterArn") for m in members if m.get("IsWriter")), None
    )
    return {
        "global_cluster_id": cluster.get("GlobalClusterIdentifier"),
        "engine": cluster.get("Engine"),
        "engine_version": cluster.get("EngineVersion"),
        "status": cluster.get("Status"),
        "members_count": len(members),
        "writer_count": sum(1 for m in members if m.get("IsWriter")),
        "reader_count": sum(1 for m in members if not m.get("IsWriter")),
        "writer_cluster_arn": writer_member_arn,
        "storage_encrypted": cluster.get("StorageEncrypted"),
    }


def verify_route53_record(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect a Route 53 record set.

    identifier format: "<HostedZoneId>:<RecordName>" (e.g. "Z123ABC:app.example.com").
    Returns aggregated info across all matching record sets (failover policy
    typically yields 2 records under the same name with different SetIdentifier).
    """
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    if ":" not in identifier:
        raise ValueError(
            f"route53_record identifier must be 'HostedZoneId:RecordName', got {identifier}"
        )
    zone_id, record_name = identifier.split(":", 1)
    r53 = session.client("route53")
    paginator = r53.get_paginator("list_resource_record_sets")
    matching = []
    target_name = record_name.rstrip(".") + "."
    for page in paginator.paginate(HostedZoneId=zone_id):
        for rrs in page.get("ResourceRecordSets", []):
            if rrs.get("Name") == target_name:
                matching.append(rrs)
    failover_records = [r for r in matching if r.get("Failover")]
    primary_record = next((r for r in failover_records if r.get("Failover") == "PRIMARY"), None)
    secondary_record = next((r for r in failover_records if r.get("Failover") == "SECONDARY"), None)
    return {
        "record_name": record_name,
        "hosted_zone_id": zone_id,
        "record_set_count": len(matching),
        "failover_routing_set_count": len(failover_records),
        "primary_health_check_id": primary_record.get("HealthCheckId") if primary_record else None,
        "secondary_health_check_id": secondary_record.get("HealthCheckId") if secondary_record else None,
        "primary_health_check_id_present": bool(primary_record and primary_record.get("HealthCheckId")),
        "secondary_health_check_id_present": bool(secondary_record and secondary_record.get("HealthCheckId")),
        "primary_alias_target": (primary_record or {}).get("AliasTarget", {}).get("DNSName"),
        "secondary_alias_target": (secondary_record or {}).get("AliasTarget", {}).get("DNSName"),
    }


def verify_alb_listener(
    identifier: str, expected: dict[str, Any]
) -> dict[str, Any]:
    """Inspect an Application Load Balancer listener.

    identifier = ALB ARN. Returns the ALB's state, DNS, and listener details.
    """
    session = _aws_session()
    if session is None:
        raise RuntimeError("boto3 unavailable")
    elbv2 = session.client("elbv2")
    resp = elbv2.describe_load_balancers(LoadBalancerArns=[identifier])
    albs = resp.get("LoadBalancers", [])
    if not albs:
        return {"alb_arn": identifier, "exists": False}
    alb = albs[0]
    listeners_resp = elbv2.describe_listeners(LoadBalancerArn=identifier)
    listeners = listeners_resp.get("Listeners", [])
    https_listeners = [l for l in listeners if l.get("Protocol") == "HTTPS"]
    return {
        "alb_arn": identifier,
        "alb_dns_name": alb.get("DNSName"),
        "scheme": alb.get("Scheme"),
        "state": alb.get("State", {}).get("Code"),
        "vpc_id": alb.get("VpcId"),
        "listener_count": len(listeners),
        "https_listener_count": len(https_listeners),
        "listener_protocols": sorted({l.get("Protocol") for l in listeners}),
    }


# --- Dispatcher -------------------------------------------------------------


RESOURCE_VERIFIERS: dict[str, Callable[[str, dict[str, Any]], dict[str, Any]]] = {
    "s3_bucket": verify_s3_bucket,
    "wafv2_web_acl": verify_wafv2_web_acl,
    "route53_health_check": verify_route53_health_check,
    "route53_record": verify_route53_record,
    "lambda_function": verify_lambda_function,
    "kms_key": verify_kms_key,
    "guardduty_detector": verify_guardduty_findings,
    "rds_cluster": verify_rds_cluster,
    "rds_global_cluster": verify_rds_global_cluster,
    "alb_listener": verify_alb_listener,
    "budgets_budget": verify_budgets_budget,
}


def verify_claim(claim: dict[str, Any]) -> ClaimResult:
    """Verify one aws_state_claim against live AWS state.

    Returns a ClaimResult. Never raises on AWS errors; reports them in
    ClaimResult.error so downstream gating logic can decide how to react.
    """
    claim_id = claim.get("id", "<unnamed>")
    resource_type = claim.get("resource_type", "")
    identifier = claim.get("identifier", "")
    expected = claim.get("expected", {})

    if not BOTO3_AVAILABLE:
        return ClaimResult(
            claim_id=claim_id,
            resource_type=resource_type,
            identifier=identifier,
            passed=False,
            error="boto3_unavailable",
        )

    verifier = RESOURCE_VERIFIERS.get(resource_type)
    if verifier is None:
        return ClaimResult(
            claim_id=claim_id,
            resource_type=resource_type,
            identifier=identifier,
            passed=False,
            error=f"no_verifier_for_resource_type:{resource_type}",
        )

    try:
        actual = verifier(identifier, expected)
    except (ClientError, BotoCoreError) as exc:
        return ClaimResult(
            claim_id=claim_id,
            resource_type=resource_type,
            identifier=identifier,
            passed=False,
            error=f"aws_api_error:{type(exc).__name__}:{exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return ClaimResult(
            claim_id=claim_id,
            resource_type=resource_type,
            identifier=identifier,
            passed=False,
            error=f"verifier_error:{type(exc).__name__}:{exc}",
        )

    diffs = _compare_expected(actual, expected) if expected else []
    return ClaimResult(
        claim_id=claim_id,
        resource_type=resource_type,
        identifier=identifier,
        passed=(len(diffs) == 0),
        actual=actual,
        diff=diffs,
    )


def verify_bundle(
    final_result_path: str | os.PathLike[str],
) -> tuple[bool, list[ClaimResult]]:
    """Read a final_result.json and verify every aws_state_claim listed.

    Returns (all_passed, results).
    """
    with open(final_result_path) as f:
        bundle = json.load(f)
    claims = bundle.get("aws_state_claims", []) or []
    results = [verify_claim(c) for c in claims]
    return all(r.passed for r in results), results


def write_verification_report(
    results: list[ClaimResult], out_path: str | os.PathLike[str]
) -> None:
    """Persist verification results next to the bundle."""
    payload = {
        "boto3_available": BOTO3_AVAILABLE,
        "claim_count": len(results),
        "passed_count": sum(1 for r in results if r.passed),
        "results": [r.to_dict() for r in results],
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)


__all__ = [
    "BOTO3_AVAILABLE",
    "ClaimResult",
    "RESOURCE_VERIFIERS",
    "verify_claim",
    "verify_bundle",
    "write_verification_report",
]
