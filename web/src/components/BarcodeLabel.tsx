/**
 * Print a barcode label for a product.
 * Opens a new window with the barcode SVG and triggers the print dialog.
 */
export function printBarcodeLabel(
	barcode: string,
	name: string,
	price: number,
	sku: string,
) {
	const printWindow = window.open("", "_blank");
	if (!printWindow) return;

	const label = `
    <html>
      <head>
        <title>Barcode Label - ${sku}</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"><\/script>
        <style>
          body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
          .label { text-align: center; padding: 10px; border: 1px dashed #ccc; margin-bottom: 10px; }
          .name { font-size: 14px; font-weight: bold; margin-bottom: 4px; }
          .price { font-size: 16px; color: #2563eb; margin-bottom: 4px; }
          .sku { font-size: 10px; color: #666; }
          @media print {
            @page { margin: 0.5in; }
            body { padding: 0; }
            .label { border: none; }
          }
        </style>
      </head>
      <body>
        <div class="label">
          <div class="name">${escapeHtml(name)}</div>
          <svg id="barcode"></svg>
          <div class="price">$${price.toFixed(2)}</div>
          <div class="sku">${escapeHtml(sku)}</div>
        </div>
        <script>
          try {
            JsBarcode("#barcode", "${escapeJs(barcode)}", {
              format: "CODE128",
              width: 2,
              height: 50,
              displayValue: true,
              fontSize: 12,
              margin: 5,
            });
          } catch(e) {
            document.getElementById("barcode").innerHTML = "<p style='color:red'>Barcode error</p>";
          }
          setTimeout(function() { window.print(); }, 500);
        <\/script>
      </body>
    </html>
  `;

	printWindow.document.write(label);
	printWindow.document.close();
}

function escapeHtml(s: string): string {
	return s
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

function escapeJs(s: string): string {
	return s
		.replace(/\\/g, "\\\\")
		.replace(/'/g, "\\'")
		.replace(/"/g, "\\&quot;");
}
