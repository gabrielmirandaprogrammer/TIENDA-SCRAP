// Le pide a la Function de Cloudflare que cree la preferencia
// y devuelve la URL de pago de MercadoPago.
export async function iniciarPagoMercadoPago(items) {
  const res = await fetch("/api/mercadopago/crear-preferencia", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok || !data.init_point) {
    throw new Error(data.error || "No se pudo iniciar el pago");
  }

  return data;
}