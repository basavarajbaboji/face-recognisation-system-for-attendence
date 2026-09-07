"""
Ultra-minimal 4-slide Tech Expo presentation generator (.pptx):
- Exactly 4 slides
- Exactly 3 to 4 short, single-line bullet points per slide
- Zero paragraphs or heavy text
- Clean, large typography with high contrast for expo screens
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# --- THEME COLORS ---
COLOR_BG_DARK = RGBColor(11, 17, 32)         # Deep Navy (#0B1120)
COLOR_CARD_BG = RGBColor(22, 33, 54)         # Slate Card (#162136)
COLOR_CARD_BORDER = RGBColor(38, 56, 89)     # Border (#263859)
COLOR_TEXT_WHITE = RGBColor(255, 255, 255)   # White
COLOR_TEXT_MUTED = RGBColor(160, 174, 192)   # Light Gray (#A0AEC0)
COLOR_CYAN = RGBColor(56, 189, 248)          # Cyan (#38BDF8)
COLOR_EMERALD = RGBColor(52, 211, 153)       # Emerald (#34D399)
COLOR_AMBER = RGBColor(251, 191, 36)         # Amber (#FBBF24)


def build_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, tag: str, title: str):
        # Tag
        tb_tag = slide.shapes.add_textbox(Inches(1.2), Inches(0.8), Inches(10.9), Inches(0.4))
        tf_tag = tb_tag.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        r_tag = p_tag.add_run()
        r_tag.text = tag.upper()
        r_tag.font.size = Pt(13)
        r_tag.font.bold = True
        r_tag.font.color.rgb = COLOR_CYAN
        r_tag.font.name = "Segoe UI"

        # Title
        tb_title = slide.shapes.add_textbox(Inches(1.2), Inches(1.25), Inches(10.9), Inches(0.9))
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title
        r_title.font.size = Pt(36)
        r_title.font.bold = True
        r_title.font.color.rgb = COLOR_TEXT_WHITE
        r_title.font.name = "Segoe UI"

    def add_card(slide, left, top, width, height, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    c1 = add_card(s1, Inches(1.2), Inches(1.0), Inches(10.933), Inches(5.5), border_color=COLOR_CYAN)
    tf1 = c1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = Inches(0.8); tf1.margin_top = Inches(0.6)

    p = tf1.paragraphs[0]
    r = p.add_run(); r.text = "TECH EXPO PROJECT DEMO"; r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = COLOR_CYAN; r.font.name = "Segoe UI"

    p = tf1.add_paragraph(); p.space_before = Pt(12)
    r = p.add_run(); r.text = "Smart Face Recognition Attendance"; r.font.size = Pt(36); r.font.bold = True; r.font.color.rgb = COLOR_TEXT_WHITE; r.font.name = "Segoe UI"

    p = tf1.add_paragraph(); p.space_before = Pt(8)
    r = p.add_run(); r.text = "Contactless, real-time campus attendance system"; r.font.size = Pt(16); r.font.color.rgb = COLOR_TEXT_MUTED; r.font.name = "Segoe UI"

    p = tf1.add_paragraph(); p.space_before = Pt(32)
    r = p.add_run(); r.text = "KEY HIGHLIGHTS:"; r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = COLOR_AMBER; r.font.name = "Segoe UI"

    bullets_1 = [
        "Fast walk-through entry with zero stopping",
        "Runs on standard PC / laptop (No GPU required)",
        "Stops proxy attendance completely",
        "Instant live dashboard & 1-click Excel download"
    ]
    for b in bullets_1:
        p = tf1.add_paragraph(); p.space_before = Pt(12)
        r = p.add_run(); r.text = "•  " + b; r.font.size = Pt(16); r.font.color.rgb = COLOR_TEXT_WHITE; r.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 2: What Is It? (4 short points)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "Overview", "What Is This Project?")

    c2 = add_card(s2, Inches(1.2), Inches(2.3), Inches(10.933), Inches(4.3), border_color=COLOR_EMERALD)
    tf2 = c2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = Inches(0.8); tf2.margin_top = Inches(0.6)

    bullets_2 = [
        ("Walk-Through Attendance: ", "Students walk naturally past the camera without waiting in queues."),
        ("Replaces Slow Hardware: ", "Eliminates slow fingerprint scanners and manual paper roll calls."),
        ("Zero Buddy Punching: ", "Nobody can mark attendance for absent friends."),
        ("Voice Greetings & Logging: ", "System recognizes the face, speaks their name, and records attendance.")
    ]
    for i, (head, desc) in enumerate(bullets_2):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        if i > 0: p.space_before = Pt(20)
        r1 = p.add_run(); r1.text = "•  " + head; r1.font.size = Pt(16); r1.font.bold = True; r1.font.color.rgb = COLOR_EMERALD; r1.font.name = "Segoe UI"
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(16); r2.font.color.rgb = COLOR_TEXT_WHITE; r2.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 3: Technologies Used (4 short points)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "Tech Stack", "Technologies Used")

    c3 = add_card(s3, Inches(1.2), Inches(2.3), Inches(10.933), Inches(4.3), border_color=COLOR_CYAN)
    tf3 = c3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_right = Inches(0.8); tf3.margin_top = Inches(0.6)

    bullets_3 = [
        ("Face Detection & Recognition: ", "OpenCV YuNet + ArcFace ONNX models"),
        ("Crowd Tracking: ", "ByteTrack algorithm (tracks moving groups in real time)"),
        ("Backend Server: ", "Python, FastAPI, and SQLite database"),
        ("Frontend Dashboard: ", "React 19, Vite, and HTML5 Canvas (60 FPS camera feed)")
    ]
    for i, (head, desc) in enumerate(bullets_3):
        p = tf3.paragraphs[0] if i == 0 else tf3.add_paragraph()
        if i > 0: p.space_before = Pt(20)
        r1 = p.add_run(); r1.text = "•  " + head; r1.font.size = Pt(16); r1.font.bold = True; r1.font.color.rgb = COLOR_CYAN; r1.font.name = "Segoe UI"
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(16); r2.font.color.rgb = COLOR_TEXT_WHITE; r2.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 4: How It Works (4 simple steps)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "Process", "How It Works (4 Steps)")

    c4 = add_card(s4, Inches(1.2), Inches(2.3), Inches(10.933), Inches(4.3), border_color=COLOR_AMBER)
    tf4 = c4.text_frame
    tf4.word_wrap = True
    tf4.margin_left = tf4.margin_right = Inches(0.8); tf4.margin_top = Inches(0.6)

    bullets_4 = [
        ("Step 1: Capture — ", "Camera captures live video of people entering."),
        ("Step 2: Detect & Track — ", "YuNet finds faces, ByteTrack assigns continuous IDs."),
        ("Step 3: Vector Match — ", "ArcFace matches face embeddings in under 0.4 milliseconds."),
        ("Step 4: Mark & Announce — ", "Logs attendance in database, speaks name, and updates dashboard.")
    ]
    for i, (head, desc) in enumerate(bullets_4):
        p = tf4.paragraphs[0] if i == 0 else tf4.add_paragraph()
        if i > 0: p.space_before = Pt(20)
        r1 = p.add_run(); r1.text = "•  " + head; r1.font.size = Pt(16); r1.font.bold = True; r1.font.color.rgb = COLOR_AMBER; r1.font.name = "Segoe UI"
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(16); r2.font.color.rgb = COLOR_TEXT_WHITE; r2.font.name = "Segoe UI"

    # Save to file with fallback if user has the file open in PowerPoint
    primary_file = "Smart_Campus_Face_Attendance_Tech_Expo.pptx"
    fallback_file = "Smart_Campus_Face_Attendance_Tech_Expo_Minimal.pptx"
    saved_files = []

    for fpath in [primary_file, "Smart_Campus_Face_Attendance_System.pptx"]:
        try:
            prs.save(fpath)
            saved_files.append(fpath)
            print(f"[SUCCESS] Saved deck to {fpath}")
        except PermissionError:
            prs.save(fallback_file)
            saved_files.append(fallback_file)
            print(f"[NOTE] '{fpath}' is open in PowerPoint. Saved updated copy to '{fallback_file}'.")
            break

    print(f"Total Slides: {len(prs.slides)}")
    return saved_files


if __name__ == "__main__":
    build_deck()
