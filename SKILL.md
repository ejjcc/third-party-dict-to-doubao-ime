---
name: wechat-dict-to-doubao-ime
description: Import a local WeType (微信输入法) or Sogou user dictionary into Doubao IME on macOS, including privacy-safe discovery, dry-run validation, backup, import, and verification. Use when the user asks to migrate, inspect, or validate personal input-method words for 豆包输入法; do not use for Windows, Android, iOS, or unrelated text conversion.
---

# WeChat Dictionary to Doubao IME

Use the bundled `import_user_dict_to_doubao_ime.py` instead of reimplementing either database format.

## Choose the operation

- For feasibility checks, inspection, or diagnostics, run a dry-run. It may stop WeType briefly to copy a consistent local snapshot, then immediately restart it.
- Run a live import only when the user explicitly asks to import or otherwise authorizes modifying the Doubao user dictionary.
- Treat a supplied Sogou `.bin`/`.sgpu` file as the Sogou source. Treat requests mentioning 微信输入法 or WeType as the WeType source.

Run commands from this skill directory so the adjacent reader module can be imported.

```bash
python3 import_user_dict_to_doubao_ime.py --wetype-user-dict --dry-run
python3 import_user_dict_to_doubao_ime.py --wetype-user-dict
python3 import_user_dict_to_doubao_ime.py /path/to/sogou-backup.bin --dry-run
```

Use `--limit 100` when the user requests a small live trial. Use an explicit path after `--wetype-user-dict` when automatic discovery fails.

## Preserve safety and privacy

- Never open the original WeType database with a LevelDB library. The bundled reader is read-only and parses a copied snapshot.
- Do not display, quote, or upload personal words unless the user explicitly asks to see examples.
- Do not use `--no-stop-wetype` for a normal import; a live copy may be inconsistent.
- Keep the automatic Doubao backup. Do not pass `--skip-backup` unless the user explicitly accepts losing rollback protection.
- If a run fails, report the run directory and error. Do not retry a live import repeatedly without diagnosing the failure.

## Report the outcome

For dry-runs, report source, parsed/selected/skipped counts, and compatibility observations without word samples. For live imports, report imported and failed counts, verification results, index utilization, backup location, and whether WeType and DoubaoIme are running afterward.

The implementation currently targets macOS, local WeType `userDict/v5`, and the installed Doubao IME framework. Internal formats can change after either application upgrades; rerun dry-run after upgrades.
