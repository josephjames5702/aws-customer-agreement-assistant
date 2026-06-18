import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf(source_md_path: str, output_pdf_path: str):
    """Parses the fetched markdown file and generates a clean PDF."""
    print(f"Reading markdown from {source_md_path}...")
    
    if not os.path.exists(source_md_path):
        print(f"Error: Source file {source_md_path} not found.")
        sys.exit(1)
        
    with open(source_md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Extract lines belonging to the actual agreement (between last updated and footer)
    content_started = False
    agreement_lines = []
    
    for line in lines:
        stripped = line.strip()
        if "Last Updated:" in stripped:
            content_started = True
        if content_started:
            if "Prior Version" in stripped or "Create an AWS account" in stripped:
                break
            agreement_lines.append(line)
            
    if not agreement_lines:
        print("Warning: Could not parse agreement section automatically, using whole file.")
        agreement_lines = lines

    # Create directory for output if it doesn't exist
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=8
    )
    
    story = []
    
    # Add title
    story.append(Paragraph("AWS Customer Agreement", title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    for line in agreement_lines:
        text = line.strip()
        if not text:
            continue
            
        # Basic markdown parsing
        if text.startswith("#"):
            # Header
            clean_text = text.lstrip("#").strip()
            level = len(text) - len(clean_text)
            if level == 1:
                story.append(Paragraph(clean_text, title_style))
            else:
                story.append(Paragraph(clean_text, heading_style))
        else:
            # Body paragraph
            story.append(Paragraph(text, body_style))
            
    print(f"Building PDF at {output_pdf_path}...")
    doc.build(story)
    print("PDF generation complete.")

if __name__ == "__main__":
    # If run directly, generate PDF from the steps cache
    source = r"C:\Users\josep\.gemini\antigravity\brain\492d8a3c-40c9-4f61-9149-5c941a88a313\.system_generated\steps\128\content.md"
    dest = r"c:\ieee paper\google proj\data\pdfs\aws_customer_agreement.pdf"
    generate_pdf(source, dest)
