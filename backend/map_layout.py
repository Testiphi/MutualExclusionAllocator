"""Stateless screenshot-to-five-map parser; no game-action or OCR dependency.

Input is the current image size, actual OCR rows and an explicit server catalog.
No button, vehicle, previous frame, filename or expected lineup participates.
The three supported UI families have calibrated proportional text geometry;
unknown framing/layouts abstain. Every result has exactly five explicit slots.
"""
from difflib import SequenceMatcher
from math import isfinite
from statistics import median
import unicodedata

SCHEMA_VERSION = 1
TITLE_MIN = .90
TEXT_MIN = .70
NAME_MIN = .72
PAIR_SUM_MIN = 1.65
AMBIGUITY_MARGIN = .30
TITLES = {'资格赛': 'qualifier', '挑战': 'challenge',
          '资格赛结果': 'result_cards', '资格赛失利': 'result_cards', '防御': 'defense_cards'}
DIALOGS = {'重新开始', '挑战胜利', '挑战结果', '比赛结果', '对手信息'}
UI_LABELS = {'为该赛道', '选择车辆', '更换车辆', '为该赛道选择车辆'}
ROW_RESULT_TITLES = {'防御结果': 'defense_rows', '挑战获胜': 'attack_rows',
                     '挑战失利': 'attack_rows', '挑战胜利': 'attack_rows', '挑战失败': 'attack_rows'}


def _norm(text):
    return ''.join(unicodedata.normalize('NFKC', text).split()).casefold()


def _score(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b), autojunk=False).ratio()


def _number(n):
    return not isinstance(n, bool) and isinstance(n, (int, float)) and isfinite(n)


def _empty(slot):
    return {'slot': slot, 'state': 'unresolved', 'big': None, 'small': None,
            'observed': [], 'boxes': [], 'name_similarity': None, 'reason': 'missing_map'}


def _result(server, version, *, layout=None, reason='unrecognized_layout'):
    return {'schema_version': SCHEMA_VERSION, 'server': server, 'catalog_version': version,
            'layout': layout, 'status': 'rejected', 'reason': reason,
            'slots': [_empty(i) for i in range(1, 6)],
            'needs_user_confirmation': True, 'diagnostics': {}}


def _catalog(catalog):
    tracks = catalog.get('tracks') if isinstance(catalog, dict) else catalog
    if not isinstance(tracks, (list, tuple)) or not 1 <= len(tracks) <= 2048:
        raise ValueError('invalid_catalog')
    pairs = []
    for item in tracks:
        if not isinstance(item, dict):
            raise ValueError('invalid_catalog')
        big, small = item.get('big', item.get('大地图')), item.get('small', item.get('小地图'))
        if not all(isinstance(s, str) and s.strip() for s in (big, small)):
            raise ValueError('invalid_catalog')
        pairs.append((big, small))
    if len({(_norm(b), _norm(s)) for b, s in pairs}) != len(pairs):
        raise ValueError('duplicate_catalog_pair')
    return pairs


def _rows(ocr, width, height):
    if not isinstance(ocr, (list, tuple)) or len(ocr) > 2000:
        raise ValueError('invalid_ocr')
    result, seen = [], set()
    for item in ocr:
        if not isinstance(item, dict):
            raise ValueError('invalid_ocr')
        text, confidence, box = item.get('text'), item.get('confidence'), item.get('box')
        if not isinstance(text, str) or len(text)>256 or not _number(confidence) or not 0 <= confidence <= 1:
            raise ValueError('invalid_ocr')
        if not isinstance(box, (list, tuple)) or len(box) != 4 or not all(_number(x) for x in box):
            raise ValueError('invalid_ocr')
        x, y, w, h = box
        if w <= 0 or h <= 0 or not 0 <= x+w/2 <= width or not 0 <= y+h/2 <= height:
            raise ValueError('invalid_ocr')
        key = (_norm(text), tuple(box))
        if not text.strip() or key in seen:
            continue
        seen.add(key)
        result.append({'id': len(result), 'text': text, 'confidence': confidence,
                       'box': list(box), 'cx': x+w/2, 'cy': y+h/2, 'h': h})
    return result


def _rank(big, small, pairs):
    candidates = []
    for b, s in pairs:
        x, y = _score(big, b), _score(small, s)
        if min(x, y) >= NAME_MIN and x+y >= PAIR_SUM_MIN:
            candidates.append({'big': b, 'small': s, 'similarity': min(x, y), 'rank': min(x,y)*2+x+y})
    candidates.sort(key=lambda r: (-r['rank'], r['big'], r['small']))
    if not candidates:
        return None, []
    if len(candidates) > 1 and candidates[0]['similarity']-candidates[1]['similarity'] < AMBIGUITY_MARGIN:
        return None, candidates
    return candidates[0], candidates


