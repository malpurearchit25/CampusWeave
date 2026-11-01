"""Build the combined evaluation report from editable Markdown and verified artifacts."""
import re,json,html,textwrap
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parents[1];DOC=ROOT/'docs'
navy=colors.HexColor('#193b65');blue=colors.HexColor('#345f99');gold=colors.HexColor('#cba34a')
font='Helvetica';bold='Helvetica-Bold';serif='Times-Roman'
fonts=Path('C:/Windows/Fonts')
if (fonts/'arial.ttf').exists():
 for n,f in [('Body','arial.ttf'),('BodyBold','arialbd.ttf'),('Display','georgia.ttf')]:pdfmetrics.registerFont(TTFont(n,str(fonts/f)))
 pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
 font,bold,serif='Body','BodyBold','Display'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('Copy',fontName=font,fontSize=9.5,leading=14,spaceAfter=7,textColor=colors.HexColor('#243348')))
styles.add(ParagraphStyle('Section',fontName=serif,fontSize=22,leading=28,spaceBefore=14,spaceAfter=12,textColor=navy,keepWithNext=True))
styles.add(ParagraphStyle('Sub',fontName=bold,fontSize=12,leading=17,spaceBefore=10,spaceAfter=6,textColor=blue,keepWithNext=True))
styles.add(ParagraphStyle('Cell',parent=styles['Copy'],fontSize=8,leading=11,spaceAfter=0,wordWrap='CJK'))
styles.add(ParagraphStyle('CodeBlock',fontName='Courier',fontSize=7.4,leading=10,backColor=colors.HexColor('#f1f4f8'),borderPadding=7,spaceAfter=9))
styles.add(ParagraphStyle('Caption',parent=styles['Copy'],fontSize=8,leading=11,textColor=blue,spaceAfter=10))
W,H=A4;CONTENT=W-88
story=[]
def inline(s):
 s=s.replace('—','-').replace('–','-').replace('\u2011','-')
 s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1 (\2)',s)
 s=html.escape(s)
 s=re.sub(r'`([^`]+)`',r'<font color="#345f99">\1</font>',s)
 s=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',s)
 return s

def p(s,style='Copy'):return Paragraph(inline(s),styles[style])
def table(rows,widths=None):
 t=Table([[p(c,'Cell') for c in row] for row in rows],colWidths=widths or [CONTENT/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1e9f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,blue),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f8fa')]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 story.extend([t,Spacer(1,10)])
def markdown(path):
 lines=path.read_text(encoding='utf-8-sig').splitlines();i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('```'):
   code=[];i+=1
   while i<len(lines) and not lines[i].startswith('```'):
    code.extend(textwrap.wrap(lines[i],95,replace_whitespace=False,drop_whitespace=False) or [' ']);i+=1
   for chunk in [code[j:j+35] for j in range(0,len(code),35)]:
    story.append(Paragraph('<br/>'.join(html.escape(x).replace(' ','&#160;') for x in chunk),styles['CodeBlock']))
  elif line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r'[:\- ]+',x) for x in cells):rows.append(cells)
    i+=1
   if rows:table(rows)
   continue
  elif line.startswith('#'):
   level=len(line)-len(line.lstrip('#'));title=line.lstrip('# ').strip()
   story.append(p(title,'Section' if level<=2 else 'Sub'))
  else:
   para=[line]
   if not re.match(r'^([-*]|\d+\.) ',line):
    while i+1<len(lines) and lines[i+1].strip() and not re.match(r'^(#|\||```|[-*] |\d+\. )',lines[i+1]):i+=1;para.append(lines[i].strip())
   story.append(p(' '.join(para)))
  i+=1

def figure(name,title,maxheight=620):
 story.extend([PageBreak(),p(title,'Section')])
 im=Image(str(DOC/name));scale=min(CONTENT/im.imageWidth,maxheight/im.imageHeight)
 im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale
 story.extend([im,Spacer(1,10),p('Source: CampusWeave implementation. Full-resolution SVG and metadata dictionary are included in the repository.','Caption')])

