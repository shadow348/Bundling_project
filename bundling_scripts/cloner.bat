@echo off
set REPO=https://github.com/shadow348/Bundling_project.git
set FOLDER=Bundling

echo 🚀 Cloning %REPO%
git clone %REPO%

cd %FOLDER%

echo 📦 Installing dependencies...
pip install -r requirements.txt

echo 📁 Creating empty folders if missing...

rem === Define your empty folders here ===
set FOLDERS=^
    bundling\bundling_scripts\backup
    bundling\bundling_scripts\click_screenshot
    bundling\bundling_scripts\exe_downloads
    bundling\bundling_scripts\networklog
    bundling\bundling_scripts\outpath ^
    bundling\bundling_scripts\screenshots ^
    bundling\bundling_scripts\taskCom ^
    bundling\bundling_scripts\video ^    
    

for %%F in (%FOLDERS%) do (
    if not exist "%%F" (
        echo Creating folder %%F
        mkdir "%%F"
    )
)

echo ✅ Setup complete!
pause
