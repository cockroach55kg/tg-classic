import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'local-mac/src'
name,url,revision=sys.argv[1:]
repo=root/name
run=lambda command:subprocess.run(command,cwd=repo,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1','GIT_TERMINAL_PROMPT':'0'},check=True)
if not (repo/'.git').exists():
 repo.mkdir(parents=True,exist_ok=True)
 run(['git','init','-q'])
 run(['git','remote','add','origin',url])
run(['git','fetch','--depth','1','origin',revision])
run(['git','checkout','--detach','FETCH_HEAD'])
print(name,'ready at',revision)
