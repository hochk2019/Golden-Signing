---
feature: token-multi-session
status: in-progress
updated: 2026-09-19
branch: (implement after user approval; prefer feature worktree if sandbox allows)
commits: (not started)
---

# Multi-token session handling (switch CKS after batch sign)

## Report

(empty — awaiting user approval before implementation)

## [S1] Problem

On a PC with **two USB tokens** (e.g. Sanchine + Jaeyoung/ECA), user signed batch with token A successfully, then cleared the job list, added new PDFs, picked **token B’s certificate** (Jaeyoung, serial `540117eca0139bb7c55c666d4550b3a4`), entered PIN, and got:

```text
Không mở được phiên ký trên token/PKCS#11.
• CKS: CÔNG TY TNHH JAEYOUNG VINA
• Nguồn: pkcs11
• Chi tiết: no token present
• Đã thử DLL: eca_csp11_v1.dll, vnptca…, fptca…, CA2_csp11.dll, ca2_ace… (+ no-serial retries)
```

Sidebar still showed ECA Token note from an earlier scan. Profile label showed PUS Safe · Token USB (not always the newly chosen company).

### Observed process vs code gaps

| Step | What happened | Code gap |
|---|---|---|
| Batch 1 sign OK (Sanchine) | PKCS#11 session opened | Session **not closed** when user later switches CKS |
| Clear list + new files + Ký | Cert picker appeared | `_token_signer` was empty/unset; catalog may still be **cached (20s)** |
| Choose Jaeyoung | serial on picker = ECA/JAEYOUNG | `CertificateInfo` **does not store which DLL** listed that serial |
| PIN → open session | every DLL: `no token present` | Tries System32 DLL list in **fixed order**, not “DLL that owned this cert”; no **preflight** that token/serial still live before PIN |
| Fallback `(no-serial)` | still fail | If it had succeeded, code could bind **wrong cert on another token** to chosen cert_info |
| Cache | certs listed when both tokens/scans valid | `collect_display_certificates(use_cache=True)` on sign path can show **stale** CKS |

**Product requirement (user):** intelligent multi-token support; report plan first; implement only after approval.

## [S2] Design

### Contracts

1. **Certificate identity includes origin**
   - Extend `CertificateInfo` with `pkcs11_library: str | None = None` (absolute path or empty).
   - PKCS#11 certs from catalog **must** carry the DLL that listed them.
   - Windows store certs: `pkcs11_library is None`, `backend == "windows_store"`.

2. **Catalog freshness on signing**
   - Opening the cert picker for a real sign (`_ensure_token_engine`) uses **fresh scan** (ignore cache) or TTL=0.
   - After batch sign completes (success or fail), **and** on Quét lại token: `clear_certificate_cache()` + close PKCS#11 session.

3. **Session lifecycle**
   - `TokenPdfSigner.close_session()` — best-effort close pkcs11 session; called when: rescan, starting `_ensure_token_engine`, app teardown if easy, replacing signer.
   - Never leave token A session open while opening token B.

4. **Open algorithm (after user picks cert + before/around PIN)**

```text
preferred = [chosen.pkcs11_library] if set else []
candidates = preferred + [d for d in discover_pkcs11_libraries() if d != preferred]
# drop unsafe fallback:
# — NO open_session without serial when serial is known
Preflight (no PIN if possible):
  list_certificates(preferred_dll) contains chosen.serial
  → if not: error before PIN
    "Không thấy serial … trên <dll>. Kiểm tra token USB đã cắm đúng, Quét lại token."
PIN once → open_session_with_pin(preferred, pin, cert_serial=serial)
On success: bind_session(session, cert, key_id) + cert_info must be the cert **returned by that DLL** (verify serial match)
If preferred fails: try other DLLs **only with cert_serial=serial** (no loose fallback)
```

5. **Reuse of existing signer**
   - `_on_sign`: if `_token_signer` is set, **re-validate** serial still present on `signer.library_path` via `list_certificates`; else drop signer and call `_ensure_token_engine()`.
   - Re-validate prevents “signed with stale token B after unplugging/switching”.

6. **Reset CKS (user-approved)**
   - Rename main button **Quét lại token** → **Reset CKS**.
   - Behavior: clear cert cache → re-enumerate PKCS#11 + store → refresh token note.  
     **Keep** in-app sessions already opened this run (keyed by cert serial/fingerprint).
   - Error dialog offers **Reset CKS** action (same behavior) instead of only “Quét lại”.
   - If user picks the **same serial** that already has an open session this run → **skip PIN**, re-bind that session (after serial re-validate).  
   - Other serials still require PIN once per session.
   - No serial-less fallback when serial is known (user chose option 1).

7. **Picker UX (minimal, smart)**
   - Cert card meta already has `token_label`; also show **DLL file name** when `pkcs11_library` set.
   - Sort certs: group by `token_label` then company name (Sanchine vs Jaeyoung easier to see).
   - Do **not** auto-select a cert across companies without user pick (keep explicit choice).

7. **Error messages**
   - Prefer: which serial, which DLL, “token present? yes/no”, last exception.
   - Never show bare `None`.

### Out of scope (this feature)

- Windows CSP/KSP software signing without PKCS#11.
- ECUSSign remote signing (paused).
- Changing PUS Safe crypto profile semantics.
- Auto-picking “the other” token without user selecting CKS.

## [S3] Out of Scope

See above. No production UI redesign beyond picker meta/sort and error text.

## Tasks (after approval)

- [ ] T1: `CertificateInfo.pkcs11_library` + catalog stamps DLL — acceptance: unit test shows cert from `eca_csp11_v1.dll` has that path (covers: S2.1)
- [ ] T2: Sign-path fresh scan + cache clear after batch/rescan — acceptance: `_ensure_token_engine` does not serve >TTL cache; `_run_batch` end calls `clear_certificate_cache()` (covers: S2.2)
- [ ] T3: `TokenPdfSigner.close_session` + call sites — acceptance: switching/rescan closes previous session (unit/smoke) (covers: S2.3)
- [ ] T4: Preferred-DLL open + serial preflight + no serial-less fallback when serial known — acceptance: mock/path tests; error text when serial missing on preferred DLL (covers: S2.4)
- [ ] T5: `_on_sign` re-validate active signer serial — acceptance: stale signer forces picker again (covers: S2.5)
- [ ] T6: Picker shows DLL/token_label + group sort — acceptance: UI lists two companies with distinct labels (covers: S2.6)
- [ ] T7: Tests + manual multi-token script checklist — acceptance: pytest green; checklist in spec Report (covers: S2)
- [ ] T8: Rebuild installer after user approval — acceptance: Setup artifact + checksums for reinstall (covers: S2)

## Manual acceptance checklist (user test)

1. Cắm 2 token (Sanchine + Jaeyoung).  
2. Ký batch với **Sanchine** → Hoàn tất N thành công.  
3. Xóa danh sách → thêm file mới → Ký → chọn **Jaeyoung** → PIN.  
4. **Kỳ vọng:** ký thành công bằng serial Jaeyoung (không `no token present` nếu token ECA vẫn cắm).  
5. Ngược lại: chọn Sanchine sau batch Jaeyoung → OK.  
6. Rút token Jaeyoung → Quét lại → picker **không** còn serial Jaeyoung (hoặc báo mất token trước PIN).
