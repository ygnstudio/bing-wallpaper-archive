# Bing Wallpaper Archive

[中文](README.md) | English

Bing Wallpaper Archive is a personal archive for daily Bing 1080P wallpapers. It stores original images, thumbnails, metadata, and an index, then updates through GitHub Actions.

---

## Status

- Status: Active
- Version: v0.2.1
- Images: 1011
- Thumbnails: 1011
- Metadata records: 1011
- Date range: 2023-05-01 - 2026-07-19

---

## Latest Wallpaper

**Date:** 2026-07-19

**Title:** 月瞰寰宇

**Copyright:** 月球与地球由阿耳忒弥斯2号机组人员拍摄 (© NASA)

[![2026-07-19](thumbnails/2026/07/20260719.jpg)](wallpapers/2026/07/20260719.jpg)

---

## Recent Wallpapers

| Date | Preview |
|---|---|
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
| 2026-07-09 | [![2026-07-09](thumbnails/2026/07/20260709.jpg)](wallpapers/2026/07/20260709.jpg) |
| 2026-07-08 | [![2026-07-08](thumbnails/2026/07/20260708.jpg)](wallpapers/2026/07/20260708.jpg) |

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
