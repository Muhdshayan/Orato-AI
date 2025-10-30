-- Migration: Add speech metrics columns to speech_metrics table
-- Run this if you have an existing speech_metrics table

-- Add new columns for speech analysis
ALTER TABLE speech_metrics 
ADD COLUMN IF NOT EXISTS total_word_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS filler_word_percentage FLOAT DEFAULT 0;

-- Update existing records to have default values
UPDATE speech_metrics 
SET total_word_count = 0, 
    filler_word_percentage = 0.0 
WHERE total_word_count IS NULL OR filler_word_percentage IS NULL;

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    column_default 
FROM information_schema.columns 
WHERE table_name = 'speech_metrics' 
ORDER BY ordinal_position;

