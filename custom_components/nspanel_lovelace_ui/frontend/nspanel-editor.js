/* NSPanel Lovelace UI card editor - Home Assistant sidebar panel (admins only).
 *
 * Plain web component, no build step and no external libraries. Forms come from the schema the
 * integration sends (backend/config_schema.py), and so do the field errors: the editor shows
 * the server's issues next to the fields, so the rules exist only once.
 */
const DOMAIN = "nspanel_lovelace_ui";

const UI = {
  en: {
    title: "NSPanel cards", save: "Save", reload: "Reload panels", undo: "Undo", redo: "Redo",
    fromDisk: "Load from file", unsaved: "Unsaved changes", noChanges: "No changes",
    panel: "Panel", addPanel: "Add panel", panelName: "Name of the new panel", deletePanel: "Delete panel",
    settings: "Panel settings", screensaver: "Screensaver", cards: "Cards", hiddenCards: "Hidden cards",
    global: "Global", yaml: "YAML", addCard: "Add card", chooseType: "Choose a card type",
    duplicate: "Duplicate", delete: "Delete", moveUp: "Move up", moveDown: "Move down", drag: "Drag to reorder",
    entities: "Entities", addEntity: "Add entity", more: "More options", advanced: "Advanced",
    confirmDelete: "Delete “{name}”?", confirmDeletePanel: "Delete panel “{name}” with all its cards?",
    cancel: "Cancel", ok: "OK", close: "Close", errors: "{n} errors", warnings: "{n} warnings",
    errorsBlock: "Fix the errors before saving.", saving: "Saving…", savedOk: "Saved. Backup: {backup}",
    reloadNow: "Reload now", reloadOk: "Panels reloaded.", reloadFailed: "Reload failed: {reason}",
    conflictTitle: "The file changed on disk",
    conflictText: "Someone changed {path} after the editor loaded it.",
    overwrite: "Overwrite with my changes", discard: "Load the file (drop my changes)",
    dirtyReload: "You have unsaved changes. Reloading uses the saved file.", saveAndReload: "Save and reload",
    reloadAnyway: "Reload without saving", dirtyLoad: "Drop your unsaved changes and load the file?",
    comments: "The file contains comments. Saving from the editor removes them (the previous file is kept as .bak).",
    parseError: "The file cannot be read: {error}. Fix it in the YAML tab.",
    yamlHelp: "The whole file. Apply the YAML to check it and edit it in the forms again.",
    applyYaml: "Apply YAML", yamlApplied: "YAML applied.", preview: "Preview", noCards: "No cards yet.",
    none: "—", value: "Value", time: "Time", addRow: "Add row",
    removeRow: "Remove", useSchedule: "Different brightness by time", item: "Entity", inherited: "inherited: {value}",
    notConfigured: "The integration is not set up yet.", loading: "Loading…", type: "Card type",
    changeType: "Change the card type? Options of the old type stay in the file.", issues: "Problems",
    list: "List (comma separated)", noPanels: "No panels. Add one.", jsonHelp: "JSON or key: value lines",
    pickIcon: "Choose icon", pickIconNow: "Choose icon (now: {icon})", pickIconDefault: "Choose icon (default: {icon})",
    defaultIcon: "Default: {icon}", iconSearch: "Search by name or alias, e.g. lamp",
    iconCategory: "Category", iconSuggested: "Suggested for this entity", iconRecent: "Recently used",
    iconAll: "All icons", iconCategories: "Categories", iconUseDefault: "Use the default", iconClear: "No icon set",
    iconMore: "Show {n} more", iconNone: "No icons found.", iconCount: "{n} icons", iconRecentEmpty: "No recently used icons yet.",
    iconAliases: "also: {aliases}", iconFont: "Only icons the panel can show (MDI {version}).", iconDeprecated: "deprecated in MDI",
    iconTemplate: "template or text – no icon preview",
  },
  pl: {
    title: "Karty NSPanel", save: "Zapisz", reload: "Przeładuj panele", undo: "Cofnij", redo: "Ponów",
    fromDisk: "Wczytaj z pliku", unsaved: "Niezapisane zmiany", noChanges: "Bez zmian",
    panel: "Panel", addPanel: "Dodaj panel", panelName: "Nazwa nowego panelu", deletePanel: "Usuń panel",
    settings: "Ustawienia panelu", screensaver: "Wygaszacz", cards: "Karty", hiddenCards: "Ukryte karty",
    global: "Globalne", yaml: "YAML", addCard: "Dodaj kartę", chooseType: "Wybierz typ karty",
    duplicate: "Duplikuj", delete: "Usuń", moveUp: "W górę", moveDown: "W dół", drag: "Przeciągnij, aby zmienić kolejność",
    entities: "Encje", addEntity: "Dodaj encję", more: "Więcej opcji", advanced: "Zaawansowane",
    confirmDelete: "Usunąć „{name}”?", confirmDeletePanel: "Usunąć panel „{name}” ze wszystkimi kartami?",
    cancel: "Anuluj", ok: "OK", close: "Zamknij", errors: "Błędy: {n}", warnings: "Ostrzeżenia: {n}",
    errorsBlock: "Popraw błędy przed zapisem.", saving: "Zapisywanie…", savedOk: "Zapisano. Kopia: {backup}",
    reloadNow: "Przeładuj teraz", reloadOk: "Panele przeładowane.", reloadFailed: "Przeładowanie nieudane: {reason}",
    conflictTitle: "Plik zmienił się na dysku",
    conflictText: "Ktoś zmienił {path} po wczytaniu go przez edytor.",
    overwrite: "Nadpisz moimi zmianami", discard: "Wczytaj plik (porzuć moje zmiany)",
    dirtyReload: "Masz niezapisane zmiany. Przeładowanie użyje zapisanego pliku.", saveAndReload: "Zapisz i przeładuj",
    reloadAnyway: "Przeładuj bez zapisu", dirtyLoad: "Porzucić niezapisane zmiany i wczytać plik?",
    comments: "Plik zawiera komentarze. Zapis z edytora je usunie (poprzedni plik zostaje jako .bak).",
    parseError: "Nie da się odczytać pliku: {error}. Popraw go w zakładce YAML.",
    yamlHelp: "Cały plik. Zastosuj YAML, żeby go sprawdzić i dalej edytować w formularzach.",
    applyYaml: "Zastosuj YAML", yamlApplied: "Zastosowano YAML.", preview: "Podgląd", noCards: "Brak kart.",
    none: "—", value: "Wartość", time: "Godzina", addRow: "Dodaj wiersz",
    removeRow: "Usuń", useSchedule: "Inna jasność zależnie od godziny", item: "Encja", inherited: "dziedziczone: {value}",
    notConfigured: "Integracja nie jest jeszcze skonfigurowana.", loading: "Wczytywanie…", type: "Typ karty",
    changeType: "Zmienić typ karty? Opcje starego typu zostaną w pliku.", issues: "Problemy",
    list: "Lista (po przecinku)", noPanels: "Brak paneli. Dodaj panel.", jsonHelp: "JSON albo wiersze klucz: wartość",
    pickIcon: "Wybierz ikonę", pickIconNow: "Wybierz ikonę (teraz: {icon})", pickIconDefault: "Wybierz ikonę (domyślna: {icon})",
    defaultIcon: "Domyślna: {icon}", iconSearch: "Szukaj po nazwie lub aliasie, np. lampa",
    iconCategory: "Kategoria", iconSuggested: "Sugerowane dla tej encji", iconRecent: "Ostatnio używane",
    iconAll: "Wszystkie ikony", iconCategories: "Kategorie", iconUseDefault: "Użyj domyślnej", iconClear: "Bez ustawionej ikony",
    iconMore: "Pokaż jeszcze {n}", iconNone: "Nie znaleziono ikon.", iconCount: "Ikony: {n}", iconRecentEmpty: "Brak ostatnio używanych ikon.",
    iconAliases: "też: {aliases}", iconFont: "Tylko ikony, które panel umie pokazać (MDI {version}).", iconDeprecated: "wycofana w MDI",
    iconTemplate: "szablon albo tekst – bez podglądu ikony",
  },
};

// MDI categories ("tags" in the MDI metadata) in Polish.
const ICON_TAGS_PL = {
  "Account / User": "Konto / użytkownik", "Agriculture": "Rolnictwo", "Alert / Error": "Alarm / błąd",
  "Alpha / Numeric": "Litery / cyfry", "Animal": "Zwierzęta", "Arrange": "Układanie", "Arrow": "Strzałki", "Audio": "Dźwięk",
  "Automotive": "Motoryzacja", "Banking": "Bankowość", "Battery": "Bateria", "Brand / Logo": "Marki / logo",
  "Cellphone / Phone": "Telefon", "Clothing": "Ubrania", "Cloud": "Chmura", "Color": "Kolor", "Currency": "Waluty",
  "Database": "Bazy danych", "Date / Time": "Data / czas", "Developer / Languages": "Programowanie",
  "Device / Tech": "Urządzenia / technika", "Drawing / Art": "Rysowanie / sztuka", "Edit / Modify": "Edycja",
  "Emoji": "Emoji", "Files / Folders": "Pliki / foldery", "Food / Drink": "Jedzenie / napoje", "Form": "Formularze",
  "Gaming / RPG": "Gry", "Geographic Information System": "Mapy (GIS)", "Hardware / Tools": "Narzędzia",
  "Health / Beauty": "Zdrowie / uroda", "Holiday": "Święta", "Home Automation": "Inteligentny dom", "Lock": "Zamki",
  "Math": "Matematyka", "Medical / Hospital": "Medycyna", "Music": "Muzyka", "Nature": "Przyroda", "Navigation": "Nawigacja",
  "Notification": "Powiadomienia", "People / Family": "Ludzie / rodzina", "Photography": "Fotografia", "Places": "Miejsca",
  "Printer": "Drukarki", "Religion": "Religia", "Science": "Nauka", "Settings": "Ustawienia", "Shape": "Kształty",
  "Shopping": "Zakupy", "Social Media": "Media społecznościowe", "Sport": "Sport", "Text / Content / Format": "Tekst / formatowanie",
  "Tooltip": "Dymki", "Transportation + Flying": "Transport lotniczy", "Transportation + Other": "Transport inny",
  "Transportation + Road": "Transport drogowy", "Transportation + Water": "Transport wodny", "Vector": "Wektory",
  "Video / Movie": "Wideo / film", "View": "Widok", "Weather": "Pogoda",
};

// Polish search words -> MDI words (icon names are English).
const ICON_WORDS_PL = {
  lampa: "lamp", lampka: "lamp", światło: "light", swiatlo: "light", żarówka: "bulb", zarowka: "bulb", oświetlenie: "light",
  gniazdko: "socket", gniazdo: "socket", wtyczka: "plug", włącznik: "switch", wlacznik: "switch", przełącznik: "switch",
  roleta: "blinds", rolety: "blinds", żaluzja: "blinds", zaslona: "curtains", zasłona: "curtains", brama: "gate",
  drzwi: "door", okno: "window", garaż: "garage", garaz: "garage", temperatura: "thermometer", termometr: "thermometer",
  wilgotność: "water-percent", wilgotnosc: "water-percent", wentylator: "fan", telewizor: "television", tv: "television",
  głośnik: "speaker", glosnik: "speaker", muzyka: "music", zamek: "lock", kłódka: "lock", kamera: "cctv", pogoda: "weather",
  słońce: "sun", slonce: "sun", deszcz: "rain", śnieg: "snow", snieg: "snow", chmura: "cloud", woda: "water", ogień: "fire",
  ogien: "fire", grzanie: "fire", grzejnik: "radiator", klimatyzacja: "air-conditioner", dom: "home", łóżko: "bed",
  lozko: "bed", kanapa: "sofa", prąd: "flash", prad: "flash", energia: "lightning-bolt", bateria: "battery",
  odkurzacz: "vacuum", pralka: "washing-machine", zmywarka: "dishwasher", lodówka: "fridge", lodowka: "fridge",
  piekarnik: "stove", kuchnia: "stove", lustro: "mirror", alarm: "alarm", ruch: "motion", czujnik: "sensor",
  samochód: "car", samochod: "car", rower: "bike", ogród: "flower", ogrod: "flower", kwiat: "flower", podlewanie: "sprinkler",
  basen: "pool", kot: "cat", pies: "dog", osoba: "account", człowiek: "account", wyjście: "exit", strzałka: "arrow",
};

