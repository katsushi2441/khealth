# khealth — Kurage 健康トラッカー

食べ方・睡眠・運動と、健診の数値（ALT・腹囲・BMI・HbA1c）を都道府県と二次医療圏ごとに、
健診のあとの保健指導の実施率を市町村と保険者ごとに、身近な料理1人前の栄養を、公的データだけで並べるデータ作り。
画面は国会トラッカーのサイトの中（xb4g/giin の lib/health_pages.php）。

- 公開: https://xb4g.com/giin/health/ （話題 /health/<話題>・保健指導 /health/kenshin・料理 /health/food）
- しないこと: 医療の助言・診断、因果の主張（地域の差は相関まで）、保険者や自治体の良し悪しの判定。

## データ

| 何を | 出典 | スクリプト | 出力 |
|---|---|---|---|
| 食べ方・睡眠・運動・健診の検査値（12の話題） | 第11回NDBオープンデータ 特定健診 2023年度（厚生労働省） | scripts/build_ndb.py | data/health/<話題>.json・index.json |
| 健診のあとの保健指導（保険者 約3,350・2018〜2024年度） | 特定健康診査・特定保健指導の実施状況（保険者別）（厚生労働省） | scripts/build_kenshin.py | data/health/kenshin.json |
| 料理1人前の栄養（6品） | 日本食品標準成分表（八訂）増補2023年（文部科学省） | scripts/build_food.py | data/health/food.json |

- raw/ は /mnt/data/khealth/raw への symlink（git に入れない）。取り直すときは各スクリプトの冒頭に書いた URL から。
- NDB は10人未満を「‐」で伏せている。0として数え、その集計に approx（概算）を付ける。回答者100人未満は割合を出さない。
- 2024年度の保険者別は、2026-10-29 の訂正後のファイル（協会けんぽ20.5%・健保組合36.8%・共済37.1% が訂正の【正】と一致することを確かめた）。
- 料理の具材と量は当社の前提（food.json の note に書く）。大根おろしは汁ごと食べる前提なので「生」の値で計算する（成分表の「おろし」は汁を切った部分の値）。
- 話題を足すときは build_ndb.py の TOPICS に1件足す（質問票の番号と数える回答、または検査値の区分）。料理は build_food.py の DISHES に足す。

## 作り直しと公開

```bash
cd /home/kojima/work/khealth
.venv/bin/python scripts/build_ndb.py --copy
.venv/bin/python scripts/build_kenshin.py --copy
.venv/bin/python scripts/build_food.py --copy
cd ../xb4g/giin && /usr/bin/python3 scripts/make_ogp_health.py
set -a; . /home/kojima/work/aixec/.env; set +a
/usr/bin/python3 scripts/deploy.py --only lib/health_pages.php data/health $(ls img/og/health*.png)
```

確かめ方: `php ../../kseisakuflow/scripts/render_local.php /giin/health/alt`（警告が出ないか）、
`php -S 127.0.0.1:<18300番台の空き> ../../kseisakuflow/scripts/router_local.php` ＋ `check_width.py`（320/360/390 のはみ出し）。

## 出典

NDBオープンデータ・特定健康診査・特定保健指導の実施状況（厚生労働省）、日本食品標準成分表（八訂）増補2023年（文部科学省）。
ALT 30 の目安は日本肝臓学会「奈良宣言2023」（受診の目安で、診断の基準ではない）。
