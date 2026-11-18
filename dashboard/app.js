"use strict";

// Dashboard financiero - Unidad 3 Actividad 1 (el administrativo vive en admin.js, Actividad 2)
// El backend es la unica fuente de calculo: aqui solo se piden datos a GraphQL y se formatean.

const API = (window.DASHBOARD_CONFIG && window.DASHBOARD_CONFIG.graphqlUrl) || "/graphql";
const CLAVE_TOKEN = "sgi.token";
const CLAVE_PERIODO = "sgi.periodo";

const LOGIN = `
mutation IniciarSesion($email: String!, $password: String!, $companyId: ID) {
  login(input: {email: $email, password: $password, companyId: $companyId}) {
    token
    tokenType
    user { name }
  }
}`;

const SESION = `
query MiSesion {
  mySession {
    company { id name rfc }
    user { name email }
    role { code name }
    permissions
  }
}`;

const INDICADORES = `
query IndicadoresEmpresa($from: Date!, $to: Date!) {
  generalBalance(fromDate: $from, toDate: $to) {
    companyId
    currency
    fromDate
    toDate
    openingBalance
    totalIncome
    totalExpense
    profit
    closingBalance
    isInRed
    accountsInRed
    accounts {
      accountId
      accountName
      isActive
      openingBalance
      totalIncome
      totalExpense
      profit
      closingBalance
      isInRed
    }
  }
}`;

// Mensajes del backend (auth.py / schema.py) que significan "la sesion ya no sirve"
const ERRORES_SESION = [
  "Falta el token",
  "El token no es valido",
  "La membresia no existe o no esta activa",
  "La membresia no existe o esta desactivada",
  "El token no corresponde a esa empresa",
];
// Mensajes que significan "la sesion sirve pero no hay permiso de lectura"
const ERRORES_PERMISO = ["El rol no tiene el permiso", "La membresia no tiene un rol activo"];

const $ = (sel) => document.querySelector(sel);

// ---------- Almacenamiento (solo en el navegador, nunca en el repositorio) ----------

function leer(clave) {
  try { return sessionStorage.getItem(clave); } catch { return null; }
}
function guardar(clave, valor) {
  try { sessionStorage.setItem(clave, valor); } catch { /* sin almacenamiento: solo en memoria */ }
}
function borrar(clave) {
  try { sessionStorage.removeItem(clave); } catch { /* nada */ }
}

let token = leer(CLAVE_TOKEN);
// Sesion del API (mySession): empresa, usuario, rol y permisos del rol
let sesion = null;
let temporizadorVencimiento = null;
let peticionActual = 0;

// ---------- GraphQL ----------

class ErrorApi extends Error {
  constructor(mensaje, tipo) {
    super(mensaje);
    this.tipo = tipo; // "sesion" | "permiso" | "fechas" | "red" | "otro"
  }
}

function clasificar(mensaje) {
  if (ERRORES_SESION.some((m) => mensaje.startsWith(m))) return "sesion";
  if (ERRORES_PERMISO.some((m) => mensaje.startsWith(m))) return "permiso";
  if (/fromDate|toDate|DateTime|Date/.test(mensaje) && !/idempotencyKey/.test(mensaje)) return "fechas";
  return "otro";
}

async function graphql(query, variables = {}, { conToken = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (conToken) {
    if (!token) throw new ErrorApi("Falta el token", "sesion");
    headers.Authorization = `Bearer ${token}`;
  }
  let respuesta;
  try {
    respuesta = await fetch(API, { method: "POST", headers, body: JSON.stringify({ query, variables }) });
  } catch {
    throw new ErrorApi("No se pudo conectar con el API. Revisa que el backend esté levantado.", "red");
  }
  let cuerpo;
  try {
    cuerpo = await respuesta.json();
  } catch {
    throw new ErrorApi(`El API respondió ${respuesta.status} sin un JSON válido.`, "red");
  }
  if (cuerpo.errors && cuerpo.errors.length) {
    const mensaje = cuerpo.errors[0].message;
    throw new ErrorApi(mensaje, clasificar(mensaje));
  }
  return cuerpo.data;
}

// ---------- Formato de importes (sin float: se trabaja con el texto que manda el servidor) ----------

function formatoMXN(valor) {
  if (valor === null || valor === undefined) return "—";
  let texto = String(valor).trim();
  let signo = "";
  if (texto.startsWith("-")) { signo = "−"; texto = texto.slice(1); }
  let [entero, decimales = ""] = texto.split(".");
  decimales = (decimales + "00").slice(0, 2);
  entero = entero.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  if (signo && /^0+$/.test(entero.replace(/,/g, "")) && decimales === "00") signo = "";
  return `${signo}$${entero}.${decimales}`;
}

const esNegativo = (valor) => String(valor).trim().startsWith("-") && !/^-0*(\.0*)?$/.test(String(valor).trim());
const esCero = (valor) => /^-?0*(\.0*)?$/.test(String(valor).trim());

// ---------- Fechas ----------

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function iso(fecha) {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

function textoFecha(valorIso) {
  const [a, m, d] = valorIso.split("-");
  return `${Number(d)} ${MESES[Number(m) - 1]} ${a}`;
}

function periodoAtajo(tipo) {
  const hoy = new Date();
  if (tipo === "mes") return [iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), iso(hoy)];
  if (tipo === "anterior") {
    return [iso(new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)), iso(new Date(hoy.getFullYear(), hoy.getMonth(), 0))];
  }
  return ["2026-10-26", "2026-10-30"]; // periodo de demostracion de la Unidad II
}

