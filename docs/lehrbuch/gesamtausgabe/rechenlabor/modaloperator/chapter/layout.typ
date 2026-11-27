#let diff = $∂$
#let teal = rgb("#087b74")
#let ink = rgb("#182d38")
#let soft = rgb("#586a70")
#set page(paper: "a4", margin: (x: 20mm, top: 21mm, bottom: 20mm),
  header: context [
    #set text(font: "Noto Sans", size: 8pt, fill: soft)
    NUMERISCHE SIMULATION DYNAMISCHER SYSTEME #h(1fr) KAPITEL 9
    #v(2pt)#line(length: 100%, stroke: 0.45pt + rgb("#aac3c0"))
  ],
  footer: context [
    #line(length: 100%, stroke: 0.4pt + rgb("#b9cac7"))#v(4pt)
    #set text(font: "Noto Sans", size: 7.8pt, fill: soft)
    ARGESIM · Vergleichsstudie zu PR 91 #h(1fr) #counter(page).display("1")
  ])
#set text(font: "Noto Serif", size: 12pt, fill: ink, lang: "de", hyphenate: true)
#set par(justify: true, leading: 0.68em, spacing: 1.02em)
#set block(spacing: 1.02em)
#set heading(numbering: none)
#show heading.where(level: 1): it => block(above: 1mm, below: 5mm)[
  #set text(font: "Noto Sans", size: 29pt, weight: "bold", fill: ink, hyphenate: false)
  #set par(justify: false, leading: 0.23em)
  #it.body
]
#show heading.where(level: 2): it => block(above: 0pt, below: 4mm)[
  #set text(font: "Noto Sans", size: 21pt, weight: "bold", fill: ink, hyphenate: false)
  #set par(justify: false, leading: 0.32em)
  #it.body
]
#show strong: set text(weight: "bold", fill: ink)
#show link: set text(fill: teal)
#show raw: set text(font: "Noto Sans Mono", size: 10pt)
#set table(inset: (x: 5pt, y: 4pt), stroke: none,
  fill: (x,y) => if y == 0 {rgb("#d8eae7")} else if calc.even(y) {rgb("#f1f6f5")} else {white})
#show table: set text(font: "Noto Sans", size: 10pt)
#show table: set par(justify: false, leading: 0.4em)
#show table.cell.where(y: 0): set text(weight: "bold")
#set figure(gap: 4pt)
#show figure.caption: set text(font: "Noto Sans", size: 9pt, fill: soft)
#show figure.caption: set par(justify: false)
#show math.equation.where(block: true): set block(above: 0.72em, below: 0.72em)
