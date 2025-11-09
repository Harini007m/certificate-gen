import os
import uuid
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from fpdf import FPDF

# ---------------- CONFIG ----------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

# Add template context processor for current datetime
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

UPLOAD_FOLDER = "uploads"
GENERATED_FOLDER = "generated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

ALLOWED_TEMPLATE_EXT = {'png', 'jpg', 'jpeg', 'docx', 'doc'}
ALLOWED_LIST_EXT = {'xlsx', 'xls', 'csv'}

# ---------------- HELPERS ----------------
def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def draw_text_on_image(template_path, output_path, name, dept):
    """Draws the student's name and department on the certificate template"""
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # FONT SETTINGS
    font_path = os.path.join("static", "fonts", "OpenSans-Bold.ttf")

    def load_truetype(size):
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            # Fall back to the default bitmap font if truetype not available
            return ImageFont.load_default()

    # Start with a reasonable font size and shrink if text is too wide
    name_font_size = 60
    dept_font_size = 40

    # Maximum allowed text width inside the certificate box (use image width with margins)
    margin = int(img.width * 0.12)
    max_width = img.width - 2 * margin

    # Load and shrink name font until it fits within max_width
    name_font = load_truetype(name_font_size)
    # Use textbbox for accurate sizing if available
    def text_size(text, font):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return draw.textsize(text, font=font)

    name_w, name_h = text_size(name, name_font)
    while name_w > max_width and name_font_size > 10:
        name_font_size -= 2
        name_font = load_truetype(name_font_size)
        name_w, name_h = text_size(name, name_font)

    # Center name horizontally; keep vertical placement near the upper-middle of the box
    name_x = (img.width - name_w) // 2
    # Keep previous vertical feel by using a relative Y (tweakable)
    name_y = int(img.height * 0.45)
    draw.text((name_x, name_y), name, fill="black", font=name_font)

    # Department text (smaller). Shrink if needed and center below the name.
    dept_text = f"Department: {dept}"
    dept_font = load_truetype(dept_font_size)
    dept_w, dept_h = text_size(dept_text, dept_font)
    while dept_w > max_width and dept_font_size > 10:
        dept_font_size -= 2
        dept_font = load_truetype(dept_font_size)
        dept_w, dept_h = text_size(dept_text, dept_font)

    dept_x = (img.width - dept_w) // 2
    dept_y = name_y + name_h + int(img.height * 0.02)
    draw.text((dept_x, dept_y), dept_text, fill="black", font=dept_font)

    img.save(output_path)


def merge_images_to_pdf(image_folder, output_pdf_path):
    """Combine all JPG/PNG certificates into a single PDF"""
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    image_files.sort()

    if not image_files:
        return None

    pdf = FPDF()
    for img_name in image_files:
        img_path = os.path.join(image_folder, img_name)
        img = Image.open(img_path)
        w, h = img.size
        pdf.add_page()
        pdf.image(img_path, 0, 0, 210, 0)  # width fit to A4
    # use keyword args for fpdf2 compatibility (name and dest) to avoid
    # TypeError: FPDF.output() takes from 1 to 2 positional arguments but 3 were given
    pdf.output(name=output_pdf_path, dest="F")
    return output_pdf_path


# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    template = request.files.get('template')
    student_file = request.files.get('listfile')

    if not template or not student_file:
        flash("Please upload both a template and student list.", "error")
        return redirect(url_for('index'))

    if not allowed_file(template.filename, ALLOWED_TEMPLATE_EXT):
        flash("Template must be an image file (PNG, JPG, JPEG, DOCX, or DOC).", "error")
        return redirect(url_for('index'))

    if not allowed_file(student_file.filename, ALLOWED_LIST_EXT):
        flash("Student list must be Excel or CSV file.", "error")
        return redirect(url_for('index'))

    # Save uploaded files
    template_filename = secure_filename(template.filename)
    list_filename = secure_filename(student_file.filename)
    template_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{template_filename}")
    list_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{list_filename}")

    template.save(template_path)
    student_file.save(list_path)

    # Read Excel/CSV
    ext = list_path.rsplit('.', 1)[1].lower()
    df = pd.read_excel(list_path) if ext in ('xlsx', 'xls') else pd.read_csv(list_path)
    df.columns = [c.lower().strip() for c in df.columns]

    batch_id = uuid.uuid4().hex
    batch_folder = os.path.join(GENERATED_FOLDER, batch_id)
    os.makedirs(batch_folder, exist_ok=True)

    for _, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        dept = str(row.get('dept', row.get('department', ''))).strip()
        output_file = os.path.join(batch_folder, f"{secure_filename(name)}.jpg")
        draw_text_on_image(template_path, output_file, name, dept)

    # Merge all images into a single PDF
    pdf_path = os.path.join(batch_folder, "All_Certificates.pdf")
    merge_images_to_pdf(batch_folder, pdf_path)

    flash("Certificates generated successfully!", "success")
    return redirect(url_for('preview', batch=batch_id))


@app.route('/preview/<batch>')
def preview(batch):
    folder = os.path.join(GENERATED_FOLDER, batch)
    files = [f for f in os.listdir(folder) if f.endswith(('.jpg', '.png', '.jpeg'))]
    pdf_path = os.path.join(folder, "All_Certificates.pdf")

    items = [{
        'name': f.rsplit('.', 1)[0],
        'file_url': url_for('download_generated', batch=batch, filename=f)
    } for f in files]

    pdf_url = url_for('download_generated', batch=batch, filename="All_Certificates.pdf")

    return render_template('preview.html', items=items, batch=batch, pdf_url=pdf_url)


@app.route('/generated/<batch>/<filename>')
def download_generated(batch, filename):
    folder = os.path.join(GENERATED_FOLDER, batch)
    return send_from_directory(folder, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
