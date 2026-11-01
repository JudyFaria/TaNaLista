// Cliente HTTP da API e sessão do usuário.

const TOKEN_KEY = "compras.token";
const USER_KEY = "compras.user";
const API_CACHE = "compras-api"; // mesmo nome usado no sw.js

// localStorage pode falhar (modo privado, bloqueio do navegador).
const storage = {
  get(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* sem persistência */ }
  },
  remove(key) {
    try { localStorage.removeItem(key); } catch { /* ignora */ }
  },
};

let memoryToken = storage.get(TOKEN_KEY);
let memoryUser = parseJson(storage.get(USER_KEY));

export const session = {
  get token() { return memoryToken; },
  get user() { return memoryUser; },
  save({ access_token, user }) {
    if (memoryUser?.id !== user.id) clearApiCache();
    memoryToken = access_token;
    memoryUser = user;
    storage.set(TOKEN_KEY, access_token);
    storage.set(USER_KEY, JSON.stringify(user));
  },
  clear() {
    memoryToken = null;
    memoryUser = null;
    storage.remove(TOKEN_KEY);
    storage.remove(USER_KEY);
    clearApiCache();
  },
};

// As listas salvas para uso offline são de um usuário só: some ao sair da conta.
function clearApiCache() {
  try { globalThis.caches?.delete(API_CACHE).catch(() => {}); } catch { /* ignora */ }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

let unauthorizedHandler = () => {};
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

let offlineHandler = () => {};
export function onOfflineData(handler) {
  offlineHandler = handler;
}

// ``binary``: o corpo é um Blob enviado como está (foto). ``blob``: a resposta é um arquivo.
async function request(method, path, body, { binary = false, blob = false } = {}) {
  const headers = { Accept: blob ? "*/*" : "application/json" };
  if (body !== undefined) headers["Content-Type"] = binary ? body.type : "application/json";
  if (session.token) headers.Authorization = `Bearer ${session.token}`;

  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : binary ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Sem conexão. Verifique sua internet e tente de novo.", 0);
  }

  if (response.headers.get("X-From-Cache")) offlineHandler();
  if (response.status === 204) return null;
  if (blob && response.ok) return response.blob();
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && session.token) unauthorizedHandler();
    throw new ApiError(data?.detail || "Algo deu errado. Tente novamente.", response.status);
  }
  return data;
}

const e = encodeURIComponent;

export const api = {
  register: (body) => request("POST", "/auth/register", body),
  login: (body) => request("POST", "/auth/login", body),
  me: () => request("GET", "/auth/me"),

  myGroups: () => request("GET", "/groups"),
  createGroup: (body) => request("POST", "/groups", body),
  searchGroups: (query) => request("GET", `/groups/search?q=${e(query)}`),
  group: (id) => request("GET", `/groups/${e(id)}`),
  updateGroup: (id, body) => request("PUT", `/groups/${e(id)}`, body),
  deleteGroup: (id) => request("DELETE", `/groups/${e(id)}`),
  regenerateInvite: (id) => request("POST", `/groups/${e(id)}/invite-code`),
  leaveGroup: (id) => request("POST", `/groups/${e(id)}/leave`),
  removeMember: (id, userId) => request("DELETE", `/groups/${e(id)}/members/${e(userId)}`),

  requestToJoin: (id) => request("POST", `/groups/${e(id)}/join-requests`),
  cancelRequest: (id) => request("DELETE", `/groups/${e(id)}/join-requests/me`),
  approveRequest: (id, userId) => request("POST", `/groups/${e(id)}/join-requests/${e(userId)}/approve`),
  rejectRequest: (id, userId) => request("POST", `/groups/${e(id)}/join-requests/${e(userId)}/reject`),

  previewInvite: (code) => request("GET", `/invites/${e(code)}`),
  acceptInvite: (code) => request("POST", `/invites/${e(code)}`),

  items: (id) => request("GET", `/groups/${e(id)}/items`),
  addItem: (id, body) => request("POST", `/groups/${e(id)}/items`, body),
  updateItem: (id, itemId, body) => request("PUT", `/groups/${e(id)}/items/${e(itemId)}`, body),
  setBought: (id, itemId, bought) => request("PATCH", `/groups/${e(id)}/items/${e(itemId)}`, { bought }),
  deleteItem: (id, itemId) => request("DELETE", `/groups/${e(id)}/items/${e(itemId)}`),
  clearBought: (id) => request("DELETE", `/groups/${e(id)}/items/bought`),
  itemImage: (id, itemId) => request("GET", `/groups/${e(id)}/items/${e(itemId)}/image`, undefined, { blob: true }),
  putItemImage: (id, itemId, blob) =>
    request("PUT", `/groups/${e(id)}/items/${e(itemId)}/image`, blob, { binary: true }),
  deleteItemImage: (id, itemId) => request("DELETE", `/groups/${e(id)}/items/${e(itemId)}/image`),
};

function parseJson(raw) {
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}
