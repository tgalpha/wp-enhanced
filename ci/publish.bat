@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd .

:: script is at proj_root/ci/
cd /d %~dp0..

poetry build
poetry publish

popd
