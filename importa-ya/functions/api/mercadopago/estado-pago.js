// Consulta el estado de un pago de MercadoPago por su id.
export async function onRequestGet({ request, env }) {
  const pagoId = new URL(request.url).searchParams.get("pago_id");
  if (!pagoId) return Response.json({ error: "falta pago_id" }, { status: 400 });

  const res = await fetch(`https://api.mercadopago.com/v1/payments/${pagoId}`, {
    headers: { Authorization: `Bearer ${env.MP_ACCESS_TOKEN}` },
  });
  if (!res.ok) return Response.json({ error: "no se pudo consultar" }, { status: 500 });

  const pago = await res.json();
  const estados = {
    approved: "aprobado", pending: "pendiente", in_process: "pendiente",
    authorized: "pendiente", rejected: "rechazado", cancelled: "cancelado",
    refunded: "devuelto",
  };

  return Response.json({
    estado: estados[pago.status] || pago.status,
    pedido_id: pago.external_reference || null,
    detalle: pago.status_detail || null,
  });
}