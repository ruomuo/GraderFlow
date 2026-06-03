$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$excludeModules = @(
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib.tests",
    "numpy.tests",
    "pandas.tests",
    "pytest",
    "setuptools",
    "wheel",
    "tensorboard",
    "tensorboardX",
    "clearml",
    "comet_ml",
    "wandb",
    "faiss",
    "paddle",
    "paddleocr"
)

$excludeArgs = @()
foreach ($m in $excludeModules) {
    $excludeArgs += "--exclude-module"
    $excludeArgs += $m
}

$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "批量阅卷系统",
    "--icon", "yuejuan.ico",
    "--add-data", "config;config",
    "--hidden-import", "pyzbar.pyzbar",
    "--collect-binaries", "pyzbar",
    "main.py"
) + $excludeArgs

Write-Host "开始打包（单文件）..."
python @args
Write-Host "打包完成：dist\批量阅卷系统.exe"
