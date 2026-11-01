// Telas da aplicação. Cada view recebe um contexto (ctx) e pode devolver um
// controlador { groupId, refresh, accepts } para receber atualizações ao vivo.

import { api, session } from "./api.js";
import {
  checkbox, field, formatDate, h, inviteUrl, onSubmit, options, plural, selectField, toast, withBusy,
} from "./dom.js";
import { compressImage } from "./image.js";
import * as shopping from "./shopping.js";

// --------------------------------------------------------------------------- //
// Entrar / criar conta
// --------------------------------------------------------------------------- //
export async function auth(ctx) {
  ctx.setTitle("Lista de Compras");
  let mode = "login";

  const tabLogin = h("button", { type: "button", onclick: () => switchTo("login") }, "Entrar");
  const tabRegister = h("button", { type: "button", onclick: () => switchTo("register") }, "Criar conta");
  const formSlot = h("div");

  ctx.root.replaceChildren(
    h("p", { class: "muted" }, "Listas de compras compartilhadas: quem participa da lista é avisado quando algo novo é adicionado."),
    ctx.hasPendingInvite && h("p", { class: "notice" }, "Entre ou crie uma conta para responder ao convite."),
    h("div", { class: "tabs", role: "group", "aria-label": "Escolha uma opção" }, tabLogin, tabRegister),
    h("section", { class: "card" }, formSlot),
  );

  function switchTo(next) {
    mode = next;
    tabLogin.setAttribute("aria-selected", String(mode === "login"));
    tabLogin.setAttribute("aria-pressed", String(mode === "login"));
    tabRegister.setAttribute("aria-selected", String(mode === "register"));
    tabRegister.setAttribute("aria-pressed", String(mode === "register"));
    formSlot.replaceChildren(mode === "login" ? loginForm() : registerForm());
  }

  function loginForm() {
    return onSubmit(
      h(
        "form",
        { novalidate: true, "aria-label": "Entrar" },
        field({ label: "Usuário", name: "username", autocomplete: "username", autocapitalize: "none", spellcheck: "false", required: true }),
        field({ label: "Senha", name: "password", type: "password", autocomplete: "current-password", required: true }),
        h("button", { class: "btn btn-block", type: "submit" }, "Entrar"),
      ),
      async (data) => ctx.onLogin(await api.login(data)),
    );
  }

  function registerForm() {
    return onSubmit(
      h(
        "form",
        { novalidate: true, "aria-label": "Criar conta" },
        field({ label: "Seu nome", name: "display_name", autocomplete: "name", hint: "Como as pessoas vão ver você.", maxlength: 50, required: true }),
        field({ label: "Usuário", name: "username", autocomplete: "username", autocapitalize: "none", spellcheck: "false", hint: "De 3 a 30 caracteres: letras minúsculas, números, _ ou .", maxlength: 30, required: true }),
        field({ label: "Senha", name: "password", type: "password", autocomplete: "new-password", hint: "Mínimo de 8 caracteres.", minlength: 8, required: true }),
        h("button", { class: "btn btn-block", type: "submit" }, "Criar conta"),
      ),
      async (data) => ctx.onLogin(await api.register(data)),
    );
  }

  switchTo(mode);
}

// --------------------------------------------------------------------------- //
// Início: minhas listas
// --------------------------------------------------------------------------- //
export async function home(ctx) {
  ctx.setTitle("Minhas listas");
  ctx.setActions(h("button", { class: "btn btn-ghost btn-small", type: "button", onclick: ctx.logout }, "Sair"));

  const list = h("div");
  ctx.root.replaceChildren(
    h("p", {}, `Olá, ${session.user?.display_name ?? ""}!`),
    notificationPrompt(),
    h(
      "div",
      { class: "row" },
      h("a", { class: "btn grow", href: "#/nova" }, "+ Nova lista"),
      h("a", { class: "btn btn-secondary grow", href: "#/buscar" }, "Buscar listas"),
    ),
    h("section", { class: "stack", "aria-labelledby": "my-lists" }, h("h2", { id: "my-lists" }, "Suas listas"), list),
  );

  async function refresh() {
    const groups = await api.myGroups();
    list.replaceChildren(
      groups.length
        ? h("ul", { class: "stack" }, groups.map(groupCard))
        : h("p", { class: "empty" }, "Você ainda não participa de nenhuma lista. Crie uma nova ou busque uma lista para entrar."),
    );
  }

  await refresh();
  return { refresh };
}

function groupCard(group) {
  const details = [
    group.pending_items != null && plural(group.pending_items, "item para comprar", "itens para comprar"),
    plural(group.member_count, "pessoa", "pessoas"),
  ].filter(Boolean).join(" · ");

  return h(
    "li",
    { class: "card" },
    h(
      "a",
      { class: "group-link", href: `#/lista/${group.id}` },
      h("strong", {}, group.name),
      h("span", { class: "muted small" }, details),
      group.pending_requests > 0 &&
        h("span", {}, h("span", { class: "badge warn" }, plural(group.pending_requests, "pedido para entrar", "pedidos para entrar"))),
    ),
  );
}

