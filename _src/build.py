#!/usr/bin/env python3
"""サイト生成スクリプト。

    python3 _src/build.py next     → next/ に仮置き版（検索に載らない指定つき）
    python3 _src/build.py .        → リポジトリ直下に本番版

原稿は _src/content/（本文の断片）と _src/data/books.json（書誌・書影・販売リンク）。
生成された HTML を直接書き換えず、原稿を直してこのスクリプトを回すこと。
本文の断片は一字も変えずに差し込む。ここで足すのは枠（ナビ・見出し・ラベル）だけ。
"""
import sys, re, json, html, shutil, hashlib, pathlib

SRC = pathlib.Path(__file__).resolve().parent
REPO = SRC.parent
OUT_ARG = sys.argv[1] if len(sys.argv) > 1 else 'next'
OUT = (REPO / OUT_ARG).resolve()
PREVIEW = OUT != REPO
SITE = 'https://minerva-kusano.github.io/kusano-profile/'
BASE = SITE + ('' if not PREVIEW else OUT.relative_to(REPO).as_posix() + '/')
OGP = SITE + 'OGP.png'
GA_ID = 'G-07SRBBH1TL'
FORM = 'https://docs.google.com/forms/d/e/1FAIpQLScdKtvg4ISGJMq74NKJ5n2lgfdLni5r_qtwsBBkKr1AJlvNTw/viewform?usp=header'

DATA = json.loads((SRC / 'data/books.json').read_text(encoding='utf-8'))
BOOKS, LABELS, T = DATA['books'], DATA['labels'], DATA['titles']


def c(name):
    return (SRC / 'content' / name).read_text(encoding='utf-8').rstrip('\n')


# ---------------------------------------------------------------- 新規に書いた文言
# （原文にはなく、今回の改修で足したもの。ここに集めておく）
SITE_NAME = '弧牛忘路――編書牛事'                     # 原文
EN_TITLE = "Lost Bull, Wandering On: a bull's work, grazing on words"  # 原文
TOP_TITLE = '草野善太｜書籍編集者ポートフォリオ — 弧牛忘路・編書牛事'   # 原文（旧 title）
TOP_DESC = '人文・社会科学の学術書を中心に、教科書、思想・批評、心理・行動科学などの領域で編集・出版活動に従事する書籍編集者のポートフォリオ。'  # 原文（旧 og:description）
NEW = {
    'who': '草野善太｜書籍編集者',
    'scope': '人文・社会科学の学術書、思想・批評、大学教科書',
    'nav': [('books/', '担当書籍', 'works'), ('editing/', '編集について', 'editing-philosophy'),
            ('about/', '来歴と関心', 'interests'), ('writing/', '文章と記録', 'writing')],
    'nav_contact': '相談する',
    'home': 'トップ',
    'skip': '本文へ',
    'label_soon': '近刊',
    'label_series': 'シリーズ',
    'label_published_short': '刊行',
    'kind_done': '実施',
    'kind_plan': '構想',
    'kind_doc': '資料',
    'all_books': 'すべての担当書籍 →',
    'read_on': '続きを読む →',
    'cultiva_note': '2026年12月から、順次刊行開始',     # コンセプトノート末尾の一文から
    'volumes': '各巻',
    'series_prefix': 'シリーズ：',
    'kanshin_note': '図と説明',
    'page_about': '来歴と関心',
    'page_writing': '文章と記録',
    'back_books': '← 担当書籍の一覧へ',
    'back_to': '← {}',
    'title_suffix': '｜草野善太｜書籍編集者ポートフォリオ',
    'desc': {
        'books/': '草野善太が編集を担当した書籍の一覧。刊行済みの本、近刊、シリーズ、準備中の企画。',
        'books/cultiva/': '教科書シリーズ〈ミネルヴァ・カルティヴァ ライブラリー〉のコンセプトノートと各巻。',
        'books/mmc/': '〈ミネルヴァ・モダンクラシックス叢書〉（全10巻、準備中）について。',
        'editing/': '書籍企画を考えるときの三つの軸（必然性・社会性・資産性）と、研修・道具づくり・刊行後の編集についての文章。',
        'editing/kenshu/': '社内の新人研修の設計と、書籍制作の全体業務フロー図。',
        'editing/josei-jitsumu/': '科研費の出版助成について、採択率の推移、年間スケジュール、手続きの変遷、出版社との連携、不採択時の代替策をまとめた研修資料。',
        'editing/josei-sengoshi/': '学振・科研費の成り立ちを戦後日本の歴史のなかで辿る研修資料。',
        'editing/tools/': '企画の工程管理と社内書類の作成を、自作の道具（アプリ）で行う取り組みについて。',
        'editing/after-publication/': '刊行後の本をもう一度編集の対象にする、という考え方について。',
        'about/': '草野善太の来歴と、関心領域の図、遍歴についての文章。',
        'writing/': '論文・講演の記録と、随筆・批評の棚「牟言芻鳴」。',
    },
    'desc_book': '{author}『{title}』（ミネルヴァ書房）。担当編集者による紹介。',
    'desc_piece': '{title}（草野善太）',
}