// Search words for the "suggested" icons of a domain.
const DOMAIN_ICON_WORDS = {
  light: ["lightbulb", "lamp", "ceiling-light", "floor-lamp", "led-strip", "wall-sconce", "spotlight"],
  switch: ["light-switch", "power-socket", "power-plug", "toggle-switch", "lightbulb", "fan", "mirror"],
  input_boolean: ["toggle-switch", "check-circle", "power"], cover: ["blinds", "window-shutter", "curtains", "garage", "gate"],
  climate: ["thermostat", "radiator", "air-conditioner", "fire", "snowflake", "heat-pump"], fan: ["fan", "air-purifier"],
  sensor: ["thermometer", "water-percent", "gauge", "flash", "lightning-bolt", "battery", "molecule-co2"],
  binary_sensor: ["door", "window", "motion-sensor", "smoke-detector", "water-alert", "leak"],
  media_player: ["speaker", "television", "music", "cast", "radio"], lock: ["lock", "door"], vacuum: ["robot-vacuum"],
  scene: ["palette", "movie", "sofa", "bed", "weather-night"], script: ["script", "play", "gesture-tap"],
  button: ["gesture-tap-button", "button", "restart"], input_button: ["gesture-tap-button", "button"],
  weather: ["weather"], person: ["account", "human"], alarm_control_panel: ["shield", "bell"], camera: ["cctv", "camera"],
  sun: ["weather-sunset", "sun"], timer: ["timer"], number: ["ray-vertex", "numeric"], input_number: ["ray-vertex", "numeric"],
  select: ["format-list-bulleted"], input_select: ["format-list-bulleted"], navigate: ["arrow-right", "home", "chevron", "menu"],
  iText: ["information", "text"], service: ["script", "play", "gesture-tap"],
};
const RECENT_ICONS_KEY = "nspanel-editor-recent-icons";

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clone = (value) => (value === undefined || value === null ? value : JSON.parse(JSON.stringify(value)));
const pathKey = (path) => path.map(String).join("\u001f");
const iconName = (value) => (value ? (String(value).includes(":") ? String(value) : `mdi:${value}`) : "");

class NSPanelCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = { loading: true };
    this._undo = [];
    this._redo = [];
    this._issues = [];
    this._validateTimer = null;
    this._dragFrom = null;
    this._beforeUnload = (event) => {
      if (this._dirty) { event.preventDefault(); event.returnValue = ""; }
    };
    this.shadowRoot.addEventListener("keydown", (ev) => this._keys(ev));
  }

  // --- Home Assistant panel API ---------------------------------------------------------------
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
  }
  get hass() { return this._hass; }
  set narrow(value) { this._narrow = value; this.toggleAttribute("narrow", !!value); }
  set panel(value) { this._panel = value; }
  set route(value) { this._route = value; }

  connectedCallback() { window.addEventListener("beforeunload", this._beforeUnload); this._render(); }
  disconnectedCallback() { window.removeEventListener("beforeunload", this._beforeUnload); }

  // --- helpers ---------------------------------------------------------------------------------
  get _lang() { return (this._hass?.language || "en").startsWith("pl") ? "pl" : "en"; }
  t(key, params = {}) {
    let text = (UI[this._lang] && UI[this._lang][key]) || UI.en[key] || key;
    for (const [name, value] of Object.entries(params)) text = text.replaceAll(`{${name}}`, value);
    return text;
  }
  l(label) { return label ? (label[this._lang] || label.en || "") : ""; }
  ws(type, data = {}) { return this._hass.callWS({ type: `${DOMAIN}/editor/${type}`, ...data }); }
  get _dirty() { return this._config !== undefined && JSON.stringify(this._config) !== this._savedJson; }
  get _panelNames() { return Object.keys(this._config?.nspanels || {}); }
  get _panelConf() { return this._config.nspanels[this._panelName]; }

  _get(path) { return path.reduce((obj, key) => (obj == null ? undefined : obj[key]), this._config); }
  _set(path, value) {
    let obj = this._config;
    for (let i = 0; i < path.length - 1; i += 1) {
      if (obj[path[i]] == null || typeof obj[path[i]] !== "object") obj[path[i]] = typeof path[i + 1] === "number" ? [] : {};
      obj = obj[path[i]];
    }
    const last = path[path.length - 1];
    if (value === undefined) {
      if (Array.isArray(obj)) obj.splice(last, 1); else delete obj[last];
    } else obj[last] = value;
  }

  _snapshot() {
    this._undo.push(JSON.stringify(this._config));
    if (this._undo.length > 100) this._undo.shift();
    this._redo = [];
  }

  _changed({ render = false } = {}) {
    this._updateStatus();
    this._scheduleValidate();
    if (render) this._render();
  }

  // --- data ------------------------------------------------------------------------------------
  async _load(keepSelection = false) {
    this._state = { loading: true };
    this._render();
    try {
      const [file, schema] = await Promise.all([this.ws("load"), this._schema ? this._schema : this.ws("schema")]);
      this._schema = schema;
      this._file = file;
      this._config = clone(file.config) || { nspanels: {} };
      if (!this._config.nspanels || typeof this._config.nspanels !== "object") this._config.nspanels = {};
      this._savedJson = JSON.stringify(this._config);
      this._revision = file.revision;
      this._issues = file.issues || [];
      this._undo = []; this._redo = [];
      this._yamlText = file.yaml;
      if (!keepSelection || !this._panelNames.includes(this._panelName)) {
        this._panelName = this._panelNames[0];
        this._section = file.parse_error ? "yaml" : "cards";
        this._cardIndex = 0;
      }
      this._state = { loading: false };
    } catch (err) {
      this._state = { loading: false, fatal: err.code === "not_configured" ? this.t("notConfigured") : (err.message || String(err)) };
    }
    this._render();
  }

  _scheduleValidate() {
    clearTimeout(this._validateTimer);
    this._validateTimer = setTimeout(async () => {
      try {
        const result = await this.ws("validate", { config: this._config });
        this._issues = result.issues;
        this._showIssues();
      } catch (err) { /* offline: keep the last issues */ }
    }, 350);
  }

  async _save(force = false) {
    if (this._errorCount) { this._toast(this.t("errorsBlock"), "error"); return false; }
    this._busy(true, this.t("saving"));
    try {
      const result = await this.ws("save", { config: this._config, revision: this._revision, force });
      if (!result.saved && result.reason === "conflict") { this._busy(false); return this._conflict(); }
      if (!result.saved) {
        this._issues = result.issues; this._showIssues(); this._busy(false);
        this._toast(this.t("errorsBlock"), "error");
        return false;
      }
      this._revision = result.revision;
      this._savedJson = JSON.stringify(this._config);
      this._yamlText = result.yaml;
      this._file.has_comments = false;
      this._issues = result.issues;
      this._busy(false);
      this._render();
      this._toast(this.t("savedOk", { backup: result.backup }), "success", { label: this.t("reloadNow"), run: () => this._reload(true) });
      return true;
    } catch (err) {
      this._busy(false);
      this._toast(err.message || String(err), "error");
      return false;
    }
  }

  async _reload(skipCheck = false) {
    if (!skipCheck && this._dirty) {
      const choice = await this._dialog(this.t("reload"), this.t("dirtyReload"),
        [{ id: "reload", label: this.t("reloadAnyway") }, { id: "save", label: this.t("saveAndReload"), primary: true }]);
      if (choice === "save") { if (!(await this._save())) return; } else if (choice !== "reload") return;
    }
    this._busy(true, this.t("reload"));
    try {
      const result = await this.ws("reload");
      this._busy(false);
      if (result.reloaded) this._toast(this.t("reloadOk"), "success");
      else this._toast(this.t("reloadFailed", { reason: result.reason || result.state }), "error");
    } catch (err) {
      this._busy(false);
      this._toast(this.t("reloadFailed", { reason: err.message || err }), "error");
    }
  }

  async _conflict() {
    const choice = await this._dialog(this.t("conflictTitle"), this.t("conflictText", { path: this._file.path }),
      [{ id: "overwrite", label: this.t("overwrite") }, { id: "discard", label: this.t("discard"), primary: true }]);
    if (choice === "overwrite") return this._save(true);
    if (choice === "discard") await this._load(true);
    return false;
  }

  async _loadFromDisk() {
    if (this._dirty) {
      const choice = await this._dialog(this.t("fromDisk"), this.t("dirtyLoad"),
        [{ id: "yes", label: this.t("fromDisk"), primary: true }]);
      if (choice !== "yes") return;
    }
    await this._load(true);
  }

  _undoRedo(from, to) {
    if (!from.length) return;
    to.push(JSON.stringify(this._config));
    this._config = JSON.parse(from.pop());
    if (!this._panelNames.includes(this._panelName)) this._panelName = this._panelNames[0];
    this._changed({ render: true });
  }

  // --- issues ----------------------------------------------------------------------------------
  get _errorCount() { return this._issues.filter((i) => i.severity === "error").length; }
  _issueText(issue) {
    const msg = this._schema?.messages?.[issue.code];
    if (!msg) return issue.text;
    let text = this.l(msg);
    for (const [name, value] of Object.entries(issue.params || {})) text = text.replaceAll(`{${name}}`, value);
    return text;
  }
  _issuesUnder(prefix) {
    const key = pathKey(prefix);
    return this._issues.filter((i) => pathKey(i.path) === key || pathKey(i.path).startsWith(key + "\u001f"));
  }

  _showIssues() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-issue-for]").forEach((el) => {
      const own = this._issues.filter((i) => pathKey(i.path) === el.dataset.issueFor);
      el.innerHTML = own.map((i) => `<span class="${i.severity}">${esc(this._issueText(i))}</span>`).join("");
      const input = el.dataset.input ? root.getElementById(el.dataset.input) : null;
      if (input) input.setAttribute("aria-invalid", own.some((i) => i.severity === "error") ? "true" : "false");
      el.closest(".field")?.classList.toggle("has-error", own.some((i) => i.severity === "error"));
      el.closest(".field")?.classList.toggle("has-warning", own.some((i) => i.severity === "warning"));
    });
    root.querySelectorAll("[data-badge]").forEach((el) => {
      const found = this._issuesUnder(JSON.parse(el.dataset.badge));
      const errors = found.filter((i) => i.severity === "error").length;
      const warnings = found.length - errors;
      el.textContent = errors ? String(errors) : warnings ? "!" : "";
      el.className = `badge ${errors ? "error" : warnings ? "warning" : ""}`;
      el.title = errors ? this.t("errors", { n: errors }) : warnings ? this.t("warnings", { n: warnings }) : "";
    });
    this._updateStatus();
    const summary = root.getElementById("summary");
    if (summary) {
      summary.innerHTML = this._summaryHtml();
      summary.querySelectorAll("[data-action=goto]").forEach((el) =>
        el.addEventListener("click", () => this._goTo(this._issues[Number(el.dataset.index)])));
    }
  }

  _updateStatus() {
    const root = this.shadowRoot;
    const status = root.getElementById("status");
    if (status) {
      status.textContent = this._config === undefined ? "" : this._dirty ? this.t("unsaved") : this.t("noChanges");
      status.classList.toggle("dirty", this._dirty);
    }
    const save = root.getElementById("save");
    if (save) {
      save.disabled = !this._dirty || this._errorCount > 0;
      save.title = this._errorCount ? this.t("errorsBlock") : "Ctrl+S";
    }
    const undo = root.getElementById("undo");
    if (undo) undo.disabled = !this._undo.length;
    const redo = root.getElementById("redo");
    if (redo) redo.disabled = !this._redo.length;
  }

  _summaryHtml() {
    if (!this._issues.length) return "";
    const errors = this._errorCount;
    const warnings = this._issues.length - errors;
    const items = this._issues.slice(0, 50).map((issue, index) =>
      `<li class="${issue.severity}"><button class="link" data-action="goto" data-index="${index}">${esc(this._describePath(issue.path))}</button>: ${esc(this._issueText(issue))}</li>`).join("");
    return `<details ${errors ? "open" : ""}><summary>${esc(this.t("issues"))}: ${errors ? esc(this.t("errors", { n: errors })) : ""} ${warnings ? esc(this.t("warnings", { n: warnings })) : ""}</summary><ul>${items}</ul></details>`;
  }

  _describePath(path) {
    const parts = [];
    if (path[0] === "nspanels" && path.length > 1) {
      parts.push(path[1]);
      if (path[2] === "cards" || path[2] === "hiddenCards") {
        const card = this._get(path.slice(0, 4));
        parts.push(card?.title || card?.type || `#${(path[3] ?? 0) + 1}`);
        if (path[4] === "entities" && typeof path[5] === "number") parts.push(`${this.t("item")} ${path[5] + 1}`);
      } else if (path[2] === "screensaver") parts.push(this.t("screensaver"));
      else parts.push(this.t("settings"));
    } else parts.push(this.t("global"));
    const last = path[path.length - 1];
    if (typeof last === "string" && path.length > 2) parts.push(last);
    return parts.join(" › ");
  }

  _goTo(issue) {
    if (!issue) return;
    const path = issue.path;
    if (path[0] === "nspanels" && path.length > 1) {
      this._panelName = path[1];
      if (path[2] === "cards" || path[2] === "hiddenCards") { this._section = path[2]; this._cardIndex = path[3] ?? 0; }
      else if (path[2] === "screensaver") this._section = "screensaver";
      else this._section = "settings";
    } else this._section = "global";
    this._render();
    const input = this.shadowRoot.querySelector(`[data-path='${CSS.escape(JSON.stringify(path))}']`);
    if (input) {
      input.closest("details")?.setAttribute("open", "");
      input.focus();
      input.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  // --- rendering ------------------------------------------------------------------------------
  _render() {
    if (!this.shadowRoot) return;
    const s = this._state;
    let body;
    if (s.loading) body = `<div class="center" role="status">${esc(this.t("loading"))}</div>`;
    else if (s.fatal) body = `<div class="center"><p class="error-text" role="alert">${esc(s.fatal)}</p></div>`;
    else body = this._mainHtml();
    const ready = !s.loading && !s.fatal;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar" role="toolbar" aria-label="${esc(this.t("title"))}">
        ${this._narrow ? `<button class="icon" data-action="menu" aria-label="Menu"><ha-icon icon="mdi:menu"></ha-icon></button>` : ""}
        <h1>${esc(this.t("title"))}</h1>
        <span id="status" class="status" role="status" aria-live="polite"></span>
        <span class="spacer"></span>
        ${ready ? `
        <button class="icon" id="undo" data-action="undo" title="${esc(this.t("undo"))} (Ctrl+Z)" aria-label="${esc(this.t("undo"))}"><ha-icon icon="mdi:undo"></ha-icon></button>
        <button class="icon" id="redo" data-action="redo" title="${esc(this.t("redo"))} (Ctrl+Y)" aria-label="${esc(this.t("redo"))}"><ha-icon icon="mdi:redo"></ha-icon></button>
        <button class="icon" data-action="fromdisk" title="${esc(this.t("fromDisk"))}" aria-label="${esc(this.t("fromDisk"))}"><ha-icon icon="mdi:file-restore-outline"></ha-icon></button>
        <button class="secondary" data-action="reload"><ha-icon icon="mdi:reload"></ha-icon><span>${esc(this.t("reload"))}</span></button>
        <button class="primary" id="save" data-action="save"><ha-icon icon="mdi:content-save"></ha-icon><span>${esc(this.t("save"))}</span></button>` : ""}
      </div>
      <div class="busy" id="busy" hidden role="status" aria-live="polite"></div>
      ${body}
      <div class="toasts" id="toasts" aria-live="polite"></div>`;
    this._bind();
    if (ready) this._showIssues();
  }

  _mainHtml() {
    const banners = [];
    if (this._file?.parse_error) banners.push(`<div class="banner error" role="alert">${esc(this.t("parseError", { error: this._file.parse_error }))}</div>`);
    if (this._file?.has_comments) banners.push(`<div class="banner warning">${esc(this.t("comments"))}</div>`);
    const panels = this._panelNames;
    const panelOptions = panels.map((name) => `<option value="${esc(name)}" ${name === this._panelName ? "selected" : ""}>${esc(name)}</option>`).join("");
    const sections = [
      ["cards", "mdi:cards-outline", this.t("cards")], ["hiddenCards", "mdi:eye-off-outline", this.t("hiddenCards")],
      ["screensaver", "mdi:weather-partly-cloudy", this.t("screensaver")], ["settings", "mdi:tune", this.t("settings")],
      ["global", "mdi:earth", this.t("global")], ["yaml", "mdi:code-braces", this.t("yaml")],
    ];
    const nav = sections.map(([id, icon, label]) => {
      const disabled = !this._panelName && !["global", "yaml"].includes(id);
      const badgePath = id === "global" ? null : id === "yaml" ? null : ["nspanels", this._panelName, ...(id === "settings" ? [] : [id])];
      const badge = badgePath && this._panelName ? `<span data-badge='${esc(JSON.stringify(badgePath))}'></span>` : "";
      return `<button class="nav ${this._section === id ? "active" : ""}" data-action="section" data-section="${id}" ${disabled ? "disabled" : ""} aria-current="${this._section === id ? "page" : "false"}"><ha-icon icon="${icon}"></ha-icon><span class="label">${esc(label)}</span>${badge}</button>`;
    }).join("");
    let content;
    if (!this._panelName && !["global", "yaml"].includes(this._section)) content = `<p class="empty">${esc(this.t("noPanels"))}</p>`;
    else if (this._section === "yaml") content = this._yamlHtml();
    else if (this._section === "global") content = this._formHtml(this._schema.global, [], this._config);
    else if (this._section === "settings") content = this._formHtml(this._schema.panel, ["nspanels", this._panelName], this._panelConf, this._config);
    else if (this._section === "screensaver") content = this._screensaverHtml();
    else content = this._cardsHtml(this._section);
    return `${banners.join("")}
      <div class="layout">
        <aside class="side">
          <div class="panel-select">
            <label for="panel">${esc(this.t("panel"))}</label>
            <div class="row">
              <select id="panel" data-action="panel">${panelOptions}</select>
              <button class="icon" data-action="add-panel" title="${esc(this.t("addPanel"))}" aria-label="${esc(this.t("addPanel"))}"><ha-icon icon="mdi:plus"></ha-icon></button>
              ${this._panelName ? `<button class="icon" data-action="delete-panel" title="${esc(this.t("deletePanel"))}" aria-label="${esc(this.t("deletePanel"))}"><ha-icon icon="mdi:delete-outline"></ha-icon></button>` : ""}
            </div>
          </div>
          <nav aria-label="${esc(this.t("panel"))}">${nav}</nav>
          <div id="summary" class="summary"></div>
        </aside>
        <main class="content ${["cards", "hiddenCards"].includes(this._section) && this._panelName ? "plain" : ""}">${content}</main>
      </div>`;
  }

  // Cards ---------------------------------------------------------------------------------------
  _cardsHtml(listKey) {
    const cards = Array.isArray(this._panelConf[listKey]) ? this._panelConf[listKey] : [];
    if (this._cardIndex >= cards.length) this._cardIndex = Math.max(0, cards.length - 1);
    const items = cards.map((card, index) => {
      const spec = this._schema.cards[card?.type] || {};
      const base = ["nspanels", this._panelName, listKey, index];
      return `<li class="card-item ${index === this._cardIndex ? "active" : ""}" draggable="true" data-index="${index}">
          <span class="handle" title="${esc(this.t("drag"))}" aria-hidden="true"><ha-icon icon="mdi:drag"></ha-icon></span>
          <button class="card-select" data-action="card" data-index="${index}" aria-current="${index === this._cardIndex}" aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown">
            <ha-icon icon="${esc(spec.icon || "mdi:card-outline")}"></ha-icon>
            <span class="card-name"><span>${esc(card?.title || this.l(spec.label) || card?.type || "?")}</span><small>${esc(this.l(spec.label) || card?.type)}${card?.key ? ` · ${esc(card.key)}` : ""}</small></span>
            <span data-badge='${esc(JSON.stringify(base))}'></span>
          </button>
          <span class="item-actions">
            <button class="icon small" data-action="card-up" data-index="${index}" aria-label="${esc(this.t("moveUp"))}" title="${esc(this.t("moveUp"))}" ${index === 0 ? "disabled" : ""}><ha-icon icon="mdi:arrow-up"></ha-icon></button>
            <button class="icon small" data-action="card-down" data-index="${index}" aria-label="${esc(this.t("moveDown"))}" title="${esc(this.t("moveDown"))}" ${index === cards.length - 1 ? "disabled" : ""}><ha-icon icon="mdi:arrow-down"></ha-icon></button>
            <button class="icon small" data-action="card-duplicate" data-index="${index}" aria-label="${esc(this.t("duplicate"))}" title="${esc(this.t("duplicate"))}"><ha-icon icon="mdi:content-copy"></ha-icon></button>
            <button class="icon small" data-action="card-delete" data-index="${index}" aria-label="${esc(this.t("delete"))}" title="${esc(this.t("delete"))}"><ha-icon icon="mdi:delete-outline"></ha-icon></button>
          </span>
        </li>`;
    }).join("");
    const card = cards[this._cardIndex];
    const editor = card ? this._cardEditorHtml(listKey, this._cardIndex, card) : `<p class="empty">${esc(this.t("noCards"))}</p>`;
    return `<div class="cards">
        <section class="card-list" aria-label="${esc(this.t(listKey))}">
          <ol data-list="${listKey}">${items}</ol>
          <button class="secondary wide" data-action="add-card" data-list="${listKey}"><ha-icon icon="mdi:plus"></ha-icon><span>${esc(this.t("addCard"))}</span></button>
          <div data-issue-for="${esc(pathKey(["nspanels", this._panelName, listKey]))}" class="issues"></div>
        </section>
        <section class="card-editor">${editor}</section>
      </div>`;
  }

  _cardEditorHtml(listKey, index, card) {
    const base = ["nspanels", this._panelName, listKey, index];
    const spec = this._schema.cards[card.type];
    const typeOptions = this._schema.card_types.map((type) =>
      `<option value="${type}" ${type === card.type ? "selected" : ""}>${esc(this.l(this._schema.cards[type].label))}</option>`).join("");
    let html = `<div class="field"><label for="card-type">${esc(this.t("type"))}</label>
      <select id="card-type" data-action="card-type" data-path='${esc(JSON.stringify([...base, "type"]))}'>${spec ? "" : `<option selected>${esc(card.type)}</option>`}${typeOptions}</select>
      <div class="issues" data-issue-for="${esc(pathKey([...base, "type"]))}" data-input="card-type"></div></div>`;
    if (!spec) return html;
    html += this._formHtml(spec.fields, base, card, null, card.type);
    if (spec.items) html += this._itemsHtml([...base, "entities"], card.entities || [], card.type);
    html += `<section class="preview" aria-label="${esc(this.t("preview"))}"><h3>${esc(this.t("preview"))}</h3>${this._previewHtml(card)}</section>`;
    return html;
  }

  _itemsHtml(path, items, context) {
    const list = Array.isArray(items) ? items : [];
    const rows = list.map((item, index) => {
      const itemPath = [...path, index];
      const entity = typeof item?.entity === "string" ? item.entity : "";
      const domain = entity.includes(".") ? entity.split(".")[0] : "";
      const state = this._hass.states[entity];
      const extra = this._schema.item.filter((f) => !["entity", "name", "icon"].includes(f.key) && this._applies(f, context, domain, entity));
      const open = extra.some((f) => item?.[f.key] !== undefined) ? "open" : "";
      return `<li class="entity-row" draggable="true" data-index="${index}" data-items='${esc(JSON.stringify(path))}'>
          <div class="entity-main">
            <span class="handle" title="${esc(this.t("drag"))}" aria-hidden="true"><ha-icon icon="mdi:drag"></ha-icon></span>
            ${this._inputHtml(this._schema.item[0], [...itemPath, "entity"], entity, context)}
            ${this._inputHtml(this._schema.item[1], [...itemPath, "name"], item?.name, context, state?.attributes?.friendly_name || "")}
            ${this._inputHtml(this._schema.item[2], [...itemPath, "icon"], item?.icon, context)}
            <span class="item-actions">
              <button class="icon small" data-action="item-up" data-index="${index}" data-items='${esc(JSON.stringify(path))}' aria-label="${esc(this.t("moveUp"))}" title="${esc(this.t("moveUp"))}" ${index === 0 ? "disabled" : ""}><ha-icon icon="mdi:arrow-up"></ha-icon></button>
              <button class="icon small" data-action="item-down" data-index="${index}" data-items='${esc(JSON.stringify(path))}' aria-label="${esc(this.t("moveDown"))}" title="${esc(this.t("moveDown"))}" ${index === list.length - 1 ? "disabled" : ""}><ha-icon icon="mdi:arrow-down"></ha-icon></button>
              <button class="icon small" data-action="item-delete" data-index="${index}" data-items='${esc(JSON.stringify(path))}' aria-label="${esc(this.t("delete"))}" title="${esc(this.t("delete"))}"><ha-icon icon="mdi:close"></ha-icon></button>
            </span>
          </div>
          <div class="issues" data-issue-for="${esc(pathKey([...itemPath, "entity"]))}" data-input="${this._id([...itemPath, "entity"])}"></div>
          <div class="issues" data-issue-for="${esc(pathKey([...itemPath, "icon"]))}"></div>
          ${extra.length ? `<details ${open}><summary>${esc(this.t("more"))}</summary><div class="grid">${extra.map((f) => this._fieldHtml(f, [...itemPath, f.key], item?.[f.key], null, context)).join("")}</div></details>` : ""}
        </li>`;
    }).join("");
    return `<fieldset class="items"><legend>${esc(this.t("entities"))} <span data-badge='${esc(JSON.stringify(path))}'></span></legend>
        <ol>${rows}</ol>
        <button class="secondary" data-action="item-add" data-items='${esc(JSON.stringify(path))}'><ha-icon icon="mdi:plus"></ha-icon><span>${esc(this.t("addEntity"))}</span></button>
        <div class="issues" data-issue-for="${esc(pathKey(path))}"></div>
      </fieldset>`;
  }

  _applies(field, context, domain, entity) {
    if (field.cards && !field.cards.includes(context)) return false;
    if (field.weather && domain !== "weather") return false;
    if (field.domains && !field.domains.includes(domain)) return false;
    if (field.pseudo_only && !entity.startsWith(field.pseudo_only)) return false;
    return true;
  }

  _screensaverHtml() {
    const base = ["nspanels", this._panelName, "screensaver"];
    const screensaver = this._panelConf.screensaver || {};
    return `${this._formHtml(this._schema.screensaver, base, screensaver, null, "statusIcon")}
      ${this._itemsHtml([...base, "entities"], screensaver.entities || [], "screensaver")}`;
  }

  // Forms ---------------------------------------------------------------------------------------
  _id(path) { return `f-${pathKey(path).replace(/[^a-zA-Z0-9]/g, "_")}`; }

  _formHtml(fields, base, data, inherited = null, context = null) {
    const basic = fields.filter((f) => !f.advanced);
    const advanced = fields.filter((f) => f.advanced);
    const render = (list) => list.map((f) => this._fieldHtml(f, [...base, f.key], data?.[f.key], inherited, context)).join("");
    const open = advanced.some((f) => data?.[f.key] !== undefined) ? "open" : "";
    return `<div class="grid">${render(basic)}</div>
      ${advanced.length ? `<details class="advanced" ${open}><summary>${esc(this.t("advanced"))}</summary><div class="grid">${render(advanced)}</div></details>` : ""}`;
  }

  _fieldHtml(field, path, value, inherited, context) {
    const id = this._id(path);
    const help = field.help ? `<small class="help" id="${id}-help">${esc(this.l(field.help))}</small>` : "";
    const inheritedValue = field.inherit && inherited && value === undefined ? inherited[field.key] : undefined;
    const placeholder = inheritedValue !== undefined ? this.t("inherited", { value: inheritedValue })
      : (field.default !== undefined && typeof field.default !== "object" ? String(field.default) : "");
    const group = ["multiselect", "item", "theme", "override"].includes(field.kind);
    const label = group ? `<span class="label" id="${id}-label">${esc(this.l(field.label))}</span>`
      : `<label for="${id}">${esc(this.l(field.label))}${field.required ? ' <span class="req" aria-hidden="true">*</span>' : ""}</label>`;
    const wide = ["item", "theme", "brightness", "multiselect", "override", "mapping"].includes(field.kind) ? " wide" : "";
    return `<div class="field${wide}">${label}${this._inputHtml(field, path, value, context, placeholder, true)}${help}
        <div class="issues" data-issue-for="${esc(pathKey(path))}" data-input="${id}" id="${id}-issues"></div></div>`;
  }

  _inputHtml(field, path, value, context, placeholder = "", labelled = false) {
    const id = this._id(path);
    const label = labelled ? "" : `aria-label="${esc(this.l(field.label))}"`;
    const data = `id="${id}" data-path='${esc(JSON.stringify(path))}' data-kind="${field.kind}" aria-describedby="${id}-issues${field.help ? ` ${id}-help` : ""}" ${field.required ? 'aria-required="true"' : ""} ${label}`;
    switch (field.kind) {
      case "bool":
        return `<input type="checkbox" role="switch" ${data} ${value === true || (value === undefined && field.default === true) ? "checked" : ""}>`;
      case "int":
        return `<input type="number" step="1" inputmode="numeric" ${field.min !== undefined ? `min="${field.min}"` : ""} ${field.max !== undefined ? `max="${field.max}"` : ""} value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" ${data}>`;
      case "select": {
        const options = field.options.map((o) => `<option value="${esc(o.value)}" ${o.value === value ? "selected" : ""}>${esc(this.l(o.label))}</option>`).join("");
        const unknown = value !== undefined && !field.options.some((o) => o.value === value) ? `<option value="${esc(value)}" selected>${esc(value)}</option>` : "";
        const defaultLabel = field.options.find((o) => o.value === field.default);
        return `<select ${data}><option value="">${esc(defaultLabel ? `(${this.l(defaultLabel.label)})` : this.t("none"))}</option>${unknown}${options}</select>`;
      }
      case "multiselect": {
        const current = Array.isArray(value) ? value : [];
        return `<div class="checks" role="group" aria-labelledby="${id}-label" id="${id}">${field.options.map((o) => `<label><input type="checkbox" data-path='${esc(JSON.stringify(path))}' data-kind="multiselect" data-value="${esc(o.value)}" ${current.includes(o.value) ? "checked" : ""}>${esc(this.l(o.label))}</label>`).join("")}</div>`;
      }
      case "navigate": {
        const keys = [...(this._panelConf?.cards || []), ...(this._panelConf?.hiddenCards || [])].filter((c) => c && c.key).map((c) => c.key);
        const options = keys.map((k) => `<option value="navigate.${esc(k)}" ${value === `navigate.${k}` ? "selected" : ""}>${esc(k)}</option>`).join("");
        const unknown = value && !keys.some((k) => value === `navigate.${k}`) ? `<option value="${esc(value)}" selected>${esc(value)}</option>` : "";
        return `<select ${data}><option value="">${esc(this.t("none"))}</option>${unknown}${options}</select>`;
      }
      case "entity": {
        const list = this._entityList(field.domains, field.pseudo);
        return `<input type="text" list="${list}" autocomplete="off" spellcheck="false" value="${esc(value ?? "")}" placeholder="${esc(placeholder || (field.domains ? `${field.domains[0]}.…` : "light.…"))}" ${data}>`;
      }
      case "icon": {
        if (value && typeof value === "object") return `<textarea rows="3" data-json="1" ${data}>${esc(JSON.stringify(value, null, 1))}</textarea>`;
        // Preview button (opens the picker) + text field with suggestions. Every icon field belongs
        // to an item, so the default icon comes from the item's entity.
        const owner = this._get([...path.slice(0, -1), "entity"]);
        const entity = typeof owner === "string" ? owner : "";
        const text = value === undefined || value === null ? "" : String(value);
        const def = this._defaultIcons?.get(entity);
        return `<span class="icon-input ${text ? "" : "is-default"}">
          <button type="button" class="icon-pick" data-action="pick-icon" data-target="${id}" aria-haspopup="dialog" title="${esc(this._pickTitle(text, def))}" aria-label="${esc(this._pickTitle(text, def))}"><ha-icon icon="${esc(this._iconPreview(text, def))}"></ha-icon></button>
          <span class="combo"><input type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${id}-list" autocomplete="off" spellcheck="false" value="${esc(text)}" placeholder="${esc(def ? this.t("defaultIcon", { icon: def }) : "mdi:…")}" ${data} data-icons="1" data-entity="${esc(entity)}">
          <ul class="suggest" id="${id}-list" role="listbox" hidden></ul></span></span>`;
      }
      case "color": {
        const hex = this._toHex(value);
        const text = Array.isArray(value) ? `[${value.join(", ")}]` : value && typeof value === "object" ? JSON.stringify(value) : value ?? "";
        return `<span class="color-input"><input type="color" value="${hex || "#ffffff"}" data-path='${esc(JSON.stringify(path))}' data-kind="color-picker" aria-label="${esc(this.l(field.label))}"><input type="text" value="${esc(text)}" placeholder="[255, 255, 255]" ${data}></span>`;
      }
      case "template":
        return `<textarea rows="${String(value ?? "").includes("\n") ? 3 : 1}" spellcheck="false" placeholder="${esc(placeholder)}" ${data}>${esc(value ?? "")}</textarea>`;
      case "strings":
        return `<input type="text" value="${esc(Array.isArray(value) ? value.join(", ") : value ?? "")}" placeholder="${esc(Array.isArray(field.default) ? field.default.join(", ") : this.t("list"))}" ${data}>`;
      case "brightness":
        return this._brightnessHtml(field, path, value, data, placeholder);
      case "item":
        return this._nestedItemHtml(field, path, value, context);
      case "theme":
        return `<div class="grid theme" role="group" aria-labelledby="${id}-label">${field.keys.map((k) => this._fieldHtml({ key: k, kind: "color", label: { en: k, pl: k } }, [...path, k], value?.[k], null, null)).join("")}</div>`;
      case "override":
        return `<div class="grid" role="group" aria-labelledby="${id}-label">${this._fieldHtml({ key: "entity", kind: "entity", label: { en: "Entity", pl: "Encja" } }, [...path, "entity"], value?.entity)}${this._fieldHtml({ key: "brightness", kind: "int", min: 0, max: 100, label: { en: "Brightness", pl: "Jasność" } }, [...path, "brightness"], value?.brightness)}</div>`;
      case "mapping":
        return `<textarea rows="3" spellcheck="false" data-json="1" placeholder="${esc(this.t("jsonHelp"))}" ${data}>${esc(value === undefined ? "" : JSON.stringify(value, null, 1))}</textarea>`;
      default:
        return `<input type="text" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" ${data}>`;
    }
  }

  _nestedItemHtml(field, path, value, context) {
    const item = value && typeof value === "object" ? value : {};
    const entity = typeof item.entity === "string" ? item.entity : "";
    const domain = entity.includes(".") ? entity.split(".")[0] : "";
    const fields = this._schema.item.filter((f) => ["entity", "name", "icon", "color"].includes(f.key) || this._applies(f, context, domain, entity));
    return `<div class="nested grid" role="group" aria-labelledby="${this._id(path)}-label">${fields.map((f) => this._fieldHtml(f.key === "entity" ? { ...f, required: !field.entity_optional } : f, [...path, f.key], item[f.key], null, context)).join("")}</div>`;
  }

  _brightnessHtml(field, path, value, data, placeholder) {
    const toggle = (checked) => `<label class="inline"><input type="checkbox" ${checked ? "checked" : ""} data-action="schedule-toggle" data-path='${esc(JSON.stringify(path))}' data-default="${field.default}">${esc(this.t("useSchedule"))}</label>`;
    if (Array.isArray(value)) {
      const rows = value.map((row, index) => `<li><input type="text" aria-label="${esc(this.t("time"))}" placeholder="07:30 / sunset + 1:00:00" value="${esc(row?.time ?? "")}" data-path='${esc(JSON.stringify([...path, index, "time"]))}' data-kind="string">
          <input type="number" min="0" max="100" aria-label="${esc(this.t("value"))}" value="${esc(row?.value ?? "")}" data-path='${esc(JSON.stringify([...path, index, "value"]))}' data-kind="int">
          <button class="icon small" data-action="row-delete" data-row='${esc(JSON.stringify([...path, index]))}' aria-label="${esc(this.t("removeRow"))}" title="${esc(this.t("removeRow"))}"><ha-icon icon="mdi:close"></ha-icon></button></li>`).join("");
      return `<div class="schedule" id="${this._id(path)}">${toggle(true)}<ol>${rows}</ol>
        <button class="secondary" data-action="row-add" data-row='${esc(JSON.stringify(path))}'><ha-icon icon="mdi:plus"></ha-icon><span>${esc(this.t("addRow"))}</span></button></div>`;
    }
    if (typeof value === "string") return `<input type="text" value="${esc(value)}" ${data}>`;
    const shown = typeof value === "number" ? value : field.default;
    return `<div class="schedule"><div class="range"><input type="range" min="0" max="100" value="${shown}" ${data} data-output="1"><output>${shown}%${typeof value === "number" ? "" : ` (${esc(placeholder)})`}</output></div>${toggle(false)}</div>`;
  }

  _yamlHtml() {
    return `<div class="yaml"><p class="help">${esc(this.t("yamlHelp"))}</p>
      <label for="yaml" class="sr-only">YAML</label>
      <textarea id="yaml" spellcheck="false" rows="28">${esc(this._yamlText || "")}</textarea>
      <div class="row"><button class="primary" data-action="apply-yaml"><ha-icon icon="mdi:check"></ha-icon><span>${esc(this.t("applyYaml"))}</span></button></div>
      <div class="issues" id="yaml-error" role="alert"></div></div>`;
  }

  _previewHtml(card) {
    const rows = (Array.isArray(card.entities) ? card.entities : []).slice(0, card.type === "cardGrid" ? 6 : 4).map((item) => {
      const entity = typeof item?.entity === "string" ? item.entity : "";
      const state = this._hass.states[entity];
      let name = item?.name || state?.attributes?.friendly_name || entity;
      if (entity.startsWith("navigate.")) name = item?.name || entity.slice(9);
      if (entity.startsWith("iText.")) name = entity.slice(6);
      if (entity === "delete") return `<div class="p-row empty"></div>`;
      const own = typeof item?.icon === "string" && item.icon ? item.icon : "";
      const icon = this._iconPreview(own, this._defaultIcons?.get(entity)).replace("mdi:shape-plus-outline", "mdi:checkbox-blank-circle-outline");
      return `<div class="p-row"><span class="p-icon"><ha-icon icon="${esc(icon)}" ${own ? `data-own-icon="${esc(own)}"` : `data-default-icon-for="${esc(entity)}"`}></ha-icon></span><span class="p-name">${esc(typeof name === "string" ? name : "")}</span><span class="p-state">${esc(state ? state.state : "")}</span></div>`;
    }).join("");
    const main = card.entity ? this._hass.states[card.entity] : null;
    const body = card.type === "cardQR" ? `<div class="p-qr"><ha-icon icon="mdi:qrcode"></ha-icon></div>${rows}`
      : main ? `<div class="p-big">${esc(main.attributes.friendly_name || card.entity)}<small>${esc(main.state)}</small></div>${rows}`
        : rows;
    return `<div class="screen ${card.type === "cardGrid" ? "grid-screen" : ""}" aria-hidden="true"><div class="p-title">${esc(card.title || "")}</div><div class="p-body">${body}</div></div>`;
  }

  // Input lists ---------------------------------------------------------------------------------
  _entityList(domains, pseudo) {
    const id = `nsp-entities-${(domains || ["all"]).join("-")}${pseudo ? "-p" : ""}`;
    if (!this._lists) this._lists = new Map();
    this._lists.set(id, { domains, pseudo });
    return id;
  }

  _fillDatalists() {
    const root = this.shadowRoot;
    for (const [id, { domains, pseudo }] of this._lists || []) {
      const list = document.createElement("datalist");
      list.id = id;
      const ids = Object.keys(this._hass.states).filter((e) => !domains || domains.includes(e.split(".")[0])).sort();
      const keys = pseudo ? [...(this._panelConf?.cards || []), ...(this._panelConf?.hiddenCards || [])].filter((c) => c && c.key).map((c) => `navigate.${c.key}`) : [];
      const extra = pseudo ? ["delete", ...keys, "navigate.UP", "iText.", "service."] : [];
      list.innerHTML = [...extra, ...ids].map((e) => `<option value="${esc(e)}">${esc(this._hass.states[e]?.attributes?.friendly_name || "")}</option>`).join("");
      root.appendChild(list);
    }
  }

  // Icons ---------------------------------------------------------------------------------------
  /** Icon to show for a field value: the icon, the entity's default, or a marker for templates/unknown. */
  _iconPreview(value, def) {
    const text = String(value ?? "").trim();
    if (!text) return def ? `mdi:${def}` : "mdi:shape-plus-outline";
    if (/^(ha|text):/.test(text)) return "mdi:code-braces";
    const name = text.replace(/^mdi:/, "");
    // The panel shows alert-circle-outline for names its font does not have.
    if (this._icons && !this._icons.known.has(name)) return "mdi:alert-circle-outline";
    return iconName(text);
  }

  _pickTitle(value, def) {
    if (value) return this.t("pickIconNow", { icon: value });
    return def ? this.t("pickIconDefault", { icon: def }) : this.t("pickIcon");
  }

  /** Picker data (every icon of the panel font), loaded once. */
  _iconData() {
    if (!this._iconsPromise) {
      this._iconsPromise = this.ws("icons").then((data) => {
        const tagText = (index) => {
          const tag = data.tags[index];
          return `${tag} ${ICON_TAGS_PL[tag] || ""}`.toLowerCase();
        };
        const rows = data.icons.map(([name, aliases, tags, deprecated]) => ({
          name, aliases, tags, deprecated: !!deprecated, tagText: tags.map(tagText).join(" ") }));
        const known = new Set();
        rows.forEach((row) => { known.add(row.name); row.aliases.split(" ").filter(Boolean).forEach((a) => known.add(a)); });
        this._icons = { mdi: data.mdi, tags: data.tags, rows, known, byName: new Map(rows.map((row) => [row.name, row])) };
        return this._icons;
      }).catch((err) => { this._iconsPromise = null; throw err; });
    }
    return this._iconsPromise;
  }

  /** Icons matching every word of the query (name, then aliases, then category), best first. */
  _searchIcons(data, query, limit = Infinity, tag = null) {
    const words = query.toLowerCase().replace(/^mdi:/, "").split(/\s+/).filter(Boolean)
      .map((word) => [word, ICON_WORDS_PL[word]].filter(Boolean));
    if (!words.length) return [];
    const hits = [];
    for (const row of data.rows) {
      if (tag !== null && !row.tags.includes(tag)) continue;
      let score = row.deprecated ? 10 : 0;
      for (const options of words) {
        let best = -1;
        for (const word of options) {
          const s = row.name === word ? 0 : row.name.startsWith(word) ? 1 : row.name.includes(word) ? 2
            : row.aliases.includes(word) ? 3 : row.tagText.includes(word) ? 5 : -1;
          if (s >= 0 && (best < 0 || s < best)) best = s;
        }
        if (best < 0) { score = -1; break; }
        score += best;
      }
      if (score >= 0) hits.push([score, row]);
    }
    hits.sort((a, b) => a[0] - b[0] || a[1].name.length - b[1].name.length || a[1].name.localeCompare(b[1].name));
    return hits.slice(0, limit).map((hit) => hit[1]);
  }

  _suggestedIcons(data, entity, def) {
    const domain = entity.startsWith("navigate.") ? "navigate" : entity.startsWith("iText.") ? "iText" : entity.split(".")[0];
    const names = new Set(def ? [def] : []);
    for (const word of DOMAIN_ICON_WORDS[domain] || ["home"]) {
      this._searchIcons(data, word, 16).forEach((row) => names.add(row.name));
    }
    return [...names].map((name) => data.byName.get(name)).filter(Boolean);
  }

  _recentIcons() {
    try { return JSON.parse(localStorage.getItem(RECENT_ICONS_KEY) || "[]").filter((n) => typeof n === "string"); } catch (err) { return []; }
  }

  _rememberIcon(name) {
    try { localStorage.setItem(RECENT_ICONS_KEY, JSON.stringify([name, ...this._recentIcons().filter((n) => n !== name)].slice(0, 32))); } catch (err) { /* private mode */ }
  }

  /** Default icons (what the panel shows without an icon) for the entities on screen. */
  async _loadDefaultIcons() {
    const root = this.shadowRoot;
    const ids = new Set();
    root.querySelectorAll("input[data-icons]").forEach((el) => { if (el.dataset.entity) ids.add(el.dataset.entity); });
    root.querySelectorAll("[data-default-icon-for]").forEach((el) => { if (el.dataset.defaultIconFor) ids.add(el.dataset.defaultIconFor); });
    if (!ids.size) return;
    let icons;
    try { icons = (await this.ws("default_icons", { entities: [...ids] })).icons; } catch (err) { return; }
    if (!this._defaultIcons) this._defaultIcons = new Map();
    for (const [id, name] of Object.entries(icons)) this._defaultIcons.set(id, name);
    root.querySelectorAll("input[data-icons]").forEach((el) => this._updateIconField(el));
    root.querySelectorAll("[data-default-icon-for]").forEach((el) => {
      const name = this._defaultIcons.get(el.dataset.defaultIconFor);
      if (name) el.setAttribute("icon", `mdi:${name}`);
    });
  }

  /** Refresh the preview button, placeholder and state of an icon field after a change. */
  _updateIconField(el) {
    const wrap = el.closest(".icon-input");
    if (!wrap) return;
    const def = this._defaultIcons?.get(el.dataset.entity);
    const text = el.value.trim();
    const name = text.replace(/^mdi:/, "");
    wrap.classList.toggle("is-default", !text);
    wrap.classList.toggle("unknown", !!(text && this._icons && !/^(ha|text):/.test(text) && !this._icons.known.has(name)));
    const button = wrap.querySelector(".icon-pick");
    button.querySelector("ha-icon").setAttribute("icon", this._iconPreview(text, def));
    button.title = this._pickTitle(text, def);
    button.setAttribute("aria-label", button.title);
    el.placeholder = def ? this.t("defaultIcon", { icon: def }) : "mdi:…";
  }

  /** Set an icon field as if typed (records undo, validates); "" = use the default. */
  _setIconValue(el, name) {
    el.value = name ? `mdi:${name}` : "";
    if (name) this._rememberIcon(name);
    // Undo goes back to before this edit (also before the typed part of a picked suggestion).
    if (this._pendingSnapshot === undefined) this._pendingSnapshot = JSON.stringify(this._config);
    el.dispatchEvent(new Event("input"));
    el.dispatchEvent(new Event("change"));
    this._closeSuggest(el);
  }

  // Suggestions under the text field (combobox) -------------------------------------------------
  async _suggest(el) {
    const query = el.value.trim();
    if (!query || /^(ha|text):/.test(query)) { this._closeSuggest(el); return; }
    let data;
    try { data = await this._iconData(); } catch (err) { return; }
    if (this.shadowRoot.activeElement !== el || el.value.trim() !== query) return;
    this._updateIconField(el);
    const hits = this._searchIcons(data, query, 8);
    const list = this.shadowRoot.getElementById(`${el.id}-list`);
    if (!list) return;
    if (!hits.length || (hits.length === 1 && `mdi:${hits[0].name}` === query)) { this._closeSuggest(el); return; }
    list.innerHTML = hits.map((row, i) => `<li role="option" id="${el.id}-opt-${i}" data-name="${esc(row.name)}" aria-selected="false"><ha-icon icon="mdi:${esc(row.name)}"></ha-icon><span>${esc(row.name)}</span></li>`).join("");
    list.hidden = false;
    el.setAttribute("aria-expanded", "true");
    el.removeAttribute("aria-activedescendant");
  }

  _closeSuggest(el) {
    const list = this.shadowRoot.getElementById(`${el.id}-list`);
    if (list) { list.hidden = true; list.innerHTML = ""; }
    el.setAttribute("aria-expanded", "false");
    el.removeAttribute("aria-activedescendant");
  }

  _suggestKeys(el, ev) {
    const list = this.shadowRoot.getElementById(`${el.id}-list`);
    const open = list && !list.hidden;
    if (!open) {
      if (ev.key === "ArrowDown" && el.value.trim()) { ev.preventDefault(); this._suggest(el); }
      return;
    }
    const options = [...list.querySelectorAll("li")];
    let index = options.findIndex((li) => li.getAttribute("aria-selected") === "true");
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      index = ev.key === "ArrowDown" ? (index + 1) % options.length : (index <= 0 ? options.length - 1 : index - 1);
      options.forEach((li, i) => li.setAttribute("aria-selected", String(i === index)));
      el.setAttribute("aria-activedescendant", options[index].id);
      options[index].scrollIntoView({ block: "nearest" });
    } else if (ev.key === "Enter" && index >= 0) {
      ev.preventDefault();
      this._setIconValue(el, options[index].dataset.name);
    } else if (ev.key === "Escape") {
      ev.preventDefault(); ev.stopPropagation();
      this._closeSuggest(el);
    }
  }

  // Picker dialog --------------------------------------------------------------------------------
  async _openIconPicker(input) {
    if (!input) return;
    const opener = input.closest(".icon-input")?.querySelector(".icon-pick");
    const entity = input.dataset.entity || "";
    const def = this._defaultIcons?.get(entity);
    const current = input.value.trim().replace(/^mdi:/, "");
    const dialog = document.createElement("dialog");
    dialog.className = "icon-dialog";
    dialog.setAttribute("aria-labelledby", "ip-title");
    dialog.innerHTML = `<div class="ip-head"><h2 id="ip-title">${esc(this.t("pickIcon"))}</h2>
        <button class="icon" data-ip="close" aria-label="${esc(this.t("close"))}" title="${esc(this.t("close"))}"><ha-icon icon="mdi:close"></ha-icon></button></div>
      <div class="ip-tools">
        <span class="ip-search"><ha-icon icon="mdi:magnify" aria-hidden="true"></ha-icon>
          <input type="search" id="ip-search" autocomplete="off" spellcheck="false" aria-label="${esc(this.t("iconSearch"))}" placeholder="${esc(this.t("iconSearch"))}" aria-controls="ip-grid"></span>
        <select id="ip-cat" aria-label="${esc(this.t("iconCategory"))}"></select>
      </div>
      <p class="ip-info" id="ip-info" aria-live="polite">${esc(this.t("loading"))}</p>
      <div class="ip-grid" id="ip-grid" role="listbox" aria-labelledby="ip-title"></div>
      <div class="ip-foot"><span class="ip-sel" id="ip-sel"></span>
        <button class="secondary" id="ip-more" hidden></button>
        ${def || current ? `<button class="secondary" data-ip="default">${def ? `<ha-icon icon="mdi:${esc(def)}"></ha-icon>` : ""}<span>${esc(def ? this.t("iconUseDefault") : this.t("iconClear"))}</span></button>` : ""}
        <button class="secondary" data-ip="close">${esc(this.t("cancel"))}</button></div>`;
    this.shadowRoot.appendChild(dialog);
    const $ = (sel) => dialog.querySelector(sel);
    const search = $("#ip-search"); const cat = $("#ip-cat"); const grid = $("#ip-grid");
    const info = $("#ip-info"); const more = $("#ip-more"); const sel = $("#ip-sel");
    let chosen = null;
    dialog.addEventListener("close", () => {
      dialog.remove();
      if (chosen !== null) this._setIconValue(input, chosen);
      (opener || input).focus();
    });
    dialog.addEventListener("click", (ev) => {
      const button = ev.target.closest("[data-ip]");
      if (button?.dataset.ip === "close") dialog.close();
      else if (button?.dataset.ip === "default") { chosen = ""; dialog.close(); }
      else if (ev.target === dialog) dialog.close(); // click on the backdrop
    });
    dialog.showModal();
    search.focus();

    let data;
    try { data = await this._iconData(); } catch (err) { info.textContent = String(err.message || err); return; }
    const recent = this._recentIcons();
    const tags = data.tags.map((tag, index) => ({ index, label: this._lang === "pl" ? ICON_TAGS_PL[tag] || tag : tag }))
      .sort((a, b) => a.label.localeCompare(b.label, this._lang));
    cat.innerHTML = `${entity ? `<option value="suggested">${esc(this.t("iconSuggested"))}</option>` : ""}
      <option value="recent">${esc(this.t("iconRecent"))}</option><option value="all">${esc(this.t("iconAll"))}</option>
      <optgroup label="${esc(this.t("iconCategories"))}">${tags.map((t) => `<option value="${t.index}">${esc(t.label)}</option>`).join("")}</optgroup>`;
    cat.value = entity ? "suggested" : recent.length ? "recent" : "all";

    const PAGE = 240;
    let rows = []; let shown = 0;
    const describe = (row) => {
      if (!row) { sel.innerHTML = ""; return; }
      const notes = [row.aliases ? this.t("iconAliases", { aliases: row.aliases.split(" ").slice(0, 4).join(", ") }) : "", row.deprecated ? this.t("iconDeprecated") : ""].filter(Boolean);
      sel.innerHTML = `<ha-icon icon="mdi:${esc(row.name)}"></ha-icon><span><b>${esc(row.name)}</b>${notes.length ? `<small>${esc(notes.join(" · "))}</small>` : ""}</span>`;
    };
    const tile = (row, index) => `<button type="button" role="option" class="ip-icon${row.name === current ? " selected" : ""}" aria-selected="${row.name === current}" tabindex="${index === 0 ? 0 : -1}" data-name="${esc(row.name)}" title="${esc(row.name)}"><ha-icon icon="mdi:${esc(row.name)}"></ha-icon><span>${esc(row.name)}</span></button>`;
    const page = () => {
      const next = rows.slice(shown, shown + PAGE);
      grid.insertAdjacentHTML("beforeend", next.map((row, i) => tile(row, shown + i)).join(""));
      shown += next.length;
      more.hidden = rows.length <= shown;
      more.textContent = this.t("iconMore", { n: Math.min(PAGE, rows.length - shown) });
    };
    const update = () => {
      const query = search.value.trim();
      const tag = /^\d+$/.test(cat.value) ? Number(cat.value) : null;
      if (query) rows = this._searchIcons(data, query, Infinity, tag);
      else if (cat.value === "suggested") rows = this._suggestedIcons(data, entity, def);
      else if (cat.value === "recent") rows = recent.map((name) => data.byName.get(name)).filter(Boolean);
      else if (tag !== null) rows = data.rows.filter((row) => row.tags.includes(tag));
      else rows = [...data.rows.filter((row) => !row.deprecated), ...data.rows.filter((row) => row.deprecated)];
      grid.innerHTML = ""; shown = 0;
      page();
      const empty = !query && cat.value === "recent" ? this.t("iconRecentEmpty") : this.t("iconNone");
      info.textContent = rows.length ? `${this.t("iconCount", { n: rows.length })} · ${this.t("iconFont", { version: data.mdi })}` : empty;
      describe(data.byName.get(current) || null);
    };
    let timer = null;
    search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(update, 120); });
    cat.addEventListener("change", update);
    more.addEventListener("click", () => {
      const first = shown;
      page();
      grid.children[first]?.focus();
    });
    grid.addEventListener("click", (ev) => {
      const button = ev.target.closest(".ip-icon");
      if (button) { chosen = button.dataset.name; dialog.close(); }
    });
    const hover = (ev) => { const button = ev.target.closest?.(".ip-icon"); if (button) describe(data.byName.get(button.dataset.name)); };
    grid.addEventListener("mouseover", hover);
    grid.addEventListener("focusin", hover);
    // Arrow keys move through the grid (one tab stop), Enter/Space choose.
    grid.addEventListener("keydown", (ev) => {
      const tiles = [...grid.querySelectorAll(".ip-icon")];
      const index = tiles.indexOf(ev.target.closest(".ip-icon"));
      if (index < 0) return;
      const columns = Math.max(1, getComputedStyle(grid).gridTemplateColumns.split(" ").length);
      const moves = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: columns, ArrowUp: -columns, Home: -index, End: tiles.length - 1 - index,
        PageDown: columns * 4, PageUp: -columns * 4 };
      if (!(ev.key in moves)) return;
      ev.preventDefault();
      if (ev.key === "ArrowUp" && index < columns) { search.focus(); return; }
      const target = tiles[Math.max(0, Math.min(tiles.length - 1, index + moves[ev.key]))];
      tiles[index].tabIndex = -1; target.tabIndex = 0; target.focus();
    });
    search.addEventListener("keydown", (ev) => {
      const first = grid.querySelector(".ip-icon");
      if (ev.key === "ArrowDown" && first) { ev.preventDefault(); first.focus(); }
      else if (ev.key === "Enter" && first) { ev.preventDefault(); chosen = first.dataset.name; dialog.close(); }
    });
    update();
    grid.querySelector(".ip-icon.selected")?.scrollIntoView({ block: "center" });
  }

  _toHex(value) {
    const part = (n) => Math.max(0, Math.min(255, Number(n) || 0)).toString(16).padStart(2, "0");
    if (Array.isArray(value) && value.length === 3) return `#${value.map(part).join("")}`;
    if (typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value)) return value;
    return "";
  }

  // --- events -----------------------------------------------------------------------------------
  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) => {
      const event = el.tagName === "SELECT" || (el.tagName === "INPUT" && el.type === "checkbox") ? "change" : "click";
      el.addEventListener(event, (ev) => this._action(el.dataset.action, el, ev));
    });
    root.querySelectorAll("[data-path][data-kind]").forEach((el) => {
      el.addEventListener("focus", () => { this._pendingSnapshot = JSON.stringify(this._config); });
      el.addEventListener("input", () => this._input(el));
      el.addEventListener("change", () => this._commit(el));
    });
    root.querySelectorAll("input[data-icons]").forEach((el) => {
      el.addEventListener("input", (ev) => { if (ev.isTrusted) this._suggest(el); }); // typing, not a picked icon
      el.addEventListener("keydown", (ev) => this._suggestKeys(el, ev));
      el.addEventListener("blur", () => setTimeout(() => this._closeSuggest(el), 150));
      const list = root.getElementById(`${el.id}-list`);
      list?.addEventListener("mousedown", (ev) => ev.preventDefault()); // keep the focus in the field
      list?.addEventListener("click", (ev) => {
        const option = ev.target.closest("li[data-name]");
        if (option) this._setIconValue(el, option.dataset.name);
      });
    });
    if (this._config) { this._fillDatalists(); this._loadDefaultIcons(); }
    // Icon names of the panel font: unknown icons show what the panel shows (alert-circle-outline).
    if (root.querySelector("input[data-icons]")) {
      this._iconData().then(() => {
        root.querySelectorAll("input[data-icons]").forEach((el) => this._updateIconField(el));
        root.querySelectorAll("[data-own-icon]").forEach((el) => el.setAttribute("icon", this._iconPreview(el.dataset.ownIcon)));
      }).catch(() => {});
    }
    this._bindDrag();
    const yaml = root.getElementById("yaml");
    if (yaml) yaml.addEventListener("input", () => { this._yamlText = yaml.value; });
    this._updateStatus();
  }

  _keys(ev) {
    const mod = ev.ctrlKey || ev.metaKey;
    const typing = ["TEXTAREA", "INPUT"].includes(ev.target.tagName);
    const key = ev.key.toLowerCase();
    if (mod && key === "s") { ev.preventDefault(); this._save(); }
    else if (mod && !ev.shiftKey && key === "z" && !typing) { ev.preventDefault(); this._undoRedo(this._undo, this._redo); }
    else if (mod && (key === "y" || (ev.shiftKey && key === "z")) && !typing) { ev.preventDefault(); this._undoRedo(this._redo, this._undo); }
    else if (ev.altKey && (ev.key === "ArrowUp" || ev.key === "ArrowDown")) {
      const li = ev.target.closest?.("li[data-index]");
      if (!li) return;
      ev.preventDefault();
      const from = Number(li.dataset.index);
      const to = from + (ev.key === "ArrowUp" ? -1 : 1);
      if (li.classList.contains("card-item")) this._moveCard(from, to, true);
      else if (li.dataset.items) this._moveItem(JSON.parse(li.dataset.items), from, to, true);
    }
  }

  _value(el) {
    const kind = el.dataset.kind;
    const raw = el.value;
    if (kind === "bool") return el.checked;
    if (kind === "int" || kind === "brightness") {
      if (raw === "") return undefined;
      return Number.isInteger(Number(raw)) ? Number(raw) : raw;
    }
    if (kind === "strings") return raw.trim() === "" ? undefined : raw.split(",").map((s) => s.trim()).filter(Boolean);
    if (kind === "color") {
      const text = raw.trim();
      if (!text) return undefined;
      const m = text.match(/^\[?\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]?$/);
      if (m) return [Number(m[1]), Number(m[2]), Number(m[3])];
      if (/^\d+$/.test(text)) return Number(text);
      try { if (text.startsWith("{")) return JSON.parse(text); } catch (err) { /* keep text */ }
      return text;
    }
    if (el.dataset.json) {
      const text = raw.trim();
      if (!text) return undefined;
      try { return JSON.parse(text); } catch (err) {
        const obj = {};
        for (const line of text.split("\n")) {
          const at = line.indexOf(":");
          if (at > 0) obj[line.slice(0, at).trim()] = line.slice(at + 1).trim();
        }
        return Object.keys(obj).length ? obj : text;
      }
    }
    return raw === "" ? undefined : raw;
  }

  _input(el) {
    const path = JSON.parse(el.dataset.path);
    const kind = el.dataset.kind;
    if (kind === "multiselect" || kind === "bool") return;
    // Undo: the state before the first keystroke of this edit (committed on "change").
    if (this._pendingSnapshot === undefined) this._pendingSnapshot = JSON.stringify(this._config);
    if (kind === "color-picker") {
      const hex = el.value;
      const rgb = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
      this._set(path, rgb);
      const text = el.parentElement.querySelector("input[type=text]");
      if (text) text.value = `[${rgb.join(", ")}]`;
      this._changed();
      return;
    }
    this._set(path, this._value(el));
    if (el.dataset.output) el.nextElementSibling.textContent = `${el.value}%`;
    if (el.dataset.icons) this._updateIconField(el);
    this._changed();
  }

  _commit(el) {
    const path = JSON.parse(el.dataset.path);
    const kind = el.dataset.kind;
    const before = this._pendingSnapshot ?? JSON.stringify(this._config);
    if (kind === "multiselect") {
      const current = Array.isArray(this._get(path)) ? this._get(path) : [];
      const next = el.checked ? [...new Set([...current, el.dataset.value])] : current.filter((v) => v !== el.dataset.value);
      this._set(path, next.length ? next : undefined);
    } else if (kind === "bool") this._set(path, el.checked);
    if (before !== undefined && before !== JSON.stringify(this._config)) {
      this._undo.push(before); this._redo = [];
      if (this._undo.length > 100) this._undo.shift();
    }
    this._pendingSnapshot = JSON.stringify(this._config);
    // Entities, keys, titles and selects change other parts of the form (options, lists, preview).
    const last = path[path.length - 1];
    this._changed({ render: ["entity", "key", "title", "type"].includes(last) || el.tagName === "SELECT" });
  }

  async _action(action, el) {
    const panel = this._config ? this._panelConf : null;
    switch (action) {
      case "menu": this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })); break;
      case "save": await this._save(); break;
      case "reload": await this._reload(); break;
      case "fromdisk": await this._loadFromDisk(); break;
      case "undo": this._undoRedo(this._undo, this._redo); break;
      case "redo": this._undoRedo(this._redo, this._undo); break;
      case "section":
        this._section = el.dataset.section; this._cardIndex = 0;
        if (this._section === "yaml" && this._dirty) {
          try { this._yamlText = (await this.ws("yaml", { config: this._config })).yaml; } catch (err) { /* keep */ }
        }
        this._render();
        break;
      case "panel": this._panelName = el.value; this._render(); break;
      case "card": this._cardIndex = Number(el.dataset.index); this._render(); break;
      case "add-panel": {
        const name = await this._prompt(this.t("addPanel"), this.t("panelName"), "nspanel");
        if (!name || this._config.nspanels[name]) return;
        this._snapshot();
        this._config.nspanels[name] = { panelRecvTopic: "tele/tasmota_XXXXXX/RESULT", panelSendTopic: "cmnd/tasmota_XXXXXX/CustomSend",
          locale: this._lang === "pl" ? "pl_PL" : "en_US", timeFormat: "%H:%M", dateFormat: "full",
          screensaver: { entities: [] }, cards: [{ type: "cardEntities", title: "NSPanel", entities: [] }] };
        this._panelName = name; this._section = "settings";
        this._changed({ render: true });
        break;
      }
      case "delete-panel": {
        if ((await this._dialog(this.t("deletePanel"), this.t("confirmDeletePanel", { name: this._panelName }), [{ id: "yes", label: this.t("delete"), danger: true }])) !== "yes") return;
        this._snapshot();
        delete this._config.nspanels[this._panelName];
        this._panelName = this._panelNames[0];
        this._changed({ render: true });
        break;
      }
      case "add-card": {
        const type = await this._chooseType();
        if (!type) return;
        this._snapshot();
        const list = el.dataset.list;
        if (!Array.isArray(panel[list])) panel[list] = [];
        const card = { type, title: this.l(this._schema.cards[type].label) };
        if (this._schema.cards[type].items) card.entities = [];
        panel[list].push(card);
        this._cardIndex = panel[list].length - 1;
        this._changed({ render: true });
        break;
      }
      case "card-type": {
        const path = JSON.parse(el.dataset.path);
        if ((await this._dialog(this.t("type"), this.t("changeType"), [{ id: "yes", label: this.t("ok"), primary: true }])) !== "yes") { this._render(); return; }
        this._snapshot();
        this._set(path, el.value);
        if (this._schema.cards[el.value]?.items && !Array.isArray(this._get(path.slice(0, -1)).entities)) this._get(path.slice(0, -1)).entities = [];
        this._changed({ render: true });
        break;
      }
      case "pick-icon": await this._openIconPicker(this.shadowRoot.getElementById(el.dataset.target)); break;
      case "card-up": this._moveCard(Number(el.dataset.index), Number(el.dataset.index) - 1); break;
      case "card-down": this._moveCard(Number(el.dataset.index), Number(el.dataset.index) + 1); break;
      case "card-duplicate": {
        const cards = panel[this._section];
        const index = Number(el.dataset.index);
        this._snapshot();
        const copy = clone(cards[index]);
        if (copy && copy.key) copy.key = `${copy.key}_2`;
        cards.splice(index + 1, 0, copy);
        this._cardIndex = index + 1;
        this._changed({ render: true });
        break;
      }
      case "card-delete": {
        const cards = panel[this._section];
        const index = Number(el.dataset.index);
        const name = cards[index]?.title || cards[index]?.type;
        if ((await this._dialog(this.t("delete"), this.t("confirmDelete", { name }), [{ id: "yes", label: this.t("delete"), danger: true }])) !== "yes") return;
        this._snapshot();
        cards.splice(index, 1);
        this._cardIndex = Math.max(0, Math.min(this._cardIndex, cards.length - 1));
        this._changed({ render: true });
        break;
      }
      case "item-add": {
        const path = JSON.parse(el.dataset.items);
        this._snapshot();
        const items = this._get(path);
        if (Array.isArray(items)) items.push({ entity: "" }); else this._set(path, [{ entity: "" }]);
        this._changed({ render: true });
        const inputs = this.shadowRoot.querySelectorAll(`li[data-items='${CSS.escape(el.dataset.items)}'] input[data-kind=entity]`);
        inputs[inputs.length - 1]?.focus();
        break;
      }
      case "item-up": this._moveItem(JSON.parse(el.dataset.items), Number(el.dataset.index), Number(el.dataset.index) - 1); break;
      case "item-down": this._moveItem(JSON.parse(el.dataset.items), Number(el.dataset.index), Number(el.dataset.index) + 1); break;
      case "item-delete": {
        const path = JSON.parse(el.dataset.items);
        this._snapshot();
        this._get(path).splice(Number(el.dataset.index), 1);
        this._changed({ render: true });
        break;
      }
      case "schedule-toggle": {
        const path = JSON.parse(el.dataset.path);
        this._snapshot();
        const current = this._get(path);
        if (el.checked) this._set(path, [{ time: "07:00", value: typeof current === "number" ? current : Number(el.dataset.default) }, { time: "22:00", value: 0 }]);
        else this._set(path, Array.isArray(current) && current[0] ? current[0].value : undefined);
        this._changed({ render: true });
        break;
      }
      case "row-add": {
        this._snapshot();
        this._get(JSON.parse(el.dataset.row)).push({ time: "12:00", value: 50 });
        this._changed({ render: true });
        break;
      }
      case "row-delete": {
        const path = JSON.parse(el.dataset.row);
        this._snapshot();
        this._get(path.slice(0, -1)).splice(path[path.length - 1], 1);
        this._changed({ render: true });
        break;
      }
      case "apply-yaml": {
        const out = this.shadowRoot.getElementById("yaml-error");
        try {
          const result = await this.ws("yaml", { yaml: this.shadowRoot.getElementById("yaml").value });
          this._snapshot();
          this._config = result.config;
          if (!this._config.nspanels || typeof this._config.nspanels !== "object") this._config.nspanels = {};
          if (!this._panelNames.includes(this._panelName)) this._panelName = this._panelNames[0];
          this._file.parse_error = null;
          this._changed({ render: true });
          this._toast(this.t("yamlApplied"), "success");
        } catch (err) { out.innerHTML = `<span class="error">${esc(err.message || err)}</span>`; }
        break;
      }
      default: break;
    }
  }

  _moveCard(from, to, focus = false) {
    const cards = this._panelConf[this._section];
    if (!Array.isArray(cards) || to < 0 || to >= cards.length || from === to) return;
    this._snapshot();
    const [card] = cards.splice(from, 1);
    cards.splice(to, 0, card);
    if (this._cardIndex === from) this._cardIndex = to;
    this._changed({ render: true });
    if (focus) this.shadowRoot.querySelector(`li.card-item[data-index="${to}"] .card-select`)?.focus();
  }

  _moveItem(path, from, to, focus = false) {
    const items = this._get(path);
    if (!Array.isArray(items) || to < 0 || to >= items.length || from === to) return;
    this._snapshot();
    const [item] = items.splice(from, 1);
    items.splice(to, 0, item);
    this._changed({ render: true });
    if (focus) this.shadowRoot.querySelector(`li[data-items='${CSS.escape(JSON.stringify(path))}'][data-index="${to}"] input`)?.focus();
  }

  _bindDrag() {
    this.shadowRoot.querySelectorAll("li[draggable=true]").forEach((li) => {
      li.addEventListener("dragstart", (ev) => {
        if (["INPUT", "TEXTAREA", "SELECT"].includes(ev.target.tagName)) { ev.preventDefault(); return; }
        this._dragFrom = { index: Number(li.dataset.index), items: li.dataset.items || null };
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", li.dataset.index);
        li.classList.add("dragging");
      });
      li.addEventListener("dragend", () => li.classList.remove("dragging"));
      li.addEventListener("dragover", (ev) => {
        if (this._dragFrom && (li.dataset.items || null) === this._dragFrom.items) { ev.preventDefault(); li.classList.add("drop"); }
      });
      li.addEventListener("dragleave", () => li.classList.remove("drop"));
      li.addEventListener("drop", (ev) => {
        ev.preventDefault();
        li.classList.remove("drop");
        const from = this._dragFrom;
        this._dragFrom = null;
        if (!from || (li.dataset.items || null) !== from.items) return;
        if (from.items) this._moveItem(JSON.parse(from.items), from.index, Number(li.dataset.index));
        else this._moveCard(from.index, Number(li.dataset.index));
      });
    });
  }

  // --- dialogs and feedback ---------------------------------------------------------------------
  _dialog(title, text, buttons) {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.setAttribute("aria-labelledby", "dlg-title");
      dialog.innerHTML = `<h2 id="dlg-title">${esc(title)}</h2><p>${esc(text)}</p><div class="actions">
        <button class="secondary" value="cancel">${esc(this.t("cancel"))}</button>
        ${buttons.map((b) => `<button value="${b.id}" class="${b.primary ? "primary" : b.danger ? "danger" : "secondary"}">${esc(b.label)}</button>`).join("")}</div>`;
      dialog.addEventListener("click", (ev) => {
        const button = ev.target.closest("button");
        if (button) dialog.close(button.value);
      });
      dialog.addEventListener("close", () => { resolve(dialog.returnValue || "cancel"); dialog.remove(); });
      this.shadowRoot.appendChild(dialog);
      dialog.showModal();
      (dialog.querySelector(".primary") || dialog.querySelector("button.secondary"))?.focus();
    });
  }

  _prompt(title, label, value) {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.innerHTML = `<form method="dialog"><h2>${esc(title)}</h2><div class="field"><label for="prompt">${esc(label)}</label>
        <input id="prompt" type="text" required pattern="[A-Za-z0-9_\\-]+" value="${esc(value)}"></div>
        <div class="actions"><button class="secondary" value="cancel" formnovalidate>${esc(this.t("cancel"))}</button><button class="primary" value="ok">${esc(this.t("ok"))}</button></div></form>`;
      dialog.addEventListener("close", () => {
        resolve(dialog.returnValue === "ok" ? dialog.querySelector("#prompt").value.trim() : null);
        dialog.remove();
      });
      this.shadowRoot.appendChild(dialog);
      dialog.showModal();
      dialog.querySelector("#prompt").select();
    });
  }

  _chooseType() {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.setAttribute("aria-labelledby", "type-title");
      dialog.innerHTML = `<h2 id="type-title">${esc(this.t("chooseType"))}</h2><div class="type-grid">${this._schema.card_types.map((type) => {
        const spec = this._schema.cards[type];
        return `<button value="${type}"><ha-icon icon="${esc(spec.icon)}"></ha-icon><span>${esc(this.l(spec.label))}</span><small>${type}</small></button>`;
      }).join("")}</div><div class="actions"><button class="secondary" value="cancel">${esc(this.t("cancel"))}</button></div>`;
      dialog.addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (b) dialog.close(b.value); });
      dialog.addEventListener("close", () => { resolve(dialog.returnValue && dialog.returnValue !== "cancel" ? dialog.returnValue : null); dialog.remove(); });
      this.shadowRoot.appendChild(dialog);
      dialog.showModal();
      dialog.querySelector(".type-grid button")?.focus();
    });
  }

  _toast(text, kind = "info", action = null) {
    const box = this.shadowRoot.getElementById("toasts");
    if (!box) return;
    const toast = document.createElement("div");
    toast.className = `toast ${kind}`;
    toast.setAttribute("role", kind === "error" ? "alert" : "status");
    toast.innerHTML = `<span>${esc(text)}</span>${action ? `<button class="link">${esc(action.label)}</button>` : ""}<button class="icon small" aria-label="${esc(this.t("close"))}"><ha-icon icon="mdi:close"></ha-icon></button>`;
    const buttons = toast.querySelectorAll("button");
    if (action) buttons[0].addEventListener("click", () => { toast.remove(); action.run(); });
    buttons[buttons.length - 1].addEventListener("click", () => toast.remove());
    box.appendChild(toast);
    setTimeout(() => toast.remove(), kind === "error" ? 12000 : 8000);
  }

  _busy(on, text = "") {
    const el = this.shadowRoot.getElementById("busy");
    if (!el) return;
    el.hidden = !on;
    el.textContent = text;
    this.shadowRoot.querySelectorAll(".toolbar button").forEach((b) => { if (on) b.setAttribute("aria-disabled", "true"); else b.removeAttribute("aria-disabled"); });
  }
}