def _roles(row, pairs):
    return (any(_score(row['text'], b) >= NAME_MIN for b, _ in pairs),
            any(_score(row['text'], s) >= NAME_MIN for _, s in pairs))


def _cells(width, expanded=None):
    left, right, pitch = .045*width, .975*width, .089*width
    if expanded is None:
        return [(left+(right-left)*i/5, left+(right-left)*(i+1)/5) for i in range(5)]
    wide = right-left-4*pitch
    edges = [left]
    for i in range(1, 6):
        edges.append(edges[-1]+(wide if i == expanded else pitch))
    return list(zip(edges[:-1], edges[1:]))


def _slot_for(cx, cells, width):
    # Do not decide a boundary hit by list order.
    hits = [i+1 for i,(l,r) in enumerate(cells) if l+.005*width < cx < r-.005*width]
    return hits[0] if len(hits) == 1 else None


def _expanded_index(cx, width, centered_header=False):
    offset = (.975-.045-4*.089)/2 if centered_header else .156
    expected = [(.045+offset+(i-1)*.089)*width for i in range(1,6)]
    hits = [i+1 for i,x in enumerate(expected) if abs(cx-x) <= .033*width]
    return hits[0] if len(hits) == 1 else None


def _matched(slot, match, rows, cell):
    return {'slot': slot, 'state': 'matched', 'big': match['big'], 'small': match['small'],
            'observed': [r['text'] for r in rows], 'boxes': [r['box'] for r in rows],
            'ocr_confidence': [r['confidence'] for r in rows],
            'name_similarity': round(match['similarity'], 4), 'reason': 'matched',
            'cell': [round(x,2) for x in cell]}


def _inline(text, pairs):
    # Both names must be read from this row. Never complete a missing name.
    text = _norm(text)
    options = {}
    for split in range(1,len(text)):
        winner, candidates = _rank(text[:split],text[split:],pairs)
        for c in candidates:
            key=(c['big'],c['small'])
            if key not in options or c['rank'] > options[key]['rank']:
                options[key]=c
    ranked=sorted(options.values(),key=lambda c:(-c['rank'],c['big'],c['small']))
    if not ranked:
        return None
    if len(ranked)>1 and ranked[0]['similarity']-ranked[1]['similarity']<AMBIGUITY_MARGIN:
        return None
    return ranked[0]


def _horizontal_map_header(rows, pairs, width, height):
    band=[r for r in rows if TEXT_MIN <= r['confidence'] and .22*height <= r['cy'] <= .31*height]
    candidates=[]
    for row in band:
        match=_inline(row['text'],pairs)
        if match:
            candidates.append((row['cx'],match,[row]))
    # Some OCR detectors split the horizontal big/small header into two boxes.
    for a in band:
        for b in band:
            if a['cx'] >= b['cx'] or abs(a['cy']-b['cy']) > .018*height:
                continue
            gap=b['box'][0]-(a['box'][0]+a['box'][2])
            if not -.005*width <= gap <= .035*width:
                continue
            match,_=_rank(a['text'],b['text'],pairs)
            if match:
                left=min(a['box'][0],b['box'][0]);right=max(a['box'][0]+a['box'][2],b['box'][0]+b['box'][2])
                candidates.append(((left+right)/2,match,[a,b]))
    located=[]
    for cx,match,parts in candidates:
        index=_expanded_index(cx,width,centered_header=True)
        if index:
            located.append((index,match,parts))
    if len(located)!=1:
        return None
    return located[0]


def _finish(out, boundary=()):
    matches=[(s['big'],s['small']) for s in out['slots'] if s['state']=='matched']
    duplicates={p for p in matches if matches.count(p)>1}
    for slot in out['slots']:
        if (slot['big'],slot['small']) in duplicates:
            slot.update(state='ambiguous',big=None,small=None,reason='duplicate_map_in_lineup')
    if boundary:out['diagnostics']['boundary_rows']=list(boundary)
    complete=all(s['state']=='matched' for s in out['slots']) and not boundary
    out.update(status='complete' if complete else 'partial',reason='five_maps_observed' if complete else 'incomplete_or_ambiguous')
    return out


