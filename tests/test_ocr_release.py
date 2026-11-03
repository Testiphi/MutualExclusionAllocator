"""OCR bundle completeness and immutable model binding without large test weights."""
import hashlib,json,unittest
from production_release_tools import OCR_FILES,OCR_ASSET_FILES,allowed,verify_ocr

class OcrBundleTests(unittest.TestCase):
    def fixture(self):
        contents={name:b'fixture' for name in OCR_FILES}
        assets={name:{'sha256':hashlib.sha256(contents[name]).hexdigest(),'bytes':len(contents[name])} for name in OCR_ASSET_FILES}
        contents['production/ocr-assets.json']=json.dumps(assets).encode()
        contents['production/ocr-models.json']=json.dumps({'models':{key:{'path':name,'sha256':assets[name]['sha256']} for key,name in zip(('det','rec','keys'),('ocr/v5_det.onnx','ocr/v5_rec.onnx','ocr/v5_keys.txt'))}}).encode()
        return contents
    def test_complete_assets_and_models_are_bound(self):
        contents=self.fixture();verify_ocr(contents)
        contents['ocr/v5_det.onnx']=b'changed'
        with self.assertRaises(ValueError):verify_ocr(contents)
    def test_partial_runtime_and_conflicting_model_manifest_rejected(self):
        contents=self.fixture();del contents['backend/map_ocr_supervisor.py']
        with self.assertRaises(ValueError):verify_ocr(contents)
        contents=self.fixture();models=json.loads(contents['production/ocr-models.json']);models['models']['det']['sha256']='0'*64
        contents['production/ocr-models.json']=json.dumps(models).encode()
        with self.assertRaises(ValueError):verify_ocr(contents)
    def test_private_files_and_arbitrary_models_still_excluded(self):
        for name in ['ocr/extra.onnx','ocr/../accounts.sqlite3','config.json','queue.json','recognition.sqlite3','media/image.png','gauntlet_data.xlsx']:
            self.assertFalse(allowed(name),name)

if __name__=='__main__':unittest.main()
