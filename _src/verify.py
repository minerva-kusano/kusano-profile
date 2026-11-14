#!/usr/bin/env python3
"""旧・単一ページと新サイトの照合。
    python3 _src/verify.py next
旧ページの本文を「ひとかたまりの文」（段落・表の升目・見出し・図中の文字…）に分け、
それぞれが新サイトのどこかに同じ文字列で存在するかを数える。あわせて表・図・外部リンク・画像を数える。"""
import sys, re, pathlib, collections
from lxml import html as H

SRC = pathlib.Path(__file__).resolve().parent
REPO = SRC.parent
OUT = REPO / (sys.argv[1] if len(sys.argv) > 1 else 'next')
BLOCK = set('div p table thead tbody tr td th ul ol li details summary blockquote svg g text h1 h2 h3 h4 h5 h6 button section article main header footer nav br rect line path defs marker'.split())
SKIP = {'script', 'style', 'head', 'title'}


def norm(s):
    return re.sub(r'[\s　▶]+', '', s)


def chunks(root):
    out, buf = [], []
    def flush():
        t = norm(''.join(buf)); buf.clear()
        if t: out.append(t)
    def walk(el):
        tag = el.tag if isinstance(el.tag, str) else ''
        tag = tag.split('}')[-1]
        if tag in SKIP or not tag:
            if el.tail: buf.append(el.tail)
            return
        blk = tag in BLOCK
        if blk: flush()
        if el.text: buf.append(el.text)
        for ch in el: walk(ch)
        if blk: flush()
        if el.tail: buf.append(el.tail)
    walk(root); flush()
    return out


def load(p):
    return H.fromstring(p.read_text(encoding='utf-8'))

old = load(SRC / 'legacy/index-2026-11-11.html')
old_chunks = chunks(old.body)
pages = sorted(OUT.rglob('index.html'))
new_chunks, new_full, per_page = [], '', {}
for p in pages:
    d = load(p)
    cs = chunks(d.body)
    per_page[p.relative_to(OUT).as_posix()] = cs
    new_chunks += cs
    new_full += '\n'.join(cs) + '\n'
newc = collections.Counter(new_chunks)
oldc = collections.Counter(old_chunks)

exact = sub = 0; missing = []; fewer = []
for t, n in oldc.items():
    if newc[t] >= n: exact += n
    elif newc[t] > 0: exact += newc[t]; fewer.append((t, n, newc[t]))
    elif t in norm(new_full): sub += n
    else:
        # リンクを挿んだために分かれた文は、新サイト側の全文（かたまりの境目を無視）で探す
        if t in ''.join(new_chunks): sub += n
        else: missing.append(t)
print(f'旧ページの文のかたまり：{sum(oldc.values())}（{sum(len(t) for t in old_chunks)}字）')
print(f'  新サイトに同じかたまりで存在：{exact}')
print(f'  リンクの挿入などで区切りだけ変わって存在：{sub}')
print(f'  回数が減ったもの：{len(fewer)}')
for t, n, m in fewer: print('    ', n, '→', m, t[:60])
print(f'  見つからないもの：{len(missing)}')
for t in missing: print('    ×', t[:120])
if "--detail" in sys.argv:
    for t, n in oldc.items():
        if newc[t] < n: print("   ~", t[:80])

added = [(t, n) for t, n in newc.items() if t not in oldc]
print(f'\n新サイトにだけある文字列（{len(added)}種）：')
for t, n in sorted(added, key=lambda x: -x[1]): print(f'   {n:3d}× {t[:90]}')

def count(doc, xp): return len(doc.xpath(xp))
def hrefs(doc): return [a.get('href') for a in doc.xpath('//a[starts-with(@href,"http")]')]
oh = collections.Counter(hrefs(old)); nh = collections.Counter()
nt = ns = ni = 0
for p in pages:
    d = load(p); nh.update(hrefs(d)); nt += count(d, '//table'); ns += count(d, '//svg'); ni += count(d, '//img')
print(f'\n表：旧 {count(old,"//table")} ／ 新 {nt}　図（SVG）：旧 {count(old,"//svg")} ／ 新 {ns}　画像：旧 {count(old,"//img")} ／ 新 {ni}')
print(f'外部リンク（宛先の種類）：旧 {len(oh)} ／ 新 {len(nh)}　旧にあって新にない：{sorted(set(oh)-set(nh))}　新にだけある：{sorted(set(nh)-set(oh))}')
print('外部リンク総数：旧', sum(oh.values()), '／新', sum(nh.values()))
# 内部リンク切れ
bad = []
for p in pages:
    d = load(p)
    for a in d.xpath('//a[@href]') + d.xpath('//link[@href]') + d.xpath('//script[@src]') + d.xpath('//img[@src]'):
        u = a.get('href') or a.get('src')
        if re.match(r'^(https?:|mailto:)', u): continue
        path, _, frag = u.partition('#'); path = path.split('?')[0]
        target = (p.parent / path).resolve() if path else p
        if target.is_dir(): target = target / 'index.html'
        if not target.exists(): bad.append((p.relative_to(OUT).as_posix(), u)); continue
        if frag and target.suffix == '.html':
            td = load(target)
            if not td.xpath(f'//*[@id="{frag}"]'): bad.append((p.relative_to(OUT).as_posix(), u + ' (#なし)'))
print('内部リンク・ファイル参照の切れ：', bad if bad else 'なし')
# 見出し構造
for p in pages:
    d = load(p); h1 = count(d, '//h1')
    if h1 != 1: print('h1 が1つでない：', p)
ids = collections.Counter()
top = load(OUT / 'index.html')
print('トップの旧アンカー：', {i: bool(top.xpath(f'//*[@id="{i}"]')) for i in ['works','editing-philosophy','history','interests','writing','fragments']})
