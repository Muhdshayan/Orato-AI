-- Enable required extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('USER', 'ADMIN')) DEFAULT 'USER',
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Video submissions table
CREATE TABLE video_submissions (
    submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    filesize BIGINT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    declared_topic VARCHAR(500) NOT NULL,
    retention_expiry TIMESTAMP,
    minio_object_name VARCHAR(500) NOT NULL,
    minio_bucket VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing jobs table
CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES video_submissions(submission_id) ON DELETE CASCADE,
    status VARCHAR(50) CHECK (status IN ('QUEUED', 'PROCESSING', 'DONE', 'FAILED')) DEFAULT 'QUEUED',
    enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_code VARCHAR(100),
    error_message TEXT
);

-- Transcripts table
CREATE TABLE transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES video_submissions(submission_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    segments JSONB,
    asr_confidence FLOAT,
    asr_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Speech metrics table
CREATE TABLE speech_metrics (
    metrics_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    filler_word_count INTEGER DEFAULT 0,
    total_word_count INTEGER DEFAULT 0,
    filler_word_percentage FLOAT DEFAULT 0,
    fluency_score FLOAT,
    speech_rate FLOAT,
    articulation_rate FLOAT,
    total_pause_time FLOAT DEFAULT 0,
    pause_count INTEGER DEFAULT 0,
    pause_durations JSONB,
    articulation_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content relevance table
CREATE TABLE content_relevance (
    content_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE,
    topic_match_score FLOAT,
    off_topic_segments JSONB,
    factual_accuracy FLOAT,
    evidence_snippets JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CV artifacts table
CREATE TABLE cv_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES video_submissions(submission_id) ON DELETE CASCADE,
    frame_index INTEGER NOT NULL,
    keypoints_json JSONB,
    face_angle FLOAT,
    evidence_frame_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posture metrics table
CREATE TABLE posture_metrics (
    posture_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES cv_artifacts(artifact_id) ON DELETE CASCADE,
    slouch_duration FLOAT,
    head_orientation FLOAT,
    shoulder_alignment FLOAT,
    posture_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gesture metrics table
CREATE TABLE gesture_metrics (
    gesture_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES cv_artifacts(artifact_id) ON DELETE CASCADE,
    hand_gesture_count INTEGER,
    gesture_velocity FLOAT,
    movement_consistency FLOAT,
    gesture_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis reports table
CREATE TABLE analysis_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID UNIQUE NOT NULL REFERENCES video_submissions(submission_id) ON DELETE CASCADE,
    overall_score FLOAT,
    relevance_score FLOAT,
    tips_json JSONB,
    visual_insights_json JSONB,
    delivery_insights_json JSONB,
    report_url VARCHAR(500),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Score cards table
CREATE TABLE score_cards (
    scorecard_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES analysis_reports(report_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    weight FLOAT NOT NULL,
    feedback TEXT,
    improvements JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_video_submissions_user_id ON video_submissions(user_id);
CREATE INDEX idx_processing_jobs_submission_id ON processing_jobs(submission_id);
CREATE INDEX idx_transcripts_submission_id ON transcripts(submission_id);
CREATE INDEX idx_speech_metrics_transcript_id ON speech_metrics(transcript_id);
CREATE INDEX idx_cv_artifacts_submission_id ON cv_artifacts(submission_id);
CREATE INDEX idx_analysis_reports_submission_id ON analysis_reports(submission_id);



DELETE FROM users;

DELETE FROM video_submissions;

Delete from transcripts;

SELECT user_id, name, email, role, created_at 
FROM users 
ORDER BY created_at DESC;

SELECT 
    submission_id,
    user_id,
    filename,
    filesize,
    declared_topic,
    minio_bucket,
    minio_object_name,
    status,
    uploaded_at
FROM video_submissions 
ORDER BY uploaded_at DESC;


SELECT 
    job_id,
    submission_id,
    status,
    enqueued_at,
    completed_at,
    error_message
FROM processing_jobs 
ORDER BY enqueued_at DESC;


SELECT 
    t.transcript_id,
    t.submission_id,
    vs.filename,
    LEFT(t.text, 100) as text_preview,
    t.asr_confidence,
    t.created_at
FROM transcripts t
JOIN video_submissions vs ON t.submission_id = vs.submission_id
ORDER BY t.created_at DESC;