function notificationPrompt() {
  if (!("Notification" in window) || Notification.permission !== "default") return null;
  const box = h(
    "section",
    { class: "card stack", "aria-labelledby": "notif-title" },
    h("h2", { id: "notif-title" }, "Receber avisos"),
    h("p", { class: "muted" }, "Seja avisado quando alguém adicionar itens às suas listas."),
    h(
      "button",
      {
        class: "btn btn-secondary",
        type: "button",
        onclick: async () => {
          const result = await Notification.requestPermission();
          box.remove();
          toast(result === "granted" ? "Avisos ativados." : "Avisos não ativados. Você pode mudar isso nas configurações do navegador.");
        },
      },
      "Ativar avisos",
    ),
  );
  return box;
}

// --------------------------------------------------------------------------- //
// Nova lista
// --------------------------------------------------------------------------- //
export async function newGroup(ctx) {
  ctx.setTitle("Nova lista", "#/");
  ctx.root.replaceChildren(
    h(
      "section",
      { class: "card" },
      onSubmit(
        h(
          "form",
          { novalidate: true, "aria-label": "Criar lista" },
          field({ label: "Nome da lista", name: "name", hint: "Ex.: Casa, Mercado do mês, Churrasco", maxlength: 60, required: true, autocomplete: "off" }),
          field({ label: "Descrição (opcional)", name: "description", type: "textarea", maxlength: 200 }),
          checkbox({
            label: "Aparecer na busca",
            name: "is_public",
            checked: true,
            hint: "Qualquer pessoa pode encontrar e pedir para entrar. Você sempre aprova quem entra.",
          }),
          h("button", { class: "btn btn-block", type: "submit" }, "Criar lista"),
        ),
        async (data) => {
          const group = await api.createGroup({
            name: data.name,
            description: data.description,
            is_public: data.is_public === "on",
          });
          toast("Lista criada! Agora convide as pessoas.");
          ctx.navigate(`#/lista/${group.id}/pessoas`);
        },
      ),
    ),
  );
}

// --------------------------------------------------------------------------- //
// Buscar listas
// --------------------------------------------------------------------------- //
export async function search(ctx) {
  ctx.setTitle("Buscar listas", "#/");
  const status = h("p", { class: "muted", role: "status" });
  const results = h("ul", { class: "stack" });

  const form = onSubmit(
    h(
      "form",
      { role: "search", "aria-label": "Buscar listas" },
      field({ label: "Nome da lista", name: "q", type: "search", minlength: 2, maxlength: 60, autocomplete: "off", enterkeyhint: "search" }),
      h("button", { class: "btn btn-block", type: "submit" }, "Buscar"),
    ),
    async ({ q }) => {
      const groups = await api.searchGroups(q);
      status.textContent = groups.length ? plural(groups.length, "lista encontrada", "listas encontradas") : "Nenhuma lista encontrada.";
      results.replaceChildren(...groups.map((g) => searchResult(g)));
    },
  );

  ctx.root.replaceChildren(
    h("p", { class: "muted" }, "Só aparecem listas que o dono deixou visíveis na busca."),
    form,
    status,
    results,
  );
}

function searchResult(group) {
  const li = h("li", { class: "card stack" });
  const render = (g) =>
    li.replaceChildren(
      h("div", {}, h("h2", {}, g.name), g.description && h("p", { class: "muted" }, g.description)),
      h("p", { class: "small muted" }, plural(g.member_count, "pessoa", "pessoas")),
      joinActions(g, () => api.requestToJoin(g.id), render),
    );
  render(group);
  return li;
}

/** Ações de entrada numa lista, compartilhadas pela busca e pelo convite. */
function joinActions(group, requestFn, rerender) {
  if (group.my_role) {
    return h("a", { class: "btn btn-secondary", href: `#/lista/${group.id}` }, "Abrir lista");
  }
  if (group.has_pending_request) {
    const cancel = h(
      "button",
      {
        class: "btn btn-ghost btn-small",
        type: "button",
        onclick: () =>
          withBusy(cancel, async () => {
            await api.cancelRequest(group.id);
            toast("Pedido cancelado.");
            rerender({ ...group, has_pending_request: false });
          }),
      },
      "Cancelar pedido",
    );
    return h("div", { class: "row" }, h("span", { class: "badge" }, "Pedido enviado — aguardando aprovação"), cancel);
  }
  const join = h(
    "button",
    {
      class: "btn",
      type: "button",
      onclick: () =>
        withBusy(join, async () => {
          const updated = await requestFn();
          toast("Pedido enviado! Você será avisado quando o dono aprovar.");
          rerender(updated);
        }),
    },
    "Pedir para entrar",
  );
  return join;
}

