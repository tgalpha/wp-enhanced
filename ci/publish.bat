@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd .

:: script is at proj_root/ci/
cd /d %~dp0..

poetry build

for /F "tokens=*" %%i in ('poetry version -s') do poetry run twine check --strict dist\wp_enhanced-%%i*

if %errorlevel% == 0 (
    poetry publish
)

popd
