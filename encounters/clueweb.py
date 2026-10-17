"""Generate the Chapter One clue web (§2.3) and write it into campaign-bible.html.

The web is an inline SVG with a small script: select a location to see what
leads in and out of it. Edit NODES (locations, rows and positions), EDGES
(leads, plus the finale's WHEN and WHERE) and DOORS (people who can take the
coterie somewhere without a clue), then run:

    python encounters/clueweb.py

Every edge must point downward (a higher row), or the routing looks wrong;
the script refuses to write if one does not. The bible keeps the chart between
<figure class="cw-fig"> … </figure>, its script between the clueweb-js
markers and its styles between the clueweb-css markers.
"""
import json, math, pathlib, re, sys
from html import escape

# id: (badge, short name, sub line, full name, type, row, x)
SLOTS = [82, 237, 392, 547, 702]
NODES = {
    'CS': ('CS', 'Cold Storage', 'the opening night', 'Cold Storage', 'start', 0, 392),
    '1':  ('1', 'Elysium', 'the Met', 'Elysium — the Metropolitan Museum of Art', 'texture', 1, SLOTS[0]),
    '4':  ('4', '1 Wall Street', 'hedge fund', 'The hedge fund — Hollingsworth Capital', 'texture', 1, SLOTS[1]),
    '9':  ('9', 'Hudson piers', 'Meatpacking', "The Hudson piers — Marisol's Landing", 'texture', 4, SLOTS[4]),
    '8':  ('8', 'Tompkins Square', 'the 3 a.m. bench', 'The park bench — Tompkins Square Park', 'texture', 1, SLOTS[3]),
    '6':  ('6', 'Bowery dive', 'near CBGB', "The Bowery dive — Sal's Low Bar", 'texture', 1, SLOTS[4]),
    '2':  ('2', "Harpy's salon", 'the Dakota', "The Harpy's salon — the Dakota", 'clue', 2, SLOTS[0]),
    '16': ('16', 'Bellevue', 'the morgue', 'The morgue — Bellevue Hospital Center', 'texture', 1, SLOTS[2]),
    '15': ('15', 'Whispering gallery', 'Grand Central', 'The whispering gallery — Grand Central Terminal', 'texture', 2, SLOTS[2]),
    '11': ('11', 'Radio station', 'Astoria', 'The radio station — WKNA 1340 AM', 'clue', 2, SLOTS[3]),
    '17': ('17', 'Coney Island', 'the Thunderbolt', 'Coney Island — the Thunderbolt', 'texture', 2, SLOTS[4]),
    '5':  ('5', "Elder's basement", 'Brooklyn Heights', "The elder's basement — the Vandermeer house", 'clue', 3, SLOTS[0]),
    '3':  ('3', 'Antigone', 'backstage', 'Backstage at Antigone — the Lazarus Theatre', 'texture', 3, SLOTS[1]),
    '10': ('10', 'SRO flophouse', "Hell's Kitchen", 'The SRO flophouse — the Hotel Marlowe', 'clue', 3, 470),
    '12': ('12', 'Record shop', 'Cherry Street', 'The record shop — Cherry Bomb Records', 'clue', 3, SLOTS[4]),
    '13': ('13', 'Soup kitchen', 'the Bowery', 'The soup kitchen — St. Dismas Mission', 'clue', 4, 392),
    '18': ('18', 'North Brother', 'East River island', 'The hospital island — North Brother Island', 'clue', 5, SLOTS[4]),
    '7':  ('7', 'Under the bridge', 'Dumbo', 'Under the Manhattan Bridge — the Arches', 'clue', 5, 237),
    '14': ('14', 'Canal St sewers', 'the Nosferatu', "The Nosferatu sewers — Sexton's Warren", 'clue', 6, 237),
    '19': ('19', 'City Hall station', 'the finale', 'The abandoned station — City Hall station', 'finale', 7, 470),
}
# (from, to, kind, label)  kind: lead | when | where
EDGES = [
    ('CS', '11', 'lead', 'the cassette: a station ident, WKNA 1340, Astoria'),
    ('CS', '10', 'lead', 'the bouncer: Eddie Quinn has been sleeping at the Hotel Marlowe'),
    ('CS', '16', 'lead', "the Sheriff's errand: fix the morgue reports (nights 3 to 5)"),
    ('1', '2', 'lead', "Isolde Varga's invitation"),
    ('2', '5', 'lead', 'the oldest name in the ledger: Vandermeer'),
    ('2', '3', 'lead', "tickets to Lucien Marrow's opening night"),
    ('3', '7', 'lead', 'Pip the stagehand, on his night off'),
    ('4', '5', 'lead', "Preston's mentor, Vandermeer"),
    ('6', '10', 'lead', 'the Hotel Marlowe, where unwanted ghouls end up'),
    ('6', '17', 'lead', "Jinx's matchbook after first contact (or Jinx in person)"),
    ('7', '14', 'lead', "the Prophet's hatch, at the Manhattan end of the bridge"),
    ('8', '15', 'lead', '"how it doesn\'t come back"'),
    ('8', '11', 'lead', "the Night Owl on Tuesday's transistor"),
    ('16', '9', 'lead', "Russo's notebook: a boat leaves Marisol's pier every night, bound people humming the Sound"),
    ('12', '9', 'lead', "Jinx's boat-hire receipt, or following the pack's car to the West Side"),
    ('9', '18', 'lead', "Marisol's boat, and the pack's crossings once she talks"),
    ('10', '13', 'lead', "Eddie's meal card"),
    ('10', '7', 'lead', 'where Eddie was taken to hear the preacher'),
    ('11', '12', 'lead', "the courier's waybill"),
    ('11', '13', 'lead', "the engineer's mission flyer"),
    ('12', '7', 'lead', "the biggest drop point on Dot's list"),
    ('13', '7', 'lead', 'where the Prophet speaks'),
    ('13', '14', 'lead', 'the faithful "go down below"'),
    ('16', '10', 'lead', "Russo's notebook: Eddie Quinn's ER admission and address"),
    ('17', '18', 'lead', "Benedetta's invitation: Marisol's pier, an hour after midnight"),
    ('7', '19', 'when', 'the long night: Old Moses, when the Sound runs past three'),
    ('11', '19', 'when', "Kess's courier envelope: a day's warning of the long night"),
    ('14', '19', 'where', "Sexton's map of the tunnels"),
    ('18', '19', 'where', "Tobias's whisper"),
]
# doors: people who can take the coterie somewhere without a clue
DOORS = {'1': 'the Sheriff', '2': 'Vivienne', '4': 'Preston', '6': 'Rook', '8': 'Mister Tuesday',
         '13': 'Rook', '14': 'Pretty Nicky'}