// --------------------------------------------------------------------------- //
// Convite (link compartilhado)
// --------------------------------------------------------------------------- //
export async function invite(ctx, code) {
  ctx.setTitle("Convite", "#/");
  const group = await api.previewInvite(code);
  const card = h("section", { class: "card stack" });

  const render = (g) =>
    card.replaceChildren(
      h("p", { class: "muted" }, "Você foi convidado para a lista"),
      h("h2", {}, g.name),
      g.description && h("p", {}, g.description),
      h("p", { class: "small muted" }, plural(g.member_count, "pessoa participa", "pessoas participam")),
      !g.my_role && !g.has_pending_request && h("p", { class: "small" }, "O dono da lista precisa aprovar sua entrada."),
      joinActions(g, () => api.acceptInvite(code), render),
    );

  render(group);
  ctx.root.replaceChildren(card);
}

// --------------------------------------------------------------------------- //
// Itens da lista: modo "Lista" (montar) e "No mercado" (comprar, funciona offline)
// --------------------------------------------------------------------------- //
const CATEGORIES = [
  ["hortifruti", "Hortifrúti"],
  ["acougue", "Açougue e peixaria"],
  ["frios", "Frios e laticínios"],
  ["padaria", "Padaria"],
  ["mantimentos", "Mantimentos"],
  ["bebidas", "Bebidas"],
  ["congelados", "Congelados"],
  ["limpeza", "Limpeza"],
  ["higiene", "Higiene"],
  ["outros", "Outros"],
];
const UNITS = [
  ["un", "un"],
  ["kg", "kg"],
  ["g", "g"],
  ["l", "L"],
  ["ml", "ml"],
  ["pct", "pacote"],
  ["cx", "caixa"],
  ["dz", "dúzia"],
];
const UNIT_LABEL = Object.fromEntries(UNITS);
const MODE_KEY = "compras.modo.";

function readMode(groupId) {
  try { return localStorage.getItem(MODE_KEY + groupId) === "mercado" ? "mercado" : "lista"; } catch { return "lista"; }
}

function saveMode(groupId, mode) {
  try { localStorage.setItem(MODE_KEY + groupId, mode); } catch { /* sem persistência */ }
}

/** "2 kg · Omo" */
function itemDetails(item) {
  const amount = item.quantity ? `${item.quantity} ${UNIT_LABEL[item.unit] ?? item.unit}` : "";
  return [amount, item.brand].filter(Boolean).join(" · ");
}

function itemBody(data) {
  return {
    name: data.name,
    brand: data.brand ?? "",
    quantity: data.quantity ?? "",
    unit: data.unit || "un",
    category: data.category || "outros",
    note: data.note ?? "",
  };
}

// --- fotos dos itens ---------------------------------------------------------- //
// A foto fica atrás do login: é buscada com o token e exibida por um endereço local (blob:).
const photoCache = new Map(); // id do item -> { version, promise }

function photoUrl(groupId, item) {
  const version = item.image_updated_at;
  const cached = photoCache.get(item.id);
  if (cached?.version === version) return cached.promise;
  cached?.promise.then((url) => URL.revokeObjectURL(url)).catch(() => {});
  const promise = api.itemImage(groupId, item.id).then((blob) => URL.createObjectURL(blob));
  promise.catch(() => {
    if (photoCache.get(item.id)?.promise === promise) photoCache.delete(item.id);
  });
  photoCache.set(item.id, { version, promise });
  return promise;
}

/** Miniatura que abre a foto ampliada. Só aparece depois de carregar (sem internet e sem cache, some). */
function photoThumb(groupId, item) {
  if (!item.has_image) return null;
  const img = h("img", { class: "item-thumb", alt: "", width: 40, height: 40 });
  const button = h(
    "button",
    { class: "thumb", type: "button", hidden: true, "aria-label": `Ver foto de ${item.name}` },
    img,
  );
  photoUrl(groupId, item)
    .then((url) => {
      img.src = url;
      button.hidden = false;
    })
    .catch(() => {});
  button.addEventListener("click", () => showPhoto(groupId, item));
  return button;
}

async function showPhoto(groupId, item) {
  let url;
  try {
    url = await photoUrl(groupId, item);
  } catch (error) {
    toast(error.message, "error");
    return;
  }
  const dialog = h("dialog", { class: "dialog", "aria-label": `Foto de ${item.name}` });
  dialog.append(
    h("img", { class: "photo-full", alt: `Foto de ${item.name}`, src: url }),
    h("button", { class: "btn btn-secondary btn-block", type: "button", onclick: () => dialog.close() }, "Fechar"),
  );
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
}

/** Centavos -> "12,50" (para preencher o campo de preço). */
function plainMoney(cents) {
  return (cents / 100).toFixed(2).replace(".", ",");
}