function periodoInicial() {
  try {
    const guardado = JSON.parse(leer(CLAVE_PERIODO) || "null");
    if (guardado && guardado.from && guardado.to) return [guardado.from, guardado.to];
  } catch { /* periodo guardado invalido */ }
  return periodoAtajo("mes");
}

function vencimientoToken(t) {
  // Solo se lee el campo exp para avisar; la validacion real la hace el backend con la firma.
  try {
    const parte = t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const datos = JSON.parse(atob(parte.padEnd(parte.length + ((4 - (parte.length % 4)) % 4), "=")));
    return typeof datos.exp === "number" ? new Date(datos.exp * 1000) : null;
  } catch {
    return null;
  }
}

// ---------- Vistas ----------

function mostrarLogin(mensaje, tipo = "error") {
  clearTimeout(temporizadorVencimiento);
  $("#vista-dashboard").hidden = true;
  $("#vista-login").hidden = false;
  const aviso = $("#login-aviso");
  aviso.hidden = !mensaje;
  aviso.textContent = mensaje || "";
  aviso.className = tipo === "error" ? "aviso error" : "aviso";
  $("#password").value = "";
  ($("#email").value ? $("#password") : $("#email")).focus();
}

function cerrarSesion(mensaje, tipo) {
  token = null;
  sesion = null;
  borrar(CLAVE_TOKEN);
  peticionActual++; // descarta respuestas que lleguen despues
  mostrarLogin(mensaje, tipo);
}

async function entrarAlDashboard() {
  $("#vista-login").hidden = true;
  $("#vista-dashboard").hidden = false;

  const vence = vencimientoToken(token);
  clearTimeout(temporizadorVencimiento);
  if (vence) {
    $("#sesion-vence").textContent = `Sesión válida hasta las ${vence.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}`;
    const restante = vence.getTime() - Date.now();
    temporizadorVencimiento = setTimeout(
      () => cerrarSesion("Tu sesión expiró. Vuelve a iniciar sesión."),
      Math.max(restante, 0),
    );
  }

  try {
    const { mySession: s } = await graphql(SESION);
    sesion = s;
    $("#empresa-nombre").textContent = s.company.name;
    $("#empresa-rfc").textContent = `RFC ${s.company.rfc} · Empresa #${s.company.id}`;
    $("#usuario-nombre").textContent = s.user.name;
    $("#usuario-rol").textContent = s.role ? s.role.code : "SIN ROL";
  } catch (e) {
    if (e.tipo === "sesion") return cerrarSesion(mensajeSesion(e));
    $("#empresa-nombre").textContent = "Empresa";
    sesion = { permissions: [] };
  }

  $("#fromDate").value = "";
  navegar(); // admin.js: abre la seccion de la URL (#/financiero por omision)
}

// Se llama cada vez que se abre la seccion financiera
function abrirFinanciero() {
  if (!$("#fromDate").value || !$("#toDate").value) {
    const [desde, hasta] = periodoInicial();
    $("#fromDate").value = desde;
    $("#toDate").value = hasta;
  }
  consultar();
}

function mensajeSesion(e) {
  if (e.message.startsWith("Falta el token")) return "Inicia sesión para ver el dashboard.";
  if (e.message.startsWith("El token no es valido")) return "Tu sesión expiró o el token no es válido. Vuelve a iniciar sesión.";
  return "Tu membresía ya no está activa en esta empresa. Vuelve a iniciar sesión.";
}

