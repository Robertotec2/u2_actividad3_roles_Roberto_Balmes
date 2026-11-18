"use strict";

// Dashboard administrativo - Unidad 3 Actividad 2
// Usuarios, Cuentas y Conceptos. Cada tabla es una query y cada Guardar es una mutation;
// despues de una mutation correcta la tabla se vuelve a consultar (no se agrega la fila a mano).
// Usa lo que define app.js: $, graphql, token, sesion, cerrarSesion, mensajeSesion, abrirFinanciero.

const Q_USUARIOS = `
query Usuarios {
  companyUsers {
    id
    isAdmin
    isActive
    user { name email }
    role { code name }
  }
}`;

const Q_CUENTAS = `
query Cuentas($activeOnly: Boolean) {
  accounts(activeOnly: $activeOnly) {
    id
    name
    accountType
    bankName
    clabeMasked
    description
    isActive
  }
}`;

const Q_CONCEPTOS = `
query Conceptos {
  concepts {
    id
    name
    type
    description
    isActive
  }
}`;

const Q_CONCEPTOS_DE_CUENTA = `
query ConceptosDeCuenta($accountId: ID!) {
  accountConcepts(accountId: $accountId) {
    id
    isActive
    concept { id name type isActive }
  }
}`;

const M_NUEVO_USUARIO = `
mutation NuevoUsuario($input: CreateCompanyUserInput!) {
  createCompanyUser(input: $input) {
    id
    isAdmin
    isActive
    user { name email }
  }
}`;

const M_DESACTIVAR_USUARIO = `
mutation DesactivarUsuario($id: ID!) {
  deactivateCompanyUser(companyUserId: $id) { id isActive user { name } }
}`;

const M_NUEVA_CUENTA = `
mutation NuevaCuenta($input: CreateAccountInput!) {
  createAccount(input: $input) {
    id
    name
    accountType
    isActive
  }
}`;

const M_NUEVO_CONCEPTO = `
mutation NuevoConcepto($input: CreateConceptInput!) {
  createConcept(input: $input) { id name type isActive }
}`;

const M_ASIGNAR = `
mutation AsignarConcepto($input: AssignConceptToAccountInput!) {
  assignConceptToAccount(input: $input) { id isActive concept { name } }
}`;

const M_QUITAR = `
mutation QuitarConcepto($input: AssignConceptToAccountInput!) {
  removeConceptFromAccount(input: $input) { id isActive concept { name } }
}`;

// Catalogo de tipos de cuenta del Parcial I
const TIPOS_CUENTA = {
  CASH: "Efectivo",
  DEBIT: "Débito",
  CREDIT: "Crédito",
  SAVINGS: "Ahorro",
  INVESTMENT: "Inversión",
  WALLET: "Monedero",
  OTHER: "Otro",
};
const TIPOS_CONCEPTO = { INCOME: "Ingreso", EXPENSE: "Egreso" };

// Mensajes del backend (sin acentos) -> texto para la pantalla
const MENSAJES = {
  "Ese correo ya esta registrado": "Ese correo ya está registrado. Usa otro correo.",
  "Esta empresa ya tiene un administrador principal": "Esta empresa ya tiene un administrador principal; no puede haber un segundo.",
  "No se puede desactivar al administrador principal": "No se puede desactivar al administrador principal.",
  "Ese concepto ya esta asignado a la cuenta": "Ese concepto ya está asignado a esta cuenta.",
  "Ese concepto no esta asignado a la cuenta": "Ese concepto ya no está asignado a esta cuenta.",
  "La CLABE tiene que tener 18 digitos": "La CLABE tiene que tener 18 dígitos.",
  "El correo no tiene un formato valido": "El correo no tiene un formato válido.",
  "La contrasena tiene que tener al menos 6 caracteres": "La contraseña tiene que tener al menos 6 caracteres.",
};
const textoError = (m) => MENSAJES[m] || m;

const RUTAS = {
  financiero: { vista: "#vista-financiero", marca: "Dashboard financiero", abrir: () => abrirFinanciero() },
  usuarios: { vista: "#vista-usuarios", marca: "Dashboard administrativo · Usuarios", lectura: "company.users.read", abrir: () => cargarUsuarios() },
  cuentas: { vista: "#vista-cuentas", marca: "Dashboard administrativo · Cuentas", lectura: "accounts.read", abrir: () => cargarCuentas() },
  conceptos: { vista: "#vista-conceptos", marca: "Dashboard administrativo · Conceptos", lectura: "concepts.read", abrir: () => cargarConceptos() },
};

