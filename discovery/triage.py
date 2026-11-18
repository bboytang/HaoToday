"""GamerPower 领取指引的内部初筛。只决定复核顺序，不断言价值、地区或领取成功。"""
import hashlib
import re


def game_triage(row):
    raw = row.get("instructions")
    steps = " ".join(raw.lower().split()) if isinstance(raw,str) else ""
    raw_desc = row.get("description")
    description = " ".join(raw_desc.lower().split()) if isinstance(raw_desc,str) else ""
    gates = steps + "\n" + description
    digest = hashlib.sha256(steps.encode()).hexdigest()
    if re.search(r"\b(chance to win|enter (?:the |a )?(?:raffle|sweepstakes)|invite (?:your |\d+ )?friends)\b",steps):
        tier,reason = "exclude","抽奖或邀请指引"
    elif re.search(r"\b(?:[1-9]\d* (?:arp|points?) required|requires? [1-9]\d* (?:arp|points?)|paid subscription|(?<!no )purchase required|auto[- ]renewal)\b",gates):
        tier,reason = "hold","存在积分、消费或订阅门槛"
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",row["end_date"]):
        tier,reason = "review","缺少可复核的截止时间"
    elif re.search(r"\b(?:add (?:the game|it) to your library|get the bundle|download or claim)\b",steps):
        tier,reason = "priority","有领取动作及截止时间，优先核对发行方"
    else:
        tier,reason = "review","领取条件未识别"
    return {"tier":tier,"reason":reason,"steps_sha256":digest,"description_sha256":hashlib.sha256(description.encode()).hexdigest(),"version":2}
