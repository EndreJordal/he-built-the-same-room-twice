"""Build encounters.html from the encounter definitions in this folder, and
refresh the encounter links in campaign-bible.html.

Each encounter gets two links:
- the combat link (main): opens imagineVTT, which opens the scene for the fight and hands
  the encounter to the combat tracker (see imagineVTT's docs/combat-link.md);
- the tracker-only link: opens the encounter straight in the combat tracker, as before.

Extra fields in an encounter file, for imagineVTT (the tracker never sees `scene`):
- "scene": the imagineVTT scene name. Default: the encounter's name for set encounters
  ("The Record Shop - Fire in the Dubbing Room"), "Random - <name>" for random ones.
- "vtt" on a combatant: how its token looks, e.g.
  {"border": "iron-chain", "type": "Brujah antitribu", "size": 1, "label": "both"}.
- "status" on a combatant: tracker conditions it starts under, e.g. ["frenzy"], ["staked"],
  ["prone"], ["immobilized"], ["battleForm"]; "secret": the ones the players should not see.
  Both pass through to the tracker unchanged, like every other combatant field.

Set IMAGINE_URL to test against a local imagineVTT, e.g.
    IMAGINE_URL=http://localhost:5180/ python encounters/build.py

Each *.json file here is one combat-tracker encounter payload (see the
tracker README, "Encounter links"). Name them `set-NN-…` for fights tied to
a location and `rnd-NN-…` for random encounters; they are listed in filename
order within each group. In the bible, an encounter link is any
`<a … data-enc="FILE-STEM" href="…">`; its href is rewritten on every build.
Run after adding or editing an encounter:

    python encounters/build.py
"""
import base64, html, json, os, pathlib, re

TRACKER = 'https://endrejordal.github.io/vtm-combat-tracker/'
IMAGINE = os.environ.get('IMAGINE_URL') or 'https://endrejordal.github.io/imagineVTT/'
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'encounters.html'
BIBLE = HERE.parent / 'campaign-bible.html'
GROUPS = [('set-', 'Set encounters', 'Fights tied to a place in the chronicle. Each is linked from its location in the bible.'),
          ('rnd-', 'Random encounters', 'Fights that can be dropped in wherever the city needs to bite. Listed in the bible under §2.9.')]


def b64(data):
    raw = json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def tracker_payload(payload):
    """The encounter as the tracker takes it: without imagineVTT's scene name."""
    return {k: v for k, v in payload.items() if k != 'scene'}


def link(payload):
    """Tracker-only link (as before imagineVTT)."""
    return TRACKER + '#encounter=' + b64(tracker_payload(payload))


def scene_name(stem, payload):
    """The imagineVTT scene the fight belongs to: one scene per encounter."""
    if payload.get('scene'):
        return payload['scene']
    name = payload.get('name') or stem
    name = name.replace(' — ', ' - ').replace('—', '-')
    return ('Random - ' + name) if stem.startswith('rnd-') else name


def combat_link(stem, payload):
    """The combat link: imagineVTT opens the scene and hands the encounter to the tracker."""
    envelope = {'v': 1, 'scene': scene_name(stem, payload), 'encounter': tracker_payload(payload)}
    return IMAGINE + '#combat=' + b64(envelope)


def inline(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)


def notes_html(notes):
    """The same small formatting the tracker supports: #, ##, -, **bold**, *italic*."""
    lines = notes if isinstance(notes, list) else str(notes).split('\n')
    out, in_list = [], False
    for line in lines:
        if line.startswith('- '):
            if not in_list: out.append('<ul>'); in_list = True
            out.append(f'<li>{inline(line[2:])}</li>'); continue
        if in_list: out.append('</ul>'); in_list = False
        if line.startswith('## '): out.append(f'<h4>{inline(line[3:])}</h4>')
        elif line.startswith('# '): continue  # the card already shows the name
        elif line.strip(): out.append(f'<p>{inline(line)}</p>')
    if in_list: out.append('</ul>')
    return '\n'.join(out)


def who(c):
    if 'custom' in c: return c['custom'].get('name', 'Unnamed')
    return c.get('name') or c.get('preset') or c.get('pc') or 'Unnamed'


