// Crea una preferencia de pago en MercadoPago (Checkout Pro).
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
  const ids = items.map((i) => Number(i.id)).filter(Number.isFinite);
  if (ids.length === 0) {
    return Response.json({ error: "carrito vacio" }, { status: 400 });
  }

  const headersSb = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
  };

  // Precios reales desde la base (el cliente no manda precios, solo ids y cantidades)
  const resProd = await fetch(
    `${env.SUPABASE_URL}/rest/v1/productos?id=in.(${ids.join(",")})&select=id,nombre,precio`,
    { headers: headersSb }
  );
  const productos = await resProd.json();

  const itemsMP = [];
  for (const item of items) {
    const p = productos.find((x) => x.id === item.id);
    if (!p || !(Number(p.precio) > 0)) continue;
    const cantidad = Math.max(1, Math.min(99, Math.floor(Number(item.cantidad) || 1)));
    itemsMP.push({
      id: String(p.id),
      title: p.nombre,
      quantity: cantidad,
      unit_price: Number(p.precio),
      currency_id: "COP",
    });
  }

  if (itemsMP.length === 0) {
    return Response.json({ error: "no hay productos validos" }, { status: 400 });
  }

  const origen = new URL(request.url).origin;
  const total = itemsMP.reduce((s, i) => s + i.unit_price * i.quantity, 0);

  // 1. Registrar el pedido como pendiente (esquema real: total NOT NULL)
  const resPedido = await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos`, {
    method: "POST",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=representation" },
    body: JSON.stringify([
      { total, estado: "pendiente", metodo_pago: "mercadopago" },
    ]),
  });
  if (!resPedido.ok) {
    console.error("Supabase rechazo el pedido:", resPedido.status, await resPedido.text());
    return Response.json({ error: "no se pudo registrar el pedido" }, { status: 500 });
  }
  const pedido = (await resPedido.json())[0];

  // 2. Registrar las lineas del pedido en detalle_pedido
  const resDetalles = await fetch(`${env.SUPABASE_URL}/rest/v1/detalle_pedido`, {
    method: "POST",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify(
      itemsMP.map((i) => ({
        pedido_id: pedido.id,
        producto_id: Number(i.id),
        cantidad: i.quantity,
        precio_unitario: i.unit_price,
        subtotal: i.unit_price * i.quantity,
      }))
    ),
  });
  if (!resDetalles.ok) {
    console.error("Supabase rechazo el detalle:", resDetalles.status, await resDetalles.text());
    // Limpieza: no dejar un pedido huerfano sin lineas
    await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?id=eq.${pedido.id}`, {
      method: "DELETE",
      headers: headersSb,
    });
    return Response.json({ error: "no se pudo registrar el detalle del pedido" }, { status: 500 });
  }

  // 3. Crear la preferencia en MercadoPago
  const resPref = await fetch("https://api.mercadopago.com/checkout/preferences", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.MP_ACCESS_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      items: itemsMP,
      external_reference: String(pedido.id),
      back_urls: {
        success: `${origen}/pago/respuesta?estado=aprobado`,
        pending: `${origen}/pago/respuesta?estado=pendiente`,
        failure: `${origen}/pago/respuesta?estado=rechazado`,
      },
      auto_return: "approved",
      notification_url: `${origen}/api/mercadopago/webhook`,
    }),
  });

  if (!resPref.ok) {
    console.error("MercadoPago rechazo la preferencia:", await resPref.text());
    return Response.json({ error: "no se pudo crear la preferencia de pago" }, { status: 500 });
  }
  const pref = await resPref.json();

  // 4. Auditoria no critica: guardar id de preferencia y snapshot (requiere las columnas pago_id y datos)
  await fetch(`${env.SUPABASE_URL}/rest/v1/pedidos?id=eq.${pedido.id}`, {
    method: "PATCH",
    headers: { ...headersSb, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ pago_id: pref.id, datos: { items: itemsMP, total } }),
  });

  return Response.json({ init_point: pref.init_point, pedido_id: String(pedido.id) });
}