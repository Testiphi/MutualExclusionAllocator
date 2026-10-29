"""Lossless column fitting and maintenance-save integration."""
import io
from pathlib import Path
import re
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET

from autofit_xlsx import MIN_CAR_WIDTH, fit_xlsx_bytes, main
from data_tools import replace_with_backup


N = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
Q = lambda n: '{' + N + '}' + n


def workbook_bytes():
    stream = io.BytesIO()
    sheet = f'''<worksheet xmlns="{N}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:x14ac="http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac" mc:Ignorable="x14ac"><sheetViews><sheetView workbookViewId="0"><pane xSplit="2" ySplit="1" topLeftCell="C2" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="2" width="14" customWidth="1"/><col min="3" max="5" width="16" customWidth="1" hidden="1"/></cols><sheetData><row r="1" ht="14"><c r="A1" t="inlineStr"><is><t>大地图</t></is></c><c r="B1" t="inlineStr"><is><t>小地图</t></is></c><c r="C1" s="1" t="inlineStr"><is><t>ap0</t></is></c><c r="D1" s="1" t="inlineStr"><is><t>迈凯伦p1★5</t></is></c><c r="E1" s="1" t="inlineStr"><is><t>杰哥[OC]</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>很长很长的大地图名称</t></is></c><c r="B2" t="inlineStr"><is><t>地图</t></is></c><c r="C2" s="1"><v>30.419</v></c><c r="D2" s="1"><v>18.399</v></c><c r="E2" s="1"><f>C2-0.1</f><v>30.319</v></c></row></sheetData><mergeCells count="1"><mergeCell ref="A2:A3"/></mergeCells></worksheet>'''
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{N}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="五区_高手" sheetId="1" r:id="r1"/><sheet name="高手参考_原始配置" sheetId="2" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr('xl/styles.xml', f'<styleSheet xmlns="{N}"><fonts count="2"><font><sz val="11"/></font><font><name val="宋体"/><sz val="10"/></font></fonts><cellXfs count="2"><xf fontId="0"/><xf fontId="1"/></cellXfs></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml', sheet)
        z.writestr('xl/worksheets/sheet2.xml', sheet)
        z.comment = b'preserve package comment'
    return stream.getvalue()


class AutoFitTests(unittest.TestCase):
    def test_only_columns_change_and_reference_sheet_is_byte_identical(self):
        before = workbook_bytes()
        after, report = fit_xlsx_bytes(before)
        self.assertEqual(len(report), 1)
        with zipfile.ZipFile(io.BytesIO(before)) as old, zipfile.ZipFile(io.BytesIO(after)) as new:
            self.assertEqual(old.comment, new.comment)
            self.assertEqual(old.namelist(), new.namelist())
            for name in old.namelist():
                if name != 'xl/worksheets/sheet1.xml':
                    self.assertEqual(old.read(name), new.read(name))
            remove = lambda raw: re.sub(rb'<cols\b[^>]*>.*?</cols>', b'', raw, flags=re.DOTALL)
            self.assertEqual(remove(old.read('xl/worksheets/sheet1.xml')),
                             remove(new.read('xl/worksheets/sheet1.xml')))

    def test_long_chinese_star_and_OC_headers_fit_without_widening_map_columns(self):
        fitted, _ = fit_xlsx_bytes(workbook_bytes())
        with zipfile.ZipFile(io.BytesIO(fitted)) as z:
            root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        cols = root.find(Q('cols'))
        widths = {ci: float(col.get('width')) for col in cols for ci in
                  range(int(col.get('min')), int(col.get('max')) + 1)}
        self.assertEqual(widths[1], 14)
        self.assertEqual(widths[2], 14)
        self.assertGreaterEqual(widths[3], MIN_CAR_WIDTH)
        self.assertGreater(widths[4], widths[3])
        self.assertGreater(widths[5], widths[3])
        self.assertTrue(all(col.get('hidden') == '1' for col in cols
                            if int(col.get('min')) >= 3))

    def test_idempotent_no_padding_accumulation(self):
        once, _ = fit_xlsx_bytes(workbook_bytes())
        twice, report = fit_xlsx_bytes(once)
        self.assertEqual(once, twice)
        self.assertEqual(report, [])

    def test_shared_save_entry_fits_and_backs_up_original_target(self):
        with tempfile.TemporaryDirectory() as temp:
            target, candidate = Path(temp) / 'scores.xlsx', Path(temp) / 'staged.xlsx'
            target.write_bytes(b'original file protected by backup')
            candidate.write_bytes(workbook_bytes())
            replace_with_backup(candidate, target)
            self.assertEqual(fit_xlsx_bytes(target.read_bytes())[1], [])
            backups = list(Path(temp).glob('scores.xlsx.*.bak'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b'original file protected by backup')

    def test_json_replacement_is_not_treated_as_workbook(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate, target = Path(temp) / 'staged', Path(temp) / 'scores.json'
            candidate.write_text('{"value":1}', encoding='utf-8')
            replace_with_backup(candidate, target)
            self.assertEqual(target.read_text(encoding='utf-8'), '{"value":1}')

    def test_preview_never_overwrites_input(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'source.xlsx', Path(temp) / 'preview.xlsx'
            before = workbook_bytes(); source.write_bytes(before)
            main(['--input', str(source), '--output', str(output)])
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(fit_xlsx_bytes(output.read_bytes())[1], [])

    def test_existing_exporter_uses_the_automatic_save_entry(self):
        import json
        import openpyxl
        from export_xlsx import export_workbook
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'scores.json', Path(temp) / 'export.xlsx'
            tiers = lambda: {tier: [] for tier in ('理论', '高手', '普通', '自动')}
            track = {'大地图': '罗马', '小地图': '罗马小道', '五区': tiers(), '四区': tiers()}
            track['五区']['高手'] = [{'cars': [{'name': '迈凯伦p1', 'stars': 5}], 'time': 18.399}]
            track['五区']['普通'] = [{'cars': [{'name': '迈凯伦p1', 'stars': 5}]}]
            source.write_text(json.dumps({'tracks': [track]}, ensure_ascii=False), encoding='utf-8')
            export_workbook(source, output)
            self.assertEqual(fit_xlsx_bytes(output.read_bytes())[1], [])
            book = openpyxl.load_workbook(output)
            try:
                self.assertEqual(book['五区_高手']['C1'].value, '迈凯伦p1★5')
                self.assertEqual(book['五区_高手']['C2'].value, 18.399)
                width = next(col.width for col in book['五区_高手'].column_dimensions.values()
                             if col.min <= 3 <= col.max)
                self.assertGreater(width, MIN_CAR_WIDTH)
            finally:
                book.close()


if __name__ == '__main__':
    unittest.main()
