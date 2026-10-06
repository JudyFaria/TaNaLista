// Utilitários de interface. Todo texto do usuário entra via textContent
// (nunca innerHTML), o que evita injeção de HTML/XSS.

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value == null || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "class") {
      el.className = value;
    } else if (value === true) {
      el.setAttribute(key, "");
    } else {
      el.setAttribute(key, value);
    }
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false || child === "") continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

let fieldSeq = 0;

/** Campo de formulário com rótulo e dica associados (acessível a leitores de tela). */
export function field({ label, name, type = "text", hint, value, ...attrs }) {
  const id = `f-${name}-${++fieldSeq}`;
  const hintId = hint ? `${id}-hint` : null;
  const common = { id, name, "aria-describedby": hintId, ...attrs };
  const input = type === "textarea"
    ? h("textarea", common, value ?? "")
    : h("input", { type, value, ...common });
  return h(
    "div",
    { class: "field" },
    h("label", { for: id }, label),
    hint && h("span", { class: "hint", id: hintId }, hint),
    input,
  );
}

/** Checkbox com o rótulo clicável inteiro (alvo de toque grande). */
export function checkbox({ label, name, checked, hint }) {
  return h(
    "label",
    { class: "check" },
    h("input", { type: "checkbox", name, checked }),
    h("span", {}, label, hint && h("span", { class: "hint" }, hint)),
  );
}

/**
 * Liga um formulário a uma ação assíncrona: desabilita o envio enquanto
 * processa e mostra o erro em uma área anunciada (role="alert").
 */
export function onSubmit(form, handler) {
  const errorBox = h("p", { class: "form-error", role: "alert", hidden: true });
  form.prepend(errorBox);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = form.querySelector('[type="submit"]');
    errorBox.hidden = true;
    if (submit) submit.disabled = true;
    try {
      await handler(Object.fromEntries(new FormData(form)));
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      if (submit) submit.disabled = false;
    }
  });
  return form;
}

/** Executa uma ação de botão com estado ocupado e erro em aviso. */
export async function withBusy(button, action) {
  button.disabled = true;
  try {
    return await action();
  } catch (error) {
    toast(error.message, "error");
    return undefined;
  } finally {
    button.disabled = false;
  }
}

export function toast(message, kind = "info") {
  const region = document.getElementById("toasts");
  const el = h("div", { class: `toast${kind === "error" ? " error" : ""}` }, message);
  region.append(el);
  setTimeout(() => el.remove(), kind === "error" ? 6000 : 4000);
}

export function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

const dateFormat = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
export function formatDate(iso) {
  return iso ? dateFormat.format(new Date(iso)) : "";
}

export function inviteUrl(code) {
  return `${location.origin}/#/convite/${encodeURIComponent(code)}`;
}
