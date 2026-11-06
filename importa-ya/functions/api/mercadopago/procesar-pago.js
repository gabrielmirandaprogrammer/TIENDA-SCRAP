// Procesa un pago con tarjeta usando el token que entrega el Payment Brick.
// Requiere MP_ACCESS_TOKEN, SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY (solo servidor).

export async function onRequestPost({ request, env }) {
  if (!env.MP_ACCESS_TOKEN || !env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return Response.json({ error: "variables de servidor no configuradas" }, { status: 500 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "cuerpo invalido" }, { status: 400 });
  }

  const items = Array.isArray(body.items) ? body.items : [];
  const formData = body.formData || {};

  if (!formData.token) {
    return Response.json({ error: "falta el token de la tarjeta" }, { status: 400 });
  }

  const ids = items.map((i) => Number(i.id)).filter(Number.isFinite);
  if (ids.length === 0) {
    return Response.json({ error: "carrito vacio" }, { status: 400 });
  }

  const headersSb = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
  };

  // Precios reales desde la base: el cliente nunca manda montos
  const resProd = await fetch(
    `${env.SUPABASE_URL}/rest/v1/productos?id=in.(${ids.join(",")})&select=id,nombre,precio`,
    { headers: headersSb }
  );
  const productos = await resProd.json();

  const lineas = [];
  for (const item of items) {
    const p = productos.find((x) => x.id === item.id);
    if (!p || !(Number(p.precio) > 0)) continue;
    const cantidad = Math.max(1, Math.min(99, Math.floor(Number(item.cantidad) || 1)));
    lineas.push({
      producto_id: p.id,
      nombre: p.nombre,
      cantidad,
      precio_unitario: Number(p.precio),
      subtotal: Number(p.precio) * cantidad,
    });
  }

  if (lineas.length === 0) {
    return Response.json({ error: "no hay productos validos" }, { status: 400 });
  }

  const total = lineas.reduce((s, l) => s + l.subtotal, 0);
  const origen = new URL(request.url).origin;

  // 1. Pedido pendiente
  const resPedido = await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos`, {
    method: "POST",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify([{ total, estado: "pendiente", metodo_pago: "mercadopago" }]),
  });

  if (!resPedido.ok) {
    console.error("Supabase rechazo el pedido:", resPedido.status, await resPedido.text());
    return Response.json({ error: "no se pudo registrar el pedido" }, { status: 500 });
  }

  const pedido = (await resPedido.json())[0];

  // 2. Lineas del pedido
  const resDetalles = await fetch(`${env.SUPABASE_URL}/rest/v1/detalle_pedido`, {
    method: "POST",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify(
      lineas.map((l) => ({
        pedido_id: pedido.id,
        producto_id: l.producto_id,
        cantidad: l.cantidad,
        precio_unitario: l.precio_unitario,
        subtotal: l.subtotal,
      }))
    ),
  });

  if (!resDetalles.ok) {
    console.error("Supabase rechazo el detalle:", resDetalles.status, await resDetalles.text());
    await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?id=eq.${pedido.id}`, {
      method: "DELETE",
      headers: headersSb,
    });
    return Response.json({ error: "no se pudo registrar el detalle del pedido" }, { status: 500 });
  }

  // 3. Crear el pago con el token de la tarjeta
  const cuerpoPago = {
    transaction_amount: total,
    token: formData.token,
    description: lineas.map((l) => `${l.cantidad}x ${l.nombre}`).join(", ").slice(0, 250),
    installments: Number(formData.installments) || 1,
    payment_method_id: formData.payment_method_id,
    payer: {
      email: formData.payer?.email,
      identification: formData.payer?.identification,
    },
    external_reference: String(pedido.id),
    notification_url: `${origen}/api/mercadopago/webhook`,
  };

  if (formData.issuer_id) cuerpoPago.issuer_id = String(formData.issuer_id);

  const resPago = await fetch("https://api.mercadopago.com/v1/payments", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.MP_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
      "X-Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(cuerpoPago),
  });

  const pago = await resPago.json();

  if (!resPago.ok) {
    console.error("MercadoPago rechazo el pago:", resPago.status, JSON.stringify(pago));
    return Response.json(
      {
        error: "no se pudo procesar el pago",
        detalle: pago?.message || pago?.cause?.[0]?.description || null,
      },
      { status: 500 }
    );
  }

  // 4. Auditoria (no critica)
  await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?id=eq.${pedido.id}`, {
    method: "PATCH",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ pago_id: String(pago.id), datos: pago }),
  });

  const estados = {
    approved: "aprobado",
    pending: "pendiente",
    in_process: "pendiente",
    authorized: "pendiente",
    rejected: "rechazado",
    cancelled: "cancelado",
    refunded: "devuelto",
  };

  return Response.json({
    pedido_id: String(pedido.id),
    pago_id: String(pago.id),
    estado: estados[pago.status] || pago.status,
    estado_mp: pago.status,
    detalle: pago.status_detail,
    mensaje: pago.status_detail,
    tres_ds_url: pago.three_ds_info?.external_resource_url || null,
  });
}