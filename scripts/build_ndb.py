#!/usr/bin/env python3
"""Kurage 健康トラッカー（khealth）: NDB オープンデータ（特定健診の検査値・質問票）から、話題ごとの割合を作る。

入力: raw/ndb11/kensa/・raw/ndb11/monshin/（第11回 NDB オープンデータ。特定健診は2023年度分。厚生労働省）
出力: data/health/<話題>.json と data/health/index.json

割合 = その回答（または検査値の区分）の人数 ÷ その質問（検査）の回答者の合計。
10未満の箇所は「‐」で伏せられているので0として数え、その集計に approx（概算）の印を付ける。回答者100人未満の集計は割合を出さない（None）。
使い方: .venv/bin/python scripts/build_ndb.py
"""
import json, os, shutil, sys, time
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'ndb11')
OUT = os.path.join(ROOT, 'data', 'health')
AGES = ['40～44歳', '45～49歳', '50～54歳', '55～59歳', '60～64歳', '65～69歳', '70～74歳']
SRC_PAGE = 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00017.html'
SRC_TITLE = '第11回NDBオープンデータ（厚生労働省）特定健診 2023年度'

Q = lambda n: os.path.join(RAW, 'monshin', '08_特定健診_問診項目', f'標準的な質問票（質問項目{n}）　{{}}別性年齢階級別分布.xlsx')
K = lambda n: os.path.join(RAW, 'kensa', '07_特定健診_検査項目', f'{n}　{{}}別性年齢階級別分布.xlsx')