function mostrarEstado(titulo, texto) {
  $("#datos").hidden = true;
  $("#estado-error").hidden = false;
  $("#estado-error-titulo").textContent = titulo;
  $("#estado-error-texto").textContent = texto;
}

function avisoPeriodo(texto) {
  const aviso = $("#periodo-aviso");
  aviso.hidden = !texto;
  aviso.textContent = texto || "";
  aviso.className = "aviso error";
}

// ---------- Consulta y pintado ----------

async function consultar() {
  const desde = $("#fromDate").value;
  const hasta = $("#toDate").value;

  if (!desde || !hasta) {
    avisoPeriodo("Escribe las dos fechas del período.");
    return;
  }
  if (desde > hasta) {
    // No se llama al API a ciegas
    avisoPeriodo(`La fecha inicial (${textoFecha(desde)}) es posterior a la final (${textoFecha(hasta)}). Corrige el período.`);
    $("#periodo-texto").textContent = "período inválido";
    mostrarEstado("Período inválido", "No se consultó el API. Ajusta las fechas y pulsa Actualizar.");
    return;
  }
  avisoPeriodo(null);
  guardar(CLAVE_PERIODO, JSON.stringify({ from: desde, to: hasta }));

  const id = ++peticionActual;
  const contenido = $("#contenido");
  contenido.classList.add("cargando");
  $("#btn-actualizar").disabled = true;
  $("#periodo-texto").textContent = `consultando ${textoFecha(desde)} al ${textoFecha(hasta)}…`;

  try {
    const { generalBalance } = await graphql(INDICADORES, { from: desde, to: hasta });
    if (id !== peticionActual) return; // llego una respuesta vieja: se ignora
    pintar(generalBalance);
  } catch (e) {
    if (id !== peticionActual) return;
    if (e.tipo === "sesion") return cerrarSesion(mensajeSesion(e));
    $("#periodo-texto").textContent = `${textoFecha(desde)} al ${textoFecha(hasta)}`;
    if (e.tipo === "permiso") {
      mostrarEstado(
        "Acceso denegado",
        "Tu rol no tiene permiso para ver los balances de la empresa (se requieren accounts.read y transactions.read). " +
        `Pide al administrador que te asigne un rol con lectura. Detalle del servidor: “${e.message}”.`,
      );
    } else if (e.tipo === "fechas") {
      mostrarEstado("Período inválido", e.message);
    } else {
      mostrarEstado("No se pudieron cargar los indicadores", e.message);
    }
  } finally {
    if (id === peticionActual) {
      contenido.classList.remove("cargando");
      $("#btn-actualizar").disabled = false;
    }
  }
}

function pintarImporte(el, valor, { rojoSiNegativo = false, profit = false } = {}) {
  el.textContent = formatoMXN(valor);
  el.classList.toggle("negativo", rojoSiNegativo && esNegativo(valor));
  el.classList.toggle("profit-negativo", profit && esNegativo(valor));
}

