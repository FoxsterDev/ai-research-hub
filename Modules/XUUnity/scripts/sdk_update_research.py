#!/usr/bin/env python3
import argparse
import datetime as dt
import io
import json
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


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
    },
    "applovin": {
        "display_name": "AppLovin MAX",
        "github_owner": "AppLovin",
        "repos": {
            "unity": "AppLovin-MAX-Unity-Plugin",
            "flutter": "AppLovin-MAX-Flutter",
            "android": "AppLovin-MAX-SDK-Android",
            "ios": "AppLovin-MAX-SDK-iOS",
        },
        "unity_registry": "https://unity.packages.applovin.com/",
        "core_package": "com.applovin.mediation.ads",
        "components": {
            "pangle": {
                "display_name": "Pangle",
                "aliases": ["bytedance", "csj"],
                "android_package": "com.applovin.mediation.adapters.bytedance.android",
                "ios_package": "com.applovin.mediation.adapters.bytedance.ios",
                "android_maven_artifact": "bytedance-adapter",
                "ios_pod": "AppLovinMediationByteDanceAdapter",
                "android_changelog": "https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/ByteDance/CHANGELOG.md",
                "ios_changelog": "https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/ByteDance/CHANGELOG.md",
            },
            "google": {
                "display_name": "Google AdMob",
                "aliases": ["admob", "google-admob"],
                "android_package": "com.applovin.mediation.adapters.google.android",
                "ios_package": "com.applovin.mediation.adapters.google.ios",
                "android_maven_artifact": "google-adapter",
                "ios_pod": "AppLovinMediationGoogleAdapter",
                "android_changelog": "https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Google/CHANGELOG.md",
                "ios_changelog": "https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Google/CHANGELOG.md",
            },
            "unityads": {
                "display_name": "Unity Ads",
                "aliases": ["unity", "unity-ads"],
                "android_package": "com.applovin.mediation.adapters.unityads.android",
                "ios_package": "com.applovin.mediation.adapters.unityads.ios",
                "android_maven_artifact": "unityads-adapter",
                "ios_pod": "AppLovinMediationUnityAdsAdapter",
            },
            "facebook": {
                "display_name": "Meta Audience Network",
                "aliases": ["meta", "fan"],
                "android_package": "com.applovin.mediation.adapters.facebook.android",
                "ios_package": "com.applovin.mediation.adapters.facebook.ios",
                "android_maven_artifact": "facebook-adapter",
                "ios_pod": "AppLovinMediationFacebookAdapter",
            },
            "ironsource": {
                "display_name": "ironSource",
                "aliases": ["iron-source"],
                "android_package": "com.applovin.mediation.adapters.ironsource.android",
                "ios_package": "com.applovin.mediation.adapters.ironsource.ios",
                "android_maven_artifact": "ironsource-adapter",
                "ios_pod": "AppLovinMediationIronSourceAdapter",
            },
            "vungle": {
                "display_name": "Liftoff Monetize",
                "aliases": ["liftoff", "liftoff-monetize"],
                "android_package": "com.applovin.mediation.adapters.vungle.android",
                "ios_package": "com.applovin.mediation.adapters.vungle.ios",
                "android_maven_artifact": "vungle-adapter",
                "ios_pod": "AppLovinMediationVungleAdapter",
            },
        },
        "known_links": {
            "unity_integration": "https://support.axon.ai/en/max/unity/overview/integration",
            "mediated_networks": "https://support.axon.ai/en/max/unity/preparing-mediated-networks",
            "mediation_debugger": "https://developers.applovin.com/en/max/unity/testing-networks/mediation-debugger/",
            "unity_releases": "https://github.com/AppLovin/AppLovin-MAX-Unity-Plugin/releases",
            "android_sdk_releases": "https://github.com/AppLovin/AppLovin-MAX-SDK-Android/releases",
            "ios_sdk_releases": "https://github.com/AppLovin/AppLovin-MAX-SDK-iOS/releases",
        },
    },
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect SDK update candidate evidence for XUUnity SDK research reports."
    )
    parser.add_argument("--vendor", required=True, help="Vendor id, for example appsflyer.")
    parser.add_argument("--platform", default="unity", help="SDK wrapper platform. Default: unity.")
    parser.add_argument("--component", default="", help="Optional vendor component, for example pangle.")
    parser.add_argument("--target-version", default="", help="Optional requested target version or lower bound.")
    parser.add_argument(
        "--target-platform",
        choices=["android", "ios", "both"],
        default="both",
        help="Platform focus for component research. Default: both.",
    )
    parser.add_argument("--limit", type=int, default=7, help="Number of releases to inspect. Default: 7.")
    parser.add_argument("--unity-iap-version", default="", help="Current Unity IAP version when relevant.")
    parser.add_argument("--current-version", default="", help="Current wrapper version, if known.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds. Default: 20.")
    return parser.parse_args()


