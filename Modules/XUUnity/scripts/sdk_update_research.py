#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


GITHUB_API = "https://api.github.com/repos/{owner}/{repo}/releases?per_page={limit}"


VENDOR_PROFILES = {
    "appsflyer": {
        "display_name": "AppsFlyer",
        "github_owner": "AppsFlyerSDK",
        "repos": {
            "unity": "appsflyer-unity-plugin",
            "flutter": "appsflyer-flutter-plugin",
        },
        "patterns": {
            "android_sdk": [
                r"Android SDK version\s*(?:-|:)?\s*v?([0-9]+(?:\.[0-9]+)+)",
                r"Android SDK\s*(?:-|:)?\s*v?([0-9]+(?:\.[0-9]+)+)",
            ],
            "ios_sdk": [
                r"iOS SDK version\s*(?:-|:)?\s*v?([0-9]+(?:\.[0-9]+)+)",
                r"iOS SDK\s*(?:-|:)?\s*v?([0-9]+(?:\.[0-9]+)+)",
            ],
            "purchase_connector": [
                r"Android Purchase Connector version\s*(?:-|:)?\s*v?([0-9]+(?:\.[0-9]+)+)",
                r"Android Purchase Connector.*?v?([0-9]+(?:\.[0-9]+)+)",
            ],
            "billing_library": [
                r"v{tag}\s*[-\u2013\u2014]\s*Billing Library\s*([0-9]+)",
                r"Billing Library\s*([0-9]+)\s*\(billing:([0-9]+(?:\.[0-9]+)+)\)",
                r"billing:([0-9]+(?:\.[0-9]+)+)",
            ],
            "min_sdk": [
                r"minSdkVersion\s+([0-9]+)",
                r"min SDK\s+([0-9]+)",
            ],
        },
        "known_links": {
            "android_changelog": "https://dev.appsflyer.com/hc/docs/android-release-notes",
            "ios_changelog": "https://dev.appsflyer.com/hc/docs/ios-release-notes",
            "purchase_connector": "https://github.com/AppsFlyerSDK/appsflyer-android-purchase-connector",
        },
    }
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect SDK update candidate evidence for XUUnity SDK research reports."
    )
    parser.add_argument("--vendor", required=True, help="Vendor id, for example appsflyer.")
    parser.add_argument("--platform", default="unity", help="SDK wrapper platform. Default: unity.")
    parser.add_argument("--limit", type=int, default=7, help="Number of releases to inspect. Default: 7.")
    parser.add_argument("--unity-iap-version", default="", help="Current Unity IAP version when relevant.")
    parser.add_argument("--current-version", default="", help="Current wrapper version, if known.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds. Default: 20.")
    return parser.parse_args()


def fetch_json(url, timeout):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "xuunity-sdk-update-research",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def first_match(patterns, text, **format_args):
    if not text:
        return ""

    for pattern in patterns:
        if format_args:
            pattern = pattern.format(**format_args)
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)

    return ""


def version_tuple(version):
    if not version:
        return ()

    return tuple(int(part) for part in re.findall(r"\d+", version))


def compare_versions(left, right):
    left_parts = version_tuple(left)
    right_parts = version_tuple(right)
    length = max(len(left_parts), len(right_parts))
    left_parts = left_parts + (0,) * (length - len(left_parts))
    right_parts = right_parts + (0,) * (length - len(right_parts))
    return (left_parts > right_parts) - (left_parts < right_parts)


def release_age_days(published_at):
    if not published_at:
        return None

    try:
        published = dt.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return None

    now = dt.datetime.now(dt.timezone.utc)
    return (now - published).days


def classify_appsflyer_branch(purchase_connector, billing_library):
    if billing_library:
        billing_major = version_tuple(billing_library)[0] if version_tuple(billing_library) else 0
        if billing_major >= 8:
            return "Option A / Billing v8"
        if billing_major == 7:
            return "Option B / Billing v7"

    if purchase_connector == "2.2.0":
        return "Option A / Billing v8"
    if purchase_connector == "2.1.2":
        return "Option B / Billing v6-v7"
    if purchase_connector:
        return "Unknown connector track"
    return "Unknown"


def appsflyer_iap_gate(unity_iap_version, purchase_connector, billing_library):
    if not unity_iap_version or (not purchase_connector and not billing_library):
        return {
            "status": "unknown",
            "reason": "Unity IAP version, Purchase Connector version, or Billing Library track is missing.",
        }

    billing_major = version_tuple(billing_library)[0] if version_tuple(billing_library) else 0

    if compare_versions(unity_iap_version, "5.0.0") < 0 and (
        purchase_connector == "2.2.0" or billing_major >= 8
    ):
        return {
            "status": "hard_reject",
            "reason": "Unity IAP below 5.0.0 is incompatible with Billing v8 or Purchase Connector 2.2.0.",
        }

    if compare_versions(unity_iap_version, "5.0.0") >= 0 and (
        purchase_connector == "2.1.2" or billing_major == 7
    ):
        return {
            "status": "mismatch",
            "reason": "Unity IAP 5.0.0+ should be checked against the Billing v8 connector track.",
        }

    return {
        "status": "pass",
        "reason": "No known AppsFlyer Purchase Connector mismatch detected.",
    }