const estado = {
  ruta: null,
  usuarios: [],
  filtroUsuarios: "todos",
  cuentas: [],
  filtroTipoCuenta: "todas",
  conceptos: [],
  filtroConceptos: "todos",
  cuentasSelector: [],
  cuentaElegida: null,
  pedido: 0, // descarta respuestas viejas al cambiar de seccion
};

const puede = (permiso) => Boolean(sesion && sesion.permissions && sesion.permissions.includes(permiso));

function el(tag, props = {}, ...hijos) {
  const nodo = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") nodo.className = v;
    else if (k === "dataset") Object.assign(nodo.dataset, v);
    else if (k.startsWith("on")) nodo.addEventListener(k.slice(2), v);
    else nodo[k] = v;
  }
  for (const h of hijos) if (h !== null && h !== undefined) nodo.append(h);
  return nodo;
}

// ---------- Enrutador ----------

function rutaActual() {
  const h = location.hash.replace(/^#\/?/, "");
  if (h.startsWith("admin/")) return h.slice(6);
  return h || "financiero";
}

function navegar() {
  let ruta = rutaActual();
  if (!RUTAS[ruta]) ruta = "financiero";
  const esperado = ruta === "financiero" ? "#/financiero" : `#/admin/${ruta}`;
  if (location.hash !== esperado) history.replaceState(null, "", esperado);

  estado.ruta = ruta;
  estado.pedido++;
  const def = RUTAS[ruta];

  for (const r of Object.values(RUTAS)) $(r.vista).hidden = true;
  $("#admin-denegado").hidden = true;
  document.querySelectorAll(".menu a").forEach((a) => {
    const activo = a.dataset.ruta === ruta;
    a.classList.toggle("activo", activo);
    if (activo) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  $("#seccion-marca").textContent = def.marca;
  $("#empresa-moneda").hidden = ruta !== "financiero"; // en administracion no hay importes: sin MXN
  document.title = `${def.marca} · Sistema General de Ingresos`;

  document.querySelectorAll(".admin-aviso").forEach((a) => { a.hidden = true; });
  document.querySelectorAll(".panel-alta").forEach((f) => { f.hidden = true; f.reset(); });

  // Botones de escritura: solo se dibujan si el rol tiene el permiso
  document.querySelectorAll("[data-permiso]").forEach((n) => { n.hidden = !puede(n.dataset.permiso); });

  $(def.vista).hidden = false;
  def.abrir();
}

function denegar(vista, permiso, detalle) {
  $(vista).hidden = true;
  $("#admin-denegado").hidden = false;
  $("#admin-denegado-texto").textContent =
    `Tu rol no tiene el permiso ${permiso} para ver esta sección. Pide al administrador un rol con lectura.` +
    (detalle ? ` Detalle del servidor: “${detalle}”.` : "");
}

function aviso(vista, texto, tipo = "error") {
  const a = $(`${vista} .admin-aviso`);
  a.hidden = !texto;
  a.textContent = texto || "";
  a.className = `admin-aviso aviso ${tipo}`;
}

// Errores de lectura: sesion -> login; permiso -> "Acceso denegado"; otro -> aviso en la vista
function errorDeLectura(e, ruta) {
  if (e.tipo === "sesion") { cerrarSesion(mensajeSesion(e)); return; }
  const def = RUTAS[ruta];
  if (e.tipo === "permiso") { denegar(def.vista, def.lectura, e.message); return; }
  aviso(def.vista, `No se pudo cargar la información: ${textoError(e.message)}`);
}

// Errores de escritura: se leen en la pantalla, no solo en la consola
function errorDeEscritura(e, vista) {
  if (e.tipo === "sesion") { cerrarSesion(mensajeSesion(e)); return; }
  aviso(vista, textoError(e.message));
}

async function enviando(form, accion) {
  const boton = form.querySelector('button[type="submit"]');
  boton.disabled = true;
  try { await accion(); } finally { boton.disabled = false; }
}

function abrirAlta(boton, form) {
  boton.addEventListener("click", () => {
    form.hidden = !form.hidden;
    if (!form.hidden) form.querySelector("input, select").focus();
  });
  form.querySelector("[data-cancelar]").addEventListener("click", () => { form.reset(); form.hidden = true; });
}

function etiquetaEstado(activo, femenino = false) {
  return el("span", { class: `etiqueta ${activo ? "ok" : "inactiva"}`, textContent: activo ? (femenino ? "Activa" : "Activo") : (femenino ? "Inactiva" : "Inactivo") });
}

function pintarVacio(contenedor, tabla, texto) {
  const vacio = contenedor.querySelector(".vacio");
  vacio.hidden = !texto;
  vacio.textContent = texto || "";
  tabla.hidden = Boolean(texto);
}

// ---------- Usuarios ----------

async function cargarUsuarios() {
  const id = estado.pedido;
  $("#vista-usuarios").classList.add("cargando");
  try {
    const { companyUsers } = await graphql(Q_USUARIOS);
    if (id !== estado.pedido) return;
    estado.usuarios = companyUsers;
    pintarUsuarios();
  } catch (e) {
    if (id === estado.pedido) errorDeLectura(e, "usuarios");
  } finally {
    $("#vista-usuarios").classList.remove("cargando");
  }
}

function pintarUsuarios() {
  const todos = estado.usuarios;
  // Conteos de personas (no importes), calculados con la misma lista
  const activos = todos.filter((u) => u.isActive).length;
  const admins = todos.filter((u) => u.isAdmin).length;
  $("#c-activos").textContent = activos;
  $("#c-inactivos").textContent = todos.length - activos;
  $("#c-admin").textContent = admins;
  const conteoAdmin = $("#conteo-admin");
  conteoAdmin.classList.toggle("alerta", admins > 1);
  $("#c-admin-nota").textContent = admins > 1
    ? "Error de datos: hay más de un administrador principal (regla del Parcial I)."
    : admins === 1 ? (todos.find((u) => u.isAdmin).user.name) : "Sin administrador principal";

  const buscar = $("#u-buscar").value.trim().toLowerCase();
  const filas = todos.filter((u) => {
    if (estado.filtroUsuarios === "activos" && !u.isActive) return false;
    if (estado.filtroUsuarios === "inactivos" && u.isActive) return false;
    return !buscar || u.user.name.toLowerCase().includes(buscar) || u.user.email.toLowerCase().includes(buscar);
  });

  const escribe = puede("company.users.write");
  const tabla = $("#tabla-usuarios");
  tabla.querySelector(".acciones-col").hidden = !escribe;
  const cuerpo = tabla.querySelector("tbody");
  cuerpo.replaceChildren();
  for (const u of filas) {
    const acciones = el("td", { class: "acciones-col" });
    acciones.hidden = !escribe;
    if (escribe && u.isActive && !u.isAdmin) {
      acciones.append(el("button", {
        type: "button", class: "secundario chico", textContent: "Desactivar",
        onclick: () => confirmarDesactivar(u),
      }));
    }
    cuerpo.append(el("tr", { class: u.isActive ? "" : "fila-inactiva" },
      el("td", { textContent: u.user.name }),
      el("td", { textContent: u.user.email }),
      el("td", {}, u.role ? el("span", { class: "chip", textContent: u.role.name }) : el("span", { class: "sin-dato", textContent: "Sin rol" })),
      el("td", { textContent: u.isAdmin ? "Sí" : "No" }),
      el("td", {}, etiquetaEstado(u.isActive)),
      acciones,
    ));
  }
  let vacio = null;
  if (todos.length === 0) vacio = "La empresa no tiene membresías registradas.";
  else if (filas.length === 0) vacio = "Ningún usuario coincide con la búsqueda o el filtro.";
  pintarVacio($("#vista-usuarios .caja-tabla"), tabla, vacio);
}

function confirmarDesactivar(u) {
  const dlg = $("#dlg-desactivar");
  $("#dlg-texto").textContent = `${u.user.name} (${u.user.email}) dejará de operar en esta empresa y no podrá iniciar sesión con ella.`;
  dlg.returnValue = "";
  dlg.onclose = async () => {
    if (dlg.returnValue !== "si") return;
    try {
      const { deactivateCompanyUser: r } = await graphql(M_DESACTIVAR_USUARIO, { id: u.id });
      aviso("#vista-usuarios", `${r.user.name} quedó inactivo. La membresía sigue en la base con su historial.`, "exito");
    } catch (e) {
      errorDeEscritura(e, "#vista-usuarios");
    }
    cargarUsuarios();
  };
  dlg.showModal();
}

$("#u-buscar").addEventListener("input", () => pintarUsuarios());
document.querySelectorAll("[data-filtro-usuarios]").forEach((b) => b.addEventListener("click", () => {
  estado.filtroUsuarios = b.dataset.filtroUsuarios;
  document.querySelectorAll("[data-filtro-usuarios]").forEach((x) => x.classList.toggle("activo", x === b));
  pintarUsuarios();
}));
abrirAlta($("#btn-nuevo-usuario"), $("#form-usuario"));

$("#form-usuario").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const input = {
    name: $("#u-nombre").value.trim(),
    email: $("#u-correo").value.trim(),
    password: $("#u-password").value,
  };
  if (!input.name || !input.email || !input.password) {
    aviso("#vista-usuarios", "Escribe nombre, correo y contraseña.");
    return;
  }
  enviando(form, async () => {
    try {
      const { createCompanyUser: r } = await graphql(M_NUEVO_USUARIO, { input });
      form.reset();
      form.hidden = true;
      aviso("#vista-usuarios", `Usuario ${r.user.name} (${r.user.email}) creado. Queda sin rol hasta la Actividad #14.`, "exito");
      await cargarUsuarios();
    } catch (e) {
      $("#u-password").value = "";
      errorDeEscritura(e, "#vista-usuarios");
    }
  });
});

// ---------- Cuentas ----------

function prepararTiposCuenta() {
  const select = $("#a-tipo");
  const filtros = $("#filtros-tipo-cuenta");
  filtros.append(el("button", { type: "button", class: "filtro activo", textContent: "Todas", dataset: { tipo: "todas" } }));
  for (const [valor, etiqueta] of Object.entries(TIPOS_CUENTA)) {
    select.append(el("option", { value: valor, textContent: etiqueta }));
    filtros.append(el("button", { type: "button", class: "filtro", textContent: etiqueta, dataset: { tipo: valor } }));
  }
  filtros.addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-tipo]");
    if (!b) return;
    estado.filtroTipoCuenta = b.dataset.tipo;
    filtros.querySelectorAll("button").forEach((x) => x.classList.toggle("activo", x === b));
    pintarCuentas();
  });
}

