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

uploaded = st.file_uploader("Envie um único PDF (sem senha ou proteção)", type="pdf")
if not uploaded:
    st.info("Por favor, faça upload de um arquivo PDF para iniciar a compressão.")
    st.stop()

# Tenta abrir com PyMuPDF
try:
    raw = uploaded.read()
    doc = fitz.open(stream=raw, filetype="pdf")
except Exception:
    st.error("Não foi possível abrir o PDF. Verifique se o arquivo não está corrompido.")
    st.stop()

if doc.is_encrypted:
    st.error("O PDF está protegido por senha ou tem segurança ativada. Envie um arquivo sem proteção.")
    doc.close()
    st.stop()

# Renderiza cada página em até 300 dpi e redimensiona para tamanho carta
images = []
with st.spinner("Processando páginas..."):
    for i in range(len(doc)):
        page = doc.load_page(i)
        mat = fitz.Matrix(MAX_DPI / 72, MAX_DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # Redimensiona mantendo proporção, cabendo em Letter
        img.thumbnail(LETTER_PX, resample=Image.Resampling.LANCZOS)
        images.append(img)
doc.close()

# Monta novo PDF em memória
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

# Comprime streams via pikepdf usando arquivo temporário
compressed_buf = io.BytesIO()
with pikepdf.Pdf.open(pdf_buf) as src:
    # Cria arquivo temporário
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp_file.name
    tmp_file.close()
    # Salva versão otimizada
    src.save(
        tmp_path,
        optimize_streams=True,
        compress_streams=True,
    )
    # Lê de volta para memória
    with open(tmp_path, "rb") as f:
        compressed_buf.write(f.read())
    compressed_buf.seek(0)
    # Remove arquivo temporário
    os.remove(tmp_path)

# Exibe tamanho final e botão de download
size_kb = len(compressed_buf.getvalue()) / 1024
st.write(f"🔄 Tamanho do PDF comprimido: **{size_kb:.1f} KB**")

if size_kb > MAX_FILE_KB:
    st.warning(
        f"O resultado ainda ultrapassa {MAX_FILE_KB} KB. "
        "Considere reduzir ainda mais a qualidade ou dividir o documento."
    )

st.download_button(
    label="📥 Baixar PDF comprimido",
    data=compressed_buf.getvalue(),
    file_name="compressed.pdf",
    mime="application/pdf",
)
