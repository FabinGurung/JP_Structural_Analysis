"""Publish two source-controlled registries into the static site; no raw standards PDFs."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",default="site/data")
 out=Path(p.parse_args().output_dir);out.mkdir(parents=True,exist_ok=True)
 for source,name,expected in [
 ("registry/fem-workflow-map.v0.1.json","fem-workflow-map.v0.1.json","menus"),
 ("registry/nbc105-verified-rule-inventory.v0.1.json","nbc105-verified-rule-inventory.v0.1.json","registered_clauses")]:
  data=json.loads((ROOT/source).read_text())
  assert len(data[expected])==14
  (out/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
 print("FEM_WORKFLOW_AND_NEPAL_CODE_SCOPE_PROJECTION_PASS")
if __name__=="__main__":main()
