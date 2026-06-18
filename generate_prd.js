const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, LevelFormat, PageNumber, PageBreak, TabStopType,
  TabStopPosition, UnderlineType
} = require("docx");
const fs = require("fs");
const path = require("path");

const C = {
  navy: "1B2A4A", blue: "2563EB", accent: "3B82F6", light: "EFF6FF",
  gray: "374151", lgray: "6B7280", border: "CBD5E1", white: "FFFFFF",
  green: "166534", greenBg: "DCFCE7", yellow: "92400E", yellowBg: "FEF3C7",
  red: "991B1B", redBg: "FEE2E2",
};

const border = (color = C.border) => ({ style: BorderStyle.SINGLE, size: 1, color });
const borders = (color) => ({ top: border(color), bottom: border(color), left: border(color), right: border(color) });
const noBorder = () => ({ style: BorderStyle.NONE, size: 0, color: "FFFFFF" });
const noBorders = () => ({ top: noBorder(), bottom: noBorder(), left: noBorder(), right: noBorder() });

const spacer = (pt = 120) => new Paragraph({ children: [new TextRun("")], spacing: { before: pt, after: 0 } });

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, bold: true, size: 36, color: C.navy, font: "Arial" })],
  spacing: { before: 480, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.blue, space: 4 } }
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, bold: true, size: 28, color: C.navy, font: "Arial" })],
  spacing: { before: 320, after: 120 },
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text, bold: true, size: 24, color: C.blue, font: "Arial" })],
  spacing: { before: 240, after: 80 },
});

const body = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, size: 22, color: C.gray, font: "Arial", ...opts })],
  spacing: { before: 60, after: 60 },
});

const bodyBold = (text) => body(text, { bold: true });

const bullet = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  children: [new TextRun({ text, size: 22, color: C.gray, font: "Arial" })],
  spacing: { before: 40, after: 40 },
});

const numbered = (text, level = 0) => new Paragraph({
  numbering: { reference: "numbers", level },
  children: [new TextRun({ text, size: 22, color: C.gray, font: "Arial" })],
  spacing: { before: 40, after: 40 },
});

const code = (text) => new Paragraph({
  children: [new TextRun({ text, size: 18, font: "Courier New", color: "1E40AF" })],
  spacing: { before: 40, after: 40 },
  indent: { left: 720 },
  shading: { fill: "F1F5F9", type: ShadingType.CLEAR },
});

const titleBlock = () => [
  new Paragraph({
    children: [new TextRun({ text: "PRODUCT REQUIREMENTS DOCUMENT", size: 48, bold: true, color: C.white, font: "Arial" })],
    alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 },
    shading: { fill: C.navy, type: ShadingType.CLEAR },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.blue } }
  }),
  new Paragraph({
    children: [new TextRun({ text: "RAG-Based Document Q&A System with Analytics Dashboard", size: 28, color: "BFDBFE", font: "Arial", italics: true })],
    alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 },
    shading: { fill: C.navy, type: ShadingType.CLEAR },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Prepared for: Vestaff  |  Prepared by: Candidate  |  Version: 1.0  |  Date: June 2026", size: 18, color: "93C5FD", font: "Arial" })],
    alignment: AlignmentType.CENTER, spacing: { before: 80, after: 0 },
    shading: { fill: C.navy, type: ShadingType.CLEAR },
  }),
  new Paragraph({
    children: [new TextRun({ text: " ", size: 24, color: C.white })],
    alignment: AlignmentType.CENTER,
    shading: { fill: C.navy, type: ShadingType.CLEAR },
    spacing: { before: 0, after: 240 },
  }),
];

const infoBox = (label, text, fill = C.light, textColor = C.navy) =>
  new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
    rows: [new TableRow({ children: [
      new TableCell({
        borders: { top: { style: BorderStyle.SINGLE, size: 8, color: C.blue }, bottom: border(C.border), left: { style: BorderStyle.SINGLE, size: 8, color: C.blue }, right: border(C.border) },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 200, right: 200 },
        width: { size: 9360, type: WidthType.DXA },
        children: [
          new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 20, color: C.blue, font: "Arial" })], spacing: { before: 0, after: 40 } }),
          new Paragraph({ children: [new TextRun({ text, size: 22, color: textColor, font: "Arial" })], spacing: { before: 0, after: 0 } }),
        ]
      })
    ]})]
  });

