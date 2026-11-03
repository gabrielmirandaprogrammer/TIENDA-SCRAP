// Webhook de MercadoPago: recibe notificaciones y actualiza el estado del pedido.
export async function onRequestPost({ request, env }) {
  const url = new URL(request.url);
  let paymentId = url.searchParams.get("data.id") || url.searchParams.get("id");
  let type = url.searchParams.get("type") || url.searchParams.get("topic");

  // MercadoPago a veces envia el cuerpo como JSON
  if (!paymentId) {
    try {
      const cuerpo = await request.json();
      if (cuerpo?.data?.id) paymentId = String(cuerpo.data.id);
      type = type || cuerpo?.type || cuerpo?.topic;
    } catch {
      /* cuerpo vacio: solo responder ok */
    }
  }

  if (!paymentId || (type && type !== "payment")) {
    return new Response("ok", { status: 200 });
  }

  const resPago = await fetch(`https://api.mercadopago.com/v1/payments/${paymentId}`, {
    headers: { Authorization: `Bearer ${env.MP_ACCESS_TOKEN}` },
  });
  if (!resPago.ok) {
    return new Response("error consultando pago", { status: 500 });
  }
  const pago = await resPago.json();

  const estados = {
    approved: "pagado",
    pending: "pendiente",
    in_process: "pendiente",
    authorized: "pendiente",
    rejected: "rechazado",
    cancelled: "cancelado",
    refunded: "devuelto",
  };

  const patch = {
    estado: estados[pago.status] || pago.status,
    transaction_id: String(pago.id),
    medio_pago: pago.payment_method_id || null,
    motivo: pago.status_detail || null,
    monto: pago.transaction_amount || null,
    datos: pago,
  };

  if (pago.external_reference) {
    await fetch(
      `${env.SUPABASE_URL}/rest/v1/pedidos?id=eq.${encodeURIComponent(pago.external_reference)}`,
      {
        method: "PATCH",
        headers: {
          apikey: env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
          "Content-Type": "application/json",
          Prefer: "return=minimal",
        },
        body: JSON.stringify(patch),
      }
    );
  }

  return new Response("ok", { status: 200 });
}