# ---------------------------------------------------------------- 小道具
def plain(s):
    s = re.sub(r'<rt>.*?</rt>', '', s)
    s = re.sub(r'<span class="new-mark">.*?</span>', '', s)
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def no_new(s):
    return re.sub(r'<span class="new-mark">.*?</span>', '', s)


def esc(s):
    return html.escape(s, quote=True)


def ext(s):
    """外部リンクに rel="noopener" を足す（文言は変えない）"""
    return re.sub(r'target="_blank"(?! rel=)', 'target="_blank" rel="noopener"', s)


def headings(s, h3=()):
    """本文中の小見出し（p.sec-h / p.sec-h-tight）を見出しタグにする。文言・クラスはそのまま。"""
    def rep(m):
        cls, text = m.group(1), m.group(2)
        tag = 'h3' if any(text.startswith(x) for x in h3) else 'h2'
        return f'<{tag} class="{cls}">{text}</{tag}>'
    return re.sub(r'<p class="(sec-h(?:-tight)?)">(.*?)</p>', rep, s)


def tables(s):
    """列が6以上ある表を、スマホで横に送れる枠で包む（文言は変えない）。"""
    def rep(m):
        first_row = re.search(r'<tr>(.*?)</tr>', m.group(0), re.S)
        cols = len(re.findall(r'<t[dh][ >]', first_row.group(1))) if first_row else 0
        return f'<div class="tbl-scroll">{m.group(0)}</div>' if cols >= 6 else m.group(0)
    return re.sub(r'<table class="tbl">.*?</table>', rep, s, flags=re.S)


def figures(s):
    """図（SVG）を、スマホで横に送れる枠で包む（中身は変えない）。"""
    return re.sub(r'<svg .*?</svg>', lambda m: f'<div class="fig-scroll">{m.group(0)}</div>', s, flags=re.S)


def link_once(s, text, href):
    assert s.count(text) == 1, (text, s.count(text))
    return s.replace(text, f'<a href="{href}">{text}</a>')


IMG = {  # 旧ファイル名 → (新ファイル名, 幅, 高さ)
    '未来思考装幀.gif': ('mirai-shikou.gif', 200, 284),
    '進化心理学概説装幀.gif': ('shinka-shinrigaku.gif', 200, 283),
    'descartes.gif': ('henyo-to-madoromi.gif', 200, 288),
    'low-login-cover.jpg': ('law-login-cover.jpg', 520, 737),
    'low-login-back.jpg': ('law-login-back.jpg', 520, 737),
    'spiritual-capital.jpg': ('spiritual-capital.jpg', 520, 749),
}


