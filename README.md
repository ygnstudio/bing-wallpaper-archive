# Bing Wallpaper Archive

Bing Wallpaper Archive 是一个个人自用的 Bing 壁纸自动归档项目。

项目会自动归档每日 Bing 1080P 壁纸，并生成缩略图、索引数据和 README 展示内容。后续该项目会接入 `ygnstudio.github.io`，作为雁归南 Studio 官网中的一个项目展示内容。

---

## 当前状态

当前版本：

```text
v0.2.1
```

当前阶段：

```text
长期维护
```

---

## 最新壁纸

**日期：** 2026-07-09

**标题：** 陆地与海洋的鸟瞰图

**版权：** 陆地与海洋的鸟瞰图，维多利亚州，澳大利亚 (© Nearmap/Getty Images)

[![2026-07-09](thumbnails/2026/07/20260709.jpg)](wallpapers/2026/07/20260709.jpg)

---

## 最近壁纸

| 日期 | 预览 |
|---|---|
| 2026-07-09 | [![2026-07-09](thumbnails/2026/07/20260709.jpg)](wallpapers/2026/07/20260709.jpg) |
| 2026-07-08 | [![2026-07-08](thumbnails/2026/07/20260708.jpg)](wallpapers/2026/07/20260708.jpg) |
| 2026-07-07 | [![2026-07-07](thumbnails/2026/07/20260707.jpg)](wallpapers/2026/07/20260707.jpg) |
| 2026-01-28 | [![2026-01-28](thumbnails/2026/01/20260128.jpg)](wallpapers/2026/01/20260128.jpg) |
| 2026-01-27 | [![2026-01-27](thumbnails/2026/01/20260127.jpg)](wallpapers/2026/01/20260127.jpg) |
| 2026-01-26 | [![2026-01-26](thumbnails/2026/01/20260126.jpg)](wallpapers/2026/01/20260126.jpg) |
| 2026-01-25 | [![2026-01-25](thumbnails/2026/01/20260125.jpg)](wallpapers/2026/01/20260125.jpg) |
| 2026-01-24 | [![2026-01-24](thumbnails/2026/01/20260124.jpg)](wallpapers/2026/01/20260124.jpg) |
| 2026-01-23 | [![2026-01-23](thumbnails/2026/01/20260123.jpg)](wallpapers/2026/01/20260123.jpg) |
| 2026-01-22 | [![2026-01-22](thumbnails/2026/01/20260122.jpg)](wallpapers/2026/01/20260122.jpg) |
| 2026-01-21 | [![2026-01-21](thumbnails/2026/01/20260121.jpg)](wallpapers/2026/01/20260121.jpg) |
| 2026-01-20 | [![2026-01-20](thumbnails/2026/01/20260120.jpg)](wallpapers/2026/01/20260120.jpg) |

---

## 归档统计

- 归档总数：1001
- 起始日期：2023-05-01
- 最新日期：2026-07-09

---

## 功能范围

本项目包含：

- 每日自动获取 Bing 1080P 壁纸。
- 按年月归档图片。
- 生成缩略图。
- 生成 `data/index.json`。
- 使用 `data/hash.json` 做去重。
- 自动更新 README。
- 检查归档完整性。
- 使用 GitHub Actions 定时运行。
- 后续接入个人官网展示。

---

## Maintenance

Historical migration tools have been removed after archive completion.

Current maintained features:

- Daily Bing wallpaper download
- Thumbnail generation
- Metadata storage
- Index generation
- README generation
- Archive integrity checking

---

## 项目边界

本项目长期不包含以下内容：

- UHD / 4K 版本保存。
- 多分辨率版本管理。
- 复杂前端图库。
- 多语言站点。
- 用户登录。
- 搜索系统。
- 数据库。
- 商业化。
- 多人协作后台。
- 多地区壁纸源。
- 高级图片标签系统。

保留这些边界的原因：

- 项目主要服务于个人自动归档需求。
- 只保存 1080P 版本，降低仓库体积和维护成本。
- 展示需求由 README 和未来的个人官网承担。
- 不引入数据库、登录、多用户等会显著增加复杂度的功能。

---

## 目录结构

```text
bing-wallpaper-archive/
  .github/
    workflows/
      update.yml

  data/
    index.json
    hash.json
    metadata.json

  scripts/
    download.py
    generate_thumbnail.py
    generate_index.py
    generate_readme.py
    check_archive.py

  wallpapers/
    YYYY/
      MM/
        YYYYMMDD.jpg

  thumbnails/
    YYYY/
      MM/
        YYYYMMDD.jpg

  README.md
  project.json
  requirements.txt
```

---

## 自动化流程

GitHub Actions 按以下流程运行：

```text
Checkout
↓
设置 Python 环境
↓
安装依赖
↓
下载 1080P 壁纸
↓
生成缩略图
↓
更新 index.json
↓
更新 README
↓
检测变更
↓
Commit
↓
Push
```

---

## 数据文件

### `data/index.json`

用于记录壁纸索引。

每条记录格式：

```json
{
  "date": "2026-07-08",
  "title": "",
  "copyright": "",
  "image": "wallpapers/2026/07/20260708.jpg",
  "thumbnail": "thumbnails/2026/07/20260708.jpg"
}
```

### `data/hash.json`

用于记录图片 SHA256 哈希，避免重复保存。

---

## License

MIT