def request_url(url, timeout, accept="application/json"):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "xuunity-sdk-update-research",
        },
    )
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_json(url, timeout, accept="application/json"):
    with request_url(url, timeout, accept) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url, timeout):
    with request_url(url, timeout, "text/plain, */*") as response:
        return response.read().decode("utf-8")


def fetch_bytes(url, timeout):
    with request_url(url, timeout, "application/octet-stream, */*") as response:
        return response.read()


def safe_call(fn, *args):
    try:
        return {"ok": True, "value": fn(*args)}
    except (urllib.error.URLError, json.JSONDecodeError, ET.ParseError, tarfile.TarError, KeyError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


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


def first_changelog_sections(text, count=8):
    if not text:
        return []

    sections = []
    current = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = [line]
            if len(sections) >= count:
                break
        elif line.startswith("## "):
            current = [line]
        elif current:
            current.append(line)

    if current and len(sections) < count:
        sections.append("\n".join(current).strip())

    return sections


def parse_dependency_xml(xml_text):
    result = {
        "android_packages": [],
        "ios_pods": [],
    }

    root = ET.fromstring(xml_text)
    for node in root.findall(".//androidPackage"):
        result["android_packages"].append({
            "spec": node.attrib.get("spec", ""),
            "repositories": [
                repo.text.strip()
                for repo in node.findall(".//repository")
                if repo.text and repo.text.strip()
            ],
        })

    for node in root.findall(".//iosPod"):
        result["ios_pods"].append({
            "name": node.attrib.get("name", ""),
            "version": node.attrib.get("version", ""),
        })

    return result


def inspect_unity_package_tarball(package_version, timeout):
    tarball_url = ((package_version.get("dist") or {}).get("tarball") or "")
    if not tarball_url:
        return {}

    raw = fetch_bytes(tarball_url, timeout)
    output = {
        "tarball": tarball_url,
        "package_json": {},
        "dependency_xml": {},
        "changelog_excerpt": [],
    }

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = {member.name: member for member in archive.getmembers() if member.isfile()}

        package_member = members.get("package/package.json")
        if package_member:
            package_file = archive.extractfile(package_member)
            if package_file:
                output["package_json"] = json.loads(package_file.read().decode("utf-8"))

        deps_member = members.get("package/Editor/Dependencies.xml")
        if deps_member:
            deps_file = archive.extractfile(deps_member)
            if deps_file:
                output["dependency_xml"] = parse_dependency_xml(deps_file.read().decode("utf-8"))

        changelog_member = members.get("package/CHANGELOG.md")
        if changelog_member:
            changelog_file = archive.extractfile(changelog_member)
            if changelog_file:
                output["changelog_excerpt"] = first_changelog_sections(
                    changelog_file.read().decode("utf-8"),
                    count=5,
                )

    return output


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


def collect_unity_registry_package(registry, package_name, timeout):
    url = registry + urllib.parse.quote(package_name, safe="")
    data = fetch_json(url, timeout)
    versions = list((data.get("versions") or {}).keys())
    latest = (data.get("dist-tags") or {}).get("latest") or (versions[-1] if versions else "")
    latest_data = (data.get("versions") or {}).get(latest, {})
    return {
        "source": url,
        "name": package_name,
        "dist_tags": data.get("dist-tags") or {},
        "latest": latest,
        "versions_tail": versions[-12:],
        "latest_metadata": {
            "display_name": latest_data.get("displayName", ""),
            "description": latest_data.get("description", ""),
            "unity": latest_data.get("unity", ""),
            "dependencies": latest_data.get("dependencies") or {},
            "documentation_url": latest_data.get("documentationUrl", ""),
            "changelog_url": latest_data.get("changelogUrl", ""),
        },
        "latest_tarball": inspect_unity_package_tarball(latest_data, timeout) if latest_data else {},
    }


def collect_maven_metadata(artifact, timeout):
    metadata_url = f"https://repo1.maven.org/maven2/com/applovin/mediation/{artifact}/maven-metadata.xml"
    text = fetch_text(metadata_url, timeout)
    root = ET.fromstring(text)
    latest = root.findtext("./versioning/latest") or ""
    release = root.findtext("./versioning/release") or ""
    versions = [node.text for node in root.findall("./versioning/versions/version") if node.text]
    pom = {}

    if release:
        pom_url = (
            f"https://repo1.maven.org/maven2/com/applovin/mediation/{artifact}/"
            f"{release}/{artifact}-{release}.pom"
        )
        pom_text = fetch_text(pom_url, timeout)
        pom_root = ET.fromstring(pom_text)
        dependencies = []
        for node in pom_root.findall(".//{*}dependency"):
            dependencies.append({
                "group_id": node.findtext("{*}groupId") or "",
                "artifact_id": node.findtext("{*}artifactId") or "",
                "version": node.findtext("{*}version") or "",
            })
        pom = {
            "source": pom_url,
            "dependencies": dependencies,
        }

    return {
        "source": metadata_url,
        "latest": latest,
        "release": release,
        "versions_tail": versions[-12:],
        "pom": pom,
    }


def collect_cocoapods_latest(pod_name, timeout):
    url = "https://trunk.cocoapods.org/api/v1/pods/" + urllib.parse.quote(pod_name) + "/specs/latest"
    data = fetch_json(url, timeout)
    return {
        "source": url,
        "version": data.get("version", ""),
        "platforms": data.get("platforms") or {},
        "source_spec": data.get("source") or {},
        "dependencies": data.get("dependencies") or {},
    }


def resolve_applovin_component(profile, component_name):
    if not component_name:
        return None, None

    normalized = component_name.strip().lower().replace(" ", "").replace("-", "")
    for key, component in profile["components"].items():
        candidates = [key] + component.get("aliases", [])
        normalized_candidates = [
            value.strip().lower().replace(" ", "").replace("-", "")
            for value in candidates
        ]
        if normalized in normalized_candidates:
            return key, component

    return None, None


def collect_applovin_releases(profile, limit, timeout):
    releases_url = GITHUB_API.format(
        owner=profile["github_owner"],
        repo=profile["repos"]["unity"],
        limit=limit,
    )
    releases = fetch_json(releases_url, timeout, accept="application/vnd.github+json")
    candidates = []
    for release in releases:
        body = release.get("body") or ""
        candidates.append({
            "tag_name": release.get("tag_name", ""),
            "published_at": release.get("published_at", ""),
            "age_days": release_age_days(release.get("published_at", "")),
            "prerelease": bool(release.get("prerelease", False)),
            "html_url": release.get("html_url", ""),
            "android_sdk": first_match([r"Android SDK \[?v?([0-9]+(?:\.[0-9]+)+)"], body),
            "ios_sdk": first_match([r"iOS SDK \[?v?([0-9]+(?:\.[0-9]+)+)"], body),
            "body_excerpt": body[:700],
        })

    return {
        "source": releases_url,
        "candidates": candidates,
    }


def collect_applovin_component(profile, component_key, component, target_platform, timeout):
    registry = profile["unity_registry"]
    output = {
        "key": component_key,
        "display_name": component["display_name"],
        "target_platform": target_platform,
        "android": {},
        "ios": {},
        "changelogs": {},
    }

    if target_platform in ("android", "both"):
        output["android"]["unity_package"] = safe_call(
            collect_unity_registry_package,
            registry,
            component["android_package"],
            timeout,
        )
        output["android"]["maven"] = safe_call(
            collect_maven_metadata,
            component["android_maven_artifact"],
            timeout,
        )

    if target_platform in ("ios", "both"):
        output["ios"]["unity_package"] = safe_call(
            collect_unity_registry_package,
            registry,
            component["ios_package"],
            timeout,
        )
        output["ios"]["cocoapods"] = safe_call(
            collect_cocoapods_latest,
            component["ios_pod"],
            timeout,
        )

    if component.get("android_changelog") and target_platform in ("android", "both"):
        result = safe_call(fetch_text, component["android_changelog"], timeout)
        output["changelogs"]["android"] = {
            "source": component["android_changelog"],
            "ok": result["ok"],
            "sections": first_changelog_sections(result["value"], count=10) if result["ok"] else [],
            "error": result.get("error", ""),
        }

    if component.get("ios_changelog") and target_platform in ("ios", "both"):
        result = safe_call(fetch_text, component["ios_changelog"], timeout)
        output["changelogs"]["ios"] = {
            "source": component["ios_changelog"],
            "ok": result["ok"],
            "sections": first_changelog_sections(result["value"], count=10) if result["ok"] else [],
            "error": result.get("error", ""),
        }

    return output


def collect_applovin(profile, args):
    registry = profile["unity_registry"]
    component_key, component = resolve_applovin_component(profile, args.component)
    output = {
        "vendor": profile["display_name"],
        "component": args.component,
        "resolved_component": component_key or "",
        "target_version": args.target_version,
        "target_platform": args.target_platform,
        "current_version": args.current_version,
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": {
            "unity_registry": registry,
            **profile.get("known_links", {}),
        },
        "core": {
            "unity_package": safe_call(collect_unity_registry_package, registry, profile["core_package"], args.timeout),
            "github_releases": safe_call(collect_applovin_releases, profile, args.limit, args.timeout),
        },
        "component_evidence": {},
        "known_components": {
            key: {
                "display_name": value["display_name"],
                "android_package": value["android_package"],
                "ios_package": value["ios_package"],
            }
            for key, value in profile["components"].items()
        },
        "notes": [
            "This script collects AppLovin evidence only. The protocol must make the final recommendation.",
            "Compare Unity scoped registry, package tarball Dependencies.xml, Maven, CocoaPods, and changelog evidence before approval.",
            "Android and iOS adapter candidates must be scored separately when their evidence differs.",
        ],
    }

    if args.component and not component:
        output["component_evidence"] = {
            "ok": False,
            "error": f"Unknown AppLovin component '{args.component}'.",
        }
    elif component:
        output["component_evidence"] = {
            "ok": True,
            "value": collect_applovin_component(
                profile,
                component_key,
                component,
                args.target_platform,
                args.timeout,
            ),
        }

    return output


def main():
    args = parse_args()
    vendor = args.vendor.strip().lower()
    profile = VENDOR_PROFILES.get(vendor)
    if not profile:
        known = ", ".join(sorted(VENDOR_PROFILES))
        print(f"Unsupported vendor '{args.vendor}'. Known vendors: {known}", file=sys.stderr)
        return 2

    if vendor == "applovin":
        try:
            output = collect_applovin(profile, args)
        except urllib.error.URLError as exc:
            print(f"Failed to fetch AppLovin evidence: {exc}", file=sys.stderr)
            return 1

        print(json.dumps(output, indent=2, sort_keys=True))
        return 0

    repos = profile["repos"]
    repo = repos.get(args.platform)
    if not repo:
        platforms = ", ".join(sorted(repos))
        print(f"Unsupported platform '{args.platform}' for {vendor}. Known platforms: {platforms}", file=sys.stderr)
        return 2

    owner = profile["github_owner"]
    releases_url = GITHUB_API.format(owner=owner, repo=repo, limit=args.limit)

    try:
        releases = fetch_json(releases_url, args.timeout, accept="application/vnd.github+json")
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