def img(R, old, alt, lazy=True):
    new, w, h = IMG[old]
    return f'<img src="{R}assets/img/{new}" alt="{alt}" width="{w}" height="{h}"' + (' loading="lazy"' if lazy else '') + '>'


def split_title(t):
    m = re.match(r'^(.*?)((?:――|——).*)$', t)
    return (m.group(1), m.group(2)) if m else (t, '')


def bib_lines(b):
    return b.get('biblio', '').split('<br>') if b.get('biblio') else []


def author(b):
    ls = bib_lines(b)
    return ls[0] if ls and '［' in ls[0] else ''


def date_line(b):
    for l in bib_lines(b):
        if '発売' in l or '刊行予定' in l:
            return l
    return ''


def tags(b):
    return ''.join(f'<span class="genre-tag">{t}</span>' for t in b['tags'])


# 書籍の並びと区分（旧ページの順序のまま。区分「近刊」「シリーズ」は今回設けたもの）
ORDER = {
    'published': ['mirai-shikou', 'shinka-shinrigaku'],
    'soon': ['henyo-to-madoromi', 'law-login', 'spiritual-capital'],
    'series': ['cultiva', 'mmc'],
}
GROUP = {s: g for g, ss in ORDER.items() for s in ss}
SERIES_OF = {'law-login': 'cultiva'}


def status_label(slug, short=True):
    g = GROUP[slug]
    if g == 'published':
        return f'<span class="work-label">{NEW["label_published_short"] if short else LABELS["published"]}</span>'
    if g == 'soon':
        return f'<span class="work-label soon">{NEW["label_soon"]}</span>'
    return f'<span class="work-label series">{NEW["label_series"]}</span>'


# ---------------------------------------------------------------- 枠
PAGES = {}   # path -> html
CSS_V = hashlib.md5((SRC / 'assets/site.css').read_bytes() + (SRC / 'assets/site.js').read_bytes()).hexdigest()[:8]


def nav(R, current=None, foot=False):
    home = R or './'
    a = []
    if foot:
        a.append(f'<a href="{home}">{NEW["home"]}</a>')
    for href, label, sec in NEW['nav']:
        cur = ' aria-current="true"' if current == sec else ''
        a.append(f'<a href="{R}{href}"{cur}>{label}</a>')
    if not foot:
        a.append(f'<a class="cta" href="#contact">{NEW["nav_contact"]}</a>')
    return '<nav class="gnav" aria-label="サイト内">' + ''.join(a) + '</nav>'


def contact_bottom():
    return ext(c('top/box-bottom.html')).replace('<div class="box-bottom">', '<div class="box-bottom" id="contact">', 1)


def page(path, title, desc, body, section=None, crumbs=None, top=False):
    depth = path.count('/')
    R = '../' * depth
    home = R or './'
    full_title = TOP_TITLE if top else plain(title) + NEW['title_suffix']
    url = BASE + path
    robots = '<meta name="robots" content="noindex,nofollow">\n' if PREVIEW else f'<link rel="canonical" href="{url}">\n'
    sec_attr = f' data-section="{section}"' if section else ''
    if top:
        header = f'''<header class="masthead">
  <p class="who">{NEW["who"]}</p>
  <h1>{SITE_NAME}</h1>
  <div class="en-title">{EN_TITLE}</div>
  <p class="scope">{NEW["scope"]}</p>
  {nav(R)}
</header>'''
    else:
        cr = [f'<a href="{home}">{NEW["home"]}</a>'] + [f'<a href="{R}{h}">{t}</a>' for h, t in (crumbs or [])] + [f'<span aria-current="page">{no_new(title)}</span>']
        header = f'''<header class="site-bar">
  <div><a class="site-name" href="{home}">{SITE_NAME}</a><span class="who">{NEW["who"]}</span></div>
  {nav(R, section if section != 'fragments' else 'writing')}
</header>
<nav class="crumbs" aria-label="現在地">{'<span class="sep">›</span>'.join(cr)}</nav>'''
    doc = f'''<!DOCTYPE html>
<html lang="ja"{sec_attr}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{GA_ID}');
</script>
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{'website' if top else 'article'}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{OGP}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc('草野善太｜書籍編集者ポートフォリオ' if top else plain(title))}">
<meta name="twitter:description" content="{esc('人文・社会科学の学術書を中心に編集・出版活動に従事する書籍編集者のポートフォリオ。' if top else desc)}">
<meta name="twitter:image" content="{OGP}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;600&family=Noto+Sans+JP:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{R}assets/site.css?v={CSS_V}">
</head>
<body>
<a class="skip" href="#main">{NEW["skip"]}</a>
<div class="W">
{header}
<main id="main">
{body}
</main>
{contact_bottom()}
<footer class="site-foot">
  {nav(R, foot=True)}
  {c('top/disclaimer.html')}
  <div>{c('top/updated.txt')}</div>
</footer>
</div>
<script src="{R}assets/site.js?v={CSS_V}"></script>
</body>
</html>
'''
    PAGES[path] = doc


