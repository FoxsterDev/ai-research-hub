# 📱 Mobile SDK Research Hub

**Vetted SDK Compatibility Reports for High-Traffic Unity Games (1M+ DAU).**

In professional mobile game development, "latest" rarely means "best." This repository serves as a central knowledge base for **Principal Mobile SDK Engineers** to track stable, store-compliant, and production-ready SDK versions.

---

## 🧠 The Problem: The "Silent Killers" of Game Stability

Updating an SDK in a high-traffic environment (1M+ DAU) introduces three critical risks that standard documentation often ignores:

1. **Dependency Hell (Billing Conflicts)**: SDKs like AppsFlyer often release parallel branches for different Google Play Billing (GPB) versions. Using a **Billing v8 (Option A)** SDK in a **Unity IAP 4.13 (Billing v7)** project causes immediate `NoClassDefFoundError` crashes during the purchase flow.
2. **Native Drift**: Unity plugins often bundle older native Android/iOS SDKs. A plugin might be new, but it could contain a native core with known ANRs or memory leaks that were already fixed in other platforms like Flutter.
3. **Store Compliance Gatekeeping**: Google and Apple frequently update requirements (e.g., Target SDK 34/35 or iOS Privacy Manifests). Using a "stable" but non-compliant version leads to rejected builds or app removal.

---

## 🎯 The Solution: Stability-First Research

This repository contains **vetted reports** generated using a proprietary Research Framework (v4.2). We do not just look at version numbers; we perform:

* **Branch Resolution**: Identifying the correct "Option B" path for Unity projects on specific IAP versions.
* **Native SDK Parity**: Ensuring the Unity plugin matches the "Flutter Canary" benchmark for native stability.
* **Critical Fix Audit**: Verifying fixes for specific native crashes (e.g., iOS ICM library crashes) before recommending an update.

---

## 🔎 Latest Production-Ready Reports

| SDK | Platform | Environment | Recommended | Status | Report |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AppsFlyer** | Unity | IAP 4.12 - 4.13 | **v6.17.80** | ✅ Stable | [View Report](./reports/unity/appsflyer/AppsFlyer_UnityIAP4.13_Analysis_2026-01-12.md) |

---

## 🏛 Methodology

All reports follow a strict scoring protocol:
- **Native Fixes (+5)**: Includes critical native ANR/Crash resolutions.
- **Billing Match (+5)**: Verified compatible with specific Unity IAP/Billing versions.
- **Compliance Check (PASS)**: Verified for Android 14/15 and iOS Privacy Manifests.

---
**Disclaimer**: These reports are for informational purposes. Always perform a staged rollout (1% -> 5% -> 20%) when updating SDKs in production.