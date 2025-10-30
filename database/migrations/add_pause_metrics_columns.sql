-- Migration: Add pause detection and speech rate columns to speech_metrics table
-- Run this if you have an existing speech_metrics table

-- Add new columns for pause detection and speech rates
ALTER TABLE speech_metrics 
ADD COLUMN IF NOT EXISTS articulation_rate FLOAT,
ADD COLUMN IF NOT EXISTS total_pause_time FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS pause_count INTEGER DEFAULT 0;

-- Update existing records to have default values
UPDATE speech_metrics 
SET total_pause_time = 0, 
    pause_count = 0
WHERE total_pause_time IS NULL OR pause_count IS NULL;

-- Add comment to pause_durations column for clarity
COMMENT ON COLUMN speech_metrics.pause_durations IS 'JSONB containing pause timestamps and summary statistics';

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'speech_metrics' 
ORDER BY ordinal_position;