W, H = 130, 46          # node box
ROW0, ROWGAP = 34, 104  # first row centre-top, row pitch
VBW = 790

def top(n):    return ROW0 + NODES[n][5] * ROWGAP
def box(n):    x = NODES[n][6]; t = top(n); return (x - W / 2, t, x + W / 2, t + H)

def ports():
    """Spread each node's outgoing (bottom) and incoming (top) edges by target x."""
    out, inn = {}, {}
    for i, (a, b, *_ ) in enumerate(EDGES):
        out.setdefault(a, []).append(i); inn.setdefault(b, []).append(i)
    pos = {}
    for d, side in ((out, 'o'), (inn, 'i')):
        for n, idx in d.items():
            other = (lambda i: NODES[EDGES[i][1]][6]) if side == 'o' else (lambda i: NODES[EDGES[i][0]][6])
            idx.sort(key=other)
            k = len(idx); span = min(W * 0.62, 18 * (k - 1))
            for j, i in enumerate(idx):
                pos[(i, side)] = NODES[n][6] - span / 2 + (span * j / (k - 1) if k > 1 else span / 2)
    return pos

def lane(row, want):
    """x of the free gap in a row nearest to `want` (for edges passing through)."""
    xs = sorted(NODES[n][6] for n in NODES if NODES[n][5] == row)
    gaps = [0 + 14] if not xs else []
    edges_ = [12] + [v for x in xs for v in (x - W / 2 - 3, x + W / 2 + 3)] + [VBW - 12]
    gaps = [((edges_[k] + edges_[k + 1]) / 2, edges_[k + 1] - edges_[k]) for k in range(0, len(edges_), 2)]
    gaps = [g for g, w in gaps if w > 4]
    return min(gaps, key=lambda g: abs(g - want))

