from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .renderer import InvoiceDraft


def render_pdf(output_pdf: Path, draft: InvoiceDraft) -> None:
    """Render the inspected invoice design directly to PDF without Excel."""
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(output_pdf), pagesize=A4)
    width, height = A4
    left, right, top = 18 * mm, width - 18 * mm, height - 18 * mm
    canvas.setTitle(f"Invoice {draft.invoice_number}")
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(left, top, "Resoflex IT Solutions (Pvt) Ltd.")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(left, top - 14, "Hettiyawatta, 12Th Lane, Puttalam Road, Kurunegala.")
    canvas.drawString(left, top - 26, "Tel : 071 6834 086")
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawRightString(right, top - 4, "Sales Invoice")

    y = top - 58
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(left, y, "To:")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(left + 22 * mm, y, draft.customer_name)
    canvas.drawString(left + 22 * mm, y - 13, draft.customer_address)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(right - 58 * mm, y, "Date:")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(right - 42 * mm, y, draft.invoice_date.strftime("%d %b, %Y"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(right - 58 * mm, y - 14, "Invoice #:")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(right - 42 * mm, y - 14, draft.invoice_number)

    y -= 58
    canvas.setFillColor(colors.HexColor("#eeeeee"))
    canvas.rect(left, y - 5, right - left, 22, fill=1, stroke=0)
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(left + 2, y + 3, "Qty")
    canvas.drawString(left + 22 * mm, y + 3, "Description")
    canvas.drawRightString(right - 35 * mm, y + 3, "Unit Price")
    canvas.drawRightString(right - 2, y + 3, "Line Total")
    y -= 20
    canvas.setFont("Helvetica", 8)
    for line in draft.lines:
        canvas.drawString(left + 2, y, f"{line.quantity:g}")
        canvas.drawString(left + 22 * mm, y, line.description[:85])
        canvas.drawRightString(right - 35 * mm, y, f"{line.unit_price:,.2f}")
        canvas.drawRightString(right - 2, y, f"{line.total:,.2f}")
        y -= 15
    y -= 5
    canvas.line(left, y, right, y)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawRightString(right - 35 * mm, y - 18, "Total")
    canvas.drawRightString(right - 2, y - 18, f"{draft.total:,.2f}")

    y -= 65
    canvas.setFont("Helvetica", 8)
    canvas.drawString(left, y, "Salesperson:")
    canvas.drawString(left + 24 * mm, y, draft.salesperson)
    canvas.drawString(left + 80 * mm, y, "Job:")
    canvas.drawString(left + 93 * mm, y, draft.job)
    canvas.drawString(left, y - 14, "Payment Terms:")
    canvas.drawString(left + 28 * mm, y - 14, draft.payment_terms)
    canvas.drawString(left + 80 * mm, y - 14, "Due Date:")
    canvas.drawString(left + 100 * mm, y - 14, draft.due_date.strftime("%d %b, %Y"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(left, 50 * mm, "Please Kindly Deposit the Payment to Commercial Bank (York Street / City Office)")
    canvas.drawString(left, 43 * mm, "A/C 1020012966, Resoflex IT Solutions Pvt. Ltd.")
    canvas.drawString(left, 25 * mm, "Director")
    canvas.drawRightString(right, 25 * mm, "Client's Signature")
    canvas.save()

