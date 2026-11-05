#!/usr/bin/env python3
"""Kurage 健康トラッカー（khealth）の静的なページ一式を out/health/ に作る。公開先は https://exbridge.jp/health/ （scripts/deploy.py）。

入力: data/health/*.json（build_ndb.py・build_kenshin.py・build_food.py が書く）と out/health/og/*.png（make_ogp.py）
ページ: /health/ ・/health/<話題>/ ・/health/kenshin/ ・/health/kenshin/kumiai/ ・/health/kenshin/<保険者番号>/ ・/health/food/ ・/health/food/<料理>/ ・sitemap.xml

**しないこと**: 医療の助言・診断、因果の主張（地域の差は相関まで）、保険者や自治体の良し悪しの判定。すべての数字に出典を付ける。
使い方: /usr/bin/python3 scripts/build_site.py
"""
import hashlib, html, json, pathlib, shutil, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'health'
OUT = ROOT / 'out' / 'health'
BASE = 'https://exbridge.jp/health/'
SITE = 'Kurage 健康トラッカー'
LOGO = 'https://exbridge.jp/images/logo-mark-128.png'
MASCOT_SRC = pathlib.Path('/home/kojima/work/kurage_web/images/kurage-mascot-cutout-300.webp')
DIET_TRACKER = 'https://xb4g.com/giin/tracker/tokutei-kenshin'
NDB_URL = 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00017.html'
KENSHIN_URL = 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000161103.html'
MEXT_URL = 'https://www.mext.go.jp/a_menu/syokuhinseibun/mext_00001.html'
TODAY = time.strftime('%Y-%m-%d')
# 題名は全角32字以内・検索で使われる語を先頭に（research/kw-2026-11-05.tsv の実測: 脂肪肝74,000・肝臓 数値22,200・睡眠不足14,800・メタボ 腹囲12,100・特定健診9,900・特定保健指導8,100・おでん カロリー5,400・間食5,400・bmi 25 4,400）
SEO_TITLE = {
    'alt': '肝臓の数値ALTが30超えの割合｜脂肪肝の目安を都道府県別に',
    'fukui': 'メタボの腹囲の基準を超えた人の割合｜都道府県・年齢別',
    'bmi': 'BMI25以上（肥満）の人の割合｜都道府県・地域・年齢別',
    'hba1c': 'HbA1c6.5%以上の人の割合｜都道府県・地域・年齢別',
    'amai-nomimono': '間食・甘い飲み物を毎日とる人の割合｜都道府県別',
    'yashoku': '夜遅い夕食（寝る前2時間以内）の割合｜都道府県別',
    'choshoku-nuki': '朝食を抜く人の割合｜都道府県・地域・年齢別',
    'hayagui': '早食いの人の割合｜都道府県・地域・年齢別',
    'sake-mainichi': 'お酒を毎日飲む人の割合｜都道府県・地域・年齢別',
    'suimin': '睡眠不足（休養がとれない）人の割合｜都道府県別',
    'undo': '運動不足（運動習慣なし）の人の割合｜都道府県別',
    'taiju-zoka': '20歳から10kg以上太った人の割合｜都道府県別',
}
FOOD_TITLE = {
    'oden-onigiri': 'おでんのカロリーと栄養｜おにぎり1個つき',
    'millefeuille-nabe': 'ミルフィーユ鍋のカロリーと栄養｜白菜と豚肉',
    'hakusai-soup': '白菜スープのカロリーと栄養｜ベーコン入り',
    'kiriboshi-sunomono': '切り干し大根の酢の物のカロリーと栄養',
    'daikon-oroshi': '大根おろしのカロリーと栄養｜汁ごと1/4本',
    'nagaimo-kimchi': '長芋キムチのカロリーと栄養｜長芋のキムチ和え',
}
# AEO: 話題ごとに「なぜこの数字を見るのか」を1文（事実だけ。原因の主張はしない）
WHY = {
    'alt': 'ALTは肝臓の細胞に多い酵素で、肝臓に脂肪がたまる脂肪肝などで高くなります。日本肝臓学会の「奈良宣言2023」は、健診でALTが30を超えたらかかりつけ医の受診を呼びかけています。',
    'fukui': '特定健診では、腹囲が男性85cm以上・女性90cm以上を、メタボリックシンドロームの判定の最初の目安にしています。',
    'bmi': 'BMIは体重(kg)÷身長(m)の2乗で、日本肥満学会の基準では25以上を肥満としています。',
    'hba1c': 'HbA1cは過去1〜2か月の血糖の平均を表す数値で、6.5%以上は糖尿病が強く疑われる目安として使われます。',
}
e = html.escape