def path(i, pos):
    a, b, kind, _ = EDGES[i]
    x0, y0 = pos[(i, 'o')], top(a) + H + (24 if a in DOORS else 0)
    x1, y1 = pos[(i, 'i')], top(b) - 2
    ra, rb = NODES[a][5], NODES[b][5]
    pts = [(x0, y0)]
    for r in range(ra + 1, rb):
        t = (r - ra) / (rb - ra)
        want = x0 + (x1 - x0) * t
        yc = ROW0 + r * ROWGAP + H / 2
        pts.append((lane(r, want), yc))
    pts.append((x1, y1))
    # smooth vertical-tangent beziers between successive points
    d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        my = (yb - ya) * 0.5
        d += f' C{xa:.1f},{ya + my:.1f} {xb:.1f},{yb - my:.1f} {xb:.1f},{yb:.1f}'
    return d

def svg():
    pos = ports()
    vbh = ROW0 + 7 * ROWGAP + H + 20
    o = [f'<svg class="cw" viewBox="0 0 {VBW} {vbh}" xmlns="http://www.w3.org/2000/svg" role="group" '
         f'aria-label="Clue web: how the Chapter One locations lead to one another">',
         '<defs>'
         '<marker id="cw-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="cw-ah"/></marker>'
         '<marker id="cw-k" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="cw-ahk"/></marker>'
         '<marker id="cw-on" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" class="cw-aho"/></marker>'
         '</defs>', '<g class="cw-edges">']
    for i, (a, b, kind, label) in enumerate(EDGES):
        o.append(f'<path class="e e-{kind}" data-a="{a}" data-b="{b}" d="{path(i, pos)}">'
                 f'<title>{escape(NODES[a][1])} → {escape(NODES[b][1])}: {escape(label)}</title></path>')
    o.append('</g><g class="cw-keys">')
    for i, (a, b, kind, label) in enumerate(EDGES):
        if kind == 'lead': continue
        x, y = pos[(i, 'o')], top(a) + H + (24 if a in DOORS else 0) + 13
        txt = kind.upper()
        o.append(f'<g class="k" data-a="{a}" data-b="{b}"><rect x="{x - 22}" y="{y - 8}" width="44" height="14" rx="2"/>'
                 f'<text x="{x}" y="{y + 2.5}">{txt}</text></g>')
    o.append('</g><g class="cw-nodes">')
    for n, (badge, name, sub, full, typ, row, x) in NODES.items():
        x0, y0, x1, y1 = box(n)
        o.append(f'<g class="n n-{typ}" data-n="{n}" tabindex="0" role="button" aria-label="{escape(full)}">')
        o.append(f'<rect class="nb" x="{x0}" y="{y0}" width="{W}" height="{H}" rx="3"/>')
        o.append(f'<circle class="b-{typ}" cx="{x0 + 17}" cy="{y0 + H / 2}" r="11"/>')
        o.append(f'<text class="bn" x="{x0 + 17}" y="{y0 + H / 2}">{escape(badge)}</text>')
        o.append(f'<text class="nt" x="{x0 + 34}" y="{y0 + 19}">{escape(name)}</text>')
        o.append(f'<text class="ns" x="{x0 + 34}" y="{y0 + 34}">{escape(sub)}</text>')
        if n in DOORS:
            o.append(f'<text class="nd" x="{x}" y="{y1 + 15}">door · {escape(DOORS[n])}</text>')
        o.append('</g>')
    o.append('</g></svg>')
    return ''.join(o)

