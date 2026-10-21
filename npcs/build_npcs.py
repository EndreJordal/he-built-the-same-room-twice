"""NPC portraits for the bible: every mention of a named NPC opens their picture and description.

Reads the descriptions (npcs-new_york.md) and the chosen portraits (locked_in/*.png) from the
portrait project, writes web-sized copies to assets/npcs/, and rewrites campaign-bible.html so
that each NPC's name is a link to a dialog showing the portrait, the description and the
original file name. Safe to run again: existing NPC links are removed and re-made, and images
that are already converted are skipped.

    python npcs/build_npcs.py
    python npcs/build_npcs.py --source C:/dev/battlemap-gen/npcs

To add an NPC: put the portrait in locked_in, the description in the .md, and an entry in NPCS
below (id, the .md heading's name, the image file stem, and the names to link).
"""
import argparse, html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIBLE = ROOT / 'campaign-bible.html'
ASSETS = ROOT / 'assets' / 'npcs'
DEFAULT_SOURCE = pathlib.Path('C:/dev/battlemap-gen/npcs')
HEIGHT, QUALITY = 1400, 80

# id, heading name in the .md, image stem in locked_in, names to link (longest first is not needed:
# the script sorts them). A group shows several portraits in one dialog.
NPCS = [
 ('vivienne', 'Vivienne Sable', 'Vivienne_Sable', ['Vivienne Sable', 'Vivienne']),
 ('tuesday', 'Mister Tuesday', 'Mister_Tuesday', ['Mister Tuesday', 'Tuesday']),
 ('rook', 'Dominic "Rook" Alvarez', 'Dominic_Rook_Alvarez', ['Dominic "Rook" Alvarez', 'Rook']),
 ('nicky', 'Pretty Nicky, masked', 'Pretty_Nicky_Masked', ['Pretty Nicky', 'Nicky']),
 ('nicky-unmasked', 'Pretty Nicky, unmasked', 'Pretty_Nicky_Unmasked', []),
 ('preston', 'Preston Whitlock', 'Preston_Whitlock', ['Preston Whitlock', 'Preston']),
 ('theo', 'Theo Castellano', 'Theo_Castellano', ['Theo Castellano', 'Theo']),
 ('honora', 'Honora Blake', 'Honora_Blake', ['Honora Blake']),
 ('eddie', 'Eddie Quinn', 'Eddie_Quinn', ['Eddie Quinn', 'Quinn, Edward', 'Eddie', 'Quinn']),
 ('hallowell', 'Ezra Hallowell', 'Ezra_Hallowell', ['Prince Ezra Hallowell', 'Ezra Hallowell', 'Hallowell']),
 ('hargrove', 'Leland Hargrove', 'Leland_Hargrove', ['Leland Hargrove', 'Hargrove']),
 ('isolde', 'Madame Isolde Varga', 'Isolde_Varga', ['Madame Isolde Varga', 'Isolde Varga', 'Isolde']),
 ('faure', 'Augustin Faure', 'Augustin_Faure', ['Augustin Faure', 'Faure']),
 ('walter', 'Walter Pryce', 'Walter_Pryce', ['Walter Pryce', 'Walter']),
 ('vandermeer', 'Cornelius Vandermeer', 'Cornelius_Vandermeer', ['Cornelius Vandermeer', 'Vandermeer']),
 ('holloway', 'Mrs. Agnes Holloway', 'Agnes_Holloway', ['Mrs. Agnes Holloway', 'Mrs. Holloway', 'Agnes Holloway']),
 ('moses', 'Old Moses', 'Old_Moses', ['Old Moses', 'Moses']),
 ('russo', 'Detective Frank Russo', 'Frank_Russo', ['Detective Frank Russo', 'Detective Russo', 'Frank Russo', 'Russo']),
 ('kahn', 'Dr. Miriam Kahn', 'Miriam_Kahn', ['Dr. Miriam Kahn', 'Dr. Kahn', 'Miriam Kahn', 'Kahn']),
 ('ricky', 'Ricky Vance, "The Night Owl"', 'Ricky_Vance', ['Ricky Vance', 'Night Owl', 'Ricky']),
 ('marisol', 'Marisol', 'Marisol', ['Marisol']),
 ('prophet', 'The Prophet', 'Prophet', ['Prophet']),
 ('ashcroft', 'Lysander Ashcroft, 1891', 'Lysander_Ashcroft_1891', ['Lysander Ashcroft', 'Ashcroft']),
 ('celestine', 'Mama Celestine', 'Mama_Celestine', ['Mama Celestine', 'Celestine']),
 ('joy', 'Sister Joy', 'Sister_Joy', ['Sister Joy']),
 ('calloway', 'Brother Calloway', 'Brother_Calloway', ['Brother Calloway', 'Calloway']),
 ('rafe', 'Rafe Delacroix', 'Rafe_Delacroix', ['Rafe Delacroix', 'Rafe']),
 ('pip', 'Pip', 'Pip', ['Pip']),
 ('dot', 'Dorothy "Dot" Malloy', 'Dorothy_Malloy', ['Dorothy "Dot" Malloy', 'Dot Malloy', 'Dot']),
 ('sexton', 'Sexton', 'Sexton', ['Sexton']),
 ('hob', 'Hob', 'Hob', ['Hob']),
 ('benedetta', 'Sister Benedetta', 'Sister_Benedetta', ['Sister Benedetta', 'Benedetta']),
 ('hollis', 'Hollis', 'Hollis', ['Hollis']),
 ('bone', 'Mister Bone', 'Mister_Bone', ['Mister Bone']),
 ('jinx', 'Jinx', 'Jinx', ['Jinx']),
 ('reyes', 'Father Dominic Reyes', 'Dominic_Reyes', ['Father Dominic Reyes', 'Father Reyes', 'Reyes']),
 ('mathilde', 'Sister Mathilde', 'Sister_Mathilde', ['Sister Mathilde', 'Mathilde']),
 ('stranger', 'The dreadlocked stranger', 'Dreadlocked_Stranger', ['dreadlocked stranger']),
]
# Which portraits a link opens: its own, then any companions.
GROUPS = {'nicky': ['nicky', 'nicky-unmasked'], 'prophet': ['prophet', 'ashcroft'], 'ashcroft': ['ashcroft', 'prophet']}

