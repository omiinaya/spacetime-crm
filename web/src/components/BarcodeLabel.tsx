import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";

interface BarcodeLabelProps {
  barcode: string;
  productName: string;
  price: number;
  sku?: string;
}

export default function BarcodeLabel({ barcode, productName, price, sku }: BarcodeLabelProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (svgRef.current) {
      try {
        JsBarcode(svgRef.current, barcode, {
          format: barcode.length >= 12 ? "EAN13" : "CODE128",
          width: 2,
          height: 50,
          displayValue: true,
          fontSize: 14,
          margin: 5,
          background: "#ffffff",
          lineColor: "#000000",
        });
      } catch {
        // fallback: just show text if barcode format fails
      }
    }
  }, [barcode]);

  return (
    <div className="inline-block bg-white p-3 rounded border border-gray-200">
      <svg ref={svgRef} />
      <p className="text-xs text-gray-500 text-center mt-1 max-w-[180px] truncate">{productName}</p>
      <p className="text-sm font-bold text-center text-black">${price.toFixed(2)}</p>
      {sku && <p className="text-[10px] text-gray-400 text-center">{sku}</p>}
    </div>
  );
}

export function printBarcodeLabel(barcode: string, productName: string, price: number, sku?: string) {
  // Build a temp SVG via jsbarcode
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("style", "width: 200px; height: 80px;");
  try {
    JsBarcode(svg, barcode, {
      format: barcode.length >= 12 ? "EAN13" : "CODE128",
      width: 2,
      height: 40,
      displayValue: true,
      fontSize: 12,
      margin: 5,
      background: "#ffffff",
      lineColor: "#000000",
    });
  } catch {
    // fallback
  }

  const svgHtml = new XMLSerializer().serializeToString(svg);

  const win = window.open("", "_blank");
  if (!win) {
    alert("Pop-up blocked. Please allow pop-ups for this site.");
    return;
  }

  win.document.write(`
    <!DOCTYPE html>
    <html>
    <head><title>Barcode Label - ${productName}</title>
    <style>
      @page { margin: 0.25in; size: 2in 1in; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        min-height: 100vh;
        font-family: Arial, sans-serif;
      }
      .label {
        text-align: center;
        padding: 8px;
        width: 2in;
      }
      .label svg { max-width: 100%; }
      .label .name { font-size: 10px; color: #333; margin-top: 2px; }
      .label .price { font-size: 14px; font-weight: bold; margin-top: 1px; }
      .label .sku { font-size: 8px; color: #999; }
      @media print {
        body { min-height: auto; }
      }
    </style>
    </head>
    <body>
      <div class="label">
        ${svgHtml}
        <div class="name">${productName.replace(/</g, "&lt;")}</div>
        <div class="price">$${price.toFixed(2)}</div>
        ${sku ? `<div class="sku">${sku.replace(/</g, "&lt;")}</div>` : ""}
      </div>
      <script>
        window.onload = function() { window.print(); window.close(); };
      <\\/script>
    </body>
    </html>
  `);
  win.document.close();
}