export async function groupItems(ctx, groupId) {
  const group = await api.group(groupId);
  ctx.setTitle(group.name, "#/");
  ctx.setActions(h("a", { class: "btn btn-ghost btn-small", href: `#/lista/${groupId}/pessoas` }, "Pessoas"));

  let items = [];
  let mode = readMode(groupId);
  let renderDeferred = false;

  const tabList = h("button", { type: "button", onclick: () => setMode("lista") }, "Lista");
  const tabMarket = h("button", { type: "button", onclick: () => setMode("mercado") }, "No mercado");
  const requestsNotice = h("div");
  const syncNotice = h("p", { class: "notice", role: "status", hidden: true });
  const content = h("div");
  const totalBar = h("div", { class: "total-bar", role: "status", "aria-live": "polite" });
  const addForm = buildAddForm();
  const dock = h("div", { class: "dock" });

  ctx.root.classList.add("has-dock");
  ctx.root.replaceChildren(
    h("div", { class: "tabs", role: "group", "aria-label": "Modo da lista" }, tabList, tabMarket),
    requestsNotice,
    syncNotice,
    content,
    dock,
  );

  if (group.join_requests.length) {
    requestsNotice.replaceChildren(
      h(
        "p",
        { class: "notice" },
        `${plural(group.join_requests.length, "pessoa quer", "pessoas querem")} entrar nesta lista. `,
        h("a", { href: `#/lista/${groupId}/pessoas` }, "Ver pedidos"),
      ),
    );
  }

  function setMode(next) {
    mode = next;
    saveMode(groupId, mode);
    render();
  }

  /** Itens do servidor com as marcações deste aparelho que ainda não foram enviadas. */
  const current = () => shopping.applyPending(groupId, items);

  async function refresh() {
    const fresh = await api.items(groupId);
    shopping.prune(groupId, fresh);
    items = fresh;
    render();
  }

  function render() {
    // Redesenhar no meio da digitação de um preço apagaria o que foi digitado.
    if (document.activeElement?.classList.contains("price-input")) {
      renderDeferred = true;
      if (mode === "mercado") updateTotal(current());
      return;
    }
    renderDeferred = false;
    const focusKey = document.activeElement?.dataset?.focusKey;

    for (const [tab, name] of [[tabList, "lista"], [tabMarket, "mercado"]]) {
      tab.setAttribute("aria-pressed", String(mode === name));
      tab.setAttribute("aria-selected", String(mode === name));
    }
    const waiting = shopping.pendingCount(groupId);
    syncNotice.hidden = waiting === 0;
    syncNotice.textContent = waiting
      ? `${plural(waiting, "marcação aguardando", "marcações aguardando")} internet para sincronizar com a lista.`
      : "";

    if (mode === "mercado") renderMarket(current());
    else renderList(current());

    // Mantém o foco no mesmo controle após atualizar (teclado e leitores de tela).
    if (focusKey) content.querySelector(`[data-focus-key="${CSS.escape(focusKey)}"]`)?.focus();
  }

  function renderLater() {
    setTimeout(() => {
      if (renderDeferred) render();
    }, 0);
  }

  // --- marcar como comprado: vale na hora e é enviado quando houver conexão --- //
  function toggle(item, bought) {
    shopping.markBought(groupId, item.id, bought);
    render();
    shopping
      .sync(groupId)
      .then((sent) => (sent ? refresh() : render()))
      .catch(() => render());
  }

  function categorySections(list, rowFn) {
    return CATEGORIES.map(([value, label]) => {
      const inCategory = list.filter((i) => i.category === value);
      if (!inCategory.length) return null;
      const titleId = `cat-${value}`;
      return h(
        "section",
        { class: "category", "aria-labelledby": titleId },
        h("h3", { id: titleId }, label, " ", h("span", { class: "muted small" }, `(${inCategory.length})`)),
        h("ul", { class: "items" }, inCategory.map(rowFn)),
      );
    });
  }

  function checkboxFor(item) {
    const box = h("input", {
      type: "checkbox",
      checked: Boolean(item.bought_at),
      "data-focus-key": `check:${item.id}`,
    });
    box.addEventListener("change", () => toggle(item, box.checked));
    return box;
  }

  // --- modo Lista ------------------------------------------------------------ //
  function renderList(view) {
    const pending = view.filter((i) => !i.bought_at);
    const bought = view.filter((i) => i.bought_at);

    content.replaceChildren(h(
      "div",
      { class: "stack" },
      h(
        "div",
        { class: "section-title" },
        h("h2", {}, "Para comprar"),
        h("span", { class: "muted small" }, plural(pending.length, "item", "itens")),
      ),
      pending.length
        ? categorySections(pending, listRow)
        : h("p", { class: "empty" }, "Nada faltando por aqui. Use o campo abaixo para adicionar."),
      bought.length > 0 && boughtSection(bought),
    ));
    dock.replaceChildren(addForm);
  }

  function boughtSection(bought) {
    const clear = h(
      "button",
      {
        class: "btn btn-ghost btn-small",
        type: "button",
        onclick: () => {
          if (!confirm("Remover todos os itens comprados da lista?")) return;
          withBusy(clear, async () => {
            await shopping.sync(groupId);
            await api.clearBought(groupId);
            toast("Itens comprados removidos.");
            await refresh();
          });
        },
      },
      "Limpar comprados",
    );
    return h(
      "details",
      {},
      h("summary", {}, `Comprados (${bought.length})`),
      h("ul", { class: "items" }, bought.map(listRow)),
      h("div", { class: "row" }, clear),
    );
  }

  function listRow(item) {
    const isBought = Boolean(item.bought_at);
    const details = itemDetails(item);
    const meta = isBought
      ? `Comprado por ${item.bought_by?.display_name ?? "alguém"}`
      : `Adicionado por ${item.added_by.display_name} · ${formatDate(item.created_at)}`;

    const edit = h(
      "button",
      { class: "icon-action", type: "button", "aria-label": `Editar ${item.name}`, "data-focus-key": `edit:${item.id}` },
      h("span", { "aria-hidden": "true" }, "✎"),
    );
    edit.addEventListener("click", () => editItem(item));

    const remove = h(
      "button",
      { class: "icon-action", type: "button", "aria-label": `Remover ${item.name}` },
      h("span", { "aria-hidden": "true" }, "✕"),
    );
    remove.addEventListener("click", () =>
      withBusy(remove, async () => {
        await api.deleteItem(groupId, item.id);
        toast(`${item.name} removido.`);
        await refresh();
      }),
    );

    return h(
      "li",
      { class: `item${isBought ? " bought" : ""}` },
      h(
        "label",
        { class: "check" },
        checkboxFor(item),
        h(
          "span",
          {},
          h("span", { class: "item-name" }, item.name),
          details && h("span", { class: "item-details" }, details),
          item.note && h("span", { class: "item-meta" }, item.note),
          h("span", { class: "item-meta" }, meta),
        ),
      ),
      photoThumb(groupId, item),
      edit,
      remove,
    );
  }

  function buildAddForm() {
    const vh = (forId, text) => h("label", { class: "visually-hidden", for: forId }, text);
    const nameInput = h("input", {
      id: "new-item", name: "name", type: "text", required: true, maxlength: 80,
      autocomplete: "off", enterkeyhint: "send", placeholder: "Ex.: café",
    });
    const category = h("select", { id: "new-category", name: "category" }, options(CATEGORIES, "outros"));

    const form = onSubmit(
      h(
        "form",
        { "aria-label": "Adicionar item" },
        h(
          "div",
          { class: "row" },
          vh("new-item", "Item para adicionar"),
          h("div", { class: "grow" }, nameInput),
          vh("new-qty", "Quantidade (opcional)"),
          h("input", {
            id: "new-qty", name: "quantity", type: "text", class: "qty", inputmode: "decimal",
            maxlength: 30, autocomplete: "off", placeholder: "Qtd.",
          }),
          vh("new-unit", "Medida"),
          h("select", { id: "new-unit", name: "unit", class: "unit" }, options(UNITS, "un")),
        ),
        h(
          "div",
          { class: "row" },
          vh("new-category", "Categoria"),
          h("div", { class: "grow" }, category),
          vh("new-brand", "Marca (opcional)"),
          h(
            "div",
            { class: "grow" },
            h("input", {
              id: "new-brand", name: "brand", type: "text", maxlength: 40,
              autocomplete: "off", placeholder: "Marca",
            }),
          ),
          h("button", { class: "btn", type: "submit" }, "Adicionar"),
        ),
      ),
      async (data) => {
        const item = await api.addItem(groupId, itemBody(data));
        form.reset();
        category.value = data.category; // quem adiciona vários itens da mesma seção não precisa trocar
        nameInput.focus();
        toast(`${item.name} adicionado.`);
        await refresh();
      },
    );
    return form;
  }

  function editItem(item) {
    const dialog = h("dialog", { class: "dialog", "aria-labelledby": "edit-title" });

    // Foto (opcional): só é enviada ao salvar, depois que os dados do item foram gravados.
    let newPhoto = null; // foto escolhida agora, já reduzida
    let previewUrl = null;
    let dropPhoto = false;
    const photoField = field({
      label: "Foto (opcional)", name: "photo", type: "file", accept: "image/*",
      hint: "Escolha da galeria ou tire uma foto agora.",
    });
    const photoInput = photoField.querySelector("input");
    const photoPreview = h("div", { class: "photo-preview" });
    const removePhoto = h("button", { class: "btn btn-ghost btn-small", type: "button", hidden: true }, "Remover foto");

    function showPreview() {
      photoPreview.replaceChildren();
      removePhoto.hidden = true;
      const show = (url) => {
        photoPreview.replaceChildren(h("img", { class: "photo-preview-img", alt: `Foto de ${item.name}`, src: url }));
        removePhoto.hidden = false;
      };
      if (newPhoto) show(previewUrl);
      else if (item.has_image && !dropPhoto) photoUrl(groupId, item).then(show).catch(() => {});
    }

    photoInput.addEventListener("change", async () => {
      const file = photoInput.files[0];
      if (!file) return;
      photoInput.disabled = true;
      try {
        newPhoto = await compressImage(file);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(newPhoto);
        dropPhoto = false;
        showPreview();
      } catch (error) {
        toast(error.message, "error");
      } finally {
        photoInput.value = "";
        photoInput.disabled = false;
      }
    });
    removePhoto.addEventListener("click", () => {
      if (newPhoto) {
        newPhoto = null;
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      } else {
        dropPhoto = true;
      }
      showPreview();
    });
    showPreview();

    const form = onSubmit(
      h(
        "form",
        { novalidate: true },
        h("h2", { id: "edit-title" }, "Editar item"),
        field({ label: "Item", name: "name", value: item.name, maxlength: 80, required: true, autocomplete: "off" }),
        field({ label: "Marca (opcional)", name: "brand", value: item.brand, maxlength: 40, autocomplete: "off" }),
        h(
          "div",
          { class: "row" },
          h("div", { class: "grow" }, field({ label: "Quantidade", name: "quantity", value: item.quantity, maxlength: 30, inputmode: "decimal", autocomplete: "off" })),
          h("div", { class: "grow" }, selectField({ label: "Medida", name: "unit", choices: UNITS, value: item.unit })),
        ),
        selectField({ label: "Categoria", name: "category", choices: CATEGORIES, value: item.category }),
        field({ label: "Observação (opcional)", name: "note", type: "textarea", value: item.note, maxlength: 140 }),
        photoField,
        photoPreview,
        h("div", { class: "row" }, removePhoto),
        h(
          "div",
          { class: "row" },
          h("button", { class: "btn btn-ghost", type: "button", onclick: () => dialog.close() }, "Cancelar"),
          h("button", { class: "btn grow", type: "submit" }, "Salvar"),
        ),
      ),
      async (data) => {
        await api.updateItem(groupId, item.id, itemBody(data));
        let photoError = null;
        try {
          if (newPhoto) await api.putItemImage(groupId, item.id, newPhoto);
          else if (dropPhoto && item.has_image) await api.deleteItemImage(groupId, item.id);
        } catch (error) {
          photoError = error;
        }
        dialog.close();
        if (photoError) toast(`Item salvo, mas a foto não foi enviada: ${photoError.message}`, "error");
        else toast("Item atualizado.");
        await refresh();
      },
    );
    dialog.append(form);
    dialog.addEventListener("close", () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      dialog.remove();
      content.querySelector(`[data-focus-key="edit:${CSS.escape(item.id)}"]`)?.focus();
    });
    document.body.append(dialog);
    dialog.showModal();
  }

  // --- modo No mercado (preços ficam no aparelho; funciona sem internet) ------ //
  function renderMarket(view) {
    // Em cada seção, o que falta pegar vem primeiro.
    const sorted = [...view].sort((a, b) => Boolean(a.bought_at) - Boolean(b.bought_at));
    content.replaceChildren(h(
      "div",
      { class: "stack" },
      h("p", { class: "muted small" }, "Marque o que pegou e anote o preço. Funciona sem internet; os preços ficam só neste aparelho."),
      view.length
        ? categorySections(sorted, marketRow)
        : h("p", { class: "empty" }, "A lista está vazia. Volte para “Lista” para adicionar itens."),
    ));
    updateTotal(view);
    dock.replaceChildren(totalBar);
  }

  function updateTotal(view) {
    const saved = shopping.prices(groupId);
    const bought = view.filter((i) => i.bought_at);
    const withoutPrice = bought.filter((i) => saved[i.id] == null).length;
    totalBar.replaceChildren(
      h(
        "div",
        { class: "total-line" },
        h("span", {}, `${bought.length} de ${plural(view.length, "item", "itens")} no carrinho`),
        h("strong", { class: "total" }, shopping.formatMoney(shopping.total(groupId, view))),
      ),
      withoutPrice > 0 &&
        h("span", { class: "muted small" }, plural(withoutPrice, "item comprado ainda sem preço", "itens comprados ainda sem preço")),
    );
  }

  /** Câmera direto no mercado: tira a foto, reduz e envia (precisa de internet). */
  function cameraButton(item) {
    const input = h("input", { type: "file", accept: "image/*", capture: "environment", hidden: true, tabindex: "-1" });
    const button = h(
      "button",
      {
        class: "icon-action",
        type: "button",
        "aria-label": `${item.has_image ? "Trocar a foto de" : "Tirar foto de"} ${item.name}`,
      },
      h("span", { "aria-hidden": "true" }, "📷"),
    );
    button.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      withBusy(button, async () => {
        await api.putItemImage(groupId, item.id, await compressImage(file));
        toast("Foto salva.");
        await refresh();
      });
    });
    return h("span", {}, button, input);
  }

  function marketRow(item) {
    const isBought = Boolean(item.bought_at);
    const saved = shopping.prices(groupId)[item.id];
    const details = itemDetails(item);

    const price = h("input", {
      type: "text",
      class: "price-input",
      inputmode: "decimal",
      autocomplete: "off",
      enterkeyhint: "done",
      placeholder: "0,00",
      value: saved != null ? plainMoney(saved) : null,
      "aria-label": `Preço pago por ${item.name}`,
      "data-focus-key": `price:${item.id}`,
    });
    price.addEventListener("change", () => {
      const raw = price.value.trim();
      const cents = shopping.parseMoney(raw);
      if (raw && cents == null) {
        price.setAttribute("aria-invalid", "true");
        toast("Valor inválido. Use, por exemplo, 12,50.", "error");
        return;
      }
      price.removeAttribute("aria-invalid");
      if (cents != null) price.value = plainMoney(cents);
      shopping.setPrice(groupId, item.id, cents);
      // Anotar o preço já coloca o item no carrinho.
      if (cents != null && !isBought) toggle(item, true);
      else updateTotal(current());
    });
    price.addEventListener("keydown", (event) => {
      if (event.key === "Enter") price.blur();
    });
    price.addEventListener("blur", renderLater);

    return h(
      "li",
      { class: `item market${isBought ? " bought" : ""}` },
      h(
        "label",
        { class: "check" },
        checkboxFor(item),
        h(
          "span",
          {},
          h("span", { class: "item-name" }, item.name),
          details && h("span", { class: "item-details" }, details),
          item.note && h("span", { class: "item-meta" }, item.note),
        ),
      ),
      photoThumb(groupId, item),
      cameraButton(item),
      h("span", { class: "price" }, h("span", { "aria-hidden": "true" }, "R$"), price),
    );
  }

  await refresh();
  if (shopping.pendingCount(groupId)) shopping.sync(groupId).then((sent) => sent && refresh()).catch(() => {});
  return { groupId, refresh, accepts: (n) => n.type === "item_added" || n.type === "items_changed" };
}

