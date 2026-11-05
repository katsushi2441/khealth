#!/usr/bin/env python3
"""Kurage 健康トラッカー（khealth）: 料理1人前の栄養を、日本食品標準成分表（八訂）増補2023年（文部科学省）から計算する。

入力: raw/mext/honpyo.xlsx（第2章 本表）
出力: data/health/food.json

具材と量は当社が置いた前提（料理ごとに note に書く）。市販品・店の料理の実際の栄養とは違う。
値は「100gあたりの成分値 × 量 ÷ 100」。可食部の重さで計算する（皮・骨などの廃棄は含めない）。
Tr（微量）は0、括弧つきの推定値はそのまま使う、「-」（未測定）は0として注記する。
使い方: .venv/bin/python scripts/build_food.py
"""
import json, os, re, shutil, sys, time
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'health')
SRC = {'title': '日本食品標準成分表（八訂）増補2023年（文部科学省）', 'url': 'https://www.mext.go.jp/a_menu/syokuhinseibun/mext_00001.html'}
COLS = {'kcal': 6, 'protein': 9, 'fat': 12, 'carb': 16, 'fiber': 18, 'salt': 60}   # PROT- / FAT- / 差引き法による利用可能炭水化物 / FIB- / NACL_EQ

# 料理: 尾形哲さん（@ogatas0520）が X で紹介した料理を、成分表の食品で組み立てたもの（具材と量は当社の前提）
DISHES = [
    {'slug': 'oden-onigiri', 'name': 'おでん（袋詰め）とおにぎり1個', 'short': 'おでん＋おにぎり',
     'note': 'おでんの具は大根・卵・ちくわ・こんにゃく・さつま揚げを1つずつとし、つゆは飲まない前提で入れていません。つゆを飲むと食塩はこれより多くなります。おにぎりは塩をふらないごはん100gと焼きのりで計算しています。',
     'items': [('06135', 100, '大根（ゆで）'), ('12005', 50, 'ゆで卵 1個'), ('10381', 30, 'ちくわ'), ('02003', 50, 'こんにゃく'),
               ('10386', 30, 'さつま揚げ'), ('01088', 100, 'ごはん（おにぎり1個）'), ('09004', 1, '焼きのり')]},
    {'slug': 'millefeuille-nabe', 'name': '白菜と豚肉のミルフィーユ鍋（1人前）', 'short': 'ミルフィーユ鍋',
     'note': '白菜200gと豚もも薄切り（脂身つき）80gで計算しています。鍋のつゆ・ポン酢などのたれは入れていません。豚ばら肉を使うと脂質とエネルギーが多くなります。',
     'items': [('06234', 200, '白菜（ゆで）'), ('11130', 80, '豚もも肉（脂身つき）')]},
    {'slug': 'hakusai-soup', 'name': '白菜とベーコンのスープ（1人前）', 'short': '白菜スープ',
     'note': '白菜150g・ベーコン20g・有塩バター5g・固形ブイヨン2.5g（1/2個の目安）で計算しています。',
     'items': [('06233', 150, '白菜'), ('11183', 20, 'ベーコン'), ('14017', 5, '有塩バター'), ('17027', 2.5, '固形ブイヨン')]},
    {'slug': 'kiriboshi-sunomono', 'name': '切り干し大根ときゅうりの酢の物（1人前）', 'short': '切り干し大根の酢の物',
     'note': '切り干し大根（乾燥）10g・きゅうり50g・穀物酢10g・上白糖3gで計算しています。',
     'items': [('06136', 10, '切り干し大根（乾）'), ('06065', 50, 'きゅうり'), ('17015', 10, '穀物酢'), ('03003', 3, '上白糖')]},
    {'slug': 'daikon-oroshi', 'name': '大根おろし（大根1/4本分・汁ごと）', 'short': '大根おろし',
     'note': '皮をむいた大根250g（1/4本ほど）をおろし、汁まで全部食べる前提で、生の大根として計算しています。成分表の「おろし」は汁を切った部分の値なので、汁ごと食べるときは生の大根の値と同じになります。',
     'items': [('06134', 250, '大根（皮なし・生、おろして汁ごと）')]},
    {'slug': 'nagaimo-kimchi', 'name': '長芋のキムチ和え（1人前）', 'short': '長芋のキムチ和え',
     'note': '長芋80g・白菜キムチ30gで計算しています。キムチは商品によって食塩の量が大きく違います。',
     'items': [('02023', 80, '長芋'), ('06236', 30, '白菜キムチ')]},
    {'slug': 'torimune-renji', 'name': '鶏むね肉のレンジ蒸し（皮なし・1人前）', 'short': '鶏むね肉のレンジ蒸し',
     'note': '鶏むね肉1枚（皮つき280g）を皮をとって2人で分ける前提で、皮なしの生の鶏むね肉125g・食塩1g（小さじ1/3の半分）・りょくとうもやし50g・こいくちしょうゆ6g（小さじ2の半分）・おろししょうが0.5gで計算しています。まぶす酒（大さじ3）と、たれのカンタン酢（市販品で成分表に無い）は入れていません。たれを全部かけると、糖質と食塩はこれより多くなります。',
     'items': [('11220', 125, '鶏むね肉（皮なし・生）'), ('17012', 1, '食塩'), ('06291', 50, 'もやし'), ('17007', 6, 'こいくちしょうゆ'), ('17069', 0.5, 'おろししょうが')]},
]


def val(x):
    """成分表の値を数にする。Tr は0、(1.2) は推定値として1.2、'-' と空は None。"""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace('(', '').replace(')', '')
    if s in ('Tr', 'tr', '0'):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def main():
    ws = openpyxl.load_workbook(os.path.join(ROOT, 'raw', 'mext', 'honpyo.xlsx'), read_only=True, data_only=True).worksheets[0]
    table = {}
    for r in ws.iter_rows(values_only=True, min_row=13):
        if r and r[1]:
            table[str(r[1]).strip()] = r
    out = []
    for d in DISHES:
        tot = {k: 0.0 for k in COLS}
        items, missing = [], set()
        for no, g, label in d['items']:
            r = table[no]
            row = {'no': no, 'label': label, 'food': re.sub(r'\s+', ' ', str(r[3]).replace('　', ' ')).strip(), 'g': g}
            for k, i in COLS.items():
                v = val(r[i])
                if v is None:
                    missing.add(k); v = 0.0
                row[k] = round(v * g / 100, 2)
                tot[k] += v * g / 100
            items.append(row)
        out.append({'slug': d['slug'], 'name': d['name'], 'short': d['short'], 'note': d['note'], 'items': items,
                    'total': {k: round(v, 1) for k, v in tot.items()}, 'missing': sorted(missing)})
        t = out[-1]['total']
        print(f"{d['short']:12} {t['kcal']:6.0f}kcal たんぱく質{t['protein']:5.1f}g 脂質{t['fat']:5.1f}g 炭水化物{t['carb']:5.1f}g 食物繊維{t['fiber']:4.1f}g 食塩{t['salt']:4.1f}g 欠け{sorted(missing)}")
    os.makedirs(OUT, exist_ok=True)
    json.dump({'generated_at': time.strftime('%Y-%m-%d'), 'source': SRC, 'dishes': out}, open(os.path.join(OUT, 'food.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