def card(path, p):
    notes = p.get('notes') or []
    lines = notes if isinstance(notes, list) else str(notes).split('\n')
    sub = next((l.strip('*') for l in lines if l.startswith('*') and not l.startswith('**')), '')
    people = ' · '.join(html.escape(who(c)) for c in p.get('combatants', []))
    n = len(p.get('combatants', []))
    url = combat_link(path.stem, p)
    tracker_url = link(p)
    return f'''<article class="enc" id="{path.stem}">
  <h2>{html.escape(p.get('name', path.stem))}</h2>
  {f'<p class="sub">{inline(sub)}</p>' if sub else ''}
  <p class="who"><span>{n} combatant{'s' if n != 1 else ''}{' + all saved players' if p.get('pcs') is True else ''}</span> {people}</p>
  <div class="acts">
    <a class="btn primary" href="{html.escape(url)}" target="_blank" rel="noopener" title="Opens the scene in imagineVTT, which starts the fight in the tracker">▶ Start in imagineVTT</a>
    <a class="btn" href="{html.escape(tracker_url)}" target="_blank" rel="noopener">Tracker only</a>
    <button class="btn" type="button" data-copy="{html.escape(url)}">Copy link</button>
    <span class="src">scene: {html.escape(scene_name(path.stem, p))}</span>
    <span class="src">encounters/{html.escape(path.name)}</span>
  </div>
  <details><summary>Combat notes</summary><div class="notes">{notes_html(notes)}</div></details>
</article>'''