def _pair_slot(index,parts,pairs,width,height,cell):
    parts=sorted(parts,key=lambda r:(r['cy'],r['cx']))
    slot=_empty(index);slot.update(observed=[r['text'] for r in parts],boxes=[r['box'] for r in parts])
    if len(parts)>2:
        slot.update(state='ambiguous',reason='cell_text_conflict');return slot
    if len(parts)!=2:return slot
    a,b=parts
    if not .003*height <= b['cy']-a['cy'] <= .07*height or abs(a['cx']-b['cx'])>.035*width:
        slot['reason']='map_line_geometry_conflict';return slot
    match,alternatives=_rank(a['text'],b['text'],pairs)
    if match is None:
        slot.update(state='ambiguous' if alternatives else 'unresolved',
                    reason='catalog_match_ambiguous' if alternatives else 'unknown_map_pair')
        return slot
    return _matched(index,match,parts,cell)


def _special_layout(rows,width,height):
    candidates=[]
    for row in rows:
        if row['confidence']<TITLE_MIN:continue
        title=_norm(row['text'])
        if title=='对手信息' and .30*width<row['cx']<.70*width and .065*height<row['cy']<.22*height:
            candidates.append(('opponent_preview',row))
        elif title=='挑战详情' and .30*width<row['cx']<.70*width and .025*height<row['cy']<.17*height:
            candidates.append(('challenge_detail_rows',row))
        elif title in ROW_RESULT_TITLES and .18*height<row['cy']<.34*height:
            if (title=='防御结果' and row['cx']<.30*width) or (title!='防御结果' and .35*width<row['cx']<.65*width):
                candidates.append((ROW_RESULT_TITLES[title],row))
    return candidates


def _fixed_layout(out,layout,title,rows,pairs,width,height):
    out['layout']=layout;out['diagnostics']['page_title']=_norm(title['text'])
    assigned={i:[] for i in range(1,6)};boundary=[]
    if layout=='opponent_preview':
        left,right=.073*width,.928*width
        cells=[(left+(right-left)*i/5,left+(right-left)*(i+1)/5) for i in range(5)]
        out['diagnostics'].update(orientation='horizontal',cells=[[round(x,2) for x in c] for c in cells])
        selected=[r for r in rows if r['confidence']>=TEXT_MIN and .34*height<r['cy']<.49*height and left<r['cx']<right]
    else:
        column=(.42*width,.60*width)
        base,pitch=(.325,.09) if layout=='challenge_detail_rows' else (.35,.07)
        cells=[((base+pitch*i)*height,(base+pitch*(i+1))*height) for i in range(5)]
        out['diagnostics'].update(orientation='vertical',rows=[[round(x,2) for x in c] for c in cells],name_column=list(column))
        selected=[r for r in rows if r['confidence']>=TEXT_MIN and column[0]<r['cx']<column[1] and cells[0][0]<r['cy']<cells[-1][1]]
        extra=[r['box'] for r in rows if r['confidence']>=TEXT_MIN and column[0]<r['cx']<column[1]
               and cells[-1][1]<=r['cy']<(.865 if layout=='challenge_detail_rows' else .79)*height and any(_roles(r,pairs))]
        boundary.extend(extra)
    for row in selected:
        if _norm(row['text']) in UI_LABELS or not any(c.isalpha() for c in row['text']):continue
        index=_slot_for(row['cx'] if layout=='opponent_preview' else row['cy'],cells,width if layout=='opponent_preview' else height)
        if index is None:boundary.append(row['box'])
        else:assigned[index].append(row)
    for index in range(1,6):
        cell=cells[index-1] if layout=='opponent_preview' else column
        out['slots'][index-1]=_pair_slot(index,assigned[index],pairs,width,height,cell)
        if layout!='opponent_preview':out['slots'][index-1]['row']=[round(x,2) for x in cells[index-1]]
    return _finish(out,boundary)


