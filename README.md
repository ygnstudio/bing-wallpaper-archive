# Bing Wallpaper Archive

Bing Wallpaper Archive is a GitHub-based automation project for archiving the daily Bing wallpaper in 1080P.

## Current Status

This repository is currently in the v0.1.0 planning and scaffold stage.

The project structure, placeholder scripts, data files, and GitHub Actions workflow are initialized, but the real wallpaper download, thumbnail generation, index generation, and README generation logic have not been implemented yet.

## Scope

This project will:

- Automatically fetch the daily Bing wallpaper.
- Save only the 1080P image version.
- Archive images by year and month.
- Generate thumbnails for README previews.
- Generate stable JSON index data.
- Update README content through automation.
- Run through GitHub Actions.

## Boundaries

This project will not include:

- UHD or 4K downloads.
- Multi-resolution image management.
- A database.
- A complex frontend gallery.
- Search.
- User accounts.
- Multi-region wallpaper sources.
- Commercial features.

## Directory Structure

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

## Automation

The GitHub Actions workflow is defined in `.github/workflows/update.yml`.

It is designed to support both manual and scheduled runs. The current workflow calls the placeholder scripts in order:

1. Download the daily 1080P wallpaper.
2. Generate thumbnails.
3. Generate `data/index.json`.
4. Generate README content.
5. Commit and push changes when files have changed.

The scripts are placeholders in v0.1.0 and intentionally do not perform real archive updates yet.

## License

MIT