// --------------------------------------------------------------------------- //
// Pessoas, convite e configurações da lista
// --------------------------------------------------------------------------- //
export async function groupPeople(ctx, groupId) {
  let group = await api.group(groupId);
  ctx.setTitle("Pessoas e convite", `#/lista/${groupId}`);

  function render() {
    const isOwner = group.my_role === "owner";
    ctx.root.replaceChildren(
      inviteSection(group, isOwner, async () => {
        group = await api.regenerateInvite(groupId);
        render();
        toast("Novo link gerado. O link antigo não funciona mais.");
      }),
      isOwner && requestsSection(),
      membersSection(isOwner),
      isOwner && settingsSection(),
      dangerSection(isOwner),
    );
  }

  function requestsSection() {
    const requests = group.join_requests;
    return h(
      "section",
      { class: "card stack", "aria-labelledby": "requests-title" },
      h("h2", { id: "requests-title" }, `Pedidos para entrar (${requests.length})`),
      requests.length
        ? h(
            "ul",
            { class: "stack" },
            requests.map((r) => {
              const approve = h("button", { class: "btn btn-small", type: "button", "aria-label": `Aceitar ${r.user.display_name}` }, "Aceitar");
              const reject = h("button", { class: "btn btn-danger btn-small", type: "button", "aria-label": `Recusar ${r.user.display_name}` }, "Recusar");
              approve.addEventListener("click", () =>
                withBusy(approve, async () => {
                  group = await api.approveRequest(groupId, r.user.id);
                  toast(`${r.user.display_name} agora participa da lista.`);
                  render();
                }),
              );
              reject.addEventListener("click", () =>
                withBusy(reject, async () => {
                  group = await api.rejectRequest(groupId, r.user.id);
                  toast("Pedido recusado.");
                  render();
                }),
              );
              return h(
                "li",
                { class: "row" },
                h(
                  "div",
                  { class: "grow" },
                  h("strong", {}, r.user.display_name),
                  h("span", { class: "item-meta" }, `@${r.user.username} · ${r.via_invite ? "pelo link de convite" : "pela busca"}`),
                ),
                approve,
                reject,
              );
            }),
          )
        : h("p", { class: "muted" }, "Nenhum pedido no momento."),
    );
  }

  function membersSection(isOwner) {
    return h(
      "section",
      { class: "card stack", "aria-labelledby": "members-title" },
      h("h2", { id: "members-title" }, `Pessoas na lista (${group.members.length})`),
      h(
        "ul",
        { class: "stack" },
        group.members.map((m) => {
          let action = null;
          if (m.role === "owner") {
            action = h("span", { class: "badge" }, "Dono");
          } else if (isOwner) {
            action = h("button", { class: "btn btn-ghost btn-small", type: "button", "aria-label": `Remover ${m.user.display_name}` }, "Remover");
            action.addEventListener("click", () => {
              if (!confirm(`Remover ${m.user.display_name} da lista?`)) return;
              withBusy(action, async () => {
                group = await api.removeMember(groupId, m.user.id);
                toast(`${m.user.display_name} foi removido.`);
                render();
              });
            });
          }
          return h(
            "li",
            { class: "row" },
            h("div", { class: "grow" }, h("strong", {}, m.user.display_name), h("span", { class: "item-meta" }, `@${m.user.username}`)),
            action,
          );
        }),
      ),
    );
  }

  function settingsSection() {
    return h(
      "section",
      { class: "card stack", "aria-labelledby": "settings-title" },
      h("h2", { id: "settings-title" }, "Configurações"),
      onSubmit(
        h(
          "form",
          { novalidate: true, "aria-labelledby": "settings-title" },
          field({ label: "Nome da lista", name: "name", value: group.name, maxlength: 60, required: true, autocomplete: "off" }),
          field({ label: "Descrição (opcional)", name: "description", type: "textarea", value: group.description, maxlength: 200 }),
          checkbox({
            label: "Aparecer na busca",
            name: "is_public",
            checked: group.is_public,
            hint: "Desmarcado: só entra quem receber o link de convite.",
          }),
          h("button", { class: "btn btn-secondary", type: "submit" }, "Salvar alterações"),
        ),
        async (data) => {
          group = await api.updateGroup(groupId, {
            name: data.name,
            description: data.description,
            is_public: data.is_public === "on",
          });
          toast("Alterações salvas.");
          ctx.setTitle("Pessoas e convite", `#/lista/${groupId}`);
        },
      ),
    );
  }

  function dangerSection(isOwner) {
    const button = h(
      "button",
      { class: "btn btn-danger btn-block", type: "button" },
      isOwner ? "Excluir lista" : "Sair da lista",
    );
    button.addEventListener("click", () => {
      const question = isOwner
        ? `Excluir a lista “${group.name}” e todos os itens? Isso não pode ser desfeito.`
        : `Sair da lista “${group.name}”?`;
      if (!confirm(question)) return;
      withBusy(button, async () => {
        await (isOwner ? api.deleteGroup(groupId) : api.leaveGroup(groupId));
        toast(isOwner ? "Lista excluída." : "Você saiu da lista.");
        ctx.navigate("#/");
      });
    });
    return h("section", { "aria-label": "Zona de perigo" }, button);
  }

  render();
  return {
    groupId,
    accepts: (n) => n.type === "join_request" || n.type === "member_joined",
    refresh: async () => {
      group = await api.group(groupId);
      render();
    },
  };
}

