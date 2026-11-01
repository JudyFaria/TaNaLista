// Compras no mercado: funciona sem internet, guardando tudo no aparelho.
//
// - Preços pagos ficam só neste aparelho (não vão para o servidor).
// - Marcar como comprado vale na hora na tela e entra numa fila; a fila é
//   enviada ao servidor assim que houver conexão.

import { api, session } from "./api.js";

const PREFIX = "compras.mercado.";

function keyFor(groupId) {
  return `${PREFIX}${session.user?.id}.${groupId}`;
}

function load(groupId) {
  try {
    const data = JSON.parse(localStorage.getItem(keyFor(groupId)));
    if (data?.prices && data?.pending) return data;
  } catch { /* sem dados salvos */ }
  return { prices: {}, pending: {} };
}

function save(groupId, data) {
  try { localStorage.setItem(keyFor(groupId), JSON.stringify(data)); } catch { /* sem persistência */ }
}

// --------------------------------------------------------------------------- //
// Preços (em centavos)
// --------------------------------------------------------------------------- //
export function prices(groupId) {
  return load(groupId).prices;
}

export function setPrice(groupId, itemId, cents) {
  const data = load(groupId);
  if (cents == null) delete data.prices[itemId];
  else data.prices[itemId] = cents;
  save(groupId, data);
}

/** Soma os preços dos itens comprados. */
export function total(groupId, items) {
  const saved = prices(groupId);
  return items.reduce((sum, item) => sum + (item.bought_at ? saved[item.id] ?? 0 : 0), 0);
}

/** Esquece preços e marcações de itens que não existem mais na lista. */
export function prune(groupId, items) {
  const ids = new Set(items.map((i) => i.id));
  const data = load(groupId);
  for (const bucket of [data.prices, data.pending]) {
    for (const id of Object.keys(bucket)) if (!ids.has(id)) delete bucket[id];
  }
  save(groupId, data);
}

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export function formatMoney(cents) {
  return money.format(cents / 100);
}

/** Aceita "12,50", "12.50", "1.234,56" e "R$ 3". Devolve centavos ou null. */
export function parseMoney(text) {
  let value = String(text ?? "").replace(/[R$\s]/g, "");
  if (!value) return null;
  if (value.includes(",")) value = value.replace(/\./g, "").replace(",", ".");
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? Math.round(number * 100) : null;
}

// --------------------------------------------------------------------------- //
// Marcações de comprado (fila para quando estiver sem internet)
// --------------------------------------------------------------------------- //
export function markBought(groupId, itemId, bought) {
  const data = load(groupId);
  data.pending[itemId] = bought;
  save(groupId, data);
}

export function pendingCount(groupId) {
  return Object.keys(load(groupId).pending).length;
}

/** Aplica as marcações ainda não enviadas sobre os itens vindos do servidor. */
export function applyPending(groupId, items) {
  const { pending } = load(groupId);
  return items.map((item) => {
    if (!(item.id in pending) || Boolean(item.bought_at) === pending[item.id]) return item;
    return pending[item.id]
      ? { ...item, bought_at: new Date().toISOString(), bought_by: session.user }
      : { ...item, bought_at: null, bought_by: null };
  });
}

const syncing = new Map();

/** Envia a fila de uma lista. Devolve true se tudo foi enviado. */
export function sync(groupId) {
  if (!syncing.has(groupId)) {
    syncing.set(groupId, flush(groupId).finally(() => syncing.delete(groupId)));
  }
  return syncing.get(groupId);
}

async function flush(groupId) {
  for (const [itemId, bought] of Object.entries(load(groupId).pending)) {
    try {
      await api.setBought(groupId, itemId, bought);
    } catch (error) {
      // Sem conexão, servidor acordando ou sessão expirada: tenta de novo depois.
      if (error.status === 0 || error.status === 401 || error.status >= 500) return false;
      // Item ou lista removidos por outra pessoa: descarta a marcação.
    }
    const data = load(groupId);
    if (data.pending[itemId] === bought) delete data.pending[itemId];
    save(groupId, data);
  }
  return true;
}

/** Envia as filas de todas as listas deste usuário (ao abrir o app ou voltar a conexão). */
export async function syncAll() {
  const prefix = `${PREFIX}${session.user?.id}.`;
  let groupIds = [];
  try {
    groupIds = Object.keys(localStorage)
      .filter((key) => key.startsWith(prefix))
      .map((key) => key.slice(prefix.length));
  } catch { /* sem armazenamento */ }
  const pending = groupIds.filter((id) => pendingCount(id) > 0);
  await Promise.all(pending.map(sync));
  return pending;
}
