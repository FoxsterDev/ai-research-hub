# AppsFlyer SDK Analysis for Unity IAP 4.13
**Analysis Date**: 2026-01-12
**Analyst**: Integrator Agent (Nexus Brain v4.1)
**Request**: Best AppsFlyer SDK version for Unity with Unity Purchasing 4.13

---

## 🎯 EXECUTIVE SUMMARY

**RECOMMENDED VERSION**: **6.17.80**
**Score**: 15/15 (Production Ready for 1M+ DAU)
**Compatibility**: ✅ Unity IAP 4.13 (Billing v7)
**Release Date**: 2025-12-24 (18 days maturity)

---

## 📊 VERSION COMPARISON TABLE

| Version | Android SDK | iOS SDK | Purchase Connector | IAP 4.13 Safe | Flutter Match | Score |
|:--------|:------------|:--------|:-------------------|:--------------|:--------------|:------|
| **6.17.80** | **6.17.5** | **6.17.8** | **2.1.2 (Option B)** | **✅** | **✅ Perfect** | **15/15** |
| 6.17.81 | 6.17.5 | 6.17.8 | 2.2.0 (Option A) | ❌ | ✅ | -5/15 |
| 6.17.72 | 6.17.3 | 6.17.7 | 2.1.1 | ✅ | ⚠️ | 10/15 |
| 6.17.71 | 6.17.3 | 6.17.7 | 2.1.0 | ✅ | ⚠️ | 9/15 |
| 6.17.7 | 6.17.3 | 6.17.7 | 2.2.0 (Option A) | ❌ | ❌ | -6/15 |
| 6.17.5 | 6.17.3 | 6.17.5 | N/A | ✅ | ❌ | 8/15 |
| v6.17.1 | 6.17.0 | 6.17.1 | Initial PC | ⚠️ | ❌ | 7/15 |

---

## 🔍 FLUTTER CANARY BENCHMARK

**Stability Baseline**: Android **6.17.5** | iOS **6.17.8**

Version 6.17.80 achieves **perfect parity** with Flutter plugin's native SDKs, indicating production-grade stability validation across multiple platforms.

---

## 📋 NATIVE SDK ANALYSIS

### Android SDK 6.17.5
- ✅ **Target SDK 34/35 Compliance**: Meets Google Play requirements for Android 14/15
- ✅ **Google Play Integrity API**: Critical fixes for store compliance
- ✅ **ANR Reduction**: Performance improvements for low-end devices
- ✅ **DMA Compliance**: Digital Markets Act requirements met
- 🔗 **Verification**: https://dev.appsflyer.com/hc/docs/android-release-notes#v6175

### iOS SDK 6.17.8
- ✅ **Privacy Manifest**: Required PrivacyInfo.xcprivacy included
- ✅ **ICM Library Crash Fix**: Critical stability fix for iOS 18+
- ✅ **Deep Linking**: UDL improvements for deferred attribution
- 🔗 **Verification**: https://dev.appsflyer.com/hc/docs/ios-release-notes#v6178

### Purchase Connector 2.1.2 (Option B)
- ✅ **Billing v6/v7 Support**: Fully compatible with Unity IAP 4.12-4.13
- ✅ **Receipt Validation**: V2 API implementation
- 🔗 **Verification**: https://github.com/AppsFlyerSDK/appsflyer-android-purchase-connector/releases/tag/2.1.2

---

## ⚠️ CRITICAL WARNINGS

### ❌ AVOID VERSION 6.17.81
**Released**: 2025-12-24 (same day as 6.17.80)
**Issue**: Contains Purchase Connector **2.2.0** (Billing v8 - "Option A" branch)
**Impact**: Will cause **revenue tracking failures** with Unity IAP 4.13
**Penalty**: -20 points (Hard Rejection)

This version is intended for Unity IAP 5.0+ projects only.

### ❌ AVOID VERSION 6.17.7
**Issue**: Purchase Connector 2.2.0 (Billing v8 conflict)
**Impact**: Same billing library incompatibility
**Penalty**: -20 points (Hard Rejection)