async function cargarCuentas() {
  const id = estado.pedido;
  $("#vista-cuentas").classList.add("cargando");
  try {
    const { accounts } = await graphql(Q_CUENTAS);
    if (id !== estado.pedido) return;
    estado.cuentas = accounts;
    pintarCuentas();
  } catch (e) {
    if (id === estado.pedido) errorDeLectura(e, "cuentas");
  } finally {
    $("#vista-cuentas").classList.remove("cargando");
  }
}

function pintarCuentas() {
  const soloActivas = $("#a-solo-activas").checked;
  const filas = estado.cuentas.filter((c) =>
    (estado.filtroTipoCuenta === "todas" || c.accountType === estado.filtroTipoCuenta) && (!soloActivas || c.isActive));
  const tabla = $("#tabla-cuentas-admin");
  const cuerpo = tabla.querySelector("tbody");
  cuerpo.replaceChildren();
  for (const c of filas) {
    cuerpo.append(el("tr", { class: c.isActive ? "" : "fila-inactiva" },
      el("td", {}, el("strong", { textContent: c.name }), c.description ? el("span", { class: "nota bloque", textContent: c.description }) : null),
      el("td", { textContent: TIPOS_CUENTA[c.accountType] || c.accountType }),
      el("td", {}, c.bankName ? c.bankName : el("span", { class: "sin-dato", textContent: "—" })),
      el("td", {}, c.clabeMasked ? el("span", { class: "mono", textContent: `CLABE ${c.clabeMasked}` }) : el("span", { class: "sin-dato", textContent: "—" })),
      el("td", {}, etiquetaEstado(c.isActive, true)),
    ));
  }
  let vacio = null;
  if (estado.cuentas.length === 0) vacio = "La empresa no tiene cuentas. Crea la primera con “Nueva cuenta”.";
  else if (filas.length === 0) vacio = "No hay cuentas con ese filtro.";
  pintarVacio($("#vista-cuentas .caja-tabla"), tabla, vacio);
}

