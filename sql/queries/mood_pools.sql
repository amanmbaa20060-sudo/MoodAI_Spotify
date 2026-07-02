-- Phase 0 mood pool verification queries (architecture §6.5)

-- Total catalog size
SELECT COUNT(*) AS total_tracks FROM tracks;

-- Tagged tracks
SELECT COUNT(*) AS tagged_tracks
FROM track_mood_tags
WHERE primary_mood IS NOT NULL;

-- ADVENTUROUS must be zero in dataset
SELECT COUNT(*) AS adventurous_count
FROM track_mood_tags
WHERE primary_mood = 'ADVENTUROUS'
   OR 'ADVENTUROUS' = ANY(mood_tags);

-- Per-mood pool counts (target >= 200 each)
SELECT 'ENERGISED' AS mood, COUNT(*) AS pool_size
FROM track_mood_tags WHERE 'ENERGISED' = ANY(mood_tags)
UNION ALL
SELECT 'FOCUSED', COUNT(*) FROM track_mood_tags WHERE 'FOCUSED' = ANY(mood_tags)
UNION ALL
SELECT 'LOW_KEY', COUNT(*) FROM track_mood_tags WHERE 'LOW_KEY' = ANY(mood_tags)
UNION ALL
SELECT 'NOSTALGIC', COUNT(*) FROM track_mood_tags WHERE 'NOSTALGIC' = ANY(mood_tags)
UNION ALL
SELECT 'SAD', COUNT(*) FROM track_mood_tags WHERE 'SAD' = ANY(mood_tags);

-- Example: novel tracks for user_new (no play history)
SELECT t.track_id, t.name, t.artist_name, m.primary_mood
FROM tracks t
JOIN track_mood_tags m ON t.track_id = m.track_id
WHERE 'FOCUSED' = ANY(m.mood_tags)
  AND t.track_id NOT IN (
    SELECT track_id FROM play_history WHERE user_id = 'user_new'
  )
LIMIT 20;