# 話題: hit は数える回答（検査値の区分）。男女で基準が違うもの（腹囲）は hit_m / hit_f
TOPICS = [
    {'slug': 'amai-nomimono', 'group': '食べ方', 'name': '間食や甘い飲み物を毎日とる人', 'short': '甘い飲み物・間食',
     'file': Q('１６'), 'hit': ['毎日'],
     'question': '朝昼夕の3食以外に間食や甘い飲み物を摂取していますか（毎日／時々／ほとんど摂取しない）',
     'lead': '特定健診の質問票で「朝昼夕の3食以外に間食や甘い飲み物を毎日とる」と答えた人の割合です。'},
    {'slug': 'yashoku', 'group': '食べ方', 'name': '寝る前2時間以内の夕食が週3回以上の人', 'short': '寝る前の夕食',
     'file': Q('１５'), 'hit': ['はい'],
     'question': '就寝前の2時間以内に夕食をとることが週に3回以上ある（はい／いいえ）',
     'lead': '特定健診の質問票で「就寝前の2時間以内に夕食をとることが週に3回以上ある」と答えた人の割合です。'},
    {'slug': 'choshoku-nuki', 'group': '食べ方', 'name': '朝食を週3回以上抜く人', 'short': '朝食を抜く',
     'file': Q('１７'), 'hit': ['はい'],
     'question': '朝食を抜くことが週に3回以上ある（はい／いいえ）',
     'lead': '特定健診の質問票で「朝食を抜くことが週に3回以上ある」と答えた人の割合です。'},
    {'slug': 'hayagui', 'group': '食べ方', 'name': '食べる速さが人より速い人', 'short': '早食い',
     'file': Q('１４'), 'hit': ['速い'],
     'question': '人と比較して食べる速度が速い（速い／ふつう／遅い）',
     'lead': '特定健診の質問票で、人と比べて食べる速さが「速い」と答えた人の割合です。'},
    {'slug': 'sake-mainichi', 'group': '食べ方', 'name': 'お酒を毎日飲む人', 'short': '毎日の飲酒',
     'file': Q('１８'), 'hit': ['毎日'],
     'question': 'お酒（日本酒、焼酎、ビール、洋酒など）を飲む頻度（毎日／時々／ほとんど飲まない（飲めない））',
     'lead': '特定健診の質問票で、お酒を「毎日」飲むと答えた人の割合です。'},
    {'slug': 'suimin', 'group': '睡眠と運動', 'name': '睡眠で休養が十分とれていない人', 'short': '睡眠',
     'file': Q('２０'), 'hit': ['いいえ'],
     'question': '睡眠で休養が十分とれている（はい／いいえ）',
     'lead': '特定健診の質問票で「睡眠で休養が十分とれている」に「いいえ」と答えた人の割合です。'},
    {'slug': 'undo', 'group': '睡眠と運動', 'name': '運動の習慣がない人', 'short': '運動の習慣',
     'file': Q('１０'), 'hit': ['いいえ'],
     'question': '1回30分以上の軽く汗をかく運動を週2日以上、1年以上実施している（はい／いいえ）',
     'lead': '特定健診の質問票で「1回30分以上の軽く汗をかく運動を週2日以上、1年以上している」に「いいえ」と答えた人の割合です。'},
    {'slug': 'taiju-zoka', 'group': '体の数値', 'name': '20歳のときから体重が10kg以上増えた人', 'short': '20歳からの体重増加',
     'file': Q('９'), 'hit': ['はい'],
     'question': '20歳の時の体重から10kg以上増加している（はい／いいえ）',
     'lead': '特定健診の質問票で「20歳の時の体重から10kg以上増加している」と答えた人の割合です。'},
    {'slug': 'alt', 'group': '体の数値', 'name': '健診でALT（肝臓の数値）が30を超えた人', 'short': 'ALT（肝臓）',
     'file': K('GPT（ALT）'), 'hit': ['31以上50以下', '51以上'],
     'question': 'GPT（ALT）の検査値の区分（30以下／31以上50以下／51以上・U/L）',
     'lead': '特定健診で、肝臓の数値のひとつ ALT（GPT）が 30 U/L を超えた人の割合です。日本肝臓学会の「奈良宣言2023」は、ALT が30を超えたらかかりつけ医を受診するよう呼びかけています（受診の目安で、診断の基準ではありません）。'},
    {'slug': 'fukui', 'group': '体の数値', 'name': '腹囲がメタボの基準を超えた人', 'short': '腹囲',
     'file': K('腹囲'), 'hit_m': ['90.0以上', '85.0以上90.0未満'], 'hit_f': ['90.0以上'],
     'question': '腹囲の区分（85.0未満／85.0以上90.0未満／90.0以上・cm）。男性85cm以上・女性90cm以上を数える',
     'lead': '特定健診で、腹囲が男性85cm以上・女性90cm以上（メタボリックシンドロームの判定に使う腹囲の基準）だった人の割合です。'},
    {'slug': 'bmi', 'group': '体の数値', 'name': 'BMIが25以上の人', 'short': 'BMI 25以上',
     'file': K('BMI'), 'hit': ['25.0以上30.0未満', '30.0以上35.0未満', '35.0以上40.0未満', '40.0以上'],
     'question': 'BMIの区分。25.0以上を数える（日本肥満学会の基準で肥満）',
     'lead': '特定健診で、BMI（体重kg÷身長mの2乗）が25以上だった人の割合です。日本肥満学会の基準では、BMI 25以上を肥満としています。'},
    {'slug': 'hba1c', 'group': '体の数値', 'name': 'HbA1cが6.5%以上の人', 'short': 'HbA1c（血糖）',
     'file': K('HbA1C'), 'hit': ['6.5以上8.0未満', '8.0以上8.4未満', '8.4以上'],
     'question': 'HbA1c（NGSP値・%）の区分。6.5以上を数える',
     'lead': '特定健診で、HbA1c（過去1〜2か月の血糖の平均を表す数値）が6.5%以上だった人の割合です。6.5%以上は、糖尿病が強く疑われる目安として使われます。'},
]


def num(v):
    if v is None or v == '' or (isinstance(v, str) and v.strip() in ('‐', '-', '－')):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def read(path, area):
    """{(pref, code, name): {answer: [M40..M70, M計, F40..F70, F計]}} を返す。"""
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    off = 4 if area else 2       # 数値の列の始まり（都道府県名・回答 / 都道府県名・番号・名前・回答）
    data, pref, code, name = {}, None, None, None
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i < 5:
            continue
        r = list(r)
        if r[0]:
            pref = str(r[0]).strip(); code = name = None
        if area:
            if r[1]: code = str(r[1]).strip()
            if r[2]: name = str(r[2]).strip()
        ans = r[off - 1]
        if ans is None:
            continue
        vals = [num(v) for v in r[off:off + 16]]
        data.setdefault((pref, code, name), {})[str(ans).strip()] = vals
    return data


