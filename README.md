# Bing Wallpaper Archive

中文 | [English](README.en.md)

Bing Wallpaper Archive 是一个个人自用的 Bing 1080P 壁纸自动归档项目。它保存原图、缩略图、metadata 和索引数据，并通过 GitHub Actions 每日更新。

---

## 状态

- 状态: Active
- 版本: v0.2.1
- 图片: 1013
- 缩略图: 1013
- Metadata 记录: 1013
- 日期范围: 2023-05-01 - 2026-07-21

---

## 最新壁纸

**日期：** 2026-07-21

**标题：** 细微之举，影响深远

**版权：** 珊瑚礁与海滩在拉贾安帕特，印度尼西亚 (© SergeUWPhoto/Shutterstock)

[![2026-07-21](thumbnails/2026/07/20260721.jpg)](wallpapers/2026/07/20260721.jpg)

---

## 最近壁纸

| 日期 | 预览 |
|---|---|
| 2026-07-21 | [![2026-07-21](thumbnails/2026/07/20260721.jpg)](wallpapers/2026/07/20260721.jpg) |
| 2026-07-20 | [![2026-07-20](thumbnails/2026/07/20260720.jpg)](wallpapers/2026/07/20260720.jpg) |
| 2026-07-19 | [![2026-07-19](thumbnails/2026/07/20260719.jpg)](wallpapers/2026/07/20260719.jpg) |
| 2026-07-18 | [![2026-07-18](thumbnails/2026/07/20260718.jpg)](wallpapers/2026/07/20260718.jpg) |
| 2026-07-17 | [![2026-07-17](thumbnails/2026/07/20260717.jpg)](wallpapers/2026/07/20260717.jpg) |
| 2026-07-16 | [![2026-07-16](thumbnails/2026/07/20260716.jpg)](wallpapers/2026/07/20260716.jpg) |
| 2026-07-15 | [![2026-07-15](thumbnails/2026/07/20260715.jpg)](wallpapers/2026/07/20260715.jpg) |
| 2026-07-14 | [![2026-07-14](thumbnails/2026/07/20260714.jpg)](wallpapers/2026/07/20260714.jpg) |
| 2026-07-13 | [![2026-07-13](thumbnails/2026/07/20260713.jpg)](wallpapers/2026/07/20260713.jpg) |
| 2026-07-12 | [![2026-07-12](thumbnails/2026/07/20260712.jpg)](wallpapers/2026/07/20260712.jpg) |
| 2026-07-11 | [![2026-07-11](thumbnails/2026/07/20260711.jpg)](wallpapers/2026/07/20260711.jpg) |
| 2026-07-10 | [![2026-07-10](thumbnails/2026/07/20260710.jpg)](wallpapers/2026/07/20260710.jpg) |

---

## 维护

当前保留的长期功能：

- 每日下载 Bing 1080P 壁纸
- 生成缩略图
- 保存 metadata、hash 和 index
- 自动生成 README
- 检查归档完整性

历史迁移工具已在归档完成后移除。

---

## 数据

- 原图：`wallpapers/YYYY/MM/YYYYMMDD.jpg`
- 缩略图：`thumbnails/YYYY/MM/YYYYMMDD.jpg`
- 索引：`data/index.json`
- Hash 记录：`data/hash.json`
- Metadata 记录：`data/metadata.json`
- 健康检查报告：`reports/archive_check.md`

本地验证：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_archive.py
```

---

## License

MIT
