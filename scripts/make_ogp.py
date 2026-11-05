#!/usr/bin/env python3
"""Kurage 健康トラッカーの OGP 画像（out/health/og/*.png、1200×630）。2026-11-05

骨格（文字の位置・右下のマスコット・左下のURL）は国会トラッカーのカード（xb4g/giin/scripts/make_ogp_all.py）と同じで、色は緑。
マスコットは縦横比のまま（変形させない）。見出しは「何が分かるか」、数字は全国の値など見る人の役に立つものだけ。
  /usr/bin/python3 scripts/make_ogp.py
"""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/home/kojima/work/xb4g/giin/scripts")
from make_ogp_all import W, H, FB, FM, FR, fit, _mascot   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "health"
OUT = ROOT / "out" / "health" / "og"
GREEN, GREEN_D, GREEN_L, GREEN_XL = "#2e7d32", "#1b5e20", "#c8e6c9", "#e8f5e9"
AMBER, NAVY, GRAY = "#f59e0b", "#12202f", "#5d6b7a"


def card(name, steps, line1, line2, sub1, sub2, url):
    img = Image.new("RGB", (W, H), "#ffffff")
    dr = ImageDraw.Draw(img, "RGBA")
    dr.ellipse([-180, -240, 480, 380], fill=(232, 245, 233, 255))
    dr.ellipse([W - 460, H - 330, W + 220, H + 240], fill=(241, 248, 241, 255))
    cx = 520 if _mascot else W // 2
    maxw = 900 if _mascot else 1080
    fc = ImageFont.truetype(FM, 26)
    ws = [dr.textlength(s, font=fc) + 44 for s in steps]
    x = cx - (sum(ws) + 14 * (len(steps) - 1)) / 2
    for s, w in zip(steps, ws):
        dr.rounded_rectangle([x, 88, x + w, 136], radius=24, fill=GREEN_XL, outline=GREEN_L, width=2)
        dr.text((x + w / 2, 112), s, font=fc, fill=GREEN_D, anchor="mm")
        x += w + 14
    dr.text((cx, 210), line1, font=fit(dr, line1, FB, 58, maxw), fill=NAVY, anchor="mm")
    f2 = fit(dr, line2, FB, 50, maxw)
    dr.text((cx, 292), line2, font=f2, fill=GREEN, anchor="mm")
    lw = dr.textlength(line2, font=f2)
    dr.rounded_rectangle([cx - lw / 2, 326, cx - lw / 2 + min(lw, 160), 332], radius=3, fill=AMBER)
    y = 380
    for t in (sub1, sub2):
        if t:
            dr.text((cx, y), t, font=fit(dr, t, FR, 27, maxw - 120), fill=GRAY, anchor="mm")
            y += 40
    band = "Kurage 健康トラッカー"
    f_band = fit(dr, band, FM, 29, 460)
    bw2 = max(460, dr.textlength(band, font=f_band) + 60)
    dr.rounded_rectangle([cx - bw2 / 2, 480, cx + bw2 / 2, 540], radius=16, fill=GREEN)
    dr.text((cx, 510), band, font=f_band, fill="#ffffff", anchor="mm")
    if _mascot:
        img.paste(_mascot, (W - _mascot.width - 40, H - _mascot.height - 30), _mascot)
    dr.text((40, H - 40), url, font=ImageFont.truetype(FR, 22), fill=GRAY, anchor="lm")
    img.save(OUT / f"{name}.png", optimize=True)


def pct(x):
    return f"{x * 100:.1f}%"


# 話題ごとのカードの見出し（何が分かるか）。検索で使われる語（research/kw-*.tsv）を入れる
TOPIC_LINE = {
    "alt": "肝臓の数値（ALT）が30を超えた人は？", "fukui": "メタボの腹囲の基準を超えた人は？", "bmi": "BMI 25以上の人は？",
    "hba1c": "HbA1cが6.5%以上の人は？", "amai-nomimono": "間食や甘い飲み物を毎日とる人は？", "yashoku": "寝る前2時間以内に夕食をとる人は？",
    "choshoku-nuki": "朝食を週3回以上抜く人は？", "hayagui": "早食いの人は？", "sake-mainichi": "お酒を毎日飲む人は？",
    "suimin": "睡眠で休養がとれていない人は？", "undo": "運動の習慣がない人は？", "taiju-zoka": "20歳から10kg以上増えた人は？",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ix = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    food = json.loads((DATA / "food.json").read_text(encoding="utf-8"))
    n = 0
    card("index", ["脂肪肝", "メタボ", "食べ方", "睡眠", "保健指導"], "肝臓の数値・メタボ・食べ方・睡眠を、", "都道府県と地域ごとに。",
         "特定健診を受けた40〜74歳の公的データ（NDBオープンデータ）から。", "健診のあとの保健指導と、料理1人前の栄養も。", "exbridge.jp/health/"); n += 1
    for t in ix["topics"]:
        card(t["slug"], ["全国", "男女と年齢", "都道府県", "二次医療圏"], TOPIC_LINE.get(t["slug"], t["name"]), "都道府県と地域ごとの割合。",
             f"全国 {pct(t['all'])}（男性 {pct(t['m'])}・女性 {pct(t['f'])}）{t['year']}の特定健診", "NDBオープンデータ（厚生労働省）から、出典つきで。", f"exbridge.jp/health/{t['slug']}/"); n += 1
    card("kenshin", ["市町村国保", "健康保険組合", "2018〜2024年度"], "特定健診のあとの保健指導は、", "どこまで届いているか。",
         "特定健診の受診率と特定保健指導の実施率を、市町村と保険者ごとに。", "厚生労働省の保険者別の公表資料から。", "exbridge.jp/health/kenshin/"); n += 1
    card("kumiai", ["健康保険組合", "共済組合", "国保組合"], "会社の健康保険組合の", "特定健診と保健指導の実施率。",
         "約1,600の健康保険組合・共済組合・国保組合を、名前で探せます。", "2018〜2024年度の推移を、厚生労働省の公表資料から。", "exbridge.jp/health/kenshin/kumiai/"); n += 1
    card("food", ["カロリー", "たんぱく質", "食物繊維", "食塩"], "身近な料理1人前の栄養を、", "食品成分表で計算。",
         "具材ごとの量と、日本食品標準成分表（八訂）増補2023年の値から。", "具材と量の前提は、ページに書いています。", "exbridge.jp/health/food/"); n += 1
    for d in food["dishes"]:
        t = d["total"]
        card("food-" + d["slug"], ["カロリー", "たんぱく質", "食物繊維", "食塩"], d["short"] + "の", "カロリーと栄養。",
             f"約{t['kcal']:.0f}kcal・たんぱく質{t['protein']}g・食物繊維{t['fiber']}g・食塩{t['salt']}g", "日本食品標準成分表（八訂）増補2023年で、具材ごとに計算。", f"exbridge.jp/health/food/{d['slug']}/"); n += 1
    print("作成", n, "枚 →", OUT)


if __name__ == "__main__":
    main()
