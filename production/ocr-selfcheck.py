"""Offline real CPU OCR smoke test; synthetic input only, no queue/business database."""
from pathlib import Path
import io
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    from PIL import Image,ImageDraw,ImageFont
    from backend.map_ocr_engine import MapOcrEngine
    from backend.map_recognition import validate_image
    manifest=json.loads((ROOT/'production/ocr-models.json').read_text())
    config={'vendor':None,'models':{key:{**item,'path':str(ROOT/item['path'])} for key,item in manifest['models'].items()}}
    image=Image.new('RGB',(1280,720),'white')
    ImageDraw.Draw(image).text((160,260),'RACEPICK',font=ImageFont.load_default(size=84),fill='black')
    stream=io.BytesIO();image.save(stream,format='PNG');raw=stream.getvalue();validate_image(raw,'image/png')
    started=time.monotonic();engine=MapOcrEngine(config);size,rows=engine.recognize(raw)
    assert size==(1280,720) and any('RACEPICK' in row['text'].replace(' ','').upper() for row in rows),rows
    print(json.dumps({'ocr_selfcheck':'passed','input':'synthetic RACEPICK','seconds':round(time.monotonic()-started,3),
                      'platform':sys.platform,'business_database_touched':False}))

if __name__=='__main__':main()