function pintar(g) {
  $("#estado-error").hidden = true;
  $("#datos").hidden = false;

  // El periodo que se muestra es el que devolvio el servidor, no el de los campos
  $("#periodo-texto").textContent = `${textoFecha(g.fromDate)} al ${textoFecha(g.toDate)} · ${g.currency}`;

  const campo = (nombre) => document.querySelector(`.indicadores [data-campo="${nombre}"]`);
  pintarImporte(campo("closingBalance"), g.closingBalance, { rojoSiNegativo: true });
  pintarImporte(campo("openingBalance"), g.openingBalance, { rojoSiNegativo: true });
  pintarImporte(campo("totalIncome"), g.totalIncome);
  pintarImporte(campo("totalExpense"), g.totalExpense);
  pintarImporte(campo("profit"), g.profit, { profit: true });
  $("#t-final").classList.toggle("en-rojo", g.isInRed);

  // Riesgo: el general y las cuentas se muestran por separado (una cuenta puede estar en rojo y el general no)
  const general = $("#riesgo-general");
  general.className = `riesgo-item ${g.isInRed ? "alerta" : "ok"}`;
  general.querySelector(".riesgo-valor").textContent = g.isInRed
    ? "Sí — saldo final general negativo"
    : "No — saldo final general en positivo o cero";

  const cuentasRojo = $("#riesgo-cuentas");
  cuentasRojo.className = `riesgo-item ${g.accountsInRed > 0 ? "alerta" : "ok"}`;
  cuentasRojo.querySelector(".riesgo-valor").textContent =
    g.accountsInRed === 0 ? "0 cuentas" : `${g.accountsInRed} ${g.accountsInRed === 1 ? "cuenta" : "cuentas"}`;
  const nombres = g.accounts.filter((c) => c.isInRed).map((c) => c.accountName);
  $("#riesgo-cuentas-nombres").textContent = nombres.length ? `En rojo: ${nombres.join(", ")}` : "Ninguna cuenta con saldo final negativo";

  // Detalle por cuenta
  const cuerpo = $("#tabla-cuentas tbody");
  cuerpo.replaceChildren();
  const vacio = $("#detalle-vacio");
  $("#tabla-cuentas").hidden = g.accounts.length === 0;

  if (g.accounts.length === 0) {
    vacio.hidden = false;
    vacio.textContent = "La empresa todavía no tiene cuentas registradas. Los indicadores aparecen en cero hasta que se creen cuentas y movimientos.";
  } else if (esCero(g.totalIncome) && esCero(g.totalExpense)) {
    vacio.hidden = false;
    vacio.textContent = `No hubo movimientos entre el ${textoFecha(g.fromDate)} y el ${textoFecha(g.toDate)}. Los saldos mostrados vienen de movimientos anteriores al período.`;
  } else {
    vacio.hidden = true;
  }

  for (const c of g.accounts) {
    const fila = document.createElement("tr");
    if (c.isInRed) fila.classList.add("en-rojo");

    const nombre = document.createElement("td");
    nombre.textContent = c.accountName;
    if (!c.isActive) {
      const tag = document.createElement("span");
      tag.className = "etiqueta inactiva";
      tag.textContent = "inactiva";
      nombre.append(tag);
    }
    fila.append(nombre);

    for (const [clave, opciones] of [
      ["openingBalance", { rojoSiNegativo: true }],
      ["totalIncome", {}],
      ["totalExpense", {}],
      ["profit", { profit: true }],
      ["closingBalance", { rojoSiNegativo: true }],
    ]) {
      const td = document.createElement("td");
      td.className = "num";
      const span = document.createElement("span");
      pintarImporte(span, c[clave], opciones);
      td.append(span);
      fila.append(td);
    }

    const estado = document.createElement("td");
    const etiqueta = document.createElement("span");
    etiqueta.className = `etiqueta ${c.isInRed ? "rojo" : "ok"}`;
    etiqueta.textContent = c.isInRed ? "En rojo" : "OK";
    estado.append(etiqueta);
    fila.append(estado);

    cuerpo.append(fila);
  }
}

// ---------- Eventos ----------

$("#form-login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const email = $("#email").value.trim();
  const password = $("#password").value;
  const companyId = $("#companyId").value.trim() || null;
  if (!email || !password) {
    mostrarLogin("Escribe tu correo y tu contraseña.");
    return;
  }
  const boton = $("#btn-entrar");
  boton.disabled = true;
  boton.textContent = "Entrando…";
  try {
    const { login } = await graphql(LOGIN, { email, password, companyId }, { conToken: false });
    token = login.token;
    guardar(CLAVE_TOKEN, token);
    $("#login-aviso").hidden = true;
    $("#password").value = "";
    await entrarAlDashboard();
  } catch (e) {
    if (e.message.startsWith("Perteneces a varias empresas")) {
      $("#campo-empresa").hidden = false;
      mostrarLogin("Perteneces a varias empresas: escribe el id de la empresa con la que quieres entrar.", "aviso");
      $("#companyId").focus();
    } else if (e.message.startsWith("Correo o contrasena incorrectos")) {
      mostrarLogin("Correo o contraseña incorrectos.");
    } else {
      mostrarLogin(e.message);
    }
  } finally {
    boton.disabled = false;
    boton.textContent = "Entrar";
  }
});

$("#form-periodo").addEventListener("submit", (ev) => {
  ev.preventDefault();
  consultar();
});

for (const id of ["#fromDate", "#toDate"]) {
  $(id).addEventListener("change", () => consultar());
}

document.querySelectorAll("[data-atajo]").forEach((boton) => {
  boton.addEventListener("click", () => {
    const [desde, hasta] = periodoAtajo(boton.dataset.atajo);
    $("#fromDate").value = desde;
    $("#toDate").value = hasta;
    consultar();
  });
});

$("#btn-salir").addEventListener("click", () => {
  borrar(CLAVE_PERIODO);
  cerrarSesion("Cerraste sesión.", "aviso");
});

// El inicio (login o dashboard) lo hace admin.js cuando ya cargo el enrutador.