CSS = """
.cw-fig{margin:1rem 0 1.2rem; border:1px solid var(--rule); background:var(--slab)}
.cw-scroll{overflow-x:auto; -webkit-overflow-scrolling:touch}
.cw{display:block; width:100%; min-width:640px; height:auto; font-family:var(--serif)}
.cw .e{fill:none; stroke:var(--ink-soft); stroke-width:1.3; opacity:.55; marker-end:url(#cw-a); transition:opacity .15s}
.cw .e-when,.cw .e-where{stroke:var(--vitae); stroke-width:2.6; opacity:.9; marker-end:url(#cw-k)}
.cw .cw-ah{fill:var(--ink-soft)} .cw .cw-ahk{fill:var(--vitae)} .cw .cw-aho{fill:var(--gold)}
.cw .k rect{fill:var(--vitae-deep); stroke:var(--vitae)} .cw .k text{fill:#f4efe4; font-size:9.5px; letter-spacing:.14em; text-anchor:middle; font-weight:600}
.cw .n{cursor:pointer; outline:none}
.cw .nb{fill:var(--slab-2); stroke:var(--rule); stroke-width:1}
.cw .n-clue .nb{stroke:var(--vitae); stroke-width:1.4}
.cw .n-start .nb{stroke:var(--gold); stroke-width:1.6}
.cw .n-finale .nb{fill:var(--vitae-deep); stroke:var(--gold); stroke-width:2}
.cw .b-clue{fill:var(--vitae)} .cw .b-texture{fill:var(--slab); stroke:var(--ink-soft); stroke-width:1}
.cw .b-start{fill:var(--gold)} .cw .b-finale{fill:var(--vitae); stroke:var(--gold); stroke-width:2}
.cw .bn{fill:#f4efe4; font-size:10.5px; font-weight:600; text-anchor:middle; dominant-baseline:central}
.cw .n-start .bn{fill:#1d1f22}
.cw .nt{fill:var(--ink); font-size:13px; font-weight:500}
.cw .ns{fill:var(--muted); font-size:10.5px; font-style:italic}
.cw .nd{fill:var(--gold); font-size:10px; font-style:italic; text-anchor:middle}
.cw .n:hover .nb,.cw .n:focus-visible .nb{stroke:var(--gold); stroke-width:2}
.cw.has-sel .e,.cw.has-sel .k{opacity:.1}
.cw.has-sel .n{opacity:.32}
.cw.has-sel .n.sel,.cw.has-sel .n.rel{opacity:1}
.cw.has-sel .n.sel .nb{stroke:var(--gold); stroke-width:2.4}
.cw.has-sel .e.on{opacity:1; stroke:var(--gold); marker-end:url(#cw-on)}
.cw.has-sel .e-when.on,.cw.has-sel .e-where.on{stroke:var(--vitae); marker-end:url(#cw-k)}
.cw.has-sel .k.on{opacity:1}
.cw-panel{border-top:1px solid var(--rule); background:var(--bg); padding:.7rem .9rem .8rem; font-size:.95rem; min-height:5.2rem}
.cw-panel h4{margin:0 0 .35rem; font-family:var(--fell-sc); font-weight:400; text-transform:lowercase; font-size:1.05rem; color:var(--gold); letter-spacing:.03em}
.cw-panel .cw-type{font-family:var(--serif); text-transform:none; font-style:italic; color:var(--muted); font-size:.9rem}
.cw-panel dl{display:grid; grid-template-columns:max-content 1fr; gap:.15rem .8rem; margin:0}
.cw-panel dt{color:var(--muted); font-style:italic}
.cw-panel dd{margin:0}
.cw-panel ul{margin:0; padding:0; list-style:none}
.cw-panel li{margin:0 0 .1rem}
.cw-panel .cw-key{color:var(--vitae); font-family:var(--fell-sc); text-transform:lowercase; letter-spacing:.06em}
.cw-panel button.cw-go{all:unset; cursor:pointer; color:var(--ink); text-decoration:underline; text-decoration-color:var(--gold); text-underline-offset:.18em}
.cw-panel button.cw-go:focus-visible{outline:2px solid var(--focus); outline-offset:2px}
.cw-panel a{color:var(--gold)}
.cw-legend{display:flex; flex-wrap:wrap; gap:.3rem 1.1rem; font-size:.85rem; color:var(--ink-soft); padding:.55rem .9rem; border-top:1px solid var(--rule)}
.cw-legend span{display:inline-flex; align-items:center; gap:.4rem}
.cw-legend i{display:inline-block; width:.8rem; height:.8rem; border-radius:50%}
.cw-legend .l-line{width:1.6rem; height:0; border-radius:0; border-top:1.5px solid var(--ink-soft)}
.cw-legend .l-key{width:1.6rem; height:0; border-radius:0; border-top:3px solid var(--vitae)}
@media (max-width:40rem){.cw-panel dl{grid-template-columns:1fr} .cw-panel dt{margin-top:.3rem}}
"""

