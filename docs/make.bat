@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=uv run --extra docs sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

uv run --version >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'uv' command was not found. Install uv from https://docs.astral.sh/uv/
	echo.and ensure it is on your PATH, then re-run this script.
	echo.
	exit /b 1
)

if "%1" == "" goto help

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd
