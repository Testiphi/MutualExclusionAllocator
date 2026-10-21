"""Stage only by default. Activation never restarts services or changes Nginx."""
import argparse
from pathlib import Path
from production_release_tools import stage,activate

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=Path('/opt/racepick'))
 g=p.add_mutually_exclusive_group(required=True);g.add_argument('--bundle',type=Path);g.add_argument('--version')
 p.add_argument('--activate',action='store_true');a=p.parse_args()
 if a.bundle:
  a.base.mkdir(parents=True,exist_ok=True);a.base.chmod(0o755)
  target=stage(a.bundle,a.base/'releases');identity=target.name;print('已校验并暂存：'+str(target))
 else:identity=a.version
 if a.activate:print('已切换应用版本；上一版本：'+str(activate(a.base,identity)))
 else:print('未切换版本，未启动服务，未改Nginx')
if __name__=='__main__':main()