JS = """
(function(){
  var data = %s;
  var svg = document.querySelector('.cw'); if (!svg) return;
  var panel = document.getElementById('cw-panel');
  var intro = panel.innerHTML, sel = null;
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function nm(n){ var d = data.nodes[n]; return (d.badge === 'CS' ? '' : d.badge + ' · ') + d.name; }
  function item(n, label, kind){
    return '<li><button type="button" class="cw-go" data-go="' + n + '">' + esc(nm(n)) + '</button>' +
      (kind !== 'lead' ? ' <span class="cw-key">' + kind + '</span>' : '') + ' — ' + esc(label) + '</li>';
  }
  function select(n){
    if (sel === n || n === null){ sel = null; svg.classList.remove('has-sel');
      svg.querySelectorAll('.sel,.rel,.on').forEach(function(e){ e.classList.remove('sel','rel','on'); });
      panel.innerHTML = intro; return; }
    sel = n; svg.classList.add('has-sel');
    svg.querySelectorAll('.n').forEach(function(g){ g.classList.toggle('sel', g.dataset.n === n); g.classList.remove('rel'); });
    var ins = [], outs = [];
    svg.querySelectorAll('.e,.k').forEach(function(e){
      var on = e.dataset.a === n || e.dataset.b === n; e.classList.toggle('on', on);
      if (on){ var other = e.dataset.a === n ? e.dataset.b : e.dataset.a;
        svg.querySelector('.n[data-n="' + other + '"]').classList.add('rel'); }
    });
    data.edges.forEach(function(e){ if (e[1] === n) ins.push(item(e[0], e[3], e[2])); if (e[0] === n) outs.push(item(e[1], e[3], e[2])); });
    var d = data.nodes[n], h = '<h4>' + esc(nm(n)) + ' <span class="cw-type">— ' + d.full + ', ' + d.type + '</span></h4><dl>';
    if (n === 'CS'){
      var doors = Object.keys(data.doors).map(function(k){ return item(k, 'via ' + data.doors[k], 'lead'); });
      outs = outs.concat(['<li><em>Doors</em> — any time, without a clue:</li>']).concat(doors);
    }
    h += '<dt>Reached from</dt><dd>' + (ins.length ? '<ul>' + ins.join('') + '</ul>' : '<em>nowhere — this is where it starts</em>') + '</dd>';
    if (data.doors[n]) h += '<dt>Door</dt><dd>' + esc(data.doors[n]) + ' can bring the coterie here at any time</dd>';
    h += '<dt>Leads to</dt><dd>' + (outs.length ? '<ul>' + outs.join('') + '</ul>' : '<em>nowhere — a dead end, on purpose</em>') + '</dd>';
    h += '</dl><p style="margin:.5rem 0 0"><a href="#' + d.anchor + '">Read the entry →</a></p>';
    panel.innerHTML = h;
  }
  svg.addEventListener('click', function(e){ var g = e.target.closest('.n'); select(g ? g.dataset.n : null); });
  svg.addEventListener('keydown', function(e){
    var g = e.target.closest && e.target.closest('.n');
    if (g && (e.key === 'Enter' || e.key === ' ')){ e.preventDefault(); select(g.dataset.n); }
    if (e.key === 'Escape') select(null);
  });
  panel.addEventListener('click', function(e){ var b = e.target.closest('[data-go]'); if (b) select(b.dataset.go); });
})();
"""

