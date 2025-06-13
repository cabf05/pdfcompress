# app.py
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import pikepdf
import tempfile
import os

st.set_page_config(page_title="PDF Compressor", layout="wide")

st.title("🔧 Compressor de PDF Personalizável")

# Parâmetros ajustáveis
st.sidebar.header("Configurações de Compressão")
DPI = st.sidebar.slider("DPI de saída (pixels por polegada)", 72, 300, 150, step=1)
QUALITY = st.sidebar.slider("Qualidade JPEG (1–100)", 10, 95, 50, step=1)
MAX_FILE_KB = 1200
LETTER_PX = (int(8.5 * DPI), int(11 * DPI))

uploaded = st.file_uploader("📄 Envie um PDF (único, sem senha)", type="pdf")
if not uploaded:
    st.info("Faça o upload de um PDF para começar.")
    st.stop()

raw = uploaded.read()
try:
    doc = fitz.open(stream=raw, filetype="pdf")
except Exception:
    st.error("Não foi possível abrir o PDF (talvez esteja corrompido).")
    st.stop()

if doc.is_encrypted:
    st.error("O PDF está protegido por senha — envie uma versão sem segurança.")
    doc.close()
    st.stop()

images = []
with st.spinner("🔄 Renderizando e redimensionando páginas…"):
    for i in range(len(doc)):
        page = doc.load_page(i)
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.thumbnail(LETTER_PX, resample=Image.Resampling.LANCZOS)
        images.append(img)
doc.close()

# Monta PDF com JPEG interno
pdf_buf = io.BytesIO()
images[0].save(
    pdf_buf,
    format="PDF",
    save_all=True,
    append_images=images[1:],
    dpi=(DPI, DPI),
    quality=QUALITY,
    optimize=True,
)
pdf_buf.seek(0)

# Tenta comprimir streams via pikepdf
compressed_buf = io.BytesIO()
with pikepdf.Pdf.open(pdf_buf) as src:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()

    try:
        src.save(tmp_path, optimize_streams=True, compress_streams=True)
    except TypeError:
        src.save(tmp_path)

    with open(tmp_path, "rb") as f:
        compressed_buf.write(f.read())
    compressed_buf.seek(0)
    os.remove(tmp_path)

# Resultado
size_kb = len(compressed_buf.getvalue()) / 1024
st.markdown(f"**Tamanho do comprimido:** {size_kb:.1f} KB")
if size_kb > MAX_FILE_KB:
    st.warning(
        f"⚠️ Ainda acima de {MAX_FILE_KB} KB! "
        "Tente reduzir ainda mais o DPI ou a qualidade."
    )

st.download_button(
    label="⬇️ Baixar PDF comprimido",
    data=compressed_buf.getvalue(),
    file_name="compressed.pdf",
    mime="application/pdf",
)