CSS = """
:root{--ink:#12202f;--sub:#5d6b7a;--line:#e3e9ec;--g:#2e7d32;--gD:#1b5e20;--gL:#43a047;--mint:#e8f5e9;--bg:#f6f9f6;--amber:#f59e0b}
*{box-sizing:border-box}html,body{overflow-x:hidden;max-width:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,-apple-system,sans-serif;line-height:1.8}
img{max-width:100%;height:auto}a{color:var(--gD)}
header.site{background:#fff;border-bottom:1px solid var(--line)}
header.site .in{max-width:960px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
header.site a.brand{display:flex;align-items:center;gap:8px;color:var(--ink);text-decoration:none;font-weight:800;min-width:0}
header.site .brand img{object-fit:contain;flex:none}header.site a.brand.logo{margin-right:-2px}
header.site .brand span{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
header.site nav{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
header.site nav a{border:1px solid #c9d3dc;border-radius:999px;padding:5px 12px;color:#12202f;text-decoration:none;font-size:13px;font-weight:700;white-space:nowrap;background:#fff}
header.site nav a.it{background:#1d4f7a;border-color:#1d4f7a;color:#fff}
header.site nav a.sns{background:#0a8a80;border-color:#0a8a80;color:#fff;font-weight:800}
@media (max-width:560px){header.site nav{margin-left:0;width:100%}header.site nav a{padding:4px 10px;font-size:12px}}
main{max-width:960px;margin:0 auto;padding:0 16px 48px}
.crumb{font-size:12.5px;color:var(--sub);margin:12px 0 0;overflow-wrap:anywhere}.crumb a{color:var(--sub)}
.hero{background:linear-gradient(135deg,#f1f8f1 0%,#dcefdc 55%,#c3e3c4 100%);border:1px solid var(--line);border-radius:18px;padding:18px;margin-top:12px}
.hero .kick{margin:0;color:var(--gD);font-weight:800;font-size:13px;letter-spacing:.04em}
.hero h1{font-size:clamp(22px,4.8vw,30px);line-height:1.4;margin:4px 0 6px;overflow-wrap:anywhere}
.hero p.lead{margin:0;font-size:15px}
.big{font-size:44px;font-weight:900;line-height:1.1;color:var(--gD);margin:6px 0}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:10px;margin-top:10px}
.kv>div{background:#fff;border-radius:14px;padding:10px 14px;min-width:0}.kv b{display:block;font-size:26px;color:var(--gD);line-height:1.3}.kv span{font-size:13px;color:var(--sub)}
.share{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}
.share button,.share a{border-radius:999px;padding:7px 16px;font-weight:800;font-size:14px;cursor:pointer;font-family:inherit;text-decoration:none}
.share .bx{background:#0f1419;color:#fff;border:0}.share .bc{background:#fff;color:var(--gD);border:2px solid var(--g)}
section{margin-top:30px}h2{font-size:20px;margin:0 0 10px;padding-left:12px;border-left:5px solid var(--g);line-height:1.5}
h3{font-size:16px;margin:16px 0 6px}
.note{color:var(--sub);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:10px}
.tp{display:block;background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 14px;text-decoration:none;color:var(--ink);min-width:0;box-shadow:0 1px 2px rgba(18,32,47,.04)}
.tp:hover{border-color:var(--g)}.tp b{display:block;line-height:1.5;overflow-wrap:anywhere}.tp .v{font-size:26px;font-weight:900;color:var(--gD)}.tp small{display:block;color:var(--sub);font-size:13px;overflow-wrap:anywhere}
.bar{display:grid;grid-template-columns:minmax(5.5em,max-content) 1fr minmax(3.6em,max-content);gap:6px 10px;align-items:center;margin:4px 0}
.bar .l{font-size:14px;overflow-wrap:anywhere}.bar .t{height:14px;background:#e9efe9;border-radius:7px;overflow:hidden}.bar .t i{display:block;height:100%;background:var(--gL);border-radius:7px}
.bar .t i.f{background:#ef6c00}.bar .n{font-size:14px;font-weight:700;text-align:right}
.leg{display:flex;gap:14px;font-size:13px;color:var(--sub);margin:4px 0 8px}.leg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.warn{background:#fff8e6;border:1px solid #f0d58a;border-radius:12px;padding:10px 14px;font-size:14px;margin-top:16px}
details.fd{background:#fff;border:1px solid var(--line);border-radius:12px;padding:8px 12px;margin:8px 0}details.fd summary{cursor:pointer;font-weight:700}
.list{list-style:none;padding:0;margin:0}.list li{border-top:1px solid var(--line);padding:8px 0;overflow-wrap:anywhere}.list li:first-child{border-top:0}
table.t{width:100%;border-collapse:collapse;font-size:14px;background:#fff;border-radius:12px;overflow:hidden}table.t th,table.t td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:right}table.t th:first-child,table.t td:first-child{text-align:left}
.src{font-size:12.5px;color:var(--sub);margin:6px 0 0;overflow-wrap:anywhere}
#q{width:100%;max-width:520px;font-size:16px;padding:10px 12px;border:1px solid #c9d3dc;border-radius:8px}
.faq details{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin-bottom:8px}.faq summary{font-weight:800;cursor:pointer}.faq p{margin:8px 0 0}
.about{background:#fff;border:1px dashed #c9d3dc;border-radius:14px;padding:12px 16px;font-size:13.5px;color:var(--sub)}
.about ul{margin:0;padding-left:18px}
footer{max-width:960px;margin:0 auto;padding:18px 16px 40px;color:var(--sub);font-size:13px}
"""

CSS_V = hashlib.md5(CSS.encode()).hexdigest()[:8]
TRACK = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-BP0650KDFR"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-BP0650KDFR');</script>
<script>(function(){var s=new Image();s.src='/simpletrack.php?url='+encodeURIComponent(location.href)+'&ref='+encodeURIComponent(document.referrer);})();</script>"""

COPY_JS = """<script>document.addEventListener('click',function(ev){var b=ev.target.closest('[data-copy]');if(!b)return;
navigator.clipboard.writeText(b.dataset.copy).then(function(){var t=b.textContent;b.textContent='コピーしました';setTimeout(function(){b.textContent=t},1600);});});</script>"""


def pct(x, d=1):
    return '—' if x is None else f'{x * 100:.{d}f}%'


def og_url(name):
    f = OUT / 'og' / f'{name}.png'
    v = hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.exists() else '0'
    return f'{BASE}og/{name}.png?v={v}'


def head(title, desc, path, og, ld, ref='health'):
    url = BASE + path
    graph = [{'@type': 'WebSite', '@id': BASE + '#site', 'name': SITE, 'url': BASE, 'inLanguage': 'ja', 'publisher': {'@id': 'https://exbridge.jp/#org'}},
             {'@type': 'Organization', '@id': 'https://exbridge.jp/#org', 'name': '株式会社エクスブリッジ', 'url': 'https://exbridge.jp/', 'logo': LOGO},
             {'@type': 'WebPage', 'name': title, 'url': url, 'description': desc, 'isPartOf': {'@id': BASE + '#site'}, 'dateModified': TODAY, 'inLanguage': 'ja',
              'primaryImageOfPage': og.split('?')[0]},
             {'@type': 'BreadcrumbList', 'itemListElement': ld.pop('crumbs')}] + ld.get('more', [])
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE}"><meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og}">
<link rel="icon" href="{LOGO}">
<script type="application/ld+json">{json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)}</script>
{TRACK}
<link rel="stylesheet" href="{BASE}assets/health.css?v={CSS_V}"></head><body>
<header class="site"><div class="in"><a class="brand logo" href="https://exbridge.jp/#ref={ref}-head-logo" title="株式会社エクスブリッジ（exbridge.jp）"><img src="{LOGO}" width="30" height="30" alt="株式会社エクスブリッジ"></a><a class="brand" href="{BASE}"><img src="{BASE}assets/mascot.webp" width="30" height="30" alt="Kurage"><span>{SITE}</span></a><nav aria-label="導入と相談"><a href="https://kappstore.exbridge.jp/#ref={ref}-head-store">Kurage App Store</a><a href="https://kurage.exbridge.jp/reseller.html#ref={ref}-head-reseller">代理店募集</a><a class="it" href="https://exbridge.jp/ai-it-komon.html#ref={ref}-head-komon">AI-IT顧問</a><a class="sns" href="https://exbridge.jp/ai-sns-komon.html#ref={ref}-head-sns-komon">AI-SNS顧問</a></nav></div></header><main>"""