def fragment():
    data = {
        'nodes': {n: {'badge': v[0], 'name': v[1], 'full': escape(v[3]), 'type': {'clue': 'a clue location', 'texture': 'a texture location', 'start': 'the start', 'finale': 'the finale'}[v[4]],
                      'anchor': '22--cold-storage' if n == 'CS' else f'loc-{n}'} for n, v in NODES.items()},
        'edges': EDGES, 'doors': DOORS,
    }
    intro = ('<p style="margin:0"><strong>Select any location</strong> to see what leads into it and out of it. '
             'Numbers match the map in §2.4. Doors are people who can take the coterie somewhere without a clue: '
             'select <em>Cold Storage</em> to see them all.</p>')
    legend = ('<div class="cw-legend" aria-hidden="true">'
              '<span><i style="background:var(--gold)"></i>Start</span>'
              '<span><i style="background:var(--vitae)"></i>Clue location</span>'
              '<span><i style="background:var(--slab);border:1px solid var(--ink-soft)"></i>Texture</span>'
              '<span><i style="background:var(--vitae);border:2px solid var(--gold)"></i>Finale</span>'
              '<span><i class="l-line"></i>Lead</span>'
              '<span><i class="l-key"></i>What the finale needs: WHEN and WHERE</span></div>')
    return (f'<figure class="cw-fig"><div class="cw-scroll">{svg()}</div>{legend}'
            f'<div class="cw-panel" id="cw-panel" aria-live="polite">{intro}</div></figure>',
            CSS.strip(), (JS % json.dumps(data)).strip())

def main():
    for a, b, *_ in EDGES:
        if NODES[b][5] <= NODES[a][5]:
            sys.exit(f'edge {a} -> {b} does not point downward: move {b} to a lower row')
    fig, css, js = fragment()
    bible = pathlib.Path(__file__).resolve().parent.parent / 'campaign-bible.html'
    t = bible.read_text(encoding='utf-8')
    t, a = re.subn(r'<figure class="cw-fig">.*?</figure>', lambda m: fig, t, count=1, flags=re.S)
    t, b = re.subn(r'(<!--clueweb-js-begin-->\n<script>\n).*?(\n</script>\n<!--clueweb-js-end-->)', lambda m: m[1] + js + m[2], t, count=1, flags=re.S)
    t, c = re.subn(r'(/\* clueweb-css-begin \*/\n).*?(\n/\* clueweb-css-end \*/)', lambda m: m[1] + css + m[2], t, count=1, flags=re.S)
    if (a, b, c) != (1, 1, 1):
        sys.exit(f'could not find the clue web in the bible (figure {a}, script {b}, styles {c})')
    bible.write_text(t, encoding='utf-8', newline='')
    print(f'clue web written: {len(NODES)} locations, {len(EDGES)} leads')


if __name__ == '__main__':
    main()
