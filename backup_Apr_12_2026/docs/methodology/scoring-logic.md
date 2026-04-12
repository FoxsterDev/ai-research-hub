# Research Methodology: SDK Stability Scoring (v4.2)

To ensure production readiness for high-traffic mobile games (1M+ DAU), every SDK version undergoes a rigorous multi-stage audit. This scoring logic prioritizes stability and store compliance over "latest-version" trends.

---

## ⚖️ The Scoring System (Total: 15 Points)

We apply a weighted scoring model to every candidate version. A version must score **>= 11.0** to be recommended for a full production rollout.

### 1. Base Stability (0-10 Points)
* **Flutter Canary Benchmark (+3)**: Points awarded if BOTH Android and iOS native versions match the latest `appsflyer-flutter-plugin` exactly. Flutter is used as the stability "canary" due to its rigorous update cycle.
* **Release Age (+3)**: >3 months (+3), 1-3 months (+2), <1 month (+1). This ensures the version has survived early-adopter bug reports.
* **Official Status (+3)**: Only full, non-beta/pre-release versions are eligible for maximum points.
* **Stability Fixes (+1)**: Explicit mentions of stability or logic fixes in the plugin release notes.

### 2. Technical Fix Bonuses (0-5 Points)
* **Native SDK Upgrade (+5)**: Awarded if the plugin upgrades to a native SDK version that fixes critical ANRs, memory leaks, or crashes (e.g., the iOS ICM library crash fix).
* **Compliance/Security (+1)**: Awarded for DMA compliance or updated security modules.

---

## 🚫 Hard Rejection & Penalty Criteria

A version is automatically disqualified or heavily penalized if it triggers any of the following deal-breakers:

| Violation | Penalty | Impact |
| :--- | :--- | :--- |
| **Billing/IAP Mismatch** | **-20 pts** | Causes `NoClassDefFoundError` in Unity IAP projects. |
| **Unresolved Crashes** | **-15 pts** | >3 confirmed reports of crashes/ANRs in the candidate version. |
| **Target SDK Incompatibility** | **-15 pts** | Non-compliance with Android 14/15 (Target SDK 34+) requirements. |
| **Missing Privacy Manifest** | **-10 pts** | Missing mandatory `PrivacyInfo.xcprivacy` for iOS. |
| **Native SDK Downgrade** | **-5 pts** | Newer plugin version containing older native SDKs than previous releases. |

---

## 🛠 Branch Resolution: Option A vs. Option B

A critical part of our methodology is **Branch Discovery**. AppsFlyer often releases two versions of the same tag to support different Google Play Billing (GPB) environments:

* **Option A (The "Newer" Branch)**: Bundles Purchase Connector v2.2.0. Requires **GPB v8** (Unity IAP 5.0.0+).
* **Option B (The "Stable" Branch)**: Bundles Purchase Connector v2.1.2. Compatible with **GPB v7** (Unity IAP 4.12/4.13).

**Using the wrong branch is the #1 cause of IAP-related build failures and runtime crashes in Unity.**.

---
*Note: This scoring logic is reviewed monthly to align with the latest store policies and Flutter Canary benchmarks.*.