$("#a-solo-activas").addEventListener("change", () => pintarCuentas());
abrirAlta($("#btn-nueva-cuenta"), $("#form-cuenta"));

$("#form-cuenta").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const vacioANull = (v) => (v.trim() === "" ? null : v.trim());
  const input = {
    name: $("#a-nombre").value.trim(),
    accountType: $("#a-tipo").value,
    bankName: vacioANull($("#a-banco").value),
    clabe: vacioANull($("#a-clabe").value),
    description: vacioANull($("#a-desc").value),
  };
  if (!input.name) {
    aviso("#vista-cuentas", "Escribe el nombre de la cuenta.");
    return;
  }
  enviando(form, async () => {
    try {
      const { createAccount: r } = await graphql(M_NUEVA_CUENTA, { input });
      form.reset();
      form.hidden = true;
      aviso("#vista-cuentas", `Cuenta ${r.name} (${TIPOS_CUENTA[r.accountType]}) creada.`, "exito");
      await cargarCuentas();
    } catch (e) {
      errorDeEscritura(e, "#vista-cuentas");
    }
  });
});

// ---------- Conceptos ----------

async function cargarConceptos() {
  const id = estado.pedido;
  $("#vista-conceptos").classList.add("cargando");
  try {
    const { concepts } = await graphql(Q_CONCEPTOS);
    if (id !== estado.pedido) return;
    estado.conceptos = concepts;
    pintarConceptos();
    // Las opciones del selector salen de accounts
    const { accounts } = await graphql(Q_CUENTAS, { activeOnly: true });
    if (id !== estado.pedido) return;
    estado.cuentasSelector = accounts;
    pintarSelectorCuentas();
  } catch (e) {
    if (id === estado.pedido) errorDeLectura(e, "conceptos");
  } finally {
    $("#vista-conceptos").classList.remove("cargando");
  }
}

