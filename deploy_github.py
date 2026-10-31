import subprocess
import os

GIT_BIN = r"C:\Program Files\Git\cmd\git.exe"
GH_BIN = r"C:\Program Files\GitHub CLI\gh.exe"

env = os.environ.copy()
env['PATH'] = r'C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;' + env.get('PATH', '')

def run_cmd(cmd):
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print("Return code:", res.returncode)
    if res.stdout:
        print("Stdout:\n", res.stdout.strip())
    if res.stderr:
        print("Stderr:\n", res.stderr.strip())
    return res

# 1. git init
run_cmd([GIT_BIN, 'init'])

# 2. config user
run_cmd([GIT_BIN, 'config', 'user.name', 'harsh122345'])
run_cmd([GIT_BIN, 'config', 'user.email', 'harsh122345@users.noreply.github.com'])

# 3. branch -M main
run_cmd([GIT_BIN, 'branch', '-M', 'main'])

# 4. add .
run_cmd([GIT_BIN, 'add', '.'])

# 5. commit
run_cmd([GIT_BIN, 'commit', '-m', 'feat: Autonomous C++17 bot with risk-aware economic planner and interactive web visualizer'])

# 6. create repo and push
run_cmd([GH_BIN, 'repo', 'create', 'Subway_Escape', '--public', '--source=.', '--remote=origin', '--push'])
