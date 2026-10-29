"""Content-based car-column widths for RacePick maintenance workbooks.

Only <cols> in the twelve standard sheets can change. Scores, formulas, styles,
sheet views, merged regions and independent reference sheets remain byte intact.
"""
import argparse
from copy import deepcopy
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
import unicodedata
import zipfile
from xml.etree import ElementTree as ET


NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q = lambda name: '{' + NS + '}' + name
MIN_CAR_WIDTH = 7.453125
HEADER_PADDING = 3.0  # Text margins and the filter dropdown.
BODY_PADDING = 1.5
SHEET_NAME = re.compile(r'^(五区|四区)_((理论|高手)(_特殊跑法)?|普通|自动)$')


def _column(address):
    result = 0
    for char in re.match(r'[A-Z]+', address).group():
        result = result * 26 + ord(char) - 64
    return result


def _text_width(text, font_size=10):
    """Conservative Songti-width estimate; no Office, Pillow or macro required."""
    widths = []
    for line in str(text).splitlines() or ['']:
        widths.append(sum(0 if unicodedata.combining(char) else
                          2 if unicodedata.east_asian_width(char) in 'FWA' else
                          4 if char == '\t' else 1 for char in line))
    return max(widths) * font_size / 10


def _cell_text(cell, shared):
    value = cell.find(Q('v'))
    value = value.text if value is not None else None
    kind = cell.get('t', 'n')
    if kind == 's':
        return shared[int(value)] if value is not None else ''
    if kind == 'inlineStr':
        return ''.join(node.text or '' for node in cell.iter(Q('t')))
    if kind == 'n' and value is not None:
        try:
            return format(float(value), '.15g')
        except ValueError:
            pass
    return value or ''