def rate(ans, idx, hit, flags=None):
    """ans: {回答: vals}。idx: 列番号。10未満で伏せられた値は0として数え、flags に 'approx' を立てる（その地域は概算）。"""
    tot = 0; h = 0
    for a, v in ans.items():
        x = v[idx]
        if x is None:
            if flags is not None:
                flags.add('approx')
            x = 0
        tot += x
        if a in hit:
            h += x
    return (h / tot if tot >= 100 else None), tot   # 回答者100人未満は割合を出さない


def rates(ans, t):
    """全体・男・女・男女の年齢別の割合と人数。"""
    hm = t.get('hit_m', t.get('hit')); hf = t.get('hit_f', t.get('hit'))
    out = {}; fl = set()
    m, nm = rate(ans, 7, hm, fl); f, nf = rate(ans, 15, hf, fl)
    out['approx'] = 'approx' in fl
    out['m'], out['f'], out['n_m'], out['n_f'] = m, f, nm, nf
    if m is not None and f is not None:
        hits = sum(v[7] or 0 for a, v in ans.items() if a in hm) + sum(v[15] or 0 for a, v in ans.items() if a in hf)
        out['all'] = hits / (nm + nf); out['n'] = nm + nf
    else:
        out['all'] = None; out['n'] = None
    out['age_m'] = [rate(ans, i, hm)[0] for i in range(7)]
    out['age_f'] = [rate(ans, 8 + i, hf)[0] for i in range(7)]
    return out


def add(a, b):
    """全国の合計用: 回答ごとの人数を足す（伏せ字は0として足し、全国値では誤差が小さいので注記する）。"""
    for k, v in b.items():
        cur = a.setdefault(k, [0] * 16)
        for i, x in enumerate(v):
            cur[i] += x or 0


def r4(x):
    return None if x is None else round(x, 4)


def clean(d):
    return {k: (r4(v) if isinstance(v, float) else ([r4(x) for x in v] if isinstance(v, list) else v)) for k, v in d.items()}


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for t in TOPICS:
        pref = read(t['file'].format('都道府県'), False)
        area = read(t['file'].format('二次医療圏'), True)
        nat = {}
        for k, ans in pref.items():
            add(nat, ans)
        national = clean(rates(nat, t))
        prefs = []
        for (p, _, _), ans in pref.items():
            if '判別不可' in p or '不明' in p:
                continue
            prefs.append({'pref': p, **clean(rates(ans, t))})
        areas = []
        for (p, code, name), ans in area.items():
            if '判別不可' in p or not code:
                continue
            areas.append({'pref': p, 'code': code, 'name': name, **clean(rates(ans, t))})
        ranked = sorted([x for x in prefs if x['all'] is not None], key=lambda x: -x['all'])
        for i, x in enumerate(ranked):
            x['rank'] = i + 1
        d = {'slug': t['slug'], 'group': t['group'], 'name': t['name'], 'short': t['short'], 'question': t['question'], 'lead': t['lead'],
             'year': '2023年度', 'source': {'title': SRC_TITLE, 'url': SRC_PAGE}, 'generated_at': time.strftime('%Y-%m-%d'),
             'ages': AGES, 'national': national, 'prefs': prefs, 'areas': areas,
             'top': [x['pref'] for x in ranked[:3]], 'bottom': [x['pref'] for x in ranked[-3:]]}
        json.dump(d, open(os.path.join(OUT, t['slug'] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        index.append({k: d[k] for k in ('slug', 'group', 'name', 'short', 'year')} | {'all': national['all'], 'm': national['m'], 'f': national['f'],
                     'top': d['top'], 'bottom': d['bottom'], 'max': ranked[0]['all'] if ranked else None, 'min': ranked[-1]['all'] if ranked else None})
        print(f"{t['slug']:15} 全国 {national['all']:.1%}  男 {national['m']:.1%}  女 {national['f']:.1%}  都道府県 {len(prefs)}  二次医療圏 {len(areas)}（割合あり {sum(a['all'] is not None for a in areas)}）  上位 {d['top']}")
    ip = os.path.join(OUT, 'index.json')
    ix = json.load(open(ip, encoding='utf-8')) if os.path.exists(ip) else {}
    ix['topics'] = index
    ix['generated_at'] = time.strftime('%Y-%m-%d')
    json.dump(ix, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
