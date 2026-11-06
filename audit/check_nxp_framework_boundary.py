#!/usr/bin/env python3
"""PE-Reborn Android17 row 167 NXP Java NFC framework source-boundary gate.

Offline relative to pinned git checkouts. SOURCE ONLY, not a Soong/device test.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OLD_SHA = "b56688d998a0d9aa4248890f13db00dd2a1ffdb2"
OLD_TREE = "73dd1ca79986452c7da4ced77866ae47eb7b18c6"
NFC_SHA = "940212c440f57032a19cf0f90c7faa8eca48d546"
NFC_TREE = "da01c841e3238648d0ae33c3392c05f1552e63d5"
SE_SHA = "a9644a6b928ca9c7fce4b1939e04c9b74c5533bb"
SE_TREE = "50324e595c97f9d7673d62a332656e161378bbdc"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args],
                                   text=True).strip()


def verify(repo, ref, sha, tree, label):
    actual = git(repo, "rev-parse", f"{ref}^{{commit}}")
    require(actual == sha, f"{label} commit mismatch: {actual}")
    got_tree = git(repo, "rev-parse", f"{actual}^{{tree}}")
    require(got_tree == tree, f"{label} source tree mismatch: {got_tree}")
    return actual


def show(repo, rev, path):
    return git(repo, "show", f"{rev}:{path}")


def legacy_nxp(repo):
    rev = verify(repo, "refs/remotes/origin/seventeen",
                 OLD_SHA, OLD_TREE, "archived NXP framework")
    bp = show(repo, rev, "Android.bp")
    xml = ET.fromstring(show(repo, rev, "com.nxp.nfc.nq.xml"))
    adapter = show(repo, rev, "com/nxp/nfc/NxpNfcAdapter.java")
    wlc = show(repo, rev, "com/nxp/nfc/NxpWlcAdapter.java")
    aidl = show(repo, rev, "com/nxp/nfc/INxpNfcAdapter.aidl")
    sems = show(repo, rev, "sems/com/nxp/sems/SemsAgent.java")
    tree_files = git(repo, "ls-tree", "-r", "--name-only", rev).splitlines()

    require('name: "com.nxp.nfc.nq"' in bp
            and "system_ext_specific: true" in bp
            and '"com.nxp.nfc.nq.xml"' in bp
            and '"com/**/*.java"' in bp,
            "archived java framework module changed")
    lib = xml.find("library")
    require(lib is not None
            and lib.get("name") == "com.nxp.nfc.nq"
            and lib.get("file") ==
                "/system/system_ext/framework/com.nxp.nfc.nq.jar",
            "archived shared library XML registration changed")
    require('getNfcAdapterVendorInterface("nxp")' in adapter
            and 'getNfcAdapterVendorInterface("wlc")' in wlc,
            "archived direct NXP/WLC Binder interface contract changed")
    for action in ("DefaultRouteSet(", "selectUicc(", "setConfig(",
                   "activateSeInterface(", "doWriteT4tData(", "nfcSelfTest("):
        require(action in aidl, f"archived privileged NFC operation changed: {action}")
    require("sems/sems.jar" in tree_files
            and "sems/com.nxp.ls.jar" in tree_files,
            "archived bundled SEMS JAR inventory changed")
    require("SEMS_HASH_TYPE_SHA1" in sems and "SEMS_HASH_TYPE_SHA256" in sems
            and "!= SEMS_HASH_TYPE_SHA1" in sems,
            "archived SEMS algorithm string code changed")
    require(not any(t in bp for t in ("sems.jar", "com.nxp.sems.jar", "com.nxp.ls.jar")),
            "SEMS binaries now wired into the archived module: re-audit")
    print("PASS: exact archived NXP framework, WLC, SEMS and Binder APIs pinned")


def official_nfc(repo):
    rev = verify(repo, "FETCH_HEAD", NFC_SHA, NFC_TREE,
                 "official Android17 NFC Mainline")
    paths = git(repo, "ls-tree", "-r", "--name-only", rev).splitlines()
    require(any(p.endswith("/NfcService.java") for p in paths),
            "official NFC service source missing")
    require(any(p.endswith("/NfcAdapter.java") for p in paths),
            "official NFC adapter framework missing")
    require(any(p.endswith("/NfcOemExtension.java") for p in paths),
            "official NFC OEM extension framework missing")
    bp = show(repo, rev, "apex/Android.bp")
    require('name: "com.android.nfcservices"' in bp
            and 'NfcNciApex' in bp,
            "official NFC Mainline APEX contract changed")
    print("PASS: exact AOSP17 NFC Mainline has service, adapter, OEM API and APEX")


def official_secure_element(repo):
    rev = verify(repo, "FETCH_HEAD", SE_SHA, SE_TREE,
                 "official Android17 secure element")
    readme = show(repo, rev, "omapi/README.md")
    require("OMAPI" in readme and "secure element" in readme.lower(),
            "official native OMAPI service boundary changed")
    paths = git(repo, "ls-tree", "-r", "--name-only", rev).splitlines()
    require(any(p.startswith("omapi/") and p.endswith(".rs") for p in paths),
            "native OMAPI source module inventory changed")
    print("PASS: exact AOSP17 secure_element has native OMAPI service")


def active_manifest(repo):
    root = Path(repo)
    entry = ET.parse(root / "default.xml").getroot()
    require(len(entry) == 1
            and entry[0].get("name") == "aosp17_pe_p2_kernel_configs.xml",
            "AOSP17 staged default changed")
    bootstrap = ET.parse(root / "aosp17_pe_bootstrap.xml").getroot()
    owners = {p.get("path"): p.get("name") for p in bootstrap.findall("project")}
    require(owners.get("packages/modules/Nfc") == "platform/packages/modules/Nfc",
            "Mainline NFC official owner changed")
    require(owners.get("system/secure_element") ==
            "platform/system/secure_element",
            "Secure Element official owner changed")
    require("vendor/nxp/opensource/commonsys/frameworks" not in owners
            and "vendor_nxp_opensource_commonsys_frameworks" not in owners.values(),
            "unreviewed legacy NXP Java frameworks enabled")
    subprocess.run(
        [sys.executable, str(root / "tools/validate_aosp17_base_profiles.py")],
        cwd=root, check=True)
    print("PASS: official AOSP17 NFC and secure_element owners retained in manifest")


def main():
    require(len(sys.argv) == 5,
            "usage: check_nxp_framework_boundary.py LEGACY_NXP AOSP17_NFC AOSP17_SE MANIFEST")
    old, nfc, se, manifest = [Path(s).resolve() for s in sys.argv[1:]]
    require(all(x.is_dir() for x in (old, nfc, se, manifest)),
            "missing source checkout")
    legacy_nxp(old)
    official_nfc(nfc)
    official_secure_element(se)
    active_manifest(manifest)
    print("PASS: row 167 Android17 NXP Java framework source boundary")
    print("OPEN: consumer/services/permission ABI, independent PE device,")
    print("      Soong/APEX/OMAPI/VINTF, SE safety, NFC tests, physical mondrian")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
