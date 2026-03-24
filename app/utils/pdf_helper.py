from markdown_pdf import Section, MarkdownPdf
import os
import tempfile

def generate_pdf_from_markdown(md_text: str, filename: str = "report.pdf") -> str:
    """
    Converts markdown text to a PDF file and returns the path to the generated file.
    The file is created in a temporary directory.
    """
    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(Section(md_text, toc=False))
    
    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    
    pdf.save(file_path)
    return file_path
