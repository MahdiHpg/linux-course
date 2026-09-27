# -*- coding: utf-8 -*-
"""Builder: Persian Linux course -> multi-page A4 book HTML (RTL)."""
import os, re, json, sys, html as html_mod
import markdown as md_lib

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, 'content')
BUILD = os.path.join(ROOT, 'build')
IMG = os.path.join(ROOT, 'images')

PAGE_W, PAGE_H = 794, 1123
COL_W = 678
BUDGET = 938

FA = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
def fa(n):
    return str(n).translate(FA)

LRM = chr(0x200E)  # left-to-right mark for Latin runs inside RTL text

FONTS_CSS = """
@font-face{font-family:Vazirmatn;src:url('../fonts/Vazirmatn-Light.ttf') format('truetype');font-weight:300;font-style:normal}
@font-face{font-family:Vazirmatn;src:url('../fonts/Vazirmatn-Regular.ttf') format('truetype');font-weight:400;font-style:normal}
@font-face{font-family:Vazirmatn;src:url('../fonts/Vazirmatn-Medium.ttf') format('truetype');font-weight:500;font-style:normal}
@font-face{font-family:Vazirmatn;src:url('../fonts/Vazirmatn-Bold.ttf') format('truetype');font-weight:700;font-style:normal}
@font-face{font-family:Vazirmatn;src:url('../fonts/Vazirmatn-Black.ttf') format('truetype');font-weight:900;font-style:normal}
@font-face{font-family:Lalezar;src:url('../fonts/Lalezar-Regular.ttf') format('truetype');font-weight:400;font-style:normal}
"""

def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.S)
    meta, body = {}, text
    if m:
        raw, body = m.group(1), m.group(2)
        key, buf = None, []
        def flush():
            if key:
                val = '\n'.join(buf).strip()
                meta[key] = val if not val.startswith('- ') else [v.strip()[2:].strip() for v in buf if v.strip().startswith('- ')]
        for line in raw.splitlines():
            km = re.match(r'^(\w+):\s*(.*)$', line)
            if km:
                flush(); key, buf = km.group(1), [km.group(2)]
            else:
                buf.append(line)
        flush()
    return meta, body

def md(text):
    return md_lib.markdown(text, extensions=['tables', 'md_in_html'])

def parse_blocks(body_md):
    lines = body_md.splitlines()
    blocks, i, n = [], 0, len(lines)
    def para_buf(buf):
        txt = '\n'.join(buf).strip()
        if txt:
            blocks.append(dict(kind='md', html=md(txt)))
    while i < n:
        line = lines[i]
        s = line.strip()
        if s.startswith(':::'):
            para_buf([])
            parts = [p.strip() for p in s[3:].split('|')]
            kind = parts[0].split()[0]
            if kind in ('figure', 'planet') and len(parts[0].split()) > 1:
                rest = parts[0].split(None, 1)[1]
                parts = [kind, rest] + parts[1:]
            inner = []
            i += 1
            while i < n and lines[i].strip() != ':::':
                inner.append(lines[i]); i += 1
            i += 1
            if kind == 'figure':
                path = parts[1] if len(parts) > 1 else ''
                cap = parts[2] if len(parts) > 2 else ''
                h = parts[3] if len(parts) > 3 else '240'
                rnd = ' round' if len(parts) > 4 and 'round' in parts[4] else ''
                cls = 'inline' if path.startswith('inline:') else ''
                src = f'images/{path}' if cls == '' else ''
                svg = path[7:] if cls else ''
                blocks.append(dict(kind='figure', cls=cls, svg=svg, src=src, cap=cap, h=int(h), rnd=rnd))
            elif kind == 'term':
                blocks.append(dict(kind='term', lines=inner))
            else:
                title = parts[1] if len(parts) > 1 else ''
                blocks.append(dict(kind='box', box=kind, title=title, html=md('\n'.join(inner))))
        elif s == '<!--pagebreak-->':
            para_buf([]); blocks.append(dict(kind='hint'))
            i += 1
        elif s.startswith('#'):
            para_buf([]); blocks.append(dict(kind='md', html=md(s), head=True)); i += 1
        elif s.startswith('- ') or re.match(r'^\d+\.', s):
            buf = []
            while i < n and (lines[i].strip().startswith('- ') or
                             re.match(r'^\d+\.', lines[i].strip()) or
                             (lines[i].strip() and lines[i].startswith('  '))):
                buf.append(lines[i]); i += 1
            para_buf([]); blocks.append(dict(kind='md', html=md('\n'.join(buf))))
        elif s.startswith('|'):
            buf = []
            while i < n and lines[i].strip().startswith('|'):
                buf.append(lines[i]); i += 1
            para_buf([]); blocks.append(dict(kind='md', html=md('\n'.join(buf)), table=True))
        elif s == '':
            para_buf([]); i += 1
        else:
            buf = [line]; i += 1
            while i < n and lines[i].strip() and not lines[i].strip().startswith((':::', '#', '|', '- ')) \
                  and not re.match(r'^\d+\.', lines[i].strip()) and lines[i].strip() != '<!--pagebreak-->':
                buf.append(lines[i]); i += 1
            para_buf(buf)
    para_buf([])
    return [b for b in blocks if not (b['kind'] == 'md' and not b['html'].strip())]

# ---------------------------------------------------------------- SVG figures
def polar(cx, cy, r, deg):
    import math
    a = math.radians(deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)