# Never link inside these elements.
SKIP = {'head', 'script', 'style', 'svg', 'nav', 'a', 'code', 'pre', 'title', 'dialog', 'button'}


def descriptions(md_path):
    md = md_path.read_text(encoding='utf-8')
    out = {}
    for head, body in re.findall(r'^### (.+?)\n(.*?)(?=^### |^## |^---|\Z)', md, re.S | re.M):
        name, _, role = head.partition(' (')
        paras = [' '.join(l.strip() for l in p.splitlines()) for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
        out[name.strip()] = {'role': role.rstrip(')').strip(), 'text': paras}
    return out


def convert(src, dst):
    from PIL import Image
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    im = Image.open(src).convert('RGB')
    if im.height > HEIGHT:
        im = im.resize((round(im.width * HEIGHT / im.height), HEIGHT), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, 'WEBP', quality=QUALITY, method=6)
    return True


def link_text(text, pattern, lookup):
    def sub(m):
        nid = lookup[m.group(0)]
        return f'<a class="npc" data-npc="{nid}" href="#npc-{nid}">{m.group(0)}</a>'
    return pattern.sub(sub, text)


def relink(page, pattern, lookup):
    page = re.sub(r'<a class="npc" data-npc="[^"]*" href="[^"]*">(.*?)</a>', r'\1', page, flags=re.S)
    out, stack, pos = [], [], 0
    for m in re.finditer(r'<!--.*?-->|<(/?)([a-zA-Z0-9]+)[^>]*?(/?)>', page, re.S):
        text = page[pos:m.start()]
        out.append(link_text(text, pattern, lookup) if text and not any(s in SKIP for s in stack) else text)
        out.append(m.group(0))
        pos = m.end()
        if m.group(0).startswith('<!--'):
            continue
        closing, tag, selfclose = m.group(1), m.group(2).lower(), m.group(3)
        if tag in ('br', 'hr', 'img', 'meta', 'link', 'input', 'source', 'wbr') or selfclose:
            continue
        if closing:
            if tag in stack:
                while stack and stack.pop() != tag:
                    pass
        else:
            stack.append(tag)
    out.append(page[pos:])
    return ''.join(out)


CSS = """
a.npc{color:inherit; text-decoration:underline dotted; text-decoration-color:var(--gold); text-underline-offset:.18em; cursor:pointer}
a.npc:hover{color:var(--gold)}
#npc-dialog{border:1px solid var(--rule); background:var(--bg); color:var(--ink); padding:0; max-width:min(64rem,94vw); max-height:92vh; width:auto}
#npc-dialog::backdrop{background:rgba(0,0,0,.72)}
#npc-dialog .npc-box{padding:1rem 1.1rem 1.1rem; display:grid; gap:1.4rem}
#npc-dialog figure{margin:0; display:grid; grid-template-columns:minmax(0,26rem) minmax(16rem,1fr); gap:1.2rem; align-items:start}
#npc-dialog figure + figure{padding-top:1.4rem; border-top:1px solid var(--rule)}
#npc-dialog img{display:block; width:100%; max-height:84vh; object-fit:contain; background:var(--slab)}
#npc-dialog h3{margin:.1rem 0 .1rem; font-family:var(--fell-sc); font-style:normal; font-weight:400; text-transform:lowercase; color:var(--gold); font-size:1.35rem}
#npc-dialog .npc-role{margin:0 0 .5rem; font-style:italic; color:var(--ink-soft)}
#npc-dialog p{margin:.4rem 0; font-size:.98rem}
#npc-dialog .npc-file{margin-top:.6rem; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.8rem; color:var(--muted)}
@media (max-width:44rem){#npc-dialog figure{grid-template-columns:1fr} #npc-dialog img{max-height:62vh}}
#npc-dialog .npc-box.multi{grid-template-columns:repeat(auto-fit,minmax(min(20rem,100%),1fr))}
#npc-dialog .npc-box.multi figure{display:block}
#npc-dialog .npc-box.multi figure + figure{padding-top:0; border-top:0}
#npc-dialog .npc-box.multi img{max-height:62vh}
#npc-dialog .npc-box.multi h3{margin-top:.7rem}
#npc-dialog .npc-close{position:sticky; top:0; float:right; margin:.4rem .4rem 0 0; font:inherit; background:var(--slab-2); color:var(--ink); border:1px solid var(--rule); cursor:pointer; padding:.1rem .55rem}
"""

JS = """
(function(){
  var data = JSON.parse(document.getElementById('npc-data').textContent);
  var dlg = document.getElementById('npc-dialog');
  if (!dlg || typeof dlg.showModal !== 'function') return;
  var box = dlg.querySelector('.npc-box');
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function card(id){
    var n = data.npcs[id];
    return '<figure><img src="' + esc(n.img) + '" alt="' + esc(n.name) + '" loading="lazy">' +
      '<figcaption><h3>' + esc(n.name) + '</h3>' + (n.role ? '<p class="npc-role">' + esc(n.role) + '</p>' : '') +
      n.text.map(function(p){ return '<p>' + esc(p) + '</p>'; }).join('') +
      '<p class="npc-file">' + esc(n.file) + '</p></figcaption></figure>';
  }
  function open(id){
    var ids = data.groups[id] || [id];
    box.className = 'npc-box' + (ids.length > 1 ? ' multi' : '');
    box.innerHTML = ids.map(card).join('');
    dlg.showModal(); dlg.scrollTop = 0;
  }
  // Capture phase, so the page's own in-page link handler never sees these clicks.
  document.addEventListener('click', function(e){
    var a = e.target.closest && e.target.closest('a.npc');
    if (!a) return;
    e.preventDefault(); e.stopImmediatePropagation();
    open(a.dataset.npc);
  }, true);
  // A click on the dialog element itself is a click on the backdrop, outside the content.
  dlg.addEventListener('click', function(e){ if (e.target === dlg) dlg.close(); });
  dlg.querySelector('.npc-close').addEventListener('click', function(){ dlg.close(); });
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=pathlib.Path, default=DEFAULT_SOURCE)
    args = ap.parse_args()
    md, pics = args.source / 'npcs-new_york.md', args.source / 'locked_in'
    if not md.exists() or not pics.exists():
        sys.exit(f'source not found: {md} / {pics}')

    desc = descriptions(md)
    data, made = {'npcs': {}, 'groups': GROUPS}, 0
    for nid, head, stem, _ in NPCS:
        if head not in desc:
            sys.exit(f'no description headed "{head}" in {md.name}')
        src = pics / f'{stem}.png'
        if not src.exists():
            sys.exit(f'missing portrait {src}')
        made += convert(src, ASSETS / f'{stem}.webp')
        data['npcs'][nid] = {'name': head, 'role': desc[head]['role'], 'text': desc[head]['text'],
                             'img': f'assets/npcs/{stem}.webp', 'file': src.name}

    lookup = {name: nid for nid, _, _, names in NPCS for name in names}
    pattern = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(n) for n in sorted(lookup, key=len, reverse=True)) + r')(?![\w-])')

    page = BIBLE.read_text(encoding='utf-8')
    page = re.sub(r'/\* npc-css-begin \*/.*?/\* npc-css-end \*/\n', '', page, flags=re.S)
    page = re.sub(r'<!-- npc-dialog-begin -->.*?<!-- npc-dialog-end -->\n', '', page, flags=re.S)
    page = relink(page, pattern, lookup)
    i = page.index('</style>\n</head>')
    page = page[:i] + '/* npc-css-begin */' + CSS + '/* npc-css-end */\n' + page[i:]
    block = ('<!-- npc-dialog-begin -->\n'
             '<dialog id="npc-dialog" aria-label="NPC"><button type="button" class="npc-close" aria-label="Close">✕</button><div class="npc-box"></div></dialog>\n'
             '<script type="application/json" id="npc-data">' + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + '</script>\n'
             '<script>' + JS + '</script>\n<!-- npc-dialog-end -->\n')
    i = page.rindex('</body>')
    page = page[:i] + block + page[i:]
    BIBLE.write_text(page, encoding='utf-8', newline='')

    links = len(re.findall(r'<a class="npc" ', page))
    per = {}
    for nid in re.findall(r'<a class="npc" data-npc="([^"]+)"', page):
        per[nid] = per.get(nid, 0) + 1
    unlinked = [nid for nid, _, _, names in NPCS if names and nid not in per]
    print(f'{len(NPCS)} portraits ({made} converted), {links} links in the bible' + (f'; never mentioned: {unlinked}' if unlinked else ''))


if __name__ == '__main__':
    main()
