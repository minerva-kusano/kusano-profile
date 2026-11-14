#!/usr/bin/env python3
"""一度きりの切り出し：旧・単一ページ (_src/legacy/index-2026-11-11.html) から
本文の断片を一字も変えずに取り出し、_src/content/ と _src/data/books.json に置く。
以後の原稿は _src/content/ 側。このスクリプトは記録として残す（再実行すると content を旧版で上書きする）。"""
import re, json, pathlib, html
HERE = pathlib.Path(__file__).parent
L = (HERE/'legacy/index-2026-11-11.html').read_text(encoding='utf-8').split('\n')
C = HERE/'content'

def rng(a, b):
    """a〜b 行（1始まり・両端含む）。行頭の字下げだけ落とす。"""
    return '\n'.join(s.strip() for s in L[a-1:b] if s.strip()) + '\n'

def put(name, text, must=None):
    if must: assert must in text, (name, must)
    p = C/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding='utf-8')

def inner(line, cls):
    m = re.search(r'<div class="%s">(.*)</div>\s*$' % re.escape(cls), L[line-1].strip(), re.S)
    assert m, (line, cls); return m.group(1)

def summary(line):
    m = re.search(r'<summary>(?:<span class="(?:aw|book)-arrow">▶</span>)?(.*)</summary>', L[line-1]); assert m, line
    return m.group(1)

# ---- トップ
put('top/lead.html', rng(190,190), '日本の書籍編集者')
put('top/profile-table.html', rng(205,213), '基本情報')
put('top/box.html', rng(217,221), '研究者・著者の方へ')
put('top/topics.html', rng(223,227), '現在、企画として関心がある主題')
put('top/box-bottom.html', rng(1305,1309), '書籍企画のご相談')
put('top/disclaimer.html', rng(1311,1311), '個人で作成・運営')
put('top/updated.txt', re.search(r'<div class="updated">(.*?)</div>', L[182]).group(1)+'\n')

# ---- 編集
put('editing/lead.html', rng(440,440), '必然性・社会性・資産性')
put('editing/matrix.html', rng(441,470), 'class="mx"')
put('editing/essay.html', rng(471,478), '編集者は専門家ではない')
put('editing/kenshu.html', rng(482,594), '研修の資料をつくる作業は')
put('editing/josei-jitsumu.html', rng(598,750), 'この回のポイント')
put('editing/josei-sengoshi.html', rng(756,874), 'この回のポイント')
put('editing/paper.html', rng(883,883), '紙の印刷物を束ねた')
put('editing/tools.html', rng(889,893), '道具をつくることは')
put('editing/after-publication.html', rng(899,907), '地続きです')

# ---- 来歴と関心
put('about/history.html', rng(917,918), '1987年福島県生まれ')
put('about/interests-figure.html', rng(930,1047), '</svg>')
put('about/interests-text.html', rng(1049,1055), '「関心 interest」という問いについて')
put('about/postmodern.html', rng(1067,1071), 'アパレル')
put('about/ushi.html', rng(1079,1090), '風立ちぬ')

# ---- 文章と記録
put('writing/list.html', rng(1103,1147), '学士論文（2013）')
put('writing/toritsugi.html', rng(1159,1253), '知的インフラ')
put('writing/series-botsu.html', rng(1260,1267), '琵琶湖疎水の麓から')
put('writing/notre-dame.html', rng(1274,1277), 'すごいものをみてしまった')
put('writing/jagaimo.html', rng(1284,1297), 'ニーチェの馬')

# 見出し（旧ページの summary の文字列そのまま）
titles = {k: summary(n) for k, n in {
  'works':230,'editing':438,'history':914,'interests':924,'writing':1101,'fragments':1153,
  'kenshu':480,'josei-jitsumu':596,'josei-sengoshi':754,'paper':881,'tools':887,'after-publication':897,
  'kanshin':928,'henreki':1061,'postmodern':1065,'ushi':1077,
  'toritsugi':1157,'series-botsu':1258,'notre-dame':1272,'jagaimo':1282,
  'mirai-afterword':246,'review-1':273,'review-2':280,'concept':363}.items()}

# ---- 書籍
def book(sumline, bibline=None, descline=None, cover=None, buy=None):
    s = L[sumline-1]
    d = {'title': re.search(r'class="book-title-text">(.*?)</span>', s).group(1),
         'tags': re.findall(r'class="genre-tag">(.*?)</span>', s)}
    if bibline:
        m = re.search(r'<div class="book-biblio( muted)?">(.*?)</div>', L[bibline-1]); d['biblio'] = m.group(2); d['biblio_muted'] = bool(m.group(1))
    if descline: d['description'] = inner(descline, 'book-description')
    if cover: d['covers'] = [re.search(r'<img src="(.*?)" alt="(.*?)">', L[n-1]).groups() for n in cover]
    if buy: d['buy'] = [(lambda m: {'href': m.group(1), 'primary': 'primary' in m.group(2), 'label': m.group(3)})(
        re.search(r'<a href="(.*?)" class="(.*?)" target="_blank">(.*?)</a>', L[n-1])) for n in range(buy[0], buy[1]+1)]
    return d

books = {
 'mirai-shikou':      book(234, 237, 241, [239], (289,292)),
 'shinka-shinrigaku': book(299, 302, 305, [303], (333,336)),
 'henyo-to-madoromi': book(343, 346, 349, [347], (351,354)),
 'cultiva':           book(360),
 'law-login':         book(375, 378, 384, [380,381], (386,389)),
 'spiritual-capital': book(404, 407, 410, [408], (412,415)),
 'mmc':               book(421, 424, 427),
}
books['cultiva']['later'] = [re.search(r'class="book-title-text">(.*?)</span>.*class="book-biblio muted">(.*?)</div>', L[n-1]).groups() for n in range(393, 400)]
labels = {'published': re.search(r'work-label">(.*?)<', L[231]).group(1), 'prep': re.search(r'work-label prep">(.*?)<', L[340]).group(1),
          'others': re.search(r'others-prep">(.*?)<', L[431]).group(1)}
(HERE/'data/books.json').write_text(json.dumps({'books': books, 'labels': labels, 'titles': titles}, ensure_ascii=False, indent=1), encoding='utf-8')

put('books/mirai-shikou.afterword.html', rng(248,264), '倫理プロトタイピング')
put('books/mirai-shikou.review-1.html', rng(275,276), 'noteで読む')
put('books/mirai-shikou.review-2.html', rng(282,283), 'noteで読む')
put('books/shinka-shinrigaku.afterword.html', rng(309,329), '田中純')
put('books/cultiva.concept.html', rng(365,371), '順次刊行開始です')
print('ok', len(list(C.rglob('*.*'))), 'files')
print(json.dumps(titles, ensure_ascii=False, indent=0)[:1500])
