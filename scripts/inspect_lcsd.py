"""核查 LCSD 官方 XML 下载样本；只读，不联网、不发布，不推断领取资格。"""
import argparse
from collections import Counter
import hashlib
import json
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def inspect(raw):
    if len(raw) > 8_000_000 or b"<!DOCTYPE" in raw.upper():
        raise ValueError("文件过大或含文档类型声明")
    root = ET.fromstring(raw)
    if root.tag != "events" or not len(root):
        raise ValueError("节目目录不可用")
    counts = Counter()
    samples = []
    seen = set()
    for row in root:
        key = row.get("id", "")
        if row.tag != "event" or not re.fullmatch(r"[0-9]+", key) or key in seen or row.find("pricec") is None:
            raise ValueError("记录结构或标识异常")
        seen.add(key)
        price = row.findtext("pricec").strip()
        if price in ("免費節目", "免費入場", "免費入場 (先到先得)"):
            counts["explicit_free_label"] += 1
            link = urlsplit(row.findtext("urlc", "").strip())
            if link.scheme == "https" and link.netloc.endswith(".gov.hk"):
                counts["free_with_gov_detail_link"] += 1
                if len(samples) < 3:
                    samples.append(key)
        elif not price:
            counts["no_price"] += 1
        elif re.fullmatch(r'\$[1-9][0-9]*(?:,\s*\$?[1-9][0-9]*)*', price):
            counts["positive_price_list"] += 1
        else:
            counts["needs_rule_review"] += 1
    return dict(source="香港特别行政区政府康乐及文化事务署 / DATA.GOV.HK；数据知识产权归原权利人",
                sha256=hashlib.sha256(raw).hexdigest(), rows=len(seen), counts=dict(counts),
                review_sample_ids=samples)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=argparse.FileType("rb"))
    with parser.parse_args().file as f:
        print(json.dumps(inspect(f.read(8_000_001)), ensure_ascii=False, indent=2))