def fit_xlsx_bytes(raw):
    """Return (candidate bytes, report), without writing or changing cell payloads."""
    report = []
    replacements = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('工作簿 ZIP 损坏，未调整列宽')
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        targets = {node.get('Id'): node.get('Target') for node in
                   ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(t.text or '' for t in node.iter(Q('t'))) for node in
                      ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        style_sizes = [10.0]
        if 'xl/styles.xml' in archive.namelist():
            styles = ET.fromstring(archive.read('xl/styles.xml'))
            fonts = styles.find(Q('fonts'))
            font_sizes = [float(font.find(Q('sz')).get('val', '10'))
                          if font.find(Q('sz')) is not None else 10.0 for font in fonts]
            style_sizes = [font_sizes[int(xf.get('fontId', '0'))]
                           for xf in styles.find(Q('cellXfs'))]
        for sheet in workbook.find(Q('sheets')):
            title = sheet.get('name', '')
            if not SHEET_NAME.fullmatch(title):
                continue
            target = targets[sheet.get('{' + REL + '}id')]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            original = archive.read(member)
            tree = ET.fromstring(original)
            cells = list(tree.iter(Q('c')))
            headers = {_column(c.get('r')): _cell_text(c, shared) for c in cells
                       if re.fullmatch(r'[A-Z]+1', c.get('r', ''))}
            first = 4 if title.endswith('_特殊跑法') else 3
            car_columns = {ci for ci, text in headers.items() if ci >= first and text}
            if not car_columns:
                continue
            desired = {ci: MIN_CAR_WIDTH for ci in car_columns}
            for cell in cells:
                ci = _column(cell.get('r'))
                if ci not in car_columns:
                    continue
                text = _cell_text(cell, shared)
                if not text:
                    continue
                row = int(re.sub(r'[A-Z]+', '', cell.get('r')))
                size = style_sizes[int(cell.get('s', '0'))]
                desired[ci] = max(desired[ci], _text_width(text, size) +
                                  (HEADER_PADDING if row == 1 else BODY_PADDING))
            desired = {ci: math.ceil(width * 256) / 256 for ci, width in desired.items()}
            old_cols = tree.find(Q('cols'))
            old_cols = list(old_cols) if old_cols is not None else []
            effective = {}
            outside = []
            for node in old_cols:
                lo, hi = int(node.get('min')), int(node.get('max'))
                for ci in car_columns:
                    if lo <= ci <= hi:
                        effective[ci] = node.attrib.copy()
                # Keep all untargeted column attributes, including hidden/outline.
                remaining = []
                start = lo
                for ci in sorted(c for c in car_columns if lo <= c <= hi):
                    if start < ci:
                        remaining.append((start, ci - 1))
                    start = ci + 1
                if start <= hi:
                    remaining.append((start, hi))
                for a, b in remaining:
                    clone = deepcopy(node)
                    clone.set('min', str(a)); clone.set('max', str(b))
                    outside.append(clone)
            new_cols = outside
            changes = []
            for ci, width in sorted(desired.items()):
                attrs = effective.get(ci, {}).copy()
                previous = attrs.get('width')
                attrs.update(min=str(ci), max=str(ci), width=str(width), customWidth='1')
                attrs.pop('bestFit', None)
                new_cols.append(ET.Element(Q('col'), attrs))
                if previous is None or float(previous) != width:
                    changes.append({'column': ci, 'header': headers[ci],
                                    'old_width': float(previous) if previous else None,
                                    'new_width': width})
            if not changes:
                continue
            prefix = re.search(rb'<((?:\w+:)?)worksheet\b', original).group(1)
            ET.register_namespace(prefix.decode().rstrip(':'), NS)
            content = b''.join(ET.tostring(c, encoding='utf-8') for c in
                               sorted(new_cols, key=lambda c: int(c.get('min'))))
            start_tag = re.search(b'<' + prefix + rb'cols\b[^>]*>', original)
            if start_tag:
                close = b'</' + prefix + b'cols>'
                end = start_tag.end() if start_tag.group().endswith(b'/>') else original.index(close, start_tag.end()) + len(close)
                opening = start_tag.group()[:-1].rstrip(b'/') + b'>'
                candidate = original[:start_tag.start()] + opening + content + close + original[end:]
            else:
                at = re.search(b'<' + prefix + rb'sheetData\b', original).start()
                candidate = original[:at] + b'<' + prefix + b'cols>' + content + b'</' + prefix + b'cols>' + original[at:]
            replacements[member] = candidate
            report.append({'sheet': title, 'columns': changes})
        if not replacements:
            return raw, []
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as result:
            result.comment = archive.comment
            for item in archive.infolist():
                result.writestr(item, replacements.get(item.filename, archive.read(item.filename)))
    return output.getvalue(), report


def autofit_file(path):
    """Fit a staged workbook; caller owns backing up the actual target file."""
    path = Path(path)
    before = path.read_bytes()
    after, report = fit_xlsx_bytes(before)
    if after == before:
        return report
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.xlsx', delete=False) as f:
            temporary = Path(f.name)
            f.write(after); f.flush(); os.fsync(f.fileno())
        if path.read_bytes() != before:
            raise ValueError('列宽调整期间输入变化，未替换')
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='按内容适配标准成绩表车辆列宽，保留所有值及原样式')
    parser.add_argument('--input', type=Path, default=Path(__file__).parent / 'gauntlet_data.xlsx')
    parser.add_argument('--output', type=Path, help='独立预览工作簿；不覆盖输入')
    parser.add_argument('--write', action='store_true', help='备份后原位调整；默认只报告')
    args = parser.parse_args(argv)
    if args.write and args.output:
        parser.error('--write 与 --output 不能同时使用')
    if args.output and args.output.resolve() == args.input.resolve():
        parser.error('原位调整请使用 --write')
    try:
        before = args.input.read_bytes()
        after, report = fit_xlsx_bytes(before)
        target = args.input if args.write else args.output
        if target and (args.output or after != before):
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.xlsx', delete=False) as f:
                    temporary = Path(f.name); f.write(after)
                if args.input.read_bytes() != before:
                    raise ValueError('预检后输入变化，未替换')
                from data_tools import replace_with_backup
                replace_with_backup(temporary, target)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        print(json.dumps({'written': bool(target and (args.output or after != before)),
                          'sheets': report}, ensure_ascii=False))
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError, KeyError) as error:
        parser.exit(1, '列宽调整失败: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