def parse_map_layout(image_size, ocr, catalog, *, server='cn', catalog_version=None):
    """Return an observation requiring confirmation, never execution permission.

    ``image_size`` is (width,height); boxes are actual image coordinates, xywh.
    ``catalog`` contains only caller-approved (big,small) pairs, no scores needed.
    Unknown/ambiguous slots remain at their true ordinal, without compression.
    """
    out=_result(server,catalog_version)
    if server not in ('cn','global'):
        out['reason']='invalid_server';return out
    if not isinstance(image_size,(list,tuple)) or len(image_size)!=2 or not all(_number(x) for x in image_size):
        out['reason']='invalid_image_size';return out
    width,height=image_size
    if width<600 or height<300 or width*height>16_000_000 or not 1.30 <= width/height <= 2.20:
        out['reason']='unsupported_image_geometry';return out
    try:
        pairs=_catalog(catalog);rows=_rows(ocr,width,height)
    except ValueError as exc:
        out['reason']=str(exc);return out
    special=_special_layout(rows,width,height)
    if len(special)>1:
        out['reason']='page_title_conflict';return out
    selected_title=special[0][1]['id'] if special else None
    for row in rows:
        if (_norm(row['text']) in DIALOGS and row['confidence']>=TITLE_MIN
                and row['id']!=selected_title and .15*width<row['cx']<.85*width and .18*height<row['cy']<.85*height):
            out['reason']='modal_overlay';return out
    if special:return _fixed_layout(out,special[0][0],special[0][1],rows,pairs,width,height)
    titles=[r for r in rows if r['confidence']>=TITLE_MIN and _norm(r['text']) in TITLES
            and r['cx']<.23*width and .065*height <= r['cy'] <= .23*height]
    names={_norm(r['text']) for r in titles}
    if len(names)!=1:
        out['reason']='page_title_conflict' if names else 'page_title_missing';return out
    title=next(iter(names));layout=TITLES[title];out['layout']=layout
    out['diagnostics']['page_title']=title
    named=[r for r in rows if r['confidence']>=TEXT_MIN and .26*height <= r['cy'] <= .39*height]
    expanded=None;header=None
    if layout=='qualifier':
        bigs=[r for r in named if _roles(r,pairs)[0]]
        if len(bigs)<3:
            out['reason']='expanded_anchor_missing';return out
        anchor=max(bigs,key=lambda r:r['h']);others=[r['h'] for r in bigs if r['id']!=anchor['id']]
        comparable=[r for r in bigs if r['h']>=anchor['h']*.78]
        if anchor['h']<.038*height or anchor['h']<median(others)*1.35 or len(comparable)!=1:
            out['reason']='expanded_anchor_ambiguous';return out
        expanded=_expanded_index(anchor['cx'],width)
        if expanded is None:
            out['reason']='expanded_anchor_off_grid';return out
        out['diagnostics']['anchor']={'kind':'large_map_heading','box':anchor['box'],'slot':expanded}
    elif layout in ('challenge','defense_cards'):
        header=_horizontal_map_header(rows,pairs,width,height)
        if header:
            expanded=header[0]
            named=[r for r in rows if r['confidence']>=TEXT_MIN and .30*height <= r['cy'] <= .40*height]
            out['diagnostics']['anchor']={'kind':'horizontal_map_header','boxes':[r['box'] for r in header[2]],'slot':expanded}
        elif layout=='challenge':
            out['reason']='challenge_header_missing_or_ambiguous';return out
    if expanded is None:
        named=[r for r in rows if r['confidence']>=TEXT_MIN and .23*height <= r['cy'] <= .39*height]
    cells=_cells(width,expanded)
    out['diagnostics']['cells']=[[round(l,2),round(r,2)] for l,r in cells]
    out['diagnostics']['expanded_slot']=expanded
    relevant=[]
    for row in named:
        if any(_roles(row,pairs)):
            relevant.append(row);continue
        if _norm(row['text']) in UI_LABELS or not any(c.isalpha() for c in row['text']):
            continue
        slot=_slot_for(row['cx'],cells,width)
        # Unknown text in a name column is evidence too: do not silently
        # discard a new/garbled third name just because it is outside catalog.
        # The qualifier expanded map name occupies the left title lane; car
        # branding and selection prompts elsewhere in that wide cell do not.
        if slot and (header is None or slot!=expanded):
            if layout=='qualifier' and slot==expanded and abs(row['cx']-anchor['cx'])>.06*width:
                continue
            relevant.append(row)
    assigned={i:[] for i in range(1,6)};boundary=[]
    for row in relevant:
        slot=_slot_for(row['cx'],cells,width)
        if slot is None:boundary.append(row['box'])
        else:assigned[slot].append(row)
    for i in range(1,6):
        parts=sorted(assigned[i],key=lambda r:(r['cy'],r['cx']))
        slot=out['slots'][i-1]
        if header and i==expanded:
            if parts:
                slot.update(state='ambiguous',reason='expanded_cell_text_conflict',observed=[r['text'] for r in parts])
            else:out['slots'][i-1]=_matched(i,header[1],header[2],cells[i-1])
            continue
        slot.update(observed=[r['text'] for r in parts],boxes=[r['box'] for r in parts])
        if len(parts)>2:
            slot.update(state='ambiguous',reason='cell_text_conflict');continue
        if len(parts)!=2:
            continue
        a,b=parts
        if b['cy']-a['cy']<.003*height or b['cy']-a['cy']>.07*height or abs(a['cx']-b['cx'])>.035*width:
            slot['reason']='map_line_geometry_conflict';continue
        match,alternatives=_rank(a['text'],b['text'],pairs)
        if match is None:
            slot.update(state='ambiguous' if alternatives else 'unresolved',
                        reason='catalog_match_ambiguous' if alternatives else 'unknown_map_pair')
            continue
        out['slots'][i-1]=_matched(i,match,parts,cells[i-1])
    return _finish(out,boundary)
