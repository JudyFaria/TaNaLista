// Ponto de entrada do frontend: rotas, sessão e notificações em tempo real.

import { api, onUnauthorized, session } from "./api.js";
import { h, toast } from "./dom.js";
import * as views from "./views.js";

const APP_NAME = "Lista de Compras";
const PENDING_ROUTE_KEY = "compras.pendingRoute";

const main = document.getElementById("main");
const titleEl = document.getElementById("page-title");
const backEl = document.getElementById("back");
const actionsEl = document.getElementById("topbar-actions");

// [padrão da rota, view, rota pública?]
const ROUTES = [
  [/^#\/entrar$/, views.auth, true],
  [/^#\/convite\/([\w-]+)$/, views.invite, false],
  [/^#\/nova$/, views.newGroup, false],
  [/^#\/buscar$/, views.search, false],
  [/^#\/lista\/(\w+)\/pessoas$/, views.groupPeople, false],
  [/^#\/lista\/(\w+)$/, views.groupItems, false],
  [/^#\/?$/, views.home, false],
];

let renderId = 0;
let controller = null; // view atual, para atualizações ao vivo

function navigate(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

function login(result) {
  session.save(result);
  events.start();
  navigate(takePendingRoute() || "#/");
}

function logout() {
  session.clear();
  events.stop();
  navigate("#/entrar");
}

async function render() {
  const id = ++renderId;
  const hash = location.hash || "#/";
  const route = ROUTES.map(([pattern, view, isPublic]) => [hash.match(pattern), view, isPublic]).find(([m]) => m);
  if (!route) return navigate("#/");

  const [match, view, isPublic] = route;
  if (!isPublic && !session.token) {
    savePendingRoute(hash);
    return navigate("#/entrar");
  }
  if (isPublic && session.token) return navigate("#/");

  // Cada renderização ganha seu próprio contêiner: respostas atrasadas de uma
  // tela antiga não sobrescrevem a tela atual.
  const root = h("div", { class: "view" }, h("p", { class: "muted center" }, "Carregando…"));
  const isCurrent = () => id === renderId;
  const ctx = {
    root,
    navigate,
    onLogin: login,
    logout,
    hasPendingInvite: Boolean(readPendingRoute()?.startsWith("#/convite/")),
    setTitle(text, backHref = null) {
      if (!isCurrent()) return;
      titleEl.textContent = text;
      document.title = text === APP_NAME ? APP_NAME : `${text} · ${APP_NAME}`;
      backEl.hidden = !backHref;
      if (backHref) backEl.href = backHref;
    },
    setActions(...nodes) {
      if (isCurrent()) actionsEl.replaceChildren(...nodes.filter(Boolean));
    },
  };

  controller = null;
  actionsEl.replaceChildren();
  main.replaceChildren(root);

  try {
    const result = await view(ctx, ...match.slice(1));
    if (isCurrent()) controller = result ?? null;
  } catch (error) {
    if (!isCurrent() || error.status === 401) return;
    root.replaceChildren(
      h("p", { class: "empty", role: "alert" }, error.message),
      h("a", { class: "btn btn-secondary", href: "#/" }, "Voltar ao início"),
    );
  }

  if (isCurrent()) {
    window.scrollTo(0, 0);
    titleEl.focus({ preventScroll: true }); // anuncia a nova tela para leitores de tela
  }
}

// --------------------------------------------------------------------------- //
// Notificações em tempo real (Server-Sent Events)
// --------------------------------------------------------------------------- //
const events = {
  source: null,
  retryTimer: null,

  start() {
    this.stop();
    if (!session.token || !("EventSource" in window)) return;
    const source = new EventSource(`/api/events?token=${encodeURIComponent(session.token)}`);
    source.addEventListener("notification", (event) => handleNotification(JSON.parse(event.data)));
    source.addEventListener("error", () => {
      // Reconexões simples o próprio EventSource faz; aqui tratamos queda definitiva.
      if (source.readyState === EventSource.CLOSED) {
        this.retryTimer = setTimeout(() => api.me().then(() => this.start()).catch(() => {}), 10_000);
      }
    });
    this.source = source;
  },

  stop() {
    clearTimeout(this.retryTimer);
    this.source?.close();
    this.source = null;
  },
};

function handleNotification(notification) {
  const { type, body, group_id: groupId } = notification;
  const target = groupId
    ? type === "join_request" ? `#/lista/${groupId}/pessoas` : `#/lista/${groupId}`
    : "#/";

  if (body) {
    if (document.visibilityState === "hidden") showSystemNotification(notification, target);
    else toast(body);
  }

  const lostAccess = type === "group_deleted" || type === "member_removed";
  if (lostAccess && controller?.groupId === groupId) return navigate("#/");

  const interested = controller?.refresh &&
    (!controller.groupId || (controller.groupId === groupId && (controller.accepts?.(notification) ?? true)));
  if (interested) controller.refresh().catch(() => {});
}

async function showSystemNotification(notification, target) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const options = {
    body: notification.body,
    icon: "/icon.svg",
    tag: `${notification.type}:${notification.group_id ?? ""}`,
    data: { url: `/${target}` },
  };
  try {
    const registration = await navigator.serviceWorker?.ready;
    if (registration) return await registration.showNotification(notification.title, options);
    new Notification(notification.title, options);
  } catch {
    toast(notification.body);
  }
}

// --------------------------------------------------------------------------- //
// Rota pendente (ex.: abriu um convite antes de fazer login)
// --------------------------------------------------------------------------- //
function savePendingRoute(hash) {
  try { sessionStorage.setItem(PENDING_ROUTE_KEY, hash); } catch { /* ignora */ }
}

function readPendingRoute() {
  try { return sessionStorage.getItem(PENDING_ROUTE_KEY); } catch { return null; }
}

function takePendingRoute() {
  const hash = readPendingRoute();
  try { sessionStorage.removeItem(PENDING_ROUTE_KEY); } catch { /* ignora */ }
  return hash;
}

// --------------------------------------------------------------------------- //
// Inicialização
// --------------------------------------------------------------------------- //
onUnauthorized(() => {
  savePendingRoute(location.hash);
  session.clear();
  events.stop();
  toast("Sua sessão expirou. Entre novamente.", "error");
  navigate("#/entrar");
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

window.addEventListener("hashchange", render);
events.start();
render();
