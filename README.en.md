# Bing Wallpaper Archive

[中文](README.md) | English

Bing Wallpaper Archive is a personal archive for daily Bing 1080P wallpapers. It stores original images, thumbnails, metadata, and an index, then updates through GitHub Actions.

---

## Status

- Status: Active
- Version: v0.2.1
- Images: 1015
- Thumbnails: 1015
- Metadata records: 1015
- Date range: 2023-05-01 - 2026-07-23

---

## Latest Wallpaper

**Date:** 2026-07-23

**Title:** 缤纷多彩的一家人

**Copyright:** 美洲红鹳群在伊莎贝拉岛，加拉帕戈斯群岛，厄瓜多尔 (© Tui De Roy/Nature Picture Library)

[![2026-07-23](thumbnails/2026/07/20260723.jpg)](wallpapers/2026/07/20260723.jpg)

---

## Recent Wallpapers

| Date | Preview |
|---|---|
| 2026-07-23 | [![2026-07-23](thumbnails/2026/07/20260723.jpg)](wallpapers/2026/07/20260723.jpg) |
| 2026-07-22 | [![2026-07-22](thumbnails/2026/07/20260722.jpg)](wallpapers/2026/07/20260722.jpg) |
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

---

## Maintenance

Current maintained features:

- Daily Bing 1080P wallpaper download
- Thumbnail generation
- Metadata, hash, and index storage
- README generation
- Archive integrity checking

Historical migration tools were removed after archive completion.

---

## Data

- Original images: `wallpapers/YYYY/MM/YYYYMMDD.jpg`
- Thumbnails: `thumbnails/YYYY/MM/YYYYMMDD.jpg`
- Index: `data/index.json`
- Hash records: `data/hash.json`
- Metadata records: `data/metadata.json`
- Health report: `reports/archive_check.md`

Run locally:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_archive.py
```

---

## License

MIT
