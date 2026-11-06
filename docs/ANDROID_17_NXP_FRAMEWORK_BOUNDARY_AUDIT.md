# Android 17 PixelExperience-Reborn — row 167: legacy NXP NFC Java framework boundary

**Audited:** 2026-11-07. **Target platform:** independent AOSP Android 17.
**Target device later:** POCO F5 Pro / Redmi K60 (`mondrian`, SM8475).
**Status:** historical-source, interface and security-boundary audit only; NOT an Android17 Java/Soong build or a device test.

## Decision

**Do not activate historical `vendor/nxp/opensource/commonsys/frameworks` in the Android17 manifest, nor silently ship its `com.nxp.nfc.nq` API and vendor SEMS JARs.** This old NXP Android 13-era framework is not the NFC HAL, is not a standalone vendor service implementation, and is not evidence that a generic framework extension is needed by mondrian. Preserve the independent AOSP17 NFC Mainline and Secure Element/OMAPI owners and review any genuinely needed NXP-specific function separately with concrete consumers.

**Independent-source policy:** LF52406 LineageOS-derived trees are *optional read-only, last-resort references* for a specific device issue; they are never the implementation foundation or automatic source of config for the PE-Reborn ROM. Do not infer NXP extension or eSE applet availability from these trees alone.

## Verified historical sources

- PixelExperience-Reborn `vendor_nxp_opensource_commonsys_frameworks` `seventeen`: commit **`b56688d998a0d9aa4248890f13db00dd2a1ffdb2`**, Git tree **`73dd1ca79986452c7da4ced77866ae47eb7b18c6`**, last commit 2022-03-22.
- Root `Android.bp` defines `java_library { name: "com.nxp.nfc.nq", installable: true, system_ext_specific: true }` and requires `com.nxp.nfc.nq.xml`. The API includes `INxpNfcAdapter.aidl`, `INxpNfcAdapterExtras.aidl`, `INxpWlcAdapter.aidl`, `INxpWlcCallBack.aidl`, `NxpNfcAdapter.java`, `NxpWlcAdapter.java` and constants.
- The `com.nxp.nfc.nq.xml` `<library>` registration advertises `/system/system_ext/framework/com.nxp.nfc.nq.jar`. Other XMLs advertise `/system/framework/com.nxp.nfc.jar`, `/vendor/framework/com.nxp.ls.jar` and `/vendor/framework/com.nxp.sems.jar`. Presence of these XMLs **does not prove all four libraries are built or installed**; only `com.nxp.nfc.nq` is declared by the inspected root `Android.bp`.
- `NxpNfcAdapter.java` accesses `ServiceManager.getService("nfc")` and `INfcAdapter.getNfcAdapterVendorInterface("nxp")`; `NxpWlcAdapter.java` calls the `"wlc"` variant. These Binder extension methods require a matching NFC Service provider and framework/API compatibility; **the NXP framework repository does not implement that service**.
- `INxpNfcAdapter.aidl` contains privileged-impact functions: `DefaultRouteSet`, `selectUicc`, `setConfig`, `activateSeInterface`, `doWriteT4tData`, NFC polling controls, field detection/RSSI and self-test. The existence of `@RequiresPermission(NFC)` annotations in Java is **not sufficient evidence** that a matching service performs secure caller authorization.
- `NxpWlcAdapter` references NXP NFC wireless charging. **Do not advertise phone wireless charging support** based on a Java API name: neither the controller capability, antenna/power circuitry nor the actual firmware/application contract has been demonstrated.
- `sems/` includes Java SEMS/APDU routines and checked-in `sems.jar` / `com.nxp.ls.jar` binaries. Neither binary's provenance or compatibility with AOSP17 was independently verified. `SemsAgent.java` compares SHA algorithm strings with Java reference `!=`, a potential correctness bug that would need fixing if legitimately used; it is not evidence of an exploitable vulnerability.
- The historical README lists NXP releases **13.02.01 / 13.03.00**. Do not confuse these old API classes with contemporary vendor releases or a supported modern Android17 Java SDK.

## AOSP17 owners and alternatives