def crumbs(items):
    """items: [(名前, path)]。最後は今のページ。"""
    h = f'<nav class="crumb"><a href="{BASE}">{SITE}</a>'
    for i, (nm, p) in enumerate(items):
        h += ' › ' + (f'<a href="{BASE}{p}">{e(nm)}</a>' if i < len(items) - 1 else e(nm))
    return h + '</nav>'


def ld_crumbs(items):
    lst = [{'@type': 'ListItem', 'position': 1, 'name': SITE, 'item': BASE}]
    for i, (nm, p) in enumerate(items):
        lst.append({'@type': 'ListItem', 'position': i + 2, 'name': nm, 'item': BASE + p})
    return lst


def share(text, path):
    url = BASE + path
    full = f'{text}\n{url}'
    intent = 'https://x.com/intent/post?text=' + urllib.parse.quote(full)
    return (f'<div class="share"><a class="bx" href="{intent}" target="_blank" rel="noopener">Xで共有</a>'
            f'<button class="bc" type="button" data-copy="{e(full)}">タイトルとURLをコピー</button></div>')


def src(title, url, extra=''):
    return f'<p class="src">出典：<a href="{url}" rel="noopener" target="_blank">{e(title)}</a>{("　" + e(extra)) if extra else ""}</p>'


def bar(label, v, mx, cls=''):
    w = 0 if (v is None or mx <= 0) else min(100, v / mx * 100)
    return f'<div class="bar"><span class="l">{e(label)}</span><span class="t"><i class="{cls}" style="width:{w:.1f}%"></i></span><span class="n">{pct(v)}</span></div>'


WARN = ('<div class="warn">公的データの数字を並べたものです。医療の助言や診断ではありません。地域や年齢による差は、食べ方や体の数値が「一緒に多い・少ない」ことを示すだけで、'
        'どちらが原因かは言えません。気になる数値がある方は、かかりつけ医や健診の機関に相談してください。</div>')

ABOUT = f"""<section><h2>出典と作り方</h2><div class="about"><ul>
<li>食べ方・睡眠・運動・健診の検査値：<a href="{NDB_URL}" rel="noopener" target="_blank">第11回NDBオープンデータ</a>（厚生労働省）の特定健診（2023年度）の「標準的な質問票」と「検査項目」の都道府県別・二次医療圏別・性年齢階級別の分布を加工して作成。対象は特定健診を受けた40〜74歳です。</li>
<li>割合は、その回答（検査値の区分）の人数を、その質問（検査）の回答者の合計で割ったものです。10人未満で伏せられた箇所は0として数えています（その地域には「概算」と書きます）。回答者100人未満の集計は割合を出していません。</li>
<li>健診のあとの保健指導：<a href="{KENSHIN_URL}" rel="noopener" target="_blank">特定健康診査・特定保健指導の実施状況（保険者別）</a>（厚生労働省、2018〜2024年度。2024年度は2026年10月29日の訂正後）。</li>
<li>料理の栄養：<a href="{MEXT_URL}" rel="noopener" target="_blank">日本食品標準成分表（八訂）増補2023年</a>（文部科学省）の100gあたりの値に、当社が置いた具材の量をかけて足したもの。</li>
<li>誤りに気づいたら <a href="https://exbridge.jp/contact.php?subject=health">お問い合わせ</a> からお知らせください。すぐに直します。</li>
</ul></div></section>"""


def foot():
    return f"""</main><footer>{SITE}は、食べ方・睡眠・健診の数値と、健診のあとの保健指導、料理の栄養を、公的データだけで並べる株式会社エクスブリッジのシステムです。医療の助言ではありません。<br>
<a href="https://exbridge.jp/profile.html#ref=exb-about-health">株式会社エクスブリッジ</a>（EXBRIDGE, Inc.／法人番号 4180001056508）　愛知県名古屋市瑞穂区内浜町34-9 305　2004年4月設立　資本金1億250万円　代表取締役 小嶋 篤<br>© 株式会社エクスブリッジ</footer>{COPY_JS}</body></html>"""


def write(path, body):
    p = OUT / path / 'index.html' if path else OUT / 'index.html'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding='utf-8')


def kr(v, i):
    if not v:
        return None
    a, b, c, d = v
    if i == 0:
        return b / a if a and b is not None else None
    return d / c if c and d is not None else None


def diet_link():
    return (f'<div class="grid"><a class="tp" href="{DIET_TRACKER}#ref=health-diet"><b>国会では：特定健診と生活習慣病の予防</b>'
            '<small>健診のあとの保健指導や生活習慣病の予防を、国会でだれが問い、政府がどう答えてきたか（Kurage 国会トラッカー）</small></a></div>')