def distro_tree(w=660, h=310):
    fams = [
        ('خانواده دبیان', 'APT', ['دبیان', 'اوبونتو', 'مینت'], '#b8365a', '#fbeef2'),
        ('خانواده ردهت', 'DNF', ['فدورا', 'RHEL', 'سنتوس'], '#c04a2a', '#fdf0ec'),
        ('خانواده آرچ', 'pacman', ['آرچ', 'مانجارو'], '#2a7aa8', '#edf5fa'),
    ]
    seg = []
    colw = w / 3
    for ci, (fam, mgr, members, col, pale) in enumerate(fams):
        x0 = ci * colw
        cxm = x0 + colw / 2
        seg.append(f'<rect x="{x0+16:.0f}" y="26" width="{colw-32:.0f}" height="46" rx="10" fill="{pale}" stroke="{col}" stroke-width="1.4"/>')
        seg.append(f'<text x="{cxm:.0f}" y="47" text-anchor="middle" font-size="15" font-weight="800" fill="{col}">{fam}</text>')
        seg.append(f'<text x="{cxm:.0f}" y="65" text-anchor="middle" font-size="11.5" fill="#6b6455">مدیر بسته: {mgr}</text>')
        for mi, mem in enumerate(members):
            y = 96 + mi * 52
            seg.append(f'<rect x="{x0+34:.0f}" y="{y}" width="{colw-68:.0f}" height="40" rx="9" fill="#ffffff" stroke="{col}" stroke-opacity="0.55"/>')
            seg.append(f'<text x="{cxm:.0f}" y="{y+25:.0f}" text-anchor="middle" font-size="13.5" font-weight="700" fill="#332f28">{mem}</text>')
            seg.append(f'<line x1="{cxm:.0f}" y1="{y-6:.0f}" x2="{cxm:.0f}" y2="{y}" stroke="{col}" stroke-opacity="0.5" stroke-width="1.1"/>')
    seg.append(f'<line x1="{colw/2:.0f}" y1="88" x2="{colw/2:.0f}" y2="96" stroke="#b3aa95"/>')
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{w/2}" y="14" text-anchor="middle" font-size="12" fill="#8f8878">همه روی کرنل مشترک لینوکس</text>'
            + ''.join(seg) + '</svg>')

def term_anatomy(w=660, h=210):
    mono = "Consolas, Menlo, monospace"
    pieces = [
        (LRM + 'mehdi@ubuntu:~$' + LRM, 'پرامپت', ['سیستم می‌نویسد', 'شما تایپ نمی‌کنید'], '#6e7681', '#f0f2f5'),
        (LRM + 'ls' + LRM, 'فرمان', ['چه کاری؟', 'نمایش فهرست'], '#1a7f37', '#eaf6ec'),
        (LRM + '-lh' + LRM, 'گزینه', ['چگونه؟', 'لیست + اندازه'], '#9a6700', '#fdf6e3'),
        (LRM + '~/Documents' + LRM, 'آرگومان', ['روی چه؟', 'این پوشه'], '#0550ae', '#eaf1fb'),
    ]
    seg = []
    bw = 148; gap = 20
    total = len(pieces) * bw + (len(pieces) - 1) * gap
    x = (w - total) / 2
    for cmd, role, desc, col, pale in pieces:
        seg.append(f'<rect x="{x:.0f}" y="34" width="{bw}" height="44" rx="10" fill="{pale}" stroke="{col}" stroke-width="1.4"/>')
        seg.append(f'<text x="{x+bw/2:.0f}" y="62" text-anchor="middle" font-family="{mono}" font-size="14.5" font-weight="700" fill="{col}">{cmd}</text>')
        seg.append(f'<line x1="{x+bw/2:.0f}" y1="80" x2="{x+bw/2:.0f}" y2="100" stroke="{col}" stroke-opacity="0.5" stroke-width="1.1"/>')
        seg.append(f'<text x="{x+bw/2:.0f}" y="118" text-anchor="middle" font-size="14" font-weight="800" fill="{col}">{role}</text>')
        seg.append(f'<text x="{x+bw/2:.0f}" y="140" text-anchor="middle" font-size="10" fill="#6b6455">{desc[0]}</text>')
        seg.append(f'<text x="{x+bw/2:.0f}" y="156" text-anchor="middle" font-size="10" fill="#6b6455">{desc[1]}</text>')
        x += bw + gap
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{w/2}" y="18" text-anchor="middle" font-size="12" fill="#8f8878">الگوی همه دستورهای لینوکس: فرمان + گزینه + آرگومان</text>'
            + ''.join(seg) + '</svg>')

def fs_tree(w=660, h=400):
    dirs = [
        ('/home', 'خانه کاربران؛ فایل‌های شخصی'),
        ('/etc', 'تنظیمات سراسری سیستم'),
        ('/var', 'داده‌های متغیر و لاگ‌ها'),
        ('/usr', 'برنامه‌ها و کتابخانه‌ها'),
        ('/bin', 'دستورهای پایه سیستم'),
        ('/tmp', 'فایل‌های موقت'),
        ('/dev', 'دستگاه‌ها به‌صورت فایل'),
        ('/proc', 'پنجره زنده به کرنل'),
    ]
    seg = []
    rw, rh = 190, 46
    rx, ry = (w - rw) / 2, 30
    seg.append(f'<rect x="{rx:.0f}" y="{ry}" width="{rw}" height="{rh}" rx="11" fill="#1f2733"/>')
    seg.append(f'<text x="{w/2}" y="{ry+30:.0f}" text-anchor="middle" font-family="Consolas, monospace" font-size="21" font-weight="800" fill="#ffffff">/</text>')
    seg.append(f'<text x="{w/2+34:.0f}" y="{ry+28:.0f}" text-anchor="start" font-size="12" fill="#c9d2e0">ریشه درخت</text>')
    cols = 4
    bw = 138; bh = 88
    gx = (w - cols * bw) / (cols + 1)
    level_y = 150
    seg.append(f'<line x1="{w/2}" y1="{ry+rh}" x2="{w/2}" y2="{level_y-18}" stroke="#9aa3ad" stroke-width="1.2"/>')
    row2_y = 268
    for k, (name, desc) in enumerate(dirs):
        row = k // cols
        c = k % cols
        bx = gx + c * (bw + gx)
        by = level_y if row == 0 else row2_y
        if row == 0:
            seg.append(f'<line x1="{w/2}" y1="{level_y-18}" x2="{bx+bw/2:.0f}" y2="{by}" stroke="#9aa3ad" stroke-width="1"/>')
        seg.append(f'<rect x="{bx:.0f}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="#f6f1e7" stroke="#a89f8a" stroke-width="1.1"/>')
        seg.append(f'<text x="{bx+bw/2:.0f}" y="{by+26:.0f}" text-anchor="middle" font-family="Consolas, monospace" font-size="15" font-weight="800" fill="#1f2733">{LRM}{name}</text>')
        words = desc.split()
        line1, line2 = ' '.join(words[:3]), ' '.join(words[3:])
        seg.append(f'<text x="{bx+bw/2:.0f}" y="{by+48:.0f}" text-anchor="middle" font-size="10.5" fill="#6b6455">{line1}</text>')
        if line2:
            seg.append(f'<text x="{bx+bw/2:.0f}" y="{by+66:.0f}" text-anchor="middle" font-size="10.5" fill="#6b6455">{line2}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">' + ''.join(seg) + '</svg>')

