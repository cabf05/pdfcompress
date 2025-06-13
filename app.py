# app.py
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import pikepdf
import tempfile
import os

# Configurações
MAX_FILE_KB = 1200
MAX_DPI = 300
LETTER_PX = (int(8.5 * MAX_DPI), int(11 * MAX_DPI))  # 2550×3300 px

st.set_page_config(page_title="PDF Compressor", layout="centered")
st.title("PDF Compressor (≤300 dpi, ≤1.2 MB)")

uploaded = st.file_uploader("Envie um único PDF (sem senha/proteção)", type="pdf")
if not uploaded:
    st.info("Faça o upload de um PDF para iniciar.")
    st.stop()

# 1) Abre e valida PDF
raw = uploaded.read()
try:
    doc = fitz.open(stream=raw, filetype="pdf")
except Exception:
    st.error("Não foi possível abrir o PDF. Ele pode estar corrompido.")
    st.stop()

if doc.is_encrypted:
    st.error("PDF protegido por senha. Envie um PDF sem proteção.")
    doc.close()
    st.stop()

# 2) Renderiza páginas em ≤300 dpi e redimensiona para Carta
images = []
with st.spinner("Renderizando páginas…"):
    for i in range(len(doc)):
        page = doc.load_page(i)
        mat = fitz.Matrix(MAX_DPI / 72, MAX_DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.thumbnail(LETTER_PX, resample=Image.Resampling.LANCZOS)
        images.append(img)
doc.close()

# 3) Recria PDF em memória
pdf_buf = io.BytesIO()
images[0].save(
    pdf_buf,
    format="PDF",
    save_all=True,
    append_images=images[1:],
    dpi=(MAX_DPI, MAX_DPI),
    quality=95,
    optimize=True,
)
pdf_buf.seek(0)

# 4) Tenta comprimir com pikepdf (flags) e faz fallback se necessário
compressed_buf = io.BytesIO()
with pikepdf.Pdf.open(pdf_buf) as src:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()

    try:
        # primeira tentativa: com flags
        src.save(tmp_path, optimize_streams=True, compress_streams=True)
    except TypeError:
        # fallback: save simples
        src.save(tmp_path)

    # lê de volta para a memória
    with open(tmp_path, "rb") as f:
        compressed_buf.write(f.read())
    compressed_buf.seek(0)
    os.remove(tmp_path)

# 5) Exibe resultado e download
size_kb = len(compressed_buf.getvalue()) / 1024
st.write(f"🔄 Tamanho do PDF comprimido: **{size_kb:.1f} KB**")
if size_kb > MAX_FILE_KB:
    st.warning(
        f"Resultado ainda acima de {MAX_FILE_KB} KB. "
        "Considere reduzir qualidade ou dividir o documento."
    )

st.download_button(
    label="📥 Baixar PDF comprimido",
    data=compressed_buf.getvalue(),
    file_name="compressed.pdf",
    mime="application/pdf",
)