EXPAND = '<button class="expand-all" onclick="toggleAll(this)" hidden>▼ すべて展開</button>'


def head(title, labels=''):
    lab = f'<div class="labels">{labels}</div>\n  ' if labels else ''
    return f'<div class="page-head">\n  {EXPAND}\n  {lab}<h1>{no_new(title)}</h1>\n</div>'


def row(href, title, kind=None, note=None, child=False):
    k = f'<span class="kind">{kind}</span>' if kind else ''
    n = f'<span class="note">{note}</span>' if note else ''
    return f'<li{" class=\"child\"" if child else ""}><a href="{href}">{k}<span class="t">{title}</span>{n}</a></li>'


# ---------------------------------------------------------------- 編集の章
EDIT = [  # (slug, 種別, 親)
    ('kenshu', NEW['kind_done'], None),
    ('josei-jitsumu', NEW['kind_doc'], 'kenshu'),
    ('josei-sengoshi', NEW['kind_doc'], 'kenshu'),
    ('tools', NEW['kind_done'], None),
    ('after-publication', NEW['kind_plan'], None),
]
EKIND = {s: k for s, k, _ in EDIT}


def edit_rows(prefix, slugs):
    return '\n'.join(row(f'{prefix}{s}/', T[s], EKIND[s], child=(s.startswith('josei'))) for s in slugs)