const STYLE = `
:host { display: block; container-type: inline-size; min-height: 100%; background: var(--primary-background-color); color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, sans-serif); --gap: 16px; --radius: var(--ha-card-border-radius, 12px); }
* { box-sizing: border-box; }
[hidden] { display: none !important; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.toolbar { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 8px; min-height: var(--header-height, 56px);
  padding: 0 12px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
  border-bottom: 1px solid var(--app-header-border-bottom, transparent); }
.toolbar h1 { font-size: 20px; font-weight: 400; margin: 0 8px 0 4px; white-space: nowrap; }
.toolbar .spacer { flex: 1; }
.toolbar button { color: inherit; }
.toolbar .primary { background: var(--app-header-text-color, #fff); color: var(--app-header-background-color, var(--primary-color)); }
.toolbar .secondary { border-color: currentColor; }
.status { font-size: 13px; opacity: .85; padding: 2px 8px; border-radius: 12px; }
.status.dirty { background: rgba(255,255,255,.22); font-weight: 500; opacity: 1; }
button { font: inherit; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; border-radius: 18px; padding: 6px 14px;
  min-height: 36px; border: 1px solid transparent; background: none; color: var(--primary-color); }
button:disabled, button[aria-disabled=true] { opacity: .45; cursor: default; }
button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible {
  outline: 2px solid var(--primary-color); outline-offset: 2px; }
.toolbar button:focus-visible { outline-color: currentColor; }
.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
.secondary { border-color: var(--divider-color); }
.danger { background: var(--error-color); color: #fff; }
button.icon { padding: 6px; border-radius: 50%; min-width: 40px; justify-content: center; }
button.icon.small { min-width: 32px; min-height: 32px; padding: 4px; color: var(--secondary-text-color); }
button.link { padding: 0; min-height: 0; border: 0; text-decoration: underline; color: var(--primary-color); text-align: left; }
button.wide { width: 100%; justify-content: center; margin-top: 8px; }
.center { padding: 48px; text-align: center; }
.banner { margin: 12px var(--gap) 0; padding: 12px 16px; border-radius: var(--radius); border-left: 4px solid; background: var(--card-background-color); }
.banner.error { border-color: var(--error-color); } .banner.warning { border-color: var(--warning-color); }
.layout { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: var(--gap); padding: var(--gap); max-width: 1500px; margin: 0 auto; }
.side, .content, .card-list, .card-editor { background: var(--card-background-color); border-radius: var(--radius);
  border: 1px solid var(--divider-color); }
.side { padding: 12px; align-self: start; position: sticky; top: calc(var(--header-height, 56px) + 16px); }
.content { padding: var(--gap); min-width: 0; }
.content.plain { background: none; border: 0; padding: 0; }
.panel-select label { font-size: 12px; color: var(--secondary-text-color); }
.row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
.panel-select select { flex: 1; min-width: 0; }
nav { display: flex; flex-direction: column; gap: 2px; margin: 12px 0; }
button.nav { justify-content: flex-start; border-radius: 8px; color: var(--primary-text-color); width: 100%; }
button.nav.active { background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); font-weight: 500; }
button.nav .label { flex: 1; text-align: left; }
.badge { min-width: 20px; height: 20px; border-radius: 10px; font-size: 12px; display: inline-flex; align-items: center; justify-content: center; padding: 0 6px; }
.badge:empty { display: none; }
.badge.error { background: var(--error-color); color: #fff; } .badge.warning { background: var(--warning-color); color: #000; }
.summary ul { padding-left: 18px; margin: 6px 0; font-size: 13px; max-height: 40vh; overflow: auto; }
.summary li { margin-bottom: 4px; }
.summary li.error::marker { color: var(--error-color); } .summary li.warning::marker { color: var(--warning-color); }
.summary summary { cursor: pointer; font-size: 14px; }
.cards { display: grid; grid-template-columns: minmax(240px, 340px) minmax(0, 1fr); gap: var(--gap); }
.card-list { padding: 8px; align-self: start; }
.card-editor { padding: var(--gap); min-width: 0; }
ol { list-style: none; margin: 0; padding: 0; }
.card-item { display: flex; align-items: center; gap: 4px; border-radius: 8px; padding: 2px; border: 1px solid transparent; }
.card-item.active { background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); border-color: var(--primary-color); }
.card-item.drop, .entity-row.drop { border-color: var(--primary-color); border-style: dashed; }
.card-item.dragging, .entity-row.dragging { opacity: .4; }
.handle { cursor: grab; color: var(--secondary-text-color); display: inline-flex; padding: 4px; }
.card-select { flex: 1; min-width: 0; justify-content: flex-start; color: var(--primary-text-color); padding: 6px 4px; border-radius: 8px; }
.card-name { display: flex; flex-direction: column; min-width: 0; text-align: left; flex: 1; }
.card-name span, .card-name small { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-name small { color: var(--secondary-text-color); font-size: 12px; }
.item-actions { display: inline-flex; }
.card-item .item-actions { opacity: .55; } .card-item:hover .item-actions, .card-item:focus-within .item-actions { opacity: 1; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px 16px; }
.field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.field.wide { grid-column: 1 / -1; }
.field > label, .field > .label, fieldset legend { font-size: 13px; color: var(--secondary-text-color); font-weight: 500; }
.req { color: var(--error-color); }
input[type=text], input[type=number], select, textarea { font: inherit; width: 100%; padding: 8px 10px; border-radius: 6px;
  border: 1px solid var(--input-outlined-idle-border-color, var(--divider-color)); background: var(--input-fill-color, var(--secondary-background-color));
  color: var(--primary-text-color); min-height: 40px; }
textarea { resize: vertical; font-family: var(--ha-font-family-code, monospace); font-size: 13px; }
input[aria-invalid=true], select[aria-invalid=true], textarea[aria-invalid=true] { border-color: var(--error-color); border-width: 2px; }
.field.has-warning input, .field.has-warning select { border-color: var(--warning-color); }
input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--primary-color); margin: 0; }
input[type=range] { width: 100%; accent-color: var(--primary-color); }
.range { display: flex; align-items: center; gap: 12px; }
.range output { min-width: 110px; font-size: 13px; color: var(--secondary-text-color); }
.help { color: var(--secondary-text-color); font-size: 12px; }
.issues span { display: block; font-size: 12px; margin-top: 2px; }
.issues .error, .error-text { color: var(--error-color); } .issues .warning { color: var(--warning-color); }
.checks { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.checks label, label.inline { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; }
.icon-input, .color-input { display: flex; align-items: center; gap: 6px; }
.icon-input { min-width: 0; }
button.icon-pick { flex: none; width: 40px; min-width: 40px; height: 40px; padding: 0; justify-content: center; border-radius: 8px;
  border: 1px solid var(--input-outlined-idle-border-color, var(--divider-color)); background: var(--input-fill-color, var(--secondary-background-color));
  color: var(--state-icon-color, var(--primary-text-color)); }
button.icon-pick:hover { border-color: var(--primary-color); }
.is-default button.icon-pick { border-style: dashed; color: var(--secondary-text-color); }
.unknown button.icon-pick { border-color: var(--warning-color); color: var(--warning-color); }
.combo { position: relative; flex: 1; min-width: 0; }
.is-default .combo input::placeholder { color: var(--secondary-text-color); opacity: 1; font-style: italic; }
.suggest { position: absolute; z-index: 20; top: calc(100% + 2px); left: 0; min-width: 100%; width: max-content; max-width: min(340px, 90vw);
  max-height: 300px; overflow: auto; margin: 0; padding: 4px; background: var(--card-background-color); border: 1px solid var(--divider-color);
  border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.suggest li { display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.suggest li:hover { background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); }
.suggest li[aria-selected=true] { background: rgba(var(--rgb-primary-color, 3, 169, 244), .25); box-shadow: inset 3px 0 var(--primary-color); }
dialog.icon-dialog { width: min(860px, calc(100vw - 32px)); height: min(720px, calc(100dvh - 32px)); max-width: none; padding: 0; }
dialog.icon-dialog[open] { display: flex; flex-direction: column; }
.ip-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 12px 0 20px; }
.ip-head h2 { margin: 0; }
.ip-tools { display: flex; gap: 8px; padding: 12px 20px 4px; flex-wrap: wrap; }
.ip-search { flex: 2 1 260px; display: flex; align-items: center; gap: 6px; padding-left: 10px; border-radius: 6px;
  border: 1px solid var(--input-outlined-idle-border-color, var(--divider-color)); background: var(--input-fill-color, var(--secondary-background-color)); }
.ip-search ha-icon { color: var(--secondary-text-color); }
.ip-search input { border: 0; background: none; padding-left: 0; }
.ip-search:focus-within { outline: 2px solid var(--primary-color); outline-offset: 1px; }
.ip-search input:focus-visible { outline: none; }
.ip-tools select { flex: 1 1 200px; width: auto; }
.ip-info { margin: 4px 20px; font-size: 12px; color: var(--secondary-text-color); }
.ip-grid { flex: 1; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 4px;
  align-content: start; padding: 4px 16px 12px; border-top: 1px solid var(--divider-color); }
button.ip-icon { flex-direction: column; justify-content: flex-start; gap: 4px; padding: 10px 4px 6px; min-height: 84px; border-radius: 10px;
  color: var(--primary-text-color); --mdc-icon-size: 32px; }
button.ip-icon span { font-size: 10.5px; line-height: 1.25; color: var(--secondary-text-color); word-break: break-word; text-align: center;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
button.ip-icon:hover { background: rgba(var(--rgb-primary-color, 3, 169, 244), .08); }
button.ip-icon:focus-visible { background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); outline-offset: -2px; }
button.ip-icon.selected { background: rgba(var(--rgb-primary-color, 3, 169, 244), .18); border-color: var(--primary-color); }
.ip-foot { display: flex; align-items: center; gap: 8px; padding: 10px 16px 12px 20px; border-top: 1px solid var(--divider-color); flex-wrap: wrap; }
.ip-sel { flex: 1; display: flex; align-items: center; gap: 10px; min-width: 0; --mdc-icon-size: 32px; }
.ip-sel span { display: flex; flex-direction: column; min-width: 0; }
.ip-sel b { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ip-sel small { color: var(--secondary-text-color); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 600px) {
  dialog.icon-dialog { width: 100vw; height: 100dvh; max-height: none; margin: 0; border-radius: 0; }
  .ip-grid { grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); padding: 4px 8px 8px; }
  .ip-sel { flex-basis: 100%; }
}
.color-input input[type=color] { width: 44px; height: 40px; padding: 2px; border-radius: 6px; border: 1px solid var(--divider-color); background: none; flex: none; }
details { margin-top: 12px; }
details > summary { cursor: pointer; color: var(--primary-color); font-weight: 500; padding: 6px 0; }
details.advanced { border-top: 1px solid var(--divider-color); padding-top: 8px; }
fieldset.items { border: 1px solid var(--divider-color); border-radius: var(--radius); margin: 16px 0 0; padding: 12px; min-width: 0; }
.entity-row { border: 1px solid var(--divider-color); border-radius: 8px; padding: 8px; margin-bottom: 8px; }
.entity-main { display: grid; grid-template-columns: auto minmax(0, 2fr) minmax(0, 1.5fr) minmax(0, 1.5fr) auto; gap: 8px; align-items: center; }
.card-editor { container-type: inline-size; }
@container (max-width: 640px) {
  .entity-main { grid-template-columns: auto minmax(0, 1fr) auto; }
  .entity-main > input, .entity-main > textarea, .entity-main > .icon-input { grid-column: 1 / -1; }
  .entity-main > .item-actions { grid-column: 3; grid-row: 1; }
}
.nested { border-left: 3px solid var(--divider-color); padding-left: 12px; }
.schedule ol li { display: grid; grid-template-columns: 1fr 100px auto; gap: 8px; margin-bottom: 6px; }
.preview { margin-top: 20px; }
.preview h3 { font-size: 14px; color: var(--secondary-text-color); font-weight: 500; margin: 0 0 8px; }
.screen { width: 100%; max-width: 480px; aspect-ratio: 3 / 2; background: #1c1c1c; color: #fff; border-radius: 10px; padding: 12px 16px;
  display: flex; flex-direction: column; border: 6px solid #2b2b2b; }
.p-title { text-align: center; font-size: 18px; margin-bottom: 8px; }
.p-body { flex: 1; display: flex; flex-direction: column; gap: 6px; overflow: hidden; }
.grid-screen .p-body { display: grid; grid-template-columns: repeat(3, 1fr); }
.p-row { display: flex; align-items: center; gap: 10px; font-size: 15px; min-height: 28px; }
.grid-screen .p-row { flex-direction: column; justify-content: center; font-size: 12px; text-align: center; }
.p-icon { color: #4fc3f7; width: 26px; display: inline-flex; justify-content: center; }
.p-name { flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; } .p-state { color: #bbb; }
.grid-screen .p-state { display: none; }
.p-big { text-align: center; font-size: 22px; display: flex; flex-direction: column; } .p-big small { color: #bbb; font-size: 14px; }
.p-qr { display: flex; justify-content: center; --mdc-icon-size: 96px; }
.empty { color: var(--secondary-text-color); padding: 24px; text-align: center; }
.yaml textarea { min-height: 50vh; }
.toasts { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; z-index: 10; width: min(560px, calc(100% - 32px)); }
.toast { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 8px; background: var(--card-background-color);
  color: var(--primary-text-color); box-shadow: 0 4px 16px rgba(0,0,0,.3); border-left: 4px solid var(--primary-color); }
.toast span { flex: 1; }
.toast.success { border-color: var(--success-color, #4caf50); } .toast.error { border-color: var(--error-color); }
.busy { position: fixed; top: calc(var(--header-height, 56px) + 8px); right: 16px; z-index: 5; background: var(--card-background-color); padding: 8px 14px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
dialog { border: 0; border-radius: var(--radius); padding: 20px 24px; background: var(--card-background-color); color: var(--primary-text-color);
  max-width: min(560px, calc(100vw - 32px)); box-shadow: 0 8px 32px rgba(0,0,0,.4); }
dialog::backdrop { background: rgba(0,0,0,.45); }
dialog h2 { margin: 0 0 12px; font-size: 20px; font-weight: 400; }
dialog .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; flex-wrap: wrap; }
.type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.type-grid button { flex-direction: column; padding: 14px 8px; border: 1px solid var(--divider-color); border-radius: 10px; color: var(--primary-text-color); }
.type-grid small { color: var(--secondary-text-color); font-size: 11px; }
@container (max-width: 1060px) { .cards { grid-template-columns: minmax(0, 1fr); } }
@container (max-width: 760px) {
  .layout { grid-template-columns: minmax(0, 1fr); padding: 8px; gap: 8px; }
  .side { position: static; }
  nav { flex-direction: row; overflow-x: auto; }
  button.nav { width: auto; white-space: nowrap; }
  .summary { display: none; }
  .toolbar button span { display: none; }
  .toolbar button.primary, .toolbar button.secondary { padding: 6px 10px; }
  .toolbar .status, .toolbar .spacer { display: none; }
  .toolbar { gap: 2px; padding: 0 4px; }
  .toolbar h1 { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: 18px; margin: 0 4px; }
  .toolbar button.icon { min-width: 36px; padding: 4px; }
  .toolbar button.primary, .toolbar button.secondary { min-width: 40px; justify-content: center; }
  .entity-main { grid-template-columns: auto minmax(0, 1fr) auto; }
  .entity-main > input, .entity-main > textarea, .entity-main > .icon-input { grid-column: 1 / -1; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
`;

customElements.get("nspanel-card-editor") || customElements.define("nspanel-card-editor", NSPanelCardEditor);
