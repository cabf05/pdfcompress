# app.py
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import pikepdf

MAX_FILE_KB = 1200
MAX_DPI = 300
LETTER_PX = (int(8.5 * MAX_DPI), int(11 * MAX_DPI))  # 2550×3300 px

st.set_page_config(page_title="PDF Compressor", layout="centered")
st.title("PDF Compressor (≤300 dpi, ≤1.2 MB)")

uploaded = st.file_uploader("Upload a single PDF (no password/security)", type="pdf")
if uploaded:
    # Read into PyMuPDF
    try:
        doc = fitz.open(stream=uploaded.read(), filetype="pdf")
    except RuntimeError:
        st.error("Cannot open PDF: it may be encrypted or corrupted.")
        st.stop()

    if doc.is_encrypted:
        st.error("This PDF is password-protected; please supply an unprotected file.")
        st.stop()

    images = []
    with st.spinner("Rendering pages..."):
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render at up to MAX_DPI
            mat = fitz.Matrix(MAX_DPI / 72, MAX_DPI / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # Resize if larger than letter
            img.thumbnail(LETTER_PX, Image.ANTIALIAS)
            images.append(img)
    doc.close()

    # Re-assemble PDF in memory
    pdf_bytes = io.BytesIO()
    images[0].save(
        pdf_bytes,
        format="PDF",
        save_all=True,
        append_images=images[1:],
        dpi=(MAX_DPI, MAX_DPI),
        quality=95,
        optimize=True,
    )
    pdf_bytes.seek(0)

    # Further compress streams with pikepdf
    compressed = io.BytesIO()
    with pikepdf.Pdf.open(pdf_bytes) as src:
        src.save(
            compressed,
            optimize_streams=True,
            compress_streams=True,
        )
    compressed.seek(0)

    size_kb = len(compressed.getvalue()) / 1024
    st.write(f"🔄 Compressed file size: **{size_kb:.1f} KB**")

    if size_kb > MAX_FILE_KB:
        st.warning(
            f"Result is still larger than {MAX_FILE_KB} KB. "
            "You may need to further downsample images or split the document."
        )

    st.download_button(
        "📥 Download compressed PDF",
        compressed.getvalue(),
        file_name="compressed.pdf",
        mime="application/pdf",
    )