def build_editing():
    sec = 'editing-philosophy'
    essay = c('editing/essay.html')
    essay = link_once(essay, '「研修を設計する」内の', 'kenshu/').replace('内の</a>', '</a>内の')
    essay = link_once(essay, '「出版助成（科研費）の実務」', 'josei-jitsumu/')
    body = f'''{head(T['editing'])}
<div class="prose">
{c('editing/lead.html')}
{c('editing/matrix.html')}
{essay}
</div>
<div class="rows-mix part">
<ul class="rows">
{edit_rows('', ['kenshu', 'josei-jitsumu', 'josei-sengoshi'])}
</ul>
<details class="afterword" id="paper">
<summary><span class="aw-arrow">▶</span>{T['paper']}</summary>
<div class="afterword-body"><div class="prose mincho">
{c('editing/paper.html')}
</div></div>
</details>
<ul class="rows">
{edit_rows('', ['tools', 'after-publication'])}
</ul>
</div>'''
    page('editing/', T['editing'], NEW['desc']['editing/'], body, sec)
    up = [('editing/', T['editing'])]

    # 研修
    k = figures(c('editing/kenshu.html'))
    body = f'''<article>
{head(T['kenshu'], f'<span class="kind">{EKIND["kenshu"]}</span>')}
<div class="prose">
{k}
</div>
<ul class="rows part">
{edit_rows('../', ['josei-jitsumu', 'josei-sengoshi']).replace(' class="child"', '')}
</ul>
<p class="back"><a href="../">{NEW['back_to'].format(T['editing'])}</a></p>
</article>'''
    page('editing/kenshu/', T['kenshu'], NEW['desc']['editing/kenshu/'], body, sec, up)

    up2 = up + [('editing/kenshu/', no_new(T['kenshu']))]
    j = tables(headings(c('editing/josei-jitsumu.html'), h3=('【',)))
    j = link_once(j, '後述の「戦後史」', '../josei-sengoshi/').replace('<a href="../josei-sengoshi/">後述の', '後述の<a href="../josei-sengoshi/">')
    for slug, text in (('josei-jitsumu', j), ('josei-sengoshi', tables(headings(c('editing/josei-sengoshi.html'))))):
        other = 'josei-sengoshi' if slug == 'josei-jitsumu' else 'josei-jitsumu'
        body = f'''<article>
{head(T[slug], f'<span class="kind">{EKIND[slug]}</span>')}
<div class="prose">
{text}
</div>
<ul class="rows part">
{edit_rows('../', [other]).replace(' class="child"', '')}
</ul>
<p class="back"><a href="../kenshu/">{NEW['back_to'].format(no_new(T['kenshu']))}</a></p>
</article>'''
        page(f'editing/{slug}/', T[slug], NEW['desc'][f'editing/{slug}/'], body, sec, up2)

    for slug in ('tools', 'after-publication'):
        body = f'''<article>
{head(T[slug], f'<span class="kind">{EKIND[slug]}</span>')}
<div class="prose">
{c(f'editing/{slug}.html')}
</div>
<p class="back"><a href="../">{NEW['back_to'].format(T['editing'])}</a></p>
</article>'''
        page(f'editing/{slug}/', T[slug], NEW['desc'][f'editing/{slug}/'], body, sec, up)


# ---------------------------------------------------------------- 担当書籍
def book_li(R, slug, href):
    b = BOOKS[slug]
    th = f'<span class="th">{img(R, b["covers"][0][0], b["covers"][0][1])}</span>' if b.get('covers') else ''
    so = f'<span class="series-of">{BOOKS[SERIES_OF[slug]]["title"]}</span>' if slug in SERIES_OF else ''
    if author(b):
        bib = '｜'.join(x for x in (author(b), date_line(b)) if x)
    elif slug == 'cultiva':
        bib = NEW['cultiva_note']
    else:
        bib = b.get('biblio', '')
    tg = f'<span class="book-tags">{tags(b)}</span>' if b['tags'] else ''
    return (f'<li><a href="{href}">{th}<span class="bd">{tg}{so}<span class="book-title-text">{b["title"]}</span>'
            f'<span class="bib">{bib}</span></span><span class="go">→</span></a></li>')


def later_list():
    cv = BOOKS['cultiva']
    return '\n'.join(f'<li><div class="plain"><span class="bd"><span class="series-of">{cv["title"]}</span>'
                     f'<span class="book-title-text">{t}</span></span><span class="book-biblio muted">{note}</span></div></li>'
                     for t, note in cv['later'])


def buy(b):
    return '<div class="book-buy">\n' + '\n'.join(
        f'<a href="{x["href"]}" class="buy-btn{" primary" if x["primary"] else ""}" target="_blank" rel="noopener">{x["label"]}</a>' for x in b['buy']) + '\n</div>'