def perms(w=660, h=330):
    groups = [('مالکار (u)', '#7b4fa8', '#f1eefb'), ('گروه (g)', '#2f7d78', '#e9f4f3'), ('بقیه (o)', '#6b6455', '#f4f2ec')]
    perms3 = ['خواندن r', 'نوشتن w', 'اجرا x']
    marks = [[True, True, False], [True, False, True], [True, False, False]]
    letters = ['rwx', 'r-x', 'r--']
    seg = []
    seg.append(f'<text x="{w/2}" y="20" text-anchor="middle" font-family="Consolas, monospace" font-size="17" font-weight="800" fill="#1f2733">{LRM}rw- r-x r--{LRM}</text>')
    seg.append(f'<text x="{w/2}" y="38" text-anchor="middle" font-size="11.5" fill="#8f8878">نمونه مجوزهای یک فایل در ls -l</text>')
    cw = 120; ch = 44; gx0 = w/2 - (3*cw)/2
    for gi, (gname, col, pale) in enumerate(groups):
        y = 60 + gi * (ch + 14)
        seg.append(f'<rect x="{gx0-178:.0f}" y="{y}" width="164" height="{ch}" rx="9" fill="{pale}" stroke="{col}" stroke-width="1.2"/>')
        seg.append(f'<text x="{gx0-96:.0f}" y="{y+28:.0f}" text-anchor="middle" font-size="13.5" font-weight="800" fill="{col}">{gname}</text>')
        seg.append(f'<text x="{gx0-96:.0f}" y="{y-6:.0f}" text-anchor="middle" font-family="Consolas, monospace" font-size="12" fill="#8f8878">{LRM}{letters[gi]}{LRM}</text>')
        for pi, p in enumerate(perms3):
            px = gx0 + pi * cw
            on = marks[gi][pi]
            seg.append(f'<rect x="{px:.0f}" y="{y}" width="{cw-10}" height="{ch}" rx="9" fill="#ffffff" stroke="#ddd6c5"/>')
            mark = '✓' if on else '✕'
            mcol = '#2f7d4f' if on else '#c0b8a4'
            seg.append(f'<text x="{px+(cw-10)/2:.0f}" y="{y+29:.0f}" text-anchor="middle" font-size="17" font-weight="800" fill="{mcol}">{mark}</text>')
            if gi == 0:
                seg.append(f'<text x="{px+(cw-10)/2:.0f}" y="{y-10:.0f}" text-anchor="middle" font-size="12" font-weight="700" fill="#6b6455">{p}</text>')
    y = 60 + 3 * (ch + 14) + 26
    seg.append(f'<rect x="{gx0-178:.0f}" y="{y}" width="{3*cw+178:.0f}" height="52" rx="11" fill="#1f2733"/>')
    seg.append(f'<text x="{w/2}" y="{y+23:.0f}" text-anchor="middle" font-size="13.5" fill="#e6d9a8">فرمول عددی: r=4 ، w=2 ، x=1 → جمع هر سه‌تایی یک رقم</text>')
    seg.append(f'<text x="{w/2}" y="{y+44:.0f}" text-anchor="middle" font-family="Consolas, monospace" font-size="16" font-weight="800" fill="#7ee787">chmod 754 file</text>')
    return f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{"".join(seg)}</svg>'

def boot_flow(w=660, h=190):
    steps = [
        ('UEFI/BIOS', 'سخت‌افزار تست می‌شود'),
        ('GRUB', 'بارگذار بوت؛ انتخاب سیستم'),
        ('کرنل ۷.۰', 'هسته بالا می‌آید'),
        ('systemd', 'سرویس‌ها ترتیب می‌گیرند'),
        ('صفحه ورود', 'لاگین شما'),
    ]
    seg = []
    bw = 112; gap = 24
    total = len(steps) * bw + (len(steps) - 1) * gap
    x = (w - total) / 2
    y = 58; bh = 74
    for k, (t, d) in enumerate(steps):
        pale = '#f6f1e7' if k % 2 == 0 else '#eaf3f6'
        col = '#8a6d1f' if k % 2 == 0 else '#2d6a80'
        seg.append(f'<rect x="{x:.0f}" y="{y}" width="{bw}" height="{bh}" rx="11" fill="{pale}" stroke="{col}" stroke-width="1.3"/>')
        seg.append(f'<text x="{x+bw/2:.0f}" y="{y+30:.0f}" text-anchor="middle" font-size="13" font-weight="800" fill="#332f28">{t}</text>')
        words = d.split()
        d1 = ' '.join(words[:2]); d2 = ' '.join(words[2:])
        seg.append(f'<text x="{x+bw/2:.0f}" y="{y+50:.0f}" text-anchor="middle" font-size="9.8" fill="#6b6455">{d1}</text>')
        if d2:
            seg.append(f'<text x="{x+bw/2:.0f}" y="{y+64:.0f}" text-anchor="middle" font-size="9.8" fill="#6b6455">{d2}</text>')
        if k < len(steps) - 1:
            ax = x + bw + 3
            seg.append(f'<line x1="{ax:.0f}" y1="{y+bh/2}" x2="{ax+gap-7:.0f}" y2="{y+bh/2}" stroke="#8f8878" stroke-width="1.6"/>')
            seg.append(f'<polygon points="{ax+gap-7:.0f},{y+bh/2-4:.0f} {ax+gap-1:.0f},{y+bh/2} {ax+gap-7:.0f},{y+bh/2+4:.0f}" fill="#8f8878"/>')
        x += bw + gap
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="{w/2}" y="26" text-anchor="middle" font-size="12" fill="#8f8878">مسیر بوت لینوکس؛ از دکمه پاور تا صفحه ورود</text>'
            + ''.join(seg) + '</svg>')

SVGS = dict(**{'distro-tree': distro_tree(), 'term-anatomy': term_anatomy(), 'fs-tree': fs_tree(), 'perms': perms(), 'boot-flow': boot_flow()})

# ---------------------------------------------------------------- block html
BOX_META = {
 'tip':      ('💡', 'نکته',      '#2f7d4f', '#eef7f0'),
 'warn':     ('⚠️', 'هشدار',     '#a06a1f', '#fdf6e8'),
 'key':      ('🔑', 'کلیدی',     '#5b4a9f', '#f1eefb'),
 'story':    ('📖', 'از تاریخ',  '#8a3d62', '#fbeff5'),
 'exercise': ('✏️', 'تمرین',     '#2c6a94', '#eaf3f9'),
}
BOX_TITLES = {'tip':'نکته','warn':'هشدار مهم','key':'جمع‌بندی','story':'روایت تاریخی','exercise':'تمرین'}