def footer(canvas,doc):
 canvas.saveState()
 if doc.page>1:
  canvas.setStrokeColor(gold);canvas.setLineWidth(.6);canvas.line(44,H-30,W-44,H-30)
  canvas.setFont(font,8);canvas.setFillColor(navy);canvas.drawString(44,H-23,'CAMPUSWEAVE  /  DBMS PROJECT & SYLLABUS WORKBOOK')
 canvas.setFont(font,8);canvas.setFillColor(blue);canvas.drawString(44,25,'Academic edition 2026-27');canvas.drawRightString(W-44,25,str(doc.page));canvas.restoreState()

story.extend([Spacer(1,90),p('CAMPUSWEAVE / ACADEMIC PLANNING','Sub'),Spacer(1,28),Paragraph('Make room<br/>for learning.',ParagraphStyle('Cover',fontName=serif,fontSize=46,leading=54,textColor=navy)),Spacer(1,28),p('College timetable planning system','Section'),p('Project report, implementation evidence and complete DBMS syllabus workbook.'),Spacer(1,35)])
table([['RELATIONAL','NON-RELATIONAL','PL/SQL'],['MySQL 8.4','MongoDB 8.0','Oracle 21c verified']])
story.extend([Spacer(1,35),p('Prepared for academic demonstration • 1 November 2026'),p('Source: github.com/malpurearchit25/CampusWeave','Caption'),PageBreak(),p('Reading guide','Section')])
table([['Part','Contents'],['1 / Evaluation','Rubric evidence map and observed verification results'],['2 / Project report','Requirements, ER mapping, normalization, SQL, transactions, architecture, demonstration and viva'],['3 / Syllabus workbook','All six units and ten laboratory experiments, with implementation boundaries'],['4 / Visual evidence','Interface screenshots, operational ER overview, detail diagrams and warehouse'],['5 / Data dictionary','Every physical table and its declared columns, nullability and keys']],[105,CONTENT-105])
for filename in ['RUBRIC_COVERAGE.md','VERIFICATION.md','PROJECT_REPORT.md','SYLLABUS_WORKBOOK.md']:
 story.append(PageBreak());markdown(DOC/filename)
for name,title in [('screenshots/overview.jpg','The faculty workspace'),('screenshots/timetable.jpg','A published academic week'),('screenshots/lab.jpg','Live transaction and trigger evidence'),('ER_overview.png','Operational ER overview'),('ER_academic.png','Academic entities and relationships'),('ER_scheduling.png','Scheduling entities and relationships'),('ER_warehouse.png','The warehouse star schema'),('architecture.png','Application architecture')]:
 if (DOC/name).exists():figure(name,title)
story.extend([PageBreak(),p('Data dictionary','Section'),p('PK: primary key; UNI: unique key; MUL: indexed/referencing column. See schema_dictionary.json and SQL for complete composite keys, foreign keys and CHECK constraints. The timetable_entries relation is a joined view over sessions and periods.')])
data=json.loads((DOC/'schema_dictionary.json').read_text())
for name,cols in data['tables'].items():
 story.append(p(name,'Sub'))
 table([['Column','Type','Null?','Key']]+[[c['COLUMN_NAME'],c['COLUMN_TYPE'],c['IS_NULLABLE'],c['COLUMN_KEY'] or '-'] for c in cols],[CONTENT*.35,CONTENT*.4,CONTENT*.12,CONTENT*.13])
SimpleDocTemplate(str(DOC/'CampusWeave_Report.pdf'),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=47,bottomMargin=44,title='CampusWeave - DBMS project and syllabus workbook',author='CampusWeave').build(story,onFirstPage=footer,onLaterPages=footer)
print('Created docs/CampusWeave_Report.pdf')