def extract_candidate(vendor, release, profile, unity_iap_version):
    body = release.get("body") or ""
    patterns = profile["patterns"]
    tag_name = release.get("tag_name", "")

    android_sdk = first_match(patterns["android_sdk"], body)
    ios_sdk = first_match(patterns["ios_sdk"], body)
    purchase_connector = first_match(patterns.get("purchase_connector", []), body)
    billing_library = first_match(patterns.get("billing_library", []), body, tag=re.escape(tag_name))
    min_sdk = first_match(patterns.get("min_sdk", []), body)
    branch = ""
    compatibility_gate = {"status": "unknown", "reason": "No vendor-specific gate applied."}

    if vendor == "appsflyer":
        branch = classify_appsflyer_branch(purchase_connector, billing_library)
        compatibility_gate = appsflyer_iap_gate(unity_iap_version, purchase_connector, billing_library)

    return {
        "tag_name": tag_name,
        "name": release.get("name", ""),
        "published_at": release.get("published_at", ""),
        "age_days": release_age_days(release.get("published_at", "")),
        "prerelease": bool(release.get("prerelease", False)),
        "html_url": release.get("html_url", ""),
        "android_sdk": android_sdk,
        "ios_sdk": ios_sdk,
        "purchase_connector": purchase_connector,
        "billing_library": billing_library,
        "branch": branch,
        "min_sdk": min_sdk,
        "compatibility_gate": compatibility_gate,
        "manual_verification_required": any(
            not value for value in [android_sdk, ios_sdk]
        ),
    }


def collect_appsflyer_canary(profile, timeout):
    owner = profile["github_owner"]
    repo = profile["repos"]["flutter"]
    url = GITHUB_API.format(owner=owner, repo=repo, limit=1)
    releases = fetch_json(url, timeout)
    if not releases:
        return {}

    body = releases[0].get("body") or ""
    patterns = profile["patterns"]
    return {
        "tag_name": releases[0].get("tag_name", ""),
        "published_at": releases[0].get("published_at", ""),
        "android_sdk": first_match(patterns["android_sdk"], body),
        "ios_sdk": first_match(patterns["ios_sdk"], body),
        "html_url": releases[0].get("html_url", ""),
    }


def main():
    args = parse_args()
    vendor = args.vendor.strip().lower()
    profile = VENDOR_PROFILES.get(vendor)
    if not profile:
        known = ", ".join(sorted(VENDOR_PROFILES))
        print(f"Unsupported vendor '{args.vendor}'. Known vendors: {known}", file=sys.stderr)
        return 2

    repos = profile["repos"]
    repo = repos.get(args.platform)
    if not repo:
        platforms = ", ".join(sorted(repos))
        print(f"Unsupported platform '{args.platform}' for {vendor}. Known platforms: {platforms}", file=sys.stderr)
        return 2

    owner = profile["github_owner"]
    releases_url = GITHUB_API.format(owner=owner, repo=repo, limit=args.limit)

    try:
        releases = fetch_json(releases_url, args.timeout)
        canary = collect_appsflyer_canary(profile, args.timeout) if vendor == "appsflyer" else {}
    except urllib.error.URLError as exc:
        print(f"Failed to fetch release data: {exc}", file=sys.stderr)
        return 1

    candidates = [
        extract_candidate(vendor, release, profile, args.unity_iap_version)
        for release in releases
    ]

    if vendor == "appsflyer" and canary:
        for candidate in candidates:
            candidate["flutter_canary_match"] = (
                bool(candidate["android_sdk"])
                and bool(candidate["ios_sdk"])
                and candidate["android_sdk"] == canary.get("android_sdk")
                and candidate["ios_sdk"] == canary.get("ios_sdk")
            )

    output = {
        "vendor": profile["display_name"],
        "platform": args.platform,
        "current_version": args.current_version,
        "unity_iap_version": args.unity_iap_version,
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": {
            "releases": releases_url,
            **profile.get("known_links", {}),
        },
        "canary": canary,
        "candidates": candidates,
        "notes": [
            "This script collects evidence only. XUUnity task/sdk_update_research.md makes the final recommendation.",
            "Unknown fields require manual verification from primary vendor sources before approving an update.",
        ],
    }

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
