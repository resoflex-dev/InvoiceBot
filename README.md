# Resoflex InvoiceBot

Milestone 1 currently provides a local, template-preserving invoice renderer.

The inspected template is `template/Bill-919 - Pack Mart Service Charges.xlsx`.
The original `.xls` and the untouched `.xlsx` backup remain in `template/`.

Run tests from the project root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

PDF export is intentionally isolated behind `export_pdf_with_excel` and requires
`pywin32` plus Microsoft Excel on the Windows host.
