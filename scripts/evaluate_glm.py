"""使用已下载的上海文旅公告 HTML 小样本；显式 --live 才调用内测服务器模型。"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys

# 先定口径再看输出。每个非空字段须含全部关键事实；None 表示原文没有该字段。
# cost 只认实际支出，不把折扣率当作实付；deadline 指获得该优惠的截止，不是使用截止。
# 适用的购买渠道、证件、预约也是参与条件。
CASES = {
    "bus": ("2026年11月17日-11月20日深圳秋假期间", {
        "reward": ["免费", "观光车"], "cost": ["免费"], "eligibility": ["深圳身份证", "深圳市医保卡"], "deadline": ["11月20日"]}),
    "museum": ("“美洲展门票+讲解”组合产品原价298元", {
        "reward": ["268元"], "cost": ["268元"], "eligibility": ["深圳锦旅公司", "购买", "预约"], "deadline": ["2026年12月31日"]}),
    "voucher": ("2026年11月1日-12日，通过春秋旅游", {
        "reward": ["兑换券", "5折起"], "cost": None, "eligibility": ["预约日期前一天", "预约"], "deadline": ["11月1日-12日"]}),
    "early_bird": ("2.早鸟一日票，至少提前10天", {
        "reward": ["9折"], "cost": None, "eligibility": ["提前10天"], "deadline": None}),
    "zoo": ("2026年11月12日-11月30日，在上海野生动物园", {
        "reward": ["139元", "269元"], "cost": ["139元", "269元"], "eligibility": ["线上购买"], "deadline": ["11月30日"]}),
}


class Segments(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data.strip())


def load_cases(path):
    parsed = Segments()
    parsed.feed(path.read_text(encoding="utf-8"))
    inputs = {}
    for label, (prefix, _) in CASES.items():
        matches = [s for s in parsed.parts if s.startswith(prefix)]
        if len(matches) != 1 or len(matches[0]) > 300:
            raise ValueError(f"{label}: 原文已变化，请先重审样本")
        inputs[label] = matches[0]
    return inputs


# 只传公开规则，不读取凭据；评测生成的缓存随事务回滚，不发布活动。
REMOTE = """
from django.db import transaction
from discovery.glm import analyze, VERSION, MODEL
from urllib.error import HTTPError
import time
stop = False
for label, text in inputs.items():
    if stop:
        print(json.dumps({"case":label,"skipped":"earlier_http_error"}))
        continue
    started=time.monotonic()
    try:
        with transaction.atomic():
            row = analyze(text)
            print(json.dumps({'case':label,'version':VERSION,'model':MODEL,'fields':row.excerpts,'usage':row.usage,'seconds':round(time.monotonic()-started,1)},ensure_ascii=False))
            transaction.set_rollback(True)
    except Exception as e:
        error = {'case':label,'error':type(e).__name__,'seconds':round(time.monotonic()-started,1)}
        if isinstance(e,HTTPError):
            error['http_status']=e.code
            stop = e.code in (401,403,429)
            # 仅记录枚举型的供应商错误代码，不记录原始正文（可能带跟踪号或其他信息）。
            try:
                code=json.loads(e.read(4096))['error']['code']
                if str(code).isascii() and str(code).isdigit(): error['provider_code']=str(code)
            except (KeyError,TypeError,ValueError): pass
        elif type(e) is ValueError and str(e) in ('模型未返回约定字段','模型摘录未通过原文校验'):
            error['reason']=str(e)
        print(json.dumps(error))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--case", choices=CASES, help="仅诊断一个样本，不重跑整批")
    args = parser.parse_args()
    inputs = load_cases(args.html)
    print("样本 SHA256:", hashlib.sha256(json.dumps(inputs,ensure_ascii=False).encode()).hexdigest(),flush=True)
    if args.case:
        inputs = {args.case: inputs[args.case]}
    if not args.live:
        print(f"{len(inputs)} 条已就绪，未调用模型")
        return
    script = "import json\ninputs="+repr(inputs)+"\n"+REMOTE
    proc = subprocess.run(["ssh","-o","BatchMode=yes","root@43.143.230.174",
        "cd /opt/haotoday && docker compose exec -T app python manage.py shell -v0"],
        input=script,text=True,capture_output=True,timeout=185,check=True)
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    if [row["case"] for row in rows] != list(inputs):
        sys.exit("未取得完整评测输出，不能计算指标")
    for row in rows:
        if "fields" in row:
            for field, need in CASES[row["case"]][1].items():
                excerpt = row["fields"][field]
                ok = excerpt is None if need is None else all(v in (excerpt or "") for v in need)
                row.setdefault("anchors_ok",{})[field] = ok
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
