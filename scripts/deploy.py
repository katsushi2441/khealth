#!/usr/bin/env python3
"""out/health/ を exbridge.jp/health/ に置く（FTPS・1接続。heteml は短時間に接続を重ねると遮断されるため）。
資格情報は /home/kojima/work/aixec/.env の FTP_*（表示しない）。
  set -a; . /home/kojima/work/aixec/.env; set +a; /usr/bin/python3 scripts/deploy.py [--changed]
--changed: 前回置いたときの md5（out/.deployed.json）と違うファイルだけ送る。
"""
import ftplib, hashlib, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "health"
DEST = "/web/exbridge_jp/health"
STATE = ROOT / "out" / ".deployed.json"


def main():
    only_changed = "--changed" in sys.argv
    prev = json.loads(STATE.read_text()) if (only_changed and STATE.exists()) else {}
    files = [p for p in sorted(SRC.rglob("*")) if p.is_file()]
    sums = {p.relative_to(SRC).as_posix(): hashlib.md5(p.read_bytes()).hexdigest() for p in files}
    todo = [p for p in files if prev.get(p.relative_to(SRC).as_posix()) != sums[p.relative_to(SRC).as_posix()]]
    ftp = ftplib.FTP_TLS(os.environ.get("FTP_HOST", "ftp-exbridge.heteml.net"), timeout=120)
    ftp.login(os.environ["FTP_USER"], os.environ["FTP_PASS"])
    ftp.prot_p()
    made = set()

    def ensure(d):
        parts = d.split("/")
        for i in range(2, len(parts) + 1):
            x = "/".join(parts[:i])
            if x and x not in made:
                try:
                    ftp.mkd(x)
                except ftplib.error_perm:
                    pass
                made.add(x)

    n = 0
    for p in todo:
        rel = p.relative_to(SRC).as_posix()
        target = f"{DEST}/{rel}"
        ensure(target.rsplit("/", 1)[0])
        with open(p, "rb") as f:
            ftp.storbinary(f"STOR {target}", f)
        n += 1
        if n % 500 == 0:
            print("  ...", n, flush=True)
    ftp.quit()
    STATE.write_text(json.dumps(sums))
    print("uploaded", n, "of", len(files), "files →", DEST)


if __name__ == "__main__":
    main()