def build_books():
    sec = 'works'
    R = '../'
    parts = [head(T['works'])]
    parts.append(f'<div class="label-row"><span class="work-label">{LABELS["published"]}</span></div>\n<ul class="booklist">\n'
                 + '\n'.join(book_li(R, s, f'{s}/') for s in ORDER['published']) + '\n</ul>')
    parts.append(f'<div class="label-row-2"><span class="work-label soon">{NEW["label_soon"]}</span></div>\n<ul class="booklist">\n'
                 + '\n'.join(book_li(R, s, f'{s}/') for s in ORDER['soon']) + '\n</ul>')
    parts.append(f'<div class="label-row-2"><span class="work-label series">{NEW["label_series"]}</span></div>\n<ul class="booklist">\n'
                 + '\n'.join(book_li(R, s, f'{s}/') for s in ORDER['series']) + '\n</ul>')
    parts.append(f'<div class="label-row-2"><span class="work-label prep">{LABELS["prep"]}</span></div>\n<ul class="booklist compact">\n'
                 + later_list() + f'\n</ul>\n<p class="others-prep">{LABELS["others"]}</p>')
    page('books/', T['works'], NEW['desc']['books/'], '\n'.join(parts), sec)

    up = [('books/', T['works'])]
    R = '../../'
    for slug in ('mirai-shikou', 'shinka-shinrigaku', 'henyo-to-madoromi', 'law-login', 'spiritual-capital'):
        b = BOOKS[slug]
        dual = len(b['covers']) > 1
        covers = ''.join(img(R, o, a, lazy=False) for o, a in b['covers'])
        series = ''
        crumbs = up
        if slug in SERIES_OF:
            ss = SERIES_OF[slug]
            series = f'\n  <p class="in-series">{NEW["series_prefix"]}<a href="../{ss}/">{BOOKS[ss]["title"]}</a></p>'
            crumbs = up + [(f'books/{ss}/', BOOKS[ss]['title'])]
        hd = head(b['title'], status_label(slug) + tags(b)).replace('</h1>', '</h1>' + series)
        extra = ''
        if slug == 'mirai-shikou':
            extra = f'''
<section class="part" id="afterword">
<h2>編集後記</h2>
<h3 class="piece">{T['mirai-afterword']}</h3>
<div class="prose mincho">
{c('books/mirai-shikou.afterword.html')}
</div>
</section>
<section class="part" id="reviews">
<h2>書評</h2>
<div class="review">
<h3>{T['review-1']}</h3>
<div class="prose mincho">
{ext(c('books/mirai-shikou.review-1.html'))}
</div>
</div>
<div class="review">
<h3>{T['review-2']}</h3>
<div class="prose mincho">
{ext(c('books/mirai-shikou.review-2.html'))}
</div>
</div>
</section>'''
        if slug == 'shinka-shinrigaku':
            extra = f'''
<section class="part" id="afterword">
<h2>編集後記</h2>
<div class="prose mincho">
{c('books/shinka-shinrigaku.afterword.html')}
</div>
</section>'''
        back = f'<p class="back"><a href="../">{NEW["back_books"]}</a></p>'
        body = f'''<article class="bookpage">
{hd}
<div class="book-top{' has-dual' if dual else ''}">
<div class="book-cover{' dual' if dual else ''}">{covers}</div>
<div class="book-side">
<div class="book-biblio">{b['biblio']}</div>
{buy(b)}
</div>
</div>
<div class="book-description">{b['description']}</div>{extra}
{back}
</article>'''
        page(f'books/{slug}/', b['title'], NEW['desc_book'].format(author=author(b), title=b['title']), body, sec, crumbs)

    # カルティヴァ
    b = BOOKS['cultiva']
    body = f'''<article class="bookpage">
{head(b['title'], status_label('cultiva') + tags(b))}
<section class="part" id="concept">
<h2>{T['concept']}</h2>
<div class="prose">
{c('books/cultiva.concept.html')}
</div>
</section>
<section class="part" id="volumes">
<h2>{NEW['volumes']}</h2>
<ul class="booklist">
{book_li(R, 'law-login', '../law-login/').replace(f'<span class="series-of">{b["title"]}</span>', '')}
</ul>
<ul class="booklist compact">
{later_list().replace(f'<span class="series-of">{b["title"]}</span>', '')}
</ul>
</section>
<p class="back"><a href="../">{NEW["back_books"]}</a></p>
</article>'''
    page('books/cultiva/', b['title'], NEW['desc']['books/cultiva/'], body, sec, up)

    # モダンクラシックス
    b = BOOKS['mmc']
    body = f'''<article class="bookpage">
{head(b['title'], status_label('mmc') + tags(b))}
<div class="book-biblio muted">{b['biblio']}</div>
<div class="book-description">{b['description']}</div>
<p class="back"><a href="../">{NEW["back_books"]}</a></p>
</article>'''
    page('books/mmc/', b['title'], NEW['desc']['books/mmc/'], body, sec, up)