def term_html(lines):
    out = []
    for line in lines:
        e = html_mod.escape(line)
        st = line.lstrip()
        if st.startswith('# '):
            out.append(f'<span class="cmt">{e}</span>')
        elif line.startswith('$ '):
            out.append(f'<span class="ps">$</span><span class="cmd">{html_mod.escape(line[2:])}</span>')
        else:
            out.append(e)
    return f'<div class="term" dir="ltr"><pre>{chr(10).join(out)}</pre></div>'

def figure_html(b):
    if b['cls'] == 'inline':
        inner = SVGS.get(b['svg'], '')
        return (f'<figure class="fig"><div class="fig-svg" style="height:{b["h"]}px">{inner}</div>'
                f'<figcaption>{b["cap"]}</figcaption></figure>')
    return (f'<figure class="fig"><img src="{b["src"]}" alt="" style="height:{b["h"]}px" class="figimg{b["rnd"]}">'
            f'<figcaption>{b["cap"]}</figcaption></figure>')

def box_html(b):
    icon, label, col, bg = BOX_META.get(b['box'], ('💡', 'نکته', '#2f7d4f', '#eef7f0'))
    title = b['title'] or BOX_TITLES.get(b['box'], 'نکته')
    return (f'<div class="box" style="border-right-color:{col};background:{bg}">'
            f'<div class="box-title" style="color:{col}"><span class="box-ic">{icon}</span>{title}</div>'
            f'{b["html"]}</div>')

def block_html(b):
    if b['kind'] == 'term':
        return term_html(b['lines'])
    if b['kind'] == 'figure':
        return figure_html(b)
    if b['kind'] == 'box':
        return box_html(b)
    return b['html']

# ---------------------------------------------------------------- chapters
def load_chapters():
    chapters = []
    for i in range(1, 15):
        path = os.path.join(CONTENT, f'ch{i:02d}.md')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        meta, body = parse_frontmatter(text)
        blocks = parse_blocks(body)
        chapters.append(dict(num=i, meta=meta, blocks=blocks))
    return chapters

ACCENTS = {1:'#c98a2d',2:'#4f5fa8',3:'#c96a2d',4:'#7b4fa8',5:'#b8483f',6:'#2f7d78',
           7:'#3d7db3',8:'#b04f7d',9:'#2f7d4f',10:'#a03d8f',11:'#4a5d8f',12:'#a8842d',
           13:'#2d7ea0',14:'#4f8f3d'}

BOOK_TITLE = 'صفر تا صد لینوکس'

# ---------------------------------------------------------------- flow + css
FLOW_TPL = '''<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="utf-8">
<link rel="stylesheet" href="build/fonts.css">
<style>{css}
body{{background:#fff}} .flowwrap{{width:{colw}px}} .flowblk{{margin:0}}
</style></head><body><div class="flowwrap" id="wrap">{blocks}</div></body></html>'''

CONTENT_CSS = '''
*{box-sizing:border-box;margin:0;padding:0}
html,body{margin:0;padding:0}
body{font-family:Vazirmatn,Segoe UI,Tahoma,sans-serif;color:#332f28;line-height:1.95;font-size:15px}
p{text-align:justify;margin:0 0 13px}
strong{font-weight:700;color:#221f19}
code{font-family:Consolas,Menlo,monospace;font-size:.88em;background:#f0ece1;border:1px solid #e3dccb;border-radius:5px;padding:0 5px;direction:ltr;unicode-bidi:isolate}
.flowblk{margin-bottom:13px}
.flowblk h2,.page h2{font-size:20px;font-weight:900;color:#1f2733;margin:6px 0 12px;padding-right:13px;border-right:4px solid #a8842d;line-height:1.5}
.flowblk h3{font-size:16.5px;font-weight:700;color:#3a352b;margin:4px 0 8px}
table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.7;margin:6px 0 14px;border-radius:8px;overflow:hidden}
th{background:#1f2733;color:#f4efe4;font-weight:700;padding:7px 9px;text-align:right}
td{padding:6px 9px;border-bottom:1px solid #e7e1d2;text-align:right;vertical-align:top}
tr:nth-child(even) td{background:#f8f5ec}
ul,ol{margin:0 0 13px;padding-right:22px}
ol{list-style-type:persian}
li{margin-bottom:5px;text-align:justify}
ol{list-style-type:persian}
.term{background:#0d1117;border:1px solid #223;border-radius:10px;padding:13px 16px;margin:4px 0 14px;direction:ltr}
.term pre{font-family:Consolas,Menlo,monospace;font-size:12.6px;line-height:1.8;color:#d5d9e0;white-space:pre-wrap;word-break:break-word;margin:0}
.term .ps{color:#7ee787;font-weight:700}
.term .cmd{color:#e8ecf2}
.term .cmt{color:#8b949e}
.box{border-radius:10px;padding:13px 16px 11px;margin:4px 0 14px;border-right:5px solid}
.box p{margin-bottom:8px;font-size:14px}
.box p:last-child{margin-bottom:0}
.box ul,.box ol{font-size:14px;margin-bottom:6px}
.box-title{font-weight:900;font-size:15px;margin-bottom:6px}
.box-ic{margin-left:7px}
.fig{display:block;width:100%;text-align:center;margin:8px auto 14px}
.figimg{max-width:100%;width:auto;object-fit:contain}
.figimg.round{border-radius:50%;object-fit:cover}
.fig-svg svg{width:100%;height:100%}
figcaption{font-size:12.5px;color:#6b6455;margin-top:7px;font-weight:500}
.page{width:794px;height:1123px;background:#fbf9f3;break-after:page;page-break-after:always;overflow:hidden;display:flex;flex-direction:column}
.page:last-child{break-after:auto;page-break-after:auto}
.p-head{flex:0 0 auto;height:58px;padding:0 58px;display:flex;align-items:center;justify-content:space-between}
.p-head .ch-lbl{font-size:12.5px;font-weight:700;color:#6b6455;display:flex;align-items:center;gap:8px}
.p-head .dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.p-head .book{font-size:11.5px;color:#a39c8c}
.p-foot{flex:0 0 auto;height:56px;margin:0 40px;border-top:1px solid #e7e1d2;display:flex;align-items:center;justify-content:space-between;padding:0 18px}
.p-foot .pgno{font-size:12.5px;font-weight:700;color:#4a463d;background:#efe9db;border-radius:20px;padding:2px 14px}
.p-foot .foot-t{font-size:11px;color:#a39c8c}
.p-body{flex:1 1 auto;min-height:0;padding:14px 58px 0}
'''

