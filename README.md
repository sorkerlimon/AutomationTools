# AutomationTools

Automation tools collection.

## chime

Chime account checker using AdsPower and Selenium.

### Setup

1. Copy `chime/config.example.py` to `chime/config.py` and fill in your AdsPower settings.
2. Add accounts to `chime/email.txt` (`email:password` per line).
3. Install dependencies:

```bash
pip install -r chime/requirements.txt
```

4. Run:

```bash
python chime/main.py
```

### Build exe

```bash
cd chime
pyinstaller chime_checker.spec
```

### Output files

- `log.txt` — run log
- `found.txt` — successful accounts
- `mobile_verify.txt` — mobile verification required