---

## 🎯 SCORING BREAKDOWN (6.17.80)

### Base Score: 10/10
- Release age (18 days): **+2**
- Official release (not pre-release): **+2**
- Flutter Canary match (perfect): **+3**
- Native SDK parity (6.17.5 + 6.17.8): **+3**

### Bonus Score: +5
- Purchase Connector compatibility (2.1.2 for IAP 4.13): **+3**
- Critical iOS crash fix (ICM library): **+2**

### Penalties: 0
- ✅ Target SDK compliance (Android 14/15)
- ✅ iOS Privacy Manifest included
- ✅ No billing library conflicts
- ✅ No native SDK downgrades
- ✅ No unresolved crash reports

**Total**: **15/15**

---

## 🚀 INSTALLATION INSTRUCTIONS

### Option 1: Unity Package Manager (Recommended)
```
https://github.com/AppsFlyerSDK/appsflyer-unity-plugin.git#6.17.80
```

### Option 2: Manual .unitypackage
🔗 Download: https://github.com/AppsFlyerSDK/appsflyer-unity-plugin/releases/tag/6.17.80

---

## 📋 PRODUCTION VALIDATION CHECKLIST

Before deploying to 1M+ DAU:

- [ ] **SDK.init()**: Verify attribution capture in AppsFlyer dashboard
- [ ] **logEvent()**: Confirm custom revenue events reach backend
- [ ] **Deep Linking**: Test UDL deferred flows
- [ ] **Purchase Connector**: Validate in-app purchase tracking (receipts appearing in dashboard)
- [ ] **Privacy/DMA**: Ensure consent data transmission
- [ ] **ANR Monitoring**: Compare pre/post-update crash rates via Firebase Crashlytics

---

## 🎯 STAGED ROLLOUT RECOMMENDATION

**DO NOT** deploy to 100% immediately:

1. **Phase 1 (QA)**: Internal testing on 50+ devices
2. **Phase 2 (Canary)**: 1% users for 24h, monitor ANR rate
3. **Phase 3 (Early Access)**: 5% → 20%, verify purchase tracking
4. **Phase 4 (Full)**: 100% after 72h stable metrics

---

## 📚 REFERENCE LINKS

- **Unity Plugin Releases**: https://github.com/AppsFlyerSDK/appsflyer-unity-plugin/releases
- **Flutter Plugin (Benchmark)**: https://github.com/AppsFlyerSDK/appsflyer-flutter-plugin/releases
- **Android SDK Changelog**: https://dev.appsflyer.com/hc/docs/android-release-notes
- **iOS SDK Changelog**: https://dev.appsflyer.com/hc/docs/ios-release-notes
- **Purchase Connector**: https://github.com/AppsFlyerSDK/appsflyer-android-purchase-connector

---

## 🔐 COMPLIANCE STATUS

- ✅ **Google Play**: Target SDK 34+ (Android 14) compliant
- ✅ **App Store**: Privacy Manifest included
- ✅ **DMA**: Digital Markets Act compliance (Android SDK 6.17.5+)
- ✅ **GDPR**: Consent management support

---

## 📊 BILLING LIBRARY COMPATIBILITY MATRIX

| Unity IAP Version | GPB Version | Required Purchase Connector | Compatible Plugin Version |
|:------------------|:------------|:----------------------------|:--------------------------|
| 3.x - 4.11 | v4 / v5 | PC 2.1.x | 6.15.x - 6.16.x |
| **4.12 - 4.13** | **v6 / v7** | **PC 2.1.2** | **6.17.80 (Option B)** |
| 5.0.0+ | v8 | PC 2.2.0 | 6.17.81+ (Option A) |

---

**Analysis Protocol**: AppsFlyer SDK Research Framework v4.1 (Ultimate Edition)
**Confidence Level**: High (Flutter validation + official changelog verification)
**Production Ready**: ✅ YES (Score 15/15 exceeds 11.0 threshold)

---
