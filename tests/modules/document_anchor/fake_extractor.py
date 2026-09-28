"""子进程异常夹具，仅访问测试 options 所在目录。"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.modules.document_anchor.support import seal
from tests.modules.document_anchor.test_acceptance import (
    _header,
    _page,
    _trailer,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode")
    parser.add_argument("--options-file")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--request-id")
    args, _ = parser.parse_known_args()
    if args.mode in {"hang", "orphan"}:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(90)"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        Path(args.options_file).with_name("owned-child.pid").write_text(str(child.pid))
        if args.mode == "orphan":
            print("invalid-json", flush=True)
            return
        time.sleep(90)
        return
    if args.mode == "huge":
        print("x" * 100000, flush=True)
        return
    header, page, trailer = _header(), _page(), _trailer()
    header.update(request_id=args.request_id, file_sha256=args.expected_sha256)
    trailer["request_id"] = args.request_id
    if args.mode == "large_valid":
        page["items"][0]["text"] = "x" * 20000
        page["items"] = [
            {**page["items"][0], "item_index": i, "source_array_index": i}
            for i in range(5)
        ]
        trailer["items_emitted"] = 5
    records = seal(header, [page], trailer)
    if args.mode == "missing_trailer":
        records.pop()
    elif args.mode == "wrong_header":
        records[0]["request_id"] = "wrong"
    elif args.mode == "incomplete":
        records[-1]["completed"] = False
    for record in records:
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
