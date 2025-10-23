import os
import sys
import json
import uuid
from datetime import datetime, timedelta

from moviepy.editor import VideoFileClip
import speech_recognition as sr
from langdetect import detect, LangDetectException

from minio import Minio
from minio.error import S3Error

import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')


MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "300"))
SUPPORTED_LANGUAGE = os.getenv("SUPPORTED_LANGUAGE", "en")


def get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_minio_client() -> Minio:
    endpoint = get_env("MINIO_ENDPOINT", required=True)
    access_key = get_env("MINIO_ACCESS_KEY", required=True)
    secret_key = get_env("MINIO_SECRET_KEY", required=True)
    secure = get_env("MINIO_SECURE", "false").lower() == "true"
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file_stream(client: Minio, bucket: str, object_name: str, file_path: str, content_type: str | None = None) -> None:
    file_stat = os.stat(file_path)
    with open(file_path, "rb") as f:
        client.put_object(bucket, object_name, f, file_stat.st_size, content_type=content_type)


def get_pg_conn():
    host = get_env("PGHOST", "127.0.0.1")
    port = int(get_env("PGPORT", "5432"))
    user = get_env("PGUSER", "postgres")
    password = get_env("PGPASSWORD", "")
    database = get_env("PGDATABASE", required=True)
    return psycopg2.connect(host=host, port=port, user=user, password=password, database=database)


def insert_video_submission(conn, user_id: str, filename: str, filesize: int, declared_topic: str, minio_bucket: str, minio_object_name: str):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO video_submissions (user_id, filename, filesize, declared_topic, minio_object_name, minio_bucket)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING submission_id
            """,
            (user_id, filename, filesize, declared_topic, minio_object_name, minio_bucket),
        )
        row = cur.fetchone()
        conn.commit()
        return row["submission_id"]


def process_video(video_path: str, declared_topic: str, user_id: str) -> None:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_video_path = f"{base_name}_video_only.mp4"
    output_audio_path = f"{base_name}_audio_only.wav"

    # 1) Load video and validate duration
    clip = VideoFileClip(video_path)
    try:
        if clip.duration > MAX_DURATION_SECONDS:
            raise ValueError(
                f"Video duration ({clip.duration:.2f}s) exceeds limit of {MAX_DURATION_SECONDS}s"
            )

        # 2) Language quick check via SpeechRecognition + langdetect on a short subclip
        sample_audio_path = f"{base_name}_langcheck.wav"
        audio_for_check = clip.audio
        if audio_for_check is None:
            raise ValueError("Video has no audio track")

        sample_end = min(15, clip.duration)
        audio_for_check.subclip(0, sample_end).write_audiofile(sample_audio_path, verbose=False, logger=None)

        recognizer = sr.Recognizer()
        with sr.AudioFile(sample_audio_path) as source:
            audio_data = recognizer.record(source)

        detected_lang = None
        try:
            transcribed_text = recognizer.recognize_google(audio_data)
            detected_lang = detect(transcribed_text)
            if detected_lang != SUPPORTED_LANGUAGE:
                raise ValueError(f"Detected language '{detected_lang}' != '{SUPPORTED_LANGUAGE}'")
        except sr.UnknownValueError:
            # proceed but warn
            pass
        except sr.RequestError as e:
            # proceed but warn
            pass
        except LangDetectException:
            # proceed but warn
            pass
        finally:
            if os.path.exists(sample_audio_path):
                os.remove(sample_audio_path)

        # 3) Split into video (no audio) and audio-only wav
        clip.write_videofile(output_video_path, audio=False, verbose=False, logger=None)
        clip.audio.write_audiofile(output_audio_path, verbose=False, logger=None)

    finally:
        clip.close()

    # 4) Upload to MinIO
    minio_bucket = get_env("MINIO_MEDIA_BUCKET", required=True)
    minio_client = get_minio_client()
    ensure_bucket(minio_client, minio_bucket)

    submission_uuid = str(uuid.uuid4())
    original_obj = f"uploads/{submission_uuid}.mp4"
    video_only_obj = f"derived/{submission_uuid}_video_only.mp4"
    audio_only_obj = f"derived/{submission_uuid}_audio_only.wav"

    upload_file_stream(minio_client, minio_bucket, original_obj, video_path, content_type="video/mp4")
    upload_file_stream(minio_client, minio_bucket, video_only_obj, output_video_path, content_type="video/mp4")
    upload_file_stream(minio_client, minio_bucket, audio_only_obj, output_audio_path, content_type="audio/wav")

    # 5) Insert DB row for submission pointing to original
    conn = get_pg_conn()
    try:
        submission_id = insert_video_submission(
            conn,
            user_id=user_id,
            filename=os.path.basename(video_path),
            filesize=os.path.getsize(video_path),
            declared_topic=declared_topic,
            minio_bucket=minio_bucket,
            minio_object_name=original_obj,
        )
        print(f"Created submission: {submission_id}")
        print(f"Uploaded to MinIO: {minio_bucket}/{original_obj}")
        print(f"Derived: {minio_bucket}/{video_only_obj}, {minio_bucket}/{audio_only_obj}")
    finally:
        conn.close()


def main():
    if len(sys.argv) < 4:
        print("Usage: python video_preprocessing.py <video_path> <declared_topic> <user_id>")
        sys.exit(1)
    video_path = sys.argv[1]
    declared_topic = sys.argv[2]
    user_id = sys.argv[3]
    process_video(video_path, declared_topic, user_id)


if __name__ == "__main__":
    main()