function pintarConceptos() {
  const soloActivos = $("#c-solo-activos").checked;
  const filas = estado.conceptos.filter((c) =>
    (estado.filtroConceptos === "todos" || c.type === estado.filtroConceptos) && (!soloActivos || c.isActive));
  const tabla = $("#tabla-conceptos");
  const cuerpo = tabla.querySelector("tbody");
  cuerpo.replaceChildren();
  for (const c of filas) {
    cuerpo.append(el("tr", { class: c.isActive ? "" : "fila-inactiva" },
      el("td", {}, el("strong", { textContent: c.name }), c.description ? el("span", { class: "nota bloque", textContent: c.description }) : null),
      el("td", {}, el("span", { class: `etiqueta ${c.type === "INCOME" ? "ingreso" : "egreso"}`, textContent: TIPOS_CONCEPTO[c.type] })),
      el("td", {}, etiquetaEstado(c.isActive)),
    ));
  }
  let vacio = null;
  if (estado.conceptos.length === 0) vacio = "La empresa no tiene conceptos todavía.";
  else if (filas.length === 0) vacio = "No hay conceptos con ese filtro.";
  pintarVacio(tabla.closest(".caja-tabla"), tabla, vacio);

  // Conceptos que se pueden permitir: los activos del catalogo
  const select = $("#cc-concepto");
  const antes = select.value;
  select.replaceChildren(...estado.conceptos.filter((c) => c.isActive).map((c) =>
    el("option", { value: c.id, textContent: `${c.name} (${TIPOS_CONCEPTO[c.type]})` })));
  if ([...select.options].some((o) => o.value === antes)) select.value = antes;
}

function pintarSelectorCuentas() {
  const select = $("#cc-cuenta");
  select.replaceChildren(...estado.cuentasSelector.map((c) =>
    el("option", { value: c.id, textContent: `${c.name} · ${TIPOS_CUENTA[c.accountType] || c.accountType}` })));
  if (estado.cuentasSelector.length === 0) {
    $("#lista-permitidos").replaceChildren();
    $("#form-asignar").hidden = true;
    const vacio = $("#permitidos-vacio");
    vacio.hidden = false;
    vacio.textContent = "No hay cuentas activas. Crea una en la sección Cuentas.";
    return;
  }
  $("#form-asignar").hidden = !puede("concepts.write");
  if (estado.cuentasSelector.some((c) => c.id === estado.cuentaElegida)) select.value = estado.cuentaElegida;
  estado.cuentaElegida = select.value;
  cargarPermitidos();
}