const twoCol = (rows, w1 = 2500, w2 = 6860) =>
  new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [w1, w2],
    rows: rows.map(([a, b], i) =>
      new TableRow({ children: [
        new TableCell({
          borders: borders(C.border), width: { size: w1, type: WidthType.DXA },
          shading: { fill: i === 0 ? C.navy : "F8FAFC", type: ShadingType.CLEAR },
          margins: { top: 100, bottom: 100, left: 160, right: 160 },
          children: [new Paragraph({ children: [new TextRun({ text: a, bold: true, size: 20, color: i === 0 ? C.white : C.navy, font: "Arial" })] })]
        }),
        new TableCell({
          borders: borders(C.border), width: { size: w2, type: WidthType.DXA },
          shading: { fill: i === 0 ? C.navy : C.white, type: ShadingType.CLEAR },
          margins: { top: 100, bottom: 100, left: 160, right: 160 },
          children: [new Paragraph({ children: [new TextRun({ text: b, bold: i === 0, size: i === 0 ? 20 : 22, color: i === 0 ? C.white : C.gray, font: "Arial" })] })]
        }),
      ]})
    )
  });

const evalTable = (rows) =>
  new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [2600, 1200, 5560],
    rows: rows.map(([cat, wt, desc], i) =>
      new TableRow({ children: [
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, width: { size: 2600, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: cat, bold: i === 0, size: 20, color: i === 0 ? C.white : C.navy, font: "Arial" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, width: { size: 1200, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: wt, bold: i === 0, size: i === 0 ? 20 : 22, color: i === 0 ? C.white : (i > 0 ? C.blue : C.gray), font: "Arial" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, width: { size: 5560, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: desc, bold: i === 0, size: i === 0 ? 20 : 22, color: i === 0 ? C.white : C.gray, font: "Arial" })] })] }),
      ]})
    )
  });

const schemaTable = (rows) =>
  new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [2200, 1600, 800, 4760],
    rows: rows.map(([col, type, req, desc], i) =>
      new TableRow({ children: [
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: col, bold: i === 0, size: i === 0 ? 18 : 19, color: i === 0 ? C.white : "1E3A5F", font: "Courier New" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 1600, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: type, bold: i === 0, size: i === 0 ? 18 : 20, color: i === 0 ? C.white : "7C3AED", font: i === 0 ? "Arial" : "Courier New" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 100, right: 100 }, width: { size: 800, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: req, bold: i === 0, size: 20, color: i === 0 ? C.white : (req === "YES" ? "166534" : C.lgray), font: "Arial" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (i % 2 === 0 ? "F8FAFC" : C.white), type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 4760, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: desc, bold: i === 0, size: i === 0 ? 18 : 21, color: i === 0 ? C.white : C.gray, font: "Arial" })] })] }),
      ]})
    )
  });

const endpointTable = (rows) =>
  new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [1600, 1800, 5960],
    rows: rows.map(([method, p, desc], i) =>
      new TableRow({ children: [
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : (method === "POST" ? "EFF6FF" : (method === "GET" ? "F0FDF4" : "F8FAFC")), type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 1600, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: method, bold: true, size: i === 0 ? 18 : 20, color: i === 0 ? C.white : (method === "POST" ? "1D4ED8" : (method === "GET" ? "166534" : C.gray)), font: "Arial" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : "F8FAFC", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: p, bold: i === 0, size: i === 0 ? 18 : 20, color: i === 0 ? C.white : "1E3A5F", font: i === 0 ? "Arial" : "Courier New" })] })] }),
        new TableCell({ borders: borders(C.border), shading: { fill: i === 0 ? C.navy : C.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 140, right: 140 }, width: { size: 5960, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: desc, bold: i === 0, size: i === 0 ? 18 : 21, color: i === 0 ? C.white : C.gray, font: "Arial" })] })] }),
      ]})
    )
  });

const divider = () => new Paragraph({
  children: [new TextRun({ text: " " })],
  border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: C.border } },
  spacing: { before: 200, after: 200 },
});

const badge = (items) => new Paragraph({
  children: items.flatMap(([text, color, bg]) => [
    new TextRun({ text: `  ${text}  `, bold: true, size: 18, color, font: "Arial", shading: { fill: bg, type: ShadingType.CLEAR } }),
    new TextRun({ text: "  ", size: 18 }),
  ]),
  spacing: { before: 80, after: 80 },
});

// Load document content from separate file
const buildContent = require("./prd_content.js");
const children = buildContent({ titleBlock, spacer, twoCol, h1, h2, h3, body, bodyBold, bullet, numbered, code, infoBox, evalTable, schemaTable, endpointTable, divider, badge, PageBreak, Paragraph, TextRun, C, AlignmentType, ShadingType });

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]},
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 36, bold: true, font: "Arial", color: C.navy }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: "Arial", color: C.navy }, paragraph: { outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, font: "Arial", color: C.blue }, paragraph: { outlineLevel: 2 } },
    ]
  },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } }, children }]
});

const outputPath = path.join(__dirname, "RAG_QA_System_PRD.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log("Done: " + outputPath);
});