PAGE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Encounters — He Built the Same Room Twice</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=IM+Fell+English+SC&display=swap" rel="stylesheet">
<style>
:root{{--bg:#1d1f22; --slab:#26292d; --slab-2:#2e3237; --ink:#dcd5c3; --ink-soft:#a9a291; --muted:#7f848b;
  --vitae:#a3302f; --vitae-deep:#6e1a1a; --gold:#b89a5e; --rule:#3a3e44; --focus:#d9b56a; color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0; background:var(--bg); color:var(--ink); font-family:"EB Garamond",Georgia,serif; font-size:1.05rem; line-height:1.45}}
main{{max-width:52rem; margin:0 auto; padding:2rem 16px 4rem}}
h1{{font-family:"IM Fell English SC",Georgia,serif; font-weight:400; text-transform:lowercase; font-size:clamp(1.8rem,5vw,2.6rem); margin:0 0 .3rem}}
.lede{{color:var(--ink-soft); font-style:italic; margin:0 0 1.6rem}}
.enc{{background:var(--slab); border:1px solid var(--rule); padding:1rem 1.1rem; margin:0 0 1.1rem}}
h2.group{{font-family:"IM Fell English SC",Georgia,serif; font-weight:400; text-transform:lowercase; font-size:1.7rem; margin:2.2rem 0 .2rem; border-top:3px double var(--rule); padding-top:1rem}}
.enc h2{{font-family:"IM Fell English SC",Georgia,serif; font-weight:400; text-transform:lowercase; color:var(--gold); font-size:1.45rem; margin:0}}
.sub{{margin:.15rem 0 .5rem; color:var(--ink-soft); font-style:italic}}
.who{{margin:.4rem 0 .8rem; font-size:.95rem}}
.who span{{display:block; color:var(--muted); font-style:italic; font-size:.88rem}}
.acts{{display:flex; flex-wrap:wrap; align-items:center; gap:.5rem .7rem}}
.btn{{font:inherit; font-size:.95rem; color:var(--ink); background:var(--slab-2); border:1px solid var(--rule); padding:.35rem .8rem; cursor:pointer; text-decoration:none}}
.btn.primary{{background:var(--vitae-deep); border-color:var(--vitae); color:#f4efe4}}
.btn:hover{{border-color:var(--gold)}}
.btn:focus-visible,summary:focus-visible{{outline:2px solid var(--focus); outline-offset:2px}}
.src{{color:var(--muted); font-size:.85rem; font-family:ui-monospace,Menlo,Consolas,monospace}}
details{{margin-top:.8rem; border-top:1px solid var(--rule); padding-top:.5rem}}
summary{{cursor:pointer; color:var(--gold); font-family:"IM Fell English SC",Georgia,serif; text-transform:lowercase}}
.notes h4{{font-family:"IM Fell English SC",Georgia,serif; font-weight:400; text-transform:lowercase; color:var(--gold); margin:1rem 0 .3rem; font-size:1.1rem}}
.notes p{{margin:.4rem 0}} .notes ul{{margin:.3rem 0; padding-left:1.2rem}} .notes li{{margin:.2rem 0}}
.foot{{color:var(--muted); font-size:.9rem; font-style:italic}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.88em; background:var(--slab-2); padding:.05em .3em}}
</style>
</head>
<body>
<main>
<h1>Encounters</h1>
<p class="lede">Premade fights for the V:TM combat tracker, balanced for six players. Each one opens with its combat notes; the notes end with what to delete for a smaller table. <em>Start in imagineVTT</em> opens the fight's scene and the tracker together (close imagineVTT first); <em>Tracker only</em> opens just the tracker.</p>
{cards}
<p class="foot">Generated by <code>encounters/build.py</code> from the JSON files in <code>encounters/</code>. Edit those, then rebuild; don't edit this page.</p>
</main>
<script>
document.addEventListener('click', function (e) {{
  var b = e.target.closest('[data-copy]'); if (!b) return;
  var text = b.dataset.copy, label = b.dataset.label || (b.dataset.label = b.textContent);
  var done = function (ok) {{ b.textContent = ok ? 'Copied' : 'Copy failed'; setTimeout(function () {{ b.textContent = label; }}, 1400); }};
  // Older copy route: works on file:// and data: pages, where the Clipboard API is blocked.
  var legacy = function () {{
    var ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed; top:0; left:0; opacity:0';
    document.body.appendChild(ta); ta.select();
    var ok = false; try {{ ok = document.execCommand('copy'); }} catch (err) {{}}
    document.body.removeChild(ta); b.focus();
    return ok;
  }};
  if (legacy()) return done(true);
  try {{ navigator.clipboard.writeText(text).then(function () {{ done(true); }}, function () {{ done(false); }}); }}
  catch (err) {{ done(false); }}
}});
</script>
</body>
</html>
'''


def main():
    files = sorted(HERE.glob('*.json'))
    cards, payloads = [], {}
    for f in files:
        p = json.loads(f.read_text(encoding='utf-8'))
        payloads[f.stem] = p
        print(f'{f.name}: {len(p.get("combatants", []))} combatants, combat link {len(combat_link(f.stem, p))} chars')
    for prefix, title, blurb in GROUPS:
        group = [f for f in files if f.name.startswith(prefix)]
        if group:
            cards.append(f'<h2 class="group">{title}</h2>\n<p class="lede">{blurb}</p>')
            cards += [card(f, payloads[f.stem]) for f in group]
    rest = [f for f in files if not any(f.name.startswith(g[0]) for g in GROUPS)]
    cards += [card(f, payloads[f.stem]) for f in rest]
    OUT.write_text(PAGE.format(cards='\n'.join(cards)), encoding='utf-8', newline='\n')
    print(f'wrote {OUT.name}')

    # Keep the bible's encounter links current.
    if BIBLE.exists():
        text = BIBLE.read_text(encoding='utf-8')
        missing = set()
        def fix(m):
            stem = m.group(2)
            if stem not in payloads: missing.add(stem); return m.group(0)
            return f'{m.group(1)}{html.escape(combat_link(stem, payloads[stem]))}{m.group(3)}'
        new = re.sub(r'(<a [^>]*data-enc="([^"]+)"[^>]*?href=")[^"]*(")', fix, text)
        n = len(re.findall(r'data-enc="', new))
        if new != text: BIBLE.write_text(new, encoding='utf-8', newline='')
        print(f'bible: {n} encounter link(s) refreshed' + (f'; unknown: {sorted(missing)}' if missing else ''))


if __name__ == '__main__':
    main()