# ---------------------------------------------------------------- 来歴と関心
def build_about():
    sec = 'interests'
    body = f'''{head(NEW['page_about'])}
<section class="part" id="history">
<h2>{T['history']}</h2>
<div class="prose">
{c('about/history.html')}
</div>
</section>
<section class="part" id="interests">
<h2>{T['interests']}</h2>
<h3 class="subsect" id="kanshin">{T['kanshin']}</h3>
{figures(c('about/interests-figure.html'))}
<div class="prose mincho figure-text">
{c('about/interests-text.html')}
</div>
<h3 class="subsect" id="henreki">{T['henreki']}</h3>
<div class="rows-mix">
<details class="afterword" id="postmodern">
<summary><span class="aw-arrow">▶</span>{T['postmodern']}</summary>
<div class="afterword-body"><div class="prose mincho">
{c('about/postmodern.html')}
</div></div>
</details>
<ul class="rows">
{row('ushi/', T['ushi'])}
</ul>
</div>
</section>'''
    page('about/', NEW['page_about'], NEW['desc']['about/'], body, sec)
    body = f'''<article>
{head(T['ushi'])}
<div class="prose mincho">
{c('about/ushi.html')}
</div>
<p class="back"><a href="../#henreki">{NEW['back_to'].format(NEW['page_about'] + '（' + T['henreki'] + '）')}</a></p>
</article>'''
    page('about/ushi/', T['ushi'], NEW['desc_piece'].format(title=T['ushi']), body, sec, [('about/', NEW['page_about'])])


# ---------------------------------------------------------------- 文章と記録
FRAG = ['toritsugi', 'series-botsu', 'notre-dame', 'jagaimo']
FRAG_PLAIN = plain(T['fragments'])


def writing_list():
    s = c('writing/list.html')
    n = iter(range(1, 10))
    return re.sub(r'<div class="writing-item">', lambda m: f'<div class="writing-item" id="w{next(n)}">', s)


def writing_items():
    s = c('writing/list.html')
    return re.findall(r'<div class="writing-year">(.*?)</div>\s*<div class="writing-title">(.*?)</div>', s)


def build_writing():
    body = f'''{head(NEW['page_writing'])}
<section class="part" id="writing">
<h2>{T['writing']}</h2>
{writing_list()}
</section>
<section class="part" id="fragments">
<h2>{T['fragments']}</h2>
<ul class="rows">
{chr(10).join(row(f'{s}/', T[s]) for s in FRAG)}
</ul>
</section>'''
    page('writing/', NEW['page_writing'], NEW['desc']['writing/'], body, 'writing')
    for s in FRAG:
        text = c(f'writing/{s}.html')
        if s == 'toritsugi':
            text = headings(text)
        body = f'''<article>
{head(T[s], f'<span class="kind">{FRAG_PLAIN}</span>')}
<div class="prose mincho">
{text}
</div>
<p class="back"><a href="../#fragments">{NEW['back_to'].format(NEW['page_writing'] + '（' + FRAG_PLAIN + '）')}</a></p>
</article>'''
        page(f'writing/{s}/', T[s], NEW['desc_piece'].format(title=plain(T[s])), body, 'fragments', [('writing/', NEW['page_writing'])])


