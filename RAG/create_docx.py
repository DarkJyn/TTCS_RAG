from docx import Document
from pathlib import Path

def txt_to_docx(txt_path_str):
    txt_path = Path(txt_path_str)
    if not txt_path.exists():
        print(f"Not found: {txt_path}")
        return
        
    content = txt_path.read_text(encoding="utf-8")
    doc = Document()
    
    # Split content by newline to create proper paragraphs
    for line in content.split('\n'):
        # Only add paragraph if line has content or it's an intentional blank line
        doc.add_paragraph(line.strip())
        
    docx_path = txt_path.with_suffix('.docx')
    doc.save(docx_path)
    print(f"Created: {docx_path}")

if __name__ == "__main__":
    txt_to_docx(r"d:\Dean'sCode\TTCS\RAG\test_pairs\pair_01_v1.txt")
    txt_to_docx(r"d:\Dean'sCode\TTCS\RAG\test_pairs\pair_01_v2.txt")
