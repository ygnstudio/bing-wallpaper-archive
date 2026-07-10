# Bing Wallpaper Archive

[中文](README.md) | English

Bing Wallpaper Archive is a personal archive for daily Bing 1080P wallpapers. It stores original images, thumbnails, metadata, and an index, then updates through GitHub Actions.

---

## Status

- Status: Active
- Version: v0.2.1
- Images: 1002
- Thumbnails: 1002
- Metadata records: 1002
- Date range: 2023-05-01 - 2026-07-10

---

## Latest Wallpaper

**Date:** 2026-07-10

**Title:** 布列塔尼的潮汐之约

**Copyright:** 圣古斯坦港, 欧赖, 布列塔尼, 法国 (© Rolf E. Staerk/Shutterstock)

[![2026-07-10](thumbnails/2026/07/20260710.jpg)](wallpapers/2026/07/20260710.jpg)

---

## Recent Wallpapers

| Date | Preview |
|---|---|
| 2026-07-10 | [![2026-07-10](thumbnails/2026/07/20260710.jpg)](wallpapers/2026/07/20260710.jpg) |
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