# ---------------------------------------------------------------- トップ
def card(slug):
    b = BOOKS[slug]
    main, sub = split_title(b['title'])
    o, a = b['covers'][0]
    bs = f'<span class="bs">{sub}</span>' if sub else ''
    ba = '<br>'.join(x for x in (author(b), date_line(b)) if x)
    return f'<a class="card" href="books/{slug}/"><span class="cv">{img("", o, a)}</span><span class="bt">{main}</span>{bs}<span class="ba">{ba}</span></a>'


def build_top():
    box = ext(c('top/box.html'))
    witems = writing_items()
    wrows = '\n'.join(row(f'writing/#w{i}', t, note=y) for i, (y, t) in enumerate(witems, 1))
    body = f'''<div class="intro-wrap">
<div class="intro-left">
{c('top/lead.html')}
{box}
</div>
<div class="profile-card">
<div class="profile-img"><img src="assets/img/profile.jpg" alt="草野善太" width="800" height="535"></div>
{c('top/profile-table.html')}
</div>
</div>

{c('top/topics.html')}

<section class="block" id="works">
<h2 class="sect">{T['works']}</h2>
<div class="block-body">
<div class="shelf">
<div class="shelf-group">
<div><span class="work-label">{LABELS['published']}</span></div>
<div class="cards">{''.join(card(s) for s in ORDER['published'])}</div>
</div>
<div class="shelf-group">
<div><span class="work-label soon">{NEW['label_soon']}</span></div>
<div class="cards">{''.join(card(s) for s in ORDER['soon'])}</div>
</div>
</div>
<div><span class="work-label series">{NEW['label_series']}</span></div>
<ul class="rows">
{row('books/cultiva/', BOOKS['cultiva']['title'], note=NEW['cultiva_note'])}
{row('books/mmc/', BOOKS['mmc']['title'], note=BOOKS['mmc']['biblio'].split('<br>')[0])}
</ul>
<p class="more"><a href="books/">{NEW['all_books']}</a></p>
</div>
</section>

<section class="block" id="editing-philosophy">
<h2 class="sect">{T['editing']}</h2>
<div class="block-body">
{c('editing/lead.html')}
{c('editing/matrix.html')}
<p class="more"><a href="editing/">{NEW['read_on']}</a></p>
<ul class="rows" style="margin-top:1rem">
{edit_rows('editing/', [s for s, _, _ in EDIT])}
</ul>
</div>
</section>

<section class="block" id="history">
<h2 class="sect">{T['history']}</h2>
<div class="block-body">
<div class="history-text">
{c('about/history.html')}
</div>
</div>
</section>

<section class="block" id="interests">
<h2 class="sect">{T['interests']}</h2>
<div class="block-body">
<ul class="rows">
{row('about/#kanshin', T['kanshin'], note=NEW['kanshin_note'])}
{row('about/#postmodern', T['postmodern'], note=T['henreki'])}
{row('about/ushi/', T['ushi'], note=T['henreki'])}
</ul>
</div>
</section>

<section class="block" id="writing">
<h2 class="sect">{T['writing']}</h2>
<div class="block-body">
<ul class="rows">
{wrows}
</ul>
</div>
</section>

<section class="block" id="fragments">
<h2 class="sect">{T['fragments']}</h2>
<div class="block-body">
<ul class="rows">
{chr(10).join(row(f'writing/{s}/', T[s]) for s in FRAG)}
</ul>
</div>
</section>'''
    page('', SITE_NAME, TOP_DESC, body, None, top=True)


# ---------------------------------------------------------------- 書き出し
def main():
    build_top(); build_books(); build_editing(); build_about(); build_writing()
    if PREVIEW and OUT.exists():
        shutil.rmtree(OUT)
    for path, doc in PAGES.items():
        p = OUT / path / 'index.html'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(doc, encoding='utf-8')
    dst = OUT / 'assets'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SRC / 'assets', dst)
    print(f'{len(PAGES)} ページを {OUT} に書き出しました（{"仮置き・noindex" if PREVIEW else "本番"}）')
    for p in PAGES:
        print('  /' + p)


if __name__ == '__main__':
    main()
