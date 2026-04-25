import logging
from fpdf import FPDF
from typing import Dict, Any
from app.services.report_generator_service import report_generator_service
from app.api.transcript import asr_service
import datetime
import textwrap

logger = logging.getLogger(__name__)

def _safe_text(text: str, max_line_len: int = 95) -> str:
    """
    Sanitize text for FPDF:
    - Strip non-Latin1 characters that FPDF's built-in fonts cannot encode.
    - Break any unbroken token longer than max_line_len so FPDF can always wrap.
    """
    if not text:
        return ""
    # Encode to latin-1, replacing unencodable chars
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    # Break long tokens (e.g. URLs, no-space strings) so FPDF wrap never fails
    words = safe.split(" ")
    broken = []
    for word in words:
        if len(word) > max_line_len:
            broken.extend(textwrap.wrap(word, max_line_len))
        else:
            broken.append(word)
    return " ".join(broken)


class OratoPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(245, 196, 0)
        self.cell(0, 10, 'ORATO-AI: INFINITE PERFORMANCE ANALYSIS', 0, 1, 'L')
        self.set_draw_color(245, 196, 0)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')


class PdfGeneratorService:
    async def generate_mega_report(self, submission_id: str) -> str:
        """
        Generates a comprehensive PDF report and returns the local file path.
        """
        logger.info(f"📄 Generating PDF Mega Report for {submission_id}")

        report_data = await report_generator_service.generate_report(submission_id)
        speech_data = await report_generator_service._get_speech_metrics(submission_id)
        visual_data = await report_generator_service._get_visual_metrics(submission_id)
        transcript = asr_service.get_transcript(submission_id)

        pdf = OratoPDF()
        pdf.set_margins(15, 15, 15)   # left, top, right — consistent safe margins
        pdf.add_page()

        # Safe usable width = page_width - left_margin - right_margin
        usable_w = pdf.w - pdf.l_margin - pdf.r_margin  # ~180mm on A4
        half_w = usable_w / 2

        # --- Section 1: Executive Summary ---
        pdf.set_font('helvetica', 'B', 20)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 15, 'Session Performance Report', 0, 1, 'L')
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, f'Overall Score: {report_data.get("overall_score", "N/A")}/100', 0, 1, 'L')
        pdf.ln(5)

        feedback = report_data.get("feedback", {})

        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 10, 'Professional Strengths', 0, 1, 'L')
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, _safe_text(feedback.get("praise", "No qualitative praise available.")))
        pdf.ln(5)

        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 10, 'Critical Growth Area', 0, 1, 'L')
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, _safe_text(feedback.get("biggest_weakness", "No critical weakness identified.")))
        pdf.ln(5)

        # --- Section 2: Modular Metrics ---
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 15, 'Modular Performance Deep-Dive', 0, 1, 'L')

        # Speech table
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 10, 'Speech Delivery Metrics:', 0, 1, 'L')
        pdf.set_font('helvetica', '', 11)
        pdf.cell(half_w, 8, f'Speaking Rate: {speech_data.get("speech_rate", 0)} WPM', 1, 0)
        pdf.cell(half_w, 8, f'Filler Density: {speech_data.get("filler_word_percentage", 0)}%', 1, 1)
        pdf.cell(half_w, 8, f'Fluency Score: {speech_data.get("fluency_score", 0)}/100', 1, 0)
        pdf.cell(half_w, 8, f'Total Pauses: {speech_data.get("pause_count", 0)}', 1, 1)
        pdf.ln(10)

        # Visual table — use real raw values, not scores
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(0, 10, 'Visual Analytics Metrics:', 0, 1, 'L')
        pdf.set_font('helvetica', '', 11)
        scores = visual_data.get("individual_scores", {}) if visual_data else {}
        eye_pct = visual_data.get("head_pose", {}).get("eye_contact_percentage", 0) if visual_data else 0
        gpm = visual_data.get("gestures", {}).get("gesture_frequency", {}).get("gestures_per_minute", 0) if visual_data else 0
        pdf.cell(half_w, 8, f'Eye Contact: {eye_pct:.1f}%', 1, 0)
        pdf.cell(half_w, 8, f'Hand Visibility: {scores.get("hand_visibility_score", 0):.1f}/100', 1, 1)
        pdf.cell(half_w, 8, f'Posture Score: {scores.get("cca_score", 0):.1f}/100', 1, 0)
        pdf.cell(half_w, 8, f'Gestures/Min: {gpm:.1f}', 1, 1)
        pdf.ln(10)

        # Action Plan
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 10, 'Strategic Action Plan', 0, 1, 'L')
        pdf.set_font('helvetica', '', 11)
        for i, step in enumerate(feedback.get("action_plan", [])):
            pdf.multi_cell(0, 7, _safe_text(f'{i+1}. {step}'))
            pdf.ln(2)

        # --- Section 3: Transcript ---
        full_text = None
        if transcript:
            full_text = (
                transcript.get("full_text") or
                transcript.get("text") or
                transcript.get("transcript") or
                transcript.get("content")
            )

        if full_text:
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 16)
            pdf.cell(0, 15, 'Full Presentation Transcript', 0, 1, 'L')
            pdf.set_font('helvetica', '', 10)
            # Use helvetica (not courier) to avoid monospace-width crash on long tokens
            pdf.multi_cell(0, 6, _safe_text(full_text))

        import tempfile, os
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"Orato_Report_{submission_id}.pdf")
        pdf.output(file_path)

        return file_path


pdf_generator_service = PdfGeneratorService()