| AOSP17 subsystem | Official upstream ref | Role / decision |
| --- | --- | --- |
| NFC Mainline framework and service | `platform/packages/modules/Nfc`, `android-17.0.0_r1`, commit `940212c440f57032a19cf0f90c7faa8eca48d546`, tree `da01c841e3238648d0ae33c3392c05f1552e63d5` | **RETAIN**. Modern `framework/`, `NfcNci/`, `libnfc-nci/`, AIDL-based NFC interfaces, OEM extension points, APEX packaging. Compare actual API and permission checks; do not graft a hidden legacy `INfcAdapter` binder into the modular service. |
| Secure Element OMAPI service | `platform/system/secure_element`, `android-17.0.0_r1`, commit `a9644a6b928ca9c7fce4b1939e04c9b74c5533bb`, tree `50324e595c97f9d7673d62a332656e161378bbdc` | **RETAIN**. Official native `omapi/` provides an Android SE service architecture, with SE access control. Not a replacement for a vendor-specific SEMS applet or proprietary vendor software if independently proven necessary. |
| Android framework OMAPI / Java APIs | Official `frameworks/base` Android17 tag, mainline NFC framework and system SE service | **RETAIN**. Consumers should prefer permission-checked supported APIs where they meet requirements; direct access to custom NXP Binder should not be introduced for arbitrary applications. |
| NXP newer vendor NFC source | Exact release must be pinned and scoped to an identified controller/feature | **OPTIONAL FUTURE REVIEW**, not an automatic source import. Modern vendor release may contain NFC HAL-side improvements without requiring 2022 Java framework packages. |
| LF52406 LineageOS-derived device trees | Different ROM base, no selected input in PE-Reborn manifest | **EXCEPTIONAL REFERENCE ONLY**, not proof of the Java API, system_ext library install, eSE provisioning or wireless charging support. |

Official upstream links:
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1
- https://android.googlesource.com/platform/system/secure_element/+/refs/tags/android-17.0.0_r1
- https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1

## Security and integration boundaries

1. **NFC privileged Binder:** identify an actual authorized consumer and working service method for every requested extension. Review permission enforcement **on the service side**, platform signature UID/privileged permissions, AppOps, caller identity, package verification, user boundaries and Binder death/recovery.
2. **NFC routing and SE operations:** `selectUicc`, AID routing, APDU writes and firmware commands can affect card emulation and potentially payments. Do not expose them broadly, add fake feature flags or bypass routing access control. NFC and OMAPI use distinct authority.
3. **Mainline/APEX:** using private Java interfaces from a separately installed `system_ext` library must not weaken the NFC Mainline APEX update boundary, exported API contract, platform classloader or signature restrictions.
4. **SEMS:** never copy or redistribute unknown proprietary JARs for convenience; verify licences, bytecode/ABI, applet/scripting protocol, access policies and real product requirements, then build a minimal owned component if legally and technically justified.
5. **Wireless charging:** the NXP WLC NFC protocol is distinct from ordinary Qi and device power supply hardware. Do not claim mondrian feature support or add UI without concrete proof.
6. **Android17 compatibility:** direct `INfcAdapter` hidden APIs might differ, and historical NXP vendor methods are not guaranteed to exist in the Mainline NFC service. Avoid compile-time and runtime breakage; do not create fake stubs that silently succeed.

## Future acceptance gates

- Baseline AOSP17 NFC+SE native source ownership and immutable upstream SHA, including security updates if separately reviewed.
- Prove the **specific consumer → framework API → NFC service → HAL/eSE** call path, hardware feature and vendor ABI are needed for PE-Reborn mondrian.
- Choose **RETAIN AOSP17 / adapt a current vendor API / minimal PE-owned module / reject** with changes justified and reviewed. No bulk ROM/LineageOS source inheritance.
- Soong build Java/framework Nfc, APEX packaging, exported API checks, VINTF, SELinux enforcing/neverallow, NFC permissions, Binder/user security and CTS/VTS.
- Physical NFC tag polling/reader, HCE, SE/UICC routes, recovery after restart, airplane/screen-off, wallet where permitted and actual product hardware/certification checks. Do not perform unapproved SE provisioning.
- Battery and responsiveness testing if making a performance claim. Rollback must be defined for any vendor-side change.

## Implementation in this review

- Source-only independent audit branch, immutably pinned historical NFC/official AOSP17 NFC+SE source checker, CI against current staging manifest.
- Active PE-Reborn AOSP17 manifest **source ownership** guarded; archive-only NXP frameworks path/name must never be added until a separately validated build and consumer.
- The historical `seventeen` branch, LF52406 device trees, kernel, proprietary blobs, existing NFC services and vendor firmware are unchanged.

**NOT COMPLETED:** port of NXP framework or SEMS, Soong/Android17 system build, actual NFC/APEX integration, HAL/SE compatibility, device VINTF, SELinux and physical mondrian testing.