function inviteSection(group, isOwner, onRegenerate) {
  const url = inviteUrl(group.invite_code);
  const message = `Entre na minha lista de compras “${group.name}”: ${url}`;

  const linkField = field({ label: "Link de convite", name: "invite", type: "url", value: url, readonly: true });
  linkField.querySelector("input").addEventListener("focus", (e) => e.target.select());

  const copy = h("button", { class: "btn btn-secondary btn-small", type: "button" }, "Copiar link");
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copiado. Cole no WhatsApp, Instagram ou onde quiser.");
    } catch {
      linkField.querySelector("input").select();
      toast("Não foi possível copiar automaticamente. Selecione o link e copie.", "error");
    }
  });

  const share = navigator.share
    ? h("button", { class: "btn btn-small", type: "button" }, "Compartilhar")
    : null;
  share?.addEventListener("click", () =>
    navigator.share({ title: group.name, text: `Entre na minha lista de compras “${group.name}”`, url }).catch(() => {}),
  );

  const whatsapp = h(
    "a",
    {
      class: "btn btn-secondary btn-small",
      href: `https://wa.me/?text=${encodeURIComponent(message)}`,
      target: "_blank",
      rel: "noopener noreferrer",
    },
    "WhatsApp",
  );

  const regenerate = isOwner
    ? h("button", { class: "btn btn-ghost btn-small", type: "button" }, "Gerar novo link")
    : null;
  regenerate?.addEventListener("click", () => {
    if (!confirm("Gerar um novo link? O link atual deixará de funcionar.")) return;
    withBusy(regenerate, onRegenerate);
  });

  return h(
    "section",
    { class: "card stack", "aria-labelledby": "invite-title" },
    h("h2", { id: "invite-title" }, "Convidar pessoas"),
    h(
      "p",
      { class: "muted" },
      isOwner
        ? "Envie o link. Quem abrir poderá pedir para entrar, e você decide se aceita."
        : "Envie o link. Quem abrir poderá pedir para entrar, e o dono da lista decide se aceita.",
    ),
    linkField,
    h("div", { class: "row" }, share, whatsapp, copy),
    regenerate,
  );
}