DARK_CSS = '''
.page.dark{background:radial-gradient(1150px 760px at 82% -12%,#1c3a2c 0%,rgba(28,58,44,0) 55%),radial-gradient(900px 700px at 8% 108%,#12253c 0%,rgba(18,37,60,0) 55%),linear-gradient(168deg,#0c1220 0%,#0b1026 52%,#101a30 100%)}
.page.dark .p-head .ch-lbl{color:#9ac7b0}
.page.dark .p-head .book{color:#5d7090}
.stars{position:absolute;inset:0;pointer-events:none}
'''

STAR_DOTS = ''.join(
    f'radial-gradient({r}px {r}px at {x}% {y}%, rgba(255,255,255,{o}) 0%, rgba(255,255,255,0) 100%)'
    + (',' if i < 41 else '')
    for i, (x, y, r, o) in enumerate([
        (4,7,1.6,.9),(11,18,1.1,.6),(18,4,1.8,.8),(24,26,1.0,.5),(30,9,1.4,.7),(37,17,1.0,.55),
        (44,6,1.9,.85),(51,21,1.1,.5),(57,12,1.5,.7),(64,3,1.0,.5),(70,15,1.8,.8),(77,7,1.1,.55),
        (83,19,1.5,.75),(90,10,1.0,.5),(96,22,1.7,.8),(7,38,1.2,.6),(15,47,1.0,.45),(23,34,1.6,.75),
        (33,44,1.0,.5),(41,36,1.4,.65),(49,48,1.0,.45),(58,39,1.7,.8),(66,46,1.0,.5),(74,33,1.4,.7),
        (82,42,1.0,.5),(91,37,1.6,.75),(97,49,1.1,.55),(5,62,1.4,.65),(13,71,1.0,.45),(21,59,1.7,.75),
        (29,68,1.0,.5),(38,61,1.3,.6),(47,74,1.0,.45),(55,64,1.6,.75),(63,57,1.0,.5),(72,72,1.4,.65),
        (80,63,1.0,.5),(88,69,1.7,.75),(95,60,1.0,.5),(9,84,1.5,.7),(27,88,1.0,.5)]))
STAR_BG = (f'background-image:{STAR_DOTS};')

# ---------------------------------------------------------------- page templates
def head(ch=None, dark=False, num_lbl=''):
    if ch:
        accent = ACCENTS[ch['num']]
        left = f'<span class="ch-lbl"><span class="dot" style="background:{accent}"></span>فصل {fa(ch["num"])} — {ch["meta"]["title"]}</span>'
    else:
        left = f'<span class="ch-lbl"><span class="dot" style="background:#a8842d"></span>{num_lbl}</span>'
    return f'<div class="p-head">{left}<span class="book">{BOOK_TITLE}</span></div>'

def foot(pn, dark=False):
    return (f'<div class="p-foot"><span class="foot-t">دوره کامل تصویری — نسخه آموزشی</span>'
            f'<span class="pgno">{fa(pn)}</span></div>')

def content_page(ch, blocks_html, pn):
    body = '\n'.join(blocks_html)
    return f'''<section class="page" id="p{pn}">
{head(ch)}
<div class="p-body">{body}</div>
{foot(pn)}
</section>'''

def opener_page(ch, pn):
    n = ch['num']; accent = ACCENTS[n]
    meta = ch['meta']
    goals = '\n'.join(f'<li>{g}</li>' for g in meta.get('goals', []))
    hero = meta.get('hero', 'images/tux.png')
    lead = meta.get('lead', '')
    return f'''<section class="page dark" id="p{pn}">
<div class="stars" style="{STAR_BG}"></div>
<div style="flex:0 0 auto;display:flex;justify-content:space-between;align-items:center;padding:56px 58px 0">
  <span style="font-size:12.5px;color:#8b93bd;letter-spacing:1px">دوره کامل صفر تا صد</span>
  <span style="font-size:12.5px;color:#8b93bd">فصل {fa(n)}</span>
</div>
<div style="flex:0 0 auto;display:flex;gap:28px;padding:34px 58px 0;align-items:flex-start">
  <div style="width:400px">
    <div style="font-family:Vazirmatn,sans-serif;font-weight:900;font-size:30px;line-height:1.3;color:{accent};opacity:.9">فصل</div><div style="font-family:Vazirmatn,sans-serif;font-weight:900;font-size:92px;line-height:1.05;color:{accent};opacity:.95;margin-top:2px">{fa(n)}</div>
    <div style="width:64px;height:5px;border-radius:3px;background:{accent};margin:12px 0 18px"></div>
    <h1 style="font-family:Lalezar,Vazirmatn,sans-serif;font-size:40px;line-height:1.4;color:#f4efe4;font-weight:400;margin-bottom:14px">{meta['title']}</h1>
    <p style="color:#b9c4d8;font-size:14px;line-height:2;text-align:justify">{lead}</p>
  </div>
  <div style="flex:1"></div>
  <div style="flex:0 0 200px;height:200px">
    <img src="{hero}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;box-shadow:0 0 80px 16px rgba(255,255,255,.10),0 0 30px 4px rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.12);background:#101a30">
  </div>
</div>
<div style="flex:1 1 auto"></div>
<div style="flex:0 0 auto;margin:0 58px 14px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:16px 22px 12px">
  <div style="font-size:14px;font-weight:900;color:{accent};margin-bottom:7px">در این فصل یاد می‌گیرید</div>
  <ul style="color:#d9dfe6;font-size:13px;line-height:1.95;padding-right:20px;margin:0">{goals}</ul>
</div>
<div style="flex:0 0 auto;text-align:center;font-size:12px;color:#5d6690;padding-bottom:26px">{fa(pn)}</div>
</section>'''