# ---------------------------------------------------------------- ページ
def page_index(ix, kenshin, food):
    desc = '食べ方・睡眠・運動と、健診のALT（肝臓）・腹囲・BMI・HbA1cを、都道府県と二次医療圏ごとに。健診のあとの保健指導の実施率を市町村と保険者ごとに。料理1人前の栄養も。すべて公的データと出典つきで並べます。'
    title = '脂肪肝・メタボ・睡眠不足の割合｜Kurage 健康トラッカー'
    h = head(title, desc, '', og_url('index'), {'crumbs': ld_crumbs([]), 'more': [{'@type': 'Dataset', 'name': SITE, 'description': desc, 'url': BASE, 'inLanguage': 'ja',
             'creator': {'@type': 'Organization', 'name': '株式会社エクスブリッジ'}, 'isBasedOn': [NDB_URL, KENSHIN_URL, MEXT_URL]}]})
    h += f'<section class="hero" style="margin-top:14px"><p class="kick">HEALTH TRACKER</p><h1>{SITE}</h1><p class="lead">{e(desc)}</p></section>'
    h += share(f'【{SITE}】食べ方・睡眠・運動と健診の数値を、都道府県と地域ごとに公的データで', '')
    groups = {}
    for t in ix['topics']:
        groups.setdefault(t['group'], []).append(t)
    for g, lst in groups.items():
        h += f'<section><h2>{e(g)}</h2><div class="grid">'
        for t in lst:
            h += (f'<a class="tp" href="{BASE}{t["slug"]}/"><b>{e(t["name"])}</b><span class="v">{pct(t["all"])}</span>'
                  f'<small>全国（{e(t["year"])}・40〜74歳）　男 {pct(t["m"])}・女 {pct(t["f"])}<br>高い県：{e("・".join(t["top"]))}</small></a>')
        h += '</div></section>'
    t = kenshin['totals']['kokuho']['2024']
    h += (f'<section><h2>健診のあと</h2><div class="grid"><a class="tp" href="{BASE}kenshin/"><b>健診のあとの保健指導（市町村・会社の健康保険ごと）</b><span class="v">{pct(kr(t, 1))}</span>'
          '<small>市町村国保で、保健指導の対象になった人のうち指導を終えた人（2024年度）。1,700を超える市町村と、会社の健康保険組合ごとに、2018年度からの推移を見られます。</small></a></div></section>')
    h += '<section><h2>料理1人前の栄養</h2><div class="grid">'
    for d in food['dishes']:
        tt = d['total']
        h += f'<a class="tp" href="{BASE}food/{d["slug"]}/"><b>{e(d["name"])}</b><small>{tt["kcal"]:.0f}kcal・たんぱく質 {tt["protein"]}g・食物繊維 {tt["fiber"]}g・食塩 {tt["salt"]}g</small></a>'
    h += '</div></section>'
    alt = next(t for t in ix['topics'] if t['slug'] == 'alt')
    xfaq = [('Kurage 健康トラッカーで何がわかりますか？', '特定健診を受けた40〜74歳の、食べ方・睡眠・運動の習慣と、ALT（肝臓）・腹囲・BMI・HbA1cの割合を、全国・都道府県・二次医療圏・性別と年齢ごとに見られます。健診のあとの保健指導の実施率を市町村と保険者ごとに、料理1人前の栄養も見られます。'),
            ('データの出典は？', '厚生労働省のNDBオープンデータ（特定健診 2023年度）と特定健康診査・特定保健指導の実施状況（保険者別）、文部科学省の日本食品標準成分表（八訂）増補2023年です。'),
            ('健診で肝臓の数値（ALT）が30を超えた人はどれくらい？', f'2023年度の特定健診では全国で{pct(alt["all"])}（男性{pct(alt["m"])}・女性{pct(alt["f"])}）です。')]
    h = h.replace('"@graph": [', '"@graph": [' + json.dumps({'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in xfaq]}, ensure_ascii=False) + ', ', 1)
    h += '<section><h2>国会では</h2>' + diet_link() + '</section>'
    h += '<section class="faq"><h2>よくある質問</h2>' + ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in xfaq) + '</section>'
    h += WARN + ABOUT + foot()
    write('', h)


def page_topic(d, ix):
    n = d['national']; slug = d['slug']
    prefs = sorted(d['prefs'], key=lambda p: -(p['all'] or -1))
    top, bot = prefs[0], prefs[-1]
    title = SEO_TITLE.get(slug, f'{d["name"]}の割合｜都道府県・地域・年齢別')
    desc = f'{d["name"]}は全国で{pct(n["all"])}（男 {pct(n["m"])}・女 {pct(n["f"])}、{d["year"]}の特定健診・40〜74歳）。都道府県・二次医療圏・性別と年齢ごとの割合を、NDBオープンデータから出典つきで並べます。'
    kind = '検査値' if '区分' in d['question'] else '質問票'
    if slug in WHY:
        faq_extra = [(f'{d["short"]}は何を表す数値ですか？', WHY[slug])]
    else:
        faq_extra = []
    faq = faq_extra + [(f'{d["name"]}は全国でどれくらいですか？', f'{d["year"]}に特定健診を受けた40〜74歳のうち {pct(n["all"])}です。男性は {pct(n["m"])}、女性は {pct(n["f"])}です（NDBオープンデータ）。'),
           (f'{d["name"]}の割合がいちばん高い都道府県は？', f'{top["pref"]}の {pct(top["all"])}です。いちばん低いのは{bot["pref"]}の {pct(bot["all"])}です。年齢の構成の違いは調整していません。'),
           ('この数字はどうやって数えていますか？', f'特定健診の{kind}（{d["question"]}）で、該当する人の数を回答者の合計で割っています。')]
    h = head(title, desc, slug + '/', og_url(slug), {'crumbs': ld_crumbs([(d['short'], slug + '/')]), 'more': [
        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]},
        {'@type': 'Dataset', 'name': title, 'description': desc, 'url': BASE + slug + '/', 'inLanguage': 'ja', 'dateModified': d['generated_at'],
         'temporalCoverage': '2023', 'spatialCoverage': {'@type': 'Place', 'name': '日本（47都道府県・335の二次医療圏）'},
         'variableMeasured': d['name'], 'creator': {'@id': 'https://exbridge.jp/#org'}, 'isBasedOn': [NDB_URL]}]}, f'health-{slug}')
    h += crumbs([(d['short'], slug + '/')])
    h += (f'<section class="hero"><p class="kick">{e(d["group"])}</p><h1>{e(d["name"])}</h1><div class="big">{pct(n["all"])}</div>'
          f'<p class="lead">全国（{e(d["year"])}の特定健診・40〜74歳）。男性 {pct(n["m"])}・女性 {pct(n["f"])}</p></section>')
    h += share(f'【{SITE}】{d["name"]}は全国で{pct(n["all"])}。都道府県・地域・年齢ごとの割合', slug + '/')
    # 要点（答えを先に。AI検索や強調スニペットが引ける1段落）
    age_m = [v for v in n['age_m'] if v is not None]
    peak = d['ages'][n['age_m'].index(max(age_m))] if age_m else ''
    h += (f'<section style="margin-top:16px"><h2>要点</h2><p class="about" style="font-size:15px;color:var(--ink)">{e(d["year"])}の特定健診（40〜74歳）で、{e(d["name"])}は全国で{pct(n["all"])}でした。'
          f'男性は{pct(n["m"])}、女性は{pct(n["f"])}です。都道府県では{e(top["pref"])}（{pct(top["all"])}）が最も高く、{e(bot["pref"])}（{pct(bot["all"])}）が最も低くなっています。'
          f'{("男性では" + e(peak) + "が最も高い年代です。") if peak else ""}出典は厚生労働省のNDBオープンデータです。</p></section>')
    if slug in WHY:
        h += f'<p>{e(WHY[slug])}</p>'
    h += f'<p>{e(d["lead"])}</p>'
    mx = max([v for v in n['age_m'] + n['age_f'] if v is not None] or [0])
    h += '<section><h2>男女と年齢で見る</h2><div class="leg"><span><i style="background:#43a047"></i>男性</span><span><i style="background:#ef6c00"></i>女性</span></div>'
    for i, a in enumerate(d['ages']):
        h += bar('男 ' + a, n['age_m'][i], mx) + bar('女 ' + a, n['age_f'][i], mx, 'f')
    h += src(d['source']['title'], d['source']['url'], '性・年齢階級別分布') + '</section>'
    h += '<section id="prefs"><h2>都道府県で見る</h2><p class="note">割合の高い順。年齢の構成の違い（高齢の人が多い県など）は調整していません。比べるときは、上の年齢別の差も合わせて見てください。</p>'
    for p in prefs:
        h += bar(f'{p.get("rank", "")}. {p["pref"]}', p['all'], top['all'])
    h += src(d['source']['title'], d['source']['url'], '都道府県別性年齢階級別分布') + '</section>'
    by = {}
    for a in d['areas']:
        by.setdefault(a['pref'], []).append(a)
    h += f'<section id="areas"><h2>地域（二次医療圏）で見る</h2><p class="note">二次医療圏は、入院医療を完結させる単位として都道府県が決めた地域です（全国で{len(d["areas"])}）。都道府県を開くと、地域ごとの割合が出ます。</p>'
    for p in prefs:
        lst = by.get(p['pref'], [])
        if not lst:
            continue
        amx = max([a['all'] or 0 for a in lst] + [p['all'] or 0])
        h += f'<details class="fd"><summary>{e(p["pref"])}　<span class="note">{len(lst)}地域・県全体 {pct(p["all"])}</span></summary>'
        for a in lst:
            h += bar(a['name'] + ('（概算）' if a.get('approx') else ''), a['all'], amx)
        h += '</details>'
    h += src(d['source']['title'], d['source']['url'], '二次医療圏別性年齢階級別分布') + '</section>'
    h += '<section><h2>ほかの話題</h2><div class="grid">'
    for t in ix['topics']:
        if t['slug'] != slug:
            h += f'<a class="tp" href="{BASE}{t["slug"]}/"><b>{e(t["name"])}</b><small>全国 {pct(t["all"])}</small></a>'
    h += f'<a class="tp" href="{BASE}kenshin/"><b>健診のあとの保健指導（市町村・会社の健康保険ごと）</b></a><a class="tp" href="{BASE}food/"><b>料理1人前の栄養</b></a></div></section>'
    h += '<section><h2>国会では</h2>' + diet_link() + '</section>'
    h += '<section class="faq"><h2>よくある質問</h2>' + ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq) + '</section>'
    h += WARN + ABOUT + foot()
    write(slug, h)


