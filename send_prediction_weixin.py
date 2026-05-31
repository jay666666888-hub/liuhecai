#!/usr/bin/env python3
"""
发送六肖预测到微信（通过iLink Bot API）
"""
import json, pathlib, urllib.request, urllib.error, asyncio, aiohttp

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
TOKEN = "13146151cc5b@im.bot:d859"
TO_USER = "o9cq801SI14R7uSI9zpdQJjFPRq4@im.wechat"
ACCOUNT_FILE = "/home/admin1/.hermes/weixin/accounts/13146151cc5b@im.bot.json"

def _base_info():
    return {"apivisible": 1, "app_claim": "hermes-agent"}

def _headers(token: str, body: str):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "iLink-App-Id": "cli_a95c6c69f9f8dbc2",
        "iLink-App-ClientVersion": "3.4.4",
    }

async def _get_updates(session: aiohttp.ClientSession, sync_buf: str) -> dict:
    body = json.dumps({"get_updates_buf": sync_buf, "base_info": _base_info()})
    url = f"{ILINK_BASE_URL}/ilink/bot/getupdates"
    headers = _headers(TOKEN, body)
    async with session.post(url, data=body.encode(), headers=headers) as resp:
        raw = await resp.text()
        if not resp.ok:
            raise RuntimeError(f"getupdates HTTP {resp.status}: {raw[:200]}")
        return json.loads(raw)

async def _send_text(session: aiohttp.ClientSession, text: str, context_token: str = None) -> dict:
    if not text.strip():
        raise ValueError("text must not be empty")
    message = {
        "from_user_id": "",
        "to_user_id": TO_USER,
        "client_id": "hermes-cron",
        "message_type": 1,
        "message_state": 4,
        "item_list": [{"type": 1, "text_item": {"text": text}}],
    }
    if context_token:
        message["context_token"] = context_token
    body = json.dumps({**{"msg": message}, "base_info": _base_info()})
    url = f"{ILINK_BASE_URL}/ilink/bot/sendmessage"
    headers = _headers(TOKEN, body)
    async with session.post(url, data=body.encode(), headers=headers) as resp:
        raw = await resp.text()
        if not resp.ok:
            raise RuntimeError(f"sendmessage HTTP {resp.status}: {raw[:200]}")
        return json.loads(raw)

async def _run(text: str) -> dict:
    timeout = aiohttp.ClientTimeout(total=30)
    sync_path = "/home/admin1/.hermes/weixin/accounts/13146151cc5b@im.bot.sync.json"

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1. 刷新context token
        sync_buf = json.loads(pathlib.Path(sync_path).read_text()).get("get_updates_buf", "")
        updates = await _get_updates(session, sync_buf)

        # 2. 保存新的sync_buf
        new_sync_buf = updates.get("get_updates_buf", sync_buf)
        if new_sync_buf != sync_buf:
            pathlib.Path(sync_path).write_text(json.dumps({"get_updates_buf": new_sync_buf}))

        # 3. 提取新鲜context_token
        context_token = None
        for msg in updates.get("msgs", []):
            if msg.get("msg", {}).get("from_user_id") == TO_USER:
                context_token = msg.get("msg", {}).get("context_token")
                break

        # 4. 发送消息
        return await _send_text(session, text, context_token)

def sync_send_text(text: str) -> dict:
    return asyncio.run(_run(text))

# ========== 读取数据 ==========
with open('/home/admin1/liuhecai_data.json') as f:
    all_data = json.load(f)
latest = all_data[-1]
本期 = latest['期号']
开奖号码 = latest.get('开奖号码', [])
开奖生肖 = latest.get('开奖生肖', [])
open_nums = []
for i, (num, zodiac) in enumerate(zip(开奖号码[:7], 开奖生肖[:7])):
    tag = '特' if i == 6 else str(i+1)
    open_nums.append(f"{num}{zodiac}")
open_str = "  ".join(open_nums)

# ========== 读取 V5 预测 ==========
v5 = json.loads(pathlib.Path('/home/admin1/liuhecai_latest_prediction.json').read_text())
v5_verify_period = v5.get('verified_period', 本期)
v5_verify_top6 = v5.get('verified_top6', [])
v5_verify_actual = v5.get('verified_actual', '')
v5_verify_hit = v5.get('verified_hit')
v5_pending_period = v5.get('pending_period', '')
v5_pending_top6 = v5.get('pending_top6', [])

# ========== 读取 V7 预测 ==========
v7 = json.loads(pathlib.Path('/home/admin1/liuhecai_v7_prediction.json').read_text())
v7_verify_period = v7.get('verified_period', v7.get('期号', 本期))
v7_verify_top6 = v7.get('prev_top6', [])
v7_verify_actual = v7.get('prev_actual', '')
v7_verify_hit = v7.get('prev_hit')
v7_pending_period = v7.get('预测期号', '')
v7_pending_top6 = v7.get('推荐6肖', [])

# ========== 格式化微信消息 ==========
v5_hit_str = "✅" if v5_verify_hit else "❌"
v7_hit_str = "✅" if v7_verify_hit else "❌"

lines = [
    "🎯 澳门六合",
    f"第{本期}期开奖",
    open_str,
    "──",
    f"V5验证 {v5_verify_period}期: {' '.join(v5_verify_top6)} → {v5_verify_actual} {v5_hit_str}",
    f"V5预测 {v5_pending_period}期: {' '.join(v5_pending_top6)}",
    "──",
    f"V7验证 {v7_verify_period}期: {' '.join(v7_verify_top6)} → {v7_verify_actual} {v7_hit_str}",
    f"V7预测 {v7_pending_period}期: {' '.join(v7_pending_top6)}",
]

msg_text = "\n".join(lines)
print("消息内容:", msg_text[:100], "...")

# ========== 发送 ==========
result = sync_send_text(msg_text)
code = result.get('errcode', result.get('ret', -1))
msg = result.get('errmsg', result.get('msg', ''))
print(f"errcode: {code}, msg: {msg}")
if code == 0:
    print("✅ 微信消息发送成功!")
else:
    print(f"❌ 发送失败: {json.dumps(result, ensure_ascii=False)}")