def cover_page():
    logos = ''.join(
        f'<div style="width:{s}px;height:{s}px;border-radius:50%;background:#ffffff;display:flex;align-items:center;justify-content:center;box-shadow:0 0 34px 6px rgba(255,255,255,.14);overflow:hidden;padding:10px">'
        f'<img src="images/{f}.png" alt="" style="max-width:100%;max-height:100%;object-fit:contain"></div>'
        for f, s in [('debian',54),('ubuntu',60),('fedora',54)])
    return f'''<section class="page dark" id="p1">
<div class="stars" style="{STAR_BG}"></div>
<div style="flex:0 0 auto;height:8px;background:linear-gradient(270deg,#7ee787,#4a5d8f,#c98a2d,#2d7ea0)"></div>
<div style="flex:1 1 auto"></div>
<div style="flex:0 0 auto;text-align:center;padding:0 40px">
  <div style="font-size:14px;color:#8b93bd;letter-spacing:6px;margin-bottom:16px">دوره کامل آموزشی</div>
  <h1 style="font-family:Lalezar,Vazirmatn,sans-serif;font-weight:400;font-size:60px;line-height:1.35;color:#f4efe4">صفر تا صد لینوکس</h1>
  <div style="width:90px;height:5px;border-radius:3px;background:linear-gradient(90deg,#7ee787,#c98a2d);margin:22px auto"></div>
  <div style="font-size:22px;color:#d9dfe6;font-weight:300;margin-bottom:8px">از نصب تا تسلط؛ دسکتاپ، ترمینال و توسعه</div>
  <div style="font-size:13px;color:#8b93bd">هماهنگ با اوبونتو ۲۶.۰۴ LTS — برای عموم مردم و برنامه‌نویسان</div>
</div>
<div style="flex:0 0 auto;text-align:center;padding:34px 30px 0">
  <div style="display:flex;justify-content:center;align-items:center;gap:18px;flex-wrap:wrap">
    <div style="width:120px;height:120px;border-radius:50%;background:#101a30;border:1px solid rgba(255,255,255,.14);display:flex;align-items:center;justify-content:center;box-shadow:0 0 60px 12px rgba(126,231,135,.12)">
      <img src="images/tux.png" alt="" style="width:86px;height:auto;object-fit:contain">
    </div>
    {logos}
  </div>
</div>
<div style="flex:1 1 auto"></div>
<div style="flex:0 0 auto;margin:0 110px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:14px 24px;text-align:center">
  <p style="color:#b9c4d8;font-size:13px;line-height:2;text-align:center;margin:0">با بیش از ۵۰ دستور واقعی در ترمینال‌نما، ۵ نمودار آموزشی، چیت‌شیت کامل، گلاساری فارسی–انگلیسی و برنامه تمرین ۹۰ روزه</p>
</div>
<div style="flex:0 0 auto;text-align:center;font-size:12px;color:#5d6690;padding:26px 0 38px">۱۴۰۵ · نسخه آموزشی عمومی</div>
</section>'''

INTRO_MD = '''<h2>این کتاب برای کهن است؟</h2>
<p>برای هر کسی که می‌خواهد بدون مشکل با لینوکس کار کند: کاربر عادی که می‌خواهد سیستم‌عامل آزاد را تجربه کند، دانشجو و کاربر کنجکاو، و برنامه‌نویس تازه‌کار تا پیشرفته که می‌خواهد ترمینال، اسکریپت‌نویسی و ابزارهای توسعه را در سطح حرفه‌ای بلد باشد. پیش‌نیازی لازم نیست؛ از نصب شروع می‌کنیم.</p>
<h2>دو بخش، یک سفر</h2>
<p><strong>بخش اول (فصل‌های ۱ تا ۳):</strong> ورود بی‌دردسر — شناخت لینوکس، نصب روی ماشین مجازی یا WSL، و کار روزمره با دسکتاپ.<br>
<strong>بخش دوم (فصل‌های ۴ تا ۱۴):</strong> قدرت واقعی — ترمینال، فایل‌ها، فایل‌سیستم، متن و grep، دسترسی‌ها و sudo، مدیر بسته، پردازش‌ها و سرویس‌ها، شبکه و SSH، بش اسکریپت‌نویسی و جعبه‌ابزار برنامه‌نویس (git، پایتون، نود، داکر).</p>
<h2>هماهنگ با نسخه‌های روز</h2>
<p>مرجع این دوره <strong>اوبونتو ۲۶.۰۴ LTS «Resolute Raccoon»</strong> است (کرنل ۷.۰ و گنوم ۵۰) — نسخه‌ای با پشتیبانی تا ۲۰۳۱. تقریباً همه‌چیز روی نسخه‌های LTS قبلی و سایر توزیع‌ها هم یکسان است؛ هرجا تفاوت مهم باشد، جداگانه گفته‌ایم.</p>
<h2>چطور از این کتاب استفاده کنیم؟</h2>
<ul>
<li>هر فصل با فهرست «در این فصل یاد می‌گیرید» شروع می‌شود؛ اول آن را بخوانید.</li>
<li>همه‌ی دستورها داخل بلاک‌های ترمینال‌نما هستند؛ حتماً هم‌زمان در سیستم خودتان تایپ‌شان کنید — این دوره با خواندن یاد گرفته نمی‌شود، با اجرا.</li>
<li>جعبه‌های رنگی راهنمای شماست: <strong>نکته</strong> برای ترفندها، <strong>هشدار</strong> برای خطاهای پرریسک، <strong>جمع‌بندی</strong> برای مرور و <strong>تمرین</strong> برای عمل.</li>
<li>فصل آخر چیت‌شیت، گلاساری و برنامه ۹۰ روزه دارد؛ چاپش کنید و کنار کیبورد بگذارید.</li>
</ul>'''

def intro_page(pn):
    warn = ('<div class="box" style="border-right-color:#a06a1f;background:#fdf6e8">'
            '<div class="box-title" style="color:#a06a1f"><span class="box-ic">⚠️</span>یادداشت ایمنی</div>'
            '<p>تمام تمرین‌های این کتاب برای اجرا در <strong>ماشین مجازی یا WSL</strong> طراحی شده‌اند تا هیچ ریسکی برای سیستم اصلی شما نداشته باشد. دستورهای حذف (به‌ویژه <code>rm -rf</code>) را هرگز روی سیستم کاری واقعی تمرین نکنید، دستورهای ناشناس اینترنتی را بدون فهمیدن اجرا نکنید و روی سرورهای واقعی، قبل از هر تغییر با تیم مسئول هماهنگ باشید. قدرت ترمینال، قدرتِ مسئولیت است.</p></div>')
    return f'''<section class="page" id="p{pn}">
{head(num_lbl='درباره این کتاب')}
<div class="p-body">{INTRO_MD}{warn}</div>
{foot(pn)}
</section>'''

