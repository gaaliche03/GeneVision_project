import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle, PageBreak, Preformatted
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

from Bio import SeqIO
from io import StringIO

#generer un rapport pdf based sur les results prédites
def generate_genevision_report(analysis_results, output_path=None):

    # initialisation du style et de page du rapport
    output_path = setup_output_path(output_path)
    styles = create_styles()
    elements = []
    
    # contenu du pdf
    add_title_and_metadata(elements, styles, analysis_results) #titre et info (username,date..)
    add_general_information(elements, styles, analysis_results) #data des résultats finales
    add_sequence_data(elements, styles, analysis_results) #les séequences
    add_results_summary(elements, styles, analysis_results) #tableau de summary
    add_sequence_content_annexes(elements, styles, analysis_results) # annexe
    
    # numérotation des pages
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=A4,
        rightMargin=72, 
        leftMargin=72,
        topMargin=72, 
        bottomMargin=72
    )
    
    # fonction de numérotation 
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawRightString(A4[0] - 72, 72 * 0.5, text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number) # build the doc with page numbers
    return output_path

#création du default filename
def setup_output_path(output_path):
    if not output_path:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        return f"genevision_report_{timestamp}.pdf"
    return output_path

#définir un style pour le doc
def create_styles():
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='CustomTitle',
        fontName='Helvetica-Bold',
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        fontName='Helvetica-Bold',
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12
    ))
    
    styles.add(ParagraphStyle(
        name='AnnexTitle',
        fontName='Helvetica-Bold',
        fontSize=16,
        spaceAfter=15,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='AnnexHeading',
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceAfter=10,
        spaceBefore=12
    ))
    
    styles.add(ParagraphStyle(
        name='CodeBlock',
        fontName='Courier',
        fontSize=10,
        leading=10
    ))
    
    return styles

#ajouter le titre et metadata du rapport
def add_title_and_metadata(elements, styles, analysis_results):
    elements.append(Paragraph('GeneVision Analysis Report', styles['CustomTitle']))
    
    file_metadata = analysis_results.get('metadata', {})
    elements.append(Paragraph(f"<b>File name:</b> {file_metadata.get('report_filename', 'genevision_report.pdf')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Generation date:</b> {file_metadata.get('date', datetime.datetime.now().strftime('%B %d, %Y'))}", styles['Normal']))
    elements.append(Paragraph(f"<b>User:</b> {file_metadata.get('user', 'Unknown')}", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

#ajouter les info général sans des links(pour input sequence..)
def add_general_information(elements, styles, analysis_results):
    elements.append(Paragraph('1. General Information', styles['CustomHeading1']))
    
    sequence_contents = analysis_results.get('sequence_contents', {})
    file_types = {
        'input_sequence': 'Analyzed sequence',
        'predicted_genes': 'Predicted genes',
        'protein_sequences': 'Protein sequences',
        'protein_structures': 'Protein 3D Structure (.pdb Files)'
    }
    
    # add a note about available files
    for key, label in file_types.items():
        if key in sequence_contents:
            elements.append(Paragraph(f"<b>{label}:</b> Available in appendix", styles['Normal']))
    
    # Tools used
    tools = analysis_results.get('tools', {})
    elements.append(Paragraph("<b>Tools used:</b>", styles['Normal']))
    
    tool_mapping = {
        'gene_prediction': 'Gene prediction',
        'functional_annotation': 'Functional annotation',
        'structural_modeling': 'Structural modeling'
    }
    
    tools_items = []
    for key, label in tool_mapping.items():
        if key in tools:
            tools_items.append(ListItem(Paragraph(f"{label}: {tools[key]}", styles['Normal'])))
    
    if tools_items:
        elements.append(ListFlowable(tools_items, bulletType='bullet', start='•'))
    
    elements.append(Spacer(1, 0.2*inch))

#section sequence data
def add_sequence_data(elements, styles, analysis_results):
    elements.append(Paragraph('2. Sequence Data', styles['CustomHeading1']))
    
    sequence_data = analysis_results.get('sequence_data', {})
    field_labels = {
        'gene_count': 'Number of predicted genes',
        'protein_count': 'Number of protein sequences',
        'sequence_length': 'Total input sequence length'
    }
    
    seq_stats_items = []
    for field, label in field_labels.items():
        if field in sequence_data:
            value = sequence_data[field]
            
            # add appropriate units
            if field == 'sequence_length':
                value = f"{value} bp"
                
            seq_stats_items.append(ListItem(Paragraph(f"{label}: {value}", styles['Normal'])))
    
    if seq_stats_items:
        elements.append(ListFlowable(seq_stats_items, bulletType='bullet', start='•'))
    
    elements.append(Spacer(1, 0.2*inch))

#section results summary
def add_results_summary(elements, styles, analysis_results):
    elements.append(Paragraph('3. Results Summary', styles['CustomHeading1']))
    
    # genes table
    genes = analysis_results.get('genes', [])
    if genes:
        table_data = [
            ['Gene ID', 'Position', 'Score', 'GO Term', 'Function', 'Description']
        ]
        
        for i, gene in enumerate(genes):
            gene_id = gene.get('id', f'Gene-{i+1}')
            
            # get GO term for the new column
            go_term = gene.get('Top GO Term', 'N/A')
            
            # format description 
            description = 'N/A'
            if 'Top GO Term Description' in gene and gene['Top GO Term Description']:
                description = gene['Top GO Term Description']
            
            # create paragraph objects for the Description column
            description_para = Paragraph(description, styles['Normal'])
            
            table_data.append([
                gene_id, 
                gene.get('position', 'N/A'), 
                gene.get('score', 'N/A'),
                go_term,
                gene.get('function', 'N/A'),
                description_para
            ])
        
        # adjust column widths to accommodate the new column
        table = Table(table_data, colWidths=[60, 70, 50, 90, 110, 180])
        table.setStyle(create_table_style())
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))

