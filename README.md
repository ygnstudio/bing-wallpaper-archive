# Bing Wallpaper Archive

## 项目简介

Bing Wallpaper Archive 是一个基于 GitHub 的自动化壁纸归档项目，用于保存每日 Bing 1080P 壁纸。

## 当前状态

当前项目处于 v0.1.0 项目骨架阶段。

项目目录、占位脚本、数据文件和 GitHub Actions 工作流已经初始化，但真实的壁纸下载、缩略图生成、索引生成和 README 自动生成逻辑尚未实现。

## 功能范围

本项目计划实现：

- 自动获取每日 Bing 壁纸。
- 只保存 1080P 图片版本。
- 按年份和月份归档图片。
- 为 README 预览生成缩略图。
- 生成稳定的 JSON 索引数据。
- 通过自动化脚本更新 README。
- 通过 GitHub Actions 定时运行。

## 项目边界

本项目不会包含：

- UHD 或 4K 图片下载。
- 多分辨率图片管理。
- 数据库。
- 复杂前端图库。
- 搜索系统。
- 用户账号。
- 多地区壁纸源。
- 商业化功能。

## 目录结构

```text
bing-wallpaper-archive/
  .github/
    workflows/
      update.yml

  scripts/
    download.py
    generate_thumbnail.py
    generate_index.py
    generate_readme.py

  wallpapers/
  thumbnails/

  data/
    index.json
    hash.json

  README.md
  project.json
```

## 自动化说明

GitHub Actions 工作流定义在 `.github/workflows/update.yml`。

该工作流支持手动触发和定时触发。当前工作流会按顺序运行以下占位脚本：

1. 下载每日 1080P 壁纸。
2. 生成缩略图。
3. 生成 `data/index.json`。
4. 生成 README 内容。
5. 如果文件发生变化，则提交并推送更新。

v0.1.0 阶段的脚本只作为占位入口，暂时不会执行真实归档更新。

## License

MIT
