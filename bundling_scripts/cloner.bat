@echo off
set REPO=https://github.com/shadow348/Bundling_project.git
set FOLDER=Bundling_project

echo Cloning %REPO%
git clone %REPO%

cd %FOLDER%
pip install -r requirements.txt

echo ✅ Setup complete!
pause