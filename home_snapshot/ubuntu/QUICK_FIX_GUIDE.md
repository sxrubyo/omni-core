# ⚡ Quick Fix Guide: Melissa + WhatsApp Bridge

## 🔴 TOP 10 FIXES (Priority Order)

### MELISSA

#### 1️⃣ **FIX: Add Auth to `/broadcast` and `/reset`** (2 min)
**File**: `~/melissa/melissa.py` line ~11400

```python
# BEFORE
@app.post("/broadcast")
async def broadcast(request: Request):
    body = await request.json()
    # ...

# AFTER - Add decorator
def _requires_master_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not _verify_master_key(args[0]):  # args[0] is request
            return {"error": "Unauthorized"}, 401
        return await f(*args, **kwargs)
    return decorated

@app.post("/broadcast")
@_requires_master_key
async def broadcast(request: Request):
    body = await request.json()
    # ...
```

---

#### 2️⃣ **FIX: Generate Strong Webhook Secret** (1 min)
**File**: `~/.env`

```bash
# BEFORE
WEBHOOK_SECRET=melissa_ultra_5

# AFTER - Run this:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output → 
WEBHOOK_SECRET=YOUR_OUTPUT_HERE
```

---

#### 3️⃣ **FIX: Use Timing-Safe Comparison** (3 min)
**File**: `~/melissa/melissa.py` lines 10997, 10864

```python
# BEFORE
if mode == "subscribe" and token == Config.WA_VERIFY_TOKEN:
if secret != Config.WEBHOOK_SECRET:

# AFTER
import secrets
if mode == "subscribe" and secrets.compare_digest(token, Config.WA_VERIFY_TOKEN):
if not secrets.compare_digest(secret, Config.WEBHOOK_SECRET):
```

---

#### 4️⃣ **FIX: Add Rate Limiting** (5 min)
```bash
pip install slowapi

# File: ~/melissa/melissa.py top
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# On webhook endpoint (line ~10820)
@app.post("/webhook")
@limiter.limit("100/minute")
async def webhook(request: Request):
    # ...
```

---

#### 5️⃣ **FIX: Fix SQLite Threading** (10 min)
**File**: `~/melissa/melissa.py` line 959

```python
# BEFORE
conn = sqlite3.connect(self.db_path, check_same_thread=False)

# AFTER
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    f'sqlite:///{self.db_path}',
    poolclass=QueuePool,
    connect_args={'timeout': 15},
    pool_size=5,
    max_overflow=10
)
```

---

### WhatsApp Bridge

#### 6️⃣ **FIX: Handle Reconnection Errors** (2 min)
**File**: `~/whatsapp-bridge/index.js` line 177

```javascript
// BEFORE
setTimeout(startBridge, 5000);

// AFTER
setTimeout(async () => {
    try {
        await startBridge();
    } catch (err) {
        logger.error({ err: err.message }, 'Reconnection failed');
    }
}, 5000);
```

---

#### 7️⃣ **FIX: Populate Webhook Token** (1 min)

```bash
# Generate token
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Update ~/.env (Melissa)
WEBHOOK_SECRET=YOUR_TOKEN_HERE

# Update ~/whatsapp-bridge/.env (Bridge)
WEBHOOK_TOKEN=YOUR_TOKEN_HERE
```

---

#### 8️⃣ **FIX: Add Graceful Shutdown** (3 min)
**File**: `~/whatsapp-bridge/index.js` before app.listen()

```javascript
process.on('SIGTERM', async () => {
    logger.info('SIGTERM received, shutting down...');
    if (keepAliveTimer) clearInterval(keepAliveTimer);
    if (presenceTimer) clearTimeout(presenceTimer);
    if (sock) {
        try { await sock.logout(); }
        catch (err) { logger.error(err.message); }
    }
    process.exit(0);
});
```

---

#### 9️⃣ **FIX: Re-authenticate WhatsApp** (5 min)

```bash
# Stop bridge
kill <PID_OF_NODE_PROCESS>

# Delete old session
rm -rf ~/whatsapp-bridge/sessions/default/

# Restart and scan QR
cd ~/whatsapp-bridge && npm start
```

---

#### 🔟 **FIX: Fix Bulk Send** (5 min)
**File**: `~/whatsapp-bridge/index.js` line 453

```javascript
// AFTER - with error handling
(async () => {
    try {
        for (let i = 0; i < messages.length; i++) {
            try {
                const result = await sock.sendMessage(...);
                messageStats.sent++;
            } catch (err) {
                logger.error({ index: i, err }, 'Send failed');
                messageStats.failed++;
            }
        }
    } catch (err) {
        logger.error({ err }, 'Bulk send failed');
    }
})().catch(err => logger.error({ err }, 'Unhandled'));
```

---

## ✅ Implementation Checklist

Phase 1 (30 min):
- [ ] Add auth to /broadcast, /reset (Melissa #1)
- [ ] Generate strong webhook secret (#2)
- [ ] Handle reconnection errors (Bridge #6)
- [ ] Populate webhook token (Bridge #7)

Phase 2 (30 min):
- [ ] Timing-safe comparison (Melissa #3)
- [ ] Graceful shutdown (Bridge #8)
- [ ] Re-authenticate WhatsApp (Bridge #9)

Phase 3 (Optional):
- [ ] Add rate limiting (Melissa #4)
- [ ] Fix SQLite threading (Melissa #5)
- [ ] Fix bulk send (Bridge #10)

---

## 🧪 Quick Test

```bash
# Test Melissa auth
curl -X POST http://localhost:8000/broadcast
# Should return 401 Unauthorized

# Check WhatsApp bridge
curl http://localhost:8002/status | grep connectionStatus
# Should show "open"

# Test webhook communication
# Send test message through bridge, verify Melissa receives it
```

---

**Status**: Ready to implement
**Time**: ~1 hour for critical fixes
**Risk**: Moderate (testing needed after each fix)
