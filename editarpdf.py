import fitz  # PyMuPDF para modificar PDFs
import streamlit as st
from PIL import Image
import io
from deep_translator import GoogleTranslator
import inflect


company_logo_path = "nombre.png"  # Ruta de la imagen fija con el nombre de la empresa
company_logo = Image.open(company_logo_path)
# Función para convertir números con centavos a texto en inglés sin guiones ni comas
def numero_a_texto(numero):
    try:
        partes = numero.replace(',', '').split('.')
        entero = int(partes[0])
        centavos = int(partes[1]) if len(partes) > 1 else 0
        p = inflect.engine()
        texto_entero = p.number_to_words(entero, andword="").upper().replace("-", " ").replace(",", "")
        texto_centavos = p.number_to_words(centavos, andword="").upper().replace("-", " ").replace(",", "") if centavos > 0 else ""
        if centavos > 0:
            return f"{texto_entero} DOLLARS WITH {texto_centavos} CENTS"
        return f"{texto_entero} DOLLARS"
    except ValueError:
        return numero  # Si no es un número válido, devolver el mismo valor

# Función para modificar el PDF
def modificar_factura(pdf_bytes, export_type, new_logo, invoice_value_text, gastos_value):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    max_width = 360  # Ancho máximo antes de hacer un salto de línea
    line_spacing = 14  # Espaciado entre líneas
    
    for page in doc:
       # Reemplazar razón social con una imagen fija
        text_instances = page.search_for("INDUSTRIAS FLYBB SAS")
        for inst in text_instances:
            rect = fitz.Rect(inst.x0, inst.y0, inst.x1, inst.y1)
            page.draw_rect(rect, color=(1,1,1), fill=(1,1,1), overlay=True)
            img_byte_arr = io.BytesIO()
            company_logo.save(img_byte_arr, format='PNG')
            page.insert_image(rect, stream=img_byte_arr.getvalue())

        # Reemplazar INVOICE VALU por INVOICE VALUE en la misma ubicación exacta
        text_instances = page.search_for("INVOICE VALU")
        for inst in text_instances:
            rect = fitz.Rect(inst.x0, inst.y0, inst.x1, inst.y1)
            page.draw_rect(rect, color=(1,1,1), fill=(1,1,1), overlay=True)
            page.insert_text((inst.x0, inst.y1), "INVOICE VALUE", fontsize=10, color=(0, 0, 0), fontname="helvetica-bold")
                        
            # Insertar el valor en letras con salto de línea si excede el ancho máximo
            palabras = invoice_value_text.split()
            linea_actual = ""
            y_offset = inst.y1 + line_spacing
            for palabra in palabras:
                if fitz.get_text_length(linea_actual + " " + palabra, fontname="helvetica", fontsize=10) > max_width:
                    page.insert_text((inst.x0, y_offset), linea_actual, fontsize=10, color=(0, 0, 0), fontname="helvetica")
                    linea_actual = palabra
                    y_offset += line_spacing
                else:
                    linea_actual += " " + palabra if linea_actual else palabra
            page.insert_text((inst.x0, y_offset), linea_actual, fontsize=10, color=(0, 0, 0), fontname="helvetica")
        
        # Reemplazar SOLO TOTAL USD por el tipo de exportación sin afectar SUBTOTAL USD
        text_instances = page.search_for("TOTAL USD")
        for inst in text_instances:
            if not any(sub_inst.y0 == inst.y0 and "SUBTOTAL USD" in page.get_text("text") for sub_inst in page.search_for("SUBTOTAL USD")):
                rect = fitz.Rect(inst.x0, inst.y0, inst.x1, inst.y1)
                page.draw_rect(rect, color=(1,1,1), fill=(1,1,1), overlay=True)
                page.insert_text((inst.x0, inst.y1 -2.5), export_type, fontsize=9, color=(0, 0, 0), fontname="helvetica-bold")
                page.insert_text((inst.x1 + 109, inst.y1 -2.5), invoice_value_code, fontsize=9, color=(0, 0, 0), fontname="helvetica")

        # Reemplazar el valor de GASTOS USD asegurando que no sobrepase inst.x1 + 130
        text_instances = page.search_for("GASTOS USD")
        for inst in text_instances:
            max_x = inst.x1 + 130
            text_width = fitz.get_text_length(gastos_value, fontname="helvetica", fontsize=9)
            gastos_x_pos = max_x - text_width if text_width < 130 else inst.x1
            page.insert_text((gastos_x_pos, inst.y1 -2.5), gastos_value, fontsize=9, color=(0, 0, 0), fontname="helvetica")

        # Cambiar el logo en la misma posición
        if new_logo:
            img = Image.open(new_logo)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            
            image_instances = page.get_images(full=True)
            if image_instances:
                img_index = image_instances[0][0]
                img_rect = page.get_image_rects(img_index)[0]
                page.draw_rect(img_rect, color=(1,1,1), fill=(1,1,1), overlay=True)
                page.insert_image(img_rect, stream=img_byte_arr.getvalue())
    
    # Guardar PDF modificado en memoria
    output_bytes = io.BytesIO()
    doc.save(output_bytes)
    doc.close()
    return output_bytes.getvalue()

# Interfaz en Streamlit
st.title("Editor de Facturas en PDF")

uploaded_file = st.file_uploader("Sube una factura en PDF", type=["pdf"])
new_logo = st.file_uploader("Sube el nuevo logo (opcional)", type=["png", "jpg"])
export_type = st.text_input("Nuevo tipo de exportación", "EXW")
invoice_value_code = st.text_input("Valor en número (USD, con centavos opcional)")
gastos_value = st.text_input("Valor de GASTOS USD")

if invoice_value_code:
    invoice_value_text = numero_a_texto(invoice_value_code)
else:
    invoice_value_text = ""

if uploaded_file and export_type and invoice_value_text and gastos_value:
    if st.button("Modificar Factura"):
        modified_pdf = modificar_factura(uploaded_file.read(), export_type, new_logo, invoice_value_text, gastos_value)
        st.download_button("Descargar Factura Modificada", modified_pdf, "factura_modificada.pdf", "application/pdf")

