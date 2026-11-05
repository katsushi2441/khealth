#!/usr/bin/env python3
"""Kurage 健康トラッカー（khealth）: 特定健診・特定保健指導の実施状況（保険者別・厚生労働省）を年度ごとにつなぐ。

入力: raw/hokensha/<年度>.xlsx（2018〜2024年度。2024年度は2026-10-29の訂正後のファイル）
出力: data/health/kenshin.json（--copy で xb4g/giin/data/health/ へ写す）

実施率は表の値をそのまま使わず、受診者数÷対象者数・終了者数÷対象者数で計算し直す（表の値と同じになることを確かめてある）。
「-」は公表されていない値。
使い方: .venv/bin/python scripts/build_kenshin.py [--copy]
"""
import json, os, shutil, sys, time
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'hokensha')
OUT = os.path.join(ROOT, 'data', 'health')
XB4G = '/home/kojima/work/xb4g/giin/data/health'
YEARS = ['2018', '2019', '2020', '2021', '2022', '2023', '2024']
SRC = {
    '2024': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_00082.html',
    '2023': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_00063.html',
    '2022': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_00045.html',
    '2021': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_00043.html',
    '2020': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/newpage_25882.html',
    '2019': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000173202_00008.html',
    '2018': 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000173202_00006.html',
}
PREFS = ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県', '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
         '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
         '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
         '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']


def kind_of(title):
    if '国民健康保険組合' in title:
        return 'kokuho-kumiai'
    if '国民健康保険' in title or '市町村国保' in title:
        return 'kokuho'
    if '健康保険組合' in title:
        return 'kenpo'
    if '共済' in title:
        return 'kyosai'
    if '協会' in title:
        return 'kyokai'
    if '船員' in title:
        return 'senin'
    return None


KIND_NAME = {'kokuho': '市町村国保', 'kokuho-kumiai': '国民健康保険組合', 'kenpo': '健康保険組合', 'kyosai': '共済組合', 'kyokai': '全国健康保険協会', 'senin': '船員保険'}


def n(x):
    if isinstance(x, (int, float)):
        return int(x)
    return None


def main():
    ins = {}
    for y in YEARS:
        wb = openpyxl.load_workbook(os.path.join(RAW, y + '.xlsx'), read_only=True, data_only=True)
        for ws in wb.worksheets:
            k = kind_of(ws.title)
            if not k:
                continue
            for r in ws.iter_rows(values_only=True, min_row=5):
                if not r or not isinstance(r[0], str) or not r[0].strip().isdigit():
                    continue
                no = r[0].strip().zfill(8)
                a, b, c, d = n(r[2]), n(r[3]), n(r[5]), n(r[6])
                e = ins.setdefault(no, {'no': no, 'kind': k, 'name': str(r[1]).strip(), 'years': {}})
                e['name'] = str(r[1]).strip()            # 新しい年度の名前で上書き（合併などで変わる）
                e['years'][y] = [a, b, c, d]
    for e in ins.values():
        pc = int(e['no'][2:4]) if e['kind'] in ('kokuho', 'kenpo', 'kokuho-kumiai') else 0
        e['pref'] = PREFS[pc - 1] if 1 <= pc <= 47 else ''
        e['short'] = e['name'].replace('（国民健康保険）', '')
    # 種類ごと・都道府県ごとの合計（市町村国保）
    tot = {}
    for e in ins.values():
        for y, (a, b, c, d) in e['years'].items():
            for key in (e['kind'], e['kind'] + '|' + e['pref']):
                t = tot.setdefault(key, {}).setdefault(y, [0, 0, 0, 0])
                for i, v in enumerate((a, b, c, d)):
                    t[i] += v or 0
    out = {'generated_at': time.strftime('%Y-%m-%d'), 'years': YEARS, 'sources': SRC, 'kind_name': KIND_NAME, 'prefs': PREFS,
           'note': '2024年度は2026年10月29日の訂正後の公表資料による。',
           'totals': tot, 'insurers': sorted(ins.values(), key=lambda e: (e['kind'], e['no']))}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'kenshin.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    for k in KIND_NAME:
        t = tot.get(k, {}).get('2024')
        if t:
            print(f"{KIND_NAME[k]:10} 保険者 {sum(1 for e in ins.values() if e['kind'] == k and '2024' in e['years']):5}  受診率 {t[1]/t[0]:.1%}  保健指導 {t[3]/t[2]:.1%}")
    nk = [e for e in ins.values() if e['kind'] == 'kokuho' and '2024' in e['years']]
    print('市町村国保で都道府県が空:', sum(1 for e in nk if not e['pref']))
    if '--copy' in sys.argv:
        os.makedirs(XB4G, exist_ok=True)
        shutil.copy(os.path.join(OUT, 'kenshin.json'), os.path.join(XB4G, 'kenshin.json'))
        print('copied')


if __name__ == '__main__':
    main()