async function cargarPermitidos() {
  const cuenta = estado.cuentaElegida;
  if (!cuenta) return;
  const id = estado.pedido;
  try {
    const { accountConcepts } = await graphql(Q_CONCEPTOS_DE_CUENTA, { accountId: cuenta });
    if (id !== estado.pedido || cuenta !== estado.cuentaElegida) return;
    pintarPermitidos(accountConcepts);
  } catch (e) {
    if (id === estado.pedido) errorDeLectura(e, "conceptos");
  }
}

function pintarPermitidos(lista) {
  const escribe = puede("concepts.write");
  const nombreCuenta = (estado.cuentasSelector.find((c) => c.id === estado.cuentaElegida) || {}).name || "";
  $("#lista-permitidos").replaceChildren(...lista.map((ac) => el("li", {},
    el("span", {}, el("strong", { textContent: ac.concept.name }), " ",
      el("span", { class: `etiqueta ${ac.concept.type === "INCOME" ? "ingreso" : "egreso"}`, textContent: TIPOS_CONCEPTO[ac.concept.type] })),
    escribe ? el("button", {
      type: "button", class: "secundario chico", textContent: "Quitar",
      onclick: () => quitar(ac.concept, nombreCuenta),
    }) : null,
  )));
  const vacio = $("#permitidos-vacio");
  vacio.hidden = lista.length > 0;
  vacio.textContent = `La cuenta ${nombreCuenta} todavía no acepta ningún concepto.`;
}

async function quitar(concepto, nombreCuenta) {
  try {
    await graphql(M_QUITAR, { input: { accountId: estado.cuentaElegida, conceptId: concepto.id } });
    aviso("#vista-conceptos", `${concepto.name} ya no está permitido en ${nombreCuenta}. Sigue en el catálogo.`, "exito");
  } catch (e) {
    errorDeEscritura(e, "#vista-conceptos");
  }
  cargarPermitidos();
}

$("#cc-cuenta").addEventListener("change", (ev) => {
  estado.cuentaElegida = ev.target.value;
  aviso("#vista-conceptos", null);
  cargarPermitidos();
});

$("#form-asignar").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const conceptId = $("#cc-concepto").value;
  if (!conceptId) {
    aviso("#vista-conceptos", "No hay conceptos activos para asignar. Crea uno con “Nuevo concepto”.");
    return;
  }
  enviando(ev.target, async () => {
    try {
      const { assignConceptToAccount: r } = await graphql(M_ASIGNAR, { input: { accountId: estado.cuentaElegida, conceptId } });
      const cuenta = estado.cuentasSelector.find((c) => c.id === estado.cuentaElegida);
      aviso("#vista-conceptos", `${r.concept.name} ahora está permitido en ${cuenta ? cuenta.name : "la cuenta"}.`, "exito");
    } catch (e) {
      errorDeEscritura(e, "#vista-conceptos");
    }
    await cargarPermitidos();
  });
});

document.querySelectorAll("[data-filtro-conceptos]").forEach((b) => b.addEventListener("click", () => {
  estado.filtroConceptos = b.dataset.filtroConceptos;
  document.querySelectorAll("[data-filtro-conceptos]").forEach((x) => x.classList.toggle("activo", x === b));
  pintarConceptos();
}));
$("#c-solo-activos").addEventListener("change", () => pintarConceptos());
abrirAlta($("#btn-nuevo-concepto"), $("#form-concepto"));

$("#form-concepto").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const desc = $("#c-desc").value.trim();
  const input = { name: $("#c-nombre").value.trim(), type: $("#c-tipo").value, description: desc || null };
  if (!input.name) {
    aviso("#vista-conceptos", "Escribe el nombre del concepto.");
    return;
  }
  enviando(form, async () => {
    try {
      const { createConcept: r } = await graphql(M_NUEVO_CONCEPTO, { input });
      form.reset();
      form.hidden = true;
      aviso("#vista-conceptos", `Concepto ${r.name} (${TIPOS_CONCEPTO[r.type]}) creado. Asígnalo a una cuenta en el panel de la derecha.`, "exito");
      await cargarConceptos();
    } catch (e) {
      errorDeEscritura(e, "#vista-conceptos");
    }
  });
});

// ---------- Inicio ----------

prepararTiposCuenta();
window.addEventListener("hashchange", () => { if (token && sesion) navegar(); });

if (token) {
  entrarAlDashboard();
} else {
  mostrarLogin(null);
}
