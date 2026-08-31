import json, subprocess, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PipelineTests(unittest.TestCase):
    def test_outputs_and_constraints(self):
        subprocess.run([sys.executable,'run_model.py'],cwd=ROOT,check=True)
        m=json.loads((ROOT/'results/metrics.json').read_text(encoding='utf-8'))
        self.assertGreater(m['data_audit']['valid_form2_rows'],0)
        self.assertEqual(m['classification']['n'],m['classification']['class_counts']['高钾']+m['classification']['class_counts']['铅钡'])
        self.assertTrue(0<=m['classification']['centroid_accuracy']<=1)
        self.assertEqual(len(m['unknown_predictions']),8)
        self.assertGreaterEqual(len(list((ROOT/'figures').glob('*.svg'))),4)

if __name__=='__main__': unittest.main()
