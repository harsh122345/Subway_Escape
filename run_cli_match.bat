@echo off
echo Running Subway Escape: submission\my_bot.exe vs sample_bot\cpp\basic_bot.exe (10 runs)
py -3 practice_arena\run_practice.py --bot "submission\my_bot.exe" --bot "sample_bot\cpp\basic_bot.exe" --runs 10 --seed 100
pause
