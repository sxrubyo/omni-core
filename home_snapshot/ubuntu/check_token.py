
import os
def _load_master_env():
    env_path = '/home/ubuntu/melissa/.env'
    if not os.path.exists(env_path):
        print("NO .env")
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ[key] = val

_load_master_env()
tok = os.environ.get('OMNI_TELEGRAM_TOKEN', '')
print(f"OMNI_TELEGRAM_TOKEN: {tok}")
if tok:
    suffix = tok.split(":")[-1][:10]
    print(f"SUFFIX: {suffix}")
else:
    print("NO TOKEN")