KWARN = ('<div class="warn">受診率＝特定健診の受診者÷対象者、保健指導の実施率＝特定保健指導を終えた人÷保健指導の対象者です。'
         '市町村国保（自営業・退職した人など）と会社の健康保険組合（会社員と家族）は対象の人が違うので、種類をまたいで比べないでください。保険者の取り組みの良し悪しを判定するものではありません。</div>')
FILTER_JS = ('<script>(function(){var q=document.getElementById("q");if(!q)return;var n=document.getElementById("qn"),ls=[].slice.call(document.querySelectorAll("#all li[data-q]")),ds=[].slice.call(document.querySelectorAll("#all details"));'
             'function f(){var v=q.value.trim().toLowerCase(),k=0;ls.forEach(function(l){var ok=!v||l.getAttribute("data-q").indexOf(v)>=0;l.style.display=ok?"":"none";if(ok)k++;});'
             'ds.forEach(function(d){d.open=!!v&&d.querySelector("li[data-q]:not([style*=none])")!==null;});n.textContent=v?k+"件":"";}q.addEventListener("input",f);})();</script>')


def page_kenshin(k):
    kn = k['kind_name']
    title = '特定健診・特定保健指導の実施率｜市町村国保・保険者別'
    desc = '健診で生活習慣の改善が必要とされた人のうち、特定保健指導を終えた人の割合を、1,700を超える市町村の国民健康保険と保険者ごとに。2018〜2024年度の推移を厚生労働省の公表資料から並べます。'
    h = head(title, desc, 'kenshin/', og_url('kenshin'), {'crumbs': ld_crumbs([('健診のあとの保健指導', 'kenshin/')])}, 'health-kenshin')
    h += crumbs([('健診のあとの保健指導', 'kenshin/')])
    h += f'<section class="hero"><p class="kick">CHECK-UPS</p><h1>{e(title)}</h1><p class="lead">{e(desc)}</p></section>'
    h += share(f'【{SITE}】{title}', 'kenshin/') + KWARN
    h += '<section><h2>保険者の種類ごと（2024年度）</h2><table class="t"><tr><th>種類</th><th>受診率</th><th>保健指導</th></tr>'
    for kk, nm in kn.items():
        t = k['totals'].get(kk, {}).get('2024')
        h += f'<tr><td>{e(nm)}</td><td>{pct(kr(t, 0))}</td><td>{pct(kr(t, 1))}</td></tr>'
    h += '</table><p class="note">表の保険者の値を種類ごとに足して計算したもの。厚生労働省が公表する全国計とは、公表されていない値（-）の扱いで少し違うことがあります。</p>'
    h += '<h3>市町村国保の推移</h3><table class="t"><tr><th>年度</th><th>受診率</th><th>保健指導</th></tr>'
    for y in k['years']:
        t = k['totals']['kokuho'].get(y)
        h += f'<tr><td>{y}</td><td>{pct(kr(t, 0))}</td><td>{pct(kr(t, 1))}</td></tr>'
    h += '</table>' + src('特定健康診査・特定保健指導の実施状況（保険者別）（厚生労働省）', KENSHIN_URL, '2018〜2024年度') + '</section>'
    by = {}
    for x in k['insurers']:
        if x['kind'] == 'kokuho' and '2024' in x['years']:
            by.setdefault(x['pref'], []).append(x)
    h += '<section id="kokuho"><h2>市町村国保（都道府県を開く）</h2><p><input id="q" type="search" placeholder="市町村の名前で探す（例：名古屋市、鹿児島市）" autocomplete="off"><br><span class="note" id="qn"></span></p><div id="all">'
    for p in k['prefs']:
        lst = by.get(p)
        if not lst:
            continue
        t = k['totals'].get('kokuho|' + p, {}).get('2024')
        h += f'<details class="fd"><summary>{e(p)}　<span class="note">{len(lst)}市町村・受診率 {pct(kr(t, 0))}・保健指導 {pct(kr(t, 1))}</span></summary><ul class="list">'
        for x in lst:
            v = x['years']['2024']
            h += f'<li data-q="{e((x["short"] + " " + p).lower())}"><a href="{BASE}kenshin/{x["no"]}/">{e(x["short"])}</a> <span class="note">受診率 {pct(kr(v, 0))}・保健指導 {pct(kr(v, 1))}</span></li>'
        h += '</ul></details>'
    h += f'</div><p><a href="{BASE}kenshin/kumiai/">会社の健康保険組合・共済組合の一覧へ</a></p></section>' + FILTER_JS
    tk = k['totals']['kokuho']['2024']
    kfaq = [('特定健診とは何ですか？', '40歳から74歳の人を対象に、メタボリックシンドロームに着目して生活習慣病を防ぐための健診です。医療保険者（市町村の国民健康保険、会社の健康保険組合など）が行います。'),
            ('特定保健指導とは何ですか？', '特定健診の結果、生活習慣病の発症リスクが高く、生活習慣の改善による予防効果が期待できる人に、保健師や管理栄養士が生活習慣を見直すサポートをするものです。'),
            ('市町村国保の特定保健指導の実施率は？', f'2024年度は、保健指導の対象になった人のうち{pct(kr(tk, 1))}が指導を終えています（保険者の値を足して計算）。特定健診の受診率は{pct(kr(tk, 0))}です。')]
    h += '<section class="faq"><h2>よくある質問</h2>' + ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in kfaq) + '</section>'
    h = h.replace('"@graph": [', '"@graph": [' + json.dumps({'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in kfaq]}, ensure_ascii=False) + ', ', 1)
    h += '<section><h2>国会では</h2>' + diet_link() + '</section>' + ABOUT + foot()
    write('kenshin', h)

    title = '健康保険組合の特定健診・特定保健指導の実施率'
    desc = '健康保険組合・共済組合・国民健康保険組合ごとに、特定健診の受診率と特定保健指導の実施率を2018〜2024年度で並べます（厚生労働省の保険者別の公表資料）。'
    h = head(title, desc, 'kenshin/kumiai/', og_url('kumiai'), {'crumbs': ld_crumbs([('健診のあとの保健指導', 'kenshin/'), ('健康保険組合・共済組合', 'kenshin/kumiai/')])}, 'health-kenshin')
    h += crumbs([('健診のあとの保健指導', 'kenshin/'), ('健康保険組合・共済組合', 'kenshin/kumiai/')])
    h += f'<section class="hero"><p class="kick">CHECK-UPS</p><h1>{e(title)}</h1><p class="lead">{e(desc)}</p></section>'
    h += share(f'【{SITE}】{title}', 'kenshin/kumiai/') + KWARN
    h += '<p><input id="q" type="search" placeholder="名前で探す（例：トヨタ、日立、教職員）" autocomplete="off"><br><span class="note" id="qn"></span></p><div id="all">'
    for kk in ('kenpo', 'kyosai', 'kokuho-kumiai'):
        lst = [x for x in k['insurers'] if x['kind'] == kk and '2024' in x['years']]
        h += f'<section><h2>{e(kn[kk])}（{len(lst)}）</h2><ul class="list">'
        for x in lst:
            v = x['years']['2024']
            h += f'<li data-q="{e((x["name"] + " " + x["pref"]).lower())}"><a href="{BASE}kenshin/{x["no"]}/">{e(x["name"])}</a> <span class="note">{e(x["pref"])} 受診率 {pct(kr(v, 0))}・保健指導 {pct(kr(v, 1))}</span></li>'
        h += '</ul></section>'
    h += '</div>' + FILTER_JS + ABOUT + foot()
    write('kenshin/kumiai', h)

    for x in k['insurers']:
        if '2024' not in x['years']:
            continue
        page_insurer(k, x)


def page_insurer(k, x):
    v24 = x['years']['2024']
    nm = x['short'] + 'の国民健康保険' if x['kind'] == 'kokuho' else x['name']
    tn = (x['short'] + '国保') if x['kind'] == 'kokuho' else x['name']
    kind = k['kind_name'][x['kind']]
    # 題名は32字以内: 「◯◯国保の特定健診・特定保健指導の実施率」→ 長ければ「◯◯ 特定健診の実施率」→ さらに長ければ名前だけ
    title = next(t for t in (f'{tn}の特定健診・特定保健指導の実施率', f'{tn}の特定健診・保健指導の実施率', f'{tn} 特定健診の実施率', tn) if len(t) <= 32 or t == tn)
    desc = f'{nm}（{(x["pref"] + "・") if x["pref"] else ""}{kind}）の特定健診の受診率は{pct(kr(v24, 0))}、特定保健指導の実施率は{pct(kr(v24, 1))}（2024年度）。2018年度からの推移を厚生労働省の公表資料から並べます。'
    path = f'kenshin/{x["no"]}/'
    ifaq = [(f'{nm}の特定健診の受診率は？', f'2024年度は{pct(kr(v24, 0))}です（対象者{v24[0]:,}人のうち受診者{v24[1]:,}人）。' if v24[0] and v24[1] is not None else '2024年度の値は公表されていません。'),
            (f'{nm}の特定保健指導の実施率は？', f'2024年度は{pct(kr(v24, 1))}です（保健指導の対象{v24[2]:,}人のうち終了{v24[3]:,}人）。' if v24[2] and v24[3] is not None else '2024年度の値は公表されていません。')]
    h = head(title, desc, path, og_url('kenshin'), {'crumbs': ld_crumbs([('健診のあとの保健指導', 'kenshin/'), (nm, path)]),
             'more': [{'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in ifaq]}]}, 'health-kenshin-p')
    h += crumbs([('健診のあとの保健指導', 'kenshin/'), (nm, path)])
    h += (f'<section class="hero"><p class="kick">{e((x["pref"] + "・") if x["pref"] else "")}{e(kind)}</p><h1>{e(nm)}</h1>'
          f'<div class="kv"><div><b>{pct(kr(v24, 0))}</b><span>特定健診の受診率（2024年度）</span></div><div><b>{pct(kr(v24, 1))}</b><span>特定保健指導の実施率（2024年度）</span></div></div></section>')
    h += share(f'【{SITE}】{title}（2018〜2024年度）', path)
    h += '<section><h2>年度ごとの推移</h2><table class="t"><tr><th>年度</th><th>対象者</th><th>受診率</th><th>指導の対象</th><th>実施率</th></tr>'
    for y in k['years']:
        v = x['years'].get(y)
        a = f'{v[0]:,}' if v and v[0] is not None else '—'
        c = f'{v[2]:,}' if v and v[2] is not None else '—'
        h += f'<tr><td>{y}</td><td>{a}</td><td>{pct(kr(v, 0))}</td><td>{c}</td><td>{pct(kr(v, 1))}</td></tr>'
    h += '</table><p class="note">「—」は公表されていない年度・値です。</p>' + src('特定健康診査・特定保健指導の実施状況（保険者別）（厚生労働省）', k['sources']['2024'], f'保険者番号 {x["no"]}。2024年度は2026年10月29日の訂正後') + '</section>'
    if x['kind'] == 'kokuho' and x['pref']:
        t = k['totals'].get('kokuho|' + x['pref'], {}).get('2024'); tn = k['totals']['kokuho']['2024']
        h += (f'<section><h2>同じ種類の中で</h2><table class="t"><tr><th></th><th>受診率</th><th>保健指導</th></tr>'
              f'<tr><td>{e(x["short"])}</td><td>{pct(kr(v24, 0))}</td><td>{pct(kr(v24, 1))}</td></tr>'
              f'<tr><td>{e(x["pref"])}の市町村国保</td><td>{pct(kr(t, 0))}</td><td>{pct(kr(t, 1))}</td></tr>'
              f'<tr><td>全国の市町村国保</td><td>{pct(kr(tn, 0))}</td><td>{pct(kr(tn, 1))}</td></tr></table>'
              f'<p><a href="{BASE}alt/#areas">{e(x["pref"])}の健診の数値（ALT・腹囲など）を地域ごとに見る</a></p></section>')
    h += ('<div class="warn">保健指導の実施率は、健診で生活習慣の改善が必要とされた人のうち、特定保健指導を終えた人の割合です。対象の人数が少ない保険者では、年によって大きく動きます。'
          '保険者の取り組みの良し悪しを判定するものではありません。</div>')
    h += '<section class="faq"><h2>よくある質問</h2>' + ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in ifaq) + '</section>'
    h += f'<p><a href="{BASE}kenshin/">保険者の一覧へ戻る</a></p>' + ABOUT + foot()
    write(path.rstrip('/'), h)


def page_food(food, ix):
    title = '料理1人前の栄養｜日本食品標準成分表で計算'
    desc = 'おでんとおにぎり、ミルフィーユ鍋、切り干し大根の酢の物など、身近な料理1人前のエネルギー・たんぱく質・脂質・炭水化物・食物繊維・食塩を、日本食品標準成分表（八訂）増補2023年で計算して並べます。'
    h = head(title, desc, 'food/', og_url('food'), {'crumbs': ld_crumbs([('料理の栄養', 'food/')])}, 'health-food')
    h += crumbs([('料理の栄養', 'food/')])
    h += f'<section class="hero"><p class="kick">FOOD</p><h1>{e(title)}</h1><p class="lead">{e(desc)}</p></section>'
    h += share(f'【{SITE}】{title}', 'food/') + '<div class="grid" style="margin-top:14px">'
    for d in food['dishes']:
        t = d['total']
        h += f'<a class="tp" href="{BASE}food/{d["slug"]}/"><b>{e(d["name"])}</b><span class="v">{t["kcal"]:.0f}<span style="font-size:15px">kcal</span></span><small>たんぱく質 {t["protein"]}g・脂質 {t["fat"]}g・炭水化物 {t["carb"]}g・食物繊維 {t["fiber"]}g・食塩 {t["salt"]}g</small></a>'
    h += '</div><p class="note">具材と量は当社が置いた前提です（料理のページに書いています）。市販品や店の料理の実際の栄養とは違います。</p>' + ABOUT + foot()
    write('food', h)
    topics = {t['slug']: t for t in ix['topics']}
    for d in food['dishes']:
        t = d['total']; path = f'food/{d["slug"]}/'
        title = FOOD_TITLE.get(d['slug'], f'{d["name"]}の栄養｜カロリー・たんぱく質・食物繊維・食塩')
        desc = f'{d["name"]}は約{t["kcal"]:.0f}kcal、たんぱく質{t["protein"]}g、脂質{t["fat"]}g、炭水化物{t["carb"]}g、食物繊維{t["fiber"]}g、食塩{t["salt"]}g。日本食品標準成分表（八訂）増補2023年で具材ごとに計算しました。'
        recipe = {'@type': 'Recipe', 'name': d['name'], 'recipeIngredient': [f'{i["label"]} {i["g"]}g' for i in d['items']],
                  'nutrition': {'@type': 'NutritionInformation', 'calories': f'{t["kcal"]:.0f} kcal', 'proteinContent': f'{t["protein"]} g', 'fatContent': f'{t["fat"]} g',
                                'carbohydrateContent': f'{t["carb"]} g', 'fiberContent': f'{t["fiber"]} g', 'sodiumContent': f'{t["salt"] / 2.54 * 1000:.0f} mg'}}
        ffaq = [(f'{d["short"]}のカロリーは？', f'当社が置いた具材と量（下の表）で、約{t["kcal"]:.0f}kcalです。日本食品標準成分表（八訂）増補2023年の値から計算しました。'),
                (f'{d["short"]}のたんぱく質と食物繊維は？', f'たんぱく質は{t["protein"]}g、食物繊維は{t["fiber"]}gです。'),
                (f'{d["short"]}の食塩は？', f'食塩相当量は{t["salt"]}gです。{d["note"]}')]
        h = head(title, desc, path, og_url('food-' + d['slug']), {'crumbs': ld_crumbs([('料理の栄養', 'food/'), (d['short'], path)]),
                 'more': [recipe, {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in ffaq]}]}, f'health-food-{d["slug"]}')
        h += crumbs([('料理の栄養', 'food/'), (d['short'], path)])
        h += (f'<section class="hero"><p class="kick">FOOD</p><h1>{e(d["name"])}</h1><div class="kv"><div><b>{t["kcal"]:.0f}kcal</b><span>エネルギー</span></div>'
              f'<div><b>{t["protein"]}g</b><span>たんぱく質</span></div><div><b>{t["fiber"]}g</b><span>食物繊維</span></div><div><b>{t["salt"]}g</b><span>食塩</span></div></div></section>')
        h += share(f'【{SITE}】{d["name"]}は約{t["kcal"]:.0f}kcal・たんぱく質{t["protein"]}g・食物繊維{t["fiber"]}g・食塩{t["salt"]}g', path)
        h += ('<section><h2>1人前の栄養</h2><table class="t"><tr><th>成分</th><th>量</th></tr>'
              f'<tr><td>エネルギー</td><td>{t["kcal"]:.0f} kcal</td></tr><tr><td>たんぱく質</td><td>{t["protein"]} g</td></tr><tr><td>脂質</td><td>{t["fat"]} g</td></tr>'
              f'<tr><td>炭水化物（利用可能炭水化物）</td><td>{t["carb"]} g</td></tr><tr><td>食物繊維</td><td>{t["fiber"]} g</td></tr><tr><td>食塩相当量</td><td>{t["salt"]} g</td></tr></table></section>')
        h += '<section><h2>具材と量（当社の前提）</h2><table class="t"><tr><th>具材</th><th>量</th><th>kcal</th><th>食塩</th></tr>'
        for i in d['items']:
            h += f'<tr><td>{e(i["label"])}<br><span class="note">成分表 {i["no"]} {e(i["food"])}</span></td><td>{i["g"]}g</td><td>{i["kcal"]:.0f}</td><td>{i["salt"]}g</td></tr>'
        h += f'</table><p class="note">{e(d["note"])}</p>' + src(food['source']['title'], food['source']['url'], '100gあたりの成分値×量÷100') + '</section>'
        h += '<div class="warn">具材と量は当社が置いた前提で、市販品や店の料理の実際の栄養とは違います。商品の栄養成分表示があれば、そちらを見てください。医療の助言ではありません。</div>'
        h += '<section><h2>ほかの料理と、食べ方のデータ</h2><div class="grid">'
        for x in food['dishes']:
            if x['slug'] != d['slug']:
                h += f'<a class="tp" href="{BASE}food/{x["slug"]}/"><b>{e(x["name"])}</b><small>{x["total"]["kcal"]:.0f}kcal</small></a>'
        for s in ('yashoku', 'amai-nomimono', 'hayagui'):
            if s in topics:
                h += f'<a class="tp" href="{BASE}{s}/"><b>{e(topics[s]["name"])}</b><small>全国 {pct(topics[s]["all"])}（都道府県・地域ごと）</small></a>'
        h += '</div></section>'
        h += '<section class="faq"><h2>よくある質問</h2>' + ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in ffaq) + '</section>'
        h += ABOUT + foot()
        write(path.rstrip('/'), h)


def sitemap():
    urls = sorted(p.parent.relative_to(OUT).as_posix() for p in OUT.rglob('index.html'))
    body = ''.join(f'<url><loc>{BASE}{"" if u == "." else u + "/"}</loc><lastmod>{TODAY}</lastmod></url>' for u in urls)
    (OUT / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>', encoding='utf-8')
    return len(urls)


def llms(ix, kenshin, food):
    """AI検索向けの要約（GEO）。何に答えるか・混同しやすい点・収録数・出典・注意。"""
    L = [f'# {SITE}', '', '> 特定健診を受けた40〜74歳の食べ方・睡眠・運動と、ALT（肝臓）・腹囲・BMI・HbA1cの割合を、全国・47都道府県・335の二次医療圏・性別と5歳刻みの年齢ごとに並べる。'
         '健診のあとの特定保健指導の実施率を、市町村の国民健康保険と健康保険組合などの保険者ごとに2018〜2024年度で並べる。身近な料理1人前の栄養を日本食品標準成分表で計算する。株式会社エクスブリッジ。', '',
         '## 何に答えるか', '- 「脂肪肝の目安（ALT 30超え）の人はどれくらい？都道府県で違う？」', '- 「睡眠不足・早食い・朝食抜き・夜遅い夕食・間食の人の割合は？」',
         '- 「自分の市町村の国保の特定健診の受診率・特定保健指導の実施率は？」', '- 「おでん・ミルフィーユ鍋などのカロリーと栄養は？」', '',
         '## 混同しやすい点', '- 割合は特定健診を受けた人（40〜74歳）の中の割合で、全人口の割合ではない。年齢構成の違いは調整していない。',
         '- 地域の差は相関で、原因は示さない。医療の助言・診断ではない。ALT 30 は受診の目安で、脂肪肝の診断基準ではない。',
         '- 市町村国保と健康保険組合は対象者が違うので、種類をまたいで比べない。', '- 料理の栄養は当社が置いた具材と量の前提による計算で、市販品の表示とは違う。', '',
         '## ページ', f'- 入口: {BASE}']
    for t in ix['topics']:
        L.append(f'- {t["name"]}（全国 {pct(t["all"])}）: {BASE}{t["slug"]}/')
    L += [f'- 特定健診・特定保健指導の実施率（保険者 {sum(1 for x in kenshin["insurers"] if "2024" in x["years"]):,}）: {BASE}kenshin/ ・保険者ごと {BASE}kenshin/<保険者番号8桁>/']
    for d in food['dishes']:
        L.append(f'- {d["name"]}（約{d["total"]["kcal"]:.0f}kcal）: {BASE}food/{d["slug"]}/')
    L += ['', '## 出典', f'- NDBオープンデータ 第11回（特定健診 2023年度・厚生労働省）: {NDB_URL}', f'- 特定健康診査・特定保健指導の実施状況（保険者別・厚生労働省）: {KENSHIN_URL}',
          f'- 日本食品標準成分表（八訂）増補2023年（文部科学省）: {MEXT_URL}', '', f'更新 {TODAY}']
    (OUT / 'llms.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')


def main():
    ix = json.loads((DATA / 'index.json').read_text(encoding='utf-8'))
    kenshin = json.loads((DATA / 'kenshin.json').read_text(encoding='utf-8'))
    food = json.loads((DATA / 'food.json').read_text(encoding='utf-8'))
    (OUT / 'assets').mkdir(parents=True, exist_ok=True)
    shutil.copy(MASCOT_SRC, OUT / 'assets' / 'mascot.webp')
    (OUT / 'assets' / 'health.css').write_text(CSS, encoding='utf-8')
    page_index(ix, kenshin, food)
    for t in ix['topics']:
        page_topic(json.loads((DATA / f'{t["slug"]}.json').read_text(encoding='utf-8')), ix)
    page_kenshin(kenshin)
    page_food(food, ix)
    llms(ix, kenshin, food)
    print('pages', sitemap(), '→', OUT)


if __name__ == '__main__':
    main()
