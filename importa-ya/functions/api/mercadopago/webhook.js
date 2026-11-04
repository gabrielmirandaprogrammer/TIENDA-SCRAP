// Webhook de MercadoPago: recibe notificaciones y actualiza el estado del pedido.
// Siempre consulta el pago directo a la API de MercadoPago; nunca confía en el POST.
export async function onRequestPost({ request, env }) {
  const url = new URL(request.url);
  let paymentId = url.searchParams.get("data.id") || url.searchParams.get("id");
  let type = url.searchParams.get("type") || url.searchParams.get("topic");

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

  if (!pago.external_reference) {
    return new Response("ok", { status: 200 });
  }

  const headers = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "return=minimal",
  };
  const filtro = `id=eq.${encodeURIComponent(pago.external_reference)}`;

  // Critico: estado del pedido (columnas garantizadas del esquema)
  await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?${filtro}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({
      estado: estados[pago.status] || pago.status,
      metodo_pago: `mercadopago/${pago.payment_method_id || "desconocido"}`,
    }),
  });

  // Auditoria no critica (ignora errores si las columnas no existen todavia)
  await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?${filtro}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ pago_id: String(pago.id), datos: pago }),
  });

  return new Response("ok", { status: 200 });
}