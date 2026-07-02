# Data source

Primary catalog file:

```
data/source/Music_Data.csv
```

(Also supports `tracks.xlsx` or any `.csv` via `--source`.)

## Required columns

Your file is mapped automatically (see `scripts/build_mood_buckets.py`):

| Canonical | Your file (`Music_Data.csv`) |
|-----------|------------------------------|
| `track_id` | `track_id` |
| `name` | `track_name` |
| `artist_name` | `artists` |
| `album_name` | `album_name` |
| `genre` | `track_genre` |
| `energy` | `energy` |
| `valence` | `valence` |
| `tempo` | `tempo` |
| `instrumentalness` | `instrumentalness` |

**Note:** The `Mood` column in your CSV is **not used** for tagging. Moods are computed from audio features only (architecture §6.5).

## Load

```bash
python scripts/excel_to_db.py --source data/source/Music_Data.csv --dry-run
python scripts/validate_coverage.py --csv data/seed/v1/track_mood_tags.csv
```