def toc_page(pn, entries):
    rows = []
    for num, title, page in entries:
        accent = ACCENTS[num]
        rows.append(f'''<a class="toc-row" href="#p{page}">
<span class="toc-num" style="background:{accent}">{fa(num)}</span>
<span class="toc-t">{title}</span>
<span class="toc-dots"></span>
<span class="toc-pg">{fa(page)}</span></a>''')
    return f'''<section class="page" id="p{pn}">
{head(num_lbl='فهرست مطالب')}
<div class="p-body">
<h2 style="font-family:Lalezar,Vazirmatn,sans-serif;font-weight:400;font-size:34px;border:none;padding:0;color:#1f2733">فهرست مطالب</h2>
<div class="toc-list">{chr(10).join(rows)}</div>
</div>
{foot(pn)}
</section>'''

BACK_MD = f'''<section class="page dark" id="plast">
<div class="stars" style="{STAR_BG}"></div>
<div style="flex:0 0 auto;height:8px;background:linear-gradient(270deg,#7ee787,#4a5d8f,#c98a2d,#2d7ea0)"></div>
<div style="flex:1 1 auto"></div>
<div style="flex:0 0 auto;text-align:center;padding:0 60px">
  <div style="font-family:Lalezar,Vazirmatn,sans-serif;font-size:46px;color:#f4efe4;line-height:1.5">هر سیستم قدرتمندی<br>با یک دستور ساده شروع شد</div>
  <div style="width:80px;height:4px;border-radius:2px;background:#7ee787;margin:26px auto"></div>
  <p style="color:#b9c4d8;font-size:14px;line-height:2.1;text-align:center;margin:0 40px">شما حالا زبان ترمینال را می‌دانید: نصب، فایل، دسترسی، سرویس، شبکه و اسکریپت. از فردا هر مشکل کامپیوتری یک «چالش ترمینالی» است — و دفترچه یادگیری‌تان را باز کنید و روزی پانزده دقیقه تمرین را شروع کنید.</p>
</div>
<div style="flex:1 1 auto"></div>
<div style="flex:0 0 auto;text-align:center;padding-bottom:80px">
  <div style="display:flex;justify-content:center;gap:16px;align-items:center">
    <img src="images/tux.png" alt="" style="width:58px;height:auto;object-fit:contain">
    <img src="images/ubuntu.png" alt="" style="width:44px;height:44px;object-fit:contain">
    <img src="images/fedora.png" alt="" style="width:44px;height:44px;object-fit:contain">
  </div>
  <div style="margin-top:22px;font-size:12px;color:#5d6690">{BOOK_TITLE} · از نصب تا تسلط — هماهنگ با اوبونتو ۲۶.۰۴ LTS</div>
</div>
</section>'''

# ---------------------------------------------------------------- packing
def pack_chapter(ch, measures, cap):
    blocks = ch['blocks']
    idx_map = [bi for bi, b in enumerate(blocks) if b['kind'] != 'hint']
    pages, cur, used = [], [], 0.0
    for pos, bi in enumerate(idx_map):
        b = blocks[bi]
        h = measures.get((ch['num'], bi), 0)
        if b['kind'] == 'md' and b.get('head'):
            nxt_h = measures.get((ch['num'], idx_map[pos + 1]), 0) if pos + 1 < len(idx_map) else 0
            needed = h + min(nxt_h, 120)
        else:
            needed = h
        if cur and used + needed > cap:
            if len(cur) > 1 and cur[-1][1].get('head'):
                popped = cur.pop()
                used -= measures.get((ch['num'], popped[0]), 0)
                pages.append(cur); cur, used = [popped], measures.get((ch['num'], popped[0]), 0)
            else:
                pages.append(cur); cur, used = [], 0.0
        cur.append((bi, b)); used += h
    if cur:
        pages.append(cur)
    return pages

def dp_pack(ch, measures, cap):
    import math
    blocks = ch['blocks']
    idx = [bi for bi, b in enumerate(blocks) if b['kind'] != 'hint']
    n = len(idx)
    sizes = [measures.get((ch['num'], bi), 0) for bi in idx]
    heads = [1 if (blocks[bi]['kind'] == 'md' and blocks[bi].get('head')) else 0 for bi in idx]
    prefix = [0]
    for sz in sizes:
        prefix.append(prefix[-1] + sz)
    total = prefix[-1]
    kmin = max(1, math.ceil(total / cap - 1e-9))
    for k in range(kmin, kmin + 5):
        INF = float('inf')
        dp = [[INF] * (k + 1) for _ in range(n + 1)]
        choice = [[-1] * (k + 1) for _ in range(n + 1)]
        dp[0][0] = 0
        for j in range(1, n + 1):
            for m in range(1, k + 1):
                for i in range(j - 1, -1, -1):
                    if dp[i][m - 1] == INF:
                        continue
                    if prefix[j] - prefix[i] > cap:
                        break
                    if m < k and heads[j - 1]:
                        continue
                    cand = max(dp[i][m - 1], prefix[j] - prefix[i])
                    if cand < dp[j][m]:
                        dp[j][m] = cand
                        choice[j][m] = i
        if dp[n][k] < INF:
            groups, j, m = [], n, k
            ok = True
            while m > 0:
                i = choice[j][m]
                if i < 0 or i >= j:
                    ok = False
                    break
                groups.append(list(range(i, j)))
                j, m = i, m - 1
            if ok and j == 0 and all(g for g in groups):
                groups.reverse()
                return [[(idx[i], blocks[idx[i]]) for i in g] for g in groups]
    return pack_chapter(ch, measures, cap)

def paginate(chapters, measures, budget=None):
    pages_out = {}
    for ch in chapters:
        cap = (budget or {}).get(ch['num'], BUDGET)
        pages_out[ch['num']] = dp_pack(ch, measures, cap)
    return pages_out

