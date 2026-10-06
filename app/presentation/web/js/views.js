// Telas da aplicação. Cada view recebe um contexto (ctx) e pode devolver um
// controlador { groupId, refresh, accepts } para receber atualizações ao vivo.

import { api, session } from "./api.js";
import { checkbox, field, formatDate, h, inviteUrl, onSubmit, plural, toast, withBusy } from "./dom.js";

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
// Itens da lista
// --------------------------------------------------------------------------- //
export async function groupItems(ctx, groupId) {
  const group = await api.group(groupId);
  ctx.setTitle(group.name, "#/");
  ctx.setActions(h("a", { class: "btn btn-ghost btn-small", href: `#/lista/${groupId}/pessoas` }, "Pessoas"));

  const requestsNotice = h("div");
  const pendingSection = h("section", { "aria-labelledby": "pending-title" });
  const boughtSection = h("section");

  const nameInput = h("input", {
    id: "new-item", name: "name", type: "text", required: true, maxlength: 80,
    autocomplete: "off", enterkeyhint: "send", placeholder: "Ex.: café",
  });
  const addForm = onSubmit(
    h(
      "form",
      { "aria-label": "Adicionar item" },
      h(
        "div",
        { class: "row" },
        h("label", { class: "visually-hidden", for: "new-item" }, "Item para adicionar"),
        h("div", { class: "grow" }, nameInput),
        h("label", { class: "visually-hidden", for: "new-qty" }, "Quantidade (opcional)"),
        h("input", { id: "new-qty", name: "quantity", type: "text", class: "qty", maxlength: 30, autocomplete: "off", placeholder: "Qtd." }),
        h("button", { class: "btn", type: "submit" }, "Adicionar"),
      ),
    ),
    async (data) => {
      const item = await api.addItem(groupId, { name: data.name, quantity: data.quantity });
      addForm.reset();
      nameInput.focus();
      toast(`${item.name} adicionado.`);
      await refresh();
    },
  );

  ctx.root.classList.add("has-dock");
  ctx.root.replaceChildren(
    requestsNotice,
    pendingSection,
    boughtSection,
    h("div", { class: "dock" }, addForm),
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

  async function refresh() {
    const items = await api.items(groupId);
    const pending = items.filter((i) => !i.bought_at);
    const bought = items.filter((i) => i.bought_at);
    const focusedId = document.activeElement?.dataset?.itemId;

    pendingSection.replaceChildren(
      h(
        "div",
        { class: "section-title" },
        h("h2", { id: "pending-title" }, "Para comprar"),
        h("span", { class: "muted small" }, plural(pending.length, "item", "itens")),
      ),
      pending.length
        ? h("ul", { class: "items" }, pending.map(itemRow))
        : h("p", { class: "empty" }, "Nada faltando por aqui. Use o campo abaixo para adicionar."),
    );

    if (bought.length) {
      const clear = h(
        "button",
        {
          class: "btn btn-ghost btn-small",
          type: "button",
          onclick: () => {
            if (!confirm("Remover todos os itens comprados da lista?")) return;
            withBusy(clear, async () => {
              await api.clearBought(groupId);
              toast("Itens comprados removidos.");
              await refresh();
            });
          },
        },
        "Limpar comprados",
      );
      boughtSection.replaceChildren(
        h(
          "details",
          {},
          h("summary", {}, `Comprados (${bought.length})`),
          h("ul", { class: "items" }, bought.map(itemRow)),
          h("div", { class: "row" }, clear),
        ),
      );
    } else {
      boughtSection.replaceChildren();
    }

    // Mantém o foco no mesmo item após atualizar (teclado e leitores de tela).
    if (focusedId) document.querySelector(`[data-item-id="${CSS.escape(focusedId)}"]`)?.focus();
  }

  function itemRow(item) {
    const isBought = Boolean(item.bought_at);
    const meta = isBought
      ? `Comprado por ${item.bought_by?.display_name ?? "alguém"}`
      : `Adicionado por ${item.added_by.display_name} · ${formatDate(item.created_at)}`;

    const box = h("input", {
      type: "checkbox",
      checked: isBought,
      "data-item-id": item.id,
      onchange: async () => {
        box.disabled = true;
        try {
          await api.setBought(groupId, item.id, box.checked);
          await refresh();
        } catch (error) {
          box.checked = !box.checked;
          box.disabled = false;
          toast(error.message, "error");
        }
      },
    });

    const remove = h(
      "button",
      {
        class: "remove",
        type: "button",
        "aria-label": `Remover ${item.name}`,
        onclick: () =>
          withBusy(remove, async () => {
            await api.deleteItem(groupId, item.id);
            toast(`${item.name} removido.`);
            await refresh();
          }),
      },
      h("span", { "aria-hidden": "true" }, "✕"),
    );

    return h(
      "li",
      { class: `item${isBought ? " bought" : ""}` },
      h(
        "label",
        { class: "check" },
        box,
        h(
          "span",
          {},
          h("span", { class: "item-name" }, item.name, item.quantity && ` — ${item.quantity}`),
          item.note && h("span", { class: "item-meta" }, item.note),
          h("span", { class: "item-meta" }, meta),
        ),
      ),
      remove,
    );
  }

  await refresh();
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
