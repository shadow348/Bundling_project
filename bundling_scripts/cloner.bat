@echo off
set REPO=https://github.com/shadow348/Bundling_project.git
set FOLDER=Bundling_project

echo 🚀 Cloning %REPO%
git clone %REPO%

cd %FOLDER%


echo 📁 Creating empty folders if missing...

rem === Define your empty folders here ===
set FOLDERS=^
    bundling_scripts\backup ^
    bundling_scripts\click_screenshot ^
    bundling_scripts\exe_downloads ^
    bundling_scripts\networklog ^
    bundling_scripts\outpath ^
    bundling_scripts\screenshots ^
    bundling_scripts\taskCom ^
    bundling_scripts\video ^    
    

for %%F in (%FOLDERS%) do (
    if not exist "%%F" (
        echo Creating folder %%F
        mkdir "%%F"
    )
)

echo ✅ Setup complete!

echo 📦 Installing dependencies...
pip install -r requirements.txt
pause