def split_oversized_tables(chapters, measures, max_h=680):
    changed = []
    for ch in chapters:
        new_blocks = []
        for bi, blk in enumerate(ch['blocks']):
            h = measures.get((ch['num'], bi), 0)
            html = blk.get('html', '') if blk['kind'] == 'md' else ''
            if blk['kind'] == 'md' and h > max_h and html.count('<table>') == 1:
                head_m = re.search(r'<thead>.*?</thead>', html, re.S)
                header = head_m.group(0) if head_m else ''
                rows = re.findall(r'<tr>.*?</tr>', html, re.S)
                if head_m:
                    rows = [r for r in rows if r not in head_m.group(0)]
                n = len(rows)
                if n >= 4:
                    row_h = max(1.0, (h - 55.0) / n)
                    per = max(4, int((max_h - 90) // row_h))
                    if per < n:
                        for ci in range(0, n, per):
                            chunk = rows[ci:ci + per]
                            new_blocks.append(dict(kind='md', head=False,
                                                   html=f'<table>{header}{chr(10).join(chunk)}</table>'))
                        changed.append((ch['num'], bi, n, per))
                        continue
                new_blocks.append(blk)
            else:
                new_blocks.append(blk)
        ch['blocks'] = new_blocks
    return changed

# ---------------------------------------------------------------- assembly
def make_flow(chapters):
    parts = []
    for ch in chapters:
        for bi, b in enumerate(ch['blocks']):
            if b['kind'] == 'hint':
                continue
            parts.append(f'<div class="flowblk" data-ch="{ch["num"]}" data-bi="{bi}">{block_html(b)}</div>')
    return parts

def page_owner(pages_html, pno):
    for item in pages_html:
        if item[0] == 'opener':
            _, ch, p = item
            if p == pno:
                return ch['num'], 'opener'
        else:
            _, ch, p, _h = item
            if p == pno:
                return ch['num'], 'content'
    return None, None

def assemble(chapters, paged):
    pages_html, toc_entries = [], []
    pn = 4
    for ch in chapters:
        toc_entries.append((ch['num'], ch['meta']['title'], pn))
        pages_html.append(('opener', ch, pn)); pn += 1
        for pg in paged[ch['num']]:
            htmls = [block_html(ch['blocks'][bi]) for bi, b in pg]
            pages_html.append(('content', ch, pn, htmls)); pn += 1
    return pages_html, toc_entries

def render_html(pages_html, toc_entries):
    out = [f'<!DOCTYPE html><html dir="rtl" lang="fa"><head><meta charset="utf-8">',
           f'<title>{BOOK_TITLE} — از نصب تا تسلط</title>',
           '<link rel="stylesheet" href="build/fonts.css">',
           f'<style>{CONTENT_CSS}{DARK_CSS}',
           '@page{size:794px 1123px;margin:0}',
           'html,body{margin:0;padding:0;background:#0b1026;width:794px}',
           '@media screen{html{background:#0b1026}}',
           '.toc-list{margin-top:10px}',
           '.toc-row{display:flex;align-items:center;gap:12px;padding:11px 6px;border-bottom:1px dashed #ddd6c5;text-decoration:none;color:#332f28}',
           '.toc-num{width:34px;height:34px;border-radius:10px;color:#fff;font-weight:900;font-size:15px;display:flex;align-items:center;justify-content:center;flex:0 0 34px}',
           '.toc-t{font-weight:700;font-size:14.5px}',
           '.toc-dots{flex:1;border-bottom:2px dotted #c9c2b0;margin:0 4px;height:1px}',
           '.toc-pg{font-weight:700;font-size:14px;color:#6b6455;background:#f0ebdd;border-radius:8px;padding:1px 12px}',
           '</style></head><body>']
    out.append(cover_page())
    out.append(intro_page(2))
    out.append(toc_page(3, toc_entries))
    for item in pages_html:
        if item[0] == 'opener':
            _, ch, p = item
            out.append(opener_page(ch, p))
        else:
            _, ch, p, htmls = item
            out.append(content_page(ch, htmls, p))
    out.append(BACK_MD)
    out.append('</body></html>')
    return '\n'.join(out)

def main():
    with open(os.path.join(BUILD, 'fonts.css'), 'w', encoding='utf-8') as f:
        f.write(FONTS_CSS)
    chapters = load_chapters()
    parts = make_flow(chapters)
    flow_html = FLOW_TPL.format(css=CONTENT_CSS, colw=COL_W, blocks=chr(10).join(parts))
    flow_path = os.path.join(ROOT, '_flow.html')
    with open(flow_path, 'w', encoding='utf-8') as f:
        f.write(flow_html)
    import subprocess
    env = dict(os.environ)
    env['NODE_PATH'] = 'C:/Users/MahdiLpTp/AppData/Roaming/npm/node_modules'
    r = subprocess.run(['node', os.path.join(ROOT, 'measure.js'), flow_path],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    if r.returncode != 0:
        print('MEASURE FAILED', r.stderr); sys.exit(1)
    measures = {(int(m['ch']), int(m['bi'])): m['h'] for m in json.loads(r.stdout)}
    splits = split_oversized_tables(chapters, measures)
    if splits:
        print('split tall tables:', splits)
        parts = make_flow(chapters)
        flow_html = FLOW_TPL.format(css=CONTENT_CSS, colw=COL_W, blocks=chr(10).join(parts))
        with open(flow_path, 'w', encoding='utf-8') as f:
            f.write(flow_html)
        r = subprocess.run(['node', os.path.join(ROOT, 'measure.js'), flow_path],
                           capture_output=True, text=True, cwd=ROOT, env=env)
        if r.returncode != 0:
            print('MEASURE FAILED', r.stderr); sys.exit(1)
        measures = {(int(m['ch']), int(m['bi'])): m['h'] for m in json.loads(r.stdout)}
    big = [(k, v) for k, v in measures.items() if v > BUDGET]
    if big:
        print('WARNING: single blocks exceed page budget:', big)
    try:
        os.remove(flow_path)
    except OSError:
        pass

    budget = {}
    for attempt in range(4):
        paged = paginate(chapters, measures, budget)
        pages_html, toc_entries = assemble(chapters, paged)
        html = render_html(pages_html, toc_entries)
        with open(os.path.join(ROOT, 'book.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        r = subprocess.run(['node', os.path.join(ROOT, 'checkfit.js')],
                           capture_output=True, text=True, cwd=ROOT, env=env)
        if r.returncode != 0:
            print('CHECKFIT FAILED', r.stderr); sys.exit(1)
        bad = json.loads(r.stdout) if r.stdout.strip() else []
        if not bad:
            total = 3 + len(pages_html) + 1
            print(f'book.html OK: pages={total} (fit attempt {attempt + 1})')
            for num, title, page in toc_entries:
                print(f'  ch{num:02d} p{page} {title}')
            return
        for b in bad:
            pno = int(b['id'][1:])
            chn, kind = page_owner(pages_html, pno)
            if kind == 'content' and chn:
                over = b['sh'] - 1123
                budget[chn] = max(560, budget.get(chn, BUDGET) - over - 28)
                print(f'  refit: ch{chn:02d} (p{pno}) over {over}px -> chapter budget {budget[chn]}')
    print('WARNING: still overflowing after refit loops')

if __name__ == '__main__':
    main()