#page annexe
def add_sequence_content_annexes(elements, styles, analysis_results):
    # check if there's content to display
    if not (analysis_results.get('sequence_contents') or
            analysis_results.get('go_annotations_content')):
        return
   
    # add a page break to start the appendix
    elements.append(PageBreak())
    elements.append(Paragraph('Appendix - Sequence Contents', styles['AnnexTitle']))
   
    # function to format sequences in 60-character lines (pour être de même format de input sequence)
    def format_sequence_content(content, width=60):

        # analyser contenu des fichiers .fasta
        formatted_content = ""
        for record in SeqIO.parse(StringIO(content), "fasta"):
            formatted_content += f">{record.id}\n"
            # chaque 60 caracteres dans une ligne
            seq_str = str(record.seq)
            chunks = [seq_str[i:i+width] for i in range(0, len(seq_str), width)]
            formatted_content += "\n".join(chunks) + "\n\n"
            
        return formatted_content
       
   
    # 1. display sequences
    sequence_contents = analysis_results.get('sequence_contents', {})
    for key, content in sequence_contents.items():
        if key == 'input_sequence':
            section_title = "A1. Input Sequence"
        elif key == 'predicted_genes':
            section_title = "A2. Predicted Genes"
        elif key == 'protein_sequences':
            section_title = "A3. Protein Sequences"
        else:
            section_title = f"A5. {key.replace('_', ' ').title()}"
       
        elements.append(Paragraph(section_title, styles['AnnexHeading']))
       
        # add formatted sequence content
        if content:
            if key == 'input_sequence':
                # display full input sequence without truncation
                elements.append(Preformatted(content, styles['CodeBlock']))
            elif key in ['predicted_genes', 'protein_sequences']:
                # format these sequences with 60 characters per line
                formatted_content = format_sequence_content(content)
                elements.append(Preformatted(formatted_content, styles['CodeBlock']))
        else:
            elements.append(Paragraph("Content not available", styles['Normal']))
       
        elements.append(Spacer(1, 0.3*inch))

#create style du table
def create_table_style():
    
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('WORDWRAP', (0, 0), (-1, -1), True),
        ('VALIGN', (5, 1), (5, -1), 'TOP'),
        ('LEADING', (5, 1), (5, -1), 12),
    ])

if __name__ == "__main__":
    